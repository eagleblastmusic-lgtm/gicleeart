from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_control_readiness_and_safety_are_late_cards() -> None:
    text = _view_text()

    assert "_GF_CONTROL_LATE_BUILD_DEFER_MS" in text
    assert "_schedule_control_late_build" in text
    assert "_build_control_late_cards" in text
    assert "studio.gicleeframe.control.deferred_readiness_late" in text
    assert "studio.gicleeframe.control.deferred_safety_late" in text
    assert "studio.gicleeframe.build.control_column.late_cards" in text


def test_control_structure_marks_shell_ready_before_late_cards() -> None:
    text = _view_text()

    start = text.index("def _micro_deferred_control_structure")
    end = text.index("def _micro_deferred_control_readiness")
    body = text[start:end]

    assert "self._shell_control_built = True" in body
    assert "_try_mark_perceived_ready" in body
    assert "self._schedule_control_late_build()" in body
    assert "_micro_deferred_control_readiness" not in body


def test_late_cards_do_not_break_lazy_editor_fields() -> None:
    text = _view_text()

    assert "studio.gicleeframe.editor.fields_lazy_startup" in text

    form_start = text.index("def _micro_deferred_editor_form_shell")
    form_end = text.index("def _micro_deferred_editor_fields")
    form_body = text[form_start:form_end]

    assert "_micro_deferred_editor_fields" not in form_body
