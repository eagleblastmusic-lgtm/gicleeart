"""Ustawienia faz GICLÉE HOME FLOW i bezpieczne scalanie z wariantem.

Fazy mają osobny plik metadanych ``home_flow_phases.json``. Podczas odczytu,
zapisu i zastosowania wariantu ich wartości są scalane z ``settings.json`` oraz
``index.json``. Dzięki temu istniejący edytor sekcji pozostaje kompatybilny,
a GICLÉE HOME FLOW jest kanonicznym miejscem konfiguracji animacji.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text

from . import homepage_variants
from . import prehero_integration as prehero
from .home_flow import DEFAULT_FLOW_ITEMS
from .registry import zone_by_id
from .service import load_zone_values, path_set

PHASE_SCHEMA_VERSION = 1
PHASE_FILENAME = "home_flow_phases.json"

PORTAL_ID = "phase:portal"
HERO_RISE_ID = "phase:hero-rise"
HERO_HOLD_ID = "phase:hero-hold"
SOUND_ID = "phase:sound-consent"
CURTAIN_ID = "phase:horizontal-curtain"
INTRO_HOLD_ID = "phase:intro-hold"

SOUND_SETTING_KEYS = {
    "enabled": "home_flow_sound_enabled",
    "question": "home_flow_sound_question",
    "toggle_label": "home_flow_sound_toggle_label",
    "start_label": "home_flow_sound_start_label",
    "audio_url": "home_flow_sound_audio_url",
    "volume": "home_flow_sound_volume",
    "auto_muted_fraction": "home_flow_sound_auto_muted_fraction",
}

DEFAULT_SOUND = {
    "enabled": True,
    "question": "Doświadczyć tej sceny z dźwiękiem?",
    "toggle_label": "Dźwięk",
    "start_label": "Rozpocznij",
    "audio_url": "",
    "volume": 28,
    "auto_muted_fraction": 35,
}

PHASE_LABELS: dict[str, str] = {
    PORTAL_ID: "Portal i tekst",
    HERO_RISE_ID: "Wjazd Hero",
    HERO_HOLD_ID: "Postój Hero",
    SOUND_ID: "Decyzja o dźwięku",
    CURTAIN_ID: "Pozioma kurtyna Hero → Giclée Art",
    INTRO_HOLD_ID: "Postój sekcji Giclée Art",
}


def phase_path(
    variant_id: str,
    *,
    variants_root: Path | None = None,
    for_write: bool = False,
) -> Path:
    return homepage_variants.variant_file_path(
        str(variant_id),
        PHASE_FILENAME,
        for_write=for_write,
        variants_root=variants_root,
    )


def _bounded_int(raw: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(float(raw))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


def _clean_text(raw: Any, default: str = "", *, limit: int = 500) -> str:
    text = str(raw if raw is not None else default).strip()
    return text[:limit]


def _normalize_phase(stable_id: str, raw: dict[str, Any] | None) -> dict[str, Any]:
    source = raw or {}
    if stable_id == PORTAL_ID:
        text = _clean_text(source.get("text"), prehero.DEFAULT_COPY_TEXT, limit=800)
        lines = [line.strip() for line in text.splitlines() if line.strip()][:5]
        return {
            "enabled": bool(source.get("enabled", True)),
            "screens": _bounded_int(source.get("screens"), 2, 1, 10),
            "text": "\n".join(lines) or prehero.DEFAULT_COPY_TEXT,
        }
    if stable_id == HERO_RISE_ID:
        return {"screens": _bounded_int(source.get("screens"), 1, 1, 5)}
    if stable_id == HERO_HOLD_ID:
        return {
            "enabled": bool(source.get("enabled", True)),
            "screens": _bounded_int(source.get("screens"), 1, 0, 5),
        }
    if stable_id == SOUND_ID:
        return {
            "enabled": bool(source.get("enabled", DEFAULT_SOUND["enabled"])),
            "question": _clean_text(source.get("question"), DEFAULT_SOUND["question"], limit=160),
            "toggle_label": _clean_text(
                source.get("toggle_label"), DEFAULT_SOUND["toggle_label"], limit=60
            ),
            "start_label": _clean_text(
                source.get("start_label"), DEFAULT_SOUND["start_label"], limit=60
            ),
            "audio_url": _clean_text(source.get("audio_url"), "", limit=1200),
            "volume": _bounded_int(source.get("volume"), 28, 0, 100),
            "auto_muted_fraction": _bounded_int(
                source.get("auto_muted_fraction"), 35, 0, 100
            ),
        }
    if stable_id == CURTAIN_ID:
        return {
            "enabled": bool(source.get("enabled", True)),
            "screens": _bounded_int(source.get("screens"), 1, 1, 5),
        }
    if stable_id == INTRO_HOLD_ID:
        return {
            "enabled": bool(source.get("enabled", True)),
            "screens": _bounded_int(source.get("screens"), 1, 0, 5),
        }
    return {}


def load_phase_metadata(
    variant_id: str,
    *,
    variants_root: Path | None = None,
) -> dict[str, Any]:
    path = phase_path(variant_id, variants_root=variants_root)
    if not path.is_file():
        return {"schema": PHASE_SCHEMA_VERSION, "phases": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"schema": PHASE_SCHEMA_VERSION, "phases": {}}
    if not isinstance(data, dict):
        return {"schema": PHASE_SCHEMA_VERSION, "phases": {}}
    raw_phases = data.get("phases")
    phases: dict[str, dict[str, Any]] = {}
    known = set(PHASE_LABELS)
    if isinstance(raw_phases, dict):
        for stable_id, raw in raw_phases.items():
            if stable_id in known and isinstance(raw, dict):
                phases[stable_id] = _normalize_phase(stable_id, raw)
    return {"schema": PHASE_SCHEMA_VERSION, "phases": phases}


def save_phase_metadata(
    variant_id: str,
    metadata: dict[str, Any],
    *,
    variants_root: Path | None = None,
) -> Path:
    path = phase_path(variant_id, variants_root=variants_root, for_write=True)
    raw_phases = metadata.get("phases") if isinstance(metadata, dict) else {}
    phases: dict[str, dict[str, Any]] = {}
    if isinstance(raw_phases, dict):
        for stable_id, raw in raw_phases.items():
            if stable_id in PHASE_LABELS and isinstance(raw, dict):
                phases[stable_id] = _normalize_phase(stable_id, raw)
    payload = {"schema": PHASE_SCHEMA_VERSION, "phases": phases}
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path


def _raw_variant_data(variant_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    index_path = homepage_variants.variant_file_path(variant_id, "index.json")
    settings_path = homepage_variants.variant_file_path(variant_id, "settings.json")
    if not index_path.is_file() or not settings_path.is_file():
        return homepage_variants.load_index_template(), homepage_variants.load_theme_settings()
    return (
        homepage_variants._load_json_file(index_path),
        homepage_variants._load_json_file(settings_path),
    )


def _hero_audio_defaults(template: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    hero = zone_by_id("hero")
    values = load_zone_values(template, hero, settings=settings) if hero is not None else {}
    return {
        "enabled": bool(values.get("hero_audio_enable", DEFAULT_SOUND["enabled"])),
        "question": DEFAULT_SOUND["question"],
        "toggle_label": DEFAULT_SOUND["toggle_label"],
        "start_label": DEFAULT_SOUND["start_label"],
        "audio_url": str(values.get("hero_audio_url") or "").strip(),
        "volume": _bounded_int(values.get("hero_audio_volume"), 28, 0, 100),
        "auto_muted_fraction": 35,
    }


def phase_defaults_from_variant(
    variant_id: str,
    stable_id: str,
) -> dict[str, Any]:
    template, settings = _raw_variant_data(variant_id)
    values = prehero.load_prehero_values(settings)
    if stable_id == PORTAL_ID:
        return _normalize_phase(
            stable_id,
            {
                "enabled": values.get("prehero_copy_enabled", True),
                "screens": values.get("prehero_reveal_screens", 2),
                "text": values.get("prehero_copy_text", prehero.DEFAULT_COPY_TEXT),
            },
        )
    if stable_id == HERO_RISE_ID:
        return _normalize_phase(
            stable_id, {"screens": values.get("prehero_hero_rise_screens", 1)}
        )
    if stable_id == HERO_HOLD_ID:
        screens = _bounded_int(values.get("prehero_hero_hold_screens"), 1, 0, 5)
        return _normalize_phase(stable_id, {"enabled": screens > 0, "screens": screens})
    if stable_id == SOUND_ID:
        return _normalize_phase(stable_id, _hero_audio_defaults(template, settings))
    if stable_id == CURTAIN_ID:
        return _normalize_phase(
            stable_id,
            {
                "enabled": values.get("prehero_horizontal_curtain_enabled", True),
                "screens": values.get("prehero_horizontal_curtain_screens", 1),
            },
        )
    if stable_id == INTRO_HOLD_ID:
        screens = _bounded_int(values.get("prehero_intro_hold_screens"), 1, 0, 5)
        return _normalize_phase(stable_id, {"enabled": screens > 0, "screens": screens})
    return {}


def effective_phase_config(variant_id: str, stable_id: str) -> dict[str, Any]:
    defaults = phase_defaults_from_variant(variant_id, stable_id)
    metadata = load_phase_metadata(variant_id)
    override = (metadata.get("phases") or {}).get(stable_id)
    if isinstance(override, dict):
        defaults.update(override)
    return _normalize_phase(stable_id, defaults)


def set_phase_config(variant_id: str, stable_id: str, values: dict[str, Any]) -> Path:
    if stable_id not in PHASE_LABELS:
        raise ValueError(f"Nieznana faza GICLÉE HOME FLOW: {stable_id}")
    metadata = load_phase_metadata(variant_id)
    phases = dict(metadata.get("phases") or {})
    phases[stable_id] = _normalize_phase(stable_id, values)
    metadata["phases"] = phases
    return save_phase_metadata(variant_id, metadata)


def reset_phase_config(variant_id: str, stable_id: str) -> Path:
    metadata = load_phase_metadata(variant_id)
    phases = dict(metadata.get("phases") or {})
    phases.pop(stable_id, None)
    metadata["phases"] = phases
    return save_phase_metadata(variant_id, metadata)


def _set_hero_audio_fields(template: dict[str, Any], sound: dict[str, Any]) -> None:
    hero = zone_by_id("hero")
    if hero is None:
        return
    mapping = {
        "hero_audio_enable": bool(sound.get("enabled")),
        "hero_audio_url": str(sound.get("audio_url") or ""),
        "hero_audio_label_on": str(sound.get("toggle_label") or "Dźwięk"),
        "hero_audio_label_off": "Wycisz",
        "hero_audio_volume": _bounded_int(sound.get("volume"), 28, 0, 100),
    }
    for field in hero.fields:
        if field.field_id in mapping and field.path:
            path_set(template, field.path, mapping[field.field_id])


def apply_phase_overrides(
    variant_id: str,
    template: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    template = copy.deepcopy(template)
    settings = copy.deepcopy(settings)
    current = settings.get("current")
    if not isinstance(current, dict):
        current = {}
        settings["current"] = current

    metadata = load_phase_metadata(variant_id)
    phases = metadata.get("phases") if isinstance(metadata, dict) else {}
    phases = phases if isinstance(phases, dict) else {}

    portal = phases.get(PORTAL_ID)
    if isinstance(portal, dict):
        cfg = _normalize_phase(PORTAL_ID, portal)
        current["prehero_copy_enabled"] = bool(cfg["enabled"])
        current["prehero_reveal_screens"] = int(cfg["screens"])
        current["prehero_copy_text"] = str(cfg["text"])

    hero_rise = phases.get(HERO_RISE_ID)
    if isinstance(hero_rise, dict):
        cfg = _normalize_phase(HERO_RISE_ID, hero_rise)
        current["prehero_hero_rise_screens"] = int(cfg["screens"])

    hero_hold = phases.get(HERO_HOLD_ID)
    if isinstance(hero_hold, dict):
        cfg = _normalize_phase(HERO_HOLD_ID, hero_hold)
        current["prehero_hero_hold_screens"] = int(cfg["screens"]) if cfg["enabled"] else 0

    curtain = phases.get(CURTAIN_ID)
    if isinstance(curtain, dict):
        cfg = _normalize_phase(CURTAIN_ID, curtain)
        current["prehero_horizontal_curtain_enabled"] = bool(cfg["enabled"])
        current["prehero_horizontal_curtain_screens"] = int(cfg["screens"])

    intro_hold = phases.get(INTRO_HOLD_ID)
    if isinstance(intro_hold, dict):
        cfg = _normalize_phase(INTRO_HOLD_ID, intro_hold)
        current["prehero_intro_hold_screens"] = int(cfg["screens"]) if cfg["enabled"] else 0

    sound_override = phases.get(SOUND_ID)
    if isinstance(sound_override, dict):
        sound = _normalize_phase(SOUND_ID, sound_override)
    else:
        sound = _normalize_phase(SOUND_ID, _hero_audio_defaults(template, settings))
    for field, key in SOUND_SETTING_KEYS.items():
        current[key] = sound[field]
    _set_hero_audio_fields(template, sound)

    return template, settings


def _install_zero_hold_normalization() -> None:
    current = prehero.normalize_prehero_values
    if getattr(current, "_giclee_phase_zero_holds", False):
        return

    def normalize_with_zero_holds(raw: dict[str, Any] | None) -> dict[str, Any]:
        out = current(raw)
        source = raw or {}
        if "prehero_hero_hold_screens" in source:
            out["prehero_hero_hold_screens"] = _bounded_int(
                source.get("prehero_hero_hold_screens"), 1, 0, 5
            )
        return out

    setattr(normalize_with_zero_holds, "_giclee_phase_zero_holds", True)
    setattr(normalize_with_zero_holds, "__wrapped__", current)
    prehero.normalize_prehero_values = normalize_with_zero_holds


def _install_sound_export() -> None:
    current = prehero.export_prehero_config
    if getattr(current, "_giclee_phase_sound_export", False):
        return

    def export_with_sound(settings: dict[str, Any] | None) -> dict[str, Any]:
        config = current(settings)
        source = prehero._settings_current(settings)
        sound = dict(DEFAULT_SOUND)
        for field, key in SOUND_SETTING_KEYS.items():
            if key in source and source[key] is not None:
                sound[field] = source[key]
        sound = _normalize_phase(SOUND_ID, sound)
        config.update(
            {
                "soundConsentEnabled": bool(sound["enabled"]),
                "soundConsentQuestion": str(sound["question"]),
                "soundConsentToggleLabel": str(sound["toggle_label"]),
                "soundConsentStartLabel": str(sound["start_label"]),
                "soundConsentAudioUrl": str(sound["audio_url"]),
                "soundConsentVolume": int(sound["volume"]),
                "soundConsentAutoMutedFraction": int(sound["auto_muted_fraction"]) / 100,
            }
        )
        return config

    setattr(export_with_sound, "_giclee_phase_sound_export", True)
    setattr(export_with_sound, "__wrapped__", current)
    prehero.export_prehero_config = export_with_sound


def _install_variant_bridge() -> None:
    current_load = homepage_variants.load_variant_data
    if not getattr(current_load, "_giclee_phase_bridge", False):

        def load_variant_data_with_phases(variant_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
            template, settings = current_load(variant_id)
            return apply_phase_overrides(variant_id, template, settings)

        setattr(load_variant_data_with_phases, "_giclee_phase_bridge", True)
        setattr(load_variant_data_with_phases, "__wrapped__", current_load)
        homepage_variants.load_variant_data = load_variant_data_with_phases

    current_persist = homepage_variants.persist_editor_to_variant
    if not getattr(current_persist, "_giclee_phase_bridge", False):

        def persist_with_phases(
            variant_id: str,
            template: dict[str, Any],
            settings: dict[str, Any],
        ) -> None:
            merged_template, merged_settings = apply_phase_overrides(
                variant_id, template, settings
            )
            current_persist(variant_id, merged_template, merged_settings)

        setattr(persist_with_phases, "_giclee_phase_bridge", True)
        setattr(persist_with_phases, "__wrapped__", current_persist)
        homepage_variants.persist_editor_to_variant = persist_with_phases


def install_home_flow_phase_settings() -> None:
    _install_zero_hold_normalization()
    _install_sound_export()
    _install_variant_bridge()


KNOWN_PHASE_IDS = frozenset(item.stable_id for item in DEFAULT_FLOW_ITEMS if item.kind == "phase")
