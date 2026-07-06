"""Deklaratywne typy assetów tła — Studio Preview (F5.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AssetKind = Literal["image", "video", "video_collage"]


@dataclass(frozen=True)
class BackgroundAssetType:
    kind: AssetKind
    label_pl: str
    hint: str


BACKGROUND_ASSET_TYPES: tuple[BackgroundAssetType, ...] = (
    BackgroundAssetType(
        kind="image",
        label_pl="obraz",
        hint="Tło sekcji jako grafika (section_background · media=image)",
    ),
    BackgroundAssetType(
        kind="video",
        label_pl="wideo",
        hint="Tło sekcji jako plik wideo (section_background · media=video)",
    ),
    BackgroundAssetType(
        kind="video_collage",
        label_pl="kolaż wideo",
        hint="Kolaż hero — osobne pole video_collage (informacyjnie w shellu F5.1)",
    ),
)


def asset_type_labels_pl() -> tuple[str, ...]:
    return tuple(row.label_pl for row in BACKGROUND_ASSET_TYPES)


__all__ = [
    "AssetKind",
    "BackgroundAssetType",
    "BACKGROUND_ASSET_TYPES",
    "asset_type_labels_pl",
]
