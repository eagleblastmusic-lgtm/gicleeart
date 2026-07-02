"""Kanoniczne URL-e storefront GicleeArt (linki wewnętrzne bez prefiksu rynku)."""

from __future__ import annotations

STORE_DOMAIN = "gicleeart.eu"
STORE_ORIGIN = f"https://{STORE_DOMAIN}"


def product_storefront_url(handle: str) -> str:
    """URL strony produktu, np. https://gicleeart.eu/products/{handle}."""
    h = (handle or "").strip().strip("/")
    if not h:
        return ""
    return f"{STORE_ORIGIN}/products/{h}"
