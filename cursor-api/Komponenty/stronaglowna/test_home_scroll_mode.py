from __future__ import annotations

import json
from pathlib import Path

from . import homepage_variants
from . import prehero_integration
from .home_scroll_mode import (
    SCROLL_MODE_LENIS,
    SCROLL_MODE_NATIVE,
    SCROLL_SETTING_KEY,
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

    save_scroll_mode("home1", SCROLL_MODE_NATIVE)

    assert load_scroll_mode("home1") == SCROLL_MODE_NATIVE
    assert load_scroll_mode("home2") == SCROLL_MODE_LENIS


def test_scroll_mode_bridge_reaches_settings_and_public_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(homepage_variants, "VARIANTS_ROOT", tmp_path)
    _write_variant(tmp_path, "home1")
    save_scroll_mode("home1", SCROLL_MODE_NATIVE)

    _template, settings = homepage_variants.load_variant_data("home1")

    assert settings["current"][SCROLL_SETTING_KEY] == SCROLL_MODE_NATIVE
    exported = prehero_integration.export_prehero_config(settings)
    assert exported["smoothScrollMode"] == SCROLL_MODE_NATIVE


def test_unknown_scroll_mode_falls_back_to_lenis() -> None:
    assert normalize_scroll_mode("something-else") == SCROLL_MODE_LENIS
    assert normalize_scroll_mode(None) == SCROLL_MODE_LENIS
