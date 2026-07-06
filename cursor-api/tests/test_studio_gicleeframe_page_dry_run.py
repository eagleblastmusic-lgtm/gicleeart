"""Testy GICLÉE FRAME™ F2 structure dry-run."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_page_draft import GicleeFramePageDraft
from giclee_app.studio.gicleeframe_page_dry_run import (
    STRUCTURE_DRY_RUN_BADGE,
    build_page_structure_dry_run,
    format_structure_dry_run_summary,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    build_gicleeframe_page_inventory,
    inventory_count_stats,
)
from giclee_app.studio.gicleeframe_readiness import (
    evaluate_gicleeframe_page_readiness,
    format_page_readiness_block,
)


def test_structure_dry_run_ok_with_real_inventory() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    dry = build_page_structure_dry_run(inv, draft)
    stats = inventory_count_stats(inv)
    assert dry.ok is True
    assert dry.source_section_count == stats["source_sections"]
    assert dry.elements_total == stats["elements_total"]
    assert dry.elements_total > dry.source_section_count
    assert dry.status_badge == STRUCTURE_DRY_RUN_BADGE


def test_structure_dry_run_tracks_ram_edits() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    eid = inv.elements[0].element_id
    draft.set_patch(eid, text="zmiana RAM")
    dry = build_page_structure_dry_run(inv, draft)
    assert eid in dry.draft_edited_ids


def test_page_readiness_save_always_blocked() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    dry = build_page_structure_dry_run(inv, GicleeFramePageDraft())
    ready = evaluate_gicleeframe_page_readiness(inv, dry)
    assert ready.page_inventory_ready is True
    assert ready.save_ready is False
    block = format_page_readiness_block(ready)
    assert "blocked" in block.lower() or "zablokowane" in block.lower()


def test_format_structure_summary_polish() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    dry = build_page_structure_dry_run(inv, GicleeFramePageDraft())
    summary = format_structure_dry_run_summary(dry)
    assert "order[]" in summary
    assert "rozwinięte" in summary.lower() or "inventory" in summary.lower()
    assert "Guardrails" in summary
