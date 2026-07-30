from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from .config import PageEditorConfig
from .service_base import merge_managed_zone_values
from .types import TemplateZone
from .viewport_screen import (
    VIEWPORT_SCREEN_DEPLOY_RELPATHS,
    VIEWPORT_SCREEN_SECTION_TYPE,
    add_viewport_screen_section,
    config_with_viewport_screen_zones,
    discover_viewport_screen_zones,
    normalize_viewport_height,
    remove_viewport_screen_section,
)


def _template() -> dict:
    return {
        "sections": {
            "hero": {"type": "rich-text", "settings": {}},
            "footer": {"type": "rich-text", "settings": {}},
        },
        "order": ["hero", "footer"],
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


def test_add_viewport_screen_after_selected_section_with_custom_height() -> None:
    template = _template()

    section_key = add_viewport_screen_section(
        template,
        height_vh=175,
        after_section_key="hero",
    )

    assert template["order"] == ["hero", section_key, "footer"]
    section = template["sections"][section_key]
    assert section["type"] == VIEWPORT_SCREEN_SECTION_TYPE
    assert section["name"] == "Ekran 175vh"
    assert section["settings"]["viewport_height_vh"] == 175


def test_viewport_screen_zone_exposes_editable_vh_value() -> None:
    template = _template()
    section_key = add_viewport_screen_section(
        template,
        height_vh="240",
        after_section_key="hero",
    )

    zones = discover_viewport_screen_zones(template)

    assert len(zones) == 1
    assert zones[0].section_key == section_key
    assert zones[0].label == "Ekran 240vh"
    field = zones[0].fields[0]
    assert field.field_id == "viewport_height_vh"
    assert field.kind == "int"
    assert field.unit == "vh"
    assert field.free_entry is True
    assert field.path == (
        "sections",
        section_key,
        "settings",
        "viewport_height_vh",
    )
    base = _config(Path("."))
    base = replace(
        base,
        zones=(
            TemplateZone("hero", "Hero", "", "hero"),
            TemplateZone("footer", "Stopka", "", "footer"),
        ),
    )
    dynamic = config_with_viewport_screen_zones(base, template)
    assert tuple(zone.section_key for zone in dynamic.zones) == (
        "hero",
        section_key,
        "footer",
    )


def test_new_viewport_screen_is_merged_into_saved_variant() -> None:
    current = _template()
    pending = _template()
    section_key = add_viewport_screen_section(
        pending,
        height_vh=225,
        after_section_key="hero",
    )
    config = config_with_viewport_screen_zones(
        _config(Path(".")),
        pending,
    )

    merged = merge_managed_zone_values(config, current, pending)

    assert merged["order"] == ["hero", section_key, "footer"]
    assert merged["sections"][section_key] == pending["sections"][section_key]


def test_remove_viewport_screen_removes_only_its_section_and_order_entry() -> None:
    template = _template()
    section_key = add_viewport_screen_section(
        template,
        height_vh=150,
        after_section_key="hero",
    )

    removed = remove_viewport_screen_section(template, section_key)

    assert removed["type"] == VIEWPORT_SCREEN_SECTION_TYPE
    assert section_key not in template["sections"]
    assert template["order"] == ["hero", "footer"]
    with pytest.raises(ValueError):
        remove_viewport_screen_section(template, "hero")


def test_safe_merge_does_not_restore_deleted_viewport_screen() -> None:
    current = _template()
    section_key = add_viewport_screen_section(
        current,
        height_vh=180,
        after_section_key="hero",
    )
    pending = {
        "sections": {
            "hero": current["sections"]["hero"],
            "footer": current["sections"]["footer"],
        },
        "order": ["hero", "footer"],
    }

    merged = merge_managed_zone_values(
        _config(Path(".")),
        current,
        pending,
    )

    assert section_key not in merged["sections"]
    assert section_key not in merged["order"]


def test_viewport_height_validation_and_runtime_contract() -> None:
    assert normalize_viewport_height("100,4") == 100
    with pytest.raises(ValueError):
        normalize_viewport_height(0)
    with pytest.raises(ValueError):
        normalize_viewport_height(10001)

    root = Path(__file__).resolve().parents[4]
    liquid = (
        root / "sections" / "giclee-viewport-screen.liquid"
    ).read_text(encoding="utf-8")
    shell = Path(__file__).with_name("gui_shell.py").read_text(encoding="utf-8")
    studio_context = (
        root
        / "cursor-api"
        / "giclee_app"
        / "ui"
        / "gicleeframe_view_film_scroll_context.py"
    ).read_text(encoding="utf-8")

    assert "height: {{ viewport_height }}vh" in liquid
    assert '"id": "viewport_height_vh"' in liquid
    assert 'label="Wstaw ekran…"' in shell
    assert 'label="Wstaw ekran…"' in studio_context
    assert 'label="Usuń ekran…"' in shell
    assert 'label="Usuń ekran…"' in studio_context
    assert (
        "sections/giclee-viewport-screen.liquid"
        in VIEWPORT_SCREEN_DEPLOY_RELPATHS
    )
