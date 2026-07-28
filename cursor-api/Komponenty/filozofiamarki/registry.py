"""Pola faktycznie używane przez stronę Filozofia marki."""

from __future__ import annotations

from dataclasses import replace

from Komponenty._shared.theme_page_editor.types import TemplateField, TemplateZone, _s

from .motion_config import preset_choices, preset_values


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


def _media_setting(name: str) -> tuple[str, ...]:
    return _s(*_MEDIA_SETTINGS, name)


def _wrota_setting(name: str) -> tuple[str, ...]:
    return _s(*_WROTA_MEDIA_SETTINGS, name)


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
                "scroll_outro_text",
                "Tekst na końcowej klatce",
                "body",
                _media_setting("scroll_outro_text"),
            ),
            TemplateField(
                "scroll_video_viewport",
                "Długość przewijania animacji",
                "int",
                _media_setting("scroll_video_viewport"),
                min_value=200,
                max_value=800,
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
                "Martwa strefa MP4",
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
                    ("image", "Obraz strony"),
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
                hint="Gdy aktywne, runtime zgłasza błąd zamiast użyć nieprzezroczystego MP4.",
            ),
        ),
    ),
)

_SCROLL_MOTION = next(zone for zone in PAGE_ZONES if zone.zone_id == "scroll_motion")

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
        "wrota_scroll_video_viewport",
        "Długość przewijania animacji",
        "int",
        _wrota_setting("scroll_video_viewport"),
        min_value=200,
        max_value=800,
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

PAGE_ZONES = PAGE_ZONES + (
    TemplateZone(
        zone_id="scroll_story_wrota",
        label="Portal Wrota — animacja",
        description=(
            "Druga animacja Film-scroll za portalem ionowym (po cytacie). "
            "Źródło filmu podmienisz w panelu „Wrota” nad edytorem."
        ),
        section_key="media_with_content_Wrota",
        fields=_WROTA_STORY_FIELDS,
    ),
    TemplateZone(
        zone_id="scroll_motion_wrota",
        label="Charakter odtwarzania — Wrota",
        description=_SCROLL_MOTION.description,
        section_key="media_with_content_Wrota",
        preset_field_id="scroll_motion_preset",
        preset_values=preset_values(),
        custom_preset_value="custom",
        recommended_preset_value="luxury",
        fields=_remap_fields_to_section(
            _SCROLL_MOTION.fields,
            from_section="media_with_content_D7REjd",
            to_section="media_with_content_Wrota",
        ),
    ),
)


__all__ = ["PAGE_ZONES"]
