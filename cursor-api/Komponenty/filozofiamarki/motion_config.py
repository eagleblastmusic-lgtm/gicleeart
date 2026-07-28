"""Kanoniczny model presetów i walidacji Film-scroll."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ASSET_NAME = "giclee-scroll-motion-presets.json"
FIELD_TO_SETTING = {
    "speed": "scroll_motion_speed",
    "easing": "scroll_motion_easing",
    "bezier": "scroll_motion_bezier",
    "smoothingMs": "scroll_motion_smoothing_ms",
    "lagMs": "scroll_motion_lag_ms",
    "inertia": "scroll_motion_inertia",
    "damping": "scroll_motion_damping",
    "maxCatchUpPerSecond": "scroll_motion_max_catchup",
    "stopBehavior": "scroll_motion_stop_behavior",
    "snapPoints": "scroll_motion_snap_points",
    "direction": "scroll_motion_direction",
    "materialStart": "scroll_motion_material_start",
    "materialEnd": "scroll_motion_material_end",
    "interpolation": "scroll_motion_interpolation",
    "frameRounding": "scroll_motion_frame_rounding",
    "mp4DeadZoneMs": "scroll_motion_mp4_dead_zone_ms",
    "webpDeadZoneFrames": "scroll_motion_webp_dead_zone_frames",
    "preloadRadius": "scroll_motion_preload_radius",
    "cacheFrames": "scroll_motion_cache_frames",
    "tailPacing": "scroll_motion_tail_pacing",
    "tailWindowFrames": "scroll_motion_tail_window_frames",
}


def _theme_root() -> Path:
    return Path(__file__).resolve().parents[3]


def preset_asset_path(root: Path | None = None) -> Path:
    return (root or _theme_root()) / "assets" / ASSET_NAME


def load_motion_catalog(root: Path | None = None) -> dict[str, Any]:
    raw = json.loads(preset_asset_path(root).read_text(encoding="utf-8"))
    if int(raw.get("version") or 0) < 1 or not isinstance(raw.get("presets"), dict):
        raise ValueError("Niepoprawny katalog presetów Film-scroll.")
    return raw


def preset_choices(root: Path | None = None) -> tuple[tuple[str, str], ...]:
    catalog = load_motion_catalog(root)
    values = tuple(
        (preset_id, str(values.get("label") or preset_id))
        for preset_id, values in catalog["presets"].items()
    )
    return values + (("custom", "Własne ustawienia"),)


def preset_values(
    root: Path | None = None,
) -> tuple[tuple[str, tuple[tuple[str, Any], ...]], ...]:
    catalog = load_motion_catalog(root)
    result: list[tuple[str, tuple[tuple[str, Any], ...]]] = []
    for preset_id, values in catalog["presets"].items():
        assignments = tuple(
            (setting, values[source_key])
            for source_key, setting in FIELD_TO_SETTING.items()
        )
        result.append((preset_id, assignments))
    return tuple(result)


def recommended_preset(engine: str, root: Path | None = None) -> str:
    catalog = load_motion_catalog(root)
    recommended = catalog.get("recommended") or {}
    value = str(recommended.get(engine) or "luxury")
    return value if value in catalog["presets"] else "luxury"


def validate_motion_settings(settings: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def number(name: str, minimum: float, maximum: float) -> float:
        try:
            value = float(settings.get(name))
        except (TypeError, ValueError):
            errors.append(f"{name}: wymagana liczba.")
            return minimum
        if not minimum <= value <= maximum:
            errors.append(f"{name}: zakres {minimum}–{maximum}.")
        return value

    number("scroll_motion_speed", 0.25, 3.0)
    number("scroll_motion_smoothing_ms", 0, 1000)
    number("scroll_motion_lag_ms", 0, 500)
    number("scroll_motion_inertia", 0, 100)
    number("scroll_motion_damping", 0, 100)
    number("scroll_motion_max_catchup", 0, 8)
    start = number("scroll_motion_material_start", 0, 100)
    end = number("scroll_motion_material_end", 0, 100)
    if end <= start:
        errors.append("Zakres materiału: koniec musi być większy od początku.")
    number("scroll_motion_mp4_dead_zone_ms", 0, 100)
    number("scroll_motion_webp_dead_zone_frames", 0, 10)
    number("scroll_motion_preload_radius", 2, 60)
    number("scroll_motion_cache_frames", 0, 120)
    number("scroll_motion_tail_window_frames", 2, 30)

    bezier = str(settings.get("scroll_motion_bezier") or "")
    try:
        points = [float(value.strip()) for value in bezier.split(",")]
    except ValueError:
        points = []
    if len(points) != 4 or not all(0 <= value <= 1 for value in (points[:1] + points[2:3])):
        errors.append(
            "Custom Cubic Bézier: podaj x1,y1,x2,y2; wartości x muszą być w 0–1."
        )
    return errors


__all__ = [
    "ASSET_NAME",
    "FIELD_TO_SETTING",
    "load_motion_catalog",
    "preset_asset_path",
    "preset_choices",
    "preset_values",
    "recommended_preset",
    "validate_motion_settings",
]
