"""Testy konfiguracji homepage section-scroll (Komponenty/stronaglowna/scroll_settings.py)."""

from __future__ import annotations

import json

import pytest

from Komponenty.stronaglowna import scroll_settings
from Komponenty.stronaglowna.scroll_settings import (
    SCROLL_DEFAULTS,
    SCROLL_PRESETS,
    apply_scroll_preset,
    load_scroll_config,
    normalize_scroll_config,
    save_scroll_config,
    validate_scroll_config,
)


@pytest.fixture
def variant_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(scroll_settings, "_data_dir", lambda: tmp_path)
    return tmp_path / "variants" / "home9"


def _write_disabled_prehero_settings(theme_root) -> None:
    config_dir = theme_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "settings_data.json").write_text(
        json.dumps(
            {
                "current": {
                    "prehero_enabled": False,
                }
            }
        ),
        encoding="utf-8",
    )


def test_defaults_are_valid():
    assert validate_scroll_config(dict(SCROLL_DEFAULTS)) == []


def test_load_missing_file_returns_defaults(variant_dir):
    cfg = load_scroll_config("home9")
    assert cfg == SCROLL_DEFAULTS
    assert cfg is not SCROLL_DEFAULTS


def test_load_corrupted_file_returns_defaults(variant_dir):
    variant_dir.mkdir(parents=True)
    (variant_dir / "scroll.json").write_text("{nie-json", encoding="utf-8")
    assert load_scroll_config("home9") == SCROLL_DEFAULTS


def test_normalize_merges_partial_and_ignores_unknown():
    cfg = normalize_scroll_config({"minDuration": 800, "nieznane_pole": 1, "debug": 1})
    assert cfg["minDuration"] == 800
    assert cfg["debug"] is True
    assert cfg["maxDuration"] == SCROLL_DEFAULTS["maxDuration"]
    assert "nieznane_pole" not in cfg


def test_normalize_coerces_header_offset():
    assert normalize_scroll_config({"headerOffset": None})["headerOffset"] is None
    assert normalize_scroll_config({"headerOffset": "48"})["headerOffset"] == 48


def test_validate_min_greater_than_max():
    cfg = dict(SCROLL_DEFAULTS, minDuration=1200, maxDuration=700)
    errors = validate_scroll_config(cfg)
    assert any("minDuration" in e and "maxDuration" in e for e in errors)


def test_validate_out_of_range_threshold():
    cfg = dict(SCROLL_DEFAULTS, wheelThreshold=10_000)
    assert validate_scroll_config(cfg)


def test_validate_bad_mobile_mode():
    cfg = dict(SCROLL_DEFAULTS, mobileMode="turbo")
    assert any("mobileMode" in e for e in validate_scroll_config(cfg))


def test_validate_bad_reduced_motion_mode():
    cfg = dict(SCROLL_DEFAULTS, reducedMotionMode="bounce")
    assert any("reducedMotionMode" in e for e in validate_scroll_config(cfg))


def test_save_and_load_roundtrip(variant_dir):
    cfg = dict(SCROLL_DEFAULTS, minDuration=700, mobileMode="soft", enabled=False)
    saved = save_scroll_config("home9", cfg)
    assert saved["minDuration"] == 700
    assert saved["enabled"] is False

    on_disk = json.loads((variant_dir / "scroll.json").read_text(encoding="utf-8"))
    assert on_disk["mobileMode"] == "soft"
    assert load_scroll_config("home9") == saved


def test_save_rejects_invalid(variant_dir):
    cfg = dict(SCROLL_DEFAULTS, minDuration=3000, maxDuration=500)
    with pytest.raises(ValueError):
        save_scroll_config("home9", cfg)
    assert not (variant_dir / "scroll.json").exists()


def test_normalize_motion_dynamics():
    assert normalize_scroll_config({"motionDynamics": "72"})["motionDynamics"] == 72
    assert normalize_scroll_config({})["motionDynamics"] == SCROLL_DEFAULTS["motionDynamics"]


def test_validate_motion_dynamics_out_of_range():
    cfg = dict(SCROLL_DEFAULTS, motionDynamics=101)
    assert any("motionDynamics" in e for e in validate_scroll_config(cfg))


@pytest.mark.parametrize("preset_name", list(SCROLL_PRESETS.keys()))
def test_scroll_presets_validate(preset_name):
    cfg = apply_scroll_preset(preset_name)
    assert validate_scroll_config(cfg) == []


def test_apply_scroll_preset_kinowy():
    cfg = apply_scroll_preset("Kinowy")
    assert cfg["minDuration"] == 950
    assert cfg["maxDuration"] == 1600
    assert cfg["motionDynamics"] == 15
    assert cfg["headingSettle"] is True


def test_apply_scroll_preset_dynamic_premium():
    cfg = apply_scroll_preset("Dynamiczny premium")
    assert cfg["motionDynamics"] == 85
    assert cfg["wheelThreshold"] == 30


def test_apply_scroll_preset_gpt():
    cfg = apply_scroll_preset("GPT")
    assert cfg["minDuration"] == 650
    assert cfg["maxDuration"] == 1050
    assert cfg["wheelThreshold"] == 60
    assert cfg["motionDynamics"] == 32
    assert cfg["mobileMode"] == "native"
    assert cfg["reducedMotionMode"] == "instant"


def test_write_home_assets_embeds_motion_dynamics(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")
    _write_disabled_prehero_settings(tmp_path)

    cfg = dict(SCROLL_DEFAULTS, enabled=False, minDuration=900, motionDynamics=85)
    home_features.write_home_assets({}, stack_enabled=True, scroll_config=cfg)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_SCROLL_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload["enabled"] is False
    assert payload["minDuration"] == 900
    assert payload["motionDynamics"] == 85
    assert payload["headerOffset"] is None


def test_write_home_assets_embeds_scroll_config(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")
    _write_disabled_prehero_settings(tmp_path)

    cfg = dict(SCROLL_DEFAULTS, enabled=False, minDuration=900)
    home_features.write_home_assets({}, stack_enabled=True, scroll_config=cfg)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_SCROLL_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload["enabled"] is False
    assert payload["minDuration"] == 900
    assert payload["headerOffset"] is None


def test_write_home_assets_without_config_uses_defaults(tmp_path, monkeypatch):
    from Komponenty.stronaglowna import home_features, service

    monkeypatch.setattr(service, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "theme_root", lambda: tmp_path)
    monkeypatch.setattr(home_features, "mobile_hero_path", lambda: tmp_path / "assets" / "MALE_ORG.webp")

    home_features.write_home_assets({}, stack_enabled=False)

    text = (tmp_path / "assets" / "giclee-home-sections.js").read_text(encoding="utf-8")
    line = next(l for l in text.splitlines() if l.startswith("window.GICLEE_HOME_SCROLL_CONFIG"))
    payload = json.loads(line.split("=", 1)[1].strip().rstrip(";"))
    assert payload == json.loads(json.dumps(SCROLL_DEFAULTS))
