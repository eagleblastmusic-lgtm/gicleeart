"""Adapter Tk dla rekursywnych bindingów drag-and-drop launchera."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk


_CLICK_EVENT = "<Button-1>"
_PRESS_EVENT = "<ButtonPress-1>"
_MOTION_EVENT = "<B1-Motion>"
_RELEASE_EVENT = "<ButtonRelease-1>"
_POINTER_CURSOR = "hand2"

DragEventCallback = Callable[[tk.Event], str | None]


def install_tile_drag_bindings(
    tile: tk.Misc,
    *,
    on_press: DragEventCallback,
    on_motion: DragEventCallback,
    on_release: DragEventCallback,
) -> None:
    """Instaluje bieżący kontrakt DnD na root tile i wszystkich potomkach."""

    def bind_recursive(widget: tk.Misc) -> None:
        # Bazowe kafelki uruchamiają akcję na Button-1. Przy DnD klik jest
        # rozstrzygany dopiero na release, o ile gest nie przeszedł w drag.
        try:
            widget.unbind(_CLICK_EVENT)
        except tk.TclError:
            pass

        widget.bind(_PRESS_EVENT, on_press, add="+")
        widget.bind(_MOTION_EVENT, on_motion, add="+")
        widget.bind(_RELEASE_EVENT, on_release, add="+")

        try:
            widget.configure(cursor=_POINTER_CURSOR)
        except tk.TclError:
            pass

        for child in widget.winfo_children():
            bind_recursive(child)

    bind_recursive(tile)


__all__ = ["DragEventCallback", "install_tile_drag_bindings"]
