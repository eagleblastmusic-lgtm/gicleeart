from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
INTERACTION_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_interaction.py"
SELECTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
)


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_gicleeframe_view_has_model_cache_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_merged_by_id" in text
    assert "_section_tree_rows_cache" in text
    assert "_section_dropdown_options_cache" in text
    assert "_section_row_frames" in text
    assert "def _rebuild_page_model_cache" in text


def test_select_element_uses_lookup_cache() -> None:
    text = SELECTION_PATH.read_text(encoding="utf-8")
    block = _method_block(text, "_select_element")

    assert "_merged_by_id.get" in block
    assert "select_element.immediate_ready" in block
    assert "_populate_editor(" not in block
    assert "next((" not in block


def test_select_element_does_not_render_section_list() -> None:
    text = SELECTION_PATH.read_text(encoding="utf-8")
    block = _method_block(text, "_select_element")

    assert "_render_section_list(" not in block
    assert "_render_section_menu(" not in block


def test_highlight_uses_row_frame_lookup() -> None:
    path = INTERACTION_PATH
    text = path.read_text(encoding="utf-8")

    assert "def _set_section_row_highlight" in text
    highlight_block = _method_block(text, "_highlight_section_row")

    assert "_set_section_row_highlight" in highlight_block
    assert "_section_row_frames" in text


def test_refresh_inventory_rebuilds_model_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_refresh_inventory")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block


def test_apply_edit_to_draft_rebuilds_model_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_apply_edit_to_draft")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block


def test_media_section_selection_defers_heavy_details_to_on_demand() -> None:
    import customtkinter as ctk
    from unittest.mock import patch

    from giclee_app.studio.gicleeframe_page_draft import MergedPageElement
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        media = MergedPageElement(
            element_id="media-1",
            section_key="section-media",
            element_type="media_section",
            group="body",
            order=0,
            label="Media",
            title="Media title",
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
        view._merged_by_id = {"media-1": media}

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
            with patch.object(view, "after_idle", side_effect=lambda cb: cb()):
                with patch.object(view, "_update_section_preview") as preview_mock:
                    with patch.object(view, "_fill_children_overview_buttons") as children_mock:
                        with patch.object(view, "_ensure_editor_identity_built"):
                            view._edit_panel = ctk.CTkFrame(view)
                            view._select_element("media-1")

        preview_mock.assert_not_called()
        children_mock.assert_not_called()
        assert any(item[0] == "studio.gicleeframe.details_on_demand.available" for item in logged)
        assert not any(item[0].endswith("preview.update.done") for item in logged)
        assert not any(item[0].endswith("children.update.done") for item in logged)
    finally:
        root.destroy()


def test_minimal_editor_path_logs_ready_without_auto_details() -> None:
    editor_text = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
    ).read_text(encoding="utf-8")
    populate = _method_block(editor_text, "_populate_editor")
    combined = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    ).read_text(encoding="utf-8") + "\n" + editor_text
    assert "studio.gicleeframe.selection.minimal_editor_ready" in combined
    assert "_show_details_on_demand_block" in populate
    assert "_update_section_preview(" not in populate
    assert "_fill_children_overview_buttons(" not in populate
