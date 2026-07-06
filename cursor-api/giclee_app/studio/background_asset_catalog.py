"""Bounded katalog assetów section_background — Studio Preview (F5.4d). Pure read-only."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from giclee_app.studio.background_asset_types import AssetKind
from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    read_stronaglowna_index_template,
)

CatalogKind = Literal["image", "video"]

ASSET_SELECTION_SECTION_TITLE = "Wybór assetu"
ASSET_SELECTION_BADGE = "draft lokalny · wybór ref"
ASSET_SELECTION_EMPTY = "Brak dostępnych assetów tego typu w aktywnym wariancie"
ASSET_SELECTION_HINT = "Wybierz istniejący asset z aktywnego wariantu · bez uploadu"


@dataclass(frozen=True)
class BackgroundAssetEntry:
    """Pozycja katalogu — display_label bez pełnego ref w UI."""

    asset_id: str
    kind: CatalogKind
    display_label: str
    ref: str


@dataclass(frozen=True)
class BackgroundAssetCatalog:
    entries: tuple[BackgroundAssetEntry, ...]


def catalog_enabled_for_folder(folder_name: str) -> bool:
    return (folder_name or "").strip() == "stronaglowna"


def build_background_asset_catalog(package_path: Path) -> BackgroundAssetCatalog:
    """Refs z 5 stref section_background aktywnego wariantu — dedupe, bez skanów dysku."""
    index_template = read_stronaglowna_index_template(package_path)
    if index_template is None:
        return BackgroundAssetCatalog(entries=())

    sections = index_template.get("sections")
    if not isinstance(sections, dict):
        return BackgroundAssetCatalog(entries=())

    image_refs: set[str] = set()
    video_refs: set[str] = set()

    for zone in STRONAGLOWNA_SECTION_BGS:
        section = sections.get(zone.section_key)
        if not isinstance(section, dict):
            continue
        settings = section.get("settings")
        if not isinstance(settings, dict):
            continue
        _collect_zone_refs(settings, image_refs, video_refs)

    entries: list[BackgroundAssetEntry] = []
    for idx, ref in enumerate(sorted(image_refs)):
        entries.append(
            BackgroundAssetEntry(
                asset_id=f"img:{idx}",
                kind="image",
                display_label=ref_to_display_label(ref),
                ref=ref,
            )
        )
    for idx, ref in enumerate(sorted(video_refs)):
        entries.append(
            BackgroundAssetEntry(
                asset_id=f"vid:{idx}",
                kind="video",
                display_label=ref_to_display_label(ref),
                ref=ref,
            )
        )
    return BackgroundAssetCatalog(entries=tuple(entries))


def filter_by_kind(
    catalog: BackgroundAssetCatalog,
    kind: CatalogKind,
) -> tuple[BackgroundAssetEntry, ...]:
    return tuple(entry for entry in catalog.entries if entry.kind == kind)


def filter_entries_for_draft_kind(
    catalog: BackgroundAssetCatalog,
    asset_kind: AssetKind | None,
) -> tuple[BackgroundAssetEntry, ...]:
    if asset_kind == "image":
        return filter_by_kind(catalog, "image")
    if asset_kind == "video":
        return filter_by_kind(catalog, "video")
    return ()


def find_entry_by_id(
    catalog: BackgroundAssetCatalog,
    asset_id: str | None,
) -> BackgroundAssetEntry | None:
    if not asset_id:
        return None
    for entry in catalog.entries:
        if entry.asset_id == asset_id:
            return entry
    return None


def validate_selected_asset_id(
    asset_id: str | None,
    catalog: BackgroundAssetCatalog,
    *,
    asset_kind: AssetKind | None,
) -> bool:
    if not asset_id or asset_kind not in ("image", "video"):
        return False
    entry = find_entry_by_id(catalog, asset_id)
    if entry is None:
        return False
    return entry.kind == asset_kind


def resolve_selected_asset_ref(
    catalog: BackgroundAssetCatalog,
    asset_id: str | None,
) -> str | None:
    entry = find_entry_by_id(catalog, asset_id)
    if entry is None:
        return None
    ref = entry.ref.strip()
    return ref or None


def ref_to_display_label(ref: str) -> str:
    """Krótka etykieta bez pełnego shopify:// w copy panelu."""
    value = (ref or "").strip()
    if not value:
        return "—"
    if "/" in value:
        return value.rsplit("/", 1)[-1]
    if ":" in value:
        return value.rsplit(":", 1)[-1]
    if len(value) > 48:
        return value[:45] + "..."
    return value


def _collect_zone_refs(
    settings: dict[str, Any],
    image_refs: set[str],
    video_refs: set[str],
) -> None:
    media = str(settings.get("background_media") or "none").strip().lower()
    image_ref = str(settings.get("background_image") or "").strip()
    video_ref = str(settings.get("video") or "").strip()

    if media == "video":
        if video_ref:
            video_refs.add(video_ref)
        return
    if media == "image":
        if image_ref:
            image_refs.add(image_ref)
        return
    if video_ref:
        video_refs.add(video_ref)
    elif image_ref:
        if "/videos/" in image_ref or image_ref.startswith("gid://shopify/Video/"):
            video_refs.add(image_ref)
        else:
            image_refs.add(image_ref)


__all__ = [
    "ASSET_SELECTION_BADGE",
    "ASSET_SELECTION_EMPTY",
    "ASSET_SELECTION_HINT",
    "ASSET_SELECTION_SECTION_TITLE",
    "BackgroundAssetCatalog",
    "BackgroundAssetEntry",
    "CatalogKind",
    "build_background_asset_catalog",
    "catalog_enabled_for_folder",
    "filter_by_kind",
    "filter_entries_for_draft_kind",
    "find_entry_by_id",
    "ref_to_display_label",
    "resolve_selected_asset_ref",
    "validate_selected_asset_id",
]
