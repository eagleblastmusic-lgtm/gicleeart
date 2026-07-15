from __future__ import annotations

import ast
from pathlib import Path
import tkinter as tk

from Komponenty.stronaproduktu.gui import _schedule_ui


class _Widget:
    def __init__(
        self,
        *,
        exists: bool = True,
        exists_error: bool = False,
        after_error: bool = False,
    ) -> None:
        self.exists = exists
        self.exists_error = exists_error
        self.after_error = after_error
        self.pending = None
        self.after_calls = 0

    def winfo_exists(self) -> bool:
        if self.exists_error:
            raise tk.TclError("widget unavailable")
        return self.exists

    def after(self, delay: int, callback):
        self.after_calls += 1
        assert delay == 0
        if self.after_error:
            raise tk.TclError("interpreter destroyed")
        self.pending = callback
        return "after-id"


def test_schedule_ui_runs_callback_for_live_widget() -> None:
    widget = _Widget()
    calls: list[str] = []

    assert _schedule_ui(widget, lambda: calls.append("done")) is True
    assert widget.pending is not None

    widget.pending()

    assert calls == ["done"]


def test_schedule_ui_ignores_widget_destroyed_before_scheduling() -> None:
    widget = _Widget(exists=False)
    calls: list[str] = []

    assert _schedule_ui(widget, lambda: calls.append("done")) is False
    assert widget.after_calls == 0
    assert calls == []


def test_schedule_ui_ignores_widget_destroyed_before_callback_runs() -> None:
    widget = _Widget()
    calls: list[str] = []

    assert _schedule_ui(widget, lambda: calls.append("done")) is True
    assert widget.pending is not None

    widget.exists = False
    widget.pending()

    assert calls == []


def test_schedule_ui_fails_closed_on_tcl_errors() -> None:
    assert _schedule_ui(_Widget(exists_error=True), lambda: None) is False
    assert _schedule_ui(_Widget(after_error=True), lambda: None) is False


def test_stronaproduktu_workers_do_not_schedule_directly_on_destroyable_views() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "Komponenty"
        / "stronaproduktu"
        / "gui.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    unsafe_lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "after"
            and isinstance(func.value, ast.Name)
            and func.value.id in {"host", "win"}
        ):
            unsafe_lines.append(node.lineno)

    assert unsafe_lines == []
