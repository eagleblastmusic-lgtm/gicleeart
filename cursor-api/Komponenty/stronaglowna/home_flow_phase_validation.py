"""Walidacja zależności pomiędzy fazami GICLÉE HOME FLOW."""

from __future__ import annotations

from typing import Any

from . import home_flow_phase_settings as phase_settings


def install_home_flow_phase_validation() -> None:
    current = phase_settings.set_phase_config
    if getattr(current, "_giclee_phase_validated", False):
        return

    def set_phase_config_validated(
        variant_id: str,
        stable_id: str,
        values: dict[str, Any],
    ):
        if stable_id == phase_settings.SOUND_ID and bool(values.get("enabled", True)):
            hold = phase_settings.effective_phase_config(
                variant_id, phase_settings.HERO_HOLD_ID
            )
            if not hold.get("enabled") or int(hold.get("screens") or 0) <= 0:
                raise ValueError(
                    "Pytanie o dźwięk wymaga aktywnego postoju Hero. "
                    "Najpierw włącz fazę «Postój Hero» i ustaw co najmniej 1 ekran."
                )

        if stable_id == phase_settings.HERO_HOLD_ID:
            enabled = bool(values.get("enabled", True))
            screens = int(values.get("screens") or 0)
            sound = phase_settings.effective_phase_config(
                variant_id, phase_settings.SOUND_ID
            )
            if (not enabled or screens <= 0) and sound.get("enabled"):
                raise ValueError(
                    "Nie można wyłączyć postoju Hero, gdy aktywna jest faza "
                    "«Decyzja o dźwięku». Najpierw wyłącz pytanie o dźwięk."
                )

        return current(variant_id, stable_id, values)

    setattr(set_phase_config_validated, "_giclee_phase_validated", True)
    setattr(set_phase_config_validated, "__wrapped__", current)
    phase_settings.set_phase_config = set_phase_config_validated
