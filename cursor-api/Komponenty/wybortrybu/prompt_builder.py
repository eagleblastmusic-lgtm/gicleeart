"""Budowanie krótkich i pełnych promptów aktywacyjnych."""

from __future__ import annotations

from .data_loader import Combination, WorkMode


def short_mode_label(mode: WorkMode) -> str:
    return mode.short_label


def short_command_for_mode(mode: WorkMode) -> str:
    return f"TRYB {short_mode_label(mode)}"


def short_prompt_for_modes(modes: list[WorkMode]) -> str:
    if not modes:
        return ""
    labels = [short_mode_label(m) for m in modes]
    return "TRYB " + " + ".join(labels)


def full_prompt_for_modes(modes: list[WorkMode]) -> str:
    if not modes:
        return ""
    labels = [short_mode_label(m) for m in modes]
    lines = [
        "Pracuj w trybie:",
        " + ".join(labels) + ".",
        "",
        "Zasady:",
    ]
    for idx, mode in enumerate(modes, start=1):
        lines.append(f"- {short_mode_label(mode)}: {mode.purpose}")
    lines.extend(["", "Przykładowe komendy:"])
    for idx, mode in enumerate(modes, start=1):
        lines.append(f"{idx}) {mode.sample_command}")
    return "\n".join(lines)


def prompt_for_combination(combo: Combination, modes: list[WorkMode]) -> str:
    if combo.prompt_full:
        return combo.prompt_full
    return full_prompt_for_modes(modes)


def short_prompt_for_combination(combo: Combination, modes: list[WorkMode]) -> str:
    if combo.prompt_short:
        return combo.prompt_short
    return short_prompt_for_modes(modes)
