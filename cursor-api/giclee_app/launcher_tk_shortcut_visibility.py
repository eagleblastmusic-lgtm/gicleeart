"""Bezpieczny odczyt widoczności widoku skrótów Tk."""

from __future__ import annotations

import tkinter as tk


def shortcut_view_is_mapped(view: tk.Misc) -> bool:
    """Zwraca stan mapowania, a przy niedostępnym Tk bezpiecznie blokuje skróty."""

    try:
        return bool(view.winfo_ismapped())
    except tk.TclError:
        return False


__all__ = ["shortcut_view_is_mapped"]
