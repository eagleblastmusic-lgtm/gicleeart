"""Mapowanie stref → templates/product.szablon-wlasna-fotografia.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="product_main",
        label="Nagłówek produktu",
        description="Tytuł produktu na stronie PDP własnej fotografii.",
        section_key="main",
        fields=(
            TemplateField(
                "product_title",
                "Tytuł",
                "heading",
                _s("main", "blocks", "product-details", "blocks", "group_icgrde", "blocks", "text_xrnftG", "settings", "text"),
            ),
        ),
    ),
    TemplateZone(
        zone_id="recommendations",
        label="Rekomendacje",
        description="Nagłówek sekcji «Może Ci się spodobać».",
        section_key="product_recommendations_qggXJq",
        fields=(
            TemplateField(
                "rec_heading",
                "Nagłówek",
                "heading",
                _s("product_recommendations_qggXJq", "blocks", "text_cbcgyb", "settings", "text"),
            ),
        ),
    ),
)
