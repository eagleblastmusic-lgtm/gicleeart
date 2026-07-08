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
            TemplateField("subtitle", "Podtytuł", "text", _s("random_artwork", "settings", "subtitle")),
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
            TemplateField(
                "background_image",
                "Własne tło — obraz",
                "shopify_image",
                _s("random_artwork", "settings", "background_image"),
                hint="Puste = domyślna scena (aurora + WebGL). Ustaw obraz, aby użyć własnego tła.",
            ),
            TemplateField(
                "background_video",
                "Własne tło — film / animacja",
                "shopify_video",
                _s("random_artwork", "settings", "background_video"),
                hint="Film ma pierwszeństwo przed obrazem. MP4/WebM/MOV lub ref shopify://files/videos/…",
            ),
            TemplateField(
                "background_parallax",
                "Parallax tła (mysz)",
                "bool",
                _s("random_artwork", "settings", "background_parallax"),
                hint="Subtelny ruch obrazu lub filmu przy ruszaniu kursorem — jak w karuzeli / konfiguratorze.",
            ),
        ),
    ),
)
