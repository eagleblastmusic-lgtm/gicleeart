"""Mapowanie stref → templates/blog.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero bloga",
        description="Nagłówek i wprowadzenie nad listą artykułów.",
        section_key="hero_BMCrdL",
        fields=(
            TemplateField("hero_title", "Nagłówek", "heading", _s("hero_BMCrdL", "blocks", "text_4crMR9", "settings", "text")),
            TemplateField("hero_intro", "Wprowadzenie", "body", _s("hero_BMCrdL", "blocks", "text_PDh9dG", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_BMCrdL", "settings", "image_1")),
        ),
        image_effect_selector=(
            ".hero__media-wrapper--desktop, "
            "[data-testid=\"hero-picture-1\"]"
        ),
    ),
    TemplateZone(
        zone_id="main",
        label="Lista artykułów",
        description="Odstępy sekcji main-blog.",
        section_key="main",
        fields=(
            TemplateField("padding_top", "Padding góra", "int", _s("main", "settings", "padding-block-start")),
            TemplateField("padding_bottom", "Padding dół", "int", _s("main", "settings", "padding-block-end")),
        ),
    ),
)
