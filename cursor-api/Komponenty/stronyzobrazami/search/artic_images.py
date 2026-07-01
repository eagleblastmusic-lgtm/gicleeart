"""Miniatury Art Institute of Chicago (IIIF + Cloudflare)."""

from __future__ import annotations

ARTIC_IIIF_BASE = "https://www.artic.edu/iiif/2"
ARTIC_REFERER = "https://www.artic.edu/"


def artic_preview_url(image_id: str, *, width: int = 200) -> str:
    img_id = (image_id or "").strip()
    if not img_id:
        return ""
    w = max(100, min(843, int(width)))
    return f"{ARTIC_IIIF_BASE}/{img_id}/full/{w},/0/default.jpg"


def artic_fetch_headers(*, artwork_id: str | int | None = None) -> dict[str, str]:
    """Cloudflare na artic.edu wymaga Referer z ich domeny."""
    referer = ARTIC_REFERER
    if artwork_id is not None and str(artwork_id).strip().isdigit():
        referer = f"https://www.artic.edu/artworks/{int(artwork_id)}"
    return {"Referer": referer, "Accept": "image/*"}


def is_artic_image_url(url: str) -> bool:
    return "artic.edu/iiif/" in (url or "")
