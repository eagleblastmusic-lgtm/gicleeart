"""Testy konfiguracji animacji «Zobacz różnicę» (final_difference_settings.py)."""

from __future__ import annotations

import json

import pytest

from Komponenty.stronaglowna import final_difference_settings
from Komponenty.stronaglowna.final_difference_settings import (
    FINAL_DIFFERENCE_DEFAULTS,
    FINAL_DIFFERENCE_PRESETS,
    apply_final_difference_preset,
    export_final_difference_config,
    load_final_difference_config,
    normalize_final_difference_config,
    save_final_difference_config,
    validate_final_difference_config,
)


@pytest.fixture
def variant_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(final_difference_settings, "_data_dir", lambda: tmp_path)
    return tmp_path / "variants" / "home9"


def test_defaults_are_valid():
    assert validate_final_difference_config(dict(FINAL_DIFFERENCE_DEFAULTS)) == []


def test_load_missing_file_returns_defaults(variant_dir):
    cfg = load_final_difference_config("home9")
    assert cfg == FINAL_DIFFERENCE_DEFAULTS
    assert cfg is not FINAL_DIFFERENCE_DEFAULTS


def test_save_and_load_roundtrip(variant_dir):
    cfg = dict(FINAL_DIFFERENCE_DEFAULTS, copyScale=1.07, durationMs=900, enabled=False)
    saved = save_final_difference_config("home9", cfg)
    assert saved["copyScale"] == 1.07
    assert saved["enabled"] is False
    on_disk = json.loads((variant_dir / "final-difference.json").read_text(encoding="utf-8"))
    assert on_disk["durationMs"] == 900
    assert load_final_difference_config("home9") == saved


def test_validate_copy_scale_out_of_range():
    cfg = dict(FINAL_DIFFERENCE_DEFAULTS, copyScale=1.5)
    assert any("copyScale" in e for e in validate_final_difference_config(cfg))


@pytest.mark.parametrize("preset_name", list(FINAL_DIFFERENCE_PRESETS.keys()))
def test_presets_validate(preset_name):
    cfg = apply_final_difference_preset(preset_name)
    assert validate_final_difference_config(cfg) == []


def test_export_includes_easing_bezier():
    cfg = export_final_difference_config({"easing": "soft"})
    assert cfg["easingBezier"] == "0.25, 1, 0.5, 1"


def test_reverse_behavior_normalizes_to_bool():
    cfg = normalize_final_difference_config({"reverseBehavior": 1})
    assert cfg["reverseBehavior"] is True
    exported = export_final_difference_config(cfg)
    assert exported["reverseBehavior"] is True


def test_write_home_assets_embeds_final_difference_config(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")

    cfg = dict(FINAL_DIFFERENCE_DEFAULTS, copyScale=1.07, mediaOffsetX=30)
    home_features.write_home_assets({}, stack_enabled=False, final_difference_config=cfg)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_FINAL_DIFFERENCE_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload["copyScale"] == 1.07
    assert payload["mediaOffsetX"] == 30
    assert payload["easingBezier"] == "0.16, 1, 0.3, 1"
