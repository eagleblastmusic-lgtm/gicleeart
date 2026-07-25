"""Mapowanie stref → templates/page.losuj-produkt.json."""

from __future__ import annotations

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s


PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="random_artwork",
        label="Losuj obraz — tło i pula",
        description="Własne tło (obraz/film) oraz źródłowa pula produktów do losowania.",
        section_key="random_artwork",
        fields=(
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
                hint=(
                    "Subtelny ruch obrazu/filmu za kursorem. W V3–V5 działa niezależnie "
                    "od reflektora Living Light (może zostać włączony przy wyłączonym świetle)."
                ),
            ),
            TemplateField(
                "bg_video_crossfade_lead_ms",
                "Przenikanie na żywym filmie (ms)",
                "int",
                _s("random_artwork", "settings", "bg_video_crossfade_lead_ms"),
                hint=(
                    "Gdy film + obraz: ile ms przed końcem filmu zaczyna się przenikanie "
                    "do grafiki (na wciąż odtwarzanym video). 0–4000, domyślnie 1400."
                ),
                min_value=0,
                max_value=4000,
                step=50,
            ),
            TemplateField(
                "bg_video_crossfade_hold_ms",
                "Przenikanie na ostatniej klatce (ms)",
                "int",
                _s("random_artwork", "settings", "bg_video_crossfade_hold_ms"),
                hint=(
                    "Po ended film zatrzymuje się na ostatniej klatce; tyle ms trwa "
                    "dalsze przenikanie zanim dekoder zostanie zwolniony. 0–4000, domyślnie 1400. "
                    "Suma z «żywym filmem» = pełny czas fade."
                ),
                min_value=0,
                max_value=4000,
                step=50,
            ),
        ),
    ),
    TemplateZone(
        zone_id="random_artwork_draw",
        label="Fine Art Oracle…",
        description=(
            "Teksty i tempo animacji losowania — scena z nagłówkiem «Niech sztuka wybierze Ciebie», "
            "fazy ładowania, wynik oraz przełącznik WebGL."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField("eyebrow", "Nadtytuł", "text", _s("random_artwork", "settings", "eyebrow")),
            TemplateField("heading", "Nagłówek", "text", _s("random_artwork", "settings", "heading")),
            TemplateField("subtitle", "Podtytuł", "text", _s("random_artwork", "settings", "subtitle")),
            TemplateField("button_label", "Przycisk losowania", "text", _s("random_artwork", "settings", "button_label")),
            TemplateField(
                "galaxy_btn_variant",
                "Wersja przycisku",
                "choice",
                _s("random_artwork", "settings", "galaxy_btn_variant"),
                hint="V1 — srebrny glow (#c8cdd4 / #e8ecf0). V2 — subtelniejszy (#b4bac2 / #d2d6dc).",
                choices=(
                    ("v1", "V1 — srebrny (obecny)"),
                    ("v2", "V2 — subtelny"),
                ),
            ),
            TemplateField(
                "loading_text",
                "Faza 1 — ładowanie",
                "text",
                _s("random_artwork", "settings", "loading_text"),
                hint=(
                    "Np. «Przeszukuję kolekcję…». Litery mają bazową opacity ~30% i "
                    "kolejno rozświetlają się falą; po przejściu do wirowania tekst robi fade-out."
                ),
            ),
            TemplateField(
                "phase_text_2",
                "Faza 2",
                "text",
                _s("random_artwork", "settings", "phase_text_2"),
                hint="Opcjonalny tekst w trakcie wirowania (WebGL onPhase). Puste = pomijane.",
            ),
            TemplateField(
                "phase_text_3",
                "Faza 3",
                "text",
                _s("random_artwork", "settings", "phase_text_3"),
                hint="Opcjonalny tekst przy spowolnieniu wyboru. Puste = pomijane.",
            ),
            TemplateField("result_heading", "Nagłówek wyniku", "text", _s("random_artwork", "settings", "result_heading")),
            TemplateField("view_label", "Przycisk «Zobacz»", "text", _s("random_artwork", "settings", "view_label")),
            TemplateField("replay_label", "Przycisk «Losuj ponownie»", "text", _s("random_artwork", "settings", "replay_label")),
            TemplateField("error_text", "Komunikat błędu", "text", _s("random_artwork", "settings", "error_text")),
            TemplateField("retry_label", "Przycisk ponowienia", "text", _s("random_artwork", "settings", "retry_label")),
            TemplateField(
                "enable_webgl",
                "Włącz efekt WebGL (Three.js)",
                "bool",
                _s("random_artwork", "settings", "enable_webgl"),
                hint="Wyłączenie zostawia elegancki wariant CSS bez sceny 3D.",
            ),
            TemplateField(
                "draw_loading_ms",
                "Minimalny czas ładowania (ms)",
                "int",
                _s("random_artwork", "settings", "draw_loading_ms"),
                hint=(
                    "300–3000. Domyślnie 700. Runtime trzyma fazę min. ~1600 ms, "
                    "żeby fala rozświetlenia liter zdążyła się pokazać; potem pierścień intro "
                    "i napis robią fade-out przed wirowaniem obrazów."
                ),
                min_value=300,
                max_value=3000,
                step=50,
            ),
            TemplateField(
                "draw_phase_hold_ms",
                "Czas trwania fazy tekstu (ms)",
                "int",
                _s("random_artwork", "settings", "draw_phase_hold_ms"),
                hint=(
                    "400–3000. Domyślnie 1100. Dotyczy faz 2/3 (fallback CSS). "
                    "Faza 1 («Przeszukuję…») ma własną animację liter i znika przy starcie spinu."
                ),
                min_value=400,
                max_value=3000,
                step=50,
            ),
        ),
    ),
    TemplateZone(
        zone_id="random_artwork_mask",
        label="Edytowanie Odkrycia maski",
        description=(
            "Spotlight reveal drugiego obrazu tła po filmie: włącznik, obraz ujawniony "
            "oraz parametry reflektora pod kursorem."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField(
                "background_hover_reveal_enabled",
                "Włącz ujawnianie przy najechaniu",
                "bool",
                _s("random_artwork", "settings", "background_hover_reveal_enabled"),
                hint="Po filmie (gdy widać grafikę tła) spotlight odsłania drugi obraz. Wyłącz, aby zostawić samo tło.",
            ),
            TemplateField(
                "background_hover_image",
                "Obraz ujawniony (hover)",
                "shopify_image",
                _s("random_artwork", "settings", "background_hover_image"),
                hint="Drugi obraz tła — widoczny w reflektorze pod kursorem. Możesz wgrać inny plik w każdej chwili.",
            ),
            TemplateField(
                "background_hover_spotlight_radius",
                "Promień odkrycia (px)",
                "int",
                _s("random_artwork", "settings", "background_hover_spotlight_radius"),
                hint="120–600. Domyślnie 340. Większa wartość = większy obszar ujawnienia.",
                min_value=120,
                max_value=600,
                step=10,
            ),
            TemplateField(
                "background_hover_spotlight_ease",
                "Płynność podążania",
                "int",
                _s("random_artwork", "settings", "background_hover_spotlight_ease"),
                hint="5–50. Domyślnie 10 (= 0.10). Niższa = wolniejszy, bardziej „oleisty” ruch reflektora.",
                min_value=5,
                max_value=50,
                step=1,
            ),
        ),
    ),
    TemplateZone(
        zone_id="random_artwork_atmosphere",
        label="Edytuj atmosferę…",
        description=(
            "Living Museum Light dla V3–V5: reflektor kursora i pył ambientowy. "
            "W aktywnym V5 reflektor jest domyślnie wyłączony, a pył startuje po spinie okręgu intro. "
            "V1 nie ładuje tej warstwy (wartości w JSON są zachowane przy przełączaniu wersji)."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField(
                "living_light_enabled",
                "Włącz reflektor kursora",
                "bool",
                _s("random_artwork", "settings", "living_light_enabled"),
                hint=(
                    "Eliptyczne podświetlenie pod kursorem. W V5 domyślnie wyłączone. "
                    "Parallax tła działa niezależnie od tego przełącznika."
                ),
            ),
            TemplateField(
                "living_dust_enabled",
                "Włącz pył ambientowy",
                "bool",
                _s("random_artwork", "settings", "living_dust_enabled"),
                hint=(
                    "Pył 2D startuje dopiero po zakończeniu animacji złotego okręgu intro "
                    "(~4,8 s od startu letter-fade). Wygasa podczas sceny WebGL (drawing)."
                ),
            ),
            TemplateField(
                "living_light_intensity",
                "Intensywność światła (%)",
                "int",
                _s("random_artwork", "settings", "living_light_intensity"),
                hint="0–100. Domyślnie 45.",
            ),
            TemplateField(
                "living_dust_particles",
                "Pył: liczba drobinek",
                "int",
                _s("random_artwork", "settings", "living_dust_particles"),
                hint="20–240. Domyślnie 120.",
            ),
            TemplateField(
                "living_dust_opacity",
                "Pył: widoczność (%)",
                "int",
                _s("random_artwork", "settings", "living_dust_opacity"),
                hint="0–200. Domyślnie 115.",
            ),
            TemplateField(
                "living_dust_size",
                "Pył: rozmiar (%)",
                "int",
                _s("random_artwork", "settings", "living_dust_size"),
                hint="50–200. Domyślnie 125.",
            ),
            TemplateField(
                "living_dust_speed",
                "Pył: szybkość (%)",
                "int",
                _s("random_artwork", "settings", "living_dust_speed"),
                hint="0–200. Domyślnie 75.",
            ),
            TemplateField(
                "living_dust_fps",
                "Pył: limit FPS",
                "int",
                _s("random_artwork", "settings", "living_dust_fps"),
                hint="12–30. Domyślnie 24.",
            ),
            TemplateField(
                "living_dust_dpr_cap",
                "Pył: limit jakości DPR (%)",
                "int",
                _s("random_artwork", "settings", "living_dust_dpr_cap"),
                hint="75–150. Domyślnie 125 = DPR 1.25.",
            ),
        ),
    ),
    TemplateZone(
        zone_id="random_artwork_v5_smoke",
        label="V5 — włącz/wyłącz dym",
        description=(
            "Efekt Elegant Fluid WebGL (Pedzel Alchemy). Domyślnie włączony w V5; "
            "startuje po animacji złotego okręgu intro. Preset i suwaki (100% = baza presetu) "
            "są w tej samej sekcji."
        ),
        section_key="random_artwork",
        settings_only=True,
        fields=(
            TemplateField(
                "cursor_smoke_enabled",
                "Włącz efekt dymu kursora",
                "bool",
                _s("random_artwork", "settings", "cursor_smoke_enabled"),
                hint=(
                    "Stonowany fluid (teal / lila / champagne / ash). "
                    "Montaż i fade-in po spinie okręgu intro — nie w trakcie letter-fade ani wirowania pierścienia."
                ),
            ),
            TemplateField(
                "cursor_smoke_preset",
                "Preset dymu",
                "choice",
                _s("random_artwork", "settings", "cursor_smoke_preset"),
                hint="Elegant V2 jest wiernym wariantem źródłowym. Pozostałe presety zmieniają tempo, paletę i charakter smugi.",
                choices=(
                    ("elegant", "Elegant V2 — oryginalny"),
                    ("gallery_mist", "Gallery Mist — miękka mgła"),
                    ("silk", "Silk — dłuższe jedwabne smugi"),
                    ("whisper", "Whisper — prawie niewidoczny"),
                ),
            ),
            TemplateField(
                "cursor_smoke_quality",
                "Jakość symulacji",
                "choice",
                _s("random_artwork", "settings", "cursor_smoke_quality"),
                hint="Standard jest zalecany. Niska oszczędza GPU; wysoka zwiększa szczegółowość dymu.",
                choices=(
                    ("low", "Niska — 512 px"),
                    ("standard", "Standard — 1024 px"),
                    ("high", "Wysoka — 1536 px"),
                ),
            ),
            TemplateField(
                "cursor_smoke_intensity",
                "Nasycenie koloru (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_intensity"),
                hint="25–200. Siła koloru wstrzykiwanego do symulacji; 100 = wartość presetu.",
                min_value=25,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_opacity",
                "Krycie całej warstwy (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_opacity"),
                hint="20–150. Widoczność canvasa nad tłem; 100 = wartość presetu.",
                min_value=20,
                max_value=150,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_size",
                "Rozmiar smugi (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_size"),
                hint="50–200. Średnica dymu tworzonego bezpośrednio pod kursorem.",
                min_value=50,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_force",
                "Siła ruchu (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_force"),
                hint="25–200. Jak mocno prędkość kursora porusza płynem.",
                min_value=25,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_persistence",
                "Trwałość smugi (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_persistence"),
                hint="50–200. Wyższa wartość oznacza wolniejsze zanikanie dymu.",
                min_value=50,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_swirl",
                "Wirowanie (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_swirl"),
                hint="0–200. Ilość zawijania i turbulentnego ruchu smugi.",
                min_value=0,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_bloom",
                "Poświata i promienie (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_bloom"),
                hint="0–200. Wzmacnia bloom i delikatne sunrays; 0 całkowicie je wygasza.",
                min_value=0,
                max_value=200,
                step=5,
            ),
            TemplateField(
                "cursor_smoke_auto_enabled",
                "Automatyczne smugi w tle",
                "bool",
                _s("random_artwork", "settings", "cursor_smoke_auto_enabled"),
                hint="Dodaje pojedynczy, subtelny oddech dymu także bez ruchu kursora.",
            ),
            TemplateField(
                "cursor_smoke_auto_frequency",
                "Częstotliwość automatycznych smug (%)",
                "int",
                _s("random_artwork", "settings", "cursor_smoke_auto_frequency"),
                hint="25–200. 200% = dwa razy częściej, 50% = dwa razy rzadziej.",
                min_value=25,
                max_value=200,
                step=5,
            ),
        ),
    ),
)
