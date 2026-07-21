"""Warianty grafiki podglądu w submenu Katalog."""

from __future__ import annotations

PREVIEW_GRAPHICS_VARIANT_FIELD_ID = "preview_graphics_variant"
PREVIEW_GRAPHICS_VARIANT_FIELD_LABEL = "Grafika"
DEFAULT_PREVIEW_GRAPHICS_VARIANT = "v1"

PREVIEW_GRAPHICS_VARIANT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("v1", "V1 — klasyczna, ciemniejsza"),
    ("v2", "V2 — jaśniejsza, lokalny gradient"),
)

PREVIEW_GRAPHICS_VARIANT_LABEL_BY_ID = dict(PREVIEW_GRAPHICS_VARIANT_OPTIONS)
PREVIEW_GRAPHICS_VARIANT_ID_BY_LABEL = {
    label: variant_id for variant_id, label in PREVIEW_GRAPHICS_VARIANT_OPTIONS
}


def normalize_preview_graphics_variant(value: object) -> str:
    variant_id = str(value or "").strip().lower()
    if variant_id in PREVIEW_GRAPHICS_VARIANT_LABEL_BY_ID:
        return variant_id
    return DEFAULT_PREVIEW_GRAPHICS_VARIANT


__all__ = [
    "DEFAULT_PREVIEW_GRAPHICS_VARIANT",
    "PREVIEW_GRAPHICS_VARIANT_FIELD_ID",
    "PREVIEW_GRAPHICS_VARIANT_FIELD_LABEL",
    "PREVIEW_GRAPHICS_VARIANT_ID_BY_LABEL",
    "PREVIEW_GRAPHICS_VARIANT_LABEL_BY_ID",
    "PREVIEW_GRAPHICS_VARIANT_OPTIONS",
    "normalize_preview_graphics_variant",
]
