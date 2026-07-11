from __future__ import annotations

from .home_flow_navigation_hotfix import (
    _CALLBACKS_ATTR,
    _dispatch_captured_callbacks,
)


class _FakeWidget:
    pass


def test_dispatch_captured_callbacks_runs_in_registration_order() -> None:
    widget = _FakeWidget()
    calls: list[str] = []
    setattr(
        widget,
        _CALLBACKS_ATTR,
        [lambda _event=None: calls.append("editor"), lambda _event=None: calls.append("tree")],
    )

    assert _dispatch_captured_callbacks(widget) is True
    assert calls == ["editor", "tree"]


def test_dispatch_captured_callbacks_returns_false_without_handlers() -> None:
    assert _dispatch_captured_callbacks(_FakeWidget()) is False
