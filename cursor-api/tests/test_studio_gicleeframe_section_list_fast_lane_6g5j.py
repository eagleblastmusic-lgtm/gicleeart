from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_section_first_visible_defer_ms_constant_exists() -> None:
    text = _view_text()
    assert "_GF_SECTION_FIRST_VISIBLE_DEFER_MS = 0" in text


def test_section_list_first_visible_fast_lane_event_exists() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.first_visible_fast_lane" in text
    assert "delay_ms=effective_delay" in text
    assert "row_count=len(self._section_dropdown_options_cache)" in text
    assert "first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE" in text


def test_section_list_incremental_scheduled_uses_fast_lane_defer() -> None:
    text = _view_text()

    start = text.index("def _schedule_section_list_incremental")
    end = text.index("def _build_context_bar", start)
    body = text[start:end]

    assert "studio.gicleeframe.section_list.incremental_scheduled" in body
    assert "_GF_SECTION_FIRST_VISIBLE_DEFER_MS" in body
    assert "delay_ms=effective_delay" in body
    assert "first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE" in body


def test_section_list_fast_lane_preserves_prior_6g5_markers() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in text
    assert "studio.gicleeframe.section_list.incremental_enter" in text
    assert "studio.gicleeframe.section_list.first_batch_start" in text
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "studio.gicleeframe.visual.perceived_ready" in text
    assert "studio.gicleeframe.top_bar.actions_late_scheduled" in text
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text


def test_section_list_fast_lane_preserves_late_defer_constants() -> None:
    text = _view_text()
    assert "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS = 1600" in text
    assert "_GF_EDITOR_IDENTITY_LATE_DEFER_MS = 1200" in text


def test_section_list_subsequent_batches_still_use_batch_delay() -> None:
    text = _view_text()

    start = text.index("def _schedule_section_list_batch_continuation")
    end = text.index("def _end_selection_priority_window", start)
    body = text[start:end]

    assert "_GF_SECTION_BATCH_DELAY_MS" in body
    assert "_render_section_list_batch(options, end)" in body

    batch_start = text.index("def _render_section_list_batch")
    batch_end = text.index("def _create_section_list_row", batch_start)
    batch_body = text[batch_start:batch_end]

    assert "_GF_SECTION_FIRST_BATCH_SIZE" in batch_body
    assert "_GF_SECTION_BATCH_SIZE" in batch_body
    assert "_schedule_section_list_batch_continuation(options, end)" in batch_body
