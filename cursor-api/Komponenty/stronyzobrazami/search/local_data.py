"""Lokalne zbiory CSV (NGA, Walters) — pobierane raz do cache."""

from __future__ import annotations

import csv
from pathlib import Path

from collections.abc import Callable

from ._cache_files import ensure_cached_csv
from .artist_match import artist_index_tokens, artist_match, index_lookup_fuzzy
from .filters import maybe_add_hit, scan_cap
from .nga_images import nga_preview_url
from .score import apply_scores
from .text_norm import norm_search_text
from .types import ArtworkHit
from . import wikidata_artists

CancelCheck = Callable[[], bool] | None

CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"

_NGA_OBJECTS_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects.csv"
)
_NGA_CONST_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/objects_constituents.csv"
)
_NGA_PEOPLE_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/constituents.csv"
)
_WALTERS_ART_URL = (
    "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/master/art.csv"
)

_nga_artist_by_object: dict[str, list[str]] | None = None
_nga_rows: list[dict[str, str]] | None = None
_nga_by_oid: dict[str, dict[str, str]] | None = None
_nga_artist_index: dict[str, set[str]] | None = None
_nga_people_qid: dict[str, str] | None = None
_walters_rows: list[dict[str, str]] | None = None
_walters_artist_index: dict[str, set[int]] | None = None


def _ensure_file(url: str, dest: Path) -> Path:
    return ensure_cached_csv(url, dest)


def _norm(s: str) -> str:
    return norm_search_text(s)


def _artist_match(needle: str, hay: str) -> bool:
    return artist_match(needle, hay, fetch_wikidata=True)


