"""Birmingham Museums Trust — Asset Bank (HTML search + metadane strony dziela)."""

from __future__ import annotations

import html
import http.cookiejar
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

import urllib.error
import urllib.request

USER_AGENT = "GicleeArt-StronyZObrazami/1.0 (collection search; +https://giclee.art)"
ROOT = "https://dams.birminghammuseums.org.uk/assetbank-birminghammuseums"
BASE = ROOT + "/action/"
VIEW = BASE + "viewAsset?id="

_PANEL_BLOCK = re.compile(
    r'<li class="panel js-panel js-add-remove asset">(.*?)</li>',
    re.S | re.I,
)
_ASSET_ID = re.compile(r"thumbnail-asset-link-(\d+)", re.I)
_THUMB = re.compile(r'src="(https://[^"]+cloudfront[^"]+)"', re.I)
_ALT = re.compile(r'\salt="([^"]*)"', re.I)
_ATTR_LI = re.compile(r"<li>\s*([^<]+?)\s*</li>", re.S)
_TITLE_PAGE = re.compile(r"Details of the image asset\s+([^|<]+)", re.I)
_ARTIST = re.compile(r"Artist:\s*([^<\n]+)", re.I)
_DATE_IN_DESC = re.compile(r"(\d{4})")
_PAGE_PREVIEW = re.compile(
    r'id="asset_thumbnail_\d+"[^>]*\s+src="(https://[^"]+cloudfront[^"]+)"',
    re.S | re.I,
)
_PAGE_PREVIEW_ALT = re.compile(r'src="(https://d2cbqpmhv5w176\.cloudfront\.net/[^"]+)"', re.I)
_ASSET_DIMS = re.compile(r"(\d{3,5})\s*x\s*\n?\s*(\d{3,5})\s*pixels", re.I)
_SPRING_CSRF = re.compile(r'springCsrfToken\s*=\s*"([^"]+)"')


