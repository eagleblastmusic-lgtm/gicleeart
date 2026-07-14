from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PAGE_CONTEXT_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_page_context.py"


def test_divider_page_context_uses_lazy_groups() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "_DIVIDER_LAZY_GROUPS" in text
    assert "collapsed_group" in text
    assert "group_placeholder_created" in text


def test_divider_group_expansion_is_lazy() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "_expand_page_context_group" in text
    assert "group_expanded" in text
    assert "group_summary_batch" in text or "group_setting_batch" in text


def test_divider_group_batches_are_cancellable() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "group_batch_stale" in text or "group_expand_stale" in text
    assert "_schedule_page_context_job" in text
