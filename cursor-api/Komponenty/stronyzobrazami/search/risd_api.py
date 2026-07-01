"""RISD Museum — Collection API v1."""

from __future__ import annotations

import urllib.parse

from .http import get_json

RISD_COLLECTION = "https://risdmuseum.org/api/v1/collection"


def _artist_from_row(row: dict) -> str:
    primary = str(row.get("primaryMaker") or "").strip()
    if primary:
        return primary
    names: list[str] = []
    for maker in row.get("makers") or []:
        if isinstance(maker, dict):
            name = str(maker.get("name") or "").strip()
            if name:
                names.append(name)
    return ", ".join(names[:3])


def _image_url(row: dict) -> str:
    images = row.get("images") or []
    if isinstance(images, list):
        for img in images:
            u = str(img or "").strip()
            if u.startswith("http"):
                return u
    return ""


def search_risd(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "search_api_fulltext": q,
        "has_images": "1",
        "items_per_page": min(max(limit * 2, 10), 25),
        "page": "0",
    }
    data = get_json(f"{RISD_COLLECTION}?{urllib.parse.urlencode(params)}", timeout=30)
    if not isinstance(data, list):
        return []
    rows: list[dict[str, str]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        url = str(row.get("url") or "").strip()
        if not title or not url:
            continue
        types = row.get("type") or []
        object_type = ", ".join(str(x) for x in types[:2]) if isinstance(types, list) else str(types)
        rows.append(
            {
                "title": title,
                "artist": _artist_from_row(row),
                "date": str(row.get("dating") or ""),
                "medium": str(row.get("mediumTechnique") or ""),
                "object_url": url,
                "image_url": _image_url(row),
                "object_type": object_type,
                "raw_id": str(row.get("id") or ""),
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
