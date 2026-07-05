"""Testy bezpiecznej rejestracji tkdnd."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty._shared import tkdnd_safe


class _TclError(Exception):
    pass


class _FailingWidget:
    def drop_target_register(self, _kind: object) -> None:
        raise _TclError('invalid command name "tkdnd::drop_target"')

    def dnd_bind(self, _event: str, _handler: object) -> None:
        raise AssertionError("dnd_bind should not run after failed register")


class _OkWidget:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def drop_target_register(self, kind: object) -> None:
        self.kind = kind

    def dnd_bind(self, event: str, handler: object) -> None:
        self.events.append((event, handler))


def test_register_drop_target_returns_false_on_tcl_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tkdnd_safe, "_DND_IMPORTED", True)
    monkeypatch.setattr(tkdnd_safe, "DND_FILES", "DND_FILES")

    ok = tkdnd_safe.register_drop_target(_FailingWidget(), on_drop=lambda e: None)

    assert ok is False


def test_register_drop_target_returns_false_when_not_imported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tkdnd_safe, "_DND_IMPORTED", False)
    monkeypatch.setattr(tkdnd_safe, "DND_FILES", None)

    ok = tkdnd_safe.register_drop_target(_OkWidget(), on_drop=lambda e: None)

    assert ok is False


def test_register_drop_target_binds_events_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tkdnd_safe, "_DND_IMPORTED", True)
    monkeypatch.setattr(tkdnd_safe, "DND_FILES", "DND_FILES")
    widget = _OkWidget()
    on_drop = lambda e: None
    on_enter = lambda e: None
    on_leave = lambda e: None

    ok = tkdnd_safe.register_drop_target(
        widget,
        on_drop=on_drop,
        on_drag_enter=on_enter,
        on_drag_leave=on_leave,
    )

    assert ok is True
    assert widget.kind == "DND_FILES"
    assert [event for event, _ in widget.events] == ["<<Drop>>", "<<DragEnter>>", "<<DragLeave>>"]