def _build_nga_artist_index(
    artist_map: dict[str, list[str]],
    *,
    cid_for_name: dict[tuple[str, str], str] | None = None,
    people_qid: dict[str, str] | None = None,
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    cid_for_name = cid_for_name or {}
    people_qid = people_qid or {}
    for oid, names in artist_map.items():
        for name in names:
            cid = cid_for_name.get((oid, name), "")
            qid = people_qid.get(cid, "")
            for token in artist_index_tokens(name, wikidata_qid=qid):
                index.setdefault(token, set()).add(oid)
    return index


def _build_walters_artist_index(rows: list[dict[str, str]]) -> dict[str, set[int]]:
    index: dict[str, set[int]] = {}
    for idx, row in enumerate(rows):
        creators = (row.get("Creators") or row.get("Creator") or "").strip()
        for token in artist_index_tokens(creators):
            index.setdefault(token, set()).add(idx)
    return index


def _load_nga() -> tuple[list[dict[str, str]], dict[str, list[str]]]:
    global _nga_rows, _nga_artist_by_object, _nga_by_oid, _nga_artist_index, _nga_people_qid
    if _nga_rows is not None and _nga_artist_by_object is not None:
        return _nga_rows, _nga_artist_by_object

    objects_path = _ensure_file(_NGA_OBJECTS_URL, CACHE_DIR / "nga_objects.csv")
    const_path = _ensure_file(_NGA_CONST_URL, CACHE_DIR / "nga_objects_constituents.csv")
    people_path = _ensure_file(_NGA_PEOPLE_URL, CACHE_DIR / "nga_constituents.csv")

    people: dict[str, str] = {}
    people_qid: dict[str, str] = {}
    with people_path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            cid = (row.get("constituentid") or row.get("constituentID") or "").strip()
            name = (
                row.get("forwarddisplayname")
                or row.get("preferreddisplayname")
                or row.get("forwardname")
                or row.get("displayname")
                or ""
            ).strip()
            qid = (row.get("wikidataid") or "").strip()
            if cid and name:
                people[cid] = name
            if cid and qid.startswith("Q"):
                people_qid[cid] = qid

    artist_map: dict[str, list[str]] = {}
    cid_for_name: dict[tuple[str, str], str] = {}
    with const_path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            oid = (row.get("objectid") or row.get("objectID") or "").strip()
            cid = (row.get("constituentid") or row.get("constituentID") or "").strip()
            role = (row.get("role") or "").lower()
            if not oid or not cid:
                continue
            if role and role not in ("artist", "maker", "painter", "sculptor", "printmaker"):
                continue
            name = people.get(cid, "")
            if name:
                artist_map.setdefault(oid, []).append(name)
                cid_for_name[(oid, name)] = cid

    rows: list[dict[str, str]] = []
    with objects_path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    by_oid: dict[str, dict[str, str]] = {}
    for row in rows:
        oid = (row.get("objectid") or row.get("objectID") or "").strip()
        if oid:
            by_oid[oid] = row

    _nga_rows = rows
    _nga_artist_by_object = artist_map
    _nga_by_oid = by_oid
    _nga_people_qid = people_qid
    _nga_artist_index = _build_nga_artist_index(
        artist_map,
        cid_for_name=cid_for_name,
        people_qid=people_qid,
    )
    return rows, artist_map


def _load_walters() -> list[dict[str, str]]:
    global _walters_rows, _walters_artist_index
    if _walters_rows is not None:
        return _walters_rows
    path = _ensure_file(_WALTERS_ART_URL, CACHE_DIR / "walters_art.csv")
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        _walters_rows = list(csv.DictReader(f))
    _walters_artist_index = _build_walters_artist_index(_walters_rows)
    return _walters_rows


def _title_match(needle: str, hay: str) -> bool:
    if not needle:
        return True
    return _norm(needle) in _norm(hay)


def _nga_artists(row: dict[str, str], artist_map: dict[str, list[str]], oid: str) -> str:
    from_map = artist_map.get(oid, [])
    if from_map:
        return ", ".join(from_map)
    return (row.get("attribution") or row.get("attributioninverted") or "").strip()


def _nga_row_iter(*, artist: str) -> list[dict[str, str]]:
    rows, _artist_map = _load_nga()
    if not artist:
        return rows
    index = _nga_artist_index or {}
    oids = index_lookup_fuzzy(index, artist, fetch_wikidata=True)
    if oids and _nga_by_oid:
        return [_nga_by_oid[oid] for oid in oids if oid in _nga_by_oid]
    return rows


def search_nga(
    *,
    artist: str,
    title: str,
    limit: int = 12,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    rows, artist_map = _load_nga()
    cap = scan_cap(limit)
    candidates: list[ArtworkHit] = []
    for row in _nga_row_iter(artist=artist):
        if cancel_check and cancel_check():
            break
        oid = (row.get("objectid") or row.get("objectID") or "").strip()
        t = (row.get("title") or "").strip()
        if not t:
            continue
        artists = _nga_artists(row, artist_map, oid)
        if not _title_match(title, t):
            continue
        if not _artist_match(artist, artists):
            continue
        obj_type = (row.get("classification") or "").strip()
        acc = (row.get("accessionnum") or row.get("accessionnumber") or "").strip()
        url = f"https://www.nga.gov/collection/art-object-page.{oid}.html"
        hit = ArtworkHit(
            source_id="nga",
            source_name="National Gallery of Art",
            title=t,
            artist=artists,
            date=(row.get("displaydate") or "").strip(),
            medium=(row.get("medium") or "").strip(),
            object_url=url,
            image_url=nga_preview_url(oid),
            accession=acc,
            object_type=obj_type,
            search_mode="local",
            score=1.0,
            raw_id=oid,
        )
        if maybe_add_hit(candidates, hit, limit=cap):
            pass
        if len(candidates) >= cap:
            break
    scored = apply_scores(candidates, query_artist=artist, query_title=title)
    scored.sort(key=lambda h: h.score, reverse=True)
    return scored[:limit]


def _walters_row_iter(*, artist: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not artist:
        return rows
    index = _walters_artist_index or {}
    idxs = index_lookup_fuzzy(index, artist, fetch_wikidata=True)
    if idxs:
        return [rows[i] for i in sorted(idxs) if 0 <= i < len(rows)]
    return rows


def search_walters(
    *,
    artist: str,
    title: str,
    limit: int = 12,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    rows = _load_walters()
    hits: list[ArtworkHit] = []
    for row in _walters_row_iter(artist=artist, rows=rows):
        if cancel_check and cancel_check():
            break
        t = (row.get("Title") or "").strip()
        creators = (row.get("Creators") or row.get("Creator") or "").strip()
        if not t:
            continue
        if not _title_match(title, t):
            continue
        if not _artist_match(artist, creators):
            continue
        oid = (row.get("ObjectID") or row.get("id") or "").strip()
        acc = (row.get("ObjectNumber") or "").strip()
        obj_type = (row.get("Classification") or "").strip()
        url = f"https://art.thewalters.org/detail/{oid}" if oid else "https://art.thewalters.org/"
        hit = ArtworkHit(
            source_id="walters",
            source_name="Walters Art Museum",
            title=t,
            artist=creators,
            date=(row.get("Date") or "").strip(),
            medium=(row.get("Medium") or "").strip(),
            object_url=url,
            image_url=walters_preview_url(oid),
            accession=acc,
            object_type=obj_type,
            search_mode="local",
            score=1.0,
            raw_id=oid,
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits
