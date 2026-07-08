"""Testy section-bg-effects (gradient BIO + parallax per sekcja homepage)."""

from __future__ import annotations

import json

import pytest

from Komponenty.stronaglowna import section_bg_effects_settings as mod
from Komponenty.stronaglowna.section_bg_effects_settings import (
    SECTION_BG_EFFECTS_DEFAULTS,
    SECTION_BG_EFFECTS_PRESETS,
    apply_section_bg_effects_preset,
    export_section_bg_effects_config,
    load_section_bg_effects_for_hook,
    save_section_bg_effects_for_hook,
)


@pytest.fixture
def variant_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_data_dir", lambda: tmp_path)
    return tmp_path / "variants" / "home9"


def test_save_hook_roundtrip(variant_dir):
    cfg = apply_section_bg_effects_preset("Gradient editorial (BIO)")
    all_saved = save_section_bg_effects_for_hook("home9", "restoration", cfg)
    assert all_saved["restoration"]["gradientPreset"] == "editorial"
    assert load_section_bg_effects_for_hook("home9", "restoration")["enabled"] is True


@pytest.mark.parametrize("preset_name", list(SECTION_BG_EFFECTS_PRESETS.keys()))
def test_presets_normalize(preset_name):
    cfg = apply_section_bg_effects_preset(preset_name)
    assert cfg["gradientPreset"] in mod.GRADIENT_PRESETS


def test_export_parallax_overscan_scale():
    exported = export_section_bg_effects_config(
        {"see-difference": dict(SECTION_BG_EFFECTS_DEFAULTS, parallaxOverscan=108)}
    )
    assert exported["see-difference"]["parallaxOverscan"] == 1.08


def test_write_home_assets_embeds_section_bg_effects(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")

    cfg = {"potential": apply_section_bg_effects_preset("Gradient + parallax")}
    home_features.write_home_assets({}, stack_enabled=False, section_bg_effects_config=cfg)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload["potential"]["parallaxEnabled"] is True
