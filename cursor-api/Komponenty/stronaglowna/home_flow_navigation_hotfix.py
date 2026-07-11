"""Naprawa nawigacji HOME FLOW dla ukrytego Listboxa na Windows/Tk.

Główny edytor nadal korzysta z istniejącego callbacku ``<<ListboxSelect>>``.
Po zastąpieniu Listboxa przez Treeview kontrolka jest jednak odmapowana przez
``pack_forget()`` i Tk na Windows może nie dostarczyć jej zdarzenia wirtualnego.
Ten hotfix przechwytuje callbacki w czasie budowy UI i uruchamia je bezpośrednio,
gdy zdarzenie jest generowane na ukrytej kontrolce.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

_SELECT_EVENT = "<<ListboxSelect>>"
_CALLBACKS_ATTR = "_giclee_home_select_callbacks"
_PROXY_ATTR = "_giclee_home_event_proxy_installed"


def _dispatch_captured_callbacks(widget: Any) -> bool:
    callbacks = list(getattr(widget, _CALLBACKS_ATTR, ()) or ())
    if not callbacks:
        return False
    for callback in callbacks:
        callback(None)
    return True


def _install_event_proxy(widget: tk.Listbox) -> None:
    if getattr(widget, _PROXY_ATTR, False):
        return
    original_event_generate = widget.event_generate

    def event_generate_proxy(sequence: str, *args: Any, **kwargs: Any) -> Any:
        if sequence == _SELECT_EVENT:
            try:
                mapped = bool(widget.winfo_ismapped())
            except tk.TclError:
                mapped = False
            if not mapped and _dispatch_captured_callbacks(widget):
                return None
        return original_event_generate(sequence, *args, **kwargs)

    widget.event_generate = event_generate_proxy  # type: ignore[method-assign]
    setattr(widget, _PROXY_ATTR, True)


def _walk_listboxes(widget: tk.Misc):
    for child in widget.winfo_children():
        if isinstance(child, tk.Listbox):
            yield child
        yield from _walk_listboxes(child)


def install_home_flow_navigation_hotfix() -> None:
    from . import gui

    current = gui._build_ui
    if getattr(current, "_giclee_hidden_list_dispatch", False):
        return

    def build_ui_with_hidden_list_dispatch(host: tk.Misc, *, inline: bool = False) -> None:
        original_bind = tk.Listbox.bind

        def capture_bind(
            widget: tk.Listbox,
            sequence: str | None = None,
            func: Callable[..., Any] | None = None,
            add: str | None = None,
        ) -> Any:
            result = original_bind(widget, sequence, func, add)
            if sequence == _SELECT_EVENT and callable(func):
                callbacks = list(getattr(widget, _CALLBACKS_ATTR, ()) or ())
                if add == "+":
                    callbacks.append(func)
                else:
                    callbacks = [func]
                setattr(widget, _CALLBACKS_ATTR, callbacks)
            return result

        tk.Listbox.bind = capture_bind  # type: ignore[method-assign]
        try:
            current(host, inline=inline)
        except Exception:
            tk.Listbox.bind = original_bind  # type: ignore[method-assign]
            raise

        def finalize() -> None:
            tk.Listbox.bind = original_bind  # type: ignore[method-assign]
            try:
                for listbox in _walk_listboxes(host):
                    if getattr(listbox, _CALLBACKS_ATTR, None):
                        _install_event_proxy(listbox)
            except tk.TclError:
                return

        # Pierwszy idle pozwala zewnętrznej nakładce HOME FLOW ukryć Listbox i
        # dopiąć swój callback synchronizujący Treeview. Drugi instaluje proxy.
        host.after_idle(lambda: host.after_idle(finalize))

    setattr(build_ui_with_hidden_list_dispatch, "_giclee_hidden_list_dispatch", True)
    setattr(build_ui_with_hidden_list_dispatch, "__wrapped__", current)
    gui._build_ui = build_ui_with_hidden_list_dispatch
