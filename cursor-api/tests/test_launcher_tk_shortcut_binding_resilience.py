"""Testy odporności traversalu fallbackowych bindingów Tk."""

from __future__ import annotations

import tkinter as tk

import pytest

from giclee_app.launcher_tk_shortcut_bindings import install_shortcut_bindtags


class _Widget:
    def __init__(
        self,
        name: str,
        *,
        children: list["_Widget"] | None = None,
        fail_bindtags: bool = False,
        fail_children: bool = False,
    ) -> None:
        self.name = name
        self.children = children or []
        self.fail_bindtags = fail_bindtags
        self.fail_children = fail_children
        self.tags: tuple[str, ...] = (name, "all")

    def winfo_children(self) -> list["_Widget"]:
        if self.fail_children:
            raise tk.TclError(f"children unavailable: {self.name}")
        return list(self.children)

    def bindtags(self, tags: tuple[str, ...] | None = None) -> tuple[str, ...]:
        if self.fail_bindtags:
            raise tk.TclError(f"bindtags unavailable: {self.name}")
        if tags is not None:
            self.tags = tuple(tags)
        return self.tags


def _callback(_event: object) -> None:
    return None


def test_bindtag_error_on_parent_does_not_block_child_or_direct_fallback() -> None:
    child = _Widget("child")
    parent = _Widget("parent", children=[child], fail_bindtags=True)
    visited: list[str] = []

    install_shortcut_bindtags(
        parent,
        "LauncherTag",
        _callback,
        bind_direct=lambda widget: visited.append(widget.name),
    )

    assert visited == ["parent", "child"]
    assert child.tags == ("LauncherTag", "child", "all")


def test_direct_tcl_error_on_parent_does_not_block_child() -> None:
    child = _Widget("child")
    parent = _Widget("parent", children=[child])
    visited: list[str] = []

    def direct(widget: _Widget) -> None:
        if widget is parent:
            raise tk.TclError("parent direct binding failed")
        visited.append(widget.name)

    install_shortcut_bindtags(
        parent,
        "LauncherTag",
        _callback,
        bind_direct=direct,
    )

    assert parent.tags == ("LauncherTag", "parent", "all")
    assert child.tags == ("LauncherTag", "child", "all")
    assert visited == ["child"]


def test_children_error_does_not_block_current_widget_binding() -> None:
    widget = _Widget("current", fail_children=True)
    visited: list[str] = []

    install_shortcut_bindtags(
        widget,
        "LauncherTag",
        _callback,
        bind_direct=lambda current: visited.append(current.name),
    )

    assert widget.tags == ("LauncherTag", "current", "all")
    assert visited == ["current"]


def test_unexpected_direct_error_still_propagates() -> None:
    widget = _Widget("current")

    with pytest.raises(RuntimeError, match="unexpected"):
        install_shortcut_bindtags(
            widget,
            "LauncherTag",
            _callback,
            bind_direct=lambda _widget: (_ for _ in ()).throw(
                RuntimeError("unexpected")
            ),
        )
