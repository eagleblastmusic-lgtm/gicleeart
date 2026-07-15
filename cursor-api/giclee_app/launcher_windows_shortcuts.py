"""Platformowy adapter WinAPI dla skrótów klasycznego launchera."""

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
    """Zwraca kod WinAPI dla ASCII A-Z, 0-9 albo F1-F12."""

    normalized = str(key or "").strip().lower()
    if len(normalized) == 1 and normalized.isalpha() and normalized.isascii():
        return ord(normalized.upper())
    if len(normalized) == 1 and normalized.isdigit() and normalized.isascii():
        return ord(normalized)
    suffix = normalized[1:]
    if normalized.startswith("f") and suffix.isdigit() and suffix.isascii():
        number = int(suffix)
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
