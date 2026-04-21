"""Inline-view komponentu "Obrazy".

Eksponuje `build_view(parent, on_back)` wymaganaprzez launcher (mode=inline).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from Komponenty._shared.tile_grid import InlineTileView, TileSpec

_COMPONENT_DIR = Path(__file__).resolve().parent

_DEFAULT_REPRODUKCJE = r"E:\Firma\1. Obrazy\2. Reprodukcje\Reprodukcje Mistrzów\1. OK"
_DEFAULT_KLIENCI = r"E:\Firma\1. Obrazy\3. Klienci"


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    tiles = [
        TileSpec(
            key="reprodukcje",
            label="Reprodukcje Mistrzow",
            icon="🎨",
            color="#1565c0",
            target_path=_DEFAULT_REPRODUKCJE,
            target_kind="path",
            description="Folder z gotowymi reprodukcjami mistrzow.",
            settings_label="Folder Reprodukcji Mistrzow",
            settings_kind="folder",
        ),
        TileSpec(
            key="klienci",
            label="Obrazy Klientow",
            icon="👥",
            color="#26a69a",
            target_path=_DEFAULT_KLIENCI,
            target_kind="path",
            description="Folder z obrazami klientow.",
            settings_label="Folder Obrazow Klientow",
            settings_kind="folder",
        ),
    ]
    view = InlineTileView(
        title="Obrazy",
        subtitle="Kliknij kafelek aby otworzyc folder w Eksploratorze",
        tiles=tiles,
        component_dir=_COMPONENT_DIR,
        on_back=on_back,
    )
    return view.mount(parent)
