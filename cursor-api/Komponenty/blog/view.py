"""Inline-view komponentu Blog.

Hierarchia ekranow (nawigacja w ramach jednego frame'u w launcherze):

    Blog (main) — 5 kafelkow:
      Generator tresci (Toplevel), Import z HTML (Toplevel), Generator tematow (Toplevel),
      Propozycje tematow (lista + PPM), Posty na blogu -> obecne posty (auto-fetch)

`on_back` z launchera wraca do glownego menu (siatki kafelkow launchera).
Wewnetrzna nawigacja zarzadzana jest przez `BlogView` (stos ekranow).
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import ttk
from typing import Any

from .generator_tematow import open_topics_generator
from .generator_tresci import open_content_generator
from .import_html import open_html_import
from .obecne_posty import build_articles_screen
from .propozycje_tematow import build_topics_screen

_COMPONENT_DIR = Path(__file__).resolve().parent

_BG = "#f4f4f7"
_BG_TILE = "#ffffff"
_BG_HOVER = "#f0f2f7"
_BORDER = "#dcdce2"

_TILE_W = 300
_TILE_H = 170
_TILES_PER_ROW = 3
_TILE_PAD = 12


class BlogView:
    """Zarzadza widokami Blog — glowna siatka + dwa pelnoekranowe podwidoki."""

    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back  # powrot do siatki kafelkow launchera
        self.frame = tk.Frame(parent, bg=_BG)

        # stos ekranow - aktualny widget ekranu trzymamy tu
        self._current_screen: tk.Widget | None = None

        self.show_main()

    # ---------- ekrany ----------
    def show_main(self) -> None:
        """Glowny ekran: 5 kafelkow."""
        self._swap_screen(self._build_main())

    def show_topics_list(self) -> None:
        """Lista propozycji tematow."""
        screen = build_topics_screen(
            self.frame,
            on_back=self.show_main,
            on_generate_content=self._open_content_generator_with_topic,
        )
        self._swap_screen(screen)

    def show_articles_list(self) -> None:
        """Lista obecnych postow z bloga (auto-refresh) — z kafelka Posty na blogu."""
        screen = build_articles_screen(
            self.frame,
            on_back=self.show_main,
        )
        self._swap_screen(screen)

    # ---------- akcje kafelkow ----------
    def _open_content_generator(self) -> None:
        open_content_generator(self.frame.winfo_toplevel())

    def _open_content_generator_with_topic(self, topic: str, topic_id: str = "") -> None:
        open_content_generator(self.frame.winfo_toplevel(), initial_topic=topic, topic_id=topic_id)

    def _open_topics_generator(self) -> None:
        open_topics_generator(self.frame.winfo_toplevel(), on_saved=self._notify_topics_saved)

    def _notify_topics_saved(self, _count: int) -> None:
        # Jesli aktualnie mamy otwarta liste propozycji - odswiez ja.
        pass  # lista sama sie odswieza przy zaladowaniu ekranu

    def _open_html_import(self) -> None:
        open_html_import(self.frame.winfo_toplevel())

    # ---------- build: main ----------
    def _build_main(self) -> tk.Widget:
        outer = tk.Frame(self.frame, bg=_BG)

        _build_toolbar(
            outer,
            title="Blog",
            subtitle="Generator promptow + publikacja postow w 7 jezykach",
            on_back=self.on_back,
            back_label="< Powrot",
        )

        body = tk.Frame(outer, bg=_BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)
        for i in range(_TILES_PER_ROW):
            body.columnconfigure(i, weight=1, uniform="blog-main")

        tiles = [
            _Tile(
                label="Generator tresci",
                icon="✍️",
                color="#1e88e5",
                description="Wpisz temat, skopiuj prompt, wklej odpowiedz, wyslij post na Shopify (7 jezykow).",
                command=self._open_content_generator,
            ),
            _Tile(
                label="Import z HTML",
                icon="📂",
                color="#00897b",
                description="Wczytaj plik HTML z podgladu AI i opublikuj post na Shopify (7 jezykow).",
                command=self._open_html_import,
            ),
            _Tile(
                label="Generator tematow",
                icon="💡",
                color="#fb8c00",
                description="Analiza obecnych postow -> prompt -> 10 propozycji tematow z uzasadnieniem.",
                command=self._open_topics_generator,
            ),
            _Tile(
                label="Propozycje tematow",
                icon="📝",
                color="#fb8c00",
                description="Zapisane propozycje (z generatora tematow) — PPM: kopiuj, usun, generuj tresc.",
                command=self.show_topics_list,
            ),
            _Tile(
                label="Posty na blogu",
                icon="📚",
                color="#43a047",
                description="Obecne opublikowane posty — auto-fetch z Shopify, dwuklik otwiera w przegladarce.",
                command=self.show_articles_list,
            ),
        ]
        for i, spec in enumerate(tiles):
            r, c = divmod(i, _TILES_PER_ROW)
            tile = _build_tile(body, spec)
            tile.grid(row=r, column=c, padx=_TILE_PAD, pady=_TILE_PAD, sticky="")

        return outer

    # ---------- swap ----------
    def _swap_screen(self, new_screen: tk.Widget) -> None:
        if self._current_screen is not None:
            try:
                self._current_screen.destroy()
            except tk.TclError:
                pass
            self._current_screen = None
        new_screen.pack(fill="both", expand=True)
        self._current_screen = new_screen


# ---------------------------------------------------------------------------
# Tile building helpers (spojne z look&feel reszty aplikacji)
# ---------------------------------------------------------------------------

class _Tile:
    def __init__(self, *, label: str, icon: str, color: str, description: str, command: Callable[[], None]) -> None:
        self.label = label
        self.icon = icon
        self.color = color
        self.description = description
        self.command = command


def _build_tile(parent: tk.Widget, spec: _Tile) -> tk.Frame:
    outer = tk.Frame(
        parent, bg=_BG_TILE, bd=0,
        highlightthickness=1,
        highlightbackground=_BORDER,
        highlightcolor=_BORDER,
        width=_TILE_W, height=_TILE_H,
    )
    outer.pack_propagate(False)

    accent = tk.Frame(outer, bg=spec.color, width=6)
    accent.pack(side="left", fill="y")

    body = tk.Frame(outer, bg=_BG_TILE)
    body.pack(side="left", fill="both", expand=True, padx=14, pady=12)

    title_row = tk.Frame(body, bg=_BG_TILE)
    title_row.pack(fill="x")
    if spec.icon:
        tk.Label(
            title_row, text=spec.icon, bg=_BG_TILE,
            font=("Segoe UI Emoji", 18),
        ).pack(side="left", padx=(0, 8))
    tk.Label(
        title_row, text=spec.label, bg=_BG_TILE,
        font=("Segoe UI", 13, "bold"), fg="#222",
        anchor="w",
    ).pack(side="left", fill="x", expand=True)

    if spec.description:
        tk.Label(
            body, text=spec.description, bg=_BG_TILE,
            font=("Segoe UI", 9), fg="#555",
            wraplength=_TILE_W - 50, justify="left", anchor="w",
        ).pack(fill="x", pady=(6, 0))

    # Hover (tylko bg)
    bg_widgets: list[tk.Widget] = []

    def _collect(w: tk.Widget) -> None:
        if w is accent:
            return
        bg_widgets.append(w)
        for ch in w.winfo_children():
            _collect(ch)

    _collect(outer)

    def _set_hover(active: bool) -> None:
        new_bg = _BG_HOVER if active else _BG_TILE
        for w in bg_widgets:
            try:
                w.configure(bg=new_bg)
            except tk.TclError:
                pass

    def _on_enter(_e: object) -> None:
        _set_hover(True)

    def _on_leave(_e: object) -> None:
        try:
            px, py = outer.winfo_pointerxy()
            ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
            ow, oh = outer.winfo_width(), outer.winfo_height()
        except tk.TclError:
            return
        if ox <= px < ox + ow and oy <= py < oy + oh:
            return
        _set_hover(False)

    def _on_click(_e: object) -> None:
        spec.command()

    def _bind(w: tk.Widget) -> None:
        w.bind("<Enter>", _on_enter, add="+")
        w.bind("<Leave>", _on_leave, add="+")
        w.bind("<Button-1>", _on_click, add="+")
        try:
            w.configure(cursor="hand2")
        except tk.TclError:
            pass
        for ch in w.winfo_children():
            _bind(ch)

    _bind(outer)
    return outer


def _build_toolbar(parent: tk.Widget, *, title: str, subtitle: str, on_back: Callable[[], None], back_label: str) -> tk.Frame:
    toolbar = tk.Frame(parent, bg=_BG)
    toolbar.pack(fill="x", padx=14, pady=(12, 4))
    ttk.Button(toolbar, text=back_label, command=on_back).pack(side="left")
    tk.Label(
        toolbar, text=title, bg=_BG,
        font=("Segoe UI", 18, "bold"), fg="#222",
    ).pack(side="left", padx=(14, 0))
    if subtitle:
        tk.Label(
            toolbar, text=subtitle, bg=_BG, fg="#666",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(10, 0), pady=(8, 0))
    return toolbar


# ---------------------------------------------------------------------------
# Entry point dla launchera
# ---------------------------------------------------------------------------

def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    view = BlogView(parent, on_back)
    return view.frame
