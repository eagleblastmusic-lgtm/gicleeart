"""Wspolne ustawianie pozycji okien Tkinter (centrowanie na ekranie)."""

from __future__ import annotations

import tkinter as tk


def position_toplevel_screen_center(win: tk.Misc, width: int, height: int) -> None:
    """Ustawia rozmiar i wycentrowanie okna wzgledem glownego monitora (geometry WxH+X+Y)."""
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


def position_toplevel_screen_center_from_reqsize(
    win: tk.Misc, *, min_width: int = 0, min_height: int = 0
) -> None:
    """Po spakowaniu widgetow: bierze reqwidth/reqheight i centruje okno na ekranie."""
    win.update_idletasks()
    w = max(min_width, win.winfo_reqwidth())
    h = max(min_height, win.winfo_reqheight())
    position_toplevel_screen_center(win, w, h)
