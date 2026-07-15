"""Best-effort adapter Tk dla wizualnego feedbacku drag-and-drop."""

from __future__ import annotations

import tkinter as tk


BORDER_NORMAL = "#dcdce2"
BORDER_DRAG_SOURCE = "#7b8798"
BORDER_DROP_TARGET = "#496a9b"
_DRAG_CURSOR = "fleur"
_DEFAULT_CURSOR = ""


def _set_tile_border(tile: tk.Frame, color: str) -> None:
    try:
        tile.configure(highlightbackground=color, highlightcolor=color)
    except tk.TclError:
        pass


def begin_drag_feedback(root: tk.Misc, source: tk.Frame) -> None:
    """Pokazuje źródło gestu i kursor przeciągania."""

    _set_tile_border(source, BORDER_DRAG_SOURCE)
    try:
        root.configure(cursor=_DRAG_CURSOR)
    except tk.TclError:
        pass


def clear_previous_drop_target(
    previous_target: tk.Frame | None,
    next_target: tk.Frame | None,
) -> None:
    """Czyści poprzedni cel wyłącznie przy rzeczywistej zmianie."""

    if previous_target is None or previous_target is next_target:
        return
    _set_tile_border(previous_target, BORDER_NORMAL)


def show_drop_target(target: tk.Frame) -> None:
    """Podświetla bieżący cel upuszczenia."""

    _set_tile_border(target, BORDER_DROP_TARGET)


def clear_drag_tile_feedback(
    source: tk.Frame,
    target: tk.Frame | None,
) -> None:
    """Przywraca normalne ramki source, a następnie targetu."""

    _set_tile_border(source, BORDER_NORMAL)
    if target is not None:
        _set_tile_border(target, BORDER_NORMAL)


def reset_drag_cursor(root: tk.Misc) -> None:
    """Best-effort przywraca domyślny kursor root."""

    try:
        root.configure(cursor=_DEFAULT_CURSOR)
    except (AttributeError, tk.TclError):
        pass


__all__ = [
    "BORDER_DRAG_SOURCE",
    "BORDER_DROP_TARGET",
    "BORDER_NORMAL",
    "begin_drag_feedback",
    "clear_drag_tile_feedback",
    "clear_previous_drop_target",
    "reset_drag_cursor",
    "show_drop_target",
]
