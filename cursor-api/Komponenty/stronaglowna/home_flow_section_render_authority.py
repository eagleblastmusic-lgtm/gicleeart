"""Autorytatywny renderer sekcji dla nawigacji GICLÉE HOME FLOW.

Treeview i edytor faz korzystają z kilku callbacków ``after_idle``. Aby formularz
fazy nie pozostał w prawym panelu po kliknięciu sekcji, każde zaznaczenie
``section:*`` kończy się wymuszonym uruchomieniem bazowego callbacku Listboxa.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Iterable

from . import home_flow_gui as base_gui
from .home_flow import flow_item_by_id
from .home_flow_navigation_hotfix import _dispatch_captured_callbacks
from .homepage_variants import active_variant_id
from .registry import HOME_ZONES

_BOUND_ATTR = "_giclee_section_render_authority_bound"
_RENDERING_ATTR = "_giclee_section_render_authority_running"
_TOKEN_ATTR = "_giclee_section_render_authority_token"


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


def _next_token(host: tk.Misc) -> int:
    token = int(getattr(host, _TOKEN_ATTR, 0) or 0) + 1
    setattr(host, _TOKEN_ATTR, token)
    return token


def _force_section_render(
    host: tk.Misc,
    tree: ttk.Treeview,
    stable_id: str,
    token: int,
) -> None:
    if int(getattr(host, _TOKEN_ATTR, 0) or 0) != token:
        return
    selected = tree.selection()
    if not selected or str(selected[0]) != stable_id:
        return
    if bool(getattr(host, _RENDERING_ATTR, False)):
        return

    index = _zone_index_for_section(stable_id)
    if index is None:
        return
    listbox = base_gui._find_section_list(host)
    if listbox is None:
        return

    setattr(host, _RENDERING_ATTR, True)
    try:
        listbox.selection_clear(0, "end")
        listbox.selection_set(index)
        listbox.activate(index)
        if not _dispatch_captured_callbacks(listbox):
            listbox.event_generate("<<ListboxSelect>>")
    finally:
        setattr(host, _RENDERING_ATTR, False)


def _decorate_section_authority(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    if tree is None or getattr(tree, _BOUND_ATTR, False):
        return
    setattr(tree, _BOUND_ATTR, True)

    def on_select(_event=None) -> None:
        if bool(getattr(host, _RENDERING_ATTR, False)):
            return
        selected = tree.selection()
        stable_id = str(selected[0]) if selected else ""
        token = _next_token(host)
        if not stable_id.startswith("section:"):
            return

        # Po wszystkich callbackach bieżącego wyboru sekcja ma zostać ostatnim
        # renderem prawego panelu. Dodatkowy after(1) zabezpiecza Windows/Tk przed
        # późniejszym callbackiem z tej samej kolejki idle.
        host.after_idle(
            lambda sid=stable_id, current=token: host.after(
                1,
                lambda: _force_section_render(host, tree, sid, current),
            )
        )

    tree.bind("<<TreeviewSelect>>", on_select, add="+")


def install_home_flow_section_render_authority() -> None:
    current = base_gui._decorate_home_editor
    if getattr(current, "_giclee_section_render_authority", False):
        return

    def decorate_with_section_authority(host: tk.Misc) -> None:
        current(host)
        host.after_idle(lambda: _decorate_section_authority(host))

    setattr(decorate_with_section_authority, "_giclee_section_render_authority", True)
    setattr(decorate_with_section_authority, "__wrapped__", current)
    base_gui._decorate_home_editor = decorate_with_section_authority
