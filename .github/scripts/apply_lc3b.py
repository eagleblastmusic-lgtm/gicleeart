from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


platform_path = ROOT / "giclee_app" / "launcher_windows_shortcuts.py"
platform_path.write_text(
    '''"""Platformowy adapter WinAPI dla skrótów klasycznego launchera."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import ctypes
import os
from typing import Any


_GA_ROOT = 2
_VK_CONTROL = 0x11
_VK_MENU = 0x12


@dataclass(frozen=True)
class WindowsShortcutSample:
    """Niemutowalna próbka aktualnie wciśniętych skrótów."""

    current_down: frozenset[str]


def shortcut_virtual_key(key: str) -> int | None:
    """Zwraca kod WinAPI dla litery, cyfry albo F1-F12."""

    normalized = str(key or "").strip().lower()
    if len(normalized) == 1 and normalized.isalpha() and normalized.isascii():
        return ord(normalized.upper())
    if len(normalized) == 1 and normalized.isdigit():
        return ord(normalized)
    if normalized.startswith("f") and normalized[1:].isdigit():
        number = int(normalized[1:])
        if 1 <= number <= 12:
            return 0x70 + number - 1
    return None


def load_windows_user32() -> Any | None:
    """Ładuje i konfiguruje user32 wyłącznie na Windows."""

    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        user32.GetAsyncKeyState.restype = ctypes.c_short
        return user32
    except (AttributeError, OSError):
        return None


def windows_launcher_is_foreground(user32: Any, window_id: int) -> bool:
    """Sprawdza, czy root HWND launchera jest aktywnym oknem systemowym."""

    try:
        hwnd = int(window_id)
        root_hwnd = int(user32.GetAncestor(ctypes.c_void_p(hwnd), _GA_ROOT) or hwnd)
        foreground = int(user32.GetForegroundWindow() or 0)
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    return foreground != 0 and foreground == root_hwnd


def sample_windows_shortcut_keys(
    user32: Any,
    keys: Iterable[str],
) -> WindowsShortcutSample:
    """Pobiera próbkę wyłącznie dla kluczy aktualnej mapy skrótów."""

    current_down: set[str] = set()
    for raw_key in keys:
        key = str(raw_key or "").strip().lower()
        vk = shortcut_virtual_key(key)
        if vk is None:
            continue
        try:
            if int(user32.GetAsyncKeyState(vk)) & 0x8000:
                current_down.add(key)
        except (AttributeError, OSError, TypeError, ValueError):
            continue
    return WindowsShortcutSample(current_down=frozenset(current_down))


def windows_shortcut_modifiers_down(user32: Any) -> bool:
    """Zwraca True, gdy wciśnięty jest Ctrl albo Alt."""

    try:
        ctrl_down = bool(int(user32.GetAsyncKeyState(_VK_CONTROL)) & 0x8000)
        alt_down = bool(int(user32.GetAsyncKeyState(_VK_MENU)) & 0x8000)
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    return ctrl_down or alt_down
''',
    encoding="utf-8",
)

