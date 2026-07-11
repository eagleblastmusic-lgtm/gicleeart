"""Bezpośrednia nawigacja sekcja/faza dla GICLÉE HOME FLOW.

Bazowy edytor buduje renderer sekcji jako funkcję lokalną ``_show_zone``. Starsza
nakładka próbowała sterować nim przez zdarzenie ukrytego Listboxa. Ten moduł
odnajduje oryginalny callback oraz jego renderer w domknięciu i wywołuje go
bezpośrednio. Dzięki temu powrót z formularza GH-Txx do GH-xx nie zależy od
kolejki zdarzeń Tk ani od mapowania kontrolki.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Iterable

from . import home_flow_gui as base_gui
from .home_flow import flow_item_by_id
from .home_flow_navigation_hotfix import _CALLBACKS_ATTR
from .home_flow_phase_settings import KNOWN_PHASE_IDS
from .homepage_variants import active_variant_id
from .registry import zone_by_id

_BOUND_ATTR = "_giclee_direct_navigation_bound"
_BRIDGE_ATTR = "_giclee_direct_navigation_bridge"


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


def _closure_value(func: Callable[..., Any], name: str) -> Any:
    code = getattr(func, "__code__", None)
    cells = getattr(func, "__closure__", None) or ()
    if code is None:
        return None
    names = tuple(getattr(code, "co_freevars", ()) or ())
    for free_name, cell in zip(names, cells):
        if free_name != name:
            continue
        try:
            return cell.cell_contents
        except ValueError:
            return None
    return None


def _resolve_bridge_from_callbacks(
    callbacks: Iterable[Callable[..., Any]],
) -> tuple[Callable[..., Any], Callable[..., Any] | None, dict[str, Any]] | None:
    for callback in callbacks:
        show_zone = _closure_value(callback, "_show_zone")
        if not callable(show_zone):
            continue
        collect = _closure_value(show_zone, "_collect_current_zone")
        state = _closure_value(show_zone, "state")
        if isinstance(state, dict):
            return show_zone, collect if callable(collect) else None, state
    return None


def _resolve_bridge(host: tk.Misc):
    cached = getattr(host, _BRIDGE_ATTR, None)
    if cached is not None:
        return cached
    listbox = base_gui._find_section_list(host)
    if listbox is None:
        return None
    callbacks = list(getattr(listbox, _CALLBACKS_ATTR, ()) or ())
    bridge = _resolve_bridge_from_callbacks(callbacks)
    if bridge is not None:
        setattr(host, _BRIDGE_ATTR, bridge)
    return bridge


def _prepare_phase(host: tk.Misc) -> None:
    bridge = _resolve_bridge(host)
    if bridge is None:
        return
    _show_zone, collect_current, state = bridge
    if state.get("selected_zone_id") and callable(collect_current):
        try:
            collect_current()
        except (tk.TclError, RuntimeError):
            pass
    # Formularz fazy nie jest formularzem sekcji. Zerujemy aktywną sekcję i
    # rejestr widgetów, aby późniejszy _show_zone nie próbował odczytać
    # zniszczonych kontrolek fazy jako pól sekcji.
    state["selected_zone_id"] = None
    widgets = state.get("widgets")
    if isinstance(widgets, dict):
        widgets.clear()
    refs = state.get("thumb_refs")
    if isinstance(refs, list):
        refs.clear()


def _select_section(host: tk.Misc, stable_id: str) -> bool:
    bridge = _resolve_bridge(host)
    if bridge is None:
        return False
    show_zone, _collect_current, state = bridge
    item = flow_item_by_id(active_variant_id(), stable_id)
    if item is None or item.kind != "section" or not item.zone_id:
        return False
    zone = zone_by_id(item.zone_id)
    if zone is None:
        return False

    # Gdy bazowy callback Listboxa już poprawnie narysował tę sekcję, nie
    # renderujemy jej drugi raz. Po formularzu fazy selected_zone_id jest None,
    # więc bezpośredni renderer zawsze zostanie uruchomiony.
    if state.get("selected_zone_id") == zone.zone_id:
        return True

    show_zone(zone)
    listbox = base_gui._find_section_list(host)
    if listbox is not None:
        try:
            index = next(i for i, row in enumerate(base_gui.HOME_ZONES) if row.zone_id == zone.zone_id)
            listbox.selection_clear(0, "end")
            listbox.selection_set(index)
            listbox.activate(index)
        except (StopIteration, tk.TclError):
            pass
    return True


def _decorate_direct_navigation(host: tk.Misc) -> None:
    tree = _find_main_tree(host)
    if tree is None or getattr(tree, _BOUND_ATTR, False):
        return
    if _resolve_bridge(host) is None:
        # Finalizacja przechwytywania callbacków następuje po dwóch idle.
        host.after(20, lambda: _decorate_direct_navigation(host))
        return

    setattr(tree, _BOUND_ATTR, True)

    def on_select(_event=None) -> None:
        selected = tree.selection()
        stable_id = str(selected[0]) if selected else ""
        if stable_id in KNOWN_PHASE_IDS:
            _prepare_phase(host)
            return
        if stable_id.startswith("section:"):
            _select_section(host, stable_id)

    tree.bind("<<TreeviewSelect>>", on_select, add="+")


def install_home_flow_direct_navigation() -> None:
    current = base_gui._decorate_home_editor
    if getattr(current, "_giclee_direct_navigation", False):
        return

    def decorate_with_direct_navigation(host: tk.Misc) -> None:
        current(host)
        host.after_idle(lambda: _decorate_direct_navigation(host))

    setattr(decorate_with_direct_navigation, "_giclee_direct_navigation", True)
    setattr(decorate_with_direct_navigation, "__wrapped__", current)
    base_gui._decorate_home_editor = decorate_with_direct_navigation
