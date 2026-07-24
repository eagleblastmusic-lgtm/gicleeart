"""Kontrakt globalnych stylów przycisków GicleeApp → Style."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.style import service


ROOT = Path(__file__).resolve().parents[2]


def _json_with_optional_header(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("/*"):
        raw = raw[raw.find("*/") + 2 :]
    return json.loads(raw)


def _settings_fixture(style: str = "basic") -> bytes:
    return (
        "/* generated settings */\n"
        "{\n"
        '  "current": {\n'
        '    "logo": "keep-me",\n'
        f'    "giclee_button_style": "{style}",\n'
        '    "primary_button_border_width": 0\n'
        "  },\n"
        '  "presets": {"Keep": {"other": true}}\n'
        "}\n"
    ).encode("utf-8")


def test_theme_registers_all_button_styles() -> None:
    schema = _json_with_optional_header(ROOT / "config" / "settings_schema.json")
    settings = _json_with_optional_header(ROOT / "config" / "settings_data.json")
    buttons = next(section for section in schema if section["name"] == "t:names.buttons")
    field = next(item for item in buttons["settings"] if item.get("id") == service.BUTTON_STYLE_KEY)

    assert field["default"] == "basic"
    assert {option["value"]: option["label"] for option in field["options"]} == {
        "basic": "Podstawowy — obecny wygląd",
        "nocturne": "Nocturne — nocna galeria",
        "frosted": "Frosted — szkło i miękki glow",
        "light-in-motion": "Light in Motion — złote światło w ruchu",
    }
    assert settings["current"][service.BUTTON_STYLE_KEY] in {
        "basic",
        "nocturne",
        "frosted",
        "light-in-motion",
    }


@pytest.mark.parametrize("layout_name", ["theme.liquid", "password.liquid"])
def test_layouts_expose_global_style_and_load_the_asset(layout_name: str) -> None:
    source = (ROOT / "layout" / layout_name).read_text(encoding="utf-8")

    assert 'data-giclee-button-style="{{ settings.giclee_button_style' in source
    assert "giclee-button-styles.css" in source
    assert "Montserrat:wght@500" in source
    assert "settings.giclee_button_style == 'frosted'" in source
    assert "settings.giclee_button_style == 'light-in-motion'" in source


def test_nocturne_css_matches_reference_and_has_bounded_scope() -> None:
    css = (ROOT / "assets" / "giclee-button-styles.css").read_text(encoding="utf-8")

    for color in ("#e6e6e6", "#b0b3b8", "#6b7077", "#2a2d33", "#0b0d10"):
        assert color in css
    assert "data-giclee-button-style='nocturne'" in css
    assert "letter-spacing: 0.14em" in css
    assert "min-block-size: 44px" in css
    assert ".add-to-cart-button" not in css  # Jest objęty przez bezpieczną klasę bazową .button.
    assert ".product-media-container__zoom-button" in css
    assert ".giclee-random-artwork__cta--primary" in css
    assert ".giclee-artist-showcase__cta" in css
    assert ".button:not(" in css
    assert ".header-actions__action" in css
    assert ".menu-drawer__back-button" in css
    assert ".localization-selector" in css
    assert ".variant-option__button-label:not(.variant-option__button-label--has-swatch)" in css
    assert ":has(:checked)" in css
    assert ":has(:focus-visible)" in css
    assert ":has([data-option-available='false'])" in css


def test_frosted_css_matches_glassmorphism_reference_and_has_full_states() -> None:
    css = (ROOT / "assets" / "giclee-button-styles.css").read_text(encoding="utf-8")

    for color in ("#eef8ff", "#bfd2df", "#b9e8fa", "#7fe4f2", "#d5a8ee", "#e8a6de"):
        assert color in css
    assert "data-giclee-button-style='frosted'" in css
    assert "backdrop-filter: blur(14px) saturate(1.25)" in css
    assert "border-radius: 16px" in css
    assert "letter-spacing: 0.14em" in css
    assert ":hover:not(:disabled, [aria-disabled='true'])" in css
    assert ":active:not(:disabled, [aria-disabled='true'])" in css
    assert ":focus-visible" in css
    assert ":is(:disabled, [aria-disabled='true'])" in css
    assert "[aria-busy='true']" in css
    assert ".product-media-container__zoom-button" in css
    assert ".giclee-random-artwork__cta--primary" in css
    assert ".variant-option__button-label:not(.variant-option__button-label--has-swatch)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_light_in_motion_css_matches_reference_and_has_full_states() -> None:
    css = (ROOT / "assets" / "giclee-button-styles.css").read_text(encoding="utf-8")

    for color in ("#f1e5d2", "#e6c38d", "#d3a866", "#f4c982", "#9c7040", "#070a0c"):
        assert color in css
    assert "data-giclee-button-style='light-in-motion'" in css
    assert "border-radius: 999px" in css
    assert "letter-spacing: 0.16em" in css
    assert "giclee-light-in-motion-flow" in css
    assert ":hover:not(:disabled, [aria-disabled='true'])" in css
    assert ":active:not(:disabled, [aria-disabled='true'])" in css
    assert ":focus-visible" in css
    assert ":is(:disabled, [aria-disabled='true'])" in css
    assert "[aria-busy='true']" in css
    assert ".product-media-container__zoom-button" in css
    assert ".giclee-random-artwork__cta--primary" in css
    assert ".variant-option__button-label:not(.variant-option__button-label--has-swatch)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css


def test_premium_button_styles_keep_skip_link_out_of_document_flow() -> None:
    css = (ROOT / "assets" / "giclee-button-styles.css").read_text(encoding="utf-8")

    for style in ("nocturne", "frosted", "light-in-motion"):
        selector = (
            f"html[data-giclee-button-style='{style}'] "
            ".skip-to-content-link.button-secondary"
        )
        assert selector in css
    assert "position: absolute;" in css
    assert "left: -99999px;" in css
    assert ".skip-to-content-link.button-secondary:is(:focus, :focus-visible)" in css
    assert "left: var(--margin-lg);" in css


def test_style_component_describes_changed_and_excluded_buttons() -> None:
    source = (ROOT / "cursor-api" / "Komponenty" / "style" / "view.py").read_text(
        encoding="utf-8"
    )

    for text in (
        "Główne CTA",
        "Drugorzędne",
        "Płatności",
        "CTA Giclée Art",
        "Warianty produktu",
        "koloru, rozmiaru, rodzaju drewna i passe-partout",
        "Kontrolki ikonowe",
        "Nie zmienia:",
        "próbek kolorów (swatch)",
    ):
        assert text in source
    assert "Podstawowy" in source
    assert "Nocturne" in source
    assert "Frosted" in source
    assert "Glassmorphism" in source
    assert "Light in Motion" in source
    assert "kinetyczne linie" in source


@pytest.mark.parametrize("target_style", ["nocturne", "frosted", "light-in-motion"])
def test_button_style_writer_changes_only_the_bounded_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_style: str,
) -> None:
    settings_path = tmp_path / "theme" / "config" / "settings_data.json"
    settings_path.parent.mkdir(parents=True)
    before = _settings_fixture()
    settings_path.write_bytes(before)
    monkeypatch.setattr(service, "_THEME_SETTINGS_PATH_OVERRIDE", settings_path)
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "app-local"))

    plan = service.build_button_style_plan(target_style)

    assert plan.changed is True
    assert '-    "giclee_button_style": "basic",' in plan.diff_text
    assert f'+    "giclee_button_style": "{target_style}",' in plan.diff_text
    removed = [
        line for line in plan.diff_text.splitlines() if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line for line in plan.diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")
    ]
    assert removed == ['-    "giclee_button_style": "basic",']
    assert added == [f'+    "giclee_button_style": "{target_style}",']

    result = service.apply_button_style_plan(
        plan,
        confirmation=service.THEME_APPLY_CONFIRMATION,
    )

    assert result.changed is True
    assert result.backup_path is not None
    assert result.backup_path.read_bytes() == before
    assert service.load_button_style() == target_style
    saved = _json_with_optional_header(settings_path)
    assert saved["current"]["logo"] == "keep-me"
    assert saved["presets"] == {"Keep": {"other": True}}


def test_button_style_renderer_preserves_windows_line_endings() -> None:
    raw = _settings_fixture().decode("utf-8").replace("\n", "\r\n")

    rendered = service._render_settings(raw, "light-in-motion")

    assert rendered.count('"giclee_button_style"') == 1
    assert '"giclee_button_style": "light-in-motion",' in rendered
    assert rendered.count("\r\n") == raw.count("\r\n")


def test_button_style_writer_rejects_stale_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "settings_data.json"
    settings_path.write_bytes(_settings_fixture())
    monkeypatch.setattr(service, "_THEME_SETTINGS_PATH_OVERRIDE", settings_path)
    plan = service.build_button_style_plan("nocturne")
    settings_path.write_bytes(_settings_fixture().replace(b"keep-me", b"external"))

    with pytest.raises(RuntimeError, match="zmieniły się"):
        service.apply_button_style_plan(
            plan,
            confirmation=service.THEME_APPLY_CONFIRMATION,
        )
