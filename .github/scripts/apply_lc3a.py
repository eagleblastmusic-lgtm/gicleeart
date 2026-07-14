from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


controller_path = ROOT / "giclee_app" / "launcher_shortcut_controller.py"
controller_path.write_text(
    '''"""Czyste decyzje pollingu i aktywacji skrótów launchera."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum


class ShortcutActivationKind(str, Enum):
    """Wynik próby uruchomienia skrótu bez efektów ubocznych."""

    UNMAPPED = "unmapped"
    MISSING_COMPONENT = "missing_component"
    LAUNCH_PENDING = "launch_pending"
    READY = "ready"


@dataclass(frozen=True)
class ShortcutPollDecision:
    """Nowe naciśnięcia oraz stan do zapamiętania po próbce."""

    pressed_keys: tuple[str, ...]
    next_down: frozenset[str]


@dataclass(frozen=True)
class ShortcutActivation:
    """Czysta decyzja aktywacji jednego znormalizowanego klawisza."""

    kind: ShortcutActivationKind
    key: str
    folder_name: str | None = None

    @property
    def handled(self) -> bool:
        return self.kind is not ShortcutActivationKind.UNMAPPED


def _normalize_keys(values: Iterable[str]) -> frozenset[str]:
    normalized: set[str] = set()
    for value in values:
        key = str(value or "").strip().lower()
        if key:
            normalized.add(key)
    return frozenset(normalized)


def resolve_shortcut_poll(
    current_down: Iterable[str],
    previous_down: Iterable[str],
    *,
    active: bool,
    modifiers_down: bool,
) -> ShortcutPollDecision:
    """Rozstrzyga zbocze klawiszy i zawsze zwraca aktualny stan próbki."""

    current = _normalize_keys(current_down)
    previous = _normalize_keys(previous_down)
    pressed: tuple[str, ...] = ()
    if active and not modifiers_down:
        pressed = tuple(sorted(current - previous))
    return ShortcutPollDecision(
        pressed_keys=pressed,
        next_down=current,
    )


def resolve_shortcut_activation(
    shortcuts: Mapping[str, str],
    key: str,
    *,
    component_exists: bool,
    launch_pending: bool,
) -> ShortcutActivation:
    """Rozstrzyga mapowanie, brak komponentu, pending albo gotowość launchu."""

    normalized_key = str(key or "").strip().lower()
    folder = str(shortcuts.get(normalized_key) or "").strip()
    if not folder:
        return ShortcutActivation(
            kind=ShortcutActivationKind.UNMAPPED,
            key=normalized_key,
        )
    if not component_exists:
        return ShortcutActivation(
            kind=ShortcutActivationKind.MISSING_COMPONENT,
            key=normalized_key,
            folder_name=folder,
        )
    if launch_pending:
        return ShortcutActivation(
            kind=ShortcutActivationKind.LAUNCH_PENDING,
            key=normalized_key,
            folder_name=folder,
        )
    return ShortcutActivation(
        kind=ShortcutActivationKind.READY,
        key=normalized_key,
        folder_name=folder,
    )
''',
    encoding="utf-8",
)

options_path = ROOT / "giclee_app" / "options_category_launcher.py"
replace_once(
    options_path,
    "from .launcher_layout import resolve_sections\n"
    "from .launcher_shortcut_options import show_shortcut_options\n",
    "from .launcher_layout import resolve_sections\n"
    "from .launcher_shortcut_controller import (\n"
    "    ShortcutActivationKind,\n"
    "    resolve_shortcut_activation,\n"
    "    resolve_shortcut_poll,\n"
    ")\n"
    "from .launcher_shortcut_options import show_shortcut_options\n",
)

old_poll = '''        active = self._windows_launcher_is_foreground() and self._launcher_shortcuts_active()
        if active:
            try:
                ctrl_down = bool(int(user32.GetAsyncKeyState(_VK_CONTROL)) & 0x8000)
                alt_down = bool(int(user32.GetAsyncKeyState(_VK_MENU)) & 0x8000)
            except (AttributeError, OSError, TypeError, ValueError):
                ctrl_down = False
                alt_down = False
            if not ctrl_down and not alt_down:
                pressed_now = current_down - self._windows_shortcut_down
                for key in sorted(pressed_now):
                    if self._trigger_shortcut(key):
                        break

        # Zapamiętujemy stan także poza aktywnym oknem. Dzięki temu przytrzymany
        # klawisz nie uruchomi komponentu dopiero po powrocie do launchera.
        self._windows_shortcut_down = current_down
'''
new_poll = '''        active = self._windows_launcher_is_foreground() and self._launcher_shortcuts_active()
        modifiers_down = False
        if active:
            try:
                ctrl_down = bool(int(user32.GetAsyncKeyState(_VK_CONTROL)) & 0x8000)
                alt_down = bool(int(user32.GetAsyncKeyState(_VK_MENU)) & 0x8000)
            except (AttributeError, OSError, TypeError, ValueError):
                ctrl_down = False
                alt_down = False
            modifiers_down = ctrl_down or alt_down

        decision = resolve_shortcut_poll(
            current_down,
            self._windows_shortcut_down,
            active=active,
            modifiers_down=modifiers_down,
        )
        # Zapamiętujemy stan także poza aktywnym oknem. Dzięki temu przytrzymany
        # klawisz nie uruchomi komponentu dopiero po powrocie do launchera.
        self._windows_shortcut_down = set(decision.next_down)
        for key in decision.pressed_keys:
            if self._trigger_shortcut(key):
                break
'''
replace_once(options_path, old_poll, new_poll)