def _get_html(url: str, *, timeout: float = 25.0) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_search_panels(html_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for block in _PANEL_BLOCK.findall(html_text):
        mid = _ASSET_ID.search(block)
        if not mid:
            continue
        aid = mid.group(1)
        if aid in seen:
            continue
        seen.add(aid)
        thumb_m = _THUMB.search(block)
        alt_m = _ALT.search(block)
        title = ""
        for li in _ATTR_LI.findall(block):
            text = html.unescape(re.sub(r"\s+", " ", li).strip())
            if text.lower().startswith("id:"):
                continue
            if text:
                title = text
                break
        rows.append(
            {
                "raw_id": aid,
                "title": title or (alt_m.group(1).strip() if alt_m else f"Asset {aid}"),
                "image_url": thumb_m.group(1) if thumb_m else "",
                "object_url": VIEW + aid,
            }
        )
    return rows


def _preview_url_from_page(page: str) -> str:
    m = _PAGE_PREVIEW.search(page)
    if m:
        return m.group(1).strip()
    m = _PAGE_PREVIEW_ALT.search(page)
    return m.group(1).strip() if m else ""


def _asset_id(*, object_url: str = "", raw_id: str = "") -> str:
    aid = (raw_id or "").strip()
    if not aid:
        m = re.search(r"[?&]id=(\d+)", object_url or "")
        aid = m.group(1) if m else ""
    return aid


def _parse_asset_dimensions(page: str) -> tuple[int, int]:
    m = _ASSET_DIMS.search(page)
    if not m:
        return 0, 0
    return int(m.group(1)), int(m.group(2))


def _parse_spring_csrf(page: str) -> str:
    m = _SPRING_CSRF.search(page)
    return m.group(1).strip() if m else ""


def _fetch_usage_type_formats(
    opener: urllib.request.OpenerDirector,
    *,
    usage_type_id: int,
    width: int,
    height: int,
    spring_csrf: str,
    timeout: float = 20.0,
) -> list[dict[str, object]]:
    q = urllib.parse.urlencode(
        {
            "id": usage_type_id,
            "height": height or 1,
            "width": width or 1,
            "_csrf": spring_csrf,
        },
    )
    url = f"{ROOT}/go/download/usage-type-formats?{q}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with opener.open(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return data if isinstance(data, list) else []


def _fetch_usage_types(
    opener: urllib.request.OpenerDirector,
    *,
    parent_id: int,
    width: int,
    height: int,
    spring_csrf: str,
    timeout: float = 20.0,
) -> list[dict[str, object]]:
    q = urllib.parse.urlencode(
        {
            "mediaTypeIds": 2,
            "id": parent_id,
            "height": height or 1,
            "width": width or 1,
            "_csrf": spring_csrf,
        },
    )
    url = f"{ROOT}/go/download/usage-types?{q}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with opener.open(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    return data if isinstance(data, list) else []


def _collect_usage_type_ids(
    opener: urllib.request.OpenerDirector,
    *,
    width: int,
    height: int,
    spring_csrf: str,
) -> set[int]:
    """Wszystkie usage type ID dostepne anonimowo (root + dzieci)."""
    seen: set[int] = set()
    queue: list[int] = [-1]
    while queue:
        parent = queue.pop(0)
        try:
            rows = _fetch_usage_types(
                opener,
                parent_id=parent,
                width=width,
                height=height,
                spring_csrf=spring_csrf,
            )
        except (OSError, urllib.error.URLError, json.JSONDecodeError, RuntimeError):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            ut_id = int(row.get("id") or 0)
            if ut_id <= 0 or ut_id in seen:
                continue
            seen.add(ut_id)
            if row.get("hasChildren"):
                queue.append(ut_id)
    # Fallback: niektore formaty (np. High Res Jpeg 10000) sa pod typem 5 bez dziecka w drzewie.
    seen.update(range(1, 20))
    return seen


def _best_jpeg_format_id(
    opener: urllib.request.OpenerDirector,
    *,
    width: int,
    height: int,
    spring_csrf: str,
) -> int:
    """Najwiekszy publiczny JPEG z Asset Bank (do ~10000 px; bez logowania, nie TIF)."""
    best_id = 0
    best_area = 0
    usage_type_ids = _collect_usage_type_ids(
        opener,
        width=width,
        height=height,
        spring_csrf=spring_csrf,
    )
    for ut in sorted(usage_type_ids):
        try:
            formats = _fetch_usage_type_formats(
                opener,
                usage_type_id=ut,
                width=width,
                height=height,
                spring_csrf=spring_csrf,
            )
        except (OSError, urllib.error.URLError, json.JSONDecodeError, RuntimeError):
            continue
        for fmt in formats:
            if not isinstance(fmt, dict):
                continue
            exts = str(fmt.get("supportedExtensions") or "").lower()
            if "jpg" not in exts and "jpeg" not in exts:
                continue
            fw = int(fmt.get("width") or 0)
            fh = int(fmt.get("height") or 0)
            area = fw * fh
            if area > best_area:
                best_area = area
                best_id = int(fmt.get("id") or 0)
    return best_id or 31


def download_birmingham_trust_hd(
    *,
    object_url: str = "",
    raw_id: str = "",
    dest: Path,
    timeout: float = 180.0,
    cancel_check=None,
) -> tuple[int, int]:
    """Pobiera najwiekszy dostepny JPEG przez POST /go/download/usage-type-format."""
    aid = _asset_id(object_url=object_url, raw_id=raw_id)
    if not aid:
        raise RuntimeError("Brak ID dziela Birmingham Museums Trust.")
    page_url = (object_url or "").strip() or VIEW + aid
    if cancel_check and cancel_check():
        raise RuntimeError("Anulowano.")

    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(
        page_url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
    )
    with opener.open(req, timeout=min(timeout, 30.0)) as resp:
        page = resp.read().decode("utf-8", errors="replace")

    spring_csrf = _parse_spring_csrf(page)
    if not spring_csrf:
        raise RuntimeError("Brak tokenu CSRF na stronie Asset Bank.")

    width, height = _parse_asset_dimensions(page)
    format_id = _best_jpeg_format_id(
        opener,
        width=width,
        height=height,
        spring_csrf=spring_csrf,
    )
    if cancel_check and cancel_check():
        raise RuntimeError("Anulowano.")

    body = json.dumps(
        {
            "assetIds": [int(aid)],
            "usageTypeFormatId": format_id,
            "otherDetails": "",
            "cropInfo": None,
        },
    ).encode("utf-8")
    post_req = urllib.request.Request(
        f"{ROOT}/go/download/usage-type-format?_csrf={urllib.parse.quote(spring_csrf, safe='')}",
        data=body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "image/*,application/json,*/*",
        },
    )
    with opener.open(post_req, timeout=timeout) as resp:
        if cancel_check and cancel_check():
            raise RuntimeError("Anulowano.")
        ct = (resp.headers.get("Content-Type") or "").lower()
        data = resp.read()
    if not data or "image" not in ct:
        raise RuntimeError("Asset Bank nie zwrocil obrazu JPEG (wymaga logowania dla pelnego TIF?).")

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    try:
        from PIL import Image

        img = Image.open(BytesIO(data))
        return img.width, img.height
    except (ImportError, OSError, ValueError):
        return 0, 0


