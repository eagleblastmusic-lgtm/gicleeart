"""Deklaratywna mapa komponentów z obsługą tła — read-only awareness dla Studio Preview."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BackgroundTier = Literal["bio_workflow", "section_background", "theme_image_bg"]


@dataclass(frozen=True)
class BackgroundCapability:
    tier: BackgroundTier
    label: str
    source_hint: str
    inline_note: str


_TIER_LABELS: dict[BackgroundTier, str] = {
    "bio_workflow": "Workflow BIO (Tier 1)",
    "section_background": "Tło sekcji (Tier 2)",
    "theme_image_bg": "Obraz tła motywu (Tier 3)",
}


_CAPABILITIES: dict[str, BackgroundCapability] = {
    "tldobio": BackgroundCapability(
        tier="bio_workflow",
        label="Tło sekcji BIO",
        source_hint="Metafield kolekcji · upload w komponencie inline",
        inline_note="Upload, kadr i gradient w komponencie inline · metafieldy kolekcji",
    ),
    "stronaglowna": BackgroundCapability(
        tier="section_background",
        label="Tło sekcji strony głównej",
        source_hint="5 stref section_background · edytor motywu inline",
        inline_note="5 stref section_background w edytorze strony głównej inline",
    ),
}


def tier_display(tier: BackgroundTier) -> str:
    return _TIER_LABELS.get(tier, tier)


def capability_for(folder_name: str) -> BackgroundCapability | None:
    key = (folder_name or "").strip()
    if not key:
        return None
    return _CAPABILITIES.get(key)


def folders_with_background() -> frozenset[str]:
    return frozenset(_CAPABILITIES.keys())


__all__ = [
    "BackgroundCapability",
    "BackgroundTier",
    "capability_for",
    "folders_with_background",
    "tier_display",
]
