"""Powiadomienie o zakonczeniu dlugiego zadania (dzwie Windows + podniesienie okna)."""
from __future__ import annotations

import tkinter as tk


def notify_long_task_done(root: tk.Misc) -> None:
    """Dzwiek systemowy (Windows) i proba przywrocenia okna na pierwszy plan."""
    try:
        import winsound

        winsound.MessageBeep()  # domyslnie MB_OK (Windows)
    except Exception:
        try:
            root.bell()
        except tk.TclError:
            pass
    try:
        root.lift()
        root.attributes("-topmost", True)
        root.after(200, lambda: root.attributes("-topmost", False))
    except tk.TclError:
        pass
