from __future__ import annotations

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


def test_startup_hotspot_context_bar_spans_exist() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.build.context_bar." in text
    assert "studio.gicleeframe.build.context_bar.frame" in text
    assert "studio.gicleeframe.build.context_bar.title" in text
    assert "studio.gicleeframe.build.context_bar.status" in text
    assert "studio.gicleeframe.build.context_bar.actions" in text


def test_startup_hotspot_command_bar_spans_exist() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.build.command_bar." in text
    assert "studio.gicleeframe.build.command_bar.frame" in text
    assert "studio.gicleeframe.build.command_bar.primary_actions" in text
    assert "studio.gicleeframe.build.command_bar.secondary_actions" in text


def test_startup_hotspot_editor_skeleton_spans_exist() -> None:
    text = _editor_shell_text()
    assert "studio.gicleeframe.build.editor_column.skeleton.ensure_column" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.identity_card" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.legacy_message" in text
    assert "studio.gicleeframe.build.editor_column.skeleton.placeholder_state" in text


def _rendering_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")


def _section_list_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")


def _combined_text() -> str:
    return _view_text() + "\n" + _section_list_shell_text() + "\n" + _rendering_text()


def test_startup_hotspot_section_list_first_visible_ready_marker() -> None:
    text = _combined_text()
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "since_enter_ms=self._since_visual_enter_ms()" in text


def test_startup_hotspot_preserves_prior_6g5_optimizations() -> None:
    combined = _view_text() + "\n" + _editor_shell_text()
    assert "studio.gicleeframe.editor.fields_lazy_startup" in combined
    assert "studio.gicleeframe.control.deferred_readiness_late" in combined
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in combined
