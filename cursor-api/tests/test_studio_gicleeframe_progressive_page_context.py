from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PAGE_CONTEXT_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_page_context.py"
HOST_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"


def test_progressive_page_context_flags_exist() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "GICLEE_GF_PROGRESSIVE_PAGE_CONTEXT" in text
    assert "def _progressive_page_context_enabled" in text
    assert "_GF_PAGE_CONTEXT_BATCH_SIZE" in text
    assert "_GF_PAGE_CONTEXT_DEFER_MS" in text


def test_page_context_is_deferred_from_populate_editor() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "studio.gicleeframe.page_context.deferred" in text
    assert "_populate_page_context_progressive" in text
    assert "_show_page_context_loading_state" in text


def test_page_context_has_batch_logging_and_stale_guard() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "studio.gicleeframe.page_context.batch" in text
    assert "page_context.progressive_done" in text
    assert "deferred_stale" in text or "batch_stale" in text


def test_page_context_jobs_are_cancelled_on_selection_change() -> None:
    page_context_text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    host_text = HOST_PATH.read_text(encoding="utf-8")

    assert "_cancel_page_context_jobs" in page_context_text
    assert "after_cancel" in page_context_text
    assert "_cancel_page_context_jobs" in host_text