old_trigger = '''    def _trigger_shortcut(self, key: str) -> bool:
        folder = self._shortcut_map.get(key)
        if not folder:
            return False
        component = self._component_by_folder(folder)
        if component is None:
            self.status_var.set(
                f"Skrót «{shortcut_display_label(key)}»: brak komponentu {folder}"
            )
            return True
        if self._shortcut_launch_pending:
            return True

        self._shortcut_launch_pending = True
        self.status_var.set(
            f"Skrót {shortcut_display_label(key)}: otwieram {component.name}"
        )

        def launch_selected() -> None:
            self._shortcut_launch_pending = False
            self._launch(component)

        self.root.after_idle(launch_selected)
        return True
'''
new_trigger = '''    def _trigger_shortcut(self, key: str) -> bool:
        folder = self._shortcut_map.get(key)
        component = self._component_by_folder(folder) if folder else None
        decision = resolve_shortcut_activation(
            self._shortcut_map,
            key,
            component_exists=component is not None,
            launch_pending=self._shortcut_launch_pending,
        )
        if decision.kind is ShortcutActivationKind.UNMAPPED:
            return False
        if decision.kind is ShortcutActivationKind.MISSING_COMPONENT:
            self.status_var.set(
                f"Skrót «{shortcut_display_label(decision.key)}»: "
                f"brak komponentu {decision.folder_name}"
            )
            return True
        if decision.kind is ShortcutActivationKind.LAUNCH_PENDING:
            return True

        assert component is not None
        self._shortcut_launch_pending = True
        self.status_var.set(
            f"Skrót {shortcut_display_label(decision.key)}: otwieram {component.name}"
        )

        def launch_selected() -> None:
            self._shortcut_launch_pending = False
            self._launch(component)

        self.root.after_idle(launch_selected)
        return True
'''
replace_once(options_path, old_trigger, new_trigger)


test_path = ROOT / "tests" / "test_launcher_shortcut_controller.py"
test_path.write_text(
    r'''"""Testy LC-3A: czyste decyzje aktywacji skrótów."""

from __future__ import annotations

import ast
from pathlib import Path
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
    assert "self._shortcut_launch_pending = False" in trigger_block
    assert "self._launch(component)" in trigger_block


class _StatusRecorder:
    def __init__(self) -> None:
        self.values: list[str] = []

    def set(self, value: str) -> None:
        self.values.append(value)


class _RootRecorder:
    def __init__(self) -> None:
        self.callbacks: list[object] = []

    def after_idle(self, callback: object) -> None:
        self.callbacks.append(callback)


def _app_for_trigger(mapping: dict[str, str], component: object | None):
    app = OptionsCategoryGicleeApp.__new__(OptionsCategoryGicleeApp)
    app._shortcut_map = mapping
    app._shortcut_launch_pending = False
    app.status_var = _StatusRecorder()
    app.root = _RootRecorder()
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
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**LC-2C tile grid placement:** `launcher_grid_layout.py` waliduje i rozwiązuje launcher-local sloty siatki. Oba rendery używają jednego `place_tile()`, zachowując trzy kolumny, row offset, paddingi oraz realne ramki DnD.\n",
    "**LC-2C tile grid placement:** `launcher_grid_layout.py` waliduje i rozwiązuje launcher-local sloty siatki. Oba rendery używają jednego `place_tile()`, zachowując trzy kolumny, row offset, paddingi oraz realne ramki DnD.\n\n"
    "**LC-3A shortcut decisions:** `launcher_shortcut_controller.py` rozstrzyga zbocza klawiszy oraz wyniki `unmapped / missing / pending / ready`. WinAPI, bindtagi Tk, fokus, statusy i `after_idle` pozostają w `OptionsCategoryGicleeApp`.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-lc3a-contract.md"
replace_once(
    contract,
    "**Status:** fresh reconnaissance · contract freeze  ",
    "**Status:** LC-3A implemented",
)
