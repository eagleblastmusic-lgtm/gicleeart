from __future__ import annotations

from pathlib import Path

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.page_section_effects_settings import (
    export_section_effects_for_front,
    save_image_effects_for_section,
)
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty.faq.registry import PAGE_ZONES


def _config(tmp_path: Path, zone: TemplateZone) -> PageEditorConfig:
    return PageEditorConfig(
        component_id="test-page",
        component_dir=tmp_path,
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/page.test.json",
        preview_path="/pages/test",
        variant_id_prefix="tp",
        zones=(zone,),
    )


def _enabled_image_effects() -> dict[str, object]:
    return {
        "desktopEnabled": True,
        "parallaxEnabled": True,
        "parallaxMaxX": 16,
        "parallaxMaxY": 10,
        "parallaxEase": 0.075,
        "parallaxOverscan": 106,
        "imageHoverEnabled": True,
        "imageHoverScale": 1.025,
        "imageHoverDurationMs": 850,
    }


def test_template_zone_selector_is_backward_compatible() -> None:
    zone = TemplateZone(
        zone_id="legacy",
        label="Legacy",
        description="Legacy zone",
        section_key="legacy_section",
    )
    assert zone.image_effect_selector is None


def test_faq_hero_declares_explicit_image_effect_selector() -> None:
    hero = next(zone for zone in PAGE_ZONES if zone.zone_id == "hero")
    assert hero.image_effect_selector == (
        '.hero__media-wrapper--desktop, [data-testid="hero-picture-1"]'
    )


def test_export_adds_selector_from_zone_registry(tmp_path: Path) -> None:
    zone = TemplateZone(
        zone_id="hero",
        label="Hero",
        description="Hero",
        section_key="hero_section",
        fields=(TemplateField("image", "Hero image", "shopify_image"),),
        image_effect_selector='.hero__media-wrapper--desktop, [data-testid="hero-picture-1"]',
    )
    config = _config(tmp_path, zone)
    save_image_effects_for_section(
        config,
        "variant-1",
        zone.section_key,
        _enabled_image_effects(),
    )

    exported = export_section_effects_for_front(config, "variant-1")

    assert exported[zone.section_key]["image"]["targetSelector"] == zone.image_effect_selector


def test_export_does_not_invent_selector_for_other_zones(tmp_path: Path) -> None:
    zone = TemplateZone(
        zone_id="editorial",
        label="Editorial",
        description="Editorial",
        section_key="editorial_section",
        fields=(TemplateField("image", "Image", "shopify_image"),),
    )
    config = _config(tmp_path, zone)
    save_image_effects_for_section(
        config,
        "variant-1",
        zone.section_key,
        _enabled_image_effects(),
    )

    exported = export_section_effects_for_front(config, "variant-1")

    assert "targetSelector" not in exported[zone.section_key]["image"]
