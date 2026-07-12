"""Konfiguracja efektów sekcji «Giclée Art — intro» (homepage).

Zapis per wariant: data/variants/<id>/studio-reveal.json.
Eksport: write_home_assets() → window.GICLEE_HOME_STUDIO_REVEAL_CONFIG
→ assets/giclee-home-sections-boot.js + giclee-home-studio-reveal.css.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from .homepage_variants import variant_file_path
from .service import _data_dir

_LEGACY_DATA_DIR = _data_dir()

GRADIENT_PRESETS: tuple[str, ...] = (
    "none",
    "editorial",
    "menu_wide",
    "menu_narrow",
    "radial_spot",
)

EASING_BEZIER: dict[str, str] = {
    "museum": "0.16, 1, 0.3, 1",
    "soft": "0.25, 1, 0.5, 1",
    "crisp": "0.22, 1, 0.36, 1",
}

PRESET_CUSTOM_LABEL = "— własne —"

STUDIO_REVEAL_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "desktopEnabled": True,
    "revealThreshold": 0.25,
    "durationMs": 980,
    "cardDurationMs": 1100,
    "textDurationMs": 900,
    "hoverDurationMs": 850,
    "headingDelayMs": 120,
    "paragraphStaggerMs": 140,
    "bgBrightnessStart": 88,
    "lightOpacityMin": 5.5,
    "lightOpacityMax": 11,
    "cardHoverScale": 1.018,
    "cardImageHoverScale": 1.025,
    "copyHoverScale": 1.022,
    "copyHoverTranslateY": -4,
    "glowEnabled": True,
    "easing": "museum",
    "gradientPreset": "editorial",
    "gradientOverlayOpacity": 100,
    "radialCenterX": 35,
    "radialCenterY": 50,
    "radialRadiusX": 55,
    "radialRadiusY": 85,
    "radialFeather": 50,
    "radialExposure": 50,
    "parallaxEnabled": True,
    "parallaxMaxX": 18,
    "parallaxMaxY": 12,
    "parallaxEase": 0.075,
    "parallaxOverscan": 106,
}

_INT_LIMITS: dict[str, tuple[int, int]] = {
    "durationMs": (400, 1600),
    "cardDurationMs": (400, 1800),
    "textDurationMs": (400, 1600),
    "hoverDurationMs": (400, 1400),
    "headingDelayMs": (0, 600),
    "paragraphStaggerMs": (0, 400),
    "bgBrightnessStart": (50, 100),
    "copyHoverTranslateY": (-12, 0),
    "gradientOverlayOpacity": (0, 100),
    "radialCenterX": (0, 100),
    "radialCenterY": (0, 100),
    "radialRadiusX": (20, 120),
    "radialRadiusY": (20, 120),
    "radialFeather": (0, 100),
    "radialExposure": (0, 100),
    "parallaxMaxX": (0, 40),
    "parallaxMaxY": (0, 28),
    "parallaxOverscan": (100, 112),
}

_FLOAT_LIMITS: dict[str, tuple[float, float]] = {
    "revealThreshold": (0.05, 1.0),
    "lightOpacityMin": (0.0, 20.0),
    "lightOpacityMax": (0.0, 20.0),
    "cardHoverScale": (1.0, 1.05),
    "cardImageHoverScale": (1.0, 1.08),
    "copyHoverScale": (1.0, 1.05),
    "parallaxEase": (0.03, 0.15),
}

STUDIO_REVEAL_PRESETS: dict[str, dict[str, Any]] = {
    "Muzealny studio (domyślny)": {},
    "Spokojniejszy reveal": {
        "cardDurationMs": 1250,
        "textDurationMs": 1000,
        "paragraphStaggerMs": 160,
        "cardHoverScale": 1.012,
        "copyHoverScale": 1.016,
        "lightOpacityMin": 4.0,
        "lightOpacityMax": 8.0,
        "easing": "soft",
    },
    "Wyraźniejszy parallax": {
        "parallaxMaxX": 26,
        "parallaxMaxY": 16,
        "parallaxOverscan": 1.08,
        "gradientPreset": "editorial",
        "cardHoverScale": 1.022,
    },
    "Gradient BIO szeroki": {
        "gradientPreset": "menu_wide",
        "gradientOverlayOpacity": 92,
        "parallaxEnabled": False,
        "lightOpacityMax": 8.0,
    },
    "Bez efektów": {
        "enabled": False,
        "parallaxEnabled": False,
        "gradientPreset": "none",
        "glowEnabled": False,
    },
}


def apply_studio_reveal_preset(name: str) -> dict[str, Any]:
    merged = dict(STUDIO_REVEAL_DEFAULTS)
    merged.update(STUDIO_REVEAL_PRESETS.get(name, {}))
    return normalize_studio_reveal_config(merged)


def studio_reveal_config_path(variant_id: str, *, for_write: bool = False) -> Path:
    current = _data_dir()
    if current != _LEGACY_DATA_DIR:
        return current / "variants" / variant_id / "studio-reveal.json"
    return variant_file_path(variant_id, "studio-reveal.json", for_write=for_write)


def normalize_studio_reveal_config(raw: Any) -> dict[str, Any]:
    cfg = dict(STUDIO_REVEAL_DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key in STUDIO_REVEAL_DEFAULTS:
        if key in raw:
            cfg[key] = raw[key]
    cfg["enabled"] = bool(cfg["enabled"])
    cfg["desktopEnabled"] = bool(cfg["desktopEnabled"])
    cfg["glowEnabled"] = bool(cfg["glowEnabled"])
    cfg["parallaxEnabled"] = bool(cfg["parallaxEnabled"])
    preset = str(cfg.get("gradientPreset") or "none").strip().lower()
    if preset not in GRADIENT_PRESETS:
        preset = "editorial"
    cfg["gradientPreset"] = preset
    easing = str(cfg.get("easing") or "museum").strip().lower()
    if easing not in EASING_BEZIER:
        easing = "museum"
    cfg["easing"] = easing
    for key in _INT_LIMITS:
        try:
            cfg[key] = int(cfg[key])
        except (TypeError, ValueError):
            cfg[key] = STUDIO_REVEAL_DEFAULTS[key]
        lo, hi = _INT_LIMITS[key]
        cfg[key] = max(lo, min(hi, cfg[key]))
    for key in _FLOAT_LIMITS:
        try:
            cfg[key] = float(cfg[key])
        except (TypeError, ValueError):
            cfg[key] = STUDIO_REVEAL_DEFAULTS[key]
        lo, hi = _FLOAT_LIMITS[key]
        cfg[key] = max(lo, min(hi, cfg[key]))
    if cfg["lightOpacityMax"] < cfg["lightOpacityMin"]:
        cfg["lightOpacityMin"], cfg["lightOpacityMax"] = cfg["lightOpacityMax"], cfg["lightOpacityMin"]
    return cfg


def validate_studio_reveal_config(cfg: dict[str, Any]) -> list[str]:
    normalized = normalize_studio_reveal_config(cfg)
    errors: list[str] = []
    if normalized["gradientPreset"] not in GRADIENT_PRESETS:
        errors.append(f"gradientPreset: dozwolone {', '.join(GRADIENT_PRESETS)}")
    return errors


def load_studio_reveal_config(variant_id: str) -> dict[str, Any]:
    path = studio_reveal_config_path(variant_id)
    if not path.is_file():
        return dict(STUDIO_REVEAL_DEFAULTS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(STUDIO_REVEAL_DEFAULTS)
    return normalize_studio_reveal_config(raw)


def save_studio_reveal_config(variant_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_studio_reveal_config(cfg)
    errors = validate_studio_reveal_config(normalized)
    if errors:
        raise ValueError("\n".join(errors))
    path = studio_reveal_config_path(variant_id, for_write=True)
    atomic_write_text(path, json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    return normalized


def export_studio_reveal_config(cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_studio_reveal_config(cfg)
    out = dict(normalized)
    out["easingBezier"] = EASING_BEZIER.get(str(normalized["easing"]), EASING_BEZIER["museum"])
    out["parallaxOverscan"] = round(normalized["parallaxOverscan"] / 100, 4)
    return out
