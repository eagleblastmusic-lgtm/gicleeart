"""Interakcje dwuklikiem dla drzewa Notatnika."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Literal

from . import gui as _gui
from .ordered_gui import OrderedNotatnikApp

DoubleClickAction = Literal["toggle", "rename", "none"]


def double_click_action(iid: str, path: Path, is_virtual: bool) -> DoubleClickAction:
    """Zwraca bezpieczna akcje dwukliku dla elementu drzewa."""
    if not iid:
        return "none"
    if is_virtual or path.is_dir():
        return "toggle"
    if path.is_file() and path.suffix.lower() == ".md":
        return "rename"
    return "none"


class InteractiveNotatnikApp(OrderedNotatnikApp):
    """Notatnik z reczna kolejnoscia oraz akcjami dwukliku."""

    def _build_ui(self) -> None:
        super()._build_ui()
        # Zastepuje bazowy binding, aby akcja zawsze dotyczyla wiersza pod kursorem.
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _on_tree_double_click(self, event: tk.Event | None = None) -> str:
        iid = self.tree.identify_row(event.y) if event is not None else ""
        if not iid:
            selection = self.tree.selection()
            iid = selection[0] if selection else ""
        if not iid:
            return "break"

        self.tree.selection_set(iid)
        self.tree.focus(iid)
        path, is_virtual = self._resolve_tree_path(iid)
        action = double_click_action(iid, path, is_virtual)

        if action == "toggle":
            self.tree.item(iid, open=not bool(self.tree.item(iid, "open")))
        elif action == "rename":
            self._rename_note(path)

        return "break"


def main() -> None:
    """Uruchamia Notatnik z rozszerzonym zachowaniem drzewa."""
    original_class = _gui.NotatnikApp
    _gui.NotatnikApp = InteractiveNotatnikApp
    try:
        _gui.main()
    finally:
        _gui.NotatnikApp = original_class
