"""WS-1.2: minimalny zapis i delta-only Apply."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.service_base import load_zone_values
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty._shared.theme_page_editor.writer_safety_delta_fix import (
    _base_path,
    apply_delta_plan,
    build_delta_apply_plan,
    build_minimal_variant_from_state,
    merge_variant_delta,
)


def _config(tmp_path: Path) -> PageEditorConfig:
    divider = TemplateZone(
        zone_id="divider",
        label="Separator",
        description="",
        section_key="divider",
        fields=(
            TemplateField(
                "thickness",
                "Grubość",
                "float",
                ("sections", "divider", "settings", "thickness"),
            ),
        ),
    )
    media = TemplateZone(
        zone_id="media",
        label="Media",
        description="",
        section_key="media",
        fields=(
            TemplateField(
                "body",
                "Treść",
                "body",
                ("sections", "media", "blocks", "text", "settings", "text"),
            ),
            TemplateField(
                "image",
                "Grafika",
                "shopify_image",
                ("sections", "media", "blocks", "visual", "settings", "image"),
            ),
        ),
    )
    return PageEditorConfig(
        component_id="test",
        component_dir=tmp_path / "component",
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/page.test.json",
        preview_path="/pages/test",
        variant_id_prefix="t",
        zones=(divider, media),
    )


def _template(thickness: float = 0.5) -> dict:
    return {
        "sections": {
            "divider": {
                "type": "divider",
                "settings": {"thickness": thickness, "untouched": "keep"},
            },
            "media": {
                "type": "media",
                "settings": {"outside_registry": 7},
                "blocks": {
                    "text": {
                        "settings": {
                            "text": "<p><strong>Zachowaj</strong><br/>formatowanie</p>"
                        }
                    },
                    "visual": {
                        "settings": {
                            "image": "shopify://shop_images/a.jpg",
                            "video_position": "cover",
                        }
                    },
                },
            },
            "foreign": {"type": "custom", "settings": {"x": 1}},
        },
        "order": ["divider", "media", "foreign"],
    }


def test_minimal_save_preserves_untouched_raw_html_and_missing_object_y(tmp_path: Path) -> None:
    config = _config(tmp_path)
    baseline = _template()
    state = {
        "template": copy.deepcopy(baseline),
        "baseline_template": copy.deepcopy(baseline),
        "zone_values": {
            zone.zone_id: load_zone_values(baseline, zone)
            for zone in config.zones
        },
    }
    state["zone_values"]["divider"]["thickness"] = "0.6"

    result = build_minimal_variant_from_state(config, state)
    expected = copy.deepcopy(baseline)
    expected["sections"]["divider"]["settings"]["thickness"] = 0.6

    assert result == expected
    visual = result["sections"]["media"]["blocks"]["visual"]["settings"]
    assert "image_object_y" not in visual


def test_delta_merge_copies_only_variant_changes(tmp_path: Path) -> None:
    config = _config(tmp_path)
    base = _template()
    variant = copy.deepcopy(base)
    variant["sections"]["divider"]["settings"]["thickness"] = 0.6

    theme = _template()
    theme["sections"]["media"]["settings"]["outside_registry"] = 99
    theme["sections"]["foreign"]["settings"]["x"] = 42

    merged = merge_variant_delta(config, theme, base, variant)

    assert merged["sections"]["divider"]["settings"]["thickness"] == 0.6
    assert merged["sections"]["media"]["settings"]["outside_registry"] == 99
    assert merged["sections"]["foreign"]["settings"]["x"] == 42
    assert (
        merged["sections"]["media"]["blocks"]["text"]["settings"]["text"]
        == theme["sections"]["media"]["blocks"]["text"]["settings"]["text"]
    )


def test_apply_plan_diff_contains_only_intended_theme_change(tmp_path: Path) -> None:
    config = _config(tmp_path)
    variant_id = "t1"
    base = _template()
    variant = copy.deepcopy(base)
    variant["sections"]["divider"]["settings"]["thickness"] = 0.6

    variant_path = (
        config.component_dir / "data" / "variants" / variant_id / config.template_basename
    )
    variant_path.parent.mkdir(parents=True, exist_ok=True)
    variant_path.write_text(json.dumps(variant, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    base_path = _base_path(config, variant_id)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    theme_path = tmp_path / "theme" / "templates" / "page.test.json"
    theme_path.parent.mkdir(parents=True, exist_ok=True)
    theme_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan = build_delta_apply_plan(
        config,
        variant_id,
        theme_path=theme_path,
        include_effects_asset=False,
    )

    assert '-        "thickness": 0.5' in plan.diff_text
    assert '+        "thickness": 0.6' in plan.diff_text
    assert "image_object_y" not in plan.diff_text
    assert "<strong>" not in plan.diff_text
    assert len(plan.changed_outputs) == 1


def test_apply_updates_theme_and_advances_variant_base(tmp_path: Path) -> None:
    config = _config(tmp_path)
    variant_id = "t1"
    base = _template()
    variant = copy.deepcopy(base)
    variant["sections"]["divider"]["settings"]["thickness"] = 0.6

    variant_path = (
        config.component_dir / "data" / "variants" / variant_id / config.template_basename
    )
    variant_path.parent.mkdir(parents=True, exist_ok=True)
    variant_bytes = (json.dumps(variant, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    variant_path.write_bytes(variant_bytes)

    base_path = _base_path(config, variant_id)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    base_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    theme_path = tmp_path / "theme" / "templates" / "page.test.json"
    theme_path.parent.mkdir(parents=True, exist_ok=True)
    theme_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    plan = build_delta_apply_plan(
        config,
        variant_id,
        theme_path=theme_path,
        include_effects_asset=False,
    )
    paths = apply_delta_plan(plan, confirmation="ZASTOSUJ t1")

    assert paths == (theme_path,)
    applied = json.loads(theme_path.read_text(encoding="utf-8"))
    assert applied["sections"]["divider"]["settings"]["thickness"] == 0.6
    assert base_path.read_bytes() == variant_bytes
