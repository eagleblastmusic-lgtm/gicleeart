"""Testy fail-closed dla odczytu fokusu skrótów launchera."""

from __future__ import annotations

import tkinter as tk

import pytest

from giclee_app import launcher_shortcuts as shortcuts


class _Root:
    def __init__(self, focus: object | None = None, *, fail: bool = False) -> None:
        self.focus = focus
        self.fail = fail

    def focus_get(self) -> object | None:
        if self.fail:
            raise tk.TclError("focus is unavailable")
        return self.focus


class _Widget:
    def __init__(self, widget_class: str, master: object | None = None) -> None:
        self.widget_class = widget_class
        self.master = master

    def winfo_class(self) -> str:
        return self.widget_class


class _BrokenClassWidget:
    master = None

    def winfo_class(self) -> str:
        raise tk.TclError("widget was destroyed")


class _BrokenMasterWidget:
    def winfo_class(self) -> str:
        return "TLabel"

    @property
    def master(self) -> object:
        raise tk.TclError("widget hierarchy is unavailable")


def test_no_focus_does_not_block_shortcuts() -> None:
    root = _Root()

    assert shortcuts.focus_blocks_shortcuts(root) is False
    assert shortcuts.dialog_blocks_shortcuts(root) is False


@pytest.mark.parametrize("widget_class", ["Entry", "TEntry", "Text", "TCombobox"])
def test_text_input_focus_blocks_shortcuts(widget_class: str) -> None:
    root = _Root(_Widget(widget_class))

    assert shortcuts.focus_blocks_shortcuts(root) is True


def test_non_text_widget_chain_does_not_block_shortcuts() -> None:
    root = _Root()
    child = _Widget("TLabel", master=root)
    root.focus = child

    assert shortcuts.focus_blocks_shortcuts(root) is False
    assert shortcuts.dialog_blocks_shortcuts(root) is False


def test_toplevel_focus_blocks_shortcuts(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeToplevel:
        def __init__(self, master: object) -> None:
            self.master = master

    monkeypatch.setattr(shortcuts.tk, "Toplevel", _FakeToplevel)
    root = _Root()
    root.focus = _FakeToplevel(root)

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_focus_get_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(fail=True)

    assert shortcuts.focus_blocks_shortcuts(root) is True
    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_widget_class_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(_BrokenClassWidget())

    assert shortcuts.focus_blocks_shortcuts(root) is True


def test_broken_widget_hierarchy_blocks_shortcuts_fail_closed() -> None:
    root = _Root(_BrokenMasterWidget())

    assert shortcuts.focus_blocks_shortcuts(root) is True
    assert shortcuts.dialog_blocks_shortcuts(root) is True
