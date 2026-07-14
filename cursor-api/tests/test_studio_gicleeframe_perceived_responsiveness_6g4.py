from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _section_list_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")


def _rendering_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")


def _combined_text() -> str:
    return _view_text() + "\n" + _section_list_shell_text() + "\n" + _rendering_text()


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


def test_gicleeframe_uses_stable_workspace_skeleton_columns() -> None:
    text = _view_text()

    assert "_GF_SKELETON_SECTION_TEXT" in text
    assert "_GF_SKELETON_EDITOR_TEXT" in text
    assert "_GF_SKELETON_CONTROL_TEXT" in text
    assert "workspace.skeleton_columns_ready" in text
    assert "_build_workspace_skeleton_column" in text
    assert "_clear_column_children" in text


def test_gicleeframe_tracks_atomic_reveal_gates() -> None:
    text = _view_text()

    assert "_try_atomic_reveal" in text
    assert "_atomic_reveal_missing_gates" in text
    assert "studio.gicleeframe.atomic_reveal.revealed" in text
    assert "_shell_sections_built" in text
    assert "_shell_editor_built" in text
    assert "_shell_control_built" in text


def test_gicleeframe_defers_heavy_editor_details_to_on_demand() -> None:
    text = _view_text()

    assert "_should_defer_editor_detail_populate" in text
    assert "studio.gicleeframe.populate_editor.details_deferred" in text
    assert "_apply_heavy_details_on_demand" in text
    assert "studio.gicleeframe.details_on_demand.requested" in text
    assert "_selection_generation" in text
    assert ".stale" in text


def test_gicleeframe_sections_deferred_packs_card_into_skeleton_column() -> None:
    text = _view_text()

    assert "card.pack(fill=\"both\", expand=True)" in text
    assert "_workspace_skeleton_columns_built" in text


def test_gicleeframe_section_list_has_progressive_first_batch() -> None:
    text = _rendering_text()
    first_batch = _constant_int(_section_list_shell_text(), "_GF_SECTION_FIRST_BATCH_SIZE")
    steady_batch = _constant_int(text, "_GF_SECTION_BATCH_SIZE")

    assert 1 <= first_batch <= steady_batch
    assert "batch_size = _GF_SECTION_FIRST_BATCH_SIZE if start == 0 else _GF_SECTION_BATCH_SIZE" in text
    assert "batch_size=batch_size" in text
