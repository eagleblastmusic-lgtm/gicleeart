from __future__ import annotations

import copy
import json
from pathlib import Path

from . import final_difference_settings
from . import home_features
from . import homepage_variants
from . import prehero_integration
from . import scroll_settings
from . import section_bg_effects_settings
from . import service
from . import studio_reveal_settings
from .home_scroll_mode import (
    SCROLL_MODE_LENIS,
    SCROLL_MODE_NATIVE,
    SCROLL_MODE_NATIVE_V2,
    SCROLL_MODE_LABELS,
    SCROLL_SETTING_KEY,
    apply_scroll_mode_to_live_theme,
    load_scroll_mode,
    normalize_scroll_mode,
    save_scroll_mode,
)


def _write_variant(root: Path, variant_id: str) -> None:
    variant = root / variant_id
    variant.mkdir(parents=True)
    (variant / "index.json").write_text("{}", encoding="utf-8")
    (variant / "settings.json").write_text(
        json.dumps({"current": {"prehero_enabled": True}}),
        encoding="utf-8",
    )


def test_scroll_mode_is_saved_per_homepage_variant(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path, "home1")
    _write_variant(tmp_path, "home2")

    save_scroll_mode("home1", SCROLL_MODE_LENIS)
    save_scroll_mode("home2", SCROLL_MODE_NATIVE_V2)

    assert load_scroll_mode("home1") == SCROLL_MODE_LENIS
    assert load_scroll_mode("home2") == SCROLL_MODE_NATIVE_V2


def test_scroll_selector_exposes_native_v2_as_separate_mode() -> None:
    assert SCROLL_MODE_LABELS[SCROLL_MODE_NATIVE] == "Zwykły — natywny"
    assert SCROLL_MODE_LABELS[SCROLL_MODE_NATIVE_V2] == "Zwykły v2 — filmowy"
    assert SCROLL_MODE_LABELS[SCROLL_MODE_LENIS] == "Lenis — płynny"


def test_scroll_mode_bridge_reaches_settings_and_public_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path, "home1")
    save_scroll_mode("home1", SCROLL_MODE_NATIVE_V2)

    _template, settings = homepage_variants.load_variant_data("home1")

    assert settings["current"][SCROLL_SETTING_KEY] == SCROLL_MODE_NATIVE_V2
    exported = prehero_integration.export_prehero_config(settings)
    assert exported["smoothScrollMode"] == SCROLL_MODE_NATIVE_V2


def test_live_apply_uses_current_theme_instead_of_variant_snapshot(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path, "home1")

    live_template = {"sections": {"current-homepage": {"type": "custom"}}}
    live_settings = {"current": {"current_homepage_marker": "keep-me"}}
    saved_settings: list[dict] = []
    generated: dict = {}

    monkeypatch.setattr(service, "load_index_template", lambda: copy.deepcopy(live_template))
    monkeypatch.setattr(service, "load_theme_settings", lambda: copy.deepcopy(live_settings))
    monkeypatch.setattr(
        service,
        "save_theme_settings",
        lambda value: saved_settings.append(copy.deepcopy(value)),
    )
    monkeypatch.setattr(service, "mobile_hero_path", lambda: tmp_path / "missing.webp")
    monkeypatch.setattr(homepage_variants, "variant_uses_home_stack", lambda _variant: True)
    monkeypatch.setattr(scroll_settings, "load_scroll_config", lambda _variant: {"scroll": 1})
    monkeypatch.setattr(
        final_difference_settings,
        "load_final_difference_config",
        lambda _variant: {"difference": 1},
    )
    monkeypatch.setattr(
        studio_reveal_settings,
        "load_studio_reveal_config",
        lambda _variant: {"studio": 1},
    )
    monkeypatch.setattr(
        section_bg_effects_settings,
        "load_section_bg_effects_config",
        lambda _variant: {"background": 1},
    )

    def capture_assets(template, **kwargs) -> None:
        generated["template"] = copy.deepcopy(template)
        generated["kwargs"] = copy.deepcopy(kwargs)

    monkeypatch.setattr(home_features, "write_home_assets", capture_assets)

    applied = apply_scroll_mode_to_live_theme("home1", SCROLL_MODE_NATIVE_V2)

    assert applied == SCROLL_MODE_NATIVE_V2
    assert saved_settings[-1]["current"]["current_homepage_marker"] == "keep-me"
    assert saved_settings[-1]["current"][SCROLL_SETTING_KEY] == SCROLL_MODE_NATIVE_V2
    assert generated["template"] == live_template
    assert "current-homepage" in generated["template"]["sections"]
    assert load_scroll_mode("home1") == SCROLL_MODE_NATIVE_V2


def test_unknown_scroll_mode_falls_back_to_native() -> None:
    assert normalize_scroll_mode("something-else") == SCROLL_MODE_NATIVE
    assert normalize_scroll_mode(None) == SCROLL_MODE_NATIVE
    assert normalize_scroll_mode(SCROLL_MODE_NATIVE) == SCROLL_MODE_NATIVE
    assert normalize_scroll_mode(SCROLL_MODE_NATIVE_V2) == SCROLL_MODE_NATIVE_V2
    assert normalize_scroll_mode(SCROLL_MODE_LENIS) == SCROLL_MODE_LENIS
