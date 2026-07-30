"""Wspólny moduł konfiguracji przewijania całej strony."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .config import PageEditorConfig
from .types import TemplateField, TemplateZone, _s


PAGE_SCROLL_SECTION_TYPE = "giclee-page-scroll-config"
LEGACY_PAGE_SCROLL_SECTION_TYPE = "giclee-filozofia-page-config"
PAGE_SCROLL_ZONE_PREFIX = "page_scroll_"
PAGE_SCROLL_DEPLOY_RELPATHS = (
    "assets/giclee-page-smooth-scroll.js",
    "assets/lenis.min.js",
    "assets/lenis.css",
    "sections/giclee-page-scroll-config.liquid",
)


def template_supports_page_scroll(template: dict[str, Any]) -> bool:
    return isinstance(template.get("sections"), dict) and isinstance(
        template.get("order"), list
    )


def page_scroll_section_key(template: dict[str, Any]) -> str | None:
    sections = template.get("sections")
    if not isinstance(sections, dict):
        return None
    for section_key, section in sections.items():
        if not isinstance(section, dict):
            continue
        if section.get("type") in {
            PAGE_SCROLL_SECTION_TYPE,
            LEGACY_PAGE_SCROLL_SECTION_TYPE,
        }:
            return str(section_key)
    return None


def template_has_page_scroll(template: dict[str, Any]) -> bool:
    return page_scroll_section_key(template) is not None


def _default_page_scroll_settings() -> dict[str, Any]:
    return {
        "page_scroll_mode": "standard",
        "scroll_smoothness": 75,
        "scroll_wheel_gain": 1.05,
        "scroll_lenis_preset": "balanced",
        "scroll_lenis_lerp": 0.245,
        "scroll_lenis_wheel_multiplier": 1.05,
        "scroll_lenis_smooth_wheel": True,
        "scroll_lenis_overscroll": True,
        "scroll_lenis_anchors": True,
        "scroll_lenis_stop_inertia_on_navigate": True,
        "scroll_line_height_px": 40,
        "scroll_page_delta_ratio": 0.9,
        "scroll_max_wheel_delta_px": 420,
        "scroll_max_target_lead_px": 800,
        "scroll_follow_tau_ms": 75,
        "scroll_stop_epsilon_px": 0.25,
        "scroll_max_frame_delta_ms": 48,
    }


def add_page_scroll_section(
    template: dict[str, Any],
    *,
    after_section_key: str | None = None,
) -> str:
    """Dodaj jedną ukrytą konfigurację globalnego scrolla i zwróć section key."""

    if not template_supports_page_scroll(template):
        raise ValueError(
            "Ten dokument nie jest szablonem Shopify z listą sections/order."
        )
    existing = page_scroll_section_key(template)
    if existing is not None:
        return existing

    section_key = "giclee_page_scroll_config"
    suffix = 2
    sections = template["sections"]
    while section_key in sections:
        section_key = f"giclee_page_scroll_config_{suffix}"
        suffix += 1
    sections[section_key] = {
        "type": PAGE_SCROLL_SECTION_TYPE,
        "name": "Scroll strony",
        "settings": _default_page_scroll_settings(),
    }

    order = template["order"]
    if after_section_key in order:
        order.insert(order.index(after_section_key) + 1, section_key)
    else:
        order.insert(0, section_key)
    return section_key


def _base_page_scroll_zone() -> TemplateZone:
    # Referencyjny katalog pól pozostaje jeden. Import jest leniwy, aby
    # wspólny edytor nie tworzył cyklu podczas ładowania rejestru Filozofii.
    from Komponenty.filozofiamarki.registry import PAGE_ZONES

    return next(zone for zone in PAGE_ZONES if zone.zone_id == "page_scroll")


def _remap_field(field: TemplateField, section_key: str) -> TemplateField:
    path = field.path
    if path and len(path) >= 3 and path[0] == "sections":
        path = _s(section_key, *path[2:])
    return replace(field, path=path)


def page_scroll_zone(section_key: str) -> TemplateZone:
    base = _base_page_scroll_zone()
    return replace(
        base,
        zone_id=f"{PAGE_SCROLL_ZONE_PREFIX}{section_key}",
        label="Scroll strony",
        description=(
            "Sposób przewijania całej bieżącej strony: natywny, płynny, "
            "Lenis albo własne parametry techniczne."
        ),
        section_key=section_key,
        fields=tuple(_remap_field(field, section_key) for field in base.fields),
    )


def discover_page_scroll_zones(
    template: dict[str, Any],
    *,
    exclude_section_keys: set[str] | None = None,
) -> tuple[TemplateZone, ...]:
    section_key = page_scroll_section_key(template)
    if section_key is None or section_key in (exclude_section_keys or set()):
        return ()
    return (page_scroll_zone(section_key),)


def config_with_page_scroll_zones(
    config: PageEditorConfig,
    template: dict[str, Any],
) -> PageEditorConfig:
    static_keys = {zone.section_key for zone in config.zones}
    dynamic = discover_page_scroll_zones(
        template,
        exclude_section_keys=static_keys,
    )
    return replace(config, zones=(*config.zones, *dynamic))


__all__ = [
    "LEGACY_PAGE_SCROLL_SECTION_TYPE",
    "PAGE_SCROLL_DEPLOY_RELPATHS",
    "PAGE_SCROLL_SECTION_TYPE",
    "PAGE_SCROLL_ZONE_PREFIX",
    "add_page_scroll_section",
    "config_with_page_scroll_zones",
    "discover_page_scroll_zones",
    "page_scroll_section_key",
    "page_scroll_zone",
    "template_has_page_scroll",
    "template_supports_page_scroll",
]
