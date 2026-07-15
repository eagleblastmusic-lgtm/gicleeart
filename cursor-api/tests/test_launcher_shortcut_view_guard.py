"""Testy fail-closed dla widoczności widoku skrótów launchera."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk

import pytest

from giclee_app import options_category_launcher as options
from giclee_app.launcher_tk_shortcut_visibility import shortcut_view_is_mapped
from giclee_app.launcher_windows_shortcuts import WindowsShortcutSample


class _View:
    def __init__(self, mapped: bool = True, *, fail: bool = False) -> None:
        self.mapped = mapped
        self.fail = fail

    def winfo_ismapped(self) -> bool:
        if self.fail:
            raise tk.TclError("view was destroyed")
        return self.mapped


class _RootRecorder:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, object]] = []
        self.focus_calls: list[str] = []

    def after(self, delay: int, callback: object) -> str:
        self.after_calls.append((delay, callback))
        return "poll-id"

    def lift(self) -> None:
        self.focus_calls.append("lift")

    def focus_force(self) -> None:
        self.focus_calls.append("focus_force")


@pytest.mark.parametrize(("mapped", "expected"), [(True, True), (False, False)])
def test_shortcut_view_mapping_is_preserved(mapped: bool, expected: bool) -> None:
    assert shortcut_view_is_mapped(_View(mapped)) is expected


def test_shortcut_view_tcl_error_fails_closed() -> None:
    assert shortcut_view_is_mapped(_View(fail=True)) is False


def test_restore_focus_returns_before_tk_calls_when_view_is_unavailable() -> None:
    app = options.OptionsCategoryGicleeApp.__new__(options.OptionsCategoryGicleeApp)
    app.tiles_view = _View(fail=True)
    app.root = _RootRecorder()
    app.canvas = object()
    app._install_shortcut_bindtags = lambda: (_ for _ in ()).throw(
        AssertionError("bindings must not be touched")
    )

    app._restore_shortcut_focus()

    assert app.root.focus_calls == []


def test_poll_reschedules_when_view_mapping_raises_tcl_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = options.OptionsCategoryGicleeApp.__new__(options.OptionsCategoryGicleeApp)
    app._windows_user32 = object()
    app._shortcut_map = {"i": "integracjagpt"}
    app._windows_shortcut_down = set()
    app._windows_shortcut_poll_id = None
    app.tiles_view = _View(fail=True)
    app.root = _RootRecorder()
    app._windows_launcher_is_foreground = lambda: True
    triggered: list[str] = []
    app._trigger_shortcut = lambda key: triggered.append(key) or True

    monkeypatch.setattr(
        options,
        "sample_windows_shortcut_keys",
        lambda _user32, _keys: WindowsShortcutSample(frozenset({"i"})),
    )
    monkeypatch.setattr(
        options,
        "windows_shortcut_modifiers_down",
        lambda _user32: (_ for _ in ()).throw(
            AssertionError("modifiers must not be sampled for inactive view")
        ),
    )

    app._poll_windows_shortcuts()

    assert app._windows_shortcut_down == {"i"}
    assert triggered == []
    assert app.root.after_calls == [(35, app._poll_windows_shortcuts)]
    assert app._windows_shortcut_poll_id == "poll-id"


def test_options_uses_shared_view_guard_in_both_runtime_paths() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "options_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    restore = source.split("def _restore_shortcut_focus", 1)[1].split(
        "\n    def ", 1
    )[0]
    active = source.split("def _launcher_shortcuts_active", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert "shortcut_view_is_mapped(self.tiles_view)" in restore
    assert "shortcut_view_is_mapped(self.tiles_view)" in active
    assert "winfo_ismapped" not in restore
    assert "winfo_ismapped" not in active
