"""Spójna warstwa wizualna kafelków komponentów dla launchera kategorii."""

from __future__ import annotations

import time
import tkinter as tk

from . import launcher as _launcher
from .category_launcher import CategoryGicleeApp
from .component_loader import Component


_MODE_LABELS = {
    "inline": "W aplikacji",
    "url": "WWW",
    "subprocess": "Nowe okno",
}

_ACTION_LABELS = {
    "inline": "Otwórz komponent  →",
    "url": "Otwórz stronę  →",
    "subprocess": "Uruchom  →",
}


def component_mode_label(mode: str) -> str:
    """Krótka etykieta informująca, gdzie otworzy się komponent."""

    return _MODE_LABELS.get(str(mode or "").strip().lower(), "Komponent")


def component_action_label(mode: str) -> str:
    """Tekst akcji dopasowany do trybu uruchomienia komponentu."""

    return _ACTION_LABELS.get(str(mode or "").strip().lower(), "Otwórz  →")


def component_display_icon(component: Component) -> str:
    """Ikona komponentu z neutralnym fallbackiem dla brakujących metadanych."""

    return component.icon.strip() if component.icon and component.icon.strip() else "◆"


class StyledCategoryGicleeApp(CategoryGicleeApp):
    """Dwupoziomowy launcher ze spójnym stylem kategorii i komponentów."""

    def _build_tile(self, parent: tk.Misc, comp: Component) -> tk.Frame:
        bg_normal = "#ffffff"
        bg_hover = "#eef1f6"
        border_normal = "#dcdce2"
        border_hover = "#c8ccd5"

        outer = tk.Frame(
            parent,
            bg=bg_normal,
            bd=0,
            highlightthickness=1,
            highlightbackground=border_normal,
            highlightcolor=border_normal,
            width=_launcher._TILE_W,
            height=_launcher._TILE_H,
        )
        outer.pack_propagate(False)

        accent = tk.Frame(outer, bg=comp.color, width=7)
        accent.pack(side="left", fill="y")

        body = tk.Frame(outer, bg=bg_normal)
        body.pack(side="left", fill="both", expand=True, padx=15, pady=13)

        top = tk.Frame(body, bg=bg_normal)
        top.pack(fill="x")
        tk.Label(
            top,
            text=component_display_icon(comp),
            bg=bg_normal,
            fg="#222",
            font=("Segoe UI Emoji", 19, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Label(
            top,
            text=component_mode_label(comp.mode),
            bg=bg_normal,
            fg="#777",
            font=("Segoe UI", 8),
            anchor="e",
        ).pack(side="right", pady=(5, 0))

        tk.Label(
            body,
            text=comp.name,
            bg=bg_normal,
            fg="#222",
            font=("Segoe UI", 13, "bold"),
            justify="left",
            anchor="w",
            wraplength=_launcher._TILE_W - 50,
        ).pack(fill="x", pady=(8, 0))

        description = comp.description.strip() if comp.description else "Otwórz komponent GicleeApp."
        tk.Label(
            body,
            text=description,
            bg=bg_normal,
            fg="#5d5d65",
            font=("Segoe UI", 9),
            justify="left",
            anchor="nw",
            wraplength=_launcher._TILE_W - 50,
        ).pack(fill="x", pady=(5, 0))

        tk.Frame(body, bg=bg_normal).pack(fill="both", expand=True)
        tk.Label(
            body,
            text=component_action_label(comp.mode),
            bg=bg_normal,
            fg=comp.color,
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        ).pack(fill="x")

        background_widgets: list[tk.Widget] = []

        def collect(widget: tk.Widget) -> None:
            if widget is accent:
                return
            background_widgets.append(widget)
            for child in widget.winfo_children():
                collect(child)

        collect(outer)

        def set_hover(active: bool) -> None:
            new_bg = bg_hover if active else bg_normal
            new_border = border_hover if active else border_normal
            for widget in background_widgets:
                try:
                    widget.configure(bg=new_bg)
                except tk.TclError:
                    pass
            try:
                outer.configure(
                    highlightbackground=new_border,
                    highlightcolor=new_border,
                )
            except tk.TclError:
                pass

        self._tile_hover_clearers.append(lambda: set_hover(False))

        def on_enter(_event: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            set_hover(True)

        def on_leave(_event: object) -> None:
            if time.monotonic() < self._suppress_tile_hover_until:
                return
            try:
                px, py = outer.winfo_pointerxy()
                ox, oy = outer.winfo_rootx(), outer.winfo_rooty()
                ow, oh = outer.winfo_width(), outer.winfo_height()
            except tk.TclError:
                return
            if ox <= px < ox + ow and oy <= py < oy + oh:
                return
            set_hover(False)

        def on_click(_event: object, selected: Component = comp) -> None:
            self._launch(selected)

        def on_right_click(event: tk.Event, selected: Component = comp) -> None:
            self._show_tile_context_menu(event, selected)

        def bind_recursive(widget: tk.Widget) -> None:
            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<Button-1>", on_click, add="+")
            widget.bind("<Button-3>", on_right_click, add="+")
            try:
                widget.configure(cursor="hand2")
            except tk.TclError:
                pass
            for child in widget.winfo_children():
                bind_recursive(child)

        bind_recursive(outer)
        return outer


def main() -> None:
    """Uruchamia launcher kategorii ze spójnymi kafelkami komponentów."""

    original_class = _launcher.GicleeApp
    _launcher.GicleeApp = StyledCategoryGicleeApp
    try:
        _launcher.main()
    finally:
        _launcher.GicleeApp = original_class


if __name__ == "__main__":
    main()
