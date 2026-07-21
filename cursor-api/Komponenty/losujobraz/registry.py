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
            TemplateField("fetch_full_pool", "Pobierz pełną pulę kolekcji", "bool", _s("random_artwork", "settings", "fetch_full_pool")),
            TemplateField(
                "background_image",
                "Własne tło — obraz",
                "shopify_image",
                _s("random_artwork", "settings", "background_image"),
                hint="Puste = domyślna scena (aurora + WebGL).",
            ),
            TemplateField(
                "background_video",
                "Własne tło — film / animacja",
                "shopify_video",
                _s("random_artwork", "settings", "background_video"),
                hint="Film ma pierwszeństwo przed obrazem. MP4/WebM/MOV lub ref Shopify.",
            ),
            TemplateField(
                "background_parallax",
                "Parallax tła (mysz)",
                "bool",
                _s("random_artwork", "settings", "background_parallax"),
                hint="Subtelny ruch obrazu lub filmu przy ruszaniu kursorem.",
            ),
        ),
    ),
    TemplateZone(
        zone_id="random_artwork_atmosphere",
        label="Edytuj atmosferę…",
        description=(
            "V1 zachowuje wartości bez ładowania warstwy. V2 używa parametrów glow, "
            "mgiełki i pyłu. V3 używa minimalnych ustawień reflektora oraz pyłu Living Museum Light."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField("atmosphere_intensity", "V2 — glow: intensywność (%)", "int", _s("random_artwork", "settings", "atmosphere_intensity"), hint="0–70. Domyślnie 35."),
            TemplateField("atmosphere_glow_size", "V2 — glow: rozmiar (%)", "int", _s("random_artwork", "settings", "atmosphere_glow_size"), hint="60–160. Domyślnie 100."),
            TemplateField("atmosphere_glow_response", "V2 — glow: responsywność (%)", "int", _s("random_artwork", "settings", "atmosphere_glow_response"), hint="10–100. Domyślnie 50."),
            TemplateField("atmosphere_haze", "V2 — mgiełka: intensywność (%)", "int", _s("random_artwork", "settings", "atmosphere_haze"), hint="0–100. Domyślnie 100."),
            TemplateField("atmosphere_haze_speed", "V2 — mgiełka: szybkość (%)", "int", _s("random_artwork", "settings", "atmosphere_haze_speed"), hint="0–200. 0 zatrzymuje ruch."),
            TemplateField("atmosphere_dust", "V2 — pył: widoczność (%)", "int", _s("random_artwork", "settings", "atmosphere_dust"), hint="0–60. Domyślnie 25."),
            TemplateField("atmosphere_dust_amount", "V2 — pył: ilość (%)", "int", _s("random_artwork", "settings", "atmosphere_dust_amount"), hint="0–100. Domyślnie 50."),
            TemplateField("atmosphere_dust_speed", "V2 — pył: szybkość (%)", "int", _s("random_artwork", "settings", "atmosphere_dust_speed"), hint="0–200. 0 zatrzymuje ruch."),
            TemplateField(
                "living_light_enabled",
                "V3 — włącz reflektor kursora",
                "bool",
                _s("random_artwork", "settings", "living_light_enabled"),
                hint="Wyłącza reflektor bez zmiany portalu ani WebGL.",
            ),
            TemplateField(
                "living_dust_enabled",
                "V3 — włącz pył ambientowy",
                "bool",
                _s("random_artwork", "settings", "living_dust_enabled"),
                hint="Pył 2D wygasa podczas właściwej animacji WebGL.",
            ),
            TemplateField(
                "living_light_intensity",
                "V3 — intensywność światła (%)",
                "int",
                _s("random_artwork", "settings", "living_light_intensity"),
                hint="0–100. Domyślnie 45.",
            ),
        ),
    ),
)
