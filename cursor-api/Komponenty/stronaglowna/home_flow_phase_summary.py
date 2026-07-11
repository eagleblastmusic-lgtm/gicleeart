"""Czytelne podsumowania ustawień faz bezpośrednio w drzewie HOME FLOW."""

from __future__ import annotations

from pathlib import PurePosixPath

from . import home_flow_gui as base_gui
from .home_flow import HomeFlowItem
from .home_flow_phase_settings import (
    CURTAIN_ID,
    HERO_HOLD_ID,
    HERO_RISE_ID,
    INTRO_HOLD_ID,
    PORTAL_ID,
    SOUND_ID,
    effective_phase_config,
)
from .homepage_variants import active_variant_id


def _screens_label(value: int) -> str:
    value = int(value)
    if value == 1:
        return "1 ekran"
    if 2 <= value <= 4:
        return f"{value} ekrany"
    return f"{value} ekranów"


def _audio_name(url: str) -> str:
    clean = str(url or "").split("?", 1)[0].rstrip("/")
    if not clean:
        return "brak pliku"
    return PurePosixPath(clean).name or "plik audio"


def phase_summary(stable_id: str) -> str:
    cfg = effective_phase_config(active_variant_id(), stable_id)
    if stable_id == PORTAL_ID:
        state = "tekst włączony" if cfg.get("enabled") else "tekst wyłączony"
        return f"{_screens_label(cfg.get('screens', 2))} · {state}"
    if stable_id == HERO_RISE_ID:
        return _screens_label(cfg.get("screens", 1))
    if stable_id == HERO_HOLD_ID:
        if not cfg.get("enabled"):
            return "wyłączona · 0vh"
        return _screens_label(cfg.get("screens", 1))
    if stable_id == SOUND_ID:
        if not cfg.get("enabled"):
            return "wyłączona"
        return f"aktywna · {_audio_name(str(cfg.get('audio_url') or ''))}"
    if stable_id == CURTAIN_ID:
        if not cfg.get("enabled"):
            return "wyłączona"
        return _screens_label(cfg.get("screens", 1))
    if stable_id == INTRO_HOLD_ID:
        if not cfg.get("enabled"):
            return "wyłączona · 0vh"
        return _screens_label(cfg.get("screens", 1))
    return ""


def install_home_flow_phase_summaries() -> None:
    current = base_gui._insert_flow_rows
    if getattr(current, "_giclee_phase_summaries", False):
        return

    def insert_with_summaries(tree, items: tuple[HomeFlowItem, ...]) -> None:
        current(tree, items)
        for item in items:
            if item.kind != "phase" or not tree.exists(item.stable_id):
                continue
            summary = phase_summary(item.stable_id)
            suffix = f"  ·  {summary}" if summary else ""
            tree.item(
                item.stable_id,
                text=f"↳ {item.code}  {item.display_name}{suffix}",
            )

    setattr(insert_with_summaries, "_giclee_phase_summaries", True)
    setattr(insert_with_summaries, "__wrapped__", current)
    base_gui._insert_flow_rows = insert_with_summaries
