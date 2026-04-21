"""Inline-view komponentu "Ceny w marketingu".

Otwiera samodzielna aplikacje webowa (index.html) w domyslnej przegladarce.
Aplikacja zawiera: kalkulator cen, edytowalna tabele kosztow, symulator P&L,
what-if, LTV/CAC, kalendarz promocji, storytelling cheat-sheet i benchmark
konkurencji.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path

from Komponenty._shared.tile_grid import InlineTileView, TileSpec
from Komponenty._shared.toast import show_toast

_COMPONENT_DIR = Path(__file__).resolve().parent
_INDEX_HTML = _COMPONENT_DIR / "index.html"
_KOSZTY_ANCHOR = "#koszty"
_REALITY_ANCHOR = "#reality-check"
_KALKULATOR_ANCHOR = "#kalkulator"


def _open_url(parent: tk.Misc, anchor: str = "") -> None:
    if not _INDEX_HTML.exists():
        show_toast(
            parent,
            "Brak pliku index.html w folderze komponentu",
            duration_ms=2000,
            bg="#a23b2a",
            fg="white",
        )
        return
    url = _INDEX_HTML.as_uri() + anchor
    webbrowser.open(url)


def _open_main(parent: tk.Misc, _spec) -> None:
    _open_url(parent)


def _open_kalkulator(parent: tk.Misc, _spec) -> None:
    _open_url(parent, _KALKULATOR_ANCHOR)


def _open_reality(parent: tk.Misc, _spec) -> None:
    _open_url(parent, _REALITY_ANCHOR)


def _open_koszty(parent: tk.Misc, _spec) -> None:
    _open_url(parent, _KOSZTY_ANCHOR)


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    tiles = [
        TileSpec(
            key="open_app",
            label="Otworz aplikacje",
            icon="📈",
            color="#1976d2",
            target_kind="callable",
            callback=_open_main,
            description="Pelna analiza pricing-u w przegladarce.",
        ),
        TileSpec(
            key="kalkulator",
            label="Kalkulator cen",
            icon="🧮",
            color="#388e3c",
            target_kind="callable",
            callback=_open_kalkulator,
            description="Kalkulator + symulator P&L + what-if.",
        ),
        TileSpec(
            key="koszty",
            label="Edytuj koszty",
            icon="💰",
            color="#f57c00",
            target_kind="callable",
            callback=_open_koszty,
            description="Edytowalna tabela kosztow produkcji.",
        ),
        TileSpec(
            key="reality",
            label="Reality check",
            icon="🔍",
            color="#7b1fa2",
            target_kind="callable",
            callback=_open_reality,
            description="Porownanie cen z konkurencja (Desenio, JUNIQE, K&M).",
        ),
    ]
    view = InlineTileView(
        title="Ceny w marketingu",
        subtitle="Analiza pricing-u, kalkulator P&L, LTV/CAC, kalendarz promocji",
        tiles=tiles,
        component_dir=_COMPONENT_DIR,
        on_back=on_back,
    )
    return view.mount(parent)
