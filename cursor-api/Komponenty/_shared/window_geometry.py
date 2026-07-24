"""Wspolne ustawianie pozycji okien Tkinter (centrowanie na ekranie)."""

from __future__ import annotations

import tkinter as tk

# Windows: zminimalizowane / „zagubione” okna czesto maja -32000.
_OFFSCREEN_THRESHOLD = -1000
_MIN_VISIBLE_W = 400
_MIN_VISIBLE_H = 300


def _screen_size(win: tk.Misc) -> tuple[int, int]:
    try:
        sw = int(win.winfo_screenwidth())
        sh = int(win.winfo_screenheight())
    except tk.TclError:
        return 1280, 800
    return max(320, sw), max(240, sh)


def clamp_toplevel_onscreen(
    win: tk.Misc,
    *,
    fallback_width: int = 1100,
    fallback_height: int = 720,
) -> None:
    """Jesli okno jest poza ekranem / zminimalizowane do -32000, przywroc na monitor."""
    try:
        win.update_idletasks()
        sw, sh = _screen_size(win)
        x = int(win.winfo_x())
        y = int(win.winfo_y())
        w = int(win.winfo_width())
        h = int(win.winfo_height())
        offscreen = (
            x < _OFFSCREEN_THRESHOLD
            or y < _OFFSCREEN_THRESHOLD
            or x > sw - 40
            or y > sh - 40
        )
        tiny = w < _MIN_VISIBLE_W or h < _MIN_VISIBLE_H
        if not offscreen and not tiny:
            return
        if tiny or w <= 1 or h <= 1:
            w = min(fallback_width, sw - 40)
            h = min(fallback_height, sh - 80)
        else:
            w = min(max(w, _MIN_VISIBLE_W), sw - 40)
            h = min(max(h, _MIN_VISIBLE_H), sh - 80)
        nx = max(0, (sw - w) // 2)
        ny = max(0, (sh - h) // 2)
        try:
            win.deiconify()
            win.state("normal")
        except tk.TclError:
            pass
        win.geometry(f"{w}x{h}+{nx}+{ny}")
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(250, lambda: _clear_topmost(win))
        except tk.TclError:
            pass
    except tk.TclError:
        return


def _clear_topmost(win: tk.Misc) -> None:
    try:
        if win.winfo_exists():
            win.attributes("-topmost", False)
    except tk.TclError:
        pass


def attach_onscreen_guard(
    win: tk.Misc,
    *,
    fallback_width: int = 1100,
    fallback_height: int = 720,
) -> None:
    """Pilnuje, zeby okno wracalo na ekran po Map/FocusIn (np. klik w pasek zadan)."""

    def _guard(_event: object | None = None) -> None:
        clamp_toplevel_onscreen(
            win,
            fallback_width=fallback_width,
            fallback_height=fallback_height,
        )

    try:
        win.bind("<Map>", _guard, add="+")
        win.bind("<FocusIn>", _guard, add="+")
        win.bind("<Visibility>", _guard, add="+")
        win.after(150, _guard)
        win.after(800, _guard)
    except tk.TclError:
        return


def position_toplevel_screen_center(win: tk.Misc, width: int, height: int) -> None:
    """Ustawia rozmiar i wycentrowanie okna wzgledem glownego monitora (geometry WxH+X+Y)."""
    sw, sh = _screen_size(win)
    width = max(200, min(int(width), sw - 40))
    height = max(160, min(int(height), sh - 80))
    x = max(0, (sw - width) // 2)
    y = max(0, (sh - height) // 2)
    try:
        win.deiconify()
        win.state("normal")
    except tk.TclError:
        pass
    win.geometry(f"{width}x{height}+{x}+{y}")
    try:
        win.lift()
        win.focus_force()
    except tk.TclError:
        pass


def position_toplevel_screen_center_from_reqsize(
    win: tk.Misc, *, min_width: int = 0, min_height: int = 0
) -> None:
    """Po spakowaniu widgetow: bierze reqwidth/reqheight i centruje okno na ekranie."""
    win.update_idletasks()
    w = max(min_width, win.winfo_reqwidth())
    h = max(min_height, win.winfo_reqheight())
    position_toplevel_screen_center(win, w, h)
