from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_preview_has_reuse_cache_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_preview_frame_cache" in text
    assert "_preview_value_widgets" in text
    assert "_preview_active_key" in text


def test_preview_has_reuse_helpers() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _hide_preview_frames" in text
    assert "def _show_preview_frame" in text
    assert "def _get_or_create_preview_frame" in text
    assert "def _preview_key_for_element" in text


def test_update_section_preview_uses_reuse_event() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_section_preview(self, m:")

    assert "preview.reuse" in block
    assert "_hide_preview_frames" in block
    assert "_show_preview_frame" in block


def test_update_section_preview_does_not_destroy_children_on_normal_path() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_section_preview(self, m:")

    if ".destroy()" in block:
        assert "preview.destroy_fallback" in block


def test_preview_key_is_type_based_not_element_id_based() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_preview_key_for_element")

    assert "element_type" in block
    assert "element_id" not in block
