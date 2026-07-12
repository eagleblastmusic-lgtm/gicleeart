"""Gradient BIO + parallax tła — sekcje homepage (poza intro, które ma studio-reveal.json).

Zapis per wariant: data/variants/<id>/section-bg-effects.json — klucze = hooki
(intro, restoration, color-correction, potential, see-difference).
Hook «intro» w pliku opcjonalny (domyślnie studio-reveal.json ma pierwszeństwo).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from .homepage_variants import variant_file_path
from .service import _data_dir

_LEGACY_DATA_DIR = _data_dir()
from .studio_reveal_settings import GRADIENT_PRESETS

SECTION_BG_EFFECTS_HOOKS: tuple[str, ...] = (
    "see-difference",
    "restoration",
    "color-correction",
    "potential",
)

SECTION_BG_EFFECTS_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "desktopEnabled": True,
    "gradientPreset": "none",
    "gradientOverlayOpacity": 100,
    "radialCenterX": 35,
    "radialCenterY": 50,
    "radialRadiusX": 55,
    "radialRadiusY": 85,
    "radialFeather": 50,
    "radialExposure": 50,
    "parallaxEnabled": False,
    "parallaxMaxX": 16,
    "parallaxMaxY": 10,
    "parallaxEase": 0.075,
    "parallaxOverscan": 106,
}

SECTION_BG_EFFECTS_PRESETS: dict[str, dict[str, Any]] = {
    "Wyłączone": {"enabled": False, "gradientPreset": "none", "parallaxEnabled": False},
    "Gradient editorial (BIO)": {
        "enabled": True,
        "gradientPreset": "editorial",
        "gradientOverlayOpacity": 100,
        "parallaxEnabled": False,
    },
    "Gradient + parallax": {
        "enabled": True,
        "gradientPreset": "editorial",
        "gradientOverlayOpacity": 92,
        "parallaxEnabled": True,
        "parallaxMaxX": 18,
        "parallaxMaxY": 12,
    },
    "Menu wide (wtopienie góra)": {
        "enabled": True,
        "gradientPreset": "menu_wide",
        "parallaxEnabled": False,
    },
    "Radial spot": {
        "enabled": True,
        "gradientPreset": "radial_spot",
        "radialExposure": 58,
        "parallaxEnabled": False,
    },
}

_INT_LIMITS: dict[str, tuple[int, int]] = {
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
    "parallaxEase": (0.03, 0.15),
}


def section_bg_effects_config_path(variant_id: str, *, for_write: bool = False) -> Path:
    current = _data_dir()
    if current != _LEGACY_DATA_DIR:
        return current / "variants" / variant_id / "section-bg-effects.json"
    return variant_file_path(variant_id, "section-bg-effects.json", for_write=for_write)


def normalize_section_bg_effects_entry(raw: Any) -> dict[str, Any]:
    cfg = dict(SECTION_BG_EFFECTS_DEFAULTS)
    if not isinstance(raw, dict):
        return cfg
    for key in SECTION_BG_EFFECTS_DEFAULTS:
        if key in raw:
            cfg[key] = raw[key]
    cfg["enabled"] = bool(cfg["enabled"])
    cfg["desktopEnabled"] = bool(cfg["desktopEnabled"])
    cfg["parallaxEnabled"] = bool(cfg["parallaxEnabled"])
    preset = str(cfg.get("gradientPreset") or "none").strip().lower()
    if preset not in GRADIENT_PRESETS:
        preset = "none"
    cfg["gradientPreset"] = preset
    for key in _INT_LIMITS:
        try:
            cfg[key] = int(cfg[key])
        except (TypeError, ValueError):
            cfg[key] = SECTION_BG_EFFECTS_DEFAULTS[key]
        lo, hi = _INT_LIMITS[key]
        cfg[key] = max(lo, min(hi, cfg[key]))
    for key in _FLOAT_LIMITS:
        try:
            cfg[key] = float(cfg[key])
        except (TypeError, ValueError):
            cfg[key] = SECTION_BG_EFFECTS_DEFAULTS[key]
        lo, hi = _FLOAT_LIMITS[key]
        cfg[key] = max(lo, min(hi, cfg[key]))
    return cfg


def normalize_section_bg_effects_file(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for hook, entry in raw.items():
        hook_key = str(hook).strip()
        if not hook_key:
            continue
        out[hook_key] = normalize_section_bg_effects_entry(entry)
    return out


def apply_section_bg_effects_preset(name: str) -> dict[str, Any]:
    merged = dict(SECTION_BG_EFFECTS_DEFAULTS)
    merged.update(SECTION_BG_EFFECTS_PRESETS.get(name, {}))
    return normalize_section_bg_effects_entry(merged)


def load_section_bg_effects_config(variant_id: str) -> dict[str, dict[str, Any]]:
    path = section_bg_effects_config_path(variant_id)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return normalize_section_bg_effects_file(raw)


def load_section_bg_effects_for_hook(variant_id: str, hook: str) -> dict[str, Any]:
    all_cfg = load_section_bg_effects_config(variant_id)
    return normalize_section_bg_effects_entry(all_cfg.get(hook))


def save_section_bg_effects_for_hook(
    variant_id: str, hook: str, entry: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    normalized_entry = normalize_section_bg_effects_entry(entry)
    all_cfg = load_section_bg_effects_config(variant_id)
    all_cfg[str(hook)] = normalized_entry
    path = section_bg_effects_config_path(variant_id, for_write=True)
    atomic_write_text(path, json.dumps(all_cfg, ensure_ascii=False, indent=2) + "\n")
    return all_cfg


def export_section_bg_effects_config(all_cfg: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for hook, entry in normalize_section_bg_effects_file(all_cfg).items():
        exported = dict(entry)
        exported["parallaxOverscan"] = round(int(entry["parallaxOverscan"]) / 100, 4)
        out[hook] = exported
    return out
