"""Europeana — Record API v2."""

from __future__ import annotations

import urllib.parse

from .env_keys import EUROPEANA_SIGNUP_URL, europeana_api_key
from .http import get_json

EUROPEANA_SEARCH = "https://api.europeana.eu/record/v2/search.json"


def _creator_label(row: dict) -> str:
    val = row.get("dcCreator") or row.get("edmAgentPrefLabel")
    if isinstance(val, list):
        return ", ".join(str(x) for x in val[:3] if x)
    return str(val or "")


def _preview_url(row: dict) -> str:
    prev = row.get("edmPreview")
    if isinstance(prev, list) and prev:
        return str(prev[0] or "").strip()
    if isinstance(prev, str):
        return prev.strip()
    return ""


def search_europeana(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    key = europeana_api_key()
    if not key:
        raise RuntimeError(
            "Brak EUROPEANA_API_KEY w cursor-api/.env "
            f"(darmowy klucz: {EUROPEANA_SIGNUP_URL} )."
        )
    q = (query or "").strip()
    if not q:
        return []
    params = {
        "wskey": key,
        "query": q,
        "rows": min(max(limit * 3, 12), 40),
        "profile": "rich",
        "reusability": "open",
        "qf": "TYPE:IMAGE",
    }
    data = get_json(f"{EUROPEANA_SEARCH}?{urllib.parse.urlencode(params)}", timeout=30)
    rows: list[dict[str, str]] = []
    for row in (data or {}).get("items") or []:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        if isinstance(title, list):
            title = title[0] if title else ""
        title = str(title or "").strip()
        url = str(row.get("guid") or row.get("link") or "").strip()
        if not title or not url:
            continue
        rows.append(
            {
                "title": title,
                "artist": _creator_label(row),
                "date": str(row.get("year") or ""),
                "object_url": url.split("?", 1)[0],
                "image_url": _preview_url(row),
                "object_type": str(row.get("type") or "IMAGE"),
                "raw_id": str(row.get("id") or ""),
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
