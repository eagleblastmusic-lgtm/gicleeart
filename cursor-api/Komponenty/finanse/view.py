"""Inline-view komponentu "Finanse"."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from Komponenty._shared.tile_grid import InlineTileView, TileSpec
from Komponenty._shared.toast import show_toast

_COMPONENT_DIR = Path(__file__).resolve().parent

_DEFAULT_WYLICZENIA = r"E:\Firma\2. Kalkulacja\GicleeArt3.xlsm"


def _ksiegowosc_in_progress(parent: tk.Misc, _spec) -> None:
    show_toast(parent, "W budowie", duration_ms=1600, bg="#444", fg="white")


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    tiles = [
        TileSpec(
            key="wyliczenia",
            label="Wyliczenia",
            icon="📊",
            color="#2e7d32",
            target_path=_DEFAULT_WYLICZENIA,
            target_kind="path",
            description="Otwiera arkusz GicleeArt3.xlsm.",
            settings_label="Plik Wyliczen (.xlsm)",
            settings_kind="file",
        ),
        TileSpec(
            key="ksiegowosc",
            label="Ksiegowosc",
            icon="🧾",
            color="#ef6c00",
            target_kind="callable",
            callback=_ksiegowosc_in_progress,
            description="(W budowie)",
        ),
    ]
    view = InlineTileView(
        title="Finanse",
        subtitle="Kalkulacje i ksiegowosc",
        tiles=tiles,
        component_dir=_COMPONENT_DIR,
        on_back=on_back,
    )
    return view.mount(parent)
