"""6G.5-S.2A — editor rows/form shell prewarm after identity prewarm."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def gicleeframe_view():
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    view = GicleeFrameView(root)
    view.pack()
    yield view
    root.destroy()


def _prepare_form_shell(view) -> None:
    view._shell_editor_built = True
    view._editor_column = ctk.CTkFrame(view)
    view._edit_panel = ctk.CTkFrame(view._editor_column, fg_color="transparent")
    view._editor_form_shell_ready = True


def test_rows_prewarm_builds_row_shells_without_selection(gicleeframe_view) -> None:
    view = gicleeframe_view
    _prepare_form_shell(view)
    view._selected_id = None

    view._run_editor_rows_prewarm()

    assert view._title_row_built
    assert view._text_row_built
    assert view._alt_row_built
    assert view._image_ref_row_built
    assert view._notes_row_built
    assert not view._children_overview_built
    assert not view._page_context_shell_built
    assert view._selected_id is None


def test_rows_prewarm_does_not_change_selected_id(gicleeframe_view) -> None:
    view = gicleeframe_view
    _prepare_form_shell(view)
    view._selected_id = "elem-keep"

    view._run_editor_rows_prewarm()

    assert view._selected_id == "elem-keep"


def test_rows_prewarm_does_not_trigger_preview_or_page_context(gicleeframe_view) -> None:
    view = gicleeframe_view
    _prepare_form_shell(view)

    with patch.object(view, "_populate_editor") as populate_mock:
        with patch.object(view, "_fill_page_context") as page_context_mock:
            with patch.object(view, "_update_section_preview") as preview_mock:
                with patch.object(view, "_ensure_children_overview_built") as children_mock:
                    with patch.object(
                        view, "_ensure_page_context_shell_built"
                    ) as page_shell_mock:
                        view._run_editor_rows_prewarm()

    populate_mock.assert_not_called()
    page_context_mock.assert_not_called()
    preview_mock.assert_not_called()
    children_mock.assert_not_called()
    page_shell_mock.assert_not_called()


def test_rows_prewarm_skips_when_row_shells_already_built(gicleeframe_view) -> None:
    view = gicleeframe_view
    _prepare_form_shell(view)
    view._title_row_built = True
    view._text_row_built = True
    view._alt_row_built = True
    view._image_ref_row_built = True
    view._notes_row_built = True
    logged: list[tuple[str, dict]] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    with patch("giclee_app.ui.gicleeframe_view_editor_shell.log_event", side_effect=_capture):
        with patch.object(view, "_ensure_title_row_built") as title_mock:
            with patch.object(view, "_ensure_notes_row_built") as notes_mock:
                view._run_editor_rows_prewarm()

    title_mock.assert_not_called()
    notes_mock.assert_not_called()
    skipped = [
        item
        for item in logged
        if item[0] == "studio.gicleeframe.editor.rows_prewarm_skipped"
    ]
    assert len(skipped) == 1
    assert skipped[0][1]["already_built"] is True
    assert skipped[0][1]["reason"] == "already_built"


def test_identity_prewarm_schedules_rows_prewarm(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._shell_editor_built = True
    view._editor_identity_late_build_done = False

    with patch.object(view, "_ensure_editor_identity_built"):
        with patch.object(view, "_schedule_editor_rows_prewarm") as schedule_mock:
            view._run_editor_identity_prewarm()

    schedule_mock.assert_called_once()
