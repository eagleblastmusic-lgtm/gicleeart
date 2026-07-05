"""Testy deklaratywnej mapy background capabilities (F4.1)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_capabilities import (
    capability_for,
    folders_with_background,
)


def test_capability_for_tldobio() -> None:
    cap = capability_for("tldobio")
    assert cap is not None
    assert cap.tier == "bio_workflow"
    assert cap.label
    assert cap.inline_note


def test_capability_for_stronaglowna() -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    assert cap.tier == "section_background"
    assert cap.label


def test_capability_for_katalog_is_none() -> None:
    assert capability_for("katalog") is None


def test_folders_with_background_exact_set() -> None:
    assert folders_with_background() == frozenset({"tldobio", "stronaglowna"})


def test_tier_display_labels() -> None:
    from giclee_app.studio.background_capabilities import tier_display

    assert "Tier 1" in tier_display("bio_workflow")
    assert "Tier 2" in tier_display("section_background")

