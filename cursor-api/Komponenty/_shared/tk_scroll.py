"""Wspólne przewijanie kółkiem myszy dla Canvas + dzieci (Windows / touchpad)."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk


def bind_mousewheel_to_canvas(canvas: tk.Canvas, root: tk.Misc) -> None:
    """Kółko nad canvasem i dziećmi przewija canvas (bez bind_all — nie psuje launchera)."""
    acc: list[int] = [0]
    job: list[str | None] = [None]

    def _flush() -> None:
        job[0] = None
        d = acc[0]
        acc[0] = 0
        if not d:
            return
        step = -d / 120.0
        if -1 < step < 1 and step != 0:
            step = math.copysign(1.0, float(-d))
        canvas.yview_scroll(int(step), "units")

    def _queue_wheel(delta: int) -> None:
        acc[0] += delta
        jid = job[0]
        if jid is not None:
            try:
                canvas.after_cancel(jid)
            except (tk.TclError, ValueError):
                pass
        job[0] = canvas.after_idle(_flush)

    def _wheel(evt: tk.Event) -> str | None:
        w = evt.widget
        if isinstance(w, (tk.Text, tk.Listbox)):
            return None
        if evt.delta:
            _queue_wheel(int(evt.delta))
            return "break"
        if evt.num == 4:
            canvas.yview_scroll(-1, "units")
            return "break"
        if evt.num == 5:
            canvas.yview_scroll(1, "units")
            return "break"
        return None

    def _bind_tree(w: tk.Misc) -> None:
        if isinstance(w, (tk.Text, tk.Listbox, ttk.Treeview)):
            return
        w.bind("<MouseWheel>", _wheel, add="+")
        w.bind("<Button-4>", _wheel, add="+")
        w.bind("<Button-5>", _wheel, add="+")
        try:
            for child in w.winfo_children():
                _bind_tree(child)
        except tk.TclError:
            pass

    _bind_tree(root)
    canvas.bind("<MouseWheel>", _wheel, add="+")
    canvas.bind("<Button-4>", _wheel, add="+")
    canvas.bind("<Button-5>", _wheel, add="+")
