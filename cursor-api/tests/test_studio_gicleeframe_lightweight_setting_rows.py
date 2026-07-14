from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
PAGE_CONTEXT_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_page_context.py"
HOST_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"


def test_lightweight_setting_summary_rows_exist() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "_create_page_context_setting_summary_row" in text
    assert "setting_summary_created" in text
    assert "group_summary_batch" in text


def test_setting_editor_is_opened_on_demand() -> None:
    text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "_open_inline_setting_editor" in text
    assert "_close_active_setting_editor" in text
    assert "setting_editor.open" in text
    assert "setting_editor.opened" in text


def test_only_one_active_setting_editor_is_tracked() -> None:
    host_text = HOST_PATH.read_text(encoding="utf-8")
    page_context_text = PAGE_CONTEXT_PATH.read_text(encoding="utf-8")

    assert "_active_setting_editor_row" in host_text
    assert "_active_setting_editor_key" in host_text
    assert "_close_active_setting_editor()" in page_context_text
