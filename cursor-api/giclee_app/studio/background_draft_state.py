"""Lokalny draft wyboru tła — Studio Preview (F5.2 / F5.4d). Tylko in-memory, bez I/O."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.background_asset_types import (
    BACKGROUND_ASSET_TYPES,
    AssetKind,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS, SectionBgZone

DRAFT_SECTION_TITLE = "Draft wyboru"
DRAFT_BADGE = "draft lokalny · niezapisany"
DRAFT_EMPTY_COPY = "Brak draftu · wybierz strefę i typ assetu"
DRAFT_DISCLAIMER = "F5.2 nie zapisuje zmian. Zapis będzie osobną fazą F5.4."
CLEAR_DRAFT_LABEL = "Wyczyść draft"


@dataclass
class BackgroundDraftState:
    """Draft strefy + typu assetu + wybrany ref — wyłącznie w pamięci UI panelu."""

    zone_field_id: str | None = None
    asset_kind: AssetKind | None = None
    selected_asset_id: str | None = None

    def is_empty(self) -> bool:
        return self.zone_field_id is None or self.asset_kind is None

    def has_selected_asset(self) -> bool:
        return bool(self.selected_asset_id)

    def clear(self) -> None:
        self.zone_field_id = None
        self.asset_kind = None
        self.selected_asset_id = None

    def clear_selected_asset(self) -> None:
        self.selected_asset_id = None

    def set_zone(self, field_id: str) -> None:
        value = (field_id or "").strip()
        self.zone_field_id = value or None

    def set_kind(self, kind: AssetKind) -> None:
        if self.asset_kind != kind:
            self.selected_asset_id = None
        self.asset_kind = kind

    def set_selected_asset(self, asset_id: str) -> None:
        value = (asset_id or "").strip()
        self.selected_asset_id = value or None

    def zone_display(self) -> str:
        zone = _zone_by_field_id(self.zone_field_id)
        if zone is not None:
            return f"{zone.field_id} ({zone.label})"
        if self.zone_field_id:
            return f"nieznana strefa ({self.zone_field_id})"
        return "—"

    def kind_label_pl(self) -> str:
        if self.asset_kind is None:
            return "—"
        for row in BACKGROUND_ASSET_TYPES:
            if row.kind == self.asset_kind:
                return row.label_pl
        return self.asset_kind

    def format_summary(self, *, selected_label: str | None = None) -> str:
        if self.is_empty():
            return DRAFT_EMPTY_COPY
        base = (
            f"Draft lokalny: {self.zone_display()} → {self.kind_label_pl()} · niezapisany"
        )
        if self.selected_asset_id:
            label = selected_label or "wybrany asset"
            return f"{base} · {label}"
        return base


def asset_selection_visible(draft: BackgroundDraftState) -> bool:
    """Picker tylko dla image/video z kompletnym draftem."""
    if draft.is_empty():
        return False
    return draft.asset_kind in ("image", "video")


def draft_enabled_for_folder(folder_name: str) -> bool:
    return (folder_name or "").strip() == "stronaglowna"


def zone_menu_options() -> tuple[tuple[str, str], ...]:
    """(field_id, etykieta menu) dla 5 stref section_background."""
    return tuple(
        (zone.field_id, f"{zone.field_id} — {zone.label}")
        for zone in STRONAGLOWNA_SECTION_BGS
    )


def kind_menu_options() -> tuple[tuple[AssetKind, str], ...]:
    """(kind, label_pl) dla typów assetów."""
    return tuple((row.kind, row.label_pl) for row in BACKGROUND_ASSET_TYPES)


def _zone_by_field_id(field_id: str | None) -> SectionBgZone | None:
    if not field_id:
        return None
    for zone in STRONAGLOWNA_SECTION_BGS:
        if zone.field_id == field_id:
            return zone
    return None


__all__ = [
    "BackgroundDraftState",
    "CLEAR_DRAFT_LABEL",
    "DRAFT_BADGE",
    "DRAFT_DISCLAIMER",
    "DRAFT_EMPTY_COPY",
    "DRAFT_SECTION_TITLE",
    "asset_selection_visible",
    "draft_enabled_for_folder",
    "kind_menu_options",
    "zone_menu_options",
]
