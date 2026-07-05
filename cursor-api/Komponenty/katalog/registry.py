"""Mapowanie stref → templates/collection.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="biography",
        label="Biografia autora",
        description="Tło i ustawienia sekcji biografii na stronie kolekcji.",
        section_key="section",
        fields=(
            TemplateField("bio_bg", "Tło — grafika", "shopify_image", _s("section", "settings", "background_image")),
            TemplateField("bio_pad_top", "Padding góra", "int", _s("section", "settings", "padding_top")),
            TemplateField("bio_pad_bottom", "Padding dół", "int", _s("section", "settings", "padding_bottom")),
        ),
    ),
    TemplateZone(
        zone_id="showcase",
        label="Galeria kolekcji",
        description="Nagłówki sekcji giclee-artist-collection-showcase.",
        section_key="giclee_artist_collection_showcase_7djLQQ",
        fields=(
            TemplateField("eyebrow", "Nadtytuł", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "eyebrow")),
            TemplateField("heading", "Nagłówek", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "heading")),
            TemplateField("lead", "Lead", "body", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "lead")),
            TemplateField("cta_label", "Etykieta CTA", "text", _s("giclee_artist_collection_showcase_7djLQQ", "settings", "cta_label")),
        ),
    ),
    TemplateZone(
        zone_id="works",
        label="Sekcja Dzieła",
        description="Nagłówek nad siatką produktów.",
        section_key="section_ANxq96",
        fields=(
            TemplateField("works_heading", "Nagłówek", "heading", _s("section_ANxq96", "blocks", "text_FNbyeV", "settings", "text")),
        ),
    ),
)