def birmingham_trust_download_url(*, object_url: str = "", raw_id: str = "", image_url: str = "") -> str:
    """Podglad JPEG ze strony dziela (miniatury w wynikach wyszukiwania)."""
    aid = _asset_id(object_url=object_url, raw_id=raw_id)
    if not aid:
        return ""
    try:
        page = _get_html(VIEW + urllib.parse.quote(aid, safe=""), timeout=20.0)
    except (OSError, urllib.error.URLError):
        return (image_url or "").strip()
    url = _preview_url_from_page(page)
    if url:
        return url
    current = (image_url or "").strip()
    if current and ".jpg-s.jpg" not in current and "-s.jpg" not in current:
        return current
    return ""


def _fetch_asset_meta(aid: str) -> dict[str, str]:
    out = {"artist": "", "date": "", "medium": "", "image_url": ""}
    try:
        page = _get_html(VIEW + urllib.parse.quote(aid, safe=""), timeout=20.0)
    except (OSError, urllib.error.URLError, RuntimeError):
        return out
    out["image_url"] = _preview_url_from_page(page)
    artist_m = _ARTIST.search(page)
    if artist_m:
        artist_raw = html.unescape(artist_m.group(1).strip())
        out["artist"] = re.sub(r"\s*\(d\.\d{4}\)\s*$", "", artist_raw).strip()
    title_m = _TITLE_PAGE.search(page)
    if title_m:
        out["title"] = html.unescape(title_m.group(1).strip())
    desc_chunk = page[page.lower().find("description") : page.lower().find("description") + 800]
    date_m = _DATE_IN_DESC.search(desc_chunk)
    if date_m:
        out["date"] = date_m.group(1)
    if "oil on" in page.lower():
        m = re.search(r"(Oil on [^<\n]+)", page, re.I)
        if m:
            out["medium"] = html.unescape(m.group(1).strip())
    return out


def search_birmingham_trust(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    url = BASE + "search?" + urllib.parse.urlencode({"keywords": q})
    try:
        html_text = _get_html(url)
    except (OSError, urllib.error.URLError) as exc:
        raise RuntimeError(str(exc)) from exc
    panels = _parse_search_panels(html_text)
    if not panels:
        return []
    cap = min(len(panels), max(limit * 4, 16))
    panels = panels[:cap]

    meta_by_id: dict[str, dict[str, str]] = {}
    workers = min(6, len(panels))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_asset_meta, p["raw_id"]): p["raw_id"] for p in panels}
        for fut in as_completed(futures):
            aid = futures[fut]
            try:
                meta_by_id[aid] = fut.result()
            except Exception:
                meta_by_id[aid] = {}

    rows: list[dict[str, str]] = []
    for panel in panels:
        aid = panel["raw_id"]
        meta = meta_by_id.get(aid) or {}
        row = {
            "title": meta.get("title") or panel["title"],
            "artist": meta.get("artist") or "",
            "date": meta.get("date") or "",
            "medium": meta.get("medium") or "",
            "object_url": panel["object_url"],
            "image_url": meta.get("image_url") or panel["image_url"],
            "object_type": "painting",
            "raw_id": aid,
        }
        rows.append(row)
        if len(rows) >= limit * 3:
            break
    return rows
