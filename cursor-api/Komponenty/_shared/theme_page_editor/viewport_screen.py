"""Puste ekrany o wysokości podanej w vh, wstawiane między sekcjami strony."""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import uuid4

from .config import PageEditorConfig
from .types import TemplateField, TemplateZone, _s


VIEWPORT_SCREEN_SECTION_TYPE = "giclee-viewport-screen"
VIEWPORT_SCREEN_ZONE_PREFIX = "viewport_screen_"
VIEWPORT_SCREEN_DEPLOY_RELPATHS = (
    "sections/giclee-viewport-screen.liquid",
)
MIN_VIEWPORT_HEIGHT_VH = 1
MAX_VIEWPORT_HEIGHT_VH = 10000
DEFAULT_VIEWPORT_HEIGHT_VH = 100


def template_supports_viewport_screen(template: dict[str, Any]) -> bool:
    return isinstance(template.get("sections"), dict) and isinstance(
        template.get("order"), list
    )


def normalize_viewport_height(value: object) -> int:
    try:
        height = int(round(float(str(value).replace(",", "."))))
    except (TypeError, ValueError) as exc:
        raise ValueError("Wysokość ekranu musi być liczbą w vh.") from exc
    if not MIN_VIEWPORT_HEIGHT_VH <= height <= MAX_VIEWPORT_HEIGHT_VH:
        raise ValueError(
            "Wysokość ekranu musi mieścić się w zakresie "
            f"{MIN_VIEWPORT_HEIGHT_VH}–{MAX_VIEWPORT_HEIGHT_VH} vh."
        )
    return height


def is_viewport_screen_section(section: object) -> bool:
    return (
        isinstance(section, dict)
        and section.get("type") == VIEWPORT_SCREEN_SECTION_TYPE
    )


def add_viewport_screen_section(
    template: dict[str, Any],
    *,
    height_vh: object = DEFAULT_VIEWPORT_HEIGHT_VH,
    after_section_key: str | None = None,
) -> str:
    """Wstaw pusty ekran bezpośrednio po wskazanej sekcji."""

    if not template_supports_viewport_screen(template):
        raise ValueError(
            "Ten dokument nie jest szablonem Shopify z listą sections/order."
        )
    height = normalize_viewport_height(height_vh)
    sections = template["sections"]
    order = template["order"]
    section_key = f"giclee_viewport_screen_{uuid4().hex[:9]}"
    while section_key in sections:
        section_key = f"giclee_viewport_screen_{uuid4().hex[:9]}"
    sections[section_key] = {
        "type": VIEWPORT_SCREEN_SECTION_TYPE,
        "name": f"Ekran {height}vh",
        "settings": {
            "viewport_height_vh": height,
        },
    }
    if after_section_key in order:
        order.insert(order.index(after_section_key) + 1, section_key)
    else:
        order.append(section_key)
    return section_key


def remove_viewport_screen_section(
    template: dict[str, Any],
    section_key: str,
) -> dict[str, Any]:
    """Usuń wyłącznie ekran utworzony przez ten moduł."""

    if not template_supports_viewport_screen(template):
        raise ValueError(
            "Ten dokument nie jest szablonem Shopify z listą sections/order."
        )
    clean_key = str(section_key or "").strip()
    section = template["sections"].get(clean_key)
    if not is_viewport_screen_section(section):
        raise ValueError("Wybrana sekcja nie jest ekranem utworzonym przez „Wstaw ekran”.")
    removed = dict(section)
    del template["sections"][clean_key]
    template["order"][:] = [
        key for key in template["order"] if str(key) != clean_key
    ]
    return removed


def viewport_screen_zone(
    section_key: str,
    section: dict[str, Any] | None = None,
) -> TemplateZone:
    source = section if isinstance(section, dict) else {}
    settings = source.get("settings")
    values = settings if isinstance(settings, dict) else {}
    try:
        height = normalize_viewport_height(
            values.get("viewport_height_vh", DEFAULT_VIEWPORT_HEIGHT_VH)
        )
    except ValueError:
        height = DEFAULT_VIEWPORT_HEIGHT_VH
    label = str(source.get("name") or "").strip() or f"Ekran {height}vh"
    return TemplateZone(
        zone_id=f"{VIEWPORT_SCREEN_ZONE_PREFIX}{section_key}",
        label=label,
        description=(
            "Pusty ekran wstawiony pomiędzy sekcjami. Wysokość jest podawana "
            "w jednostkach vh: 100 vh oznacza jeden pełny viewport."
        ),
        section_key=section_key,
        fields=(
            TemplateField(
                "viewport_height_vh",
                "Wysokość pustego ekranu",
                "int",
                _s(section_key, "settings", "viewport_height_vh"),
                hint=(
                    "Wpisz własną wysokość w vh, np. 100 = jeden ekran, "
                    "200 = dwa ekrany."
                ),
                min_value=MIN_VIEWPORT_HEIGHT_VH,
                max_value=MAX_VIEWPORT_HEIGHT_VH,
                step=1,
                unit="vh",
                free_entry=True,
            ),
        ),
    )


def discover_viewport_screen_zones(
    template: dict[str, Any],
    *,
    exclude_section_keys: set[str] | None = None,
) -> tuple[TemplateZone, ...]:
    sections = template.get("sections")
    order = template.get("order")
    if not isinstance(sections, dict) or not isinstance(order, list):
        return ()
    excluded = exclude_section_keys or set()
    zones: list[TemplateZone] = []
    for raw_key in order:
        section_key = str(raw_key)
        section = sections.get(section_key)
        if (
            section_key in excluded
            or not is_viewport_screen_section(section)
        ):
            continue
        zones.append(viewport_screen_zone(section_key, section))
    return tuple(zones)


def config_with_viewport_screen_zones(
    config: PageEditorConfig,
    template: dict[str, Any],
) -> PageEditorConfig:
    static_keys = {zone.section_key for zone in config.zones}
    dynamic = discover_viewport_screen_zones(
        template,
        exclude_section_keys=static_keys,
    )
    if not dynamic:
        return config

    order = [
        str(section_key)
        for section_key in template.get("order", [])
    ]
    order_index = {section_key: index for index, section_key in enumerate(order)}
    zones = list(config.zones)
    for screen_zone in dynamic:
        screen_position = order_index.get(screen_zone.section_key, len(order))
        insert_at = len(zones)
        for index, existing in enumerate(zones):
            existing_position = order_index.get(existing.section_key)
            if existing_position is not None and existing_position > screen_position:
                insert_at = index
                break
        zones.insert(insert_at, screen_zone)
    return replace(config, zones=tuple(zones))


def template_has_viewport_screen(template: dict[str, Any]) -> bool:
    sections = template.get("sections")
    return isinstance(sections, dict) and any(
        is_viewport_screen_section(section)
        for section in sections.values()
    )


__all__ = [
    "DEFAULT_VIEWPORT_HEIGHT_VH",
    "MAX_VIEWPORT_HEIGHT_VH",
    "MIN_VIEWPORT_HEIGHT_VH",
    "VIEWPORT_SCREEN_DEPLOY_RELPATHS",
    "VIEWPORT_SCREEN_SECTION_TYPE",
    "VIEWPORT_SCREEN_ZONE_PREFIX",
    "add_viewport_screen_section",
    "config_with_viewport_screen_zones",
    "discover_viewport_screen_zones",
    "is_viewport_screen_section",
    "normalize_viewport_height",
    "remove_viewport_screen_section",
    "template_has_viewport_screen",
    "template_supports_viewport_screen",
    "viewport_screen_zone",
]
