from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _combined_text() -> str:
    top_bar = (ROOT / "giclee_app" / "ui" / "gicleeframe_view_top_bar.py").read_text(
        encoding="utf-8"
    )
    return _view_text() + "\n" + top_bar


def test_section_list_incremental_scheduled_event_exists() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.incremental_scheduled" in text
    assert "delay_ms=effective_delay" in text
    assert "row_count=len(self._section_dropdown_options_cache)" in text
    assert "first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE" in text


def test_section_list_incremental_enter_event_exists() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.incremental_enter" in text

    start = text.index("def _render_section_list_incremental")
    end = text.index("if self._section_list_scroll is None:", start)
    body = text[start:end]

    assert "since_enter_ms=self._since_visual_enter_ms()" in body
    assert "row_count=len(self._section_dropdown_options_cache)" in body


def test_section_list_first_batch_start_event_exists() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.first_batch_start" in text


def test_section_list_first_batch_spans_exist() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.first_batch.prepare" in text
    assert "studio.gicleeframe.section_list.first_batch.rows" in text
    assert "studio.gicleeframe.section_list.first_batch.pack_or_layout" in text


def test_section_list_column_ready_for_rows_event_exists() -> None:
    text = _view_text()

    start = text.index("def _log_section_list_column_ready")
    end = text.index("def _build_sections_column_shell", start)
    body = text[start:end]

    assert "studio.gicleeframe.section_list.column_ready_for_rows" in body
    assert "since_enter_ms=self._since_visual_enter_ms()" in body


def test_section_list_diagnostics_preserves_prior_6g5_markers() -> None:
    text = _combined_text()
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "studio.gicleeframe.visual.perceived_ready" in text
    assert "studio.gicleeframe.top_bar.actions_late_scheduled" in text
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text


def test_schedule_section_list_incremental_helper_exists() -> None:
    text = _view_text()
    assert "def _schedule_section_list_incremental" in text
    assert "self._schedule_section_list_incremental()" in text
