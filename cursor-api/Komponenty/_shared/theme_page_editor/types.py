"""Typy stref i pól edytora szablonów motywu."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

FieldKind = Literal[
    "shopify_image",
    "shopify_video",
    "theme_asset",
    "section_background",
    "media_type",
    "video_collage",
    "heading",
    "body",
    "text",
    "link",
    "bool",
    "int",
    "float",
    "blocks_visible",
]

PathKey = tuple[str, ...]


@dataclass(frozen=True)
class TemplateField:
    field_id: str
    label: str
    kind: FieldKind
    path: PathKey | None = None
    theme_asset: str | None = None
    hint: str = ""
    block_paths: tuple[PathKey, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TemplateZone:
    zone_id: str
    label: str
    description: str
    section_key: str
    fields: tuple[TemplateField, ...] = field(default_factory=tuple)
    settings_only: bool = False


def _s(section: str, *parts: str) -> PathKey:
    return ("sections", section, *parts)


def zone_by_id(zones: tuple[TemplateZone, ...], zone_id: str) -> TemplateZone | None:
    for zone in zones:
        if zone.zone_id == zone_id:
            return zone
    return None


def zone_enabled(template: dict[str, Any], zone: TemplateZone) -> bool:
    if zone.settings_only:
        return True
    section = (template.get("sections") or {}).get(zone.section_key)
    if not isinstance(section, dict):
        return False
    return not bool(section.get("disabled"))


def set_zone_enabled(template: dict[str, Any], zone: TemplateZone, enabled: bool) -> None:
    if zone.settings_only:
        return
    section = (template.get("sections") or {}).get(zone.section_key)
    if not isinstance(section, dict):
        return
    if enabled:
        section.pop("disabled", None)
    else:
        section["disabled"] = True


__all__ = [
    "FieldKind",
    "PathKey",
    "TemplateField",
    "TemplateZone",
    "_s",
    "zone_by_id",
    "zone_enabled",
    "set_zone_enabled",
]
