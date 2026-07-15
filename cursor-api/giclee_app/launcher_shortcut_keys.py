"""Czysty kontrakt klawiszy skrótów launchera."""

from __future__ import annotations


_MIN_FUNCTION_KEY = 1
_MAX_FUNCTION_KEY = 12
_FUNCTION_KEY_VK_BASE = 0x70


def normalize_shortcut_key(value: object) -> str | None:
    """Zwraca kanoniczny klawisz: ASCII A-Z, 0-9 albo F1-F12."""

    raw = str(value or "").strip().lower()
    if len(raw) == 1 and raw.isascii() and raw.isalnum():
        return raw

    suffix = raw[1:]
    if raw.startswith("f") and suffix.isascii() and suffix.isdigit():
        number = int(suffix)
        if _MIN_FUNCTION_KEY <= number <= _MAX_FUNCTION_KEY:
            return f"f{number}"
    return None


def shortcut_virtual_key(value: object) -> int | None:
    """Zwraca kod WinAPI dla obsługiwanego klawisza bez zależności od WinAPI."""

    normalized = normalize_shortcut_key(value)
    if normalized is None:
        return None
    if len(normalized) == 1:
        return ord(normalized.upper())
    return _FUNCTION_KEY_VK_BASE + int(normalized[1:]) - 1


__all__ = ["normalize_shortcut_key", "shortcut_virtual_key"]
