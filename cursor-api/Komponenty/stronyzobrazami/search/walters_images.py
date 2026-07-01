"""Walters Art Museum — URL obrazow z media.csv (GitHub API)."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .http import USER_AGENT
from ._cache_files import ensure_cached_csv

_MEDIA_URL = (
    "https://raw.githubusercontent.com/WaltersArtMuseum/api-thewalters-org/master/media.csv"
)
_CACHE = Path(__file__).resolve().parents[1] / "data" / "cache" / "walters_media.csv"

_preview_by_object: dict[str, str] | None = None
_download_by_object: dict[str, str] | None = None

_FRONT_RE = re.compile(r"front", re.I)


def _load_media() -> tuple[dict[str, str], dict[str, str]]:
    global _preview_by_object, _download_by_object
    if _preview_by_object is not None and _download_by_object is not None:
        return _preview_by_object, _download_by_object

    path = ensure_cached_csv(_MEDIA_URL, _CACHE)
    preview: dict[str, str] = {}
    download: dict[str, str] = {}
    rows_by_oid: dict[str, list[dict[str, str]]] = {}

    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            oid = (row.get("ObjectID") or "").strip()
            url = (row.get("ImageURL") or "").strip()
            if not oid or not url.startswith("http"):
                continue
            rows_by_oid.setdefault(oid, []).append(row)

    for oid, rows in rows_by_oid.items():
        primary = [r for r in rows if (r.get("IsPrimary") or "").strip() == "1"]
        front = [r for r in rows if _FRONT_RE.search(r.get("MediaView") or "")]
        chosen = primary or front or rows
        chosen.sort(
            key=lambda r: (
                0 if (r.get("IsPrimary") or "").strip() == "1" else 1,
                0 if _FRONT_RE.search(r.get("MediaView") or "") else 1,
                int((r.get("Rank") or "99") or 99),
            ),
        )
        best = (chosen[0].get("ImageURL") or "").strip()
        if best:
            preview[oid] = best
            download[oid] = best

    _preview_by_object = preview
    _download_by_object = download
    return preview, download


def walters_preview_url(object_id: str | int) -> str:
    oid = str(object_id or "").strip()
    if not oid:
        return ""
    preview, _ = _load_media()
    return preview.get(oid, "")


def walters_download_url(object_id: str | int) -> str:
    oid = str(object_id or "").strip()
    if not oid:
        return ""
    _, download = _load_media()
    return download.get(oid, "")
