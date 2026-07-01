"""Newfields (Indianapolis Museum of Art) — wyszukiwanie kolekcji online."""

from __future__ import annotations

import re
import ssl
import urllib.request

from .http import USER_AGENT

NEWFIELDS_SEARCH = "https://collections.discovernewfields.org/api/search"
NEWFIELDS_ARTWORK_BASE = "https://collections.discovernewfields.org/art/artwork"
NEWFIELDS_PAGE_SIZE = 20

_ARTWORK_META_CACHE: dict[str, tuple[str, str]] = {}

_RE_MATERIALS = re.compile(
    r"Materials</span>\s*<div[^>]*>(.*?)</div>",
    re.S | re.I,
)
_RE_OBJECT_TYPES = re.compile(
    r"Object Types</span>\s*<div[^>]*>(.*?)</div>",
    re.S | re.I,
)


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def newfields_artwork_meta(artwork_id: str, *, timeout: float = 15.0) -> tuple[str, str]:
    """Pobiera (object_type, medium) ze strony dziela — API search tego nie zwraca."""
    oid = (artwork_id or "").strip()
    if not oid:
        return "", ""
    if oid in _ARTWORK_META_CACHE:
        return _ARTWORK_META_CACHE[oid]

    object_type = ""
    medium = ""
    url = f"{NEWFIELDS_ARTWORK_BASE}/{oid}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except OSError:
        _ARTWORK_META_CACHE[oid] = ("", "")
        return "", ""

    m_types = _RE_OBJECT_TYPES.search(html)
    if m_types:
        object_type = _strip_html(m_types.group(1))
    m_med = _RE_MATERIALS.search(html)
    if m_med:
        medium = _strip_html(m_med.group(1))

    _ARTWORK_META_CACHE[oid] = (object_type, medium)
    return object_type, medium


def reset_artwork_meta_cache_for_tests() -> None:
    _ARTWORK_META_CACHE.clear()


def newfields_creators(row: dict) -> str:
    names: list[str] = []
    for creator in row.get("creators") or []:
        if not isinstance(creator, dict):
            continue
        party = creator.get("party")
        if isinstance(party, dict):
            name = str(party.get("full_name") or "").strip()
            if name:
                names.append(name)
                continue
        name = str(creator.get("creator") or "").strip()
        if name:
            names.append(name)
    return ", ".join(names)


def newfields_date(row: dict) -> str:
    start = row.get("date_created_earliest")
    end = row.get("date_created_latest")
    if start and end and start != end:
        return f"{start}-{end}"
    if start:
        return str(start)
    if end:
        return str(end)
    return str(row.get("item_date") or "")


def newfields_image_url(row: dict) -> str:
    images = row.get("images") or []
    if not images or not isinstance(images[0], dict):
        return ""
    image = images[0]
    return str(image.get("iiif_thumbnail_url") or image.get("iiif_url") or "").strip()


def newfields_iiif_preview_url(url: str, *, size: int = 200) -> str:
    """URL miniatury — __small to JSON IIIF, nie JPEG; buduj /full/!size,size/."""
    u = (url or "").strip()
    if not u or "iiif.discovernewfields.org" not in u:
        return u
    base = u.removesuffix("__small").rstrip("/")
    if "/full/" in base:
        return re.sub(r"/full/[^/]+/", f"/full/!{size},{size}/", base)
    return f"{base}/full/!{size},{size}/0/default.jpg"


def newfields_artwork_url(artwork_id: str) -> str:
    return f"{NEWFIELDS_ARTWORK_BASE}/{artwork_id}"
