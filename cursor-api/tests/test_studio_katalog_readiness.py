"""Testy Katalog readiness (F4) — save_ready zawsze False."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_draft_state import KatalogDraftState
from giclee_app.studio.katalog_dry_run import KatalogPlanDryRun
from giclee_app.studio.katalog_readiness import (
    WRITER_STATUS,
    evaluate_katalog_plan_readiness,
    format_readiness_block,
)

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"


def _assert_no_writes_in_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "shutil" not in text
    assert "requests" not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_readiness_empty_draft_not_complete() -> None:
    draft = KatalogDraftState()
    dry_run = KatalogPlanDryRun(
        ok=False,
        errors=("x",),
        operation_summary="",
        target_owner="",
        fields_touched=(),
        blocked_paths=(),
    )
    readiness = evaluate_katalog_plan_readiness(draft, dry_run)
    assert readiness.plan_complete is False
    assert readiness.save_ready is False
    assert readiness.writer_status == WRITER_STATUS


def test_readiness_ok_dry_run_plan_complete_but_save_blocked() -> None:
    draft = KatalogDraftState()
    draft.set_intent("review_structure")
    dry_run = KatalogPlanDryRun(
        ok=True,
        errors=(),
        operation_summary="legacy katalog",
        target_owner="legacy",
        fields_touched=("manifest",),
        blocked_paths=("Shopify",),
    )
    readiness = evaluate_katalog_plan_readiness(draft, dry_run)
    assert readiness.plan_complete is True
    assert readiness.save_ready is False
    assert readiness.writer_status == WRITER_STATUS
    assert "not started" in readiness.block_reason


def test_readiness_failed_dry_run_not_complete() -> None:
    draft = KatalogDraftState()
    draft.set_intent("plan_collection_layout")
    dry_run = KatalogPlanDryRun(
        ok=False,
        errors=("brak wariantu",),
        operation_summary="blocked",
        target_owner="legacy",
        fields_touched=(),
        blocked_paths=(),
    )
    readiness = evaluate_katalog_plan_readiness(draft, dry_run)
    assert readiness.plan_complete is False
    assert readiness.save_ready is False


def test_format_readiness_block_mentions_writer_and_shopify() -> None:
    draft = KatalogDraftState()
    draft.set_intent("review_structure")
    dry_run = KatalogPlanDryRun(
        ok=True,
        errors=(),
        operation_summary="x",
        target_owner="legacy",
        fields_touched=(),
        blocked_paths=(),
    )
    readiness = evaluate_katalog_plan_readiness(draft, dry_run)
    block = format_readiness_block(readiness)
    assert "writer: not_started" in block or "Writer: not_started" in block
    assert "Shopify" in block
    assert "local planning only" in block


def test_readiness_module_allows_save_ready_field_name() -> None:
    """Techniczne pole save_ready jest OK — test UI sprawdza copy osobno."""
    text = (_STUDIO_ROOT / "katalog_readiness.py").read_text(encoding="utf-8")
    assert "save_ready" in text
    _assert_no_writes_in_source(_STUDIO_ROOT / "katalog_readiness.py")
