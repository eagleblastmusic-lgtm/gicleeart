"""Read-only shell biblioteki assetów — Studio Preview (F5.1 / F5.1b)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from giclee_app.studio.background_asset_types import asset_type_labels_pl
from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    stronaglowna_zone_statuses,
)

_SHELL_TITLE = "Biblioteka / Assety"
_F51B_HEADER = "F5.1b · read-only · aktywny wariant"
_FALLBACK = (
    "Nie udało się odczytać przypisań z aktywnego wariantu · "
    "edytor inline pozostaje źródłem prawdy"
)
_F52_NOTE = "Draft wyboru w F5.2 · Podgląd koncepcyjny w F5.3 · Zapis w F5.4"


@dataclass(frozen=True)
class AssetLibrarySection:
    """Sekcja panelu — tytuł + wielolinijkowy body."""

    title: str
    body: str


def asset_library_section(
    folder_name: str,
    package_path: Path | None = None,
) -> AssetLibrarySection | None:
    """Pure read-only shell — bounded manifest + index dla stronaglowna."""
    key = (folder_name or "").strip()
    if key != "stronaglowna":
        return None
    if package_path is None:
        return AssetLibrarySection(title=_SHELL_TITLE, body=_build_types_only_body())
    return AssetLibrarySection(
        title=_SHELL_TITLE,
        body=_build_stronaglowna_body(Path(package_path)),
    )


def asset_library_rows(
    folder_name: str,
    package_path: Path | None = None,
) -> tuple[tuple[str, str], ...]:
    """Wiersze (title, body) do wstawienia w panel_rows."""
    section = asset_library_section(folder_name, package_path)
    if section is None:
        return ()
    return ((section.title, section.body),)


def _build_types_only_body() -> str:
    labels = " · ".join(asset_type_labels_pl())
    return "\n".join(
        [
            _F51B_HEADER,
            _FALLBACK,
            f"Typy assetów: {labels}",
            _F52_NOTE,
        ]
    )


def _build_stronaglowna_body(package_path: Path) -> str:
    active_info, zone_rows = stronaglowna_zone_statuses(package_path)
    labels = " · ".join(asset_type_labels_pl())
    lines: list[str] = [_F51B_HEADER]

    if active_info is not None:
        active_id, active_label = active_info
        lines.append(f"Aktywny wariant: {active_id} · {active_label}")
    else:
        lines.append("Aktywny wariant: nieznany (brak manifest.json)")

    if zone_rows is None:
        lines.extend([_FALLBACK, f"Typy assetów: {labels}", _F52_NOTE])
        return "\n".join(lines)

    lines.append(f"Przypisania section_background ({len(STRONAGLOWNA_SECTION_BGS)}):")
    for zone, status in zone_rows:
        lines.append(f"· {zone.field_id} ({zone.label}): {status}")

    lines.extend([f"Typy assetów: {labels}", _F52_NOTE])
    return "\n".join(lines)


__all__ = [
    "AssetLibrarySection",
    "asset_library_rows",
    "asset_library_section",
]
