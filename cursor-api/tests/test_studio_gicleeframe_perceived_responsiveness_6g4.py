from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_gicleeframe_uses_stable_workspace_skeleton_columns() -> None:
    text = _view_text()

    assert "_GF_SKELETON_SECTION_TEXT" in text
    assert "_GF_SKELETON_EDITOR_TEXT" in text
    assert "_GF_SKELETON_CONTROL_TEXT" in text
    assert "workspace.skeleton_columns_ready" in text
    assert "_build_workspace_skeleton_column" in text
    assert "_clear_column_children" in text


def test_gicleeframe_tracks_perceived_ready_after_deferred_shell_parts() -> None:
    text = _view_text()

    assert "_try_mark_perceived_ready" in text
    assert "studio.gicleeframe.visual.perceived_ready" in text
    assert "_shell_sections_built" in text
    assert "_shell_editor_built" in text
    assert "_shell_control_built" in text


def test_gicleeframe_defers_heavy_media_section_editor_details() -> None:
    text = _view_text()

    assert "_should_defer_editor_detail_populate" in text
    assert "studio.gicleeframe.populate_editor.details_deferred" in text
    assert "_populate_editor_layer_nav_deferred" in text
    assert "_populate_editor_children_deferred" in text
    assert "studio.gicleeframe.populate_editor.layer_nav_deferred" in text
    assert "studio.gicleeframe.populate_editor.children_deferred" in text
    assert "_selection_generation" in text
    assert ".stale" in text


def test_gicleeframe_sections_deferred_packs_card_into_skeleton_column() -> None:
    text = _view_text()

    assert "card.pack(fill=\"both\", expand=True)" in text
    assert "_workspace_skeleton_columns_built" in text


def test_gicleeframe_section_list_has_smaller_first_batch() -> None:
    text = _view_text()

    assert "_GF_SECTION_FIRST_BATCH_SIZE = 2" in text
    assert "batch_size = _GF_SECTION_FIRST_BATCH_SIZE if start == 0 else _GF_SECTION_BATCH_SIZE" in text
    assert "batch_size=batch_size" in text
