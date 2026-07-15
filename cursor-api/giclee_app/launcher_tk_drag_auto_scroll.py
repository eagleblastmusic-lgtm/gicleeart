"""Adapter Tk dla pionowego auto-scrollu podczas drag-and-drop."""

from __future__ import annotations

import tkinter as tk


DRAG_AUTO_SCROLL_MARGIN_PX = 42


def auto_scroll_drag(
    canvas: tk.Misc,
    y_root: int,
    *,
    margin: int = DRAG_AUTO_SCROLL_MARGIN_PX,
) -> None:
    """Przewija canvas o jedną jednostkę przy górnej lub dolnej krawędzi."""

    if margin < 0:
        raise ValueError("margin must be non-negative")

    try:
        top = canvas.winfo_rooty()
        bottom = top + canvas.winfo_height()
    except tk.TclError:
        return

    if y_root < top + margin:
        canvas.yview_scroll(-1, "units")
    elif y_root > bottom - margin:
        canvas.yview_scroll(1, "units")


__all__ = ["DRAG_AUTO_SCROLL_MARGIN_PX", "auto_scroll_drag"]
