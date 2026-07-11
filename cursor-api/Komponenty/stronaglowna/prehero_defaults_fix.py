"""Poprawne stosowanie wartości domyślnych ustawień GICLÉE HOME FLOW.

W starszej integracji brakujące klucze były zamieniane na ``None`` przed
normalizacją. Dla pól bool powodowało to wyłączenie pre-Hero mimo domyślnej
wartości ``True``. Ten mały hotfix zachowuje wyłącznie faktycznie zapisane
wartości i pozwala normalizatorowi zastosować prawidłowe domyślne ustawienia.
"""

from __future__ import annotations

from typing import Any

from . import prehero_integration as _base


def install_prehero_defaults_fix() -> None:
    current = _base.load_prehero_values
    if getattr(current, "_giclee_defaults_fixed", False):
        return

    def load_prehero_values_with_defaults(
        settings: dict[str, Any] | None,
    ) -> dict[str, Any]:
        stored = _base._settings_current(settings)
        raw = {
            key: stored[key]
            for key in _base._SETTING_KEYS
            if key in stored and stored[key] is not None
        }
        values = _base.normalize_prehero_values(raw)
        values["_enabled"] = bool(values["prehero_enabled"])
        return values

    setattr(load_prehero_values_with_defaults, "_giclee_defaults_fixed", True)
    setattr(load_prehero_values_with_defaults, "__wrapped__", current)
    _base.load_prehero_values = load_prehero_values_with_defaults
