"""Testy wariantów Grafika V1/V2 w Submenu katalog."""

from __future__ import annotations

import json
from pathlib import Path

from Komponenty.submenukatalog.graphics import (
    DEFAULT_PREVIEW_GRAPHICS_VARIANT,
    PREVIEW_GRAPHICS_VARIANT_FIELD_ID,
    PREVIEW_GRAPHICS_VARIANT_OPTIONS,
    normalize_preview_graphics_variant,
)
from Komponenty.submenukatalog.registry import PAGE_ZONES

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "assets" / "giclee-catalog-submenu-config.json"
JS = ROOT / "assets" / "giclee-catalog-panel.js"
CSS = ROOT / "assets" / "giclee-catalog-panel.css"


def test_graphics_catalog_is_readonly_v1_v2_contract() -> None:
    assert PREVIEW_GRAPHICS_VARIANT_OPTIONS == (
        ("v1", "V1 — klasyczna, ciemniejsza"),
        ("v2", "V2 — jaśniejsza, lokalny gradient"),
    )
    assert normalize_preview_graphics_variant(None) == DEFAULT_PREVIEW_GRAPHICS_VARIANT
    assert normalize_preview_graphics_variant(" V2 ") == "v2"
    assert normalize_preview_graphics_variant("unknown") == "v1"


def test_appearance_zone_exposes_graphics_before_dimensions() -> None:
    zone = next(item for item in PAGE_ZONES if item.zone_id == "appearance")
    ids = [field.field_id for field in zone.fields]
    assert ids == [PREVIEW_GRAPHICS_VARIANT_FIELD_ID, "preview_width_px", "panel_max_height_vh"]
    assert zone.fields[0].path == ("appearance", PREVIEW_GRAPHICS_VARIANT_FIELD_ID)


def test_deploy_config_uses_supported_variant_without_changing_code_default() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    supported = {variant_id for variant_id, _label in PREVIEW_GRAPHICS_VARIANT_OPTIONS}
    assert payload["appearance"]["preview_graphics_variant"] in supported
    assert DEFAULT_PREVIEW_GRAPHICS_VARIANT == "v1"


def test_frontend_applies_data_attribute_and_v2_css_only() -> None:
    js = JS.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert "preview_graphics_variant: 'v1'" in js
    assert "data-preview-graphics-variant" in js
    assert "CATALOG_PREVIEW_GRAPHICS_VARIANT" in js
    assert "brightness(0.5) saturate(0.75)" in css
    assert "#giclee-catalog-panel[data-preview-graphics-variant='v2'] #giclee-preview-img" in css
    assert "brightness(0.68) saturate(0.88) contrast(1.02)" in css
    assert "#giclee-catalog-panel[data-preview-graphics-variant='v2'] #giclee-preview-info" in css
