"""Launcher kategorii z menu Opcje i konfigurowalnymi skrótami."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from . import launcher as _launcher
from .launcher_layout import resolve_sections
from .launcher_shortcut_controller import (
    ShortcutActivationKind,
    resolve_shortcut_activation,
    resolve_shortcut_poll,
)
from .launcher_shortcut_options import show_shortcut_options
from .launcher_tk_shortcut_bindings import (
    bind_shortcut_class,
    bind_widget_shortcut,
    install_shortcut_bindtags,
)
from .launcher_windows_shortcuts import (
    load_windows_user32 as _load_windows_user32,
    sample_windows_shortcut_keys,
    shortcut_virtual_key,
    windows_launcher_is_foreground,
    windows_shortcut_modifiers_down,
)
from .launcher_shortcuts import (
    dialog_blocks_shortcuts,
    focus_blocks_shortcuts,
    load_launcher_shortcuts,
    shortcut_display_label,
    shortcut_key_from_event,
)
from .styled_category_launcher import StyledCategoryGicleeApp


_WINDOWS_SHORTCUT_POLL_MS = 35


class OptionsCategoryGicleeApp(StyledCategoryGicleeApp):
    """Spójny launcher z jednym menu ustawień i dynamicznymi skrótami."""

    def __init__(self, root: tk.Tk) -> None:
        self._shortcut_map = load_launcher_shortcuts()
        self._shortcut_launch_pending = False
        self._shortcut_bindtag = f"GicleeLauncherShortcuts_{id(self)}"
        self._windows_user32 = _load_windows_user32()
        self._windows_shortcut_down: set[str] = set()
        self._windows_shortcut_poll_id: str | None = None
        self._options_menu: tk.Menu | None = None
        self._options_button: ttk.Menubutton | None = None
        super().__init__(root)

        # Root jest początkowo withdrawn przez splash. Poller nie potrzebuje fokusu
        # konkretnego widgetu, ale uruchamiamy go dopiero po zbudowaniu launchera.
        if self._windows_user32 is not None:
            try:
                self._windows_shortcut_poll_id = self.root.after(
                    120,
                    self._poll_windows_shortcuts,
                )
            except tk.TclError:
                self._windows_shortcut_poll_id = None
        else:
            try:
                self.root.after(80, self._restore_shortcut_focus)
                self.root.after(320, self._restore_shortcut_focus)
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        super()._build_ui()
        self._install_options_menu()
        self._install_shortcut_bindtags()
        try:
            self.root.bind(
                "<Map>",
                lambda _event: self.root.after_idle(self._restore_shortcut_focus),
                add="+",
            )
        except tk.TclError:
            pass

    def _render_tiles(self) -> None:
        super()._render_tiles()
        try:
            self.root.after_idle(self._install_shortcut_bindtags)
        except tk.TclError:
            pass

    def _bind_launcher_shortcuts(self) -> None:
        """Rejestruje fallback Tk wyłącznie poza trybem WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        if not bind_shortcut_class(
            self.root,
            self._shortcut_bindtag,
            self._on_launcher_key_shortcut,
        ):
            return
        self._install_shortcut_bindtags()

    def _install_shortcut_bindtags(self) -> None:
        """Instaluje fallback Tk na całym drzewie widgetów poza Windows WinAPI."""

        if getattr(self, "_windows_user32", None) is not None:
            return
        install_shortcut_bindtags(
            self.root,
            self._shortcut_bindtag,
            self._on_launcher_key_shortcut,
            bind_direct=self._bind_shortcut_directly,
        )

    def _bind_shortcut_directly(self, widget: tk.Misc) -> None:
        bind_widget_shortcut(widget, self._on_launcher_key_shortcut)

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
        self._windows_shortcut_down.clear()
        self._bind_launcher_shortcuts()
        try:
            self.root.after_idle(self._restore_shortcut_focus)
        except tk.TclError:
            pass
        labels = ", ".join(
            shortcut_display_label(key) for key in sorted(self._shortcut_map)
        )
        self.status_var.set(
            f"Zapisano skróty: {labels}" if labels else "Usunięto wszystkie skróty"
        )

    def _restore_shortcut_focus(self) -> None:
        if not self.tiles_view.winfo_ismapped():
            return
        try:
            self.root.lift()
            self.root.focus_force()
            self.canvas.focus_set()
            self._install_shortcut_bindtags()
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

    def _windows_launcher_is_foreground(self) -> bool:
        user32 = self._windows_user32
        if user32 is None:
            return False
        try:
            window_id = int(self.root.winfo_id())
        except (TypeError, ValueError, tk.TclError):
            return False
        return windows_launcher_is_foreground(user32, window_id)

    def _poll_windows_shortcuts(self) -> None:
        user32 = self._windows_user32
        if user32 is None:
            return

        sample = sample_windows_shortcut_keys(user32, self._shortcut_map)
        current_down = set(sample.current_down)

        active = self._windows_launcher_is_foreground() and self._launcher_shortcuts_active()
        modifiers_down = windows_shortcut_modifiers_down(user32) if active else False

        decision = resolve_shortcut_poll(
            current_down,
            self._windows_shortcut_down,
            active=active,
            modifiers_down=modifiers_down,
        )
        # Zapamiętujemy stan także poza aktywnym oknem. Dzięki temu przytrzymany
        # klawisz nie uruchomi komponentu dopiero po powrocie do launchera.
        self._windows_shortcut_down = set(decision.next_down)
        for key in decision.pressed_keys:
            if self._trigger_shortcut(key):
                break
        try:
            self._windows_shortcut_poll_id = self.root.after(
                _WINDOWS_SHORTCUT_POLL_MS,
                self._poll_windows_shortcuts,
            )
        except tk.TclError:
            self._windows_shortcut_poll_id = None

    def _trigger_shortcut(self, key: str) -> bool:
        folder = self._shortcut_map.get(key)
        component = self._component_by_folder(folder) if folder else None
        decision = resolve_shortcut_activation(
            self._shortcut_map,
            key,
            component_exists=component is not None,
            launch_pending=self._shortcut_launch_pending,
        )
        if decision.kind is ShortcutActivationKind.UNMAPPED:
            return False
        if decision.kind is ShortcutActivationKind.MISSING_COMPONENT:
            self.status_var.set(
                f"Skrót «{shortcut_display_label(decision.key)}»: "
                f"brak komponentu {decision.folder_name}"
            )
            return True
        if decision.kind is ShortcutActivationKind.LAUNCH_PENDING:
            return True

        assert component is not None
        self._shortcut_launch_pending = True
        self.status_var.set(
            f"Skrót {shortcut_display_label(decision.key)}: otwieram {component.name}"
        )

        def launch_selected() -> None:
            self._shortcut_launch_pending = False
            self._launch(component)

        try:
            self.root.after_idle(launch_selected)
        except tk.TclError:
            self._shortcut_launch_pending = False
        return True

    def _on_launcher_key_shortcut(self, event: tk.Event) -> str | None:
        if not self._launcher_shortcuts_active():
            return None
        if event.state & (0x4 | 0x8):
            return None
        key = self._launcher_shortcut_key(event)
        if not key:
            return None
        return "break" if self._trigger_shortcut(key) else None


def main() -> None:
    """Uruchamia pełny launcher kategorii z menu Opcje."""

    _launcher.main(app_factory=OptionsCategoryGicleeApp)


if __name__ == "__main__":
    main()
