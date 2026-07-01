"""Smithsonian Open Access — miniatury i pelna rozdzielczosc z onlineMedia."""

from __future__ import annotations

import re
import threading
import urllib.parse

from .env_keys import smithsonian_api_key
from .http import get_json

SMITHSONIAN_MEDIA = "https://api.si.edu/openaccess/api/v1.0/content/{record_id}/onlineMedia"
_IDS_DELIVERY = re.compile(
    r"https?://ids\.si\.edu/ids/deliveryService\?id=([^&\"'\\]+)",
    re.IGNORECASE,
)

_media_cache: dict[str, str] = {}
_media_lock = threading.Lock()

def _record_link_url(descriptive: dict) -> str:
    link = descriptive.get("record_link")
    if isinstance(link, dict):
        return str(link.get("content") or link.get("@id") or "").strip()
    return str(link or "").strip()


def smithsonian_object_url(row: dict) -> str:
    content = (row or {}).get("content") or {}
    descriptive = content.get("descriptiveNonRepeating") or {}
    url = _record_link_url(descriptive)
    if url.startswith("http"):
        return url
    oid = str((row or {}).get("id") or "").strip()
    if oid:
        return f"https://www.si.edu/object/{urllib.parse.quote(oid, safe='')}"
    return ""


def _media_urls_from_block(block: dict) -> list[str]:
    urls: list[str] = []
    content = (block or {}).get("content") or {}
    descriptive = content.get("descriptiveNonRepeating") or {}
    online = descriptive.get("online_media") or {}
    if isinstance(online, dict):
        media = online.get("media") or online.get("Media") or []
        if isinstance(media, list):
            for item in media:
                if isinstance(item, dict):
                    u = str(item.get("content") or item.get("@id") or item.get("thumbnail") or "").strip()
                    if u.startswith("http"):
                        urls.append(u)
                elif isinstance(item, str) and item.startswith("http"):
                    urls.append(item)
        thumb = str(online.get("thumbnail") or "").strip()
        if thumb.startswith("http"):
            urls.append(thumb)
    return urls


def _upgrade_ids_url(url: str, *, large: bool) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    m = _IDS_DELIVERY.search(u)
    if m and large:
        base = u.split("&max=", 1)[0].split("&width=", 1)[0]
        return f"{base}&max=0"
    return u


def smithsonian_image_url(record_id: str, *, api_key: str = "", large: bool = False) -> str:
    """Najlepszy URL obrazu z API onlineMedia (ids.si.edu deliveryService)."""
    oid = (record_id or "").strip()
    if not oid:
        return ""
    cache_key = f"{oid}|{1 if large else 0}"
    with _media_lock:
        cached = _media_cache.get(cache_key)
    if cached is not None:
        return cached
    key = (api_key or smithsonian_api_key()).strip()
    if not key:
        return ""
    q = urllib.parse.urlencode({"api_key": key})
    url = SMITHSONIAN_MEDIA.format(record_id=urllib.parse.quote(oid, safe="")) + "?" + q
    try:
        data = get_json(url, timeout=25)
    except RuntimeError:
        with _media_lock:
            _media_cache[cache_key] = ""
        return ""
    rows = ((data or {}).get("response") or {}).get("rows") or []
    best = ""
    for row in rows:
        for media_url in _media_urls_from_block(row):
            if "deliveryService" in media_url or "ids.si.edu" in media_url:
                best = media_url
                break
        if best:
            break
    if not best and rows:
        best = _media_urls_from_block(rows[0])[0] if _media_urls_from_block(rows[0]) else ""
    result = _upgrade_ids_url(best, large=large)
    with _media_lock:
        _media_cache[cache_key] = result
    return result
