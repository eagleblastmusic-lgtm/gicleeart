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
    TemplateZone(
        zone_id="random_artwork_atmosphere",
        label="Edytuj atmosferę…",
        description=(
            "Parametry wariantu V2 — atmosfera muzealna. W V1 wartości są zachowane, "
            "ale warstwa atmosfery nie jest ładowana. Zakresy są podane przy każdym polu."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField(
                "atmosphere_intensity",
                "Glow kursora — intensywność (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_intensity"),
                hint="0–70. Domyślnie 35. Steruje jasnością miękkiej poświaty.",
            ),
            TemplateField(
                "atmosphere_glow_size",
                "Glow kursora — rozmiar (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_glow_size"),
                hint="60–160. Domyślnie 100. Większa wartość daje szersze, bardziej ambientowe światło.",
            ),
            TemplateField(
                "atmosphere_glow_response",
                "Glow kursora — responsywność (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_glow_response"),
                hint="10–100. Domyślnie 50. Niżej = większy lag i bardziej miękki ruch; wyżej = szybsze śledzenie.",
            ),
            TemplateField(
                "atmosphere_haze",
                "Mgiełka — intensywność (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_haze"),
                hint="0–100. Domyślnie 100. Skaluje jasność obu warstw ambientowej głębi.",
            ),
            TemplateField(
                "atmosphere_haze_speed",
                "Mgiełka — szybkość ruchu (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_haze_speed"),
                hint="0–200. Domyślnie 100. 0 zatrzymuje ruch; 200 przyspiesza go dwukrotnie.",
            ),
            TemplateField(
                "atmosphere_dust",
                "Pył — widoczność (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_dust"),
                hint="0–60. Domyślnie 25. Steruje przezroczystością drobinek.",
            ),
            TemplateField(
                "atmosphere_dust_amount",
                "Pył — ilość (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_dust_amount"),
                hint="0–100. Domyślnie 50. Steruje liczbą drobinek, niezależnie od ich widoczności.",
            ),
            TemplateField(
                "atmosphere_dust_speed",
                "Pył — szybkość ruchu (%)",
                "int",
                _s("random_artwork", "settings", "atmosphere_dust_speed"),
                hint="0–200. Domyślnie 100. 0 zatrzymuje pył; 200 przyspiesza go dwukrotnie.",
            ),
        ),
    ),
)
