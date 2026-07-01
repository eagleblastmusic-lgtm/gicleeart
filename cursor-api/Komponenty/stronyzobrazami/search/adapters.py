"""Adaptery wyszukiwania — REST API muzeow i kolekcji."""

from __future__ import annotations

import inspect
import re
import urllib.parse
from typing import Callable

from .artic_images import artic_fetch_headers, artic_preview_url, is_artic_image_url
from .belvedere_iiif import belvedere_search_url, parse_belvedere_manifest
from .birmingham_trust_api import search_birmingham_trust
from .cooper_hewitt_api import search_cooper_hewitt
from .env_keys import SIGNUP_URL, smithsonian_api_key
from .europeana_api import search_europeana
from .fng_api import search_fng
from .iiif_presentation_search import ALBERTINA_IIIF_SEARCH, iiif_search_url, parse_iiif_manifest
from .loc_api import search_loc
from .nypl_api import search_nypl
from .paris_musees_api import search_paris_musees as paris_musees_query
from .risd_api import search_risd
from .tepapa_api import search_tepapa
from .wellcome_api import search_wellcome

from .filters import filter_hits, maybe_add_hit, scan_cap
from .http import get_json, post_json
from .mia_images import mia_preview_url
from .newfields_api import (
    NEWFIELDS_PAGE_SIZE,
    NEWFIELDS_SEARCH,
    newfields_artwork_url,
    newfields_artwork_meta,
    newfields_creators,
    newfields_date,
    newfields_image_url,
)
from .artist_match import artist_match
from .local_data import search_nga, search_walters
from .registry import SourceDef
from .rijks_lod import RIJKS_SEARCH, parse_rijks_object
from .smithsonian_media import smithsonian_object_url
from .types import ArtworkHit
from .web_urls import build_web_search_url
from .web_urls import web_fallback_hits

CancelCheck = Callable[[], bool] | None

MET_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
ARTIC_BASE = "https://api.artic.edu/api/v1/artworks/search"
CLEVELAND_BASE = "https://openaccess-api.clevelandart.org/api/artworks/"
SMK_BASE = "https://api.smk.dk/api/v1/art/search/"
MIA_BASE = "https://search.artsmia.org/"
SMITHSONIAN_BASE = "https://api.si.edu/openaccess/api/v1.0/search"
GETTY_SEARCH = "https://www.getty.edu/art/collection/api/search"
_GETTY_EXCLUDED_TYPES = frozenset(
    {
        "Drawing",
        "Print",
        "Album",
        "Book",
        "Portfolio",
        "Card photograph",
    }
)
_GETTY_DEFAULT_TYPES = ("Painting", "Photograph")


def _cleveland_image_url(images: dict) -> str:
    if not isinstance(images, dict):
        return ""
    for key in ("print", "web", "full"):
        block = images.get(key) or {}
        if isinstance(block, dict):
            url = str(block.get("url") or block.get("full") or "").strip()
            if url:
                return url
    return ""


def _getty_preview_url(manifest: dict) -> str:
    if not isinstance(manifest, dict):
        return ""
    thumb = str(manifest.get("thumb") or "").strip()
    if thumb and "media.getty.edu" in thumb and "/full/" in thumb:
        service = thumb.split("/full/", 1)[0]
        return f"{service}/full/800,/0/default.jpg"
    mid = str(manifest.get("@id") or "").strip()
    if mid and "iiif" in mid.lower():
        service = mid.split("/full/", 1)[0].rstrip("/")
        return f"{service}/full/800,/0/default.jpg"
    return thumb


def _combined_query(*, artist: str, title: str) -> str:
    return " ".join(x.strip() for x in (artist, title) if x.strip())


def _artist_in_text(artist: str, text: str) -> bool:
    return artist_match(artist, text, fetch_wikidata=True)


