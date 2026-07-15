"""Testy kanonicznej próbki skrótów WinAPI."""

from __future__ import annotations

from types import SimpleNamespace

from giclee_app.launcher_windows_shortcuts import (
    WindowsShortcutSample,
    sample_windows_shortcut_keys,
)


class _KeyStateCall:
    def __init__(self, states: dict[int, int]) -> None:
        self.states = states
        self.calls: list[int] = []

    def __call__(self, virtual_key: int) -> int:
        self.calls.append(virtual_key)
        return self.states.get(virtual_key, 0)


def test_sample_canonicalizes_and_deduplicates_aliases() -> None:
    key_state = _KeyStateCall({0x71: 0x8000, ord("A"): 0x8000})
    user32 = SimpleNamespace(GetAsyncKeyState=key_state)
    keys = [" F02 ", "f2", "A", "a", "ą", "f١"]
    before = list(keys)

    sample = sample_windows_shortcut_keys(user32, keys)

    assert sample == WindowsShortcutSample(frozenset({"f2", "a"}))
    assert key_state.calls == [0x71, ord("A")]
    assert keys == before


def test_sample_keeps_first_seen_order_while_ignoring_invalid_keys() -> None:
    key_state = _KeyStateCall({ord("B"): 0x8000, 0x70: 0x8000})
    user32 = SimpleNamespace(GetAsyncKeyState=key_state)

    sample = sample_windows_shortcut_keys(
        user32,
        ["invalid", "B", "f01", " b ", "F1"],
    )

    assert sample.current_down == frozenset({"b", "f1"})
    assert key_state.calls == [ord("B"), 0x70]
