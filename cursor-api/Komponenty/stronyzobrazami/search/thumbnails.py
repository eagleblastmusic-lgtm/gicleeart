"""Cache i optymalizacja URL miniatur podgladu w wyszukiwarce."""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .artic_images import artic_fetch_headers, is_artic_image_url
from .mia_images import normalize_mia_image_url
from .newfields_api import newfields_iiif_preview_url

USER_AGENT = "GicleeArt-StronyZObrazami/1.0 (collection search)"
PREVIEW_SIZE = (220, 220)
MAX_CACHE_ENTRIES = 150
PREFETCH_LIMIT = 30

_lock = threading.Lock()
_bytes_cache: dict[str, bytes] = {}
_cache_order: list[str] = []


def optimize_preview_url(url: str) -> str:
    """Zmniejsza rozmiar pobieranego pliku (IIIF, Mia, Met CDN)."""
    u = (url or "").strip()
    if not u:
        return ""
    u = normalize_mia_image_url(u)
    u = newfields_iiif_preview_url(u)
    u = re.sub(r"/full/\d+,/", "/full/200,/", u)
    u = re.sub(r"/full/max/", "/full/200,/", u)
    return u


def get_cached_bytes(url: str) -> bytes | None:
    key = optimize_preview_url(url)
    if not key:
        return None
    with _lock:
        return _bytes_cache.get(key)


def _request_headers(url: str) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "image/*"}
    if is_artic_image_url(url):
        headers.update(artic_fetch_headers())
    return headers


def fetch_thumbnail_bytes(url: str, *, timeout: float = 12.0) -> bytes | None:
    key = optimize_preview_url(url)
    if not key:
        return None
    with _lock:
        if key in _bytes_cache:
            return _bytes_cache[key]
    try:
        req = Request(key, headers=_request_headers(key))
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        if not raw:
            return None
        with _lock:
            if key not in _bytes_cache:
                _bytes_cache[key] = raw
                _cache_order.append(key)
                while len(_cache_order) > MAX_CACHE_ENTRIES:
                    old = _cache_order.pop(0)
                    _bytes_cache.pop(old, None)
        return raw
    except (OSError, URLError, ValueError):
        return None


def bytes_to_photo(raw: bytes) -> Any:
    from PIL import Image, ImageTk

    im = Image.open(BytesIO(raw)).convert("RGB")
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # type: ignore[attr-defined]
    im.thumbnail(PREVIEW_SIZE, resample)
    return ImageTk.PhotoImage(im)


def prefetch_urls(urls: list[str], *, max_workers: int = 6, limit: int = PREFETCH_LIMIT) -> None:
    """Pobiera miniatury w tle zaraz po wyszukiwaniu."""
    todo: list[str] = []
    seen: set[str] = set()
    for url in urls:
        key = optimize_preview_url(url)
        if not key or key in seen:
            continue
        seen.add(key)
        with _lock:
            if key in _bytes_cache:
                continue
        todo.append(key)
        if len(todo) >= limit:
            break
    if not todo:
        return

    def _fetch_one(u: str) -> None:
        fetch_thumbnail_bytes(u)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for _ in pool.map(_fetch_one, todo):
            pass


def clear_cache() -> None:
    with _lock:
        _bytes_cache.clear()
        _cache_order.clear()
