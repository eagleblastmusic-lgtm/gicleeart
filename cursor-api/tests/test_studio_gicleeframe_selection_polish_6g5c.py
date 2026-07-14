from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
EDITOR_SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
DETAILS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_details_on_demand.py"


def _view_text() -> str:
    return VIEW_PATH.read_text(encoding="utf-8")


def _editor_shell_text() -> str:
    return EDITOR_SHELL_PATH.read_text(encoding="utf-8")


def _details_text() -> str:
    return DETAILS_PATH.read_text(encoding="utf-8")


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_divider_is_not_deferred_only_for_page_settings() -> None:
    text = _details_text()
    body = _method_block(text, "_should_defer_editor_detail_populate")

    assert "return True" in body
    assert "_populate_editor_preview_deferred" in text
    assert "_populate_editor_layer_nav_deferred" in text
    assert "_populate_editor_children_deferred" in text


def test_media_section_preview_is_deferred() -> None:
    combined = _details_text() + "\n" + _editor_shell_text()

    assert "_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS" in combined
    assert "_populate_editor_preview_deferred" in combined
    assert "studio.gicleeframe.populate_editor.preview_deferred" in combined
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in combined


def test_media_section_children_can_be_delayed_later_than_default() -> None:
    from giclee_app.ui import gicleeframe_view_details_on_demand as details

    text = _details_text()

    assert (
        details._GF_SELECTION_CHILDREN_LATE_DEFER_MS
        > details._GF_SELECTION_CHILDREN_DEFER_MS
    )
    assert "_populate_editor_children_deferred" in text


def test_selection_polish_preserves_lazy_startup_and_late_control() -> None:
    combined = _view_text() + "\n" + _editor_shell_text()

    assert "studio.gicleeframe.editor.fields_lazy_startup" in combined
    assert "studio.gicleeframe.control.deferred_readiness_late" in combined
    assert "studio.gicleeframe.control.deferred_safety_late" in combined
