"""Testy LC-3B: platformowy adapter skrótów Windows."""

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
    windows_primary_button_down,
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
        ("٧", None),
        ("f١", None),
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
    keys = [" A ", "b", "F1", "invalid", "c", "٧", "f١"]
    before = list(keys)

    sample = sample_windows_shortcut_keys(user32, keys)

    assert sample == WindowsShortcutSample(
        current_down=frozenset({"a", "f1"})
    )
    assert keys == before
    assert [call[0] for call in user32.GetAsyncKeyState.calls] == [
        ord("A"),
        ord("B"),
        0x70,
        ord("C"),
    ]
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


def test_primary_button_detects_lbutton_and_fail_closed() -> None:
    user32 = _fake_user32()
    user32.GetAsyncKeyState.callback = lambda vk: 0x8000 if vk == 0x01 else 0
    assert windows_primary_button_down(user32) is True

    user32.GetAsyncKeyState.callback = lambda _vk: 0
    assert windows_primary_button_down(user32) is False

    user32.GetAsyncKeyState.callback = lambda _vk: (_ for _ in ()).throw(OSError("x"))
    assert windows_primary_button_down(user32) is False


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
    assert "windows_primary_button_down(" in poll
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
        "windows_primary_button_down",
        lambda _user32: False,
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


def test_options_poll_backs_off_while_primary_button_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = options.OptionsCategoryGicleeApp.__new__(options.OptionsCategoryGicleeApp)
    app._windows_user32 = object()
    app._shortcut_map = {"i": "integracjagpt"}
    app._windows_shortcut_down = set()
    app._windows_shortcut_poll_id = None
    app.root = _RootRecorder()
    app._windows_launcher_is_foreground = lambda: (_ for _ in ()).throw(
        AssertionError("foreground must be skipped during pointer drag")
    )
    app._launcher_shortcuts_active = lambda: (_ for _ in ()).throw(
        AssertionError("shortcut activity must be skipped during pointer drag")
    )
    triggered: list[str] = []
    app._trigger_shortcut = lambda key: triggered.append(key) or True

    monkeypatch.setattr(
        options,
        "sample_windows_shortcut_keys",
        lambda _user32, _keys: WindowsShortcutSample(frozenset({"i"})),
    )
    monkeypatch.setattr(
        options,
        "windows_primary_button_down",
        lambda _user32: True,
    )
    monkeypatch.setattr(
        options,
        "windows_shortcut_modifiers_down",
        lambda _user32: (_ for _ in ()).throw(
            AssertionError("modifiers must not be sampled during pointer drag")
        ),
    )

    app._poll_windows_shortcuts()

    assert app._windows_shortcut_down == {"i"}
    assert triggered == []
    assert app.root.after_calls == [(250, app._poll_windows_shortcuts)]
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
