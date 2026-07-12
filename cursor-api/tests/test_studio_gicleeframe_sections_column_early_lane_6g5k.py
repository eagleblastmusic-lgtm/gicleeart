from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


def test_sections_column_early_defer_ms_constant_exists() -> None:
    text = _view_text()
    assert "_GF_SECTIONS_COLUMN_EARLY_DEFER_MS = 0" in text


def test_sections_column_early_lane_scheduled_event_exists() -> None:
    text = _view_text()

    start = text.index("def _schedule_sections_column_early_lane")
    end = text.index("def _build_sections_column_deferred", start)
    body = text[start:end]

    assert "studio.gicleeframe.sections_column.early_lane_scheduled" in body
    assert "delay_ms=_GF_SECTIONS_COLUMN_EARLY_DEFER_MS" in body
    assert "row_count=len(self._section_dropdown_options_cache)" in body
    assert "first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE" in body


def test_sections_column_early_lane_scheduled_after_workspace_critical() -> None:
    text = _view_text()

    start = text.index("def _build_page_editor_section_critical")
    end = text.index("def _build_workspace_skeleton_column", start)
    body = text[start:end]

    assert "_schedule_sections_column_early_lane()" in body
    assert "studio.gicleeframe.build.workspace.critical" in body


def test_sections_column_early_lane_not_scheduled_from_build_shell_critical_ready() -> None:
    text = _view_text()

    start = text.index("studio.gicleeframe.shell.critical_ready")
    end = text.index("self.after(_GF_SHELL_EDITOR_DEFER_MS", start)
    body = text[start:end]

    assert "_schedule_sections_column_early_lane()" not in body


def test_sections_column_early_lane_helper_uses_early_defer() -> None:
    text = _view_text()

    start = text.index("def _schedule_sections_column_early_lane")
    end = text.index("def _build_sections_column_deferred", start)
    body = text[start:end]

    assert "_GF_SECTIONS_COLUMN_EARLY_DEFER_MS" in body
    assert "self.after(" in body
    assert "self._build_sections_column_deferred" in body
    assert "_sections_column_early_lane_scheduled" in body


def test_sections_column_early_lane_preserves_section_list_markers() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.column_shell_ready" in text
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in text
    assert "studio.gicleeframe.sections_column.early_lane_enter" in text
    assert "studio.gicleeframe.section_list.first_visible_fast_lane" in text
    assert "studio.gicleeframe.section_list.incremental_scheduled" in text
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "studio.gicleeframe.visual.perceived_ready" in text


def test_sections_column_early_lane_shell_before_extras() -> None:
    text = _view_text()

    start = text.index("def _build_sections_column_deferred")
    end = text.index("def _build_editor_column_deferred", start)
    body = text[start:end]

    assert "_build_sections_column_shell" in body
    assert "_flush_pending_section_list_if_needed()" in body
    assert "_build_sections_column_extras_deferred" in body
    assert body.index("_flush_pending_section_list_if_needed()") < body.index(
        "_build_sections_column_extras_deferred"
    )


def test_sections_column_early_lane_preserves_fast_lane_constants() -> None:
    text = _view_text()
    assert "_GF_SECTION_FIRST_VISIBLE_DEFER_MS" in text
    assert "_GF_SECTION_FIRST_BATCH_SIZE" in text


def test_sections_column_early_lane_preserves_late_lane_ordering() -> None:
    text = _view_text()
    identity_ms = _constant_int(text, "_GF_EDITOR_IDENTITY_LATE_DEFER_MS")
    top_bar_ms = _constant_int(text, "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS")

    assert 0 < identity_ms <= top_bar_ms


def test_sections_column_early_lane_preserves_late_startup_markers() -> None:
    text = _view_text()
    assert "studio.gicleeframe.top_bar.actions_late_scheduled" in text
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text
