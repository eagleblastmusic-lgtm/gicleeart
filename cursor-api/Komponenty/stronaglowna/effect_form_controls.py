"""Wspólne włączanie/wyłączanie pól parametrów efektów (GUI strona główna)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable

_ENABLED_LABEL_FG = "#333333"
_DISABLED_LABEL_FG = "#aaaaaa"


def _widget_set_enabled(widget: tk.Misc, enabled: bool, *, readonly: bool = False) -> None:
    if widget is None:
        return
    wclass = widget.winfo_class()
    try:
        if wclass == "TCombobox":
            if enabled and readonly:
                widget.configure(state="readonly")
            elif enabled:
                widget.configure(state="normal")
            else:
                widget.configure(state="disabled")
        elif wclass in ("TSpinbox", "Spinbox"):
            widget.configure(state="normal" if enabled else "disabled")
        elif wclass in ("TCheckbutton", "Checkbutton", "TRadiobutton", "Radiobutton", "TButton", "Button"):
            widget.configure(state="normal" if enabled else "disabled")
        elif wclass == "TLabel":
            widget.configure(foreground=_ENABLED_LABEL_FG if enabled else _DISABLED_LABEL_FG)
        elif wclass == "TScale":
            widget.configure(state="normal" if enabled else "disabled")
    except tk.TclError:
        pass


class EffectControlGroup:
    """Zbiór widgetów współdzielących stan aktywny / wyszarzony."""

    def __init__(self) -> None:
        self._entries: list[tuple[tk.Misc, dict[str, Any]]] = []

    def add(self, widget: tk.Misc, *, readonly: bool = False) -> None:
        if widget is not None:
            self._entries.append((widget, {"readonly": readonly}))

    def add_all(self, widgets: list[tk.Misc], *, readonly: bool = False) -> None:
        for widget in widgets:
            self.add(widget, readonly=readonly)

    def set_enabled(self, enabled: bool) -> None:
        for widget, opts in self._entries:
            _widget_set_enabled(widget, enabled, **opts)


def bind_master_toggle(
    master_var: tk.BooleanVar,
    group: EffectControlGroup,
    *,
    extra_sync: Callable[[], None] | None = None,
) -> None:
    """Wyłącza `group`, gdy master_var == False; woła extra_sync po każdej zmianie."""

    def _sync(*_a: object) -> None:
        group.set_enabled(bool(master_var.get()))
        if extra_sync is not None:
            extra_sync()

    master_var.trace_add("write", _sync)
    _sync()
