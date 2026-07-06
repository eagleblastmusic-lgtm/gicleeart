"""Read-only shell biblioteki assetów — Studio Preview (F5.1)."""

from __future__ import annotations

from dataclasses import dataclass

from giclee_app.studio.background_asset_types import BACKGROUND_ASSET_TYPES
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_SHELL_TITLE = "Biblioteka / Assety"
_SHELL_NOTE = "F5.1 to shell read-only · wybór assetu będzie dostępny w kolejnych fazach"
_PLACEHOLDER = "Wybór assetu będzie dostępny w kolejnych fazach"


@dataclass(frozen=True)
class AssetLibrarySection:
    """Sekcja panelu — tytuł + wielolinijkowy body."""

    title: str
    body: str


def asset_library_section(folder_name: str) -> AssetLibrarySection | None:
    """Pure shell dla panelu tła — bez I/O, bez listowania plików."""
    key = (folder_name or "").strip()
    if key != "stronaglowna":
        return None
    return AssetLibrarySection(title=_SHELL_TITLE, body=_build_stronaglowna_body())


def asset_library_rows(folder_name: str) -> tuple[tuple[str, str], ...]:
    """Wiersze (title, body) do wstawienia w panel_rows — pusty dla innych komponentów."""
    section = asset_library_section(folder_name)
    if section is None:
        return ()
    return ((section.title, section.body),)


def _build_stronaglowna_body() -> str:
    type_lines = [f"· {row.label_pl} — {row.hint}" for row in BACKGROUND_ASSET_TYPES]
    zone_lines = [
        f"· {zone.field_id} ({zone.label})" for zone in STRONAGLOWNA_SECTION_BGS
    ]
    blocks = [
        _SHELL_NOTE,
        f"Obsługiwane typy assetów ({len(BACKGROUND_ASSET_TYPES)}):",
        *type_lines,
        f"Strefy section_background ({len(STRONAGLOWNA_SECTION_BGS)}):",
        *zone_lines,
        _PLACEHOLDER,
    ]
    return "\n".join(blocks)


__all__ = [
    "AssetLibrarySection",
    "asset_library_rows",
    "asset_library_section",
]
