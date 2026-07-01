"""Okno z ostatnimi wpisami dziennika akcji (kopiowanie do schowka)."""
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

from Komponenty._shared.activity_log import read_tail
from Komponenty._shared.window_geometry import position_toplevel_screen_center


def open_activity_log_dialog(master: tk.Misc, *, title: str = "Dziennik akcji") -> None:
    dlg = tk.Toplevel(master)
    dlg.title(title)
    position_toplevel_screen_center(dlg, 720, 520)
    dlg.transient(master)

    txt = scrolledtext.ScrolledText(dlg, wrap="word", font=("Consolas", 9))
    txt.pack(fill="both", expand=True, padx=10, pady=(10, 6))

    def refresh() -> None:
        lines = read_tail()
        body = "\n".join(lines) if lines else "(brak wpisow)"
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.insert("1.0", body)
        txt.configure(state="disabled")

    def copy_all() -> None:
        lines = read_tail()
        master.clipboard_clear()
        master.clipboard_append("\n".join(lines) if lines else "")
        try:
            master.update_idletasks()
        except tk.TclError:
            pass

    bar = ttk.Frame(dlg)
    bar.pack(fill="x", padx=10, pady=(0, 10))
    ttk.Button(bar, text="Odswiez", command=refresh).pack(side="left")
    ttk.Button(bar, text="Kopiuj calosc", command=copy_all).pack(side="left", padx=(8, 0))
    ttk.Button(bar, text="Zamknij", command=dlg.destroy).pack(side="right")

    refresh()
