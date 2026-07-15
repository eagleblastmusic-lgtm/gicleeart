"""Testy zastosowania zapisanej mapy skrótów w aktywnym launcherze."""

from __future__ import annotations

import ast
from pathlib import Path
import tkinter as tk

from giclee_app.options_category_launcher import OptionsCategoryGicleeApp


class _StatusRecorder:
    def __init__(self) -> None:
        self.values: list[str] = []

    def set(self, value: str) -> None:
        self.values.append(value)


class _RootRecorder:
    def __init__(self, *, fail_after_idle: bool = False) -> None:
        self.fail_after_idle = fail_after_idle
        self.callbacks: list[object] = []

    def after_idle(self, callback: object) -> None:
        if self.fail_after_idle:
            raise tk.TclError("root is unavailable")
        self.callbacks.append(callback)


def _app_for_apply(*, root: _RootRecorder) -> tuple[OptionsCategoryGicleeApp, list[str]]:
    app = OptionsCategoryGicleeApp.__new__(OptionsCategoryGicleeApp)
    app._shortcut_map = {"i": "integracjagpt"}
    app._windows_shortcut_down = {"i"}
    app.root = root
    app.status_var = _StatusRecorder()
    app._restore_shortcut_focus = lambda: None
    bind_calls: list[str] = []
    app._bind_launcher_shortcuts = lambda: bind_calls.append("bind")
    return app, bind_calls


def test_apply_shortcuts_keeps_success_when_focus_schedule_fails() -> None:
    root = _RootRecorder(fail_after_idle=True)
    app, bind_calls = _app_for_apply(root=root)

    app._apply_shortcuts({"n": "notatnik"})

    assert app._shortcut_map == {"n": "notatnik"}
    assert app._windows_shortcut_down == set()
    assert bind_calls == ["bind"]
    assert root.callbacks == []
    assert app.status_var.values == ["Zapisano skróty: N"]


def test_apply_shortcuts_schedules_focus_and_reports_empty_mapping() -> None:
    root = _RootRecorder()
    app, bind_calls = _app_for_apply(root=root)

    app._apply_shortcuts({})

    assert app._shortcut_map == {}
    assert app._windows_shortcut_down == set()
    assert bind_calls == ["bind"]
    assert root.callbacks == [app._restore_shortcut_focus]
    assert app.status_var.values == ["Usunięto wszystkie skróty"]


def test_apply_shortcuts_catches_only_focus_scheduling_tcl_error() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "options_category_launcher.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_apply_shortcuts"
    )
    try_node = next(node for node in method.body if isinstance(node, ast.Try))

    assert len(try_node.body) == 1
    call = try_node.body[0]
    assert isinstance(call, ast.Expr)
    assert isinstance(call.value, ast.Call)
    assert isinstance(call.value.func, ast.Attribute)
    assert call.value.func.attr == "after_idle"
    assert len(try_node.handlers) == 1
    handler = try_node.handlers[0]
    assert isinstance(handler.type, ast.Attribute)
    assert handler.type.attr == "TclError"

    status_calls = [
        node
        for node in method.body
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and node.value.func.attr == "set"
    ]
    assert len(status_calls) == 1
    assert method.body.index(status_calls[0]) > method.body.index(try_node)
