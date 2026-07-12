"""Finnish National Gallery — lokalny cache obiektow (API /v1/search niedostepne)."""

from __future__ import annotations

import gzip
import json
import ssl
import urllib.request
from pathlib import Path

from giclee_app.app_paths import atomic_write_bytes, cache_path

from .artist_match import artist_index_tokens, artist_match, index_lookup_fuzzy
from .env_keys import fng_api_key
from .filters import maybe_add_hit, scan_cap
from .http import USER_AGENT
from .score import apply_scores
from .text_norm import norm_search_text
from .types import ArtworkHit

_LEGACY_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"
_LEGACY_FNG_OBJECTS_GZ = _LEGACY_CACHE_DIR / "fng_objects.json.gz"

# Zachowane punkty podmiany dla istniejacych testow i jawnych callerow.
_DEFAULT_CACHE_DIR = _LEGACY_CACHE_DIR
_DEFAULT_FNG_OBJECTS_GZ = _LEGACY_FNG_OBJECTS_GZ
CACHE_DIR = _DEFAULT_CACHE_DIR
FNG_OBJECTS_GZ = _DEFAULT_FNG_OBJECTS_GZ

_RUNTIME_RELATIVE = "Komponenty/stronyzobrazami/data/cache/fng_objects.json.gz"
FNG_OBJECTS_URL = "https://kokoelma.kansallisgalleria.fi/api/v1/objects"

_rows: list[dict[str, object]] | None = None
_artist_index: dict[str, set[int]] | None = None


def _cache_store():
    return cache_path(_RUNTIME_RELATIVE, legacy=_LEGACY_FNG_OBJECTS_GZ)


def _override_cache_file() -> Path | None:
    cache_file = Path(FNG_OBJECTS_GZ)
    if cache_file != _DEFAULT_FNG_OBJECTS_GZ:
        return cache_file

    cache_dir = Path(CACHE_DIR)
    if cache_dir != _DEFAULT_CACHE_DIR:
        return cache_dir / _LEGACY_FNG_OBJECTS_GZ.name
    return None


def _read_cache_file() -> Path:
    override = _override_cache_file()
    return override if override is not None else _cache_store().read_path()


def _write_cache_file() -> Path:
    override = _override_cache_file()
    return override if override is not None else _cache_store().write_path


def reset_fng_cache_for_tests() -> None:
    global _rows, _artist_index
    _rows = None
    _artist_index = None


def fng_cache_ready() -> bool:
    path = _read_cache_file()
    return path.is_file() and path.stat().st_size > 100


def ensure_fng_cache(*, timeout: float = 600.0) -> Path:
    """Pobiera pelna liste obiektow (raz, ~270 MB skompresowane)."""
    current = _read_cache_file()
    if current.is_file() and current.stat().st_size > 1_000_000:
        return current

    key = fng_api_key()
    if not key:
        raise RuntimeError("Brak FNG_API_KEY w cursor-api/.env")

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

    target = _write_cache_file()
    payload = raw if raw[:2] == b"\x1f\x8b" else gzip.compress(raw)
    atomic_write_bytes(target, payload)
    reset_fng_cache_for_tests()
    return target


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

    path = _read_cache_file()
    if not path.is_file():
        path = ensure_fng_cache()
    with gzip.open(path, "rt", encoding="utf-8") as fh:
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
