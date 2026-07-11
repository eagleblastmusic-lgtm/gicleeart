"""Naprawa powrotu z formularza fazy do edytora sekcji HOME FLOW.

Po kliknięciu fazy ukryty Listbox ma już wybraną sekcję-właściciela. Powrót do tej
samej sekcji nie zmienia indeksu Listboxa, więc Tk może nie uruchomić ponownie
bazowego renderera. Moduł pamięta aktywną fazę i wymusza bezpośrednie wywołanie
przechwyconych callbacków sekcji po następnym kliknięciu elementu section:*.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable

from . import home_flow_gui as base_gui
from .home_flow import flow_item_by_id
from .home_flow_navigation_hotfix import _dispatch_captured_callbacks
from .home_flow_phase_settings import KNOWN_PHASE_IDS
from .homepage_variants import active_variant_id
from .registry import HOME_ZONES

_ACTIVE_PHASE_ATTR = "_giclee_inline_active_phase"
_BOUND_ATTR = "_giclee_phase_return_bound"


def _walk(widget: tk.Misc) -> Iterable[tk.Misc]:
    for child in widget.winfo_children():
        yield child
        yield from _walk(child)


def _find_main_tree(host: tk.Misc) -> ttk.Treeview | None:
    for widget in _walk(host):
        if not isinstance(widget, ttk.Treeview):
            continue
        try:
            if "headings" not in str(widget.cget("show")):
                return widget
        except tk.TclError:
            continue
    return None


def _zone_index_for_section(stable_id: str) -> int | None:
    item = flow_item_by_id(active_variant_id(), stable_id)
    if item is None or item.kind != "section" or not item.zone_id:
        return None
    for index, zone in enumerate(HOME_ZONES):
        if zone.zone_id == item.zone_id:
            return index
    return None


def _restore_section_panel(host: tk.Misc, tree: ttk.Treeview, stable_id: str) -> None:
    if not tree.selection() or str(tree.selection()[0]) != stable_id:
        return
    index = _zone_index_for_section(stable_id)
    if index is None:
        return
    listbox = base_gui._find_section_list(host)
    if listbox is None:
        return

    listbox.selection_clear(0, "end")
    listbox.selection_set(index)
    listbox.activate(index)

    # Najpierw korzystamy z callbacków przechwyconych przez hotfix nawigacji.
    # Fallback event_generate pozostaje dla środowisk, w których kontrolka jest mapowana.
    if not _dispatch_captured_callbacks(listbox):
        listbox.event_generate("<<ListboxSelect>>")

    setattr(host, _ACTIVE_PHASE_ATTR, "")


def _decorate_phase_return(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    if tree is None or getattr(tree, _BOUND_ATTR, False):
        return
    setattr(tree, _BOUND_ATTR, True)

    def on_select(_event=None) -> None:
        selected = tree.selection()
        stable_id = str(selected[0]) if selected else ""
        if stable_id in KNOWN_PHASE_IDS:
            setattr(host, _ACTIVE_PHASE_ATTR, stable_id)
            return

        if not stable_id.startswith("section:"):
            return
        if not str(getattr(host, _ACTIVE_PHASE_ATTR, "") or ""):
            return

        host.after_idle(
            lambda sid=stable_id: _restore_section_panel(host, tree, sid)
        )

    tree.bind("<<TreeviewSelect>>", on_select, add="+")


def install_home_flow_phase_return_hotfix() -> None:
    current = base_gui._decorate_home_editor
    if getattr(current, "_giclee_phase_return_hotfix", False):
        return

    def decorate_with_phase_return(host: tk.Misc) -> None:
        current(host)
        host.after_idle(lambda: _decorate_phase_return(host))

    setattr(decorate_with_phase_return, "_giclee_phase_return_hotfix", True)
    setattr(decorate_with_phase_return, "__wrapped__", current)
    base_gui._decorate_home_editor = decorate_with_phase_return
