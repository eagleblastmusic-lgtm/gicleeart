"""NYPL Digital Collections — repo API v2."""

from __future__ import annotations

import urllib.parse

from .env_keys import NYPL_SIGNUP_URL, nypl_api_token
from .http import get_json

NYPL_SEARCH = "https://api.repo.nypl.org/api/v2/items/search"
NYPL_ITEM = "https://digitalcollections.nypl.org/items"


def _title_from_row(row: dict) -> str:
    for key in ("title", "label", "name"):
        val = row.get(key)
        if isinstance(val, list):
            val = val[0] if val else ""
        val = str(val or "").strip()
        if val:
            return val
    return ""


def _image_url(row: dict) -> str:
    for key in ("image_uri", "image_url", "thumbnail", "thumb"):
        val = str(row.get(key) or "").strip()
        if val.startswith("http"):
            return val
    captures = row.get("captures") or row.get("capture") or []
    if isinstance(captures, list):
        for cap in captures:
            if isinstance(cap, dict):
                u = str(cap.get("image_uri") or cap.get("thumbnail") or "").strip()
                if u.startswith("http"):
                    return u
    return ""


def search_nypl(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    token = nypl_api_token()
    if not token:
        raise RuntimeError(
            "Brak NYPL_API_TOKEN w cursor-api/.env "
            f"(rejestracja: {NYPL_SIGNUP_URL} )."
        )
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "q": q,
        "publicDomainOnly": "true",
        "per_page": min(max(limit * 3, 12), 50),
    }
    data = get_json(
        f"{NYPL_SEARCH}?{urllib.parse.urlencode(params)}",
        timeout=30,
        headers={"Authorization": f'Token token="{token}"'},
    )
    candidates = (
        (data or {}).get("nypl_results")
        or (data or {}).get("results")
        or (data or {}).get("items")
        or []
    )
    rows: list[dict[str, str]] = []
    for row in candidates:
        if not isinstance(row, dict):
            continue
        title = _title_from_row(row)
        uuid = str(row.get("uuid") or row.get("id") or "").strip()
        if not title or not uuid:
            continue
        object_url = str(row.get("item_uri") or row.get("uri") or "").strip()
        if not object_url:
            object_url = f"{NYPL_ITEM}/{uuid}"
        rows.append(
            {
                "title": title,
                "artist": str(row.get("creator") or row.get("artist") or ""),
                "date": str(row.get("date") or ""),
                "object_url": object_url,
                "image_url": _image_url(row),
                "object_type": str(row.get("type") or "image"),
                "raw_id": uuid,
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
