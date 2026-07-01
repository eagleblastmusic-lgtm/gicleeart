"""Wellcome Collection — Catalogue API v2."""

from __future__ import annotations

import urllib.parse

from .http import get_json

WELLCOME_WORKS = "https://api.wellcomecollection.org/catalogue/v2/works"
WELLCOME_BASE = "https://wellcomecollection.org/works"


def search_wellcome(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    params = {"query": q, "pageSize": min(max(limit * 3, 12), 40)}
    data = get_json(f"{WELLCOME_WORKS}?{urllib.parse.urlencode(params)}", timeout=25)
    rows: list[dict[str, str]] = []
    for row in (data or {}).get("results") or []:
        if not isinstance(row, dict):
            continue
        wid = str(row.get("id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not wid or not title:
            continue
        thumb = row.get("thumbnail") or {}
        image_url = ""
        if isinstance(thumb, dict):
            image_url = str(thumb.get("url") or "").strip()
        fmt = row.get("workType") or {}
        object_type = str(fmt.get("label") or "") if isinstance(fmt, dict) else ""
        rows.append(
            {
                "title": title,
                "artist": "",
                "date": "",
                "object_url": f"{WELLCOME_BASE}/{wid}",
                "image_url": image_url,
                "object_type": object_type,
                "raw_id": wid,
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
