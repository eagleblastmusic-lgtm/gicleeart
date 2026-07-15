"""Testy priorytetowych bindingów powrotu z kategorii."""

from __future__ import annotations

import tkinter as tk

import pytest

from giclee_app.dragdrop_category_launcher import (
    DragDropCategoryGicleeApp,
    _CATEGORY_BACK_SEQUENCES,
)
from giclee_app.options_category_launcher import OptionsCategoryGicleeApp


class _RootRecorder:
    def __init__(self, *, fail_sequence: str | None = None) -> None:
        self.fail_sequence = fail_sequence
        self.calls: list[tuple[str, str, object, str]] = []

    def bind_class(
        self,
        bindtag: str,
        sequence: str,
        callback: object,
        add: str = "",
    ) -> None:
        if sequence == self.fail_sequence:
            raise tk.TclError("binding unavailable")
        self.calls.append((bindtag, sequence, callback, add))


def test_category_back_keys_use_priority_shortcut_bindtag() -> None:
    app = DragDropCategoryGicleeApp.__new__(DragDropCategoryGicleeApp)
    app.root = _RootRecorder()
    app._shortcut_bindtag = "LauncherPriority"

    app._bind_category_back_shortcuts()

    assert [call[1] for call in app.root.calls] == list(_CATEGORY_BACK_SEQUENCES)
    assert all(call[0] == "LauncherPriority" for call in app.root.calls)
    assert all(call[2] == app._on_category_back for call in app.root.calls)
    assert all(call[3] == "+" for call in app.root.calls)


def test_one_tcl_binding_error_does_not_block_remaining_keys() -> None:
    app = DragDropCategoryGicleeApp.__new__(DragDropCategoryGicleeApp)
    app.root = _RootRecorder(fail_sequence="<Escape>")
    app._shortcut_bindtag = "LauncherPriority"

    app._bind_category_back_shortcuts()

    assert [call[1] for call in app.root.calls] == ["<Alt-Left>", "<BackSpace>"]


def test_build_ui_installs_navigation_after_options_tree_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    app = DragDropCategoryGicleeApp.__new__(DragDropCategoryGicleeApp)

    monkeypatch.setattr(
        OptionsCategoryGicleeApp,
        "_build_ui",
        lambda _self: order.append("super"),
    )
    app._bind_category_back_shortcuts = lambda: order.append("navigation")

    DragDropCategoryGicleeApp._build_ui(app)

    assert order == ["super", "navigation"]
