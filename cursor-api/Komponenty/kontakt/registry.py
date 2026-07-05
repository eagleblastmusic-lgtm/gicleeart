"""Mapowanie stref → templates/page.contact.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="hero",
        label="Hero — Kontakt",
        description="Nagłówek i tło sekcji hero.",
        section_key="hero_VWALbr",
        fields=(
            TemplateField("hero_heading", "Nagłówek", "heading", _s("hero_VWALbr", "blocks", "text_XJxnAG", "settings", "text")),
            TemplateField("hero_image", "Tło — grafika", "shopify_image", _s("hero_VWALbr", "settings", "image_1")),
        ),
    ),
    TemplateZone(
        zone_id="form",
        label="Formularz kontaktowy",
        description="Przycisk wysyłki formularza.",
        section_key="form",
        fields=(
            TemplateField(
                "submit_label",
                "Etykieta przycisku",
                "text",
                _s("form", "blocks", "contact_form_UwiCkQ", "blocks", "submit-button", "settings", "label"),
            ),
        ),
    ),
)
