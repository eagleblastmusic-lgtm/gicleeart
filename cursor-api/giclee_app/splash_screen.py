"""Ekran startowy GicleeApp — logo + napis, fade in / fade out (lagodny gradient).

Styl: jasne tony, akcent „zlota”, bez ramki okna. Teksty logo: klasyczny szeryf
(Cambria / Palatino / Times / Georgia wg dostepnosci w systemie).
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from collections.abc import Callable


def _logo_typeface() -> str:
    """Klasyczny, czytelny szeryf (tradycyjny zestaw jak w edytorach / ksiazkach)."""
    available = {f.lower(): f for f in tkfont.families()}
    for name in (
        "cambria",
        "constantia",
        "calisto mt",
        "palatino linotype",
        "book antiqua",
        "palatino",
        "times new roman",
        "liberation serif",
        "crimson text",
        "eb garamond",
        "cormorant garamond",
        "cormorant",
        "georgia",
        "times",
    ):
        if name in available:
            return available[name]
    return "Georgia"


_SPLASH_FADE_STEP = 0.08
_SPLASH_FADE_MS = 14
_SPLASH_HOLD_MS = 500
_SPLASH_FALLBACK_MS = 650


def run_splash_then(root: tk.Tk, on_complete: Callable[[], None]) -> None:
    """Pokazuje Toplevel z animacja alfa, potem wywoluje on_complete (np. GicleeApp)."""
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    try:
        splash.attributes("-topmost", True)
    except tk.TclError:
        pass

    w, h = 560, 380
    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    splash.geometry(f"{w}x{h}+{x}+{y}")
    try:
        splash.lift()
        splash.focus_force()
    except tk.TclError:
        pass

    canvas = tk.Canvas(splash, width=w, height=h, highlightthickness=0, bd=0)
    canvas.pack(fill="both", expand=True)

    logo_face = _logo_typeface()
    # Litera w kole — nieco mniejsza niz sama sfera (proporcje jak w znaku firmowym).
    font_g = (logo_face, 34, "bold")
    font_title = (logo_face, 30, "bold")
    font_app = (logo_face, 18)

    # Gradient pionowy (lagodniejszy, troche wiecej kontrastu gora/dol)
    top = (252, 247, 240)
    bottom = (224, 232, 242)
    for i in range(h):
        t = i / max(h - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        color = f"#{r:02x}{g:02x}{b:02x}"
        canvas.create_line(0, i, w, i, fill=color, width=1)

    cx = w // 2
    # Znak w kole: styl „pieczec / emblemat” — obraczka + jasny dysk (nie plaski zloty placek).
    cy = 118
    rad = 50
    ring = 4
    # Zewnetrzna obraczka (tylko obrys — jak ramka medalionu)
    canvas.create_oval(
        cx - rad - ring, cy - rad - ring, cx + rad + ring, cy + rad + ring,
        outline="#6e5a45", width=2, fill="",
    )
    # Cienka zlotawa linia srodkowa (glebia)
    canvas.create_oval(
        cx - rad - 1, cy - rad - 1, cx + rad + 1, cy + rad + 1,
        outline="#c4b08a", width=1, fill="",
    )
    # Dysk: kosci sloniowa / papier — neutralny, czytelny
    canvas.create_oval(
        cx - rad, cy - rad, cx + rad, cy + rad,
        fill="#faf8f4", outline="#b9a88c", width=1,
    )
    # Litera: ciemny braz-grafit (bez cienia — czysciej)
    canvas.create_text(
        cx, cy, text="G",
        fill="#2a2420",
        font=font_g,
    )

    y_title = cy + rad + 44
    y_rule = y_title + 32
    y_app = y_rule + 26

    canvas.create_text(cx + 1, y_title + 1, text="Giclee", fill="#d5d0c8", font=font_title)
    canvas.create_text(cx, y_title, text="Giclee", fill="#1e1e1e", font=font_title)

    line_half = 100
    canvas.create_line(
        cx - line_half, y_rule, cx + line_half, y_rule,
        fill="#b8b3ab", width=1,
    )

    canvas.create_text(cx + 1, y_app + 1, text="App", fill="#cfcac4", font=font_app)
    canvas.create_text(cx, y_app, text="App", fill="#5a6570", font=font_app)

    alpha_supported = True
    try:
        splash.attributes("-alpha", 0.0)
    except tk.TclError:
        alpha_supported = False

    state: dict[str, float | str] = {"a": 0.0, "phase": "in"}

    def finish() -> None:
        try:
            splash.destroy()
        except tk.TclError:
            pass
        on_complete()

    def tick() -> None:
        phase = str(state["phase"])
        if phase == "in":
            state["a"] = float(state["a"]) + _SPLASH_FADE_STEP
            if state["a"] >= 1.0:
                state["a"] = 1.0
                state["phase"] = "hold"
                if alpha_supported:
                    try:
                        splash.attributes("-alpha", 1.0)
                    except tk.TclError:
                        pass
                splash.after(_SPLASH_HOLD_MS, tick)
                return
            if alpha_supported:
                try:
                    splash.attributes("-alpha", float(state["a"]))
                except tk.TclError:
                    pass
            splash.after(_SPLASH_FADE_MS, tick)
        elif phase == "hold":
            state["phase"] = "out"
            splash.after(_SPLASH_FADE_MS, tick)
        elif phase == "out":
            state["a"] = float(state["a"]) - _SPLASH_FADE_STEP
            if state["a"] <= 0:
                if alpha_supported:
                    try:
                        splash.attributes("-alpha", 0.0)
                    except tk.TclError:
                        pass
                finish()
                return
            if alpha_supported:
                try:
                    splash.attributes("-alpha", float(state["a"]))
                except tk.TclError:
                    pass
            splash.after(_SPLASH_FADE_MS, tick)

    if not alpha_supported:
        splash.after(150, lambda: splash.after(_SPLASH_FALLBACK_MS, finish))
    else:
        splash.after(80, tick)
