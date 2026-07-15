"""Testy ochrony markera bezpośredniego bindingu skrótów Tk."""

from __future__ import annotations

import tkinter as tk

import pytest

from giclee_app.launcher_tk_shortcut_bindings import bind_widget_shortcut


_MARKER = "_giclee_launcher_shortcut_bound"


def _callback(_event: object) -> None:
    return None


class _BrokenMarkerWidget:
    def __init__(self) -> None:
        self.bind_calls: list[tuple[str, object, str]] = []

    def __getattribute__(self, name: str) -> object:
        if name == _MARKER:
            raise tk.TclError("widget was destroyed")
        return object.__getattribute__(self, name)

    def bind(self, sequence: str, callback: object, add: str = "") -> str:
        self.bind_calls.append((sequence, callback, add))
        return "binding-id"


class _UnexpectedMarkerWidget:
    def __getattribute__(self, name: str) -> object:
        if name == _MARKER:
            raise RuntimeError("unexpected marker failure")
        return object.__getattribute__(self, name)

    def bind(self, sequence: str, callback: object, add: str = "") -> str:
        return "binding-id"


def test_marker_tcl_error_returns_false_before_binding() -> None:
    widget = _BrokenMarkerWidget()

    assert bind_widget_shortcut(widget, _callback) is False
    assert widget.bind_calls == []


def test_unexpected_marker_error_still_propagates() -> None:
    widget = _UnexpectedMarkerWidget()

    with pytest.raises(RuntimeError, match="unexpected marker failure"):
        bind_widget_shortcut(widget, _callback)
