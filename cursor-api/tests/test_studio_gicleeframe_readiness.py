"""Testy GICLÉE FRAME™ readiness — save_ready zawsze False."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_draft_state import GicleeFrameDraftState
from giclee_app.studio.gicleeframe_dry_run import build_gicleeframe_plan_dry_run
from giclee_app.studio.gicleeframe_page_draft import GicleeFramePageDraft
from giclee_app.studio.gicleeframe_page_dry_run import build_page_structure_dry_run
from giclee_app.studio.gicleeframe_page_inventory import build_gicleeframe_page_inventory
from giclee_app.studio.gicleeframe_readiness import (
    WRITER_STATUS,
    evaluate_gicleeframe_page_readiness,
    evaluate_gicleeframe_readiness,
    format_page_readiness_block,
    format_readiness_block,
    readiness_display_rows,
    readiness_page_display_rows,
)

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"


def test_readiness_empty_draft_not_complete() -> None:
    draft = GicleeFrameDraftState()
    dry_run = build_gicleeframe_plan_dry_run(draft)
    readiness = evaluate_gicleeframe_readiness(draft, dry_run)
    assert readiness.plan_complete is False
    assert readiness.save_ready is False
    assert readiness.writer_status == WRITER_STATUS
    assert readiness.design_brief_ready is True
    assert readiness.app_planning_ready is True


def test_readiness_ok_dry_run_plan_complete_but_save_blocked() -> None:
    draft = GicleeFrameDraftState()
    draft.set_variant("default_dark")
    draft.set_placement("hero")
    dry_run = build_gicleeframe_plan_dry_run(draft)
    readiness = evaluate_gicleeframe_readiness(draft, dry_run)
    assert readiness.plan_complete is True
    assert readiness.save_ready is False
    assert readiness.writer_status == WRITER_STATUS
    assert readiness.shopify_impl_status == "not_started"
    assert readiness.sync_deploy_status == "blocked"


def test_format_readiness_block_mentions_writer_and_shopify() -> None:
    draft = GicleeFrameDraftState()
    draft.set_variant("section_label")
    dry_run = build_gicleeframe_plan_dry_run(draft)
    readiness = evaluate_gicleeframe_readiness(draft, dry_run)
    block = format_readiness_block(readiness)
    assert "Writer" in block
    assert "Shopify" in block
    assert "zablokowane" in block.lower() or "blocked" in block.lower()


def test_readiness_display_rows_has_five_items() -> None:
    rows = readiness_display_rows()
    assert len(rows) == 5
    labels = {r.label for r in rows}
    assert "Design brief" in labels
    assert "Writer/save" in labels


def test_readiness_module_allows_save_ready_field_name() -> None:
    text = (_STUDIO_ROOT / "gicleeframe_readiness.py").read_text(encoding="utf-8")
    assert "save_ready" in text
    assert "write_text" not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_page_readiness_rows_include_writer_blocks() -> None:
    rows = readiness_page_display_rows()
    labels = {r.label for r in rows}
    assert "Shopify writer" in labels
    assert "Save/Zapisz/Zastosuj" in labels


def test_page_readiness_save_blocked_with_inventory() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    dry = build_page_structure_dry_run(inv, GicleeFramePageDraft())
    ready = evaluate_gicleeframe_page_readiness(inv, dry)
    assert ready.save_ready is False
    assert ready.structure_dry_run_ready is True
    block = format_page_readiness_block(ready)
    assert "struktura" in block.lower() or "inventory" in block.lower()
