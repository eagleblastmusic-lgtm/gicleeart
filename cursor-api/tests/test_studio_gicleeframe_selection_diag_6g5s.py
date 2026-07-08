"""6G.5-S.DIAG — selection click interaction latency instrumentation."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _sample_merged(element_id: str, element_type: str = "media_section"):
    from giclee_app.studio.gicleeframe_page_draft import MergedPageElement

    return MergedPageElement(
        element_id=element_id,
        section_key=f"section-{element_id}",
        element_type=element_type,
        group="body",
        order=0,
        label=f"Label {element_id}",
        title=f"Title {element_id}",
        text="",
        image_ref="",
        alt="",
        notes="",
        editable=True,
        source="inventory",
        status="ok",
        has_draft_patch=False,
        visible=True,
    )


def test_selection_diag_click_events_exist() -> None:
    text = _view_text()
    click_body = _method_block(text, "_on_section_row_click")
    assert "studio.gicleeframe.selection.click" in click_body
    for field in (
        "element_id",
        "source",
        "static_lane",
        "scroll_ready",
        "selection_generation_next",
    ):
        assert field in click_body


def test_selection_diag_pipeline_events_exist() -> None:
    text = _view_text()
    for event in (
        "studio.gicleeframe.selection.start",
        "studio.gicleeframe.selection.jobs_cancelled",
        "studio.gicleeframe.selection.immediate_highlight_done",
        "studio.gicleeframe.selection.pending_state_done",
        "studio.gicleeframe.selection.priority_start",
        "studio.gicleeframe.selection.priority_end",
        "studio.gicleeframe.selection.populate_scheduled",
        "studio.gicleeframe.selection.populate_priority_scheduled",
        "studio.gicleeframe.selection.populate_enter",
        "studio.gicleeframe.selection.populate_done",
        "studio.gicleeframe.background.deferred_for_selection",
    ):
        assert event in text


def test_selection_diag_editor_segment_events_exist() -> None:
    text = _view_text()
    marker = "def _populate_editor("
    assert marker in text
    populate_body = text.split(marker, 1)[1].split("\n    def ", 1)[0]
    for segment in (
        "studio.gicleeframe.selection.editor.ensure_identity",
        "studio.gicleeframe.selection.editor.ensure_rows",
        "studio.gicleeframe.selection.editor.preview",
        "studio.gicleeframe.selection.editor.rows_visibility",
        "studio.gicleeframe.selection.editor.fields",
        "studio.gicleeframe.selection.editor.layer_nav",
        "studio.gicleeframe.selection.editor.children",
        "studio.gicleeframe.selection.editor.page_context_schedule_or_fill",
    ):
        assert segment in populate_body


def test_selection_diag_atomic_swap_events_exist() -> None:
    text = _view_text()
    for event in (
        "studio.gicleeframe.selection.atomic_swap.scheduled",
        "studio.gicleeframe.selection.atomic_swap.ready",
        "studio.gicleeframe.selection.atomic_swap.applied",
        "studio.gicleeframe.selection.cache_hit_skip_visible_refresh",
        "studio.gicleeframe.selection.cache_hit_partial",
    ):
        assert event in text


def test_selection_diag_page_context_events_exist() -> None:
    text = _view_text()
    for event in (
        "studio.gicleeframe.selection.page_context.loading_state",
        "studio.gicleeframe.selection.page_context.populate_enter",
        "studio.gicleeframe.selection.page_context.populate_done",
        "studio.gicleeframe.selection.page_context.stale",
    ):
        assert event in text


def test_selection_diag_events_include_generation() -> None:
    text = _view_text()
    for method in (
        "_select_element",
        "_populate_editor_deferred",
        "_populate_editor",
        "_populate_page_context_progressive_stable",
    ):
        body = _method_block(text, method)
        assert "generation" in body


def test_stale_deferred_populate_does_not_update_ui() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        first = _sample_merged("elem-a")
        second = _sample_merged("elem-b", element_type="divider")
        view._merged_by_id = {"elem-a": first, "elem-b": second}
        view._selected_id = "elem-b"
        view._selection_generation = 2

        subtitle_before = (
            view._editor_section_subtitle.cget("text")
            if view._editor_section_subtitle is not None
            else ""
        )

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
            with patch.object(view, "_populate_editor") as populate_mock:
                view._populate_editor_deferred("elem-a", generation=1)

        populate_mock.assert_not_called()
        assert not any(
            item[0] == "studio.gicleeframe.selection.populate_done" for item in logged
        )
        if view._editor_section_subtitle is not None:
            assert view._editor_section_subtitle.cget("text") == subtitle_before
    finally:
        root.destroy()


def test_populate_done_logs_only_for_current_generation() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        element = _sample_merged("elem-current")
        view._merged_by_id = {"elem-current": element}
        view._selected_id = "elem-current"
        view._selection_generation = 5

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
            with patch.object(view, "_populate_editor"):
                view._populate_editor_deferred("elem-current", generation=5)
                view._selection_generation = 6
                view._populate_editor_deferred("elem-current", generation=5)

        done_events = [
            item for item in logged if item[0] == "studio.gicleeframe.selection.populate_done"
        ]
        assert len(done_events) == 1
        assert done_events[0][1]["generation"] == 5
    finally:
        root.destroy()


def test_selection_diag_preserves_prior_6g5_markers() -> None:
    text = _view_text()
    for marker in (
        "studio.gicleeframe.section_list.static_lane_ready",
        "studio.gicleeframe.section_list.first_visible_ready",
        "studio.gicleeframe.visual.perceived_ready",
        "studio.gicleeframe.section_list.scroll_upgrade_scheduled",
        "studio.gicleeframe.sections_column.early_lane_scheduled",
        "studio.gicleeframe.visual.perceived_ready_gate_check",
        "select_element.immediate_ready",
        "populate_editor.deferred_stale",
    ):
        assert marker in text
