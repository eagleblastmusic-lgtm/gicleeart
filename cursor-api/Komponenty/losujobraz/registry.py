"""Mapowanie stref → templates/page.losuj-produkt.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="random_artwork",
        label="Losuj obraz — interfejs",
        description="Teksty sekcji giclee-random-artwork (Fine Art Oracle).",
        section_key="random_artwork",
        fields=(
            TemplateField("eyebrow", "Nadtytuł", "text", _s("random_artwork", "settings", "eyebrow")),
            TemplateField("heading", "Nagłówek", "text", _s("random_artwork", "settings", "heading")),
            TemplateField("subtitle", "Podtytuł", "body", _s("random_artwork", "settings", "subtitle")),
            TemplateField("button_label", "Przycisk losowania", "text", _s("random_artwork", "settings", "button_label")),
            TemplateField("loading_text", "Tekst ładowania", "text", _s("random_artwork", "settings", "loading_text")),
            TemplateField("result_heading", "Nagłówek wyniku", "text", _s("random_artwork", "settings", "result_heading")),
            TemplateField("view_label", "Przycisk «Zobacz»", "text", _s("random_artwork", "settings", "view_label")),
            TemplateField("replay_label", "Przycisk «Losuj ponownie»", "text", _s("random_artwork", "settings", "replay_label")),
            TemplateField("error_text", "Komunikat błędu", "text", _s("random_artwork", "settings", "error_text")),
            TemplateField("retry_label", "Przycisk ponowienia", "text", _s("random_artwork", "settings", "retry_label")),
            TemplateField("pool_limit", "Limit puli produktów", "int", _s("random_artwork", "settings", "pool_limit")),
            TemplateField(
                "fetch_full_pool",
                "Pobierz pełną pulę kolekcji",
                "bool",
                _s("random_artwork", "settings", "fetch_full_pool"),
            ),
        ),
    ),
)
