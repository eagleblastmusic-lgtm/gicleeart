"""Testy GICLÉE FRAME™ dry-run — pure, bez zapisu."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_brief import VARIANTS
from giclee_app.studio.gicleeframe_draft_state import GicleeFrameDraftState
from giclee_app.studio.gicleeframe_dry_run import (
    DRY_RUN_BADGE,
    build_gicleeframe_plan_dry_run,
    format_dry_run_summary,
)


def test_dry_run_empty_not_ok() -> None:
    draft = GicleeFrameDraftState()
    dry_run = build_gicleeframe_plan_dry_run(draft)
    assert dry_run.ok is False
    assert dry_run.errors
    assert dry_run.status_badge == DRY_RUN_BADGE


def test_dry_run_ok_for_each_variant() -> None:
    for variant in VARIANTS:
        draft = GicleeFrameDraftState()
        draft.set_variant(variant.variant_id)
        dry_run = build_gicleeframe_plan_dry_run(draft)
        assert dry_run.ok is True, variant.variant_id
        assert variant.label_pl in dry_run.variants_available
        assert "giclee-frame-mark" in dry_run.theme_snippet_hint


def test_dry_run_with_placement() -> None:
    draft = GicleeFrameDraftState()
    draft.set_variant("hero_label")
    draft.set_placement("product_page")
    dry_run = build_gicleeframe_plan_dry_run(draft)
    assert dry_run.ok is True
    assert "product_page" in dry_run.theme_snippet_hint or "product_page" in dry_run.placement_rationale


def test_format_dry_run_summary_polish() -> None:
    draft = GicleeFrameDraftState()
    draft.set_variant("compact")
    dry_run = build_gicleeframe_plan_dry_run(draft)
    summary = format_dry_run_summary(dry_run)
    assert "Przyszły output Shopify" in summary
    assert "Czego unikać" in summary
    assert "nie zapisano" in summary.lower() or DRY_RUN_BADGE in summary
