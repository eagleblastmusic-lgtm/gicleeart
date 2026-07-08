from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}(\n"
    if marker not in text:
        marker = f"def {name}("
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_layer_nav_has_reuse_cache_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_layer_nav_tile_cache" in text
    assert "_layer_nav_title_widgets" in text
    assert "_layer_nav_visible_keys" in text


def test_layer_nav_has_reuse_helpers() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _hide_layer_nav_tiles" in text
    assert "def _show_layer_nav_tile" in text
    assert "def _get_or_create_layer_nav_tile" in text
    assert "def _update_layer_nav_tile" in text


def test_update_layer_nav_uses_reuse_event() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav")

    assert "layer_nav.reuse" in block
    assert "_sync_layer_nav_visibility" in block
    assert "_update_layer_nav_tile" in block


def test_update_layer_nav_does_not_destroy_children_on_normal_path() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav")

    if ".destroy()" in block:
        assert "layer_nav.destroy_fallback" in block


def test_layer_nav_callbacks_rebind_current_target() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav_tile")

    assert "element_id" in block
    assert "_select_element" in block