def _rows_to_hits(
    rows: list[dict[str, str]],
    *,
    source_id: str,
    source_name: str,
    artist: str,
    title: str,
    limit: int,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    hits: list[ArtworkHit] = []
    for row in rows:
        if cancel_check and cancel_check():
            break
        t = str(row.get("title") or "").strip()
        adn = str(row.get("artist") or "").strip()
        if title and title.lower() not in t.lower():
            continue
        if artist and not _artist_in_text(artist, adn) and not _artist_in_text(artist, t):
            continue
        hit = ArtworkHit(
            source_id=source_id,
            source_name=source_name,
            title=t,
            artist=adn,
            date=str(row.get("date") or ""),
            medium=str(row.get("medium") or ""),
            object_url=str(row.get("object_url") or ""),
            image_url=str(row.get("image_url") or ""),
            object_type=str(row.get("object_type") or ""),
            search_mode="api",
            score=1.0,
            raw_id=str(row.get("raw_id") or ""),
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def _search_rows_api(
    fn: Callable[..., list[dict[str, str]]],
    *,
    source_id: str,
    source_name: str,
    artist: str,
    title: str,
    limit: int,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []
    rows = fn(query=q, limit=limit)
    return _rows_to_hits(
        rows,
        source_id=source_id,
        source_name=source_name,
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_met(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []
    params = {"q": q, "hasImages": "true"}
    if artist and not title:
        params["artistOrCulture"] = "true"
    if title and not artist:
        params["title"] = "true"
    data = get_json(f"{MET_BASE}/search?{urllib.parse.urlencode(params)}", timeout=20)
    ids = (data or {}).get("objectIDs") or []
    hits: list[ArtworkHit] = []
    for oid in ids[: scan_cap(limit)]:
        if cancel_check and cancel_check():
            break
        obj = get_json(f"{MET_BASE}/objects/{oid}", timeout=15)
        if not isinstance(obj, dict):
            continue
        adn = obj.get("artistDisplayName") or ""
        if not _artist_in_text(artist, adn):
            continue
        t = str(obj.get("title") or "").strip()
        if not t:
            continue
        img = (obj.get("primaryImage") or obj.get("primaryImageSmall") or "").strip()
        obj_type = str(obj.get("classification") or obj.get("objectName") or "")
        hit = ArtworkHit(
            source_id="met",
            source_name="The Met",
            title=t,
            artist=adn,
            date=str(obj.get("objectDate") or ""),
            medium=str(obj.get("medium") or ""),
            object_url=str(obj.get("objectURL") or ""),
            image_url=img,
            accession=str(obj.get("objectID") or oid),
            department=str(obj.get("department") or ""),
            object_type=obj_type,
            search_mode="api",
            score=1.0,
            raw_id=str(oid),
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_artic(*, artist: str, title: str, limit: int = 8) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []
    params = {
        "q": q,
        "fields": "id,title,artist_display,date_display,medium_display,image_id,artwork_type_title",
        "limit": str(min(scan_cap(limit), 50)),
    }
    data = get_json(f"{ARTIC_BASE}?{urllib.parse.urlencode(params)}", timeout=20)
    hits: list[ArtworkHit] = []
    for row in (data or {}).get("data") or []:
        if not isinstance(row, dict):
            continue
        adn = str(row.get("artist_display") or "")
        if not _artist_in_text(artist, adn):
            continue
        t = str(row.get("title") or "").strip()
        if not t:
            continue
        oid = row.get("id")
        img_id = row.get("image_id")
        obj_type = str(row.get("artwork_type_title") or "")
        img = artic_preview_url(str(img_id)) if img_id else ""
        hit = ArtworkHit(
            source_id="artic",
            source_name="Art Institute of Chicago",
            title=t,
            artist=adn,
            date=str(row.get("date_display") or ""),
            medium=str(row.get("medium_display") or ""),
            object_url=f"https://www.artic.edu/artworks/{oid}",
            image_url=img,
            department=obj_type,
            object_type=obj_type,
            search_mode="api",
            score=1.0,
            raw_id=str(oid or ""),
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_cleveland(*, artist: str, title: str, limit: int = 8) -> list[ArtworkHit]:
    params: dict[str, str | int] = {
        "has_image": 1,
        "limit": min(scan_cap(limit), 40),
    }
    if artist:
        params["artists"] = artist
    if title:
        params["title"] = title
    if not artist and not title:
        return []
    if not artist or not title:
        params["q"] = _combined_query(artist=artist, title=title)
    data = get_json(f"{CLEVELAND_BASE}?{urllib.parse.urlencode(params)}", timeout=25)
    hits: list[ArtworkHit] = []
    for row in (data or {}).get("data") or []:
        if not isinstance(row, dict):
            continue
        creators = row.get("creators") or []
        adn = ""
        if isinstance(creators, list) and creators:
            adn = str((creators[0] or {}).get("description") or "")
        if not _artist_in_text(artist, adn):
            continue
        t = str(row.get("title") or "").strip()
        if not t:
            continue
        images = row.get("images") or {}
        img = _cleveland_image_url(images)
        acc = str(row.get("accession_number") or "")
        obj_type = str(row.get("type") or "")
        hit = ArtworkHit(
            source_id="cleveland",
            source_name="Cleveland Museum of Art",
            title=t,
            artist=adn,
            date=str(row.get("creation_date") or ""),
            medium=str(row.get("technique") or ""),
            object_url=str(row.get("url") or ""),
            image_url=img,
            accession=acc,
            department=str(row.get("department") or ""),
            object_type=obj_type,
            search_mode="api",
            score=1.0,
            raw_id=str(row.get("id") or ""),
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_smk(*, artist: str, title: str, limit: int = 8) -> list[ArtworkHit]:
    keys = _combined_query(artist=artist, title=title)
    if not keys:
        return []
    params = {
        "keys": keys,
        "rows": min(scan_cap(limit), 40),
        "offset": 0,
        "lang": "en",
    }
    data = get_json(f"{SMK_BASE}?{urllib.parse.urlencode(params)}", timeout=25)
    hits: list[ArtworkHit] = []
    for row in (data or {}).get("items") or []:
        if not isinstance(row, dict):
            continue
        titles = row.get("titles") or []
        t = ""
        for block in titles:
            if isinstance(block, dict) and block.get("title"):
                t = str(block["title"])
                if block.get("type") in ("preferred", "title"):
                    break
        artists: list[str] = []
        for prod in row.get("production") or []:
            if isinstance(prod, dict) and prod.get("creator"):
                artists.append(str(prod["creator"]))
        adn = ", ".join(dict.fromkeys(artists))
        if not _artist_in_text(artist, adn):
            continue
        if title and title.lower() not in t.lower():
            continue
        oid = str(row.get("object_number") or row.get("id") or "")
        obj_url = f"https://open.smk.dk/en/artwork/image/{oid}" if oid else "https://open.smk.dk/"
        img = ""
        for img_row in row.get("images") or []:
            if isinstance(img_row, dict) and img_row.get("uri"):
                img = str(img_row["uri"])
                break
        materials = ", ".join(
            str(m.get("material") or m)
            for m in (row.get("materials") or [])
            if isinstance(m, dict) or isinstance(m, str)
        )
        hit = ArtworkHit(
            source_id="smk",
            source_name="SMK (Dania)",
            title=t or oid,
            artist=adn,
            date=str(row.get("production_date") or ""),
            object_url=obj_url,
            image_url=img,
            accession=oid,
            medium=materials,
            search_mode="api",
            score=1.0,
            raw_id=oid,
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_mia(*, artist: str, title: str, limit: int = 8) -> list[ArtworkHit]:
    parts: list[str] = []
    if artist:
        parts.append(f'artist:"{artist}"')
    if title:
        parts.append(f'title:"{title}"')
    q = " ".join(parts) if parts else _combined_query(artist=artist, title=title)
    if not q:
        return []
    url = MIA_BASE + urllib.parse.quote(q)
    data = get_json(url, timeout=25)
    hits: list[ArtworkHit] = []
    for block in ((data or {}).get("hits") or {}).get("hits") or []:
        src = (block or {}).get("_source") or {}
        if not isinstance(src, dict):
            continue
        t = str(src.get("title") or "").strip()
        adn = str(src.get("artist") or "").strip()
        if not t:
            continue
        if not _artist_in_text(artist, adn):
            continue
        oid = str(src.get("id") or "")
        obj_type = str(src.get("classification") or "")
        hit = ArtworkHit(
            source_id="mia",
            source_name="Minneapolis Institute of Art",
            title=t,
            artist=adn,
            date=str(src.get("dated") or src.get("date") or ""),
            medium=str(src.get("medium") or ""),
            object_url=f"https://collections.artsmia.org/art/{oid}" if oid else "",
                image_url=mia_preview_url(oid) if oid else "",
            accession=str(src.get("accession_number") or ""),
            object_type=obj_type,
            search_mode="api",
            score=float((block or {}).get("_score") or 1.0),
            raw_id=oid,
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_smithsonian(*, artist: str, title: str, limit: int = 8) -> list[ArtworkHit]:
    api_key = smithsonian_api_key()
    if not api_key:
        raise RuntimeError(
            "Brak SMITHSONIAN_API_KEY w cursor-api/.env "
            f"(darmowy klucz: {SIGNUP_URL} ). "
            "Ustaw w zakladce Wyszukiwarka → «Klucz Smithsonian…»."
        )
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []
    params = {
        "api_key": api_key,
        "q": q,
        "start": 0,
        "rows": min(scan_cap(limit), 20),
    }
    data = get_json(f"{SMITHSONIAN_BASE}?{urllib.parse.urlencode(params)}", timeout=30)
    hits: list[ArtworkHit] = []
    rows = ((data or {}).get("response") or {}).get("rows") or []
    for row in rows:
        content = (row or {}).get("content") or {}
        descriptive = content.get("descriptiveNonRepeating") or {}
        title_raw = descriptive.get("title")
        if isinstance(title_raw, dict):
            t = str(title_raw.get("content") or "")
        else:
            t = str(title_raw or "")
        indexed = content.get("indexedStructured") or {}
        names = indexed.get("name") or []
        if isinstance(names, str):
            names = [names]
        adn = ", ".join(str(n) for n in names[:3])
        if not _artist_in_text(artist, adn):
            continue
        obj_types = indexed.get("object_type") or []
        if isinstance(obj_types, str):
            obj_types = [obj_types]
        obj_type = ", ".join(str(x) for x in obj_types[:2])
        oid = str((row or {}).get("id") or "")
        url = smithsonian_object_url(row)
        hit = ArtworkHit(
            source_id="smithsonian",
            source_name="Smithsonian",
            title=t or oid,
            artist=adn,
            object_url=url,
            object_type=obj_type,
            search_mode="api",
            score=1.0,
            raw_id=oid,
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_rijks(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    params: dict[str, str] = {"imageAvailable": "true"}
    if artist:
        params["creator"] = artist
    if title:
        params["title"] = title
    if not artist and not title:
        return []
    data = get_json(f"{RIJKS_SEARCH}?{urllib.parse.urlencode(params)}", timeout=25)
    items = data.get("orderedItems") or []
    img_cache: dict[str, str] = {}
    hits: list[ArtworkHit] = []
    for item in items[: scan_cap(limit)]:
        if cancel_check and cancel_check():
            break
        if not isinstance(item, dict):
            continue
        obj_id = str(item.get("id") or "")
        if not obj_id:
            continue
        try:
            obj = get_json(obj_id, timeout=20)
        except RuntimeError:
            continue
        if not isinstance(obj, dict):
            continue
        parsed = parse_rijks_object(obj, cache=img_cache)
        adn = parsed["artist"]
        if not _artist_in_text(artist, adn):
            continue
        t = parsed["title"]
        if title and title.lower() not in t.lower():
            continue
        if not t:
            continue
        hit = ArtworkHit(
            source_id="rijks",
            source_name="Rijksmuseum",
            title=t,
            artist=adn,
            date=parsed["date"],
            object_url=parsed["object_url"],
            image_url=parsed["image_url"],
            accession=parsed["accession"],
            object_type=parsed["object_type"],
            search_mode="api",
            score=1.0,
            raw_id=parsed["raw_id"],
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_belvedere(
    *,
    artist: str,
    title: str,
    limit: int = 8,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []

    cap = scan_cap(limit)
    if cancel_check and cancel_check():
        return []

    root = get_json(belvedere_search_url(q), timeout=20)
    page_url = ""
    for collection in root.get("collections") or []:
        if isinstance(collection, dict):
            page_url = str(collection.get("@id") or "").strip()
            if page_url:
                break
    if not page_url:
        page_url = belvedere_search_url(q, page=1)

    hits: list[ArtworkHit] = []
    page_num = 1
    max_pages = max(3, (cap // 10) + 2)
    while len(hits) < limit and page_num <= max_pages:
        if cancel_check and cancel_check():
            break
        current_url = page_url if page_num == 1 else belvedere_search_url(q, page=page_num)
        page = get_json(current_url, timeout=20)
        manifests = page.get("manifests") or []
        if not manifests:
            break
        for manifest_ref in manifests:
            if cancel_check and cancel_check():
                break
            if len(hits) >= limit:
                break
            if not isinstance(manifest_ref, dict):
                continue
            manifest_url = str(manifest_ref.get("@id") or "").strip()
            if not manifest_url:
                continue
            manifest = get_json(manifest_url, timeout=20)
            if not isinstance(manifest, dict):
                continue
            parsed = parse_belvedere_manifest(manifest)
            t = parsed["title"].strip()
            if not t:
                continue
            if title and title.lower() not in t.lower():
                continue
            adn = parsed["artist"].strip()
            if not _artist_in_text(artist, adn):
                continue
            object_url = parsed["object_url"].strip()
            if object_url and "/en/" not in object_url:
                object_url = object_url.replace(
                    "https://sammlung.belvedere.at/objects/",
                    "https://sammlung.belvedere.at/en/objects/",
                    1,
                )
            hit = ArtworkHit(
                source_id="belvedere",
                source_name="Belvedere",
                title=t,
                artist=adn,
                date=parsed["date"],
                medium=parsed["medium"],
                object_url=object_url or "https://sammlung.belvedere.at/en/search",
                image_url=parsed["image_url"],
                accession=parsed["accession"],
                object_type=parsed["object_type"],
                search_mode="api",
                score=1.0,
                raw_id=parsed["raw_id"],
            )
            if maybe_add_hit(hits, hit, limit=limit):
                continue
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
        total = int(page.get("total") or 0)
        start = int(page.get("startIndex") or 0)
        if total and start + len(manifests) >= total:
            break
        if len(manifests) < 10:
            break
        page_num += 1
    return hits


def search_newfields(
    *,
    artist: str,
    title: str,
    limit: int = 8,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []

    cap = scan_cap(limit)
    hits: list[ArtworkHit] = []
    offset = 0
    while len(hits) < limit and offset < max(cap * 2, NEWFIELDS_PAGE_SIZE):
        if cancel_check and cancel_check():
            break
        data = post_json(
            NEWFIELDS_SEARCH,
            {"searchTerm": q, "from": offset},
            timeout=20,
        )
        results = (data or {}).get("results") or []
        if not results:
            break
        for row in results:
            if cancel_check and cancel_check():
                break
            if not isinstance(row, dict) or row.get("__typename") != "Artwork":
                continue
            t = str(row.get("title") or "").strip()
            if not t:
                continue
            if title and title.lower() not in t.lower():
                continue
            creators = newfields_creators(row)
            if not _artist_in_text(artist, creators):
                continue
            artwork_id = str(row.get("artwork_id") or "").strip()
            if not artwork_id:
                continue
            object_type, medium = newfields_artwork_meta(artwork_id)
            hit = ArtworkHit(
                source_id="newfields",
                source_name="Indianapolis / Newfields",
                title=t,
                artist=creators.split(",")[0].strip() if creators else "",
                date=newfields_date(row),
                object_url=newfields_artwork_url(artwork_id),
                image_url=newfields_image_url(row),
                accession=str(row.get("accession_number") or ""),
                object_type=object_type,
                medium=medium,
                search_mode="api",
                score=1.0,
                raw_id=artwork_id,
            )
            if maybe_add_hit(hits, hit, limit=limit):
                continue
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break
        offset += len(results)
        if len(results) < NEWFIELDS_PAGE_SIZE:
            break
    return hits


def _getty_producer_text(row: dict) -> str:
    names: list[str] = []
    for producer in row.get("producers") or []:
        if not isinstance(producer, dict):
            continue
        primary = str(producer.get("primary_name") or "").strip()
        if primary:
            names.append(primary)
        for name in producer.get("all_names") or []:
            text = str(name or "").strip()
            if text:
                names.append(text)
    return ", ".join(names)


def _getty_artist(row: dict) -> str:
    for producer in row.get("producers") or []:
        if not isinstance(producer, dict):
            continue
        roles = producer.get("role") or []
        if any(str(role).lower() == "artist" for role in roles):
            return str(producer.get("primary_name") or "").strip()
    text = _getty_producer_text(row)
    return text.split(",")[0].strip() if text else ""


def _getty_keep_types(facets: dict) -> list[str]:
    facet_types = [
        str(item.get("name") or "").strip()
        for item in (facets.get("classification_and_object_type") or [])
        if isinstance(item, dict) and item.get("name")
    ]
    keep = [name for name in facet_types if name not in _GETTY_EXCLUDED_TYPES]
    return keep or list(_GETTY_DEFAULT_TYPES)


def search_getty(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []

    cap = scan_cap(limit)
    probe = get_json(
        f"{GETTY_SEARCH}?{urllib.parse.urlencode({'q': q, 'from': 0, 'size': 1})}",
        timeout=20,
    )
    keep_types = _getty_keep_types((probe or {}).get("facets") or {})

    params: list[tuple[str, str]] = [("q", q), ("from", "0"), ("size", str(min(cap, 50)))]
    for obj_type in keep_types:
        params.append(("classification_and_object_type", obj_type))

    if cancel_check and cancel_check():
        return []

    data = get_json(f"{GETTY_SEARCH}?{urllib.parse.urlencode(params, doseq=True)}", timeout=20)
    hits: list[ArtworkHit] = []
    seen: set[str] = set()
    for row in (data or {}).get("data") or []:
        if cancel_check and cancel_check():
            break
        if not isinstance(row, dict):
            continue
        if row.get("is_parent"):
            continue
        oid = str(row.get("id") or "").strip()
        if not oid or oid in seen:
            continue
        t = str(row.get("primary_name") or "").strip()
        if not t:
            continue
        if title and title.lower() not in t.lower():
            continue
        producers = _getty_producer_text(row)
        if not _artist_in_text(artist, producers):
            continue
        seen.add(oid)
        slug = str(row.get("slug_with_path") or "").strip()
        object_url = (
            f"https://www.getty.edu/art/collection{slug}"
            if slug
            else "https://www.getty.edu/art/collection/"
        )
        manifest = row.get("manifest") if isinstance(row.get("manifest"), dict) else {}
        title_lower = t.lower()
        object_type = "Album" if "album" in title_lower else ""
        hit = ArtworkHit(
            source_id="getty",
            source_name="Getty Museum",
            title=t,
            artist=_getty_artist(row),
            date=str(row.get("date_created") or ""),
            object_url=object_url,
            image_url=_getty_preview_url(manifest if isinstance(manifest, dict) else {}),
            accession=str(row.get("accession_number") or row.get("object_number") or ""),
            object_type=object_type,
            search_mode="api",
            score=1.0,
            raw_id=oid.removeprefix("object/"),
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def _search_iiif_collection(
    *,
    source_id: str,
    source_name: str,
    search_base: str,
    artist: str,
    title: str,
    limit: int,
    cancel_check: CancelCheck = None,
    parse_manifest: Callable[[dict], dict[str, str]] | None = None,
) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []

    cap = scan_cap(limit)
    if cancel_check and cancel_check():
        return []

    root = get_json(iiif_search_url(search_base, q), timeout=20)
    page_url = ""
    for collection in root.get("collections") or []:
        if isinstance(collection, dict):
            page_url = str(collection.get("@id") or "").strip()
            if page_url:
                break
    if not page_url:
        page_url = iiif_search_url(search_base, q, page=1)

    parse_fn = parse_manifest or parse_iiif_manifest
    hits: list[ArtworkHit] = []
    page_num = 1
    max_pages = max(3, (cap // 10) + 2)
    while len(hits) < limit and page_num <= max_pages:
        if cancel_check and cancel_check():
            break
        current_url = page_url if page_num == 1 else iiif_search_url(search_base, q, page=page_num)
        page = get_json(current_url, timeout=20)
        manifests = page.get("manifests") or []
        if not manifests:
            break
        for manifest_ref in manifests:
            if cancel_check and cancel_check():
                break
            if len(hits) >= limit:
                break
            if not isinstance(manifest_ref, dict):
                continue
            manifest_url = str(manifest_ref.get("@id") or "").strip()
            if not manifest_url:
                continue
            manifest = get_json(manifest_url, timeout=20)
            if not isinstance(manifest, dict):
                continue
            parsed = parse_fn(manifest)
            t = parsed["title"].strip()
            if not t:
                continue
            if title and title.lower() not in t.lower():
                continue
            adn = parsed["artist"].strip()
            if not _artist_in_text(artist, adn):
                continue
            object_url = parsed["object_url"].strip()
            hit = ArtworkHit(
                source_id=source_id,
                source_name=source_name,
                title=t,
                artist=adn,
                date=parsed["date"],
                medium=parsed["medium"],
                object_url=object_url or build_web_search_url(source_id, artist=artist, title=title),
                image_url=parsed["image_url"],
                accession=parsed["accession"],
                object_type=parsed["object_type"],
                search_mode="api",
                score=1.0,
                raw_id=parsed["raw_id"],
            )
            if maybe_add_hit(hits, hit, limit=limit):
                continue
            if len(hits) >= limit:
                break
        page_num += 1
    return hits


def search_albertina(
    *,
    artist: str,
    title: str,
    limit: int = 8,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    return _search_iiif_collection(
        source_id="albertina",
        source_name="Albertina",
        search_base=ALBERTINA_IIIF_SEARCH,
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_paris_musees(
    *,
    artist: str,
    title: str,
    limit: int = 8,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    q = _combined_query(artist=artist, title=title)
    if not q:
        return []
    if cancel_check and cancel_check():
        return []

    hits: list[ArtworkHit] = []
    for row in paris_musees_query(query=q, limit=limit):
        if cancel_check and cancel_check():
            break
        t = row["title"].strip()
        adn = row["artist"].strip()
        if title and title.lower() not in t.lower():
            continue
        if not _artist_in_text(artist, adn) and not _artist_in_text(artist, t):
            continue
        hit = ArtworkHit(
            source_id="paris_musees",
            source_name="Paris Musées",
            title=t,
            artist=adn,
            date=row.get("date") or "",
            medium=row.get("medium") or "",
            object_url=row.get("object_url") or "",
            image_url=row.get("image_url") or "",
            object_type=row.get("object_type") or "",
            search_mode="api",
            score=1.0,
            raw_id=row.get("raw_id") or "",
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_fng_source(
    *,
    artist: str,
    title: str,
    limit: int = 8,
    cancel_check: CancelCheck = None,
) -> list[ArtworkHit]:
    if cancel_check and cancel_check():
        return []

    hits: list[ArtworkHit] = []
    for row in search_fng(artist=artist, title=title, limit=limit):
        if cancel_check and cancel_check():
            break
        t = row["title"].strip()
        adn = row["artist"].strip()
        if title and title.lower() not in t.lower():
            continue
        if not _artist_in_text(artist, adn):
            continue
        hit = ArtworkHit(
            source_id="fng",
            source_name="Finnish National Gallery",
            title=t,
            artist=adn,
            date=row.get("date") or "",
            medium=row.get("medium") or "",
            object_url=row.get("object_url") or "",
            image_url=row.get("image_url") or "",
            object_type=row.get("object_type") or "",
            search_mode="api",
            score=1.0,
            raw_id=row.get("raw_id") or "",
        )
        if maybe_add_hit(hits, hit, limit=limit):
            continue
        if len(hits) >= limit:
            break
    return hits


def search_birmingham_trust_source(
    *, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None
) -> list[ArtworkHit]:
    return _search_rows_api(
        search_birmingham_trust,
        source_id="birmingham_trust",
        source_name="Birmingham Museums Trust",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_risd_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_risd,
        source_id="risd",
        source_name="RISD Museum",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_loc_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_loc,
        source_id="loc",
        source_name="Library of Congress",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_wellcome_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_wellcome,
        source_id="wellcome",
        source_name="Wellcome Collection",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_tepapa_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_tepapa,
        source_id="tepapa",
        source_name="Te Papa",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_europeana_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_europeana,
        source_id="europeana",
        source_name="Europeana",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_cooper_hewitt_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_cooper_hewitt,
        source_id="cooper_hewitt",
        source_name="Cooper Hewitt",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


def search_nypl_source(*, artist: str, title: str, limit: int = 8, cancel_check: CancelCheck = None) -> list[ArtworkHit]:
    return _search_rows_api(
        search_nypl,
        source_id="nypl",
        source_name="NYPL Digital Collections",
        artist=artist,
        title=title,
        limit=limit,
        cancel_check=cancel_check,
    )


SearchFn = Callable[..., list[ArtworkHit]]

_API_SEARCH: dict[str, SearchFn] = {
    "rijks": search_rijks,
    "met": search_met,
    "artic": search_artic,
    "cleveland": search_cleveland,
    "smk": search_smk,
    "mia": search_mia,
    "smithsonian": search_smithsonian,
    "getty": search_getty,
    "belvedere": search_belvedere,
    "newfields": search_newfields,
    "albertina": search_albertina,
    "paris_musees": search_paris_musees,
    "fng": search_fng_source,
    "risd": search_risd_source,
    "loc": search_loc_source,
    "wellcome": search_wellcome_source,
    "tepapa": search_tepapa_source,
    "europeana": search_europeana_source,
    "cooper_hewitt": search_cooper_hewitt_source,
    "nypl": search_nypl_source,
    "birmingham_trust": search_birmingham_trust_source,
}

_LOCAL_SEARCH: dict[str, SearchFn] = {
    "nga": search_nga,
    "walters": search_walters,
}


def search_source(
    src: SourceDef,
    *,
    artist: str,
    title: str,
    limit: int = 8,
    allow_web_fallback: bool = True,
    cancel_check: CancelCheck = None,
) -> tuple[list[ArtworkHit], str, str]:
    """Zwraca (hits, error, mode)."""
    if cancel_check and cancel_check():
        return [], "Anulowano.", "api"

    fn = _API_SEARCH.get(src.source_id)
    if fn and src.api:
        try:
            call_kwargs: dict[str, object] = {"artist": artist, "title": title, "limit": limit}
            if cancel_check and "cancel_check" in inspect.signature(fn).parameters:
                call_kwargs["cancel_check"] = cancel_check
            hits = fn(**call_kwargs)
            hits = filter_hits(hits)
            return hits, "", "api"
        except Exception as exc:
            if allow_web_fallback and src.web_fallback:
                return web_fallback_hits(src.source_id, src.name, artist=artist, title=title), str(exc), "web"
            return [], str(exc), "api"

    fn_local = _LOCAL_SEARCH.get(src.source_id)
    if fn_local and src.local:
        try:
            call_kwargs: dict[str, object] = {"artist": artist, "title": title, "limit": limit}
            if cancel_check and "cancel_check" in inspect.signature(fn_local).parameters:
                call_kwargs["cancel_check"] = cancel_check
            hits = fn_local(**call_kwargs)
            hits = filter_hits(hits)
            return hits, "", "local"
        except Exception as exc:
            if allow_web_fallback and src.web_fallback:
                return web_fallback_hits(src.source_id, src.name, artist=artist, title=title), str(exc), "web"
            return [], str(exc), "local"

    if allow_web_fallback and src.web_fallback:
        return web_fallback_hits(src.source_id, src.name, artist=artist, title=title), "", "web"

    return [], "Brak adaptera wyszukiwania.", "web"
