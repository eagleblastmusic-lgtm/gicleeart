"""Regresja priorytetu roadmapy aktywnych starterów v40."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_DIR = REPO_ROOT / "Pliki startowe dla GPT"


def _read(name: str) -> str:
    return (STARTER_DIR / name).read_text(encoding="utf-8")


def test_v40_active_docs_restore_refactor_roadmap_priority() -> None:
    current = _read("CURRENT_APP_STATE.md")
    roadmap = _read("GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md")
    readme = _read("README_GICLEE_CURSOR_ARCHITECT_UPDATE_v40.md")
    start_message = _read("Wiadomość początkowa.txt")

    active_docs = "\n".join((current, roadmap, readme))
    assert "Bartosz OS / AgentRuntime / Antigravity SDK discovery** — NEXT PRIMARY" not in active_docs
    assert "NEXT PRIMARY (po ukończeniu Start Files v40):** Bartosz OS" not in active_docs
    assert "next: Bartosz OS discovery" not in active_docs

    assert (
        "NEXT PRIMARY po domknięciu Start Files v40:** ETAP 4B — Launcher Composition"
        in current
    )
    assert "ETAP 4B — Launcher Composition** — **NEXT PRIMARY" in roadmap
    assert roadmap.index("ETAP 4B — Launcher Composition") < roadmap.index(
        "ETAP 5 — Shopify theme modularization"
    )
    assert "next: dalszy refaktor zgodnie z roadmapą" in readme

    assert "Bartosz OS" not in start_message
    assert "NEXT PRIMARY" not in start_message.upper()
    assert "generowany automatycznie" not in start_message
    assert "po użyciu odpowiedniej akcji" in start_message
    assert "CURRENT_APP_STATE.md" in start_message
    assert "GICLEE_PROJECT_REFACTOR_ROADMAP_v2.md" in start_message
    assert "GitHub connectora" in start_message
