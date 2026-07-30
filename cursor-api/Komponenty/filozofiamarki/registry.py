"""Pola faktycznie używane przez stronę Filozofia marki."""

from __future__ import annotations

from dataclasses import replace

from Komponenty._shared.theme_page_editor.types import (
    FieldGroupVariantLibrary,
    TemplateField,
    TemplateZone,
    _s,
)

from .motion_config import preset_choices, preset_values
from .video_sequence import native_video_source_choices


_MEDIA_SETTINGS = (
    "media_with_content_D7REjd",
    "blocks",
    "media",
    "settings",
)
_WROTA_MEDIA_SETTINGS = (
    "media_with_content_Wrota",
    "blocks",
    "media",
    "settings",
)

def _quote_setting(name: str) -> tuple[str, ...]:
    return _s("section_tAj94h", "settings", name)


def _media_setting(name: str) -> tuple[str, ...]:
    return _s(*_MEDIA_SETTINGS, name)


def _wrota_setting(name: str) -> tuple[str, ...]:
    return _s(*_WROTA_MEDIA_SETTINGS, name)


def _philosophy_video_choices(
    values: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    return native_video_source_choices(values, family="philosophy")


def _wrota_video_choices(
    values: dict[str, object],
) -> tuple[tuple[str, str], ...]:
    normalized = {
        "scroll_video_engine": values.get("wrota_scroll_video_engine"),
        "scroll_video_quality": values.get("wrota_scroll_video_quality"),
        "scroll_video_container": values.get("wrota_scroll_video_container"),
    }
    return native_video_source_choices(normalized, family="wrota")


def _remap_fields_to_section(
    fields: tuple[TemplateField, ...],
    *,
    from_section: str,
    to_section: str,
    id_prefix: str = "",
) -> tuple[TemplateField, ...]:
    remapped: list[TemplateField] = []
    for item in fields:
        path = item.path
        if path and len(path) > 1 and path[1] == from_section:
            path = (path[0], to_section, *path[2:])
        remapped.append(
            replace(
                item,
                field_id=f"{id_prefix}{item.field_id}" if id_prefix else item.field_id,
                path=path,
            )
        )
    return tuple(remapped)


PAGE_ZONES: tuple[TemplateZone, ...] = (
    TemplateZone(
        zone_id="page_scroll",
        label="Scroll strony",
        description=(
            "Sposób przewijania całej strony Filozofia marki. "
            "«Płynny» = lekki mechanizm strony. «Lenis» = silnik lenis.dev. "
            "«Własny» = ręczne parametry techniczne."
        ),
        section_key="giclee_filozofia_page_config",
        fields=(
            TemplateField(
                "page_scroll_mode",
                "Tryb scrolla",
                "choice",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "page_scroll_mode",
                ),
                choices=(
                    ("standard", "Standardowy"),
                    ("smooth", "Płynny — lekki"),
                    ("lenis", "Lenis"),
                    ("custom", "Własny"),
                ),
                hint=(
                    "Standardowy = natywny. Płynny = krótki, responsywny smoothing. "
                    "Lenis = lokalnie dołączony Lenis. Własny = pełna kontrola parametrów."
                ),
            ),
            TemplateField(
                "scroll_smoothness",
                "Płynność / responsywność",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_smoothness",
                ),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                hint=(
                    "Wyżej = szybsza reakcja i krótsze doganianie kółka. "
                    "75% to profil zbalansowany."
                ),
                visible_when=(("page_scroll_mode", ("smooth",)),),
            ),
            TemplateField(
                "scroll_wheel_gain",
                "Siła kółka",
                "float",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_wheel_gain",
                ),
                min_value=0.1,
                max_value=5.0,
                step=0.01,
                hint="1.00 = naturalna odległość; wyżej = większy skok.",
                visible_when=(("page_scroll_mode", ("smooth", "custom")),),
            ),
            TemplateField(
                "scroll_lenis_preset",
                "Profil Lenis",
                "choice",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_preset",
                ),
                choices=(
                    ("balanced", "Zbalansowany"),
                    ("responsive", "Responsywny"),
                    ("cinematic", "Filmowy"),
                    ("custom", "Własne ustawienia"),
                ),
                hint=(
                    "Własne ustawienia zapisują się w bieżącej wersji strony. "
                    "Niżej możesz też tworzyć wiele nazwanych wariantów Lenis."
                ),
                visible_when=(("page_scroll_mode", ("lenis",)),),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_lerp",
                "Lerp",
                "float",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_lerp",
                ),
                min_value=0.01,
                max_value=1.0,
                step=0.005,
                hint=(
                    "Wyżej = szybsze doganianie. 0.245 odpowiada profilowi "
                    "zbalansowanemu."
                ),
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_wheel_multiplier",
                "Siła kółka Lenis",
                "float",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_wheel_multiplier",
                ),
                min_value=0.1,
                max_value=5.0,
                step=0.05,
                hint="1.00 = naturalna odległość impulsu kółka.",
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_smooth_wheel",
                "Wygładzaj kółko",
                "bool",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_smooth_wheel",
                ),
                hint="Wyłączenie pozostawia natywny ruch kółka wewnątrz Lenis.",
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_overscroll",
                "Overscroll",
                "bool",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_overscroll",
                ),
                hint="Kontroluje propagowanie ruchu na początku i końcu strony.",
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_anchors",
                "Obsługuj linki kotwicowe",
                "bool",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_anchors",
                ),
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_lenis_stop_inertia_on_navigate",
                "Zatrzymaj bezwładność przy nawigacji",
                "bool",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_lenis_stop_inertia_on_navigate",
                ),
                visible_when=(
                    ("page_scroll_mode", ("lenis",)),
                    ("scroll_lenis_preset", ("custom",)),
                ),
                group_id="lenis_settings",
                group_label="Ustawienia Lenis",
                group_collapsed=True,
            ),
            TemplateField(
                "scroll_line_height_px",
                "Line height (px)",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_line_height_px",
                ),
                min_value=1,
                max_value=200,
                step=1,
                unit=" px",
                hint="Przelicznik deltaMode = lines (Płynny: 40).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_page_delta_ratio",
                "Page delta ratio",
                "float",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_page_delta_ratio",
                ),
                min_value=0.1,
                max_value=2.0,
                step=0.05,
                hint="Przelicznik deltaMode = pages (Płynny: 0.9).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_max_wheel_delta_px",
                "Max wheel delta (px)",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_max_wheel_delta_px",
                ),
                min_value=50,
                max_value=2000,
                step=10,
                unit=" px",
                hint="Max skok na jedno wheel (Płynny: 420).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_max_target_lead_px",
                "Max target lead (px)",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_max_target_lead_px",
                ),
                min_value=100,
                max_value=5000,
                step=50,
                unit=" px",
                hint="Max wyprzedzenie targetu (Płynny 75%: 800).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_follow_tau_ms",
                "Follow tau (ms)",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_follow_tau_ms",
                ),
                min_value=1,
                max_value=1200,
                step=1,
                unit=" ms",
                hint=(
                    "Stała doganiania — wyżej = wolniej (Płynny 75%: ok. 74). "
                    "1–16 ≈ prawie natychmiastowo."
                ),
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_stop_epsilon_px",
                "Stop epsilon (px)",
                "float",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_stop_epsilon_px",
                ),
                min_value=0.01,
                max_value=5.0,
                step=0.01,
                unit=" px",
                hint="Próg zatrzymania animacji (Płynny: 0.25).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
            TemplateField(
                "scroll_max_frame_delta_ms",
                "Max frame delta (ms)",
                "int",
                _s(
                    "giclee_filozofia_page_config",
                    "settings",
                    "scroll_max_frame_delta_ms",
                ),
                min_value=8,
                max_value=100,
                step=1,
                unit=" ms",
                hint="Clamp delty czasu między klatkami (Płynny: 48).",
                visible_when=(("page_scroll_mode", ("custom",)),),
            ),
        ),
        preset_field_id="scroll_lenis_preset",
        preset_values=(
            (
                "balanced",
                (
                    ("scroll_lenis_lerp", 0.245),
                    ("scroll_lenis_wheel_multiplier", 1.05),
                    ("scroll_lenis_smooth_wheel", True),
                    ("scroll_lenis_overscroll", True),
                    ("scroll_lenis_anchors", True),
                    ("scroll_lenis_stop_inertia_on_navigate", True),
                ),
            ),
            (
                "responsive",
                (
                    ("scroll_lenis_lerp", 0.32),
                    ("scroll_lenis_wheel_multiplier", 1.0),
                    ("scroll_lenis_smooth_wheel", True),
                    ("scroll_lenis_overscroll", True),
                    ("scroll_lenis_anchors", True),
                    ("scroll_lenis_stop_inertia_on_navigate", True),
                ),
            ),
            (
                "cinematic",
                (
                    ("scroll_lenis_lerp", 0.14),
                    ("scroll_lenis_wheel_multiplier", 0.9),
                    ("scroll_lenis_smooth_wheel", True),
                    ("scroll_lenis_overscroll", True),
                    ("scroll_lenis_anchors", True),
                    ("scroll_lenis_stop_inertia_on_navigate", True),
                ),
            ),
        ),
        field_group_variant_libraries=(
            FieldGroupVariantLibrary(
                group_id="lenis_settings",
                label="Moje warianty Lenis",
                storage_filename="lenis-scroll-variants.json",
                controlled_field_ids=(
                    "scroll_lenis_lerp",
                    "scroll_lenis_wheel_multiplier",
                    "scroll_lenis_smooth_wheel",
                    "scroll_lenis_overscroll",
                    "scroll_lenis_anchors",
                    "scroll_lenis_stop_inertia_on_navigate",
                ),
                preset_field_id="scroll_lenis_preset",
                custom_preset_value="custom",
            ),
        ),
    ),
    TemplateZone(
        zone_id="scroll_story",
        label="Animacja przewijana",
        description=(
            "Treści wyświetlane nad sekwencją 60 FPS. Znak | w nagłówku "
            "rozpoczyna nową linię. Sam film podmienisz w panelu nad edytorem."
        ),
        section_key="media_with_content_D7REjd",
        fields=(
            TemplateField(
                "scroll_video_engine",
                "Sposób odtwarzania",
                "choice",
                _media_setting("scroll_video_engine"),
                choices=(
                    ("video", "Film — natywny odtwarzacz"),
                    ("frames", "Klatki — sekwencja WebP"),
                ),
                hint="Wybierz wariant przygotowany w panelu wgrywania.",
            ),
            TemplateField(
                "scroll_video_quality",
                "Jakość wyświetlania",
                "choice",
                _media_setting("scroll_video_quality"),
                choices=(
                    ("720p", "720p — najwyższa płynność"),
                    ("1080p", "1080p — Full HD"),
                ),
                hint=(
                    "Rozdzielczość działa niezależnie dla filmu i klatek WebP."
                ),
            ),
            TemplateField(
                "scroll_video_container",
                "Format filmu",
                "choice",
                _media_setting("scroll_video_container"),
                choices=(
                    ("mp4", "MP4 H.264 — najwyższa zgodność"),
                    ("webm", "WebM — gotowy plik, możliwa alfa"),
                ),
                hint=(
                    "Dotyczy trybu Film. Wybierz format przygotowany w panelu "
                    "wgrywania; klatki WebP ignorują to ustawienie."
                ),
            ),
            TemplateField(
                "scroll_video_source",
                "Konkretny plik",
                "choice",
                _media_setting("scroll_video_source"),
                hint=(
                    "Lista pokazuje pliki zgodne z wybranym formatem i jakością. "
                    "Domyślny slot zachowuje dotychczasowe działanie."
                ),
                choice_provider=_philosophy_video_choices,
                choice_dependencies=(
                    "scroll_video_engine",
                    "scroll_video_quality",
                    "scroll_video_container",
                ),
                visible_when=(
                    ("scroll_video_engine", ("video",)),
                ),
            ),
            TemplateField(
                "scroll_intro_title",
                "Nagłówek początkowy",
                "text",
                _media_setting("scroll_intro_title"),
                hint="Przykład: FILOZOFIA|MARKI",
            ),
            TemplateField(
                "scroll_intro_subtitle",
                "Podtytuł początkowy",
                "body",
                _media_setting("scroll_intro_subtitle"),
            ),
            TemplateField(
                "scroll_intro_pin_vh",
                "Przypięcie nagłówka początkowego",
                "int",
                _media_setting("scroll_intro_pin_vh"),
                min_value=10,
                max_value=300,
                step=5,
                unit="vh",
                hint=(
                    "Jak długo nagłówek z podtytułem pozostaje przypięty "
                    "podczas scrolla, zanim zejdzie razem z przewijaniem."
                ),
            ),
            TemplateField(
                "scroll_intro_fade_start_vh",
                "Start znikania nagłówka początkowego",
                "int",
                _media_setting("scroll_intro_fade_start_vh"),
                min_value=0,
                max_value=300,
                step=5,
                unit="vh",
                hint=(
                    "Po ilu vh przewijania nagłówek zaczyna znikać. "
                    "Jeśli przypięcie jest dłuższe, znikanie zacznie się "
                    "dopiero po jego zakończeniu."
                ),
            ),
            TemplateField(
                "scroll_outro_text",
                "Tekst na końcowej klatce",
                "body",
                _media_setting("scroll_outro_text"),
            ),
            TemplateField(
                "scroll_outro_appear_percent",
                "Pojawienie się tekstu końcowego",
                "int",
                _media_setting("scroll_outro_appear_percent"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                hint=(
                    "W którym momencie animacji filmu pojawia się tekst "
                    "końcowy (0% = start, 100% = końcowa klatka)."
                ),
            ),
            TemplateField(
                "scroll_outro_pin_vh",
                "Przypięcie tekstu końcowego",
                "int",
                _media_setting("scroll_outro_pin_vh"),
                min_value=10,
                max_value=300,
                step=5,
                unit="vh",
                hint=(
                    "Jak długo tekst końcowy pozostaje przypięty po pojawieniu "
                    "się, zanim zejdzie razem z przewijaniem."
                ),
            ),
            TemplateField(
                "scroll_video_viewport",
                "Długość przewijania animacji",
                "int",
                _media_setting("scroll_video_viewport"),
                min_value=200,
                max_value=1500,
                step=25,
                unit="vh",
                hint="400vh odpowiada aktualnej stronie.",
            ),
            TemplateField(
                "scroll_video_fit",
                "Dopasowanie kadru",
                "choice",
                _media_setting("video_position"),
                choices=(
                    ("cover", "Wypełnij kadr"),
                    ("contain", "Pokaż całą klatkę"),
                ),
            ),
        ),
    ),
    TemplateZone(
        zone_id="scroll_motion",
        label="Charakter odtwarzania",
        description=(
            "Profil ruchu jest wspólny dla filmu i klatek oraz dla 720p/1080p. "
            "Preset ustawia wszystkie wartości. Ręczna zmiana przełącza profil "
            "na Własne ustawienia; dokładny powrót rozpoznaje preset ponownie."
        ),
        section_key="media_with_content_D7REjd",
        preset_field_id="scroll_motion_preset",
        preset_values=preset_values(),
        custom_preset_value="custom",
        recommended_preset_value="luxury",
        fields=(
            TemplateField(
                "scroll_motion_preset",
                "Preset",
                "choice",
                _media_setting("scroll_motion_preset"),
                choices=preset_choices(),
                hint="Gotowy charakter ruchu; zalecany dla tej strony: Delikatny luksusowy.",
            ),
            TemplateField(
                "scroll_motion_speed",
                "Tempo",
                "float",
                _media_setting("scroll_motion_speed"),
                min_value=0.25,
                max_value=3.0,
                step=0.05,
                hint=(
                    "Określa, jak szybko materiał przechodzi od początku do końca "
                    "względem przewijania."
                ),
            ),
            TemplateField(
                "scroll_motion_easing",
                "Easing",
                "choice",
                _media_setting("scroll_motion_easing"),
                choices=(
                    ("linear", "Linear"),
                    ("ease-in", "Ease In"),
                    ("ease-out", "Ease Out"),
                    ("ease-in-out", "Ease In-Out"),
                    ("sine-in-out", "Sine In-Out"),
                    ("quad-in-out", "Quad In-Out"),
                    ("cubic-in-out", "Cubic In-Out"),
                    ("quart-in-out", "Quart In-Out"),
                    ("expo-in-out", "Expo In-Out"),
                    ("smoothstep", "Smoothstep"),
                    ("smootherstep", "Smootherstep"),
                    ("custom-bezier", "Custom Cubic Bézier"),
                ),
                hint="Zmienia tempo ruchu na początku, w środku i na końcu sekcji.",
            ),
            TemplateField(
                "scroll_motion_bezier",
                "Custom Cubic Bézier",
                "text",
                _media_setting("scroll_motion_bezier"),
                hint="Cztery liczby x1,y1,x2,y2, np. 0.25,0.10,0.25,1.00.",
            ),
            TemplateField(
                "scroll_motion_smoothing_ms",
                "Wygładzanie",
                "int",
                _media_setting("scroll_motion_smoothing_ms"),
                min_value=0,
                max_value=1000,
                step=10,
                unit=" ms",
                hint="Łagodzi nagłe zmiany pozycji animacji; obliczenia używają deltaTime.",
            ),
            TemplateField(
                "scroll_motion_lag_ms",
                "Lag",
                "int",
                _media_setting("scroll_motion_lag_ms"),
                min_value=0,
                max_value=500,
                step=5,
                unit=" ms",
                hint="Kontrolowane opóźnienie reakcji bez timeoutów i kolejki zdarzeń.",
            ),
            TemplateField(
                "scroll_motion_inertia",
                "Bezwładność",
                "int",
                _media_setting("scroll_motion_inertia"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                hint="Powoduje miękkie wyhamowanie po zmianie prędkości scrolla.",
            ),
            TemplateField(
                "scroll_motion_damping",
                "Tłumienie",
                "int",
                _media_setting("scroll_motion_damping"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                hint="Wysoka wartość usuwa sprężynowanie i oscylacje.",
            ),
            TemplateField(
                "scroll_motion_max_catchup",
                "Maksymalna prędkość nadrabiania",
                "float",
                _media_setting("scroll_motion_max_catchup"),
                min_value=0,
                max_value=8,
                step=0.05,
                unit=" /s",
                hint="Postęp na sekundę; 0 oznacza brak limitu.",
            ),
            TemplateField(
                "scroll_motion_stop_behavior",
                "Po zatrzymaniu scrolla",
                "choice",
                _media_setting("scroll_motion_stop_behavior"),
                choices=(
                    ("immediate", "Zatrzymaj natychmiast"),
                    ("reach", "Płynnie dojdź do celu"),
                    ("nearest-frame", "Dokończ do najbliższej klatki"),
                    ("decelerate", "Delikatnie wyhamuj"),
                    ("snap", "Snap do najbliższego punktu"),
                ),
            ),
            TemplateField(
                "scroll_motion_snap_points",
                "Liczba punktów snap",
                "int",
                _media_setting("scroll_motion_snap_points"),
                min_value=2,
                max_value=20,
                step=1,
            ),
            TemplateField(
                "scroll_motion_direction",
                "Kierunek",
                "choice",
                _media_setting("scroll_motion_direction"),
                choices=(("normal", "Normalny"), ("reverse", "Odwrócony")),
            ),
            TemplateField(
                "scroll_motion_material_start",
                "Początek materiału",
                "int",
                _media_setting("scroll_motion_material_start"),
                min_value=0,
                max_value=99,
                step=1,
                unit="%",
            ),
            TemplateField(
                "scroll_motion_material_end",
                "Koniec materiału",
                "int",
                _media_setting("scroll_motion_material_end"),
                min_value=1,
                max_value=100,
                step=1,
                unit="%",
            ),
            TemplateField(
                "scroll_motion_interpolation",
                "Interpolacja postępu",
                "choice",
                _media_setting("scroll_motion_interpolation"),
                choices=(
                    ("none", "Brak — natychmiast"),
                    ("linear", "Linear"),
                    ("exponential", "Exponential smoothing"),
                    ("damp", "Damp"),
                    ("spring", "Spring"),
                    ("velocity", "Velocity-based"),
                ),
                hint="WebP interpoluje postęp, nie miesza kosztownie dwóch bitmap.",
            ),
            TemplateField(
                "scroll_motion_tail_pacing",
                "Płynne domknięcie hamowania",
                "bool",
                _media_setting("scroll_motion_tail_pacing"),
                hint=(
                    "W końcowej fazie pokazuje sąsiednie klatki 60 FPS w równym "
                    "rytmie, zamiast długo zatrzymywać obraz i nagle przeskakiwać."
                ),
            ),
            TemplateField(
                "scroll_motion_tail_window_frames",
                "Zakres płynnego domknięcia",
                "int",
                _media_setting("scroll_motion_tail_window_frames"),
                min_value=2,
                max_value=30,
                step=1,
                unit=" kl.",
                hint="Liczba końcowych klatek objętych stabilnym frame pacingiem.",
            ),
            TemplateField(
                "scroll_motion_frame_rounding",
                "Wybór klatki WebP",
                "choice",
                _media_setting("scroll_motion_frame_rounding"),
                choices=(("floor", "Floor"), ("round", "Round"), ("ceil", "Ceil")),
            ),
            TemplateField(
                "scroll_motion_mp4_dead_zone_ms",
                "Martwa strefa filmu (MP4/WebM)",
                "int",
                _media_setting("scroll_motion_mp4_dead_zone_ms"),
                min_value=0,
                max_value=100,
                step=1,
                unit=" ms",
            ),
            TemplateField(
                "scroll_motion_webp_dead_zone_frames",
                "Martwa strefa WebP",
                "int",
                _media_setting("scroll_motion_webp_dead_zone_frames"),
                min_value=0,
                max_value=10,
                step=1,
                unit=" kl.",
            ),
            TemplateField(
                "scroll_motion_preload_radius",
                "Promień preloadu WebP",
                "int",
                _media_setting("scroll_motion_preload_radius"),
                min_value=2,
                max_value=60,
                step=1,
                unit=" kl.",
            ),
            TemplateField(
                "scroll_motion_cache_frames",
                "Limit cache bitmap",
                "int",
                _media_setting("scroll_motion_cache_frames"),
                min_value=0,
                max_value=120,
                step=2,
                unit=" kl.",
                hint="0 dobiera limit automatycznie do pamięci i rozdzielczości.",
            ),
        ),
    ),
    TemplateZone(
        zone_id="scroll_alpha",
        label="Przezroczystość i tło",
        description=(
            "Klatki WebP zachowują RGBA. MP4 H.264 nie przenosi kanału alfa i "
            "korzysta z jawnego tła fallbacku."
        ),
        section_key="media_with_content_D7REjd",
        fields=(
            TemplateField(
                "scroll_preserve_alpha",
                "Zachowaj kanał alfa",
                "bool",
                _media_setting("scroll_preserve_alpha"),
                hint="Włączone domyślnie; generator WebP nie spłaszcza przezroczystości.",
            ),
            TemplateField(
                "scroll_background_mode",
                "Tryb tła",
                "choice",
                _media_setting("scroll_background_mode"),
                choices=(
                    ("auto", "Auto"),
                    ("transparent", "Przezroczyste"),
                    ("color", "Kolor"),
                    ("gradient", "Gradient"),
                    ("image", "Obraz (CSS url)"),
                    ("asset", "Plik tła — obraz"),
                    ("webm", "Plik tła — WebM + alfa"),
                ),
            ),
            TemplateField(
                "scroll_background_value",
                "Kolor / gradient / obraz fallbacku",
                "text",
                _media_setting("scroll_background_value"),
                hint="Np. #000000 albo linear-gradient(180deg,#000,#181818).",
            ),
            TemplateField(
                "scroll_alpha_diagnostics",
                "Diagnostyka krawędzi alfa",
                "bool",
                _media_setting("scroll_alpha_diagnostics"),
            ),
            TemplateField(
                "scroll_force_transparent",
                "Wymuś wariant przezroczysty",
                "bool",
                _media_setting("scroll_force_transparent"),
                hint=(
                    "Gdy aktywne, runtime wymaga WebM lub sekwencji WebP "
                    "z potwierdzonym kanałem alfa."
                ),
            ),
        ),
    ),
)

_SCROLL_MOTION = next(zone for zone in PAGE_ZONES if zone.zone_id == "scroll_motion")
_SCROLL_STORY = next(zone for zone in PAGE_ZONES if zone.zone_id == "scroll_story")
_SCROLL_ALPHA = next(zone for zone in PAGE_ZONES if zone.zone_id == "scroll_alpha")
_SCROLL_ALPHA_FIELDS_GROUPED = tuple(
    replace(
        field,
        group_id="film_scroll_background",
        group_label="Ustawienia tła",
        group_collapsed=True,
    )
    for field in _SCROLL_ALPHA.fields
)
_SCROLL_MOTION_FIELDS_GROUPED = tuple(
    replace(
        field,
        group_id="film_scroll_motion",
        group_label="Charakter odtwarzania",
        group_collapsed=True,
    )
    for field in _SCROLL_MOTION.fields
)
PAGE_ZONES = tuple(
    replace(
        zone,
        description=(
            f"{zone.description} Ustawienia tła i charakter ruchu są dostępne "
            "w zwijanych grupach poniżej."
        ),
        fields=(
            *_SCROLL_ALPHA_FIELDS_GROUPED,
            *zone.fields,
            *_SCROLL_MOTION_FIELDS_GROUPED,
        ),
        preset_field_id=_SCROLL_MOTION.preset_field_id,
        preset_values=_SCROLL_MOTION.preset_values,
        custom_preset_value=_SCROLL_MOTION.custom_preset_value,
        recommended_preset_value=_SCROLL_MOTION.recommended_preset_value,
    )
    if zone.zone_id == _SCROLL_STORY.zone_id
    else zone
    for zone in PAGE_ZONES
    if zone.zone_id not in {
        _SCROLL_MOTION.zone_id,
        _SCROLL_ALPHA.zone_id,
    }
)

_WROTA_STORY_FIELDS = (
    TemplateField(
        "wrota_scroll_video_engine",
        "Sposób odtwarzania",
        "choice",
        _wrota_setting("scroll_video_engine"),
        choices=(
            ("video", "Film — natywny odtwarzacz"),
            ("frames", "Klatki — sekwencja WebP"),
        ),
        hint="Domyślnie Film MP4 (portal Wrota).",
    ),
    TemplateField(
        "wrota_scroll_video_quality",
        "Jakość wyświetlania",
        "choice",
        _wrota_setting("scroll_video_quality"),
        choices=(
            ("720p", "720p — najwyższa płynność"),
            ("1080p", "1080p — Full HD"),
        ),
    ),
    TemplateField(
        "wrota_scroll_video_container",
        "Format filmu",
        "choice",
        _wrota_setting("scroll_video_container"),
        choices=(
            ("mp4", "MP4 H.264 — najwyższa zgodność"),
            ("webm", "WebM — gotowy plik, możliwa alfa"),
        ),
        hint="Dotyczy trybu Film; wybierz wcześniej przygotowany wariant.",
    ),
    TemplateField(
        "wrota_scroll_video_source",
        "Konkretny plik",
        "choice",
        _wrota_setting("scroll_video_source"),
        hint=(
            "Lista pokazuje pliki Wrota zgodne z wybranym formatem i jakością."
        ),
        choice_provider=_wrota_video_choices,
        choice_dependencies=(
            "wrota_scroll_video_engine",
            "wrota_scroll_video_quality",
            "wrota_scroll_video_container",
        ),
        visible_when=(
            ("wrota_scroll_video_engine", ("video",)),
        ),
    ),
    TemplateField(
        "wrota_scroll_video_viewport",
        "Długość przewijania animacji",
        "int",
        _wrota_setting("scroll_video_viewport"),
        min_value=200,
        max_value=1500,
        step=25,
        unit="vh",
        hint="Portal otwiera się na początku sekcji; potem scrub filmu.",
    ),
    TemplateField(
        "wrota_scroll_video_fit",
        "Dopasowanie kadru",
        "choice",
        _wrota_setting("video_position"),
        choices=(
            ("cover", "Wypełnij kadr"),
            ("contain", "Pokaż całą klatkę"),
        ),
    ),
)

_WROTA_MOTION_FIELDS_GROUPED = tuple(
    replace(
        field,
        group_id="film_scroll_motion_wrota",
        group_label="Charakter odtwarzania",
        group_collapsed=True,
    )
    for field in _remap_fields_to_section(
        _SCROLL_MOTION.fields,
        from_section="media_with_content_D7REjd",
        to_section="media_with_content_Wrota",
    )
)

PAGE_ZONES = PAGE_ZONES + (
    TemplateZone(
        zone_id="quote_screen",
        label="Ekran cytatu",
        description=(
            "Sticky ekran z cytatem przed portalem Wrota. "
            "Możesz wstawić własne tło obrazkowe oraz ustawić przezroczystość "
            "pasa tekstu i paddingu separatorów."
        ),
        section_key="section_tAj94h",
        settings_only=True,
        fields=(
            TemplateField(
                "fm_quote_text_bg_opacity",
                "Tło tekstu",
                "int",
                _quote_setting("fm_quote_text_bg_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
            TemplateField(
                "fm_quote_divider_top_above_opacity",
                "Górny separator — nad kreską",
                "int",
                _quote_setting("fm_quote_divider_top_above_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
            TemplateField(
                "fm_quote_divider_top_below_opacity",
                "Górny separator — pod kreską",
                "int",
                _quote_setting("fm_quote_divider_top_below_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
            TemplateField(
                "fm_quote_divider_bottom_above_opacity",
                "Dolny separator — nad kreską",
                "int",
                _quote_setting("fm_quote_divider_bottom_above_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
            TemplateField(
                "fm_quote_divider_bottom_below_opacity",
                "Dolny separator — pod kreską",
                "int",
                _quote_setting("fm_quote_divider_bottom_below_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
            TemplateField(
                "fm_quote_bg_parallax_enabled",
                "Paralaksa tła (mysz, desktop)",
                "bool",
                _quote_setting("fm_quote_bg_parallax_enabled"),
                visible_when=(("_quote_screen_internal", ("show",)),),
            ),
        ),
    ),
    TemplateZone(
        zone_id="scroll_story_wrota",
        label="Portal Wrota — animacja",
        description=(
            "Druga animacja Film-scroll za portalem ionowym (po cytacie). "
            "Źródło filmu podmienisz w panelu „Wrota” nad edytorem. "
            "Charakter ruchu jest dostępny w zwijanej grupie poniżej."
        ),
        section_key="media_with_content_Wrota",
        fields=(*_WROTA_STORY_FIELDS, *_WROTA_MOTION_FIELDS_GROUPED),
        preset_field_id="scroll_motion_preset",
        preset_values=preset_values(),
        custom_preset_value="custom",
        recommended_preset_value="luxury",
    ),
    TemplateZone(
        zone_id="wrota_parallax",
        label="Tło paralaksy — po Wrotach",
        description=(
            "Po końcówce filmu Wrota pojawia się tło Bottom "
            "(paralaksa pod kursorem)."
        ),
        section_key="media_with_content_Wrota",
        settings_only=True,
        fields=(
            TemplateField(
                "fm_bg_parallax_enabled",
                "Paralaksa tła",
                "bool",
                _wrota_setting("fm_bg_parallax_enabled"),
                # Ukryte w generycznym rendererze — checkbox rysuje panel strefy.
                visible_when=(("_wrota_parallax_internal", ("show",)),),
            ),
        ),
    ),
    TemplateZone(
        zone_id="before_after_gallery",
        label="Przed i po",
        description=(
            "Galeria porównań wyświetlana po dwóch tekstach na tle paralaksy. "
            "Każdy slajd ma osobny obraz „Przed” i „Po”, a po ostatnim "
            "następuje crossfade z powrotem do samej paralaksy Bottom."
        ),
        section_key="media_with_content_Wrota",
        settings_only=True,
        fields=(
            TemplateField(
                "before_after_count",
                "Liczba obrazów w galerii",
                "int",
                _wrota_setting("before_after_count"),
                min_value=0,
                max_value=12,
                step=1,
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_motion_blur",
                "Efekt smużenia kart",
                "bool",
                _wrota_setting("before_after_motion_blur"),
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_film_grain",
                "Animowane filmowe ziarno",
                "bool",
                _wrota_setting("before_after_film_grain"),
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_bg_transparent",
                "Przezroczystość tła",
                "bool",
                _wrota_setting("before_after_bg_transparent"),
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_preserve_prev_bg",
                "Zachowaj winietę i efekty tła z poprzedniego ekranu",
                "bool",
                _wrota_setting("before_after_preserve_prev_bg"),
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_bg_radial_opacity",
                "Tło — radialny blob",
                "int",
                _wrota_setting("before_after_bg_radial_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_bg_linear_opacity",
                "Tło — liniowy gradient",
                "int",
                _wrota_setting("before_after_bg_linear_opacity"),
                min_value=0,
                max_value=100,
                step=1,
                unit="%",
                visible_when=(("_before_after_internal", ("show",)),),
            ),
            TemplateField(
                "before_after_texts_json",
                "Teksty galerii",
                "text",
                _wrota_setting("before_after_texts_json"),
                visible_when=(("_before_after_internal", ("show",)),),
            ),
        ),
    ),
)


__all__ = ["PAGE_ZONES"]
