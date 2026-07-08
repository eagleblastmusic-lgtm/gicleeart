"""Testy konfiguracji efektów sekcji «Giclée Art — intro» (studio_reveal_settings.py)."""

from __future__ import annotations

import json

import pytest

from Komponenty.stronaglowna import studio_reveal_settings
from Komponenty.stronaglowna.studio_reveal_settings import (
    GRADIENT_PRESETS,
    STUDIO_REVEAL_DEFAULTS,
    STUDIO_REVEAL_PRESETS,
    apply_studio_reveal_preset,
    export_studio_reveal_config,
    load_studio_reveal_config,
    normalize_studio_reveal_config,
    save_studio_reveal_config,
    validate_studio_reveal_config,
)


@pytest.fixture
def variant_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(studio_reveal_settings, "_data_dir", lambda: tmp_path)
    return tmp_path / "variants" / "home9"


def test_defaults_are_valid():
    assert validate_studio_reveal_config(dict(STUDIO_REVEAL_DEFAULTS)) == []


def test_load_missing_file_returns_defaults(variant_dir):
    cfg = load_studio_reveal_config("home9")
    assert cfg == STUDIO_REVEAL_DEFAULTS
    assert cfg is not STUDIO_REVEAL_DEFAULTS


def test_save_and_load_roundtrip(variant_dir):
    cfg = dict(
        STUDIO_REVEAL_DEFAULTS,
        gradientPreset="menu_wide",
        parallaxMaxX=24,
        enabled=False,
    )
    saved = save_studio_reveal_config("home9", cfg)
    assert saved["gradientPreset"] == "menu_wide"
    assert saved["enabled"] is False
    on_disk = json.loads((variant_dir / "studio-reveal.json").read_text(encoding="utf-8"))
    assert on_disk["parallaxMaxX"] == 24
    assert load_studio_reveal_config("home9") == saved


@pytest.mark.parametrize("preset_name", list(STUDIO_REVEAL_PRESETS.keys()))
def test_presets_validate(preset_name):
    cfg = apply_studio_reveal_preset(preset_name)
    assert validate_studio_reveal_config(cfg) == []


def test_export_includes_easing_bezier_and_parallax_scale():
    cfg = export_studio_reveal_config({"easing": "soft", "parallaxOverscan": 108})
    assert cfg["easingBezier"] == "0.25, 1, 0.5, 1"
    assert cfg["parallaxOverscan"] == 1.08


def test_invalid_gradient_falls_back_to_editorial():
    cfg = normalize_studio_reveal_config({"gradientPreset": "unknown"})
    assert cfg["gradientPreset"] == "editorial"
    assert cfg["gradientPreset"] in GRADIENT_PRESETS


def test_write_home_assets_embeds_studio_reveal_config(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")

    cfg = dict(STUDIO_REVEAL_DEFAULTS, gradientPreset="radial_spot", parallaxMaxX=22)
    home_features.write_home_assets({}, stack_enabled=False, studio_reveal_config=cfg)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_STUDIO_REVEAL_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload["gradientPreset"] == "radial_spot"
    assert payload["parallaxMaxX"] == 22
    assert payload["easingBezier"] == "0.16, 1, 0.3, 1"
