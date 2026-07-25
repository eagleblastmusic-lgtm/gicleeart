"""Platformowy adapter WinAPI dla skrótów klasycznego launchera."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import ctypes
import os
from typing import Any

from .launcher_shortcut_keys import normalize_shortcut_key, shortcut_virtual_key


_GA_ROOT = 2
_VK_LBUTTON = 0x01
_VK_CONTROL = 0x11
_VK_MENU = 0x12


@dataclass(frozen=True)
class WindowsShortcutSample:
    """Niemutowalna próbka aktualnie wciśniętych skrótów."""

    current_down: frozenset[str]


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
    """Pobiera kanoniczną próbkę wyłącznie dla kluczy aktualnej mapy."""

    current_down: set[str] = set()
    sampled: set[str] = set()
    for raw_key in keys:
        key = normalize_shortcut_key(raw_key)
        if key is None or key in sampled:
            continue
        sampled.add(key)
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


def windows_primary_button_down(user32: Any) -> bool:
    """True gdy wciśnięty jest lewy przycisk myszy (VK_LBUTTON).

    Używane do odciążenia pętli Tk podczas przeciągania okna / gestów LMB.
    """

    try:
        return bool(int(user32.GetAsyncKeyState(_VK_LBUTTON)) & 0x8000)
    except (AttributeError, OSError, TypeError, ValueError):
        return False
