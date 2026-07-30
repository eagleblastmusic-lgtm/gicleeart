"""Wspólny moduł dodawania sekcji Film-scroll do edytowanych stron."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

from Komponenty.filozofiamarki.motion_config import preset_choices, preset_values
from Komponenty.filozofiamarki.video_sequence import (
    activate_selected_video_sources,
    native_video_source_choices,
    parse_native_video_source_spec,
    sync_scroll_video_shopifyignore,
)

from .config import PageEditorConfig
from .types import FieldKind, TemplateField, TemplateZone, _s


FILM_SCROLL_ASSET_PREFIX = "giclee-film-scroll-"
FILM_SCROLL_ZONE_PREFIX = "film_scroll_"
SHARED_ASSET_FAMILY = "shared"
FILM_SCROLL_DEPLOY_RELPATHS = (
    "assets/giclee-scroll-motion-presets.json",
    "assets/giclee-scroll-scrub-video.js",
    "blocks/_media-without-appearance.liquid",
    "sections/media-with-content.liquid",
    "snippets/media.liquid",
)


def template_supports_film_scroll(template: dict[str, Any]) -> bool:
    return isinstance(template.get("sections"), dict) and isinstance(
        template.get("order"), list
    )


def activate_film_scroll_assets() -> None:
    """Aktywuj źródła wszystkich instancji i odśwież selektywny sync."""

    activate_selected_video_sources()
    sync_scroll_video_shopifyignore()


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (normalized or "film")[:28].rstrip("-")


def _media_settings(section_key: str, name: str) -> tuple[str, ...]:
    return _s(section_key, "blocks", "media", "settings", name)


def _media_block(section: dict[str, Any]) -> dict[str, Any] | None:
    blocks = section.get("blocks")
    if not isinstance(blocks, dict):
        return None
    media = blocks.get("media")
    if not isinstance(media, dict):
        return None
    settings = media.get("settings")
    if not isinstance(settings, dict):
        return None
    return media


def is_dynamic_film_scroll_section(section: object) -> bool:
    if not isinstance(section, dict):
        return False
    media = _media_block(section)
    if media is None:
        return False
    settings = media.get("settings") or {}
    return (
        media.get("type") == "_media-without-appearance"
        and settings.get("media_type") == "scroll_video"
        and str(settings.get("scroll_video_asset") or "").startswith(
            FILM_SCROLL_ASSET_PREFIX
        )
    )


def _default_media_settings(asset_id: str) -> dict[str, Any]:
    return {
        "media_type": "scroll_video",
        "image": "",
        "link": "",
        "video_loop": True,
        "video_autoplay": False,
        "scroll_video_asset": asset_id,
        "scroll_video_engine": "video",
        "scroll_video_container": "webm",
        "scroll_video_source": "",
        "scroll_video_quality": "1080p",
        "scroll_intro_title": "",
        "scroll_intro_subtitle": "",
        "scroll_outro_text": "",
        "scroll_motion_preset": "direct",
        "scroll_motion_speed": 1.0,
        "scroll_motion_easing": "linear",
        "scroll_motion_bezier": "0.25,0.10,0.25,1.00",
        "scroll_motion_smoothing_ms": 0,
        "scroll_motion_lag_ms": 0,
        "scroll_motion_inertia": 0,
        "scroll_motion_damping": 100,
        "scroll_motion_max_catchup": 0.0,
        "scroll_motion_stop_behavior": "immediate",
        "scroll_motion_snap_points": 5,
        "scroll_motion_direction": "normal",
        "scroll_motion_material_start": 0,
        "scroll_motion_material_end": 100,
        "scroll_motion_interpolation": "none",
        "scroll_motion_tail_pacing": False,
        "scroll_motion_tail_window_frames": 12,
        "scroll_motion_frame_rounding": "round",
        "scroll_motion_mp4_dead_zone_ms": 4,
        "scroll_motion_webp_dead_zone_frames": 1,
        "scroll_motion_preload_radius": 12,
        "scroll_motion_cache_frames": 0,
        "scroll_preserve_alpha": True,
        "scroll_background_mode": "auto",
        "scroll_background_value": "#000000",
        "scroll_alpha_diagnostics": False,
        "scroll_force_transparent": False,
        "scroll_video_duration": 4,
        "scroll_video_viewport": 400,
        "image_position": "cover",
        "video_position": "cover",
    }


def add_film_scroll_section(
    template: dict[str, Any],
    *,
    label: str,
    after_section_key: str | None = None,
) -> str:
    """Dodaj kompletny szkielet Shopify i zwróć jego unikalny section key."""

    if not template_supports_film_scroll(template):
        raise ValueError(
            "Ten dokument nie jest szablonem Shopify z listą sections/order."
        )
    clean_label = str(label or "").strip() or "Film-scroll"
    token = uuid4().hex[:7]
    section_key = f"film_scroll_{_slug(clean_label).replace('-', '_')}_{token}"
    asset_id = f"{FILM_SCROLL_ASSET_PREFIX}{token}"
    section = {
        "type": "media-with-content",
        # Nie pokazuj pustej sekcji na stronie. Udany import filmu w panelu
        # automatycznie ją włączy.
        "disabled": True,
        "blocks": {
            "media": {
                "type": "_media-without-appearance",
                "static": True,
                "settings": _default_media_settings(asset_id),
                "blocks": {},
            },
            "content": {
                "type": "_content-without-appearance",
                "static": True,
                "settings": {
                    "horizontal_alignment_flex_direction_column": "center",
                    "vertical_alignment_flex_direction_column": "center",
                    "gap": 24,
                },
                "blocks": {},
                "block_order": [],
            },
        },
        "name": f"Scroll Film — {clean_label}",
        "settings": {
            "media_position": "right",
            "media_width": "medium",
            "media_height": "100svh",
            "section_width": "full-width",
            "extend_media": True,
            "color_scheme": "scheme-1",
            "padding-block-start": 0,
            "padding-block-end": 0,
        },
    }
    sections = template["sections"]
    order = template["order"]
    sections[section_key] = section
    if after_section_key in order:
        order.insert(order.index(after_section_key) + 1, section_key)
    else:
        order.append(section_key)
    return section_key


def _shared_video_choices(values: dict[str, object]) -> tuple[tuple[str, str], ...]:
    return native_video_source_choices(
        values,
        family=SHARED_ASSET_FAMILY,
    )


def _field(
    section_key: str,
    field_id: str,
    label: str,
    kind: FieldKind,
    **kwargs: Any,
) -> TemplateField:
    return TemplateField(
        field_id,
        label,
        kind,
        _media_settings(section_key, field_id),
        **kwargs,
    )


def _motion_field(
    section_key: str,
    field_id: str,
    label: str,
    kind: FieldKind,
    **kwargs: Any,
) -> TemplateField:
    return _field(
        section_key,
        field_id,
        label,
        kind,
        group_id="film_scroll_motion",
        group_label="Charakter odtwarzania",
        group_collapsed=True,
        **kwargs,
    )


def _film_scroll_fields(section_key: str) -> tuple[TemplateField, ...]:
    return (
        _field(
            section_key,
            "scroll_video_engine",
            "Sposób odtwarzania",
            "choice",
            choices=(
                ("video", "Film — MP4 lub WebM"),
                ("frames", "Klatki — sekwencja WebP"),
            ),
        ),
        _field(
            section_key,
            "scroll_video_quality",
            "Jakość wyświetlania",
            "choice",
            choices=(("720p", "720p"), ("1080p", "1080p — Full HD")),
        ),
        _field(
            section_key,
            "scroll_video_container",
            "Format filmu",
            "choice",
            choices=(("mp4", "MP4 H.264"), ("webm", "WebM — możliwa alfa")),
            visible_when=(("scroll_video_engine", ("video",)),),
        ),
        _field(
            section_key,
            "scroll_video_source",
            "Konkretny plik",
            "choice",
            choice_provider=_shared_video_choices,
            choice_dependencies=(
                "scroll_video_engine",
                "scroll_video_quality",
                "scroll_video_container",
            ),
            visible_when=(("scroll_video_engine", ("video",)),),
            hint=(
                "Wybierz przygotowany plik albo użyj przycisku «Przygotuj nowy film»."
            ),
        ),
        _field(
            section_key,
            "scroll_intro_title",
            "Nagłówek początkowy",
            "text",
            hint="Znak | rozpoczyna nową linię.",
        ),
        _field(
            section_key,
            "scroll_intro_subtitle",
            "Podtytuł początkowy",
            "body",
        ),
        _field(
            section_key,
            "scroll_outro_text",
            "Tekst końcowy",
            "body",
        ),
        _field(
            section_key,
            "scroll_video_viewport",
            "Długość przewijania",
            "int",
            min_value=200,
            max_value=1500,
            step=25,
            unit="vh",
        ),
        _field(
            section_key,
            "video_position",
            "Dopasowanie kadru",
            "choice",
            choices=(("cover", "Wypełnij kadr"), ("contain", "Pokaż całość")),
        ),
        _field(
            section_key,
            "scroll_background_mode",
            "Tryb tła",
            "choice",
            choices=(
                ("auto", "Auto"),
                ("transparent", "Przezroczyste"),
                ("color", "Kolor"),
                ("gradient", "Gradient"),
            ),
        ),
        _field(
            section_key,
            "scroll_background_value",
            "Kolor / gradient tła",
            "text",
        ),
        _field(
            section_key,
            "scroll_preserve_alpha",
            "Zachowaj kanał alfa",
            "bool",
        ),
        _field(
            section_key,
            "scroll_force_transparent",
            "Wymuś przezroczystość",
            "bool",
        ),
        _motion_field(
            section_key,
            "scroll_motion_preset",
            "Preset",
            "choice",
            choices=preset_choices(),
        ),
        _motion_field(
            section_key,
            "scroll_motion_speed",
            "Tempo",
            "float",
            min_value=0.25,
            max_value=3.0,
            step=0.05,
        ),
        _motion_field(
            section_key,
            "scroll_motion_easing",
            "Easing",
            "choice",
            choices=(
                ("linear", "Linear"),
                ("ease-in", "Ease In"),
                ("ease-out", "Ease Out"),
                ("ease-in-out", "Ease In-Out"),
                ("sine-in-out", "Sine In-Out"),
                ("cubic-in-out", "Cubic In-Out"),
                ("smootherstep", "Smootherstep"),
                ("custom-bezier", "Custom Cubic Bézier"),
            ),
        ),
        _motion_field(
            section_key,
            "scroll_motion_bezier",
            "Custom Cubic Bézier",
            "text",
        ),
        _motion_field(
            section_key,
            "scroll_motion_smoothing_ms",
            "Wygładzanie",
            "int",
            min_value=0,
            max_value=1000,
            step=10,
            unit=" ms",
        ),
        _motion_field(
            section_key,
            "scroll_motion_lag_ms",
            "Lag",
            "int",
            min_value=0,
            max_value=500,
            step=5,
            unit=" ms",
        ),
        _motion_field(
            section_key,
            "scroll_motion_inertia",
            "Bezwładność",
            "int",
            min_value=0,
            max_value=100,
            unit="%",
        ),
        _motion_field(
            section_key,
            "scroll_motion_damping",
            "Tłumienie",
            "int",
            min_value=0,
            max_value=100,
            unit="%",
        ),
        _motion_field(
            section_key,
            "scroll_motion_max_catchup",
            "Maksymalna prędkość nadrabiania",
            "float",
            min_value=0,
            max_value=8,
            step=0.05,
            unit=" /s",
        ),
        _motion_field(
            section_key,
            "scroll_motion_stop_behavior",
            "Po zatrzymaniu scrolla",
            "choice",
            choices=(
                ("immediate", "Zatrzymaj natychmiast"),
                ("reach", "Płynnie dojdź do celu"),
                ("nearest-frame", "Najbliższa klatka"),
                ("decelerate", "Delikatnie wyhamuj"),
                ("snap", "Snap do punktu"),
            ),
        ),
        _motion_field(
            section_key,
            "scroll_motion_snap_points",
            "Liczba punktów snap",
            "int",
            min_value=2,
            max_value=20,
        ),
        _motion_field(
            section_key,
            "scroll_motion_direction",
            "Kierunek",
            "choice",
            choices=(("normal", "Normalny"), ("reverse", "Odwrócony")),
        ),
        _motion_field(
            section_key,
            "scroll_motion_material_start",
            "Początek materiału",
            "int",
            min_value=0,
            max_value=99,
            unit="%",
        ),
        _motion_field(
            section_key,
            "scroll_motion_material_end",
            "Koniec materiału",
            "int",
            min_value=1,
            max_value=100,
            unit="%",
        ),
        _motion_field(
            section_key,
            "scroll_motion_interpolation",
            "Interpolacja postępu",
            "choice",
            choices=(
                ("none", "Brak"),
                ("linear", "Linear"),
                ("exponential", "Exponential"),
                ("damp", "Damp"),
                ("spring", "Spring"),
                ("velocity", "Velocity"),
            ),
        ),
        _motion_field(
            section_key,
            "scroll_motion_tail_pacing",
            "Płynne domknięcie hamowania",
            "bool",
        ),
        _motion_field(
            section_key,
            "scroll_motion_tail_window_frames",
            "Zakres płynnego domknięcia",
            "int",
            min_value=2,
            max_value=30,
            unit=" kl.",
        ),
        _motion_field(
            section_key,
            "scroll_motion_frame_rounding",
            "Wybór klatki WebP",
            "choice",
            choices=(("floor", "Floor"), ("round", "Round"), ("ceil", "Ceil")),
        ),
        _motion_field(
            section_key,
            "scroll_motion_mp4_dead_zone_ms",
            "Martwa strefa MP4/WebM",
            "int",
            min_value=0,
            max_value=100,
            unit=" ms",
        ),
        _motion_field(
            section_key,
            "scroll_motion_webp_dead_zone_frames",
            "Martwa strefa WebP",
            "int",
            min_value=0,
            max_value=10,
            unit=" kl.",
        ),
        _motion_field(
            section_key,
            "scroll_motion_preload_radius",
            "Promień preloadu WebP",
            "int",
            min_value=2,
            max_value=60,
            unit=" kl.",
        ),
        _motion_field(
            section_key,
            "scroll_motion_cache_frames",
            "Limit cache bitmap",
            "int",
            min_value=0,
            max_value=120,
            step=2,
            unit=" kl.",
        ),
    )


def discover_film_scroll_zones(
    template: dict[str, Any],
    *,
    exclude_section_keys: set[str] | None = None,
) -> tuple[TemplateZone, ...]:
    excluded = exclude_section_keys or set()
    sections = template.get("sections")
    if not isinstance(sections, dict):
        return ()
    result: list[TemplateZone] = []
    for section_key, section in sections.items():
        if section_key in excluded or not is_dynamic_film_scroll_section(section):
            continue
        raw_name = str(section.get("name") or "Scroll Film")
        label = raw_name.split("—", 1)[-1].strip() if "—" in raw_name else raw_name
        result.append(
            TemplateZone(
                zone_id=f"{FILM_SCROLL_ZONE_PREFIX}{section_key}",
                label=f"Scroll Film — {label}",
                description=(
                    "Kompletny moduł Film-scroll. Źródło, treści, tło i charakter "
                    "odtwarzania dotyczą wyłącznie tej instancji."
                ),
                section_key=section_key,
                fields=_film_scroll_fields(section_key),
                preset_field_id="scroll_motion_preset",
                preset_values=preset_values(),
                custom_preset_value="custom",
                recommended_preset_value="luxury",
            )
        )
    return tuple(result)


def config_with_film_scroll_zones(
    config: PageEditorConfig,
    template: dict[str, Any],
) -> PageEditorConfig:
    static_keys = {zone.section_key for zone in config.zones}
    dynamic = discover_film_scroll_zones(
        template,
        exclude_section_keys=static_keys,
    )
    return replace(config, zones=(*config.zones, *dynamic))


def selected_film_scroll_asset_relpaths(
    template: dict[str, Any],
) -> tuple[str, ...]:
    paths: list[str] = []
    sections = template.get("sections")
    if not isinstance(sections, dict):
        return ()
    for section in sections.values():
        if not isinstance(section, dict):
            continue
        media = _media_block(section)
        if media is None:
            continue
        settings = media.get("settings") or {}
        if settings.get("media_type") != "scroll_video":
            continue
        spec = parse_native_video_source_spec(settings.get("scroll_video_source"))
        for key in ("video", "poster", "manifest"):
            name = Path(str(spec.get(key) or "")).name
            if name and name not in {".", ".."}:
                paths.append(f"assets/{name}")
    return tuple(dict.fromkeys(paths))


def template_has_film_scroll(template: dict[str, Any]) -> bool:
    sections = template.get("sections")
    if not isinstance(sections, dict):
        return False
    for section in sections.values():
        if not isinstance(section, dict):
            continue
        media = _media_block(section)
        if media is not None and (media.get("settings") or {}).get(
            "media_type"
        ) == "scroll_video":
            return True
    return False


__all__ = [
    "FILM_SCROLL_ASSET_PREFIX",
    "FILM_SCROLL_DEPLOY_RELPATHS",
    "FILM_SCROLL_ZONE_PREFIX",
    "SHARED_ASSET_FAMILY",
    "activate_film_scroll_assets",
    "add_film_scroll_section",
    "config_with_film_scroll_zones",
    "discover_film_scroll_zones",
    "is_dynamic_film_scroll_section",
    "selected_film_scroll_asset_relpaths",
    "template_has_film_scroll",
    "template_supports_film_scroll",
]
