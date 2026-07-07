from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def test_divider_is_not_deferred_only_for_page_settings() -> None:
    text = _view_text()

    assert "Same page_settings dla dividera" in text
    assert 'm.element_type == "media_section"' in text
    assert 'getattr(fields, "children", False)' in text

    start = text.index("def _should_defer_editor_detail_populate")
    end = text.index("def _merged_for_selection_generation")
    body = text[start:end]

    assert "bool(m.page_settings)" not in body


def test_media_section_preview_is_deferred() -> None:
    text = _view_text()

    assert "_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS" in text
    assert "_populate_editor_preview_deferred" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred" in text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in text


def test_media_section_children_can_be_delayed_later_than_default() -> None:
    text = _view_text()

    assert "_GF_SELECTION_CHILDREN_LATE_DEFER_MS" in text
    assert "_GF_SELECTION_CHILDREN_DEFER_MS" in text
    assert "children_delay" in text
    assert 'if etype == "media_section"' in text


def test_selection_polish_preserves_lazy_startup_and_late_control() -> None:
    text = _view_text()

    assert "studio.gicleeframe.editor.fields_lazy_startup" in text
    assert "studio.gicleeframe.control.deferred_readiness_late" in text
    assert "studio.gicleeframe.control.deferred_safety_late" in text
