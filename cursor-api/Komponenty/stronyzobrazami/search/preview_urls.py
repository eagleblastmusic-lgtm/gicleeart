"""URL miniatury dla wyniku (lazy Smithsonian)."""

from __future__ import annotations

from .newfields_api import newfields_iiif_preview_url
from .smithsonian_media import smithsonian_image_url
from .types import ArtworkHit


def artwork_preview_url(hit: ArtworkHit) -> str:
    url = (hit.image_url or "").strip()
    if hit.source_id == "newfields" and url:
        return newfields_iiif_preview_url(url)
    if url:
        return url
    if hit.source_id == "smithsonian" and hit.raw_id:
        return smithsonian_image_url(hit.raw_id, large=False)
    return ""