options_path = ROOT / "giclee_app" / "options_category_launcher.py"
replace_once(
    options_path,
    "import ctypes\nimport os\nimport tkinter as tk\n",
    "import tkinter as tk\n",
)
replace_once(
    options_path,
    "from .launcher_shortcut_options import show_shortcut_options\n",
    "from .launcher_shortcut_options import show_shortcut_options\n"
    "from .launcher_windows_shortcuts import (\n"
    "    load_windows_user32 as _load_windows_user32,\n"
    "    sample_windows_shortcut_keys,\n"
    "    shortcut_virtual_key,\n"
    "    windows_launcher_is_foreground,\n"
    "    windows_shortcut_modifiers_down,\n"
    ")\n",
)
old_platform_block = '''_WINDOWS_SHORTCUT_POLL_MS = 35
_GA_ROOT = 2
_VK_CONTROL = 0x11
_VK_MENU = 0x12


def shortcut_virtual_key(key: str) -> int | None:
    """Zwraca kod WinAPI dla litery, cyfry albo F1-F12."""

    normalized = str(key or "").strip().lower()
    if len(normalized) == 1 and normalized.isalpha() and normalized.isascii():
        return ord(normalized.upper())
    if len(normalized) == 1 and normalized.isdigit():
        return ord(normalized)
    if normalized.startswith("f") and normalized[1:].isdigit():
        number = int(normalized[1:])
        if 1 <= number <= 12:
            return 0x70 + number - 1
    return None


def _load_windows_user32() -> Any | None:
    if os.name != "nt":
        return None
    try:
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
        user32.GetAsyncKeyState.restype = ctypes.c_short
        return user32
    except (AttributeError, OSError):
        return None
'''
replace_once(
    options_path,
    old_platform_block,
    "_WINDOWS_SHORTCUT_POLL_MS = 35\n",
)
old_foreground = '''    def _windows_launcher_is_foreground(self) -> bool:
        user32 = self._windows_user32
        if user32 is None:
            return False
        try:
            hwnd = int(self.root.winfo_id())
            root_hwnd = int(user32.GetAncestor(ctypes.c_void_p(hwnd), _GA_ROOT) or hwnd)
            foreground = int(user32.GetForegroundWindow() or 0)
        except (AttributeError, OSError, TypeError, ValueError, tk.TclError):
            return False
        return foreground != 0 and foreground == root_hwnd
'''
new_foreground = '''    def _windows_launcher_is_foreground(self) -> bool:
        user32 = self._windows_user32
        if user32 is None:
            return False
        try:
            window_id = int(self.root.winfo_id())
        except (TypeError, ValueError, tk.TclError):
            return False
        return windows_launcher_is_foreground(user32, window_id)
'''
replace_once(options_path, old_foreground, new_foreground)
old_sample = '''        current_down: set[str] = set()
        for key in self._shortcut_map:
            vk = shortcut_virtual_key(key)
            if vk is None:
                continue
            try:
                if int(user32.GetAsyncKeyState(vk)) & 0x8000:
                    current_down.add(key)
            except (AttributeError, OSError, TypeError, ValueError):
                continue

        active = self._windows_launcher_is_foreground() and self._launcher_shortcuts_active()
        modifiers_down = False
        if active:
            try:
                ctrl_down = bool(int(user32.GetAsyncKeyState(_VK_CONTROL)) & 0x8000)
                alt_down = bool(int(user32.GetAsyncKeyState(_VK_MENU)) & 0x8000)
            except (AttributeError, OSError, TypeError, ValueError):
                ctrl_down = False
                alt_down = False
            modifiers_down = ctrl_down or alt_down
'''
new_sample = '''        sample = sample_windows_shortcut_keys(user32, self._shortcut_map)
        current_down = set(sample.current_down)

        active = self._windows_launcher_is_foreground() and self._launcher_shortcuts_active()
        modifiers_down = windows_shortcut_modifiers_down(user32) if active else False
'''
replace_once(options_path, old_sample, new_sample)


