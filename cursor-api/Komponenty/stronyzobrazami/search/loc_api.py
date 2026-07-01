"""Library of Congress — wyszukiwanie JSON (bez klucza API)."""

from __future__ import annotations

import urllib.parse

from .http import get_json

LOC_SEARCH = "https://www.loc.gov/search/"


def _best_image(urls: object) -> str:
    if not urls:
        return ""
    if isinstance(urls, str):
        return urls.split("#", 1)[0]
    if isinstance(urls, list):
        for candidate in reversed(urls):
            u = str(candidate or "").split("#", 1)[0].strip()
            if u.startswith("http"):
                return u
    return ""


def _artist_label(row: dict) -> str:
    for key in ("contributor", "creator"):
        val = row.get(key)
        if isinstance(val, list):
            return ", ".join(str(x) for x in val[:3] if x)
        if val:
            return str(val)
    return ""


def search_loc(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "fo": "json",
        "q": q,
        "at": "results",
        "c": min(max(limit * 4, 12), 40),
        "fa": "online-format:image",
    }
    data = get_json(f"{LOC_SEARCH}?{urllib.parse.urlencode(params)}", timeout=25)
    rows: list[dict[str, str]] = []
    for row in (data or {}).get("results") or []:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not title or not url:
            continue
        rows.append(
            {
                "title": title,
                "artist": _artist_label(row),
                "date": str(row.get("date") or ""),
                "object_url": url,
                "image_url": _best_image(row.get("image_url")),
                "object_type": str(row.get("original_format") or row.get("type") or ""),
                "raw_id": str(row.get("id") or ""),
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
