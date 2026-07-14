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


def _editor_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
    ).read_text(encoding="utf-8")


def _top_bar_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view_top_bar.py").read_text(
        encoding="utf-8"
    )


def _section_list_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")


def _rendering_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")


def _combined_text() -> str:
    return _view_text() + "\n" + _section_list_shell_text() + "\n" + _rendering_text()


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


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
    text = _section_list_shell_text()

    start = text.index("studio.gicleeframe.section_list.first_visible_ready")
    end = text.index("self._schedule_atomic_reveal_check", start)
    body = text[start:end]

    assert "self._section_list_first_visible_built = True" in body
    assert "_try_mark_perceived_ready" in body


def test_empty_section_list_marks_first_visible_built() -> None:
    text = _rendering_text()

    start = text.index("def _render_section_list_incremental")
    end = text.index("def _render_section_list_batch", start)
    body = text[start:end]

    assert "if not self._merged:" in body
    assert "self._section_list_first_visible_built = True" in body
    assert "_try_mark_perceived_ready" in body


def test_identity_card_late_defer_follows_prewarm_lane() -> None:
    editor_text = _editor_shell_text()
    prewarm_ms = _constant_int(editor_text, "_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS")
    identity_ms = _constant_int(editor_text, "_GF_EDITOR_IDENTITY_LATE_DEFER_MS")
    top_bar_ms = _constant_int(_top_bar_text(), "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS")

    assert 0 < prewarm_ms < identity_ms <= top_bar_ms


def test_identity_card_late_scheduled_event_exists() -> None:
    text = _editor_shell_text()
    assert "studio.gicleeframe.editor.identity_card_late_scheduled" in text
    assert "delay_ms=_GF_EDITOR_IDENTITY_LATE_DEFER_MS" in text


def test_first_visible_sections_preserves_prior_6g5_optimizations() -> None:
    text = _combined_text() + "\n" + _editor_shell_text()
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in text
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.control.deferred_readiness_late" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text
