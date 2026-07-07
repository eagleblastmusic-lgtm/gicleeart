"""6G.5-S.1 — selection stability during init_refresh.light + editor identity prewarm."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


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


@pytest.fixture(scope="module")
def gicleeframe_view():
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    view = GicleeFrameView(root)
    view.pack()
    yield view
    root.destroy()


def _patch_inventory_refresh(view) -> None:
    view._inventory = MagicMock()
    view._page_draft = MagicMock()
    view._page_draft.is_empty.return_value = True
    view._on_status = None


def test_refresh_inventory_light_preserves_active_selected_id(gicleeframe_view) -> None:
    view = gicleeframe_view
    element = _sample_merged("elem-keep")
    view._selected_id = "elem-keep"
    view._selection_generation = 3
    view._shell_editor_built = True
    _patch_inventory_refresh(view)

    with patch(
        "giclee_app.ui.gicleeframe_view.build_gicleeframe_page_inventory",
        return_value=MagicMock(),
    ):
        with patch(
            "giclee_app.ui.gicleeframe_view.merge_inventory_with_draft",
            return_value=[element],
        ):
            with patch.object(view, "_update_top_bar"):
                with patch.object(view, "_highlight_section_row"):
                    with patch.object(view, "_show_editor_selection_pending_state"):
                        with patch.object(
                            view,
                            "_ensure_preserved_selection_populate_after_inventory_light",
                        ):
                            view._refresh_inventory_light()

    assert view._selected_id == "elem-keep"


def test_refresh_inventory_light_clears_selected_id_when_missing_after_merge(
    gicleeframe_view,
) -> None:
    view = gicleeframe_view
    view._selected_id = "elem-gone"
    view._selection_generation = 2
    _patch_inventory_refresh(view)

    with patch(
        "giclee_app.ui.gicleeframe_view.build_gicleeframe_page_inventory",
        return_value=MagicMock(),
    ):
        with patch(
            "giclee_app.ui.gicleeframe_view.merge_inventory_with_draft",
            return_value=[],
        ):
            with patch.object(view, "_update_top_bar"):
                with patch.object(view, "_show_editor_placeholder_state"):
                    view._refresh_inventory_light()

    assert view._selected_id is None


def test_refresh_inventory_light_logs_preserved_event(gicleeframe_view) -> None:
    view = gicleeframe_view
    element = _sample_merged("elem-preserved")
    view._selected_id = "elem-preserved"
    view._selection_generation = 4
    view._shell_editor_built = False
    _patch_inventory_refresh(view)
    logged: list[tuple[str, dict]] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
        with patch(
            "giclee_app.ui.gicleeframe_view.build_gicleeframe_page_inventory",
            return_value=MagicMock(),
        ):
            with patch(
                "giclee_app.ui.gicleeframe_view.merge_inventory_with_draft",
                return_value=[element],
            ):
                with patch.object(view, "_update_top_bar"):
                    view._refresh_inventory_light()

    preserved = [
        item
        for item in logged
        if item[0] == "studio.gicleeframe.selection.preserved_after_inventory_light"
    ]
    assert len(preserved) == 1
    payload = preserved[0][1]
    assert payload["element_id"] == "elem-preserved"
    assert payload["generation"] == 4
    assert payload["reason"] == "merged_exists"
    assert payload["merged_exists"] is True
    assert payload["shell_editor_built"] is False


def test_refresh_inventory_light_logs_cleared_event(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._selected_id = "elem-missing"
    view._selection_generation = 5
    view._shell_editor_built = True
    _patch_inventory_refresh(view)
    logged: list[tuple[str, dict]] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
        with patch(
            "giclee_app.ui.gicleeframe_view.build_gicleeframe_page_inventory",
            return_value=MagicMock(),
        ):
            with patch(
                "giclee_app.ui.gicleeframe_view.merge_inventory_with_draft",
                return_value=[],
            ):
                with patch.object(view, "_update_top_bar"):
                    with patch.object(view, "_show_editor_placeholder_state"):
                        view._refresh_inventory_light()

    cleared = [
        item
        for item in logged
        if item[0] == "studio.gicleeframe.selection.cleared_after_inventory_light"
    ]
    assert len(cleared) == 1
    payload = cleared[0][1]
    assert payload["element_id"] == "elem-missing"
    assert payload["generation"] == 5
    assert payload["reason"] == "missing_after_merge"
    assert payload["merged_exists"] is False
    assert payload["shell_editor_built"] is True


def test_identity_prewarm_builds_only_identity_shell(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._shell_editor_built = True
    view._editor_identity_late_build_done = False

    with patch.object(view, "_ensure_editor_identity_built") as ensure_mock:
        with patch.object(view, "_populate_editor") as populate_mock:
            with patch.object(view, "_fill_page_context") as page_context_mock:
                with patch.object(view, "_update_section_preview") as preview_mock:
                    view._run_editor_identity_prewarm()

    ensure_mock.assert_called_once()
    populate_mock.assert_not_called()
    page_context_mock.assert_not_called()
    preview_mock.assert_not_called()


def test_identity_prewarm_skips_when_identity_already_built(gicleeframe_view) -> None:
    view = gicleeframe_view
    view._shell_editor_built = True
    view._editor_identity_late_build_done = True
    logged: list[tuple[str, dict]] = []

    def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
        logged.append((event, kwargs))

    with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
        with patch.object(view, "_ensure_editor_identity_built") as ensure_mock:
            view._run_editor_identity_prewarm()

    ensure_mock.assert_not_called()
    skipped = [
        item
        for item in logged
        if item[0] == "studio.gicleeframe.editor.identity_prewarm_skipped"
    ]
    assert len(skipped) == 1
    assert skipped[0][1]["already_built"] is True
    assert skipped[0][1]["reason"] == "already_built"
