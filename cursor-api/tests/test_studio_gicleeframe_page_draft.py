"""Testy GICLÉE FRAME™ F2 RAM page draft — merge z inventory."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_page_draft import (
    DRAFT_RAM_DISCLAIMER,
    GicleeFramePageDraft,
    merge_inventory_with_draft,
)
from giclee_app.studio.gicleeframe_page_inventory import build_gicleeframe_page_inventory


def test_draft_empty_merge_matches_inventory() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    merged = merge_inventory_with_draft(inv, draft)
    assert len(merged) == len(inv.elements)
    assert not any(m.has_draft_patch for m in merged)


def test_draft_patch_marks_element_edited() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    target = inv.elements[0]
    draft = GicleeFramePageDraft()
    draft.set_patch(target.element_id, title="RAM tytuł", status="draft_edited")
    merged = merge_inventory_with_draft(inv, draft)
    patched = next(m for m in merged if m.element_id == target.element_id)
    assert patched.title == "RAM tytuł"
    assert patched.has_draft_patch is True
    assert patched.source == "ram_draft"


def test_draft_clear_resets_patches() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("x::y", notes="test")
    assert not draft.is_empty()
    draft.clear()
    assert draft.is_empty()


def test_draft_disclaimer_copy() -> None:
    assert "lokalnym draftem" in DRAFT_RAM_DISCLAIMER.lower()
    assert "nic nie zapisano" in DRAFT_RAM_DISCLAIMER.lower()
