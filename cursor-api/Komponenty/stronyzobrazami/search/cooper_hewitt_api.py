"""Cooper Hewitt — REST API (OAuth access token)."""

from __future__ import annotations

import urllib.parse

from .env_keys import COOPER_HEWITT_SIGNUP_URL, cooper_hewitt_access_token
from .http import get_json

COOPER_REST = "https://api.collection.cooperhewitt.org/rest/"


def _person_label(obj: dict) -> str:
    for key in ("person", "people", "makers"):
        val = obj.get(key)
        if isinstance(val, list) and val:
            parts = []
            for item in val[:3]:
                if isinstance(item, dict):
                    parts.append(str(item.get("name") or item.get("summary") or "").strip())
                elif item:
                    parts.append(str(item))
            return ", ".join(p for p in parts if p)
        if isinstance(val, dict):
            return str(val.get("name") or val.get("summary") or "")
    return str(obj.get("person_name") or "")


def _image_url(obj: dict) -> str:
    images = obj.get("images") or []
    if isinstance(images, list):
        for img in images:
            if isinstance(img, dict):
                u = str(img.get("url") or img.get("z") or "").strip()
                if u.startswith("http"):
                    return u
            elif isinstance(img, str) and img.startswith("http"):
                return img
    return str(obj.get("primary_image") or obj.get("image") or "").strip()


def search_cooper_hewitt(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    token = cooper_hewitt_access_token()
    if not token:
        raise RuntimeError(
            "Brak COOPER_HEWITT_ACCESS_TOKEN w cursor-api/.env "
            f"(token: {COOPER_HEWITT_SIGNUP_URL} )."
        )
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "method": "cooperhewitt.search.objects",
        "access_token": token,
        "query": q,
        "has_images": "1",
        "per_page": min(max(limit * 2, 10), 25),
    }
    data = get_json(f"{COOPER_REST}?{urllib.parse.urlencode(params)}", timeout=30)
    if not isinstance(data, dict) or data.get("stat") != "ok":
        err = ""
        if isinstance(data, dict):
            err = str((data.get("error") or {}).get("error") or data.get("error") or "")
        raise RuntimeError(err or "Blad API Cooper Hewitt")
    rows: list[dict[str, str]] = []
    for obj in (data.get("objects") or data.get("object") or []):
        if not isinstance(obj, dict):
            continue
        title = str(obj.get("title") or obj.get("summary") or "").strip()
        url = str(obj.get("url") or "").strip()
        if not title:
            continue
        if not url and obj.get("id"):
            url = f"https://collection.cooperhewitt.org/objects/{obj['id']}/"
        if not url:
            continue
        rows.append(
            {
                "title": title,
                "artist": _person_label(obj),
                "date": str(obj.get("display_date") or obj.get("date") or ""),
                "medium": str(obj.get("medium") or ""),
                "object_url": url,
                "image_url": _image_url(obj),
                "object_type": str(obj.get("type") or ""),
                "raw_id": str(obj.get("id") or obj.get("tms:id") or ""),
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
