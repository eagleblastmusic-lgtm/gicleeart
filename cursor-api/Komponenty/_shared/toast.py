"""Krotki, samoznikajacy toast (fade in / fade out) jako Toplevel bez ramki.

Uzycie:
    from Komponenty._shared.toast import show_toast
    show_toast(root, "Skopiowano!")
    show_toast(root, "W budowie", duration_ms=1800, bg="#333", fg="white")
"""

from __future__ import annotations

import tkinter as tk

_DEFAULT_BG = "#222"
_DEFAULT_FG = "#fff"


def show_toast(
    parent: tk.Misc,
    text: str,
    *,
    duration_ms: int = 1500,
    fade_ms: int = 220,
    bg: str = _DEFAULT_BG,
    fg: str = _DEFAULT_FG,
    font: tuple | None = None,
) -> tk.Toplevel:
    """Pokazuje toast na srodku-dolu okna rodzica.

    Wraca utworzony Toplevel (zwykle ignorujemy).
    """
    root = parent.winfo_toplevel()
    win = tk.Toplevel(root)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try:
        win.attributes("-alpha", 0.0)
    except tk.TclError:
        pass

    label = tk.Label(
        win, text=text, bg=bg, fg=fg,
        font=font or ("Segoe UI", 11, "bold"),
        padx=22, pady=12,
    )
    label.pack()

    win.update_idletasks()
    # Pozycja: srodek-dol rodzica (ok. 1/4 wysokosci od dolu)
    try:
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()
    except tk.TclError:
        rx, ry, rw, rh = 0, 0, win.winfo_screenwidth(), win.winfo_screenheight()
    ww = win.winfo_width()
    wh = win.winfo_height()
    x = rx + max(0, (rw - ww) // 2)
    y = ry + rh - wh - max(40, rh // 6)
    win.geometry(f"+{x}+{y}")

    state = {"alive": True}

    def _fade(direction: str, step: int = 0) -> None:
        if not state["alive"] or not win.winfo_exists():
            return
        steps = max(1, fade_ms // 16)
        if direction == "in":
            alpha = min(1.0, step / steps)
        else:
            alpha = max(0.0, 1.0 - step / steps)
        try:
            win.attributes("-alpha", alpha)
        except tk.TclError:
            return
        if step < steps:
            win.after(16, _fade, direction, step + 1)
        elif direction == "in":
            win.after(duration_ms, _fade, "out", 0)
        else:
            state["alive"] = False
            try:
                win.destroy()
            except tk.TclError:
                pass

    _fade("in", 0)
    return win
