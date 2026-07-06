"""Asset Lab — statyczny katalog narzędzi graficznych (F6.2, read-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssetLabRisk = Literal["N", "M", "H"]

_WORKFLOW_SUMMARY = (
    "Warsztat graficzny — przetwarzanie plików przed dalszym pipeline'em. "
    "Każde narzędzie uruchamia się jako osobny proces (legacy backend)."
)

_STATUS_STRIP = "8 narzędzi · launch-only · legacy backend"

_LAUNCH_BUTTON_LABEL = "Otwórz narzędzie"
LEGACY_BACKEND_BADGE = "legacy backend"
UNAVAILABLE_LABEL = "niedostępny"


@dataclass(frozen=True)
class AssetLabTool:
    folder: str
    summary: str
    risk: AssetLabRisk
    sort_order: int


_TOOLS: tuple[AssetLabTool, ...] = (
    AssetLabTool(
        folder="nazwijobraz",
        summary="Konwencja nazw plików reprodukcji na dysku lokalnym.",
        risk="N",
        sort_order=1,
    ),
    AssetLabTool(
        folder="infoplikow",
        summary="Metadane plików graficznych — rozmiar, format, EXIF.",
        risk="N",
        sort_order=2,
    ),
    AssetLabTool(
        folder="squoosh",
        summary="Kolejka konwersji do WebP (Squoosh CLI lub Pillow).",
        risk="N",
        sort_order=3,
    ),
    AssetLabTool(
        folder="print_optimize",
        summary="Optymalizacja obrazów pod druk — pipeline PIL.",
        risk="N",
        sort_order=4,
    ),
    AssetLabTool(
        folder="przedpo",
        summary="Porównanie wersji obrazu — przed i po korekcji.",
        risk="N",
        sort_order=5,
    ),
    AssetLabTool(
        folder="kolaz",
        summary="Składanie wielu obrazów w jedną grafikę — presety BIO i układy.",
        risk="M",
        sort_order=6,
    ),
    AssetLabTool(
        folder="mockup",
        summary="Mock-up katalogowy w ramce A4 — render lokalny, publish w legacy.",
        risk="H",
        sort_order=7,
    ),
    AssetLabTool(
        folder="pobierzobraz",
        summary="Pobranie obrazu produktu z Shopify lub CDN.",
        risk="M",
        sort_order=8,
    ),
)

ASSET_LAB_FOLDERS: tuple[str, ...] = tuple(t.folder for t in _TOOLS)


def workflow_summary() -> str:
    return _WORKFLOW_SUMMARY


def status_strip() -> str:
    return _STATUS_STRIP


def launch_button_label() -> str:
    return _LAUNCH_BUTTON_LABEL


def tools_in_order() -> tuple[AssetLabTool, ...]:
    return _TOOLS


def is_asset_lab_folder(folder: str) -> bool:
    key = (folder or "").strip()
    return key in ASSET_LAB_FOLDERS


def tool_for_folder(folder: str) -> AssetLabTool | None:
    key = (folder or "").strip()
    for tool in _TOOLS:
        if tool.folder == key:
            return tool
    return None


__all__ = [
    "ASSET_LAB_FOLDERS",
    "AssetLabRisk",
    "AssetLabTool",
    "is_asset_lab_folder",
    "launch_button_label",
    "status_strip",
    "tool_for_folder",
    "tools_in_order",
    "workflow_summary",
]
