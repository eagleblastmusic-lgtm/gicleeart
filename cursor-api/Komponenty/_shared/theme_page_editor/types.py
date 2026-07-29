"""Typy stref i pól edytora szablonów motywu."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
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
    "choice",
    "bool",
    "int",
    "float",
    "blocks_visible",
]

PathKey = tuple[str, ...]
ChoiceProvider = Callable[
    [dict[str, Any]],
    tuple[tuple[str, str], ...],
]


@dataclass(frozen=True)
class FieldGroupVariantLibrary:
    group_id: str
    label: str
    storage_filename: str
    controlled_field_ids: tuple[str, ...]
    preset_field_id: str
    custom_preset_value: str = "custom"


@dataclass(frozen=True)
class TemplateField:
    field_id: str
    label: str
    kind: FieldKind
    path: PathKey | None = None
    theme_asset: str | None = None
    hint: str = ""
    block_paths: tuple[PathKey, ...] = field(default_factory=tuple)
    choices: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    choice_provider: ChoiceProvider | None = None
    choice_dependencies: tuple[str, ...] = field(default_factory=tuple)
    visible_when: tuple[tuple[str, tuple[str, ...]], ...] = field(
        default_factory=tuple
    )
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    unit: str | None = None
    # Opcjonalna grupa pól renderowana jako zwijany akordeon.
    group_id: str | None = None
    group_label: str = ""
    group_collapsed: bool = False


@dataclass(frozen=True)
class TemplateZone:
    zone_id: str
    label: str
    description: str
    section_key: str
    fields: tuple[TemplateField, ...] = field(default_factory=tuple)
    settings_only: bool = False
    # Opcjonalny, jawny cel efektów grafiki na froncie. Pozostaje pusty dla
    # istniejących stref, które korzystają z bezpiecznego fallbacku runtime.
    image_effect_selector: str | None = None
    # Opcjonalna obsługa zestawów ustawień. Każdy wpis ma postać:
    # (wartość presetu, ((field_id, value), ...)).
    # GUI ustawia cały zestaw i rozpoznaje go ponownie po ręcznej edycji.
    preset_field_id: str | None = None
    preset_values: tuple[
        tuple[str, tuple[tuple[str, Any], ...]], ...
    ] = field(default_factory=tuple)
    custom_preset_value: str = "custom"
    recommended_preset_value: str | None = None
    field_group_variant_libraries: tuple[
        FieldGroupVariantLibrary, ...
    ] = field(default_factory=tuple)


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
    "ChoiceProvider",
    "FieldGroupVariantLibrary",
    "PathKey",
    "TemplateField",
    "TemplateZone",
    "_s",
    "zone_by_id",
    "zone_enabled",
    "set_zone_enabled",
]
