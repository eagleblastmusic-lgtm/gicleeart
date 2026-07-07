from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_gicleeframe_view_has_model_cache_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_merged_by_id" in text
    assert "_section_tree_rows_cache" in text
    assert "_section_dropdown_options_cache" in text
    assert "_section_row_frames" in text
    assert "def _rebuild_page_model_cache" in text


def test_select_element_uses_lookup_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_select_element")

    assert "_merged_by_id.get" in block
    assert "select_element.immediate_ready" in block
    assert "_populate_editor(" not in block
    assert "next((" not in block


def test_select_element_does_not_render_section_list() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_select_element")

    assert "_render_section_list(" not in block
    assert "_render_section_menu(" not in block


def test_highlight_uses_row_frame_lookup() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _set_section_row_highlight" in text
    highlight_block = _method_block(text, "_highlight_section_row")

    assert "_set_section_row_highlight" in highlight_block
    assert "_section_row_frames" in text


def test_refresh_inventory_rebuilds_model_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_refresh_inventory")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block


def test_apply_edit_to_draft_rebuilds_model_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_apply_edit_to_draft")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block
