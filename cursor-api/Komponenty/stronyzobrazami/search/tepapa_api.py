"""Te Papa — REST search API."""

from __future__ import annotations

import urllib.parse

from .http import get_json

TEPAPA_SEARCH = "https://collections.tepapa.govt.nz/api/search"
TEPAPA_OBJECT = "https://collections.tepapa.govt.nz/object"
_SKIP_TYPES = frozenset({"Person", "Topic", "Document", "Taxon", "Place"})


def _artist_from_production(row: dict) -> str:
    names: list[str] = []
    for block in row.get("production") or []:
        if not isinstance(block, dict):
            continue
        role = str(block.get("role") or "").lower()
        if role and role not in ("artist", "painter", "printmaker", "photographer", "after"):
            continue
        contrib = block.get("contributor") or {}
        if isinstance(contrib, dict):
            name = str(contrib.get("title") or "").strip()
            if name:
                names.append(name)
        elif block.get("title"):
            names.append(str(block["title"]).split(";")[0].strip())
    return ", ".join(dict.fromkeys(names))


def search_tepapa(*, query: str, limit: int = 8) -> list[dict[str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    params = {"q": q, "type": "Object"}
    data = get_json(f"{TEPAPA_SEARCH}?{urllib.parse.urlencode(params)}", timeout=25)
    rows: list[dict[str, str]] = []
    for row in (data or {}).get("results") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("type") or "") in _SKIP_TYPES:
            continue
        oid = row.get("id")
        title = str(row.get("title") or "").strip()
        if not oid or not title:
            continue
        date = ""
        for block in row.get("production") or []:
            if isinstance(block, dict) and block.get("createdDate"):
                date = str(block["createdDate"])
                break
        rows.append(
            {
                "title": title,
                "artist": _artist_from_production(row),
                "date": date,
                "object_url": f"{TEPAPA_OBJECT}/{oid}",
                "image_url": "",
                "object_type": str(row.get("collectionLabel") or row.get("collection") or ""),
                "raw_id": str(oid),
            }
        )
        if len(rows) >= limit * 3:
            break
    return rows
