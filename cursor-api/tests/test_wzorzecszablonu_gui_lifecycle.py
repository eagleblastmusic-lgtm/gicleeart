from __future__ import annotations

import ast
from pathlib import Path
import tkinter as tk

from Komponenty.wzorzecszablonu.gui import _schedule_ui


class _Widget:
    def __init__(self, *, exists: bool = True, after_error: bool = False) -> None:
        self.exists = exists
        self.after_error = after_error
        self.pending = None

    def winfo_exists(self) -> bool:
        return self.exists

    def after(self, delay: int, callback):
        assert delay == 0
        if self.after_error:
            raise tk.TclError("interpreter destroyed")
        self.pending = callback
        return "after-id"


def test_schedule_ui_runs_for_live_view() -> None:
    widget = _Widget()
    calls: list[str] = []

    assert _schedule_ui(widget, lambda: calls.append("done")) is True
    assert widget.pending is not None

    widget.pending()

    assert calls == ["done"]


def test_schedule_ui_skips_callback_after_view_is_destroyed() -> None:
    widget = _Widget()
    calls: list[str] = []

    assert _schedule_ui(widget, lambda: calls.append("done")) is True
    assert widget.pending is not None

    widget.exists = False
    widget.pending()

    assert calls == []


def test_schedule_ui_handles_destroyed_interpreter() -> None:
    widget = _Widget(after_error=True)

    assert _schedule_ui(widget, lambda: None) is False


def test_workers_use_lifecycle_guard_instead_of_direct_after() -> None:
    source_path = (
        Path(__file__).resolve().parents[1]
        / "Komponenty"
        / "wzorzecszablonu"
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
            and func.value.id in {"host", "tree"}
        ):
            unsafe_lines.append(node.lineno)

    assert unsafe_lines == []
