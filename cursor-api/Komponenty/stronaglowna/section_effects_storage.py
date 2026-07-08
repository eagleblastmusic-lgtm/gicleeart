"""Per-hook storage for homepage effect packs (scroll reveal, text hover, …).

Legacy single-file configs (studio-reveal.json, final-difference.json) remain
the source of truth for intro / see-difference. Other hooks use section-effects.json.

Adding a new effect type: extend HOME_EFFECT_STORAGE in home_effects_registry.py
and load/save helpers here if needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .final_difference_settings import (
    FINAL_DIFFERENCE_DEFAULTS,
    load_final_difference_config,
    save_final_difference_config,
)
from .section_bg_effects_settings import (
    SECTION_BG_EFFECTS_DEFAULTS,
    load_section_bg_effects_for_hook,
    save_section_bg_effects_for_hook,
)
from .service import _data_dir
from .studio_reveal_settings import (
    STUDIO_REVEAL_DEFAULTS,
    load_studio_reveal_config,
    save_studio_reveal_config,
)

INTRO_HOOK = "intro"
SEE_DIFFERENCE_HOOK = "see-difference"

_SCROLL_REVEAL_KEYS = (
    "enabled",
    "desktopEnabled",
    "glowEnabled",
    "revealThreshold",
    "durationMs",
    "cardDurationMs",
    "textDurationMs",
    "hoverDurationMs",
    "headingDelayMs",
    "paragraphStaggerMs",
    "bgBrightnessStart",
    "lightOpacityMin",
    "lightOpacityMax",
    "cardHoverScale",
    "cardImageHoverScale",
    "copyHoverScale",
    "copyHoverTranslateY",
    "easing",
)

_GRADIENT_KEYS = (
    "gradientPreset",
    "gradientOverlayOpacity",
    "radialCenterX",
    "radialCenterY",
    "radialRadiusX",
    "radialRadiusY",
    "radialFeather",
    "radialExposure",
)

_PARALLAX_KEYS = (
    "parallaxEnabled",
    "parallaxMaxX",
    "parallaxMaxY",
    "parallaxEase",
    "parallaxOverscan",
)


def section_effects_path(variant_id: str) -> Path:
    return _data_dir() / "variants" / variant_id / "section-effects.json"


def load_section_effects_file(variant_id: str) -> dict[str, dict[str, Any]]:
    path = section_effects_path(variant_id)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for hook, packs in raw.items():
        if isinstance(hook, str) and isinstance(packs, dict):
            out[hook] = {str(k): v for k, v in packs.items() if isinstance(k, str)}
    return out


def save_section_effects_file(variant_id: str, data: dict[str, dict[str, Any]]) -> None:
    path = section_effects_path(variant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _pick(cfg: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: cfg[k] for k in keys if k in cfg}


def _merge_defaults(defaults: dict[str, Any], partial: dict[str, Any]) -> dict[str, Any]:
    out = dict(defaults)
    out.update(partial)
    return out


def load_scroll_reveal_for_hook(variant_id: str, hook: str) -> dict[str, Any]:
    if hook == INTRO_HOOK:
        full = load_studio_reveal_config(variant_id)
        return _merge_defaults(STUDIO_REVEAL_DEFAULTS, _pick(full, _SCROLL_REVEAL_KEYS))
    packs = load_section_effects_file(variant_id).get(hook, {})
    raw = packs.get("scroll_reveal")
    if not isinstance(raw, dict):
        raw = {}
    base = _pick(STUDIO_REVEAL_DEFAULTS, _SCROLL_REVEAL_KEYS)
    base["enabled"] = False
    return _merge_defaults(base, raw)


def save_scroll_reveal_for_hook(variant_id: str, hook: str, entry: dict[str, Any]) -> dict[str, Any]:
    if hook == INTRO_HOOK:
        full = load_studio_reveal_config(variant_id)
        full.update(_pick(entry, _SCROLL_REVEAL_KEYS))
        return save_studio_reveal_config(variant_id, full)
    all_data = load_section_effects_file(variant_id)
    hook_packs = dict(all_data.get(hook) or {})
    hook_packs["scroll_reveal"] = _pick(entry, _SCROLL_REVEAL_KEYS)
    all_data[hook] = hook_packs
    save_section_effects_file(variant_id, all_data)
    return hook_packs["scroll_reveal"]


def load_text_hover_for_hook(variant_id: str, hook: str) -> dict[str, Any]:
    if hook == SEE_DIFFERENCE_HOOK:
        return load_final_difference_config(variant_id)
    packs = load_section_effects_file(variant_id).get(hook, {})
    raw = packs.get("text_hover")
    if not isinstance(raw, dict):
        raw = {}
    base = dict(FINAL_DIFFERENCE_DEFAULTS)
    base["enabled"] = False
    return _merge_defaults(base, raw)


def save_text_hover_for_hook(variant_id: str, hook: str, entry: dict[str, Any]) -> dict[str, Any]:
    if hook == SEE_DIFFERENCE_HOOK:
        return save_final_difference_config(variant_id, entry)
    all_data = load_section_effects_file(variant_id)
    hook_packs = dict(all_data.get(hook) or {})
    hook_packs["text_hover"] = dict(entry)
    all_data[hook] = hook_packs
    save_section_effects_file(variant_id, all_data)
    return hook_packs["text_hover"]


def load_gradient_bio_for_hook(variant_id: str, hook: str) -> dict[str, Any]:
    if hook == INTRO_HOOK:
        full = load_studio_reveal_config(variant_id)
        cfg = _merge_defaults(SECTION_BG_EFFECTS_DEFAULTS, _pick(full, _GRADIENT_KEYS))
        preset = str(cfg.get("gradientPreset", "none"))
        cfg["enabled"] = preset != "none"
        cfg["desktopEnabled"] = bool(full.get("desktopEnabled", True))
        return cfg
    bg = load_section_bg_effects_for_hook(variant_id, hook)
    return _merge_defaults(SECTION_BG_EFFECTS_DEFAULTS, bg)


def load_parallax_for_hook(variant_id: str, hook: str) -> dict[str, Any]:
    if hook == INTRO_HOOK:
        full = load_studio_reveal_config(variant_id)
        return _merge_defaults(SECTION_BG_EFFECTS_DEFAULTS, _pick(full, _PARALLAX_KEYS))
    bg = load_section_bg_effects_for_hook(variant_id, hook)
    return _merge_defaults(SECTION_BG_EFFECTS_DEFAULTS, _pick(bg, _PARALLAX_KEYS))


def save_gradient_parallax_for_hook(
    variant_id: str,
    hook: str,
    gradient_partial: dict[str, Any],
    parallax_partial: dict[str, Any],
) -> dict[str, Any]:
    if hook == INTRO_HOOK:
        full = load_studio_reveal_config(variant_id)
        full.update(_pick(gradient_partial, _GRADIENT_KEYS))
        full.update(_pick(parallax_partial, _PARALLAX_KEYS))
        saved = save_studio_reveal_config(variant_id, full)
        return _merge_defaults(SECTION_BG_EFFECTS_DEFAULTS, {**_pick(saved, _GRADIENT_KEYS), **_pick(saved, _PARALLAX_KEYS)})
    bg = load_section_bg_effects_for_hook(variant_id, hook)
    grad = _pick(gradient_partial, _GRADIENT_KEYS)
    par = _pick(parallax_partial, _PARALLAX_KEYS)
    merged = dict(SECTION_BG_EFFECTS_DEFAULTS)
    merged.update(bg)
    merged.update(grad)
    merged.update(par)
    gradient_on = str(merged.get("gradientPreset", "none")) != "none"
    parallax_on = bool(merged.get("parallaxEnabled"))
    merged["enabled"] = gradient_on or parallax_on
    if not gradient_on:
        merged["gradientPreset"] = "none"
    return save_section_bg_effects_for_hook(variant_id, hook, merged)


def export_section_effects_config(variant_id: str) -> dict[str, dict[str, Any]]:
    """Per-hook packs for front (boot.js → GICLEE_HOME_SECTION_EFFECTS_CONFIG); excludes legacy intro/see-difference globals."""
    out: dict[str, dict[str, Any]] = {}
    for hook, packs in load_section_effects_file(variant_id).items():
        if hook in (INTRO_HOOK, SEE_DIFFERENCE_HOOK):
            continue
        if packs:
            out[hook] = packs
    return out
