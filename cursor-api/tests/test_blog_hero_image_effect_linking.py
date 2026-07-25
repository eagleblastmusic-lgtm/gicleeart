from __future__ import annotations

from pathlib import Path

from Komponenty._shared.theme_page_editor.config import PageEditorConfig
from Komponenty._shared.theme_page_editor.page_section_effects_settings import (
    effects_asset_basename,
    export_section_effects_for_front,
    save_image_effects_for_section,
    write_page_section_effects_asset,
)
from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone
from Komponenty.stronablogu.gui import _config as blog_editor_config
from Komponenty.stronablogu.registry import PAGE_ZONES


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


def test_blog_hero_declares_explicit_image_effect_selector() -> None:
    hero = next(zone for zone in PAGE_ZONES if zone.zone_id == "hero")
    assert hero.image_effect_selector == (
        '.hero__media-wrapper--desktop, [data-testid="hero-picture-1"]'
    )


def test_blog_effects_asset_basename() -> None:
    assert effects_asset_basename(blog_editor_config()) == "blog-section-effects.js"


def test_blog_export_adds_selector_from_zone_registry(tmp_path: Path) -> None:
    zone = TemplateZone(
        zone_id="hero",
        label="Hero",
        description="Hero",
        section_key="hero_section",
        fields=(TemplateField("image", "Hero image", "shopify_image"),),
        image_effect_selector='.hero__media-wrapper--desktop, [data-testid="hero-picture-1"]',
    )
    config = PageEditorConfig(
        component_id="stronablogu",
        component_dir=tmp_path,
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/blog.json",
        preview_path="/blogs/news",
        variant_id_prefix="sb",
        zones=(zone,),
    )
    save_image_effects_for_section(
        config,
        "sb1",
        zone.section_key,
        _enabled_image_effects(),
    )

    exported = export_section_effects_for_front(config, "sb1")

    assert exported[zone.section_key]["image"]["targetSelector"] == zone.image_effect_selector


def test_write_blog_section_effects_asset_includes_selector(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    from Komponenty._shared.theme_page_editor import page_section_effects_settings as mod

    theme = tmp_path / "theme"
    (theme / "assets").mkdir(parents=True)
    monkeypatch.setattr(mod, "theme_root", lambda: theme)

    hero = next(zone for zone in PAGE_ZONES if zone.zone_id == "hero")
    config = PageEditorConfig(
        component_id="stronablogu",
        component_dir=tmp_path / "component",
        app_title="Test",
        intro_title="Test",
        intro_body="Test",
        template_rel="templates/blog.json",
        preview_path="/blogs/news",
        variant_id_prefix="sb",
        zones=(hero,),
    )
    save_image_effects_for_section(
        config,
        "sb1",
        hero.section_key,
        _enabled_image_effects(),
    )
    path = write_page_section_effects_asset(config, "sb1")
    content = path.read_text(encoding="utf-8")

    assert path.name == "blog-section-effects.js"
    assert "targetSelector" in content
    assert "hero-picture-1" in content
