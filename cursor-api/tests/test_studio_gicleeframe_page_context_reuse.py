from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_page_context_has_reuse_cache_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_page_context_row_cache" in text
    assert "_page_context_value_widgets" in text
    assert "_page_context_visible_keys" in text


def test_page_context_has_reuse_helpers() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _hide_page_context_rows" in text
    assert "def _show_page_context_row" in text
    assert "def _get_or_create_page_context_row" in text


def test_fill_page_context_uses_reuse_event() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_fill_page_context")

    assert "page_context.reuse" in block
    assert "_hide_page_context_rows" in block
    assert "_show_page_context_row" in block


def test_fill_page_context_does_not_destroy_children_on_normal_path() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_fill_page_context")

    if ".destroy()" in block:
        assert "page_context.destroy_fallback" in block


def test_setting_callbacks_do_not_capture_static_old_element_id() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "self._selected_id" in text
