"""Finnish National Gallery — lokalny cache obiektow (API /v1/search niedostepne)."""

from __future__ import annotations

import gzip
import json
import ssl
import urllib.request
from pathlib import Path

from .artist_match import artist_index_tokens, artist_match, index_lookup_fuzzy
from .env_keys import fng_api_key
from .filters import maybe_add_hit, scan_cap
from .http import USER_AGENT
from .score import apply_scores
from .text_norm import norm_search_text
from .types import ArtworkHit

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
FNG_OBJECTS_GZ = CACHE_DIR / "fng_objects.json.gz"
FNG_OBJECTS_URL = "https://kokoelma.kansallisgalleria.fi/api/v1/objects"

_rows: list[dict[str, object]] | None = None
_artist_index: dict[str, set[int]] | None = None


def reset_fng_cache_for_tests() -> None:
    global _rows, _artist_index
    _rows = None
    _artist_index = None


def fng_cache_ready() -> bool:
    return FNG_OBJECTS_GZ.is_file() and FNG_OBJECTS_GZ.stat().st_size > 100


def ensure_fng_cache(*, timeout: float = 600.0) -> Path:
    """Pobiera pelna liste obiektow (raz, ~270 MB skompresowane)."""
    if fng_cache_ready() and FNG_OBJECTS_GZ.stat().st_size > 1_000_000:
        return FNG_OBJECTS_GZ

    key = fng_api_key()
    if not key:
        raise RuntimeError("Brak FNG_API_KEY w cursor-api/.env")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        FNG_OBJECTS_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "x-api-key": key,
        },
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        raw = resp.read()
    if not raw:
        raise RuntimeError("Pusta odpowiedz FNG /v1/objects")
    FNG_OBJECTS_GZ.write_bytes(raw if raw[:2] == b"\x1f\x8b" else gzip.compress(raw))
    reset_fng_cache_for_tests()
    return FNG_OBJECTS_GZ


def _pick_text(block: object) -> str:
    if isinstance(block, str):
        return block.strip()
    if isinstance(block, dict):
        for key in ("en", "fi", "sv"):
            val = block.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        for val in block.values():
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def _artist_name(row: dict[str, object]) -> str:
    names: list[str] = []
    for person in row.get("people") or []:
        if not isinstance(person, dict):
            continue
        role = person.get("role") or {}
        role_fi = role.get("fi") if isinstance(role, dict) else ""
        fn = str(person.get("firstName") or "").strip()
        ln = str(person.get("familyName") or "").strip()
        full = " ".join(x for x in (fn, ln) if x).strip()
        if not full:
            continue
        if role_fi == "taiteilija":
            return full
        names.append(full)
    return names[0] if names else ""


def _image_url(row: dict[str, object]) -> str:
    for media in row.get("multimedia") or []:
        if not isinstance(media, dict):
            continue
        jpg = media.get("jpg") or {}
        if isinstance(jpg, dict):
            url = str(jpg.get("500") or jpg.get("1000") or "").strip()
            if url:
                return url
    return ""


def _load_rows() -> list[dict[str, object]]:
    global _rows
    if _rows is not None:
        return _rows
    if not FNG_OBJECTS_GZ.is_file():
        ensure_fng_cache()
    with gzip.open(FNG_OBJECTS_GZ, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise RuntimeError("Niepoprawny format cache FNG")
    _rows = [row for row in data if isinstance(row, dict)]
    return _rows


def _load_artist_index(rows: list[dict[str, object]]) -> dict[str, set[int]]:
    global _artist_index
    if _artist_index is not None:
        return _artist_index
    index: dict[str, set[int]] = {}
    for idx, row in enumerate(rows):
        for token in artist_index_tokens(_artist_name(row)):
            index.setdefault(token, set()).add(idx)
    _artist_index = index
    return index


def search_fng_local(
    *,
    artist: str = "",
    title: str = "",
    limit: int = 8,
) -> list[ArtworkHit]:
    artist = (artist or "").strip()
    title = (title or "").strip()
    if not artist and not title:
        return []

    rows = _load_rows()
    index = _load_artist_index(rows)
    cap = scan_cap(limit)

    candidate_idxs: set[int] | None = None
    if artist:
        candidate_idxs = index_lookup_fuzzy(index, artist, fetch_wikidata=True)
        if not candidate_idxs:
            return []

    title_norm = norm_search_text(title) if title else ""
    hits: list[ArtworkHit] = []
    for idx, row in enumerate(rows):
        if candidate_idxs is not None and idx not in candidate_idxs:
            continue
        if len(hits) >= cap * 3:
            break
        title_text = _pick_text(row.get("title"))
        if not title_text:
            continue
        if title_norm and title_norm not in norm_search_text(title_text):
            continue
        adn = _artist_name(row)
        if artist and not artist_match(artist, adn, fetch_wikidata=True):
            continue
        if not _image_url(row):
            continue
        oid = str(row.get("objectId") or row.get("id") or "").strip()
        hit = ArtworkHit(
            source_id="fng",
            source_name="Finnish National Gallery",
            title=title_text,
            artist=adn,
            date=_pick_text(row.get("timePeriod")),
            medium=_pick_text(row.get("technique")),
            object_type=_pick_text(row.get("classification") or row.get("category")),
            object_url=f"https://www.kansallisgalleria.fi/en/object/{oid}" if oid else "",
            image_url=_image_url(row),
            search_mode="local",
            score=1.0,
            raw_id=oid,
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break

    scored = apply_scores(hits, query_artist=artist, query_title=title)
    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:limit]
