"""Koncepcyjny podgląd draftu tła — Studio Preview (F5.3). Pure, bez apply i bez I/O."""

from __future__ import annotations

from giclee_app.studio.background_asset_types import AssetKind
from giclee_app.studio.background_draft_state import (
    BackgroundDraftState,
    draft_enabled_for_folder,
)

PREVIEW_SECTION_TITLE = "Podgląd draftu"
PREVIEW_EMPTY_COPY = "Podgląd pojawi się po wyborze strefy i typu"
PREVIEW_BADGE = "podgląd koncepcyjny · niezastosowany"
PREVIEW_DISCLAIMER = (
    "F5.3 nie stosuje zmian. Zapis i realne zastosowanie będą osobną fazą F5.4."
)

_PLACEHOLDERS: dict[AssetKind, str] = {
    "image": "placeholder obrazu",
    "video": "placeholder wideo",
    "video_collage": "placeholder kolażu",
}


def preview_enabled_for_folder(folder_name: str) -> bool:
    return draft_enabled_for_folder(folder_name)


def placeholder_label_for_kind(kind: AssetKind | None) -> str:
    if kind is None:
        return "—"
    return _PLACEHOLDERS.get(kind, kind)


def format_preview_body(draft: BackgroundDraftState) -> str:
    """Wielolinijkowy tekst podglądu — testowalny bez Tk."""
    if draft.is_empty():
        return PREVIEW_EMPTY_COPY
    lines = [
        PREVIEW_BADGE,
        f"Strefa: {draft.zone_display()}",
        f"Typ: {draft.kind_label_pl()}",
        placeholder_label_for_kind(draft.asset_kind),
        PREVIEW_DISCLAIMER,
    ]
    return "\n".join(lines)


__all__ = [
    "PREVIEW_BADGE",
    "PREVIEW_DISCLAIMER",
    "PREVIEW_EMPTY_COPY",
    "PREVIEW_SECTION_TITLE",
    "format_preview_body",
    "placeholder_label_for_kind",
    "preview_enabled_for_folder",
]
