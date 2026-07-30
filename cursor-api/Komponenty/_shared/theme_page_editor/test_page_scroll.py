from __future__ import annotations

from pathlib import Path

from .config import PageEditorConfig
from .page_scroll import (
    PAGE_SCROLL_DEPLOY_RELPATHS,
    PAGE_SCROLL_SECTION_TYPE,
    add_page_scroll_section,
    config_with_page_scroll_zones,
    discover_page_scroll_zones,
    page_scroll_section_key,
)


def _template() -> dict:
    return {
        "sections": {
            "hero": {
                "type": "rich-text",
                "settings": {},
                "blocks": {},
            }
        },
        "order": ["hero"],
    }


def _config(tmp_path: Path) -> PageEditorConfig:
    return PageEditorConfig(
        component_id="test-page",
        component_dir=tmp_path,
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/page.test.json",
        preview_path="/pages/test",
        variant_id_prefix="test",
        zones=(),
    )


def test_add_page_scroll_creates_one_global_config_and_visible_zone(
    tmp_path: Path,
) -> None:
    template = _template()

    section_key = add_page_scroll_section(
        template,
        after_section_key="hero",
    )
    duplicate_key = add_page_scroll_section(template)

    assert duplicate_key == section_key
    assert template["order"] == ["hero", section_key]
    assert page_scroll_section_key(template) == section_key
    assert (
        sum(
            section.get("type") == PAGE_SCROLL_SECTION_TYPE
            for section in template["sections"].values()
        )
        == 1
    )
    section = template["sections"][section_key]
    assert section["name"] == "Scroll strony"
    assert section["settings"]["page_scroll_mode"] == "standard"
    assert section["settings"]["scroll_lenis_preset"] == "balanced"

    zones = discover_page_scroll_zones(template)
    assert len(zones) == 1
    assert zones[0].label == "Scroll strony"
    mode = next(
        field for field in zones[0].fields if field.field_id == "page_scroll_mode"
    )
    lenis = next(
        field
        for field in zones[0].fields
        if field.field_id == "scroll_lenis_preset"
    )
    assert mode.path == (
        "sections",
        section_key,
        "settings",
        "page_scroll_mode",
    )
    assert lenis.group_label == "Ustawienia Lenis"
    assert lenis.group_collapsed is True

    dynamic_config = config_with_page_scroll_zones(
        _config(tmp_path),
        template,
    )
    assert dynamic_config.zones == zones


def test_page_scroll_runtime_is_portable_and_context_actions_are_available() -> None:
    root = Path(__file__).resolve().parents[4]
    section = (root / "sections" / "giclee-page-scroll-config.liquid").read_text(
        encoding="utf-8"
    )
    runtime = (root / "assets" / "giclee-page-smooth-scroll.js").read_text(
        encoding="utf-8"
    )
    shell = Path(__file__).with_name("gui_shell.py").read_text(encoding="utf-8")
    studio_context = (
        root
        / "cursor-api"
        / "giclee_app"
        / "ui"
        / "gicleeframe_view_film_scroll_context.py"
    ).read_text(encoding="utf-8")

    assert 'label="Dodaj „Scroll strony”…"' in shell
    assert 'label="Dodaj „Scroll strony”…"' in studio_context
    assert "GICLEE_PAGE_SCROLL_CONFIG" in section
    assert "lenis.min.js" in section
    assert "giclee-page-smooth-scroll.js" in section
    assert "window.GICLEE_PAGE_SCROLL_CONFIG" in runtime
    assert "template-page-filozofia-marki" not in runtime
    assert "sections/giclee-page-scroll-config.liquid" in PAGE_SCROLL_DEPLOY_RELPATHS
