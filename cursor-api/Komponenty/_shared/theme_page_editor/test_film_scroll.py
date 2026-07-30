from __future__ import annotations

import copy
import json
from pathlib import Path

from Komponenty.filozofiamarki.video_sequence import (
    ASSET_FAMILIES,
    active_scroll_video_deploy_relpaths,
    iter_scroll_video_block_settings,
)

from .config import PageEditorConfig
from .film_scroll import (
    FILM_SCROLL_DEPLOY_RELPATHS,
    add_film_scroll_section,
    config_with_film_scroll_zones,
    discover_film_scroll_zones,
    selected_film_scroll_asset_relpaths,
    template_supports_film_scroll,
)
from .service_base import merge_managed_zone_values
from . import variants as varmod


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


def test_add_scroll_film_creates_shopify_section_and_one_gicleeapp_zone(
    tmp_path: Path,
) -> None:
    template = _template()
    assert template_supports_film_scroll(template)

    section_key = add_film_scroll_section(
        template,
        label="Pracownia",
        after_section_key="hero",
    )

    section = template["sections"][section_key]
    settings = section["blocks"]["media"]["settings"]
    assert template["order"] == ["hero", section_key]
    assert section["type"] == "media-with-content"
    assert section["disabled"] is True
    assert section["name"] == "Scroll Film — Pracownia"
    assert settings["media_type"] == "scroll_video"
    assert settings["scroll_video_container"] == "webm"
    assert settings["scroll_video_asset"].startswith("giclee-film-scroll-")

    zones = discover_film_scroll_zones(template)
    assert len(zones) == 1
    assert zones[0].label == "Scroll Film — Pracownia"
    motion = next(
        field for field in zones[0].fields if field.field_id == "scroll_motion_preset"
    )
    assert motion.group_label == "Charakter odtwarzania"
    assert motion.group_collapsed is True

    dynamic_config = config_with_film_scroll_zones(_config(tmp_path), template)
    assert dynamic_config.zones == zones


def test_new_scroll_film_is_merged_as_complete_section(tmp_path: Path) -> None:
    current = _template()
    pending = copy.deepcopy(current)
    section_key = add_film_scroll_section(
        pending,
        label="Nowa scena",
        after_section_key="hero",
    )
    config = config_with_film_scroll_zones(_config(tmp_path), pending)

    merged = merge_managed_zone_values(config, current, pending)

    assert merged["order"] == ["hero", section_key]
    assert merged["sections"][section_key] == pending["sections"][section_key]


def test_selected_library_assets_and_runtime_dependencies_are_deployable() -> None:
    template = _template()
    section_key = add_film_scroll_section(template, label="Asset")
    settings = template["sections"][section_key]["blocks"]["media"]["settings"]
    settings["scroll_video_source"] = (
        "giclee-scroll-library-shared-1080p-webm-test.webm::"
        "giclee-scroll-library-shared-1080p-webm-test-poster.webp::"
        "giclee-scroll-library-shared-1080p-webm-test-manifest.json::"
        "120::60::1920::1080::false::vp9"
    )

    assert selected_film_scroll_asset_relpaths(template) == (
        "assets/giclee-scroll-library-shared-1080p-webm-test.webm",
        "assets/giclee-scroll-library-shared-1080p-webm-test-poster.webp",
        "assets/giclee-scroll-library-shared-1080p-webm-test-manifest.json",
    )
    assert "shared" in ASSET_FAMILIES
    assert "assets/giclee-scroll-scrub-video.js" in FILM_SCROLL_DEPLOY_RELPATHS


def test_shared_scroll_film_is_discovered_outside_philosophy_template(
    tmp_path: Path,
) -> None:
    template = _template()
    section_key = add_film_scroll_section(template, label="Inna strona")
    settings = template["sections"][section_key]["blocks"]["media"]["settings"]
    settings["scroll_video_source"] = (
        "giclee-scroll-library-shared-1080p-webm-test.webm::"
        "giclee-scroll-library-shared-1080p-webm-test-poster.webp::"
        "giclee-scroll-library-shared-1080p-webm-test-manifest.json::"
        "120::60::1920::1080::true::vp9"
    )
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "page.inna.json").write_text(
        json.dumps(template),
        encoding="utf-8",
    )

    selections = iter_scroll_video_block_settings(tmp_path)
    deploy_paths = active_scroll_video_deploy_relpaths(tmp_path)

    assert selections == [
        {
            "family": "shared",
            "asset_id": settings["scroll_video_asset"],
            "engine": "video",
            "container": "webm",
            "quality": "1080p",
            "source_spec": settings["scroll_video_source"],
        }
    ]
    assert (
        "assets/giclee-scroll-library-shared-1080p-webm-test.webm"
        in deploy_paths
    )
    assert (
        "assets/giclee-scroll-library-shared-1080p-webm-test-manifest.json"
        in deploy_paths
    )


def test_shared_editor_exposes_context_action_and_motion_button_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    shell = (
        root
        / "Komponenty"
        / "_shared"
        / "theme_page_editor"
        / "gui_shell.py"
    ).read_text(encoding="utf-8")
    studio_context = (
        root.parent
        / "cursor-api"
        / "giclee_app"
        / "ui"
        / "gicleeframe_view_film_scroll_context.py"
    ).read_text(encoding="utf-8")
    liquid = (root.parent / "snippets" / "media.liquid").read_text(
        encoding="utf-8"
    )

    assert 'label="Dodaj „Scroll Film”…"' in shell
    assert 'zone_list.bind("<Button-3>"' in shell
    assert 'left.bind("<Button-3>"' in shell
    assert 'zone_list.bind("<Double-Button-1>"' in shell
    assert "rename_section_label(" in shell
    assert "build_film_scroll_source_controls" in shell
    assert "activate_film_scroll_assets()" in shell
    assert "initial_section_key" in shell
    assert 'label="Dodaj „Scroll Film”…"' in studio_context
    assert "persist_editor_to_variant" in studio_context
    assert "Charakter odtwarzania" in Path(__file__).with_name(
        "film_scroll.py"
    ).read_text(encoding="utf-8")
    assert "scroll_source_spec | split: '::'" in liquid
    assert "scroll_is_shared" in liquid
    assert "media-block__scroll-stage--standalone" in liquid
    assert "--scroll-separator-band: 0px" in liquid
    assert "height: 100svh" in liquid
    assert "top: 0" in liquid


def test_section_labels_are_saved_per_variant_and_copied(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    varmod.ensure_variants_initialized(config)

    varmod.rename_section_label(
        config,
        "test1",
        "film_scroll_scene",
        "Scena finałowa",
    )
    copied_id = varmod.create_variant_copy(config, "test1", "Kopia")

    assert varmod.section_labels(config, "test1") == {
        "film_scroll_scene": "Scena finałowa"
    }
    assert varmod.section_labels(config, copied_id) == {
        "film_scroll_scene": "Scena finałowa"
    }
