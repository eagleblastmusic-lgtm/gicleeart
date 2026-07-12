"""Warianty wyróżnienia aktywnego artysty w submenu Katalog."""

from __future__ import annotations

ARTIST_HOVER_EFFECT_FIELD_ID = "artist_hover_effect"
ARTIST_HOVER_EFFECT_FIELD_LABEL = "Efekt aktywnego artysty"
DEFAULT_ARTIST_HOVER_EFFECT = "classic"

ARTIST_HOVER_EFFECT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("classic", "Klasyczny"),
    ("curatorial_glow", "Kuratorskie światło"),
    ("depth_of_field", "Głębia ostrości"),
    ("museum_marker", "Znacznik muzealny"),
    ("preview_focus", "Focus obrazu"),
)

ARTIST_HOVER_EFFECT_LABEL_BY_ID = dict(ARTIST_HOVER_EFFECT_OPTIONS)
ARTIST_HOVER_EFFECT_ID_BY_LABEL = {
    label: effect_id for effect_id, label in ARTIST_HOVER_EFFECT_OPTIONS
}


def normalize_artist_hover_effect(value: object) -> str:
    """Zwróć obsługiwany identyfikator albo bezpieczny wariant klasyczny."""

    effect_id = str(value or "").strip()
    if effect_id in ARTIST_HOVER_EFFECT_LABEL_BY_ID:
        return effect_id
    return DEFAULT_ARTIST_HOVER_EFFECT


__all__ = [
    "ARTIST_HOVER_EFFECT_FIELD_ID",
    "ARTIST_HOVER_EFFECT_FIELD_LABEL",
    "ARTIST_HOVER_EFFECT_ID_BY_LABEL",
    "ARTIST_HOVER_EFFECT_LABEL_BY_ID",
    "ARTIST_HOVER_EFFECT_OPTIONS",
    "DEFAULT_ARTIST_HOVER_EFFECT",
    "normalize_artist_hover_effect",
]
