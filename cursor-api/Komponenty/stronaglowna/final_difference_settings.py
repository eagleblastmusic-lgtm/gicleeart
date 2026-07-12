"""Konfiguracja animacji hover/focus sekcji «Zobacz różnicę» (final homepage).

Zapis per wariant: data/variants/<id>/final-difference.json.
Eksport do motywu: write_home_assets() dopisuje window.GICLEE_HOME_FINAL_DIFFERENCE_CONFIG
do assets/giclee-home-sections.js — front ustawia CSS variables na .giclee-home-final-difference.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from .homepage_variants import variant_file_path
from .service import _data_dir

_LEGACY_DATA_DIR = _data_dir()

EASING_MODES: tuple[str, ...] = ("museum", "soft", "crisp")

EASING_BEZIER: dict[str, str] = {
    "museum": "0.16, 1, 0.3, 1",
    "soft": "0.25, 1, 0.5, 1",
    "crisp": "0.22, 1, 0.36, 1",
}

PRESET_CUSTOM_LABEL = "— własne —"

FINAL_DIFFERENCE_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "desktopEnabled": True,
    "copyScale": 1.062,
    "copyTranslateY": -8,
    "mediaOffsetX": 24,
    "mediaScale": 0.965,
    "mediaBrightness": 82,
    "bgBrightness": 78,
    "bgVeilOpacity": 16,
    "durationMs": 850,
    "easing": "museum",
    "glowEnabled": True,
    "reverseBehavior": False,
}

_INT_LIMITS: dict[str, tuple[int, int]] = {
    "copyTranslateY": (-24, 0),
    "mediaOffsetX": (0, 48),
    "mediaBrightness": (50, 100),
    "bgBrightness": (50, 100),
    "bgVeilOpacity": (0, 40),
    "durationMs": (400, 1600),
}

_FLOAT_LIMITS: dict[str, tuple[float, float]] = {
    "copyScale": (1.0, 1.12),
    "mediaScale": (0.9, 1.0),
}

FINAL_DIFFERENCE_PRESETS: dict[str, dict[str, Any]] = {
    "Muzealny (domyślny)": {},
    "Delikatniejszy": {
        "copyScale": 1.055,
        "copyTranslateY": -6,
        "mediaOffsetX": 18,
        "mediaScale": 0.975,
        "mediaBrightness": 85,
        "bgBrightness": 82,
        "bgVeilOpacity": 10,
        "durationMs": 950,
        "easing": "soft",
    },
    "Wyraźniejszy": {
        "copyScale": 1.07,
        "copyTranslateY": -10,
        "mediaOffsetX": 28,
        "mediaScale": 0.955,
        "mediaBrightness": 78,
        "bgBrightness": 72,
        "bgVeilOpacity": 22,
        "durationMs": 750,
        "easing": "crisp",
    },
}

_BOOL_KEYS = ("enabled", "desktopEnabled", "glowEnabled", "reverseBehavior")


def apply_final_difference_preset(name: str) -> dict[str, Any]:
    merged = dict(FINAL_DIFFERENCE_DEFAULTS)
    merged.update(FINAL_DIFFERENCE_PRESETS.get(name, {}))
    return normalize_final_difference_config(merged)


def final_difference_config_path(variant_id: str, *, for_write: bool = False) -> Path:
    current = _data_dir()
    if current != _LEGACY_DATA_DIR:
        return current / "variants" / variant_id / "final-difference.json"
    return variant_file_path(variant_id, "final-difference.json", for_write=for_write)


def normalize_final_difference_config(raw: Any) -> dict[str, Any]:
    cfg = dict(FINAL_DIFFERENCE_DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key in FINAL_DIFFERENCE_DEFAULTS:
        if key not in raw:
            continue
        value = raw[key]
        if key in _BOOL_KEYS:
            cfg[key] = bool(value)
        elif key in _INT_LIMITS:
            try:
                cfg[key] = int(value)
            except (TypeError, ValueError):
                pass
        elif key in _FLOAT_LIMITS:
            try:
                cfg[key] = float(value)
            except (TypeError, ValueError):
                pass
        elif key == "easing":
            cfg[key] = str(value)
        else:
            cfg[key] = value
    return cfg


def validate_final_difference_config(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, (lo, hi) in _INT_LIMITS.items():
        value = cfg.get(key)
        if not isinstance(value, int):
            errors.append(f"{key}: wymagana liczba całkowita.")
        elif not lo <= value <= hi:
            errors.append(f"{key}: wartość {value} poza zakresem {lo}–{hi}.")
    for key, (lo, hi) in _FLOAT_LIMITS.items():
        value = cfg.get(key)
        if not isinstance(value, (int, float)):
            errors.append(f"{key}: wymagana liczba.")
        elif not lo <= float(value) <= hi:
            errors.append(f"{key}: wartość {value} poza zakresem {lo}–{hi}.")
    if cfg.get("easing") not in EASING_MODES:
        errors.append(f"easing: dozwolone {', '.join(EASING_MODES)}.")
    return errors


def load_final_difference_config(variant_id: str) -> dict[str, Any]:
    path = final_difference_config_path(variant_id)
    if not path.is_file():
        return dict(FINAL_DIFFERENCE_DEFAULTS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(FINAL_DIFFERENCE_DEFAULTS)
    return normalize_final_difference_config(raw)


def save_final_difference_config(variant_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_final_difference_config(cfg)
    errors = validate_final_difference_config(normalized)
    if errors:
        raise ValueError("Nieprawidłowa konfiguracja animacji:\n- " + "\n- ".join(errors))
    path = final_difference_config_path(variant_id, for_write=True)
    atomic_write_text(path, json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    return normalized


def export_final_difference_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """Konfiguracja do eksportu JS (z rozwiązanym cubic-bezier)."""
    normalized = normalize_final_difference_config(cfg)
    easing_key = str(normalized.get("easing") or "museum")
    bezier = EASING_BEZIER.get(easing_key, EASING_BEZIER["museum"])
    out = dict(normalized)
    out["easingBezier"] = bezier
    return out
