from __future__ import annotations

import json
from pathlib import Path

import pytest

from . import homepage_variants
from . import prehero_integration
from .home_flow_phase_settings import (
    HERO_HOLD_ID,
    INTRO_HOLD_ID,
    PORTAL_ID,
    SOUND_ID,
    apply_phase_overrides,
    effective_phase_config,
    set_phase_config,
)
from .service import path_get, path_set


def _write_variant(root: Path) -> None:
    variant = root / "home1"
    variant.mkdir(parents=True)
    template: dict = {}
    path_set(
        template,
        ("sections", "slideshow_4LMfx7", "settings", "enable_audio"),
        True,
    )
    path_set(
        template,
        ("sections", "slideshow_4LMfx7", "settings", "audio_url"),
        "https://cdn.shopify.com/files/ambient.mp3",
    )
    path_set(
        template,
        ("sections", "slideshow_4LMfx7", "settings", "audio_volume"),
        31,
    )
    (variant / "index.json").write_text(json.dumps(template), encoding="utf-8")
    (variant / "settings.json").write_text(
        json.dumps(
            {
                "current": {
                    "prehero_enabled": True,
                    "prehero_reveal_screens": 2,
                    "prehero_hero_hold_screens": 1,
                    "prehero_intro_hold_screens": 1,
                }
            }
        ),
        encoding="utf-8",
    )


def _sound_values(*, enabled: bool, url: str = "") -> dict:
    return {
        "enabled": enabled,
        "question": "Włączyć ambient?",
        "toggle_label": "Dźwięk pracowni",
        "start_label": "Rozpocznij scenę",
        "audio_url": url,
        "volume": 42,
        "auto_muted_fraction": 50,
    }


def test_phase_overrides_merge_into_settings_template_and_export(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path)

    set_phase_config(
        "home1",
        PORTAL_ID,
        {"enabled": True, "screens": 3, "text": "Linia A\nLinia B"},
    )
    set_phase_config(
        "home1",
        INTRO_HOLD_ID,
        {"enabled": True, "screens": 2},
    )
    set_phase_config(
        "home1",
        SOUND_ID,
        _sound_values(
            enabled=True,
            url="https://cdn.shopify.com/files/custom.mp3",
        ),
    )

    template = json.loads((tmp_path / "home1" / "index.json").read_text(encoding="utf-8"))
    settings = json.loads((tmp_path / "home1" / "settings.json").read_text(encoding="utf-8"))
    merged_template, merged_settings = apply_phase_overrides(
        "home1", template, settings
    )
    current = merged_settings["current"]

    assert current["prehero_reveal_screens"] == 3
    assert current["prehero_copy_text"] == "Linia A\nLinia B"
    assert current["prehero_hero_hold_screens"] == 1
    assert current["prehero_intro_hold_screens"] == 2
    assert current["home_flow_sound_audio_url"].endswith("custom.mp3")
    assert current["home_flow_sound_volume"] == 42

    assert path_get(
        merged_template,
        ("sections", "slideshow_4LMfx7", "settings", "audio_url"),
    ).endswith("custom.mp3")

    exported = prehero_integration.export_prehero_config(merged_settings)
    assert exported["heroHoldVh"] == 100
    assert exported["introHoldVh"] == 200
    assert exported["soundConsentQuestion"] == "Włączyć ambient?"
    assert exported["soundConsentVolume"] == 42
    assert exported["soundConsentAutoMutedFraction"] == 0.5


def test_sound_phase_defaults_migrate_existing_hero_audio(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path)

    sound = effective_phase_config("home1", SOUND_ID)

    assert sound["enabled"] is True
    assert sound["audio_url"].endswith("ambient.mp3")
    assert sound["volume"] == 31


def test_zero_hero_hold_is_allowed_after_sound_consent_is_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path)

    set_phase_config("home1", SOUND_ID, _sound_values(enabled=False))
    set_phase_config("home1", HERO_HOLD_ID, {"enabled": False, "screens": 1})

    _template, settings = homepage_variants.load_variant_data("home1")
    assert settings["current"]["prehero_hero_hold_screens"] == 0
    assert prehero_integration.export_prehero_config(settings)["heroHoldVh"] == 0


def test_validation_blocks_sound_prompt_without_hero_hold(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path)

    set_phase_config("home1", SOUND_ID, _sound_values(enabled=False))
    set_phase_config("home1", HERO_HOLD_ID, {"enabled": False, "screens": 1})

    with pytest.raises(ValueError, match="wymaga aktywnego postoju Hero"):
        set_phase_config("home1", SOUND_ID, _sound_values(enabled=True))
