"""Testy efektów per sekcja stron menu (page_section_effects_settings.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.page_section_effects_settings import (
    PAGE_IMAGE_EFFECT_DEFAULTS,
    effects_asset_basename,
    export_image_effects_config,
    export_section_effects_for_front,
    load_section_effects_config,
    normalize_section_effects_entry,
    save_image_effects_for_section,
    save_text_effects_for_section,
    write_page_section_effects_asset,
    zone_has_image_effects,
    zone_has_text_effects,
)
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty.stronaglowna import studio_reveal_settings
from Komponenty.stronaglowna.studio_reveal_settings import STUDIO_REVEAL_DEFAULTS


@pytest.fixture
def page_config(tmp_path: Path) -> PageEditorConfig:
    component_dir = tmp_path / "gicleeframe"
    component_dir.mkdir(parents=True)
    return PageEditorConfig(
        component_id="gicleeframe",
        component_dir=component_dir,
        app_title="Giclée Frame — test",
        intro_title="Giclée Frame",
        intro_body="test",
        template_rel="templates/page.giclee-frame.json",
        preview_path="/pages/giclee-frame",
        variant_id_prefix="gf",
        zones=(),
    )


def test_effects_asset_basename():
    cfg = PageEditorConfig(
        component_id="gicleeframe",
        component_dir=Path("."),
        app_title="x",
        intro_title="x",
        intro_body="x",
        template_rel="templates/page.giclee-frame.json",
        preview_path="/pages/giclee-frame",
        variant_id_prefix="gf",
        zones=(),
    )
    assert effects_asset_basename(cfg) == "giclee-frame-section-effects.js"


def test_zone_has_text_and_image_effects():
    text_zone = TemplateZone(
        zone_id="passe",
        section_key="section_ABC",
        label="Archiwalne passe-partout",
        description="test",
        fields=(
            TemplateField("heading_jumbo", "Nagłówek", "text"),
            TemplateField("body", "Treść", "body"),
            TemplateField("image", "Grafika", "shopify_image"),
        ),
    )
    sep_zone = TemplateZone(
        zone_id="sep1",
        section_key="section_SEP",
        label="Separator",
        description="",
        fields=(),
        settings_only=True,
    )
    assert zone_has_text_effects(text_zone) is True
    assert zone_has_image_effects(text_zone) is True
    assert zone_has_text_effects(sep_zone) is False
    assert zone_has_image_effects(sep_zone) is False


def test_save_text_and_image_roundtrip(page_config: PageEditorConfig):
    text_cfg = dict(STUDIO_REVEAL_DEFAULTS, enabled=True, copyHoverScale=1.03)
    image_cfg = dict(PAGE_IMAGE_EFFECT_DEFAULTS, parallaxEnabled=True, imageHoverScale=1.04)
    save_text_effects_for_section(page_config, "gf1", "section_ABC", text_cfg)
    save_image_effects_for_section(page_config, "gf1", "section_ABC", image_cfg)

    loaded = load_section_effects_config(page_config, "gf1")
    assert loaded["section_ABC"]["text"]["copyHoverScale"] == 1.03
    assert loaded["section_ABC"]["image"]["parallaxEnabled"] is True
    assert loaded["section_ABC"]["image"]["imageHoverScale"] == 1.04


def test_export_section_effects_for_front_skips_disabled(page_config: PageEditorConfig):
    save_text_effects_for_section(
        page_config,
        "gf1",
        "section_ON",
        dict(STUDIO_REVEAL_DEFAULTS, enabled=True),
    )
    save_text_effects_for_section(
        page_config,
        "gf1",
        "section_OFF",
        dict(STUDIO_REVEAL_DEFAULTS, enabled=False),
    )
    exported = export_section_effects_for_front(page_config, "gf1")
    assert "section_ON" in exported
    assert "section_OFF" not in exported
    assert "text" in exported["section_ON"]


def test_export_image_effects_config():
    out = export_image_effects_config({"parallaxEnabled": True, "parallaxOverscan": 108})
    assert out["enabled"] is True
    assert out["parallaxOverscan"] == 1.08


def test_normalize_section_effects_entry():
    raw = {
        "section_X": {
            "text": {"enabled": True, "gradientPreset": "unknown"},
            "image": {"parallaxEnabled": True, "imageHoverScale": 9},
        }
    }
    out = normalize_section_effects_entry(raw)
    assert out["section_X"]["text"]["enabled"] is True
    assert out["section_X"]["image"]["imageHoverScale"] == 1.08


def test_write_page_section_effects_asset(page_config: PageEditorConfig, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(studio_reveal_settings, "_data_dir", lambda: tmp_path)
    theme = tmp_path / "theme"
    theme.mkdir()
    monkeypatch.setattr(
        "Komponenty._shared.theme_page_editor.page_section_effects_settings.theme_root",
        lambda: theme,
    )

    save_text_effects_for_section(
        page_config,
        "gf1",
        "section_ABC",
        dict(STUDIO_REVEAL_DEFAULTS, enabled=True),
    )
    path = write_page_section_effects_asset(page_config, "gf1")
    assert path == theme / "assets" / "giclee-frame-section-effects.js"
    content = path.read_text(encoding="utf-8")
    assert "GICLEE_PAGE_SECTION_EFFECTS" in content
    payload = json.loads(content.split("=", 1)[1].strip().rstrip(";"))
    assert payload["page"] == "giclee-frame"
    assert "section_ABC" in payload["sections"]
