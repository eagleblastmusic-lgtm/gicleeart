from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]

INTERACTION_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_interaction.py"
SELECTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
)
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"


def test_section_row_click_does_not_collapse_by_default() -> None:
    path = INTERACTION_PATH
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK" in text
    assert "def _collapse_section_list_on_click_enabled" in text
    assert "_on_section_row_click" in text
    assert "collapse_list=_collapse_section_list_on_click_enabled()" in text


def test_select_element_has_immediate_and_deferred_pipeline() -> None:
    selection_text = SELECTION_PATH.read_text(encoding="utf-8")

    assert "_selection_generation" in selection_text
    assert "_cancel_selection_jobs" in selection_text
    assert "_populate_editor_deferred" in selection_text
    assert "select_element.immediate_ready" in selection_text
    assert "populate_editor.deferred" in selection_text


def test_page_context_waits_for_stable_selection() -> None:
    text = VIEW_PATH.read_text(encoding="utf-8")

    assert "_GF_PAGE_CONTEXT_STABLE_DEFER_MS" in text
    assert "_populate_page_context_progressive_stable" in text
    assert "stable_defer_stale" in text


def test_section_dropdown_reuses_rows() -> None:
    path = INTERACTION_PATH
    text = path.read_text(encoding="utf-8")

    assert "_ensure_section_dropdown_rows" in text
    assert "section_dropdown.rows_reused" in text
