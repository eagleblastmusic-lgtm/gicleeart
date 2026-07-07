"""6G.5-P.DIAG — sections column shell cost attribution instrumentation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_sections_column_deferred_subspans_exist() -> None:
    body = _method_block(_view_text(), "_build_sections_column_deferred")
    expected = [
        "studio.gicleeframe.build.sections_column.deferred.clear_children",
        "studio.gicleeframe.build.sections_column.deferred.shell_build",
        "studio.gicleeframe.build.sections_column.deferred.card_pack",
    ]
    for event in expected:
        assert event in body


def test_sections_column_deferred_clear_children_diag_fields() -> None:
    body = _method_block(_view_text(), "_build_sections_column_deferred")
    assert "children_count=len(children)" in body
    assert "child_types=" in body
    assert "winfo_children()" in body


def test_sections_column_shell_subspans_exist() -> None:
    text = _view_text()
    shell_body = _method_block(text, "_build_sections_column_shell")
    scroll_body = _method_block(text, "_create_section_list_scroll_frame")
    expected_shell = [
        "studio.gicleeframe.build.sections_column.shell.card",
        "studio.gicleeframe.build.sections_column.shell.extras_slot",
        "studio.gicleeframe.build.sections_column.shell.ready_log",
    ]
    for event in expected_shell:
        assert event in shell_body
    expected_scroll = [
        "studio.gicleeframe.build.sections_column.shell.scroll_create",
        "studio.gicleeframe.build.sections_column.shell.scroll_pack",
    ]
    for event in expected_scroll:
        assert event in scroll_body


def test_sections_column_shell_diag_preserves_prior_6g5_markers() -> None:
    text = _view_text()
    assert "studio.gicleeframe.build.sections_column.deferred.shell" in text
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in text
    assert "studio.gicleeframe.sections_column.early_lane_enter" in text
    assert "studio.gicleeframe.sections_column.extras_skipped_missing_slot" in text
    assert "uses_async_first_paint = True" in text
