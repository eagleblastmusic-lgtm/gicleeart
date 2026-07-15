"""Regresja fokusu Tk po splashu w launcherze używającym WinAPI."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from giclee_app import options_category_launcher as options


class _RootRecorder:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, Callable[[], object]]] = []

    def after(self, delay: int, callback: Callable[[], object]) -> str:
        self.after_calls.append((delay, callback))
        return f"after-{delay}"


def _build_without_tk(
    monkeypatch: pytest.MonkeyPatch,
    *,
    user32: object | None,
) -> tuple[options.OptionsCategoryGicleeApp, _RootRecorder]:
    root = _RootRecorder()
    monkeypatch.setattr(options, "load_launcher_shortcuts", lambda: {})
    monkeypatch.setattr(options, "_load_windows_user32", lambda: user32)

    def fake_super_init(app: object, received_root: object) -> None:
        app.root = received_root

    monkeypatch.setattr(
        options.StyledCategoryGicleeApp,
        "__init__",
        fake_super_init,
    )
    app = options.OptionsCategoryGicleeApp(root)  # type: ignore[arg-type]
    return app, root


def test_windows_mode_schedules_polling_and_tk_focus_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, root = _build_without_tk(monkeypatch, user32=object())

    assert [delay for delay, _callback in root.after_calls] == [120, 80, 320]
    assert root.after_calls[0][1] == app._poll_windows_shortcuts
    assert root.after_calls[1][1] == app._restore_shortcut_focus
    assert root.after_calls[2][1] == app._restore_shortcut_focus
    assert app._windows_shortcut_poll_id == "after-120"


def test_tk_fallback_still_schedules_the_same_focus_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app, root = _build_without_tk(monkeypatch, user32=None)

    assert [delay for delay, _callback in root.after_calls] == [80, 320]
    assert all(
        callback == app._restore_shortcut_focus
        for _delay, callback in root.after_calls
    )
    assert app._windows_shortcut_poll_id is None
