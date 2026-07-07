from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_section_list_first_visible_built_flag_exists() -> None:
    text = _view_text()
    assert "_section_list_first_visible_built = False" in text


def test_try_mark_perceived_ready_waits_for_first_visible_sections() -> None:
    text = _view_text()

    start = text.index("def _try_mark_perceived_ready")
    end = text.index("def _build_workspace_critical", start)
    body = text[start:end]

    assert "_section_list_first_visible_built" in body
    assert "first_visible" in body
    assert "missing_gates" in body


def test_first_visible_ready_sets_flag_and_triggers_perceived_ready() -> None:
    text = _view_text()

    start = text.index("studio.gicleeframe.section_list.first_visible_ready")
    end = text.index("if end < len(options):", start)
    body = text[start:end]

    assert "self._section_list_first_visible_built = True" in body
    assert "_try_mark_perceived_ready" in body


def test_empty_section_list_marks_first_visible_built() -> None:
    text = _view_text()

    start = text.index("def _render_section_list_incremental")
    end = text.index("def _render_section_list_batch", start)
    body = text[start:end]

    assert "if not self._merged:" in body
    assert "self._section_list_first_visible_built = True" in body
    assert "_try_mark_perceived_ready" in body


def test_identity_card_late_defer_is_1200_ms() -> None:
    text = _view_text()
    assert "_GF_EDITOR_IDENTITY_LATE_DEFER_MS = 1200" in text


def test_identity_card_late_scheduled_event_exists() -> None:
    text = _view_text()
    assert "studio.gicleeframe.editor.identity_card_late_scheduled" in text
    assert "delay_ms=_GF_EDITOR_IDENTITY_LATE_DEFER_MS" in text


def test_first_visible_sections_preserves_prior_6g5_optimizations() -> None:
    text = _view_text()
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.control.deferred_readiness_late" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text
