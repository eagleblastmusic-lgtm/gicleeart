"""Konfiguracja animacji przewijania strony głównej (homepage section-scroll).

Zapis per wariant: data/variants/<id>/scroll.json.
Eksport do motywu: write_home_assets() dopisuje window.GICLEE_HOME_SCROLL_CONFIG
do assets/giclee-home-sections.js — front czyta obiekt z bezpiecznym fallbackiem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from .homepage_variants import variant_file_path
from .service import _data_dir

_LEGACY_DATA_DIR = _data_dir()

MOBILE_MODES: tuple[str, ...] = ("native", "soft", "disabled")
REDUCED_MOTION_MODES: tuple[str, ...] = ("instant", "off")

SCROLL_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "desktopEnabled": True,
    "mobileMode": "native",
    "minDuration": 650,
    "maxDuration": 1100,
    "wheelThreshold": 40,
    "touchThreshold": 48,
    "headerOffset": None,
    "headerOffsetExtra": 24,
    "separatorOffset": 8,
    "motionDynamics": 50,
    "reducedMotionMode": "instant",
    "headingSettle": True,
    "debug": False,
}

_INT_LIMITS: dict[str, tuple[int, int]] = {
    "minDuration": (200, 3000),
    "maxDuration": (200, 4000),
    "wheelThreshold": (5, 400),
    "touchThreshold": (5, 400),
    "headerOffsetExtra": (0, 200),
    "separatorOffset": (0, 120),
    "motionDynamics": (0, 100),
}

PRESET_CUSTOM_LABEL = "— własne —"

SCROLL_PRESETS: dict[str, dict[str, Any]] = {
    "Galeria (domyślny)": {},
    "Editorial — kontemplacyjny": {
        "minDuration": 850,
        "maxDuration": 1400,
        "wheelThreshold": 55,
        "motionDynamics": 25,
    },
    "Kinowy": {
        "minDuration": 950,
        "maxDuration": 1600,
        "wheelThreshold": 60,
        "motionDynamics": 15,
        "headingSettle": True,
    },
    "Dynamiczny premium": {
        "minDuration": 480,
        "maxDuration": 820,
        "wheelThreshold": 30,
        "motionDynamics": 85,
    },
    "Miękki editorial": {
        "minDuration": 700,
        "maxDuration": 1150,
        "wheelThreshold": 45,
        "motionDynamics": 40,
    },
    "GPT": {
        "minDuration": 650,
        "maxDuration": 1050,
        "wheelThreshold": 60,
        "motionDynamics": 32,
    },
}


def apply_scroll_preset(name: str) -> dict[str, Any]:
    """Zwraca pełną konfigurację po nałożeniu presetu na domyślne wartości."""
    merged = dict(SCROLL_DEFAULTS)
    overrides = SCROLL_PRESETS.get(name, {})
    merged.update(overrides)
    return normalize_scroll_config(merged)

_BOOL_KEYS = ("enabled", "desktopEnabled", "headingSettle", "debug")


def scroll_config_path(variant_id: str, *, for_write: bool = False) -> Path:
    current = _data_dir()
    if current != _LEGACY_DATA_DIR:
        return current / "variants" / variant_id / "scroll.json"
    return variant_file_path(variant_id, "scroll.json", for_write=for_write)


def normalize_scroll_config(raw: Any) -> dict[str, Any]:
    """Domyślne + wartości z pliku; nieznane klucze pomijane, typy koercjonowane."""
    cfg = dict(SCROLL_DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key in SCROLL_DEFAULTS:
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
        elif key == "headerOffset":
            if value is None:
                cfg[key] = None
            else:
                try:
                    cfg[key] = int(value)
                except (TypeError, ValueError):
                    pass
        else:
            cfg[key] = str(value)
    return cfg


def validate_scroll_config(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, (lo, hi) in _INT_LIMITS.items():
        value = cfg.get(key)
        if not isinstance(value, int):
            errors.append(f"{key}: wymagana liczba całkowita.")
        elif not lo <= value <= hi:
            errors.append(f"{key}: wartość {value} poza zakresem {lo}–{hi}.")
    if (
        isinstance(cfg.get("minDuration"), int)
        and isinstance(cfg.get("maxDuration"), int)
        and cfg["minDuration"] > cfg["maxDuration"]
    ):
        errors.append("minDuration nie może być większe niż maxDuration.")
    header_offset = cfg.get("headerOffset")
    if header_offset is not None:
        if not isinstance(header_offset, int):
            errors.append("headerOffset: liczba całkowita lub puste (auto).")
        elif not 0 <= header_offset <= 400:
            errors.append(f"headerOffset: wartość {header_offset} poza zakresem 0–400.")
    if cfg.get("mobileMode") not in MOBILE_MODES:
        errors.append(f"mobileMode: dozwolone {', '.join(MOBILE_MODES)}.")
    if cfg.get("reducedMotionMode") not in REDUCED_MOTION_MODES:
        errors.append(f"reducedMotionMode: dozwolone {', '.join(REDUCED_MOTION_MODES)}.")
    return errors


def load_scroll_config(variant_id: str) -> dict[str, Any]:
    path = scroll_config_path(variant_id)
    if not path.is_file():
        return dict(SCROLL_DEFAULTS)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(SCROLL_DEFAULTS)
    return normalize_scroll_config(raw)


def save_scroll_config(variant_id: str, cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_scroll_config(cfg)
    errors = validate_scroll_config(normalized)
    if errors:
        raise ValueError("Nieprawidłowa konfiguracja przewijania:\n- " + "\n- ".join(errors))
    path = scroll_config_path(variant_id, for_write=True)
    atomic_write_text(path, json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    return normalized
