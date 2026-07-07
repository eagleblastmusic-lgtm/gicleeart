from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_startup_hotspot_context_bar_spans_exist() -> None:
    text = _view_text()
    assert "studio.gicleeframe.build.context_bar." in text
    assert "studio.gicleeframe.build.context_bar.frame" in text
    assert "studio.gicleeframe.build.context_bar.title" in text
    assert "studio.gicleeframe.build.context_bar.status" in text
    assert "studio.gicleeframe.build.context_bar.actions" in text


def test_startup_hotspot_command_bar_spans_exist() -> None:
    text = _view_text()
    assert "studio.gicleeframe.build.command_bar." in text
    assert "studio.gicleeframe.build.command_bar.frame" in text
    assert "studio.gicleeframe.build.command_bar.primary_actions" in text
    assert "studio.gicleeframe.build.command_bar.secondary_actions" in text


def test_startup_hotspot_editor_skeleton_spans_exist() -> None:
    text = _view_text()
    assert "studio.gicleeframe.build.editor_column.skeleton.ensure_column" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.identity_card" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.legacy_message" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.placeholder_state" in text


def test_startup_hotspot_section_list_first_visible_ready_marker() -> None:
    text = _view_text()
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "since_enter_ms=self._since_visual_enter_ms()" in text


def test_startup_hotspot_preserves_prior_6g5_optimizations() -> None:
    text = _view_text()
    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.control.deferred_readiness_late" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text
