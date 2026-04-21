"""Inline-view komponentu Social Media.

Hierarchia ekranow (nawigacja w ramach jednego frame'u w launcherze):

    Social Media (main)
    +-- Generator tresci  (Toplevel dialog)
    +-- Planer postow     (sub-view z kolejka)
    +-- Cykl              (sub-view)
    +-- Dodaj post        (sub-view: 4 kanaly -> Toplevel kreator)

`on_back` z launchera wraca do glownego menu launchera.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from .cykl.view import build_cykl_view
from .generator_tresci import open_content_generator
from .manual_post import open_manual_post_wizard, open_social_ids_dialog
from .planer_postow import build_planer_screen

_BG = "#f4f4f7"
_BG_TILE = "#ffffff"
_BG_HOVER = "#f0f2f7"
_BORDER = "#dcdce2"

_TILE_W = 300
_TILE_H = 170
_TILES_PER_ROW = 3
_TILE_PAD = 12


class SocialMediaView:
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back
        self.frame = tk.Frame(parent, bg=_BG)
        self._current_screen: tk.Widget | None = None
        self.show_main()

    # ---------- screens ----------
    def show_main(self) -> None:
        self._swap(self._build_main())

    def show_planner(self) -> None:
        screen = build_planer_screen(self.frame, on_back=self.show_main)
        self._swap(screen)

    def show_cykl(self) -> None:
        screen = build_cykl_view(self.frame, on_back=self.show_main)
        self._swap(screen)

    def show_dodaj_post_hub(self) -> None:
        self._swap(self._build_dodaj_post_hub())

    # ---------- actions ----------
    def _open_generator(self) -> None:
        open_content_generator(self.frame.winfo_toplevel())

    # ---------- build ----------
    def _build_main(self) -> tk.Widget:
        outer = tk.Frame(self.frame, bg=_BG)

        _toolbar(outer, title="Social Media", subtitle="Generator postow + planer kolejki", on_back=self.on_back)

        body = tk.Frame(outer, bg=_BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)
        for i in range(_TILES_PER_ROW):
            body.columnconfigure(i, weight=1, uniform="sm-main")

        tiles = [
            _Tile(
                label="Generator tresci",
                icon="✍️",
                color="#e91e63",
                description="Wybierz platforme i jezyk, wpisz temat, skopiuj prompt, wklej odpowiedz -> podglad + zapis do planera.",
                command=self._open_generator,
            ),
            _Tile(
                label="Planer postow",
                icon="🗓️",
                color="#6a1b9a",
                description="Kolejka zaplanowanych postow (PL/EN, 6 platform) - statusy, edycja, kopiuj caption, eksport CSV.",
                command=self.show_planner,
            ),
            _Tile(
                label="Cykl - Obraz na rano, popoludnie i wieczor",
                icon="🔁",
                color="#00897b",
                description="Automatyczny cykl 3 postow dziennie (FB PL/EN + IG PL/EN z karuzela), tresc przez Opus, kolejka po kolekcjach artystow.",
                command=self.show_cykl,
            ),
            _Tile(
                label="Dodaj post",
                icon="📤",
                color="#5c6bc0",
                description="Reczna publikacja na Facebook lub Instagram (PL / EU): grafika + podpis, bez kolejki Cyklu.",
                command=self.show_dodaj_post_hub,
            ),
        ]
        for i, spec in enumerate(tiles):
            r, c = divmod(i, _TILES_PER_ROW)
            tile = _build_tile(body, spec)
            tile.grid(row=r, column=c, padx=_TILE_PAD, pady=_TILE_PAD, sticky="")

        return outer

    def _build_dodaj_post_hub(self) -> tk.Widget:
        """Ekran z 4 kafelkami kanalow recznej publikacji."""
        outer = tk.Frame(self.frame, bg=_BG)
        _toolbar(
            outer,
            title="Dodaj post",
            subtitle="Wybierz kanal (wymaga tokenow Meta z Cyklu)",
            on_back=self.show_main,
        )

        hub_bar = tk.Frame(outer, bg=_BG)
        hub_bar.pack(fill="x", padx=14, pady=(0, 4))
        ttk.Button(
            hub_bar,
            text="Id socjali",
            command=lambda: open_social_ids_dialog(self.frame.winfo_toplevel()),
        ).pack(side="left")

        body = tk.Frame(outer, bg=_BG)
        body.pack(fill="both", expand=True, padx=14, pady=10)

        hub_specs = [
            ("fb_pl", "Facebook PL", "📘", "#1877f2"),
            ("ig_pl", "Instagram PL", "📸", "#e1306c"),
            ("fb_en", "Facebook EU", "📘", "#1565c0"),
            ("ig_en", "Instagram EU", "📸", "#c2185b"),
        ]

        intro = tk.Label(
            body,
            text="Kazdy kanal otwiera ten sam kreator: dodaj zdjecia, wpisz podpis, Publikuj.\n"
            "Grafiki trafiaja na CDN Shopify, potem do Meta (jak w Cyklu).",
            bg=_BG, fg="#555", font=("Segoe UI", 10), justify="left",
        )
        intro.pack(anchor="w", pady=(0, 12))

        grid = tk.Frame(body, bg=_BG)
        grid.pack(fill="both", expand=True)

        for i in range(2):
            grid.columnconfigure(i, weight=1)
        for i in range(2):
            grid.rowconfigure(i, weight=1)

        for idx, (code, label, icon, color) in enumerate(hub_specs):
            r, c = divmod(idx, 2)

            def _open(code=code) -> None:
                open_manual_post_wizard(self.frame.winfo_toplevel(), code)

            spec = _Tile(
                label=label,
                icon=icon,
                color=color,
                description="Grafika + podpis. Wiele zdjec = karuzela (IG) lub album (FB).",
                command=_open,
            )
            tile = _build_tile(grid, spec)
            tile.grid(row=r, column=c, padx=_TILE_PAD, pady=_TILE_PAD, sticky="")

        return outer

    def _swap(self, new_screen: tk.Widget) -> None:
        if self._current_screen is not None:
            try:
                self._current_screen.destroy()
            except tk.TclError:
                pass
        new_screen.pack(fill="both", expand=True)
        self._current_screen = new_screen


# ---------------------------------------------------------------------------
# Tile helpers (identyczne jak w blog/view.py)
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


def _toolbar(parent: tk.Widget, *, title: str, subtitle: str, on_back: Callable[[], None]) -> tk.Frame:
    toolbar = tk.Frame(parent, bg=_BG)
    toolbar.pack(fill="x", padx=14, pady=(12, 4))
    ttk.Button(toolbar, text="< Powrot", command=on_back).pack(side="left")
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
# Entry point
# ---------------------------------------------------------------------------

def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    view = SocialMediaView(parent, on_back)
    return view.frame
