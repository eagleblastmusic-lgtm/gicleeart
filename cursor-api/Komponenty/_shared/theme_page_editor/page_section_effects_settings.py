"""Efekty per sekcja stron menu (tekst + grafika) — zapis w data/variants/<id>/section-effects.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Komponenty.stronaglowna.section_bg_effects_settings import (
    SECTION_BG_EFFECTS_DEFAULTS,
    normalize_section_bg_effects_entry,
)
from Komponenty.stronaglowna.service import theme_root
from Komponenty.stronaglowna.studio_reveal_settings import (
    STUDIO_REVEAL_DEFAULTS,
    export_studio_reveal_config,
    normalize_studio_reveal_config,
    validate_studio_reveal_config,
)

from .config import PageEditorConfig
from .types import TemplateZone

PAGE_IMAGE_EFFECT_DEFAULTS: dict[str, Any] = {
    **SECTION_BG_EFFECTS_DEFAULTS,
    "parallaxEnabled": False,
    "parallaxReturnEase": 0.035,
    "imageHoverEnabled": True,
    "imageHoverScale": 1.025,
    "imageHoverDurationMs": 850,
}

PAGE_IMAGE_FLOAT_KEYS = ("parallaxEase", "parallaxReturnEase", "imageHoverScale")
PAGE_IMAGE_INT_KEYS = (
    "parallaxMaxX",
    "parallaxMaxY",
    "parallaxOverscan",
    "imageHoverDurationMs",
)
PAGE_IMAGE_BOOL_KEYS = ("parallaxEnabled", "desktopEnabled", "imageHoverEnabled")


def zone_has_text_effects(zone: TemplateZone) -> bool:
    if zone.settings_only:
        return False
    return any(
        fld.kind in ("text", "body", "heading") or "jumbo" in fld.field_id
        for fld in zone.fields
    )


def zone_has_image_effects(zone: TemplateZone) -> bool:
    if (zone.image_effect_selector or "").strip():
        return True
    if zone.settings_only:
        return False
    return any(fld.kind == "shopify_image" for fld in zone.fields)


def section_effects_path(config: PageEditorConfig, variant_id: str) -> Path:
    return config.component_dir / "data" / "variants" / variant_id / "section-effects.json"


def _normalize_image_effects(raw: Any) -> dict[str, Any]:
    base = dict(PAGE_IMAGE_EFFECT_DEFAULTS)
    if not isinstance(raw, dict):
        return base
    merged = normalize_section_bg_effects_entry({**base, **raw})
    for key in PAGE_IMAGE_BOOL_KEYS:
        if key in raw:
            merged[key] = bool(raw[key])
    for key in PAGE_IMAGE_INT_KEYS:
        if key in raw:
            try:
                merged[key] = int(raw[key])
            except (TypeError, ValueError):
                pass
    for key in PAGE_IMAGE_FLOAT_KEYS:
        if key in raw:
            try:
                merged[key] = float(raw[key])
            except (TypeError, ValueError):
                pass
    merged["parallaxReturnEase"] = max(
        0.01,
        min(
            0.10,
            float(
                merged.get(
                    "parallaxReturnEase",
                    PAGE_IMAGE_EFFECT_DEFAULTS["parallaxReturnEase"],
                )
            ),
        ),
    )
    merged["imageHoverScale"] = max(1.0, min(1.08, float(merged.get("imageHoverScale", 1.025))))
    merged["imageHoverDurationMs"] = max(400, min(1600, int(merged.get("imageHoverDurationMs", 850))))
    merged["enabled"] = bool(merged.get("parallaxEnabled")) or bool(merged.get("imageHoverEnabled"))
    return merged


def normalize_section_effects_entry(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for section_key, entry in raw.items():
        if not isinstance(section_key, str) or not section_key.strip():
            continue
        if not isinstance(entry, dict):
            continue
        text_raw = entry.get("text")
        image_raw = entry.get("image")
        section_out: dict[str, Any] = {}
        if isinstance(text_raw, dict):
            section_out["text"] = normalize_studio_reveal_config(text_raw)
        if isinstance(image_raw, dict):
            section_out["image"] = _normalize_image_effects(image_raw)
        if section_out:
            out[section_key] = section_out
    return out


def load_section_effects_config(config: PageEditorConfig, variant_id: str) -> dict[str, dict[str, Any]]:
    path = section_effects_path(config, variant_id)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return normalize_section_effects_entry(raw)


def load_text_effects_for_section(
    config: PageEditorConfig,
    variant_id: str,
    section_key: str,
) -> dict[str, Any]:
    all_cfg = load_section_effects_config(config, variant_id)
    entry = all_cfg.get(section_key, {})
    text = entry.get("text")
    if isinstance(text, dict):
        return normalize_studio_reveal_config(text)
    return dict(STUDIO_REVEAL_DEFAULTS)


def load_image_effects_for_section(
    config: PageEditorConfig,
    variant_id: str,
    section_key: str,
) -> dict[str, Any]:
    all_cfg = load_section_effects_config(config, variant_id)
    entry = all_cfg.get(section_key, {})
    image = entry.get("image")
    return _normalize_image_effects(image if isinstance(image, dict) else {})


def save_text_effects_for_section(
    config: PageEditorConfig,
    variant_id: str,
    section_key: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_studio_reveal_config(entry)
    errors = validate_studio_reveal_config(normalized)
    if errors:
        raise ValueError("\n".join(errors))
    all_cfg = load_section_effects_config(config, variant_id)
    section_entry = dict(all_cfg.get(section_key, {}))
    section_entry["text"] = normalized
    all_cfg[section_key] = section_entry
    _write_section_effects_file(config, variant_id, all_cfg)
    return normalized


def save_image_effects_for_section(
    config: PageEditorConfig,
    variant_id: str,
    section_key: str,
    entry: dict[str, Any],
) -> dict[str, Any]:
    normalized = _normalize_image_effects(entry)
    all_cfg = load_section_effects_config(config, variant_id)
    section_entry = dict(all_cfg.get(section_key, {}))
    section_entry["image"] = normalized
    all_cfg[section_key] = section_entry
    _write_section_effects_file(config, variant_id, all_cfg)
    return normalized


def _write_section_effects_file(
    config: PageEditorConfig,
    variant_id: str,
    data: dict[str, dict[str, Any]],
) -> None:
    path = section_effects_path(config, variant_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_section_effects_entry(data)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_image_effects_config(cfg: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_image_effects(cfg)
    out = {
        "enabled": bool(normalized.get("enabled")),
        "desktopEnabled": bool(normalized.get("desktopEnabled", True)),
        "parallaxEnabled": bool(normalized.get("parallaxEnabled")),
        "parallaxMaxX": int(normalized.get("parallaxMaxX", 16)),
        "parallaxMaxY": int(normalized.get("parallaxMaxY", 10)),
        "parallaxEase": float(normalized.get("parallaxEase", 0.075)),
        "parallaxReturnEase": float(
            normalized.get("parallaxReturnEase", PAGE_IMAGE_EFFECT_DEFAULTS["parallaxReturnEase"])
        ),
        "parallaxOverscan": round(int(normalized.get("parallaxOverscan", 106)) / 100, 4),
        "imageHoverEnabled": bool(normalized.get("imageHoverEnabled")),
        "imageHoverScale": float(normalized.get("imageHoverScale", 1.025)),
        "imageHoverDurationMs": int(normalized.get("imageHoverDurationMs", 850)),
    }
    return out


def _image_effect_selector_for_section(config: PageEditorConfig, section_key: str) -> str | None:
    """Zwraca zaufany selektor z rejestru komponentu, nigdy z danych użytkownika."""

    for zone in config.zones:
        if zone.section_key != section_key:
            continue
        selector = (zone.image_effect_selector or "").strip()
        if selector:
            return selector
    return None


def export_section_effects_for_front(
    config: PageEditorConfig,
    variant_id: str,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for section_key, entry in load_section_effects_config(config, variant_id).items():
        exported: dict[str, Any] = {}
        text_raw = entry.get("text")
        if isinstance(text_raw, dict) and text_raw.get("enabled"):
            exported["text"] = export_studio_reveal_config(text_raw)
        image_raw = entry.get("image")
        if isinstance(image_raw, dict):
            image_cfg = _normalize_image_effects(image_raw)
            if image_cfg.get("enabled"):
                image_export = export_image_effects_config(image_cfg)
                target_selector = _image_effect_selector_for_section(config, section_key)
                if target_selector:
                    image_export["targetSelector"] = target_selector
                exported["image"] = image_export
        if exported:
            out[section_key] = exported
    return out


def effects_asset_basename(config: PageEditorConfig) -> str:
    slug = config.template_basename.removeprefix("page.").removesuffix(".json")
    return f"{slug}-section-effects.js"


def page_template_slug(config: PageEditorConfig) -> str:
    return config.template_basename.removeprefix("page.").removesuffix(".json")


def write_page_section_effects_asset(config: PageEditorConfig, variant_id: str) -> Path:
    from Komponenty.stronaglowna.home_features import _write_text_if_changed

    sections = export_section_effects_for_front(config, variant_id)
    payload = {
        "page": page_template_slug(config),
        "variant": variant_id,
        "sections": sections,
    }
    line = "window.GICLEE_PAGE_SECTION_EFFECTS = " + json.dumps(payload, ensure_ascii=False) + ";\n"
    assets_dir = theme_root() / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / effects_asset_basename(config)
    _write_text_if_changed(path, line)
    return path
