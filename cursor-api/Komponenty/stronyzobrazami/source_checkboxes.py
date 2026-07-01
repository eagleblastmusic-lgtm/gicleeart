"""Przewijalna lista checkboxow zrodel wyszukiwania."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

DEFAULT_SOURCE_LIST_HEIGHT = 120


def mount_scrollable_source_list(
    parent: tk.Misc,
    *,
    height: int = DEFAULT_SOURCE_LIST_HEIGHT,
) -> ttk.Frame:
    """Zwraca wewnetrzny frame — checkboxy zrodel (scroll pionowy)."""
    container = ttk.Frame(parent)
    container.pack(fill="x")

    canvas = tk.Canvas(container, height=height, highlightthickness=0)
    scroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas)

    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scroll.set)

    def _resize(event: tk.Event) -> None:
        canvas.itemconfigure(win_id, width=event.width)

    def _scroll_region(_event: tk.Event | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _wheel(event: tk.Event) -> None:
        if getattr(event, "delta", 0):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif getattr(event, "num", 0) == 4:
            canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", 0) == 5:
            canvas.yview_scroll(1, "units")

    inner.bind("<Configure>", _scroll_region)
    canvas.bind("<Configure>", _resize)
    canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
    canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

    canvas.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")

    inner._refresh_scroll = _scroll_region  # type: ignore[attr-defined]
    return inner


def refresh_source_list_scroll(inner: ttk.Frame) -> None:
    fn = getattr(inner, "_refresh_scroll", None)
    if callable(fn):
        inner.update_idletasks()
        fn()
