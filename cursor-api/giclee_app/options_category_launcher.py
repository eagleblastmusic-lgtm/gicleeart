"""Launcher kategorii z menu Opcje i konfigurowalnymi skrótami."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from . import launcher as _launcher
from .launcher_layout import resolve_sections
from .launcher_shortcut_options import show_shortcut_options
from .launcher_shortcuts import (
    dialog_blocks_shortcuts,
    focus_blocks_shortcuts,
    load_launcher_shortcuts,
    shortcut_display_label,
    shortcut_key_from_event,
)
from .styled_category_launcher import StyledCategoryGicleeApp


class OptionsCategoryGicleeApp(StyledCategoryGicleeApp):
    """Spójny launcher z jednym menu ustawień i dynamicznymi skrótami."""

    def __init__(self, root: tk.Tk) -> None:
        self._shortcut_map = load_launcher_shortcuts()
        self._shortcut_bind_id: str | None = None
        self._shortcut_launch_pending = False
        self._options_menu: tk.Menu | None = None
        self._options_button: ttk.Menubutton | None = None
        super().__init__(root)

    def _build_ui(self) -> None:
        super()._build_ui()
        self._install_options_menu()

    def _bind_launcher_shortcuts(self) -> None:
        """Wiąże skróty z głównym oknem dokładnie raz.

        Poprzednia wersja używała ``bind_all`` i przy kolejnych powrotach z widoków
        inline mogła dokładać globalne callbacki. Dodatkowo aktywny grab menu/dialogu
        potrafił blokować mapę użytkownika także po zamknięciu okna ustawień.
        Binding na poziomie głównego Toplevel działa dla jego dzieci, ale nie przechwytuje
        klawiszy z obcych dialogów.
        """

        if self._shortcut_bind_id:
            try:
                self.root.unbind("<KeyPress>", self._shortcut_bind_id)
            except tk.TclError:
                pass
            self._shortcut_bind_id = None
        try:
            self._shortcut_bind_id = self.root.bind(
                "<KeyPress>",
                self._on_launcher_key_shortcut,
                add="+",
            )
        except tk.TclError:
            self._shortcut_bind_id = None

    def _find_widget_by_text(self, parent: tk.Misc, expected: str) -> tk.Widget | None:
        for child in parent.winfo_children():
            try:
                if child.cget("text") == expected:
                    return child
            except (tk.TclError, TypeError):
                pass
            found = self._find_widget_by_text(child, expected)
            if found is not None:
                return found
        return None

    def _install_options_menu(self) -> None:
        token_button = self._find_widget_by_text(self.root, "Token setup")
        session_button = self._find_widget_by_text(self.root, "Stan sesji")
        old_options_button = self._find_widget_by_text(self.root, "Opcje")
        instruction_button = self._find_widget_by_text(self.root, "Instrukcja")

        anchor = instruction_button or old_options_button or session_button or token_button
        if anchor is None or anchor.master is None:
            return
        toolbar = anchor.master

        for widget in (token_button, session_button, old_options_button):
            if widget is None:
                continue
            try:
                widget.destroy()
            except tk.TclError:
                pass

        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Token Setup", command=self._show_token_setup)
        menu.add_command(label="Stan sesji", command=self._show_session_status)
        menu.add_separator()
        menu.add_command(label="Układ kafelków", command=self._show_launcher_options)
        menu.add_command(label="Skróty", command=self._show_shortcut_options)

        options_button = ttk.Menubutton(toolbar, text="Opcje", menu=menu)
        pack_options: dict[str, Any] = {"side": "left", "padx": 4}
        if instruction_button is not None:
            pack_options["before"] = instruction_button
        options_button.pack(**pack_options)

        self._options_menu = menu
        self._options_button = options_button

    def _show_shortcut_options(self) -> None:
        sections = resolve_sections(
            self._all_components,
            self._layout,
            normally_visible=self._normally_visible,
        )
        show_shortcut_options(
            self.root,
            sections=sections,
            shortcuts=self._shortcut_map,
            on_saved=self._apply_shortcuts,
        )

    def _apply_shortcuts(self, shortcuts: dict[str, str]) -> None:
        self._shortcut_map = dict(shortcuts)
        # Odświeżamy binding i fokus po zamknięciu modala, aby nowe przypisanie
        # działało natychmiast bez ponownego uruchamiania aplikacji ani klikania tła.
        self._bind_launcher_shortcuts()
        self.root.after_idle(self._restore_shortcut_focus)
        self.status_var.set(f"Zapisano skróty: {len(self._shortcut_map)}")

    def _restore_shortcut_focus(self) -> None:
        if not self.tiles_view.winfo_ismapped():
            return
        try:
            self.root.lift()
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def _launcher_shortcut_key(self, event: tk.Event) -> str | None:
        return shortcut_key_from_event(event)

    def _launcher_shortcuts_active(self) -> bool:
        if not self.tiles_view.winfo_ismapped():
            return False
        if dialog_blocks_shortcuts(self.root):
            return False
        if focus_blocks_shortcuts(self.root):
            return False
        return True

    def _on_launcher_key_shortcut(self, event: tk.Event) -> str | None:
        if not self._launcher_shortcuts_active():
            return None
        if event.state & (0x4 | 0x8):  # Control, Alt
            return None
        key = self._launcher_shortcut_key(event)
        if not key:
            return None
        folder = self._shortcut_map.get(key)
        if not folder:
            return None
        component = self._component_by_folder(folder)
        if component is None:
            self.status_var.set(f"Skrót «{shortcut_display_label(key)}»: brak komponentu {folder}")
            return "break"
        if self._shortcut_launch_pending:
            return "break"

        self._shortcut_launch_pending = True
        self.status_var.set(
            f"Skrót {shortcut_display_label(key)}: otwieram {component.name}"
        )

        def launch_selected() -> None:
            self._shortcut_launch_pending = False
            self._launch(component)

        # Uruchomienie po zakończeniu obsługi KeyPress jest stabilniejsze dla widoków
        # inline, które w trakcie otwierania przebudowują główny kontener launchera.
        self.root.after_idle(launch_selected)
        return "break"


def main() -> None:
    """Uruchamia pełny launcher kategorii z menu Opcje."""

    original_class = _launcher.GicleeApp
    _launcher.GicleeApp = OptionsCategoryGicleeApp
    try:
        _launcher.main()
    finally:
        _launcher.GicleeApp = original_class


if __name__ == "__main__":
    main()