test_path = ROOT / "tests" / "test_launcher_windows_shortcuts.py"
test_path.write_text(
    r'''"""Testy LC-3B: platformowy adapter skrótów Windows."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from giclee_app import launcher_windows_shortcuts as platform
from giclee_app import options_category_launcher as options
from giclee_app.launcher_windows_shortcuts import (
    WindowsShortcutSample,
    load_windows_user32,
    sample_windows_shortcut_keys,
    shortcut_virtual_key,
    windows_launcher_is_foreground,
    windows_shortcut_modifiers_down,
)


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("a", ord("A")),
        (" Z ", ord("Z")),
        ("0", ord("0")),
        ("9", ord("9")),
        ("f1", 0x70),
        ("F12", 0x7B),
        ("f0", None),
        ("f13", None),
        ("ą", None),
        ("ab", None),
        ("", None),
    ],
)
def test_shortcut_virtual_key_mapping(key: str, expected: int | None) -> None:
    assert shortcut_virtual_key(key) == expected


def test_options_module_keeps_virtual_key_compatibility_reexport() -> None:
    assert options.shortcut_virtual_key is platform.shortcut_virtual_key


def test_load_user32_returns_none_outside_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform.os, "name", "posix")
    assert load_windows_user32() is None


class _FakeCall:
    def __init__(self, callback=None) -> None:  # type: ignore[no-untyped-def]
        self.callback = callback or (lambda *_args: 0)
        self.restype = None
        self.argtypes = None
        self.calls: list[tuple[object, ...]] = []

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        return self.callback(*args)


def _fake_user32() -> SimpleNamespace:
    return SimpleNamespace(
        GetForegroundWindow=_FakeCall(),
        GetAncestor=_FakeCall(),
        GetAsyncKeyState=_FakeCall(),
    )


def test_load_user32_configures_ctypes_signatures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user32 = _fake_user32()
    monkeypatch.setattr(platform.os, "name", "nt")
    monkeypatch.setattr(
        platform.ctypes,
        "windll",
        SimpleNamespace(user32=user32),
        raising=False,
    )

    loaded = load_windows_user32()

    assert loaded is user32
    assert user32.GetForegroundWindow.restype is platform.ctypes.c_void_p
    assert user32.GetAncestor.argtypes == (
        platform.ctypes.c_void_p,
        platform.ctypes.c_uint,
    )
    assert user32.GetAncestor.restype is platform.ctypes.c_void_p
    assert user32.GetAsyncKeyState.argtypes == (platform.ctypes.c_int,)
    assert user32.GetAsyncKeyState.restype is platform.ctypes.c_short


def test_load_user32_returns_none_when_backend_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(platform.os, "name", "nt")
    monkeypatch.delattr(platform.ctypes, "windll", raising=False)
    assert load_windows_user32() is None


def test_foreground_uses_root_ancestor_and_zero_is_inactive() -> None:
    user32 = _fake_user32()
    user32.GetAncestor.callback = lambda _hwnd, _kind: 222
    user32.GetForegroundWindow.callback = lambda: 222
    assert windows_launcher_is_foreground(user32, 111) is True

    user32.GetForegroundWindow.callback = lambda: 0
    assert windows_launcher_is_foreground(user32, 111) is False


def test_foreground_falls_back_to_original_hwnd_and_handles_errors() -> None:
    user32 = _fake_user32()
    user32.GetAncestor.callback = lambda _hwnd, _kind: 0
    user32.GetForegroundWindow.callback = lambda: 111
    assert windows_launcher_is_foreground(user32, 111) is True

    user32.GetAncestor.callback = lambda *_args: (_ for _ in ()).throw(OSError("x"))
    assert windows_launcher_is_foreground(user32, 111) is False


def test_sample_keys_normalizes_filters_and_continues_after_error() -> None:
    states = {
        ord("A"): 0x8000,
        ord("B"): 0,
        0x70: 0x8000,
    }

    def get_state(vk: int) -> int:
        if vk == ord("C"):
            raise OSError("bad key")
        return states.get(vk, 0)

    user32 = _fake_user32()
    user32.GetAsyncKeyState.callback = get_state
    keys = [" A ", "b", "F1", "invalid", "c"]
    before = list(keys)

    sample = sample_windows_shortcut_keys(user32, keys)

    assert sample == WindowsShortcutSample(
        current_down=frozenset({"a", "f1"})
    )
    assert keys == before
    with pytest.raises(AttributeError):
        sample.current_down.add("x")  # type: ignore[attr-defined]


def test_modifiers_detect_ctrl_or_alt_and_fail_closed() -> None:
    user32 = _fake_user32()
    states = {0x11: 0x8000, 0x12: 0}
    user32.GetAsyncKeyState.callback = lambda vk: states.get(vk, 0)
    assert windows_shortcut_modifiers_down(user32) is True

    states[0x11] = 0
    states[0x12] = 0x8000
    assert windows_shortcut_modifiers_down(user32) is True

    user32.GetAsyncKeyState.callback = lambda _vk: (_ for _ in ()).throw(OSError("x"))
    assert windows_shortcut_modifiers_down(user32) is False


def test_platform_module_has_no_tk_launcher_studio_or_component_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_windows_shortcuts.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "tkinter" not in imports
    assert "launcher" not in imports
    assert "launcher_studio" not in imports
    assert not any(name.startswith("giclee_app.ui") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)


def test_options_class_delegates_direct_winapi_calls_to_adapter() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "options_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    poll = source.split("def _poll_windows_shortcuts", 1)[1].split("\n    def ", 1)[0]
    foreground = source.split("def _windows_launcher_is_foreground", 1)[1].split(
        "\n    def ", 1
    )[0]

    assert "GetAsyncKeyState" not in source
    assert "GetForegroundWindow" not in source
    assert "GetAncestor" not in source
    assert "ctypes" not in source
    assert "sample_windows_shortcut_keys(" in poll
    assert "windows_shortcut_modifiers_down(" in poll
    assert "resolve_shortcut_poll(" in poll
    assert "self.root.after(" in poll
    assert "windows_launcher_is_foreground(" in foreground
    assert "tk.TclError" in foreground


class _RootRecorder:
    def __init__(self) -> None:
        self.after_calls: list[tuple[int, object]] = []

    def after(self, delay: int, callback: object) -> str:
        self.after_calls.append((delay, callback))
        return "poll-id"

    def winfo_id(self) -> int:
        return 123


def test_options_poll_keeps_timer_and_controller_orchestration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = options.OptionsCategoryGicleeApp.__new__(options.OptionsCategoryGicleeApp)
    app._windows_user32 = object()
    app._shortcut_map = {"i": "integracjagpt"}
    app._windows_shortcut_down = set()
    app._windows_shortcut_poll_id = None
    app.root = _RootRecorder()
    app._windows_launcher_is_foreground = lambda: True
    app._launcher_shortcuts_active = lambda: True
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
        lambda _user32: False,
    )

    app._poll_windows_shortcuts()

    assert app._windows_shortcut_down == {"i"}
    assert triggered == ["i"]
    assert app.root.after_calls == [(35, app._poll_windows_shortcuts)]
    assert app._windows_shortcut_poll_id == "poll-id"


def test_foreground_wrapper_handles_tk_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = options.OptionsCategoryGicleeApp.__new__(options.OptionsCategoryGicleeApp)
    app._windows_user32 = object()
    app.root = SimpleNamespace(
        winfo_id=lambda: (_ for _ in ()).throw(options.tk.TclError("no root"))
    )
    called: list[object] = []
    monkeypatch.setattr(
        options,
        "windows_launcher_is_foreground",
        lambda *_args: called.append(True) or True,
    )

    assert app._windows_launcher_is_foreground() is False
    assert called == []
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**LC-3A shortcut decisions:** `launcher_shortcut_controller.py` rozstrzyga zbocza klawiszy oraz wyniki `unmapped / missing / pending / ready`. WinAPI, bindtagi Tk, fokus, statusy i `after_idle` pozostają w `OptionsCategoryGicleeApp`.\n",
    "**LC-3A shortcut decisions:** `launcher_shortcut_controller.py` rozstrzyga zbocza klawiszy oraz wyniki `unmapped / missing / pending / ready`. WinAPI, bindtagi Tk, fokus, statusy i `after_idle` pozostają w `OptionsCategoryGicleeApp`.\n\n"
    "**LC-3B Windows adapter:** `launcher_windows_shortcuts.py` izoluje virtual-key mapping, user32, foreground i próbki klawiszy/modyfikatorów. `OptionsCategoryGicleeApp` nadal posiada timery, aktywność, Tk fallback oraz LC-3A orchestration.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-lc3b-contract.md"
replace_once(
    contract,
    "**Status:** fresh reconnaissance · contract freeze  ",
    "**Status:** LC-3B implemented",
)
