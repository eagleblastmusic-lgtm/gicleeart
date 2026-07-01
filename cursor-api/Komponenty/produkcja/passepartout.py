"""Kolor passepartout z line item property Shopify (nie wariant)."""

from __future__ import annotations

from typing import Any

PASSEPARTOUT_PROPERTY_KEY = "Passepartout"
PASSEPARTOUT_VALUES = ("Białe", "Czarne")
PASSEPARTOUT_DEFAULT = "Białe"

_PROPERTY_ALIASES = frozenset(
    {
        "passepartout",
        "kolor passepartout",
        "kolor passe-partout",
        "passe-partout",
    }
)


def normalize_passepartout(value: str | None) -> str:
    v = (value or "").strip().casefold().replace("ą", "a").replace("ę", "e")
    if v in ("czarny", "czarne", "black"):
        return "Czarne"
    if v in ("bialy", "biale", "white", ""):
        return PASSEPARTOUT_DEFAULT
    raw = (value or "").strip()
    if raw in PASSEPARTOUT_VALUES:
        return raw
    # kompatybilność wsteczna (stare zamówienia)
    if raw in ("Biały", "Czarny"):
        return "Czarne" if raw == "Czarny" else "Białe"
    return PASSEPARTOUT_DEFAULT


def parse_passepartout_from_line(line: dict[str, Any]) -> str:
    """Czyta kolor passepartout z properties pozycji zamówienia Shopify."""
    props = line.get("properties") or []
    if isinstance(props, dict):
        for key, val in props.items():
            name = str(key or "").strip()
            if name.casefold() in _PROPERTY_ALIASES or name == PASSEPARTOUT_PROPERTY_KEY:
                return normalize_passepartout(str(val or ""))
        return ""

    for prop in props:
        if not isinstance(prop, dict):
            continue
        name = str(prop.get("name") or "").strip()
        val = str(prop.get("value") or "").strip()
        if not val:
            continue
        if name == PASSEPARTOUT_PROPERTY_KEY or name.casefold() in _PROPERTY_ALIASES:
            return normalize_passepartout(val)
    return ""


def parse_passepartout_from_config(config: dict[str, Any] | None) -> str:
    if not config:
        return ""
    for key in ("passepartout", "passe_partout", "pp"):
        if key in config:
            return normalize_passepartout(str(config.get(key) or ""))
    return ""
