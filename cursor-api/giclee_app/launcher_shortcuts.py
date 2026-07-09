"""Skróty klawiszowe GicleeApp — wspólne dla klasycznego launchera i Studio."""

from __future__ import annotations

import tkinter as tk

# Litera (lowercase) -> folder_name w Komponenty/.
LAUNCHER_KEY_SHORTCUTS: dict[str, str] = {
    "i": "integracjagpt",
}


def shortcut_key_from_event(event: tk.Event) -> str | None:
    ch = event.char or ""
    if len(ch) == 1 and ch.isprintable() and not ch.isspace():
        return ch.lower()
    keysym = (event.keysym or "").lower()
    if len(keysym) == 1:
        return keysym
    return None


def focus_blocks_shortcuts(root: tk.Misc) -> bool:
    """True gdy fokus jest w polu tekstowym (nie uruchamiaj skrótu)."""
    focus = root.focus_get()
    if focus is None:
        return False
    widget: tk.Misc | None = focus
    for _ in range(12):
        if widget is None:
            break
        try:
            cls = widget.winfo_class().lower()
        except tk.TclError:
            break
        if "entry" in cls or "text" in cls or "combobox" in cls:
            return True
        try:
            widget = widget.master
        except (AttributeError, tk.TclError):
            break
    return False


def dialog_blocks_shortcuts(root: tk.Misc) -> bool:
    """True gdy fokus jest w osobnym oknie dialogowym (Toplevel)."""
    focus = root.focus_get()
    if focus is None:
        return False
    cur: tk.Misc | None = focus
    while cur is not None:
        if isinstance(cur, tk.Toplevel) and cur != root:
            return True
        cur = cur.master  # type: ignore[assignment]
    return False
