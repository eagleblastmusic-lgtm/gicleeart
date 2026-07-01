"""NGA opendata — miniatury i IIIF z published_images.csv."""

from __future__ import annotations

import csv
from pathlib import Path

from ._cache_files import ensure_cached_csv

_PUBLISHED_URL = (
    "https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data/published_images.csv"
)
_CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "nga_published_images.csv"

_by_object: dict[str, dict[str, str]] | None = None


def _load_published() -> dict[str, dict[str, str]]:
    global _by_object
    if _by_object is not None:
        return _by_object

    path = ensure_cached_csv(_PUBLISHED_URL, _CACHE)
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            oid = (row.get("depictstmsobjectid") or row.get("depictsTmsObjectId") or row.get("depictstmsobjectid") or "").strip()
            if not oid:
                continue
            thumb = (row.get("iiifThumbURL") or row.get("iiifthumburl") or "").strip()
            iiif = (row.get("iiifURL") or row.get("iiifurl") or "").strip()
            view = (row.get("viewtype") or row.get("viewType") or "").strip().lower()
            prev = out.get(oid)
            if prev and view != "primary" and prev.get("viewtype") == "primary":
                continue
            if prev and not iiif and not thumb:
                continue
            out[oid] = {
                "thumb": thumb,
                "iiif": iiif,
                "viewtype": view,
            }

    _by_object = out
    return out


def nga_preview_url(object_id: str | int) -> str:
    oid = str(object_id or "").strip()
    if not oid:
        return ""
    row = _load_published().get(oid) or {}
    thumb = row.get("thumb") or ""
    if thumb:
        return thumb
    iiif = row.get("iiif") or ""
    if iiif:
        base = iiif.rstrip("/")
        return f"{base}/full/!200,200/0/default.jpg"
    return ""


def nga_iiif_service(object_id: str | int) -> str:
    oid = str(object_id or "").strip()
    if not oid:
        return ""
    row = _load_published().get(oid) or {}
    return (row.get("iiif") or "").strip()
