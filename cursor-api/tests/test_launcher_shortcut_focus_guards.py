"""Testy fail-closed dla odczytu fokusu skrótów launchera."""

from __future__ import annotations

import tkinter as tk

import pytest

from giclee_app import launcher_shortcuts as shortcuts


class _Root:
    master = None

    def __init__(
        self,
        focus: object | None = None,
        *,
        grabbed: object | None = None,
        children: list[object] | None = None,
        fail: bool = False,
        fail_children: bool = False,
        fail_grab: bool = False,
    ) -> None:
        self.focus = focus
        self.grabbed = grabbed
        self.children = list(children or [])
        self.fail = fail
        self.fail_children = fail_children
        self.fail_grab = fail_grab

    def focus_get(self) -> object | None:
        if self.fail:
            raise tk.TclError("focus is unavailable")
        return self.focus

    def grab_current(self) -> object | None:
        if self.fail_grab:
            raise tk.TclError("grab is unavailable")
        return self.grabbed

    def winfo_children(self) -> list[object]:
        if self.fail_children:
            raise tk.TclError("children are unavailable")
        return list(self.children)

    def winfo_class(self) -> str:
        return "Tk"


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
        def __init__(self, master: object, *, mapped: bool = True) -> None:
            self.master = master
            self.mapped = mapped

        def winfo_ismapped(self) -> bool:
            return self.mapped

    monkeypatch.setattr(shortcuts.tk, "Toplevel", _FakeToplevel)
    root = _Root()
    root.focus = _FakeToplevel(root)

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_grabbed_toplevel_blocks_when_focus_stays_on_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeToplevel:
        def __init__(self, master: object) -> None:
            self.master = master

        def winfo_ismapped(self) -> bool:
            return False

    monkeypatch.setattr(shortcuts.tk, "Toplevel", _FakeToplevel)
    root = _Root()
    root.focus = root
    root.grabbed = _FakeToplevel(root)

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_mapped_toplevel_blocks_when_focus_stays_on_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeToplevel:
        def __init__(self, master: object, *, mapped: bool) -> None:
            self.master = master
            self.mapped = mapped

        def winfo_ismapped(self) -> bool:
            return self.mapped

    monkeypatch.setattr(shortcuts.tk, "Toplevel", _FakeToplevel)
    root = _Root()
    root.focus = root
    root.children = [_FakeToplevel(root, mapped=True)]

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_unmapped_toplevel_does_not_block_when_focus_stays_on_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeToplevel:
        def __init__(self, master: object, *, mapped: bool) -> None:
            self.master = master
            self.mapped = mapped

        def winfo_ismapped(self) -> bool:
            return self.mapped

    monkeypatch.setattr(shortcuts.tk, "Toplevel", _FakeToplevel)
    root = _Root()
    root.focus = root
    root.children = [_FakeToplevel(root, mapped=False)]

    assert shortcuts.dialog_blocks_shortcuts(root) is False


def test_focus_get_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(fail=True)

    assert shortcuts.focus_blocks_shortcuts(root) is True
    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_grab_current_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(fail_grab=True)

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_winfo_children_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(fail_children=True)

    assert shortcuts.dialog_blocks_shortcuts(root) is True


def test_widget_class_tcl_error_blocks_shortcuts_fail_closed() -> None:
    root = _Root(_BrokenClassWidget())

    assert shortcuts.focus_blocks_shortcuts(root) is True


def test_broken_widget_hierarchy_blocks_shortcuts_fail_closed() -> None:
    root = _Root(_BrokenMasterWidget())

    assert shortcuts.focus_blocks_shortcuts(root) is True
    assert shortcuts.dialog_blocks_shortcuts(root) is True
