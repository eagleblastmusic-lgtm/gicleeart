"""Finnish National Gallery — REST API (kokoelma.kansallisgalleria.fi)."""

from __future__ import annotations

from .env_keys import fng_api_key
from .fng_local import (
    _artist_name,
    _image_url,
    _pick_text,
    search_fng_local,
)
from .http import post_json

# Swagger UI: https://kokoelma.kansallisgalleria.fi/api/swagger
KOKOELMA_API = "https://kokoelma.kansallisgalleria.fi/api"
PUBLIC_OBJECT = "https://www.kansallisgalleria.fi/en/object"


def _row_from_item(item: dict[str, object]) -> dict[str, str]:
    oid = str(item.get("objectId") or item.get("id") or "").strip()
    return {
        "title": _pick_text(item.get("title")),
        "artist": _artist_name(item),
        "date": _pick_text(item.get("timePeriod")),
        "medium": _pick_text(item.get("technique")),
        "object_type": _pick_text(item.get("classification") or item.get("category")),
        "object_url": f"{PUBLIC_OBJECT}/{oid}" if oid else "",
        "image_url": _image_url(item),
        "raw_id": oid,
    }


def search_fng_api(*, artist: str, title: str, limit: int = 8) -> list[dict[str, str]]:
    """POST /v1/search na kokoelma (bez parametru limit — API go odrzuca)."""
    key = fng_api_key()
    if not key:
        raise RuntimeError("Brak FNG_API_KEY w cursor-api/.env")

    terms = [t.strip() for t in (artist, title) if t.strip()]
    if not terms:
        return []

    payload: dict[str, object] = {"searchTerms": terms, "hasImage": True}
    data = post_json(
        f"{KOKOELMA_API}/v1/search",
        payload,
        headers={"x-api-key": key},
        timeout=25,
    )
    if not isinstance(data, list):
        return []

    rows: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        row = _row_from_item(item)
        if row["title"]:
            rows.append(row)
        if len(rows) >= max(limit * 4, limit):
            break
    return rows


def search_fng(*, artist: str, title: str, limit: int = 8) -> list[dict[str, str]]:
    """Najpierw API kokoelma; przy bledzie — lokalny cache /v1/objects."""
    try:
        return search_fng_api(artist=artist, title=title, limit=limit)
    except Exception:
        from .types import ArtworkHit

        hits = search_fng_local(artist=artist, title=title, limit=limit)
        return [
            {
                "title": hit.title,
                "artist": hit.artist,
                "date": hit.date,
                "medium": hit.medium,
                "object_type": hit.object_type,
                "object_url": hit.object_url,
                "image_url": hit.image_url,
                "raw_id": hit.raw_id,
            }
            for hit in hits
        ]
