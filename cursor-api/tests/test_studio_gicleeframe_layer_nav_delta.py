from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_layer_nav_has_delta_state() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_layer_nav_rendered_signatures" in text
    assert "_layer_nav_bound_targets" in text
    assert "_layer_nav_visible_order" in text


def test_layer_nav_has_signature_and_visibility_sync_helpers() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "def _layer_nav_tile_signature" in text
    assert "def _sync_layer_nav_visibility" in text


def test_update_layer_nav_tile_can_skip_unchanged_tile() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav_tile")

    assert "_layer_nav_rendered_signatures" in block
    assert "tile_skipped" in block
    assert "tile_updated" in block


def test_update_layer_nav_uses_delta_not_global_hide() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav(self, m:")

    assert "_sync_layer_nav_visibility" in block
    assert "layer_nav.delta" in block
    assert "_hide_layer_nav_tiles()" not in block


def test_layer_nav_rebinds_only_when_target_changes() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_update_layer_nav_tile")

    assert "_layer_nav_bound_targets" in block
    assert "previous_target" in block
    assert "_select_element" in block
