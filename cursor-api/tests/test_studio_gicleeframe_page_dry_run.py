"""Testy GICLÉE FRAME™ F2/F2.1 structure dry-run."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_page_draft import (
    DEFAULT_VARIANT_NAME,
    GicleeFramePageDraft,
    VARIANT_COMPARE_NOTE,
)
from giclee_app.studio.gicleeframe_page_dry_run import (
    F3_LOCAL_DRAFT_NOTE,
    F4_BOUNDED_WRITER_NOTE,
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
    assert dry.variant_id == inv.variant_id
    assert dry.draft_name == DEFAULT_VARIANT_NAME
    assert dry.draft_edit_count == 0


def test_structure_dry_run_tracks_ram_edits() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    eid = inv.elements[0].element_id
    draft.set_patch(eid, text="zmiana RAM")
    dry = build_page_structure_dry_run(inv, draft)
    assert eid in dry.draft_edited_ids
    assert dry.draft_edit_count == 1
    assert len(dry.draft_field_changes) == 1
    _eid, fields = dry.draft_field_changes[0]
    assert _eid == eid
    assert "tekst" in fields


def test_dry_run_summary_shows_draft_and_nothing_saved() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    draft.rename_active_variant("Test wariant")
    dry = build_page_structure_dry_run(inv, draft)
    summary = format_structure_dry_run_summary(dry)
    assert "Test wariant" in summary
    assert "Wariant roboczy RAM" in summary
    assert "Wariant źródłowy" in summary
    assert "nic nie zapisano" in summary.lower()
    assert VARIANT_COMPARE_NOTE in summary
    assert F3_LOCAL_DRAFT_NOTE in summary
    assert "F4:" in summary or F4_BOUNDED_WRITER_NOTE.split(":")[0] in summary


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
