"""Testy LC-3A: czyste decyzje aktywacji skrótów."""

from __future__ import annotations

import ast
from pathlib import Path
import tkinter as tk
from types import SimpleNamespace

import pytest

from giclee_app.launcher_shortcut_controller import (
    ShortcutActivationKind,
    resolve_shortcut_activation,
    resolve_shortcut_poll,
)
from giclee_app.options_category_launcher import OptionsCategoryGicleeApp


def test_active_poll_returns_sorted_new_keys_and_current_state() -> None:
    current = {"f2", "a", "b"}
    previous = {"b"}

    decision = resolve_shortcut_poll(
        current,
        previous,
        active=True,
        modifiers_down=False,
    )

    assert decision.pressed_keys == ("a", "f2")
    assert decision.next_down == frozenset({"a", "b", "f2"})


def test_held_key_is_not_returned_again() -> None:
    decision = resolve_shortcut_poll(
        {"i"},
        {"i"},
        active=True,
        modifiers_down=False,
    )
    assert decision.pressed_keys == ()
    assert decision.next_down == frozenset({"i"})


@pytest.mark.parametrize(
    ("active", "modifiers_down"),
    [(False, False), (True, True), (False, True)],
)
def test_inactive_or_modified_poll_blocks_activation_but_updates_state(
    active: bool,
    modifiers_down: bool,
) -> None:
    decision = resolve_shortcut_poll(
        {"i"},
        set(),
        active=active,
        modifiers_down=modifiers_down,
    )
    assert decision.pressed_keys == ()
    assert decision.next_down == frozenset({"i"})


def test_poll_does_not_mutate_inputs_and_normalizes_keys() -> None:
    current = [" A ", "F2", ""]
    previous = ["a"]
    current_before = list(current)
    previous_before = list(previous)

    decision = resolve_shortcut_poll(
        current,
        previous,
        active=True,
        modifiers_down=False,
    )

    assert current == current_before
    assert previous == previous_before
    assert decision.pressed_keys == ("f2",)
    assert decision.next_down == frozenset({"a", "f2"})


@pytest.mark.parametrize(
    ("mapping", "key", "component_exists", "pending", "kind", "handled", "folder"),
    [
        ({}, "i", False, False, ShortcutActivationKind.UNMAPPED, False, None),
        (
            {"i": "integracjagpt"},
            "I",
            False,
            False,
            ShortcutActivationKind.MISSING_COMPONENT,
            True,
            "integracjagpt",
        ),
        (
            {"i": "integracjagpt"},
            "i",
            True,
            True,
            ShortcutActivationKind.LAUNCH_PENDING,
            True,
            "integracjagpt",
        ),
        (
            {"i": "integracjagpt"},
            " i ",
            True,
            False,
            ShortcutActivationKind.READY,
            True,
            "integracjagpt",
        ),
    ],
)
def test_activation_outcomes(
    mapping: dict[str, str],
    key: str,
    component_exists: bool,
    pending: bool,
    kind: ShortcutActivationKind,
    handled: bool,
    folder: str | None,
) -> None:
    decision = resolve_shortcut_activation(
        mapping,
        key,
        component_exists=component_exists,
        launch_pending=pending,
    )
    assert decision.kind is kind
    assert decision.handled is handled
    assert decision.key == "i"
    assert decision.folder_name == folder


def test_missing_component_has_priority_over_pending() -> None:
    decision = resolve_shortcut_activation(
        {"n": "notatnik"},
        "n",
        component_exists=False,
        launch_pending=True,
    )
    assert decision.kind is ShortcutActivationKind.MISSING_COMPONENT


def test_controller_module_has_no_platform_ui_or_launcher_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_shortcut_controller.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "tkinter" not in imports
    assert "ctypes" not in imports
    assert "launcher" not in imports
    assert not any(name.startswith("giclee_app.ui") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)


def test_options_launcher_uses_poll_and_activation_resolvers() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "options_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    poll_block = source.split("def _poll_windows_shortcuts", 1)[1].split(
        "\n    def ", 1
    )[0]
    trigger_block = source.split("def _trigger_shortcut", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert "resolve_shortcut_poll(" in poll_block
    assert "self._windows_shortcut_down = set(decision.next_down)" in poll_block
    assert "for key in decision.pressed_keys" in poll_block
    assert "resolve_shortcut_activation(" in trigger_block
    assert "self.root.after_idle(launch_selected)" in trigger_block
    assert "except tk.TclError:" in trigger_block
    assert "self._shortcut_launch_pending = False" in trigger_block
    assert "self._launch(component)" in trigger_block


class _StatusRecorder:
    def __init__(self) -> None:
        self.values: list[str] = []

    def set(self, value: str) -> None:
        self.values.append(value)


class _RootRecorder:
    def __init__(self, *, fail_after_idle: bool = False) -> None:
        self.callbacks: list[object] = []
        self.fail_after_idle = fail_after_idle

    def after_idle(self, callback: object) -> None:
        if self.fail_after_idle:
            raise tk.TclError("root is unavailable")
        self.callbacks.append(callback)


def _app_for_trigger(
    mapping: dict[str, str],
    component: object | None,
    *,
    root: _RootRecorder | None = None,
):
    app = OptionsCategoryGicleeApp.__new__(OptionsCategoryGicleeApp)
    app._shortcut_map = mapping
    app._shortcut_launch_pending = False
    app.status_var = _StatusRecorder()
    app.root = root or _RootRecorder()
    app._component_by_folder = lambda _folder: component
    app.launched = []
    app._launch = app.launched.append
    return app


def test_trigger_ready_preserves_status_pending_and_after_idle_launch() -> None:
    component = SimpleNamespace(name="Notatnik")
    app = _app_for_trigger({"n": "notatnik"}, component)

    assert app._trigger_shortcut("n") is True
    assert app._shortcut_launch_pending is True
    assert app.status_var.values == ["Skrót N: otwieram Notatnik"]
    assert len(app.root.callbacks) == 1
    assert app.launched == []

    callback = app.root.callbacks[0]
    assert callable(callback)
    callback()

    assert app._shortcut_launch_pending is False
    assert app.launched == [component]


def test_trigger_rolls_back_pending_when_after_idle_fails() -> None:
    component = SimpleNamespace(name="Notatnik")
    root = _RootRecorder(fail_after_idle=True)
    app = _app_for_trigger({"n": "notatnik"}, component, root=root)

    assert app._trigger_shortcut("n") is True
    assert app._shortcut_launch_pending is False
    assert app.launched == []
    assert root.callbacks == []

    root.fail_after_idle = False
    assert app._trigger_shortcut("n") is True
    assert app._shortcut_launch_pending is True
    assert len(root.callbacks) == 1


def test_trigger_missing_and_unmapped_preserve_handled_contract() -> None:
    missing = _app_for_trigger({"n": "notatnik"}, None)
    assert missing._trigger_shortcut("n") is True
    assert missing.status_var.values == ["Skrót «N»: brak komponentu notatnik"]
    assert missing.root.callbacks == []

    unmapped = _app_for_trigger({}, None)
    assert unmapped._trigger_shortcut("x") is False
    assert unmapped.status_var.values == []
    assert unmapped.root.callbacks == []


def test_trigger_pending_does_not_schedule_second_launch() -> None:
    component = SimpleNamespace(name="Notatnik")
    app = _app_for_trigger({"n": "notatnik"}, component)
    app._shortcut_launch_pending = True

    assert app._trigger_shortcut("n") is True
    assert app.root.callbacks == []
    assert app.status_var.values == []
