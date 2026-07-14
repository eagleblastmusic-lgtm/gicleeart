from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
HOST_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
INTERACTION_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_interaction.py"
SELECTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
)


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_gicleeframe_view_has_model_cache_fields() -> None:
    host_text = HOST_PATH.read_text(encoding="utf-8")
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")

    assert "_merged_by_id" in host_text
    assert "_section_tree_rows_cache" in host_text
    assert "_section_dropdown_options_cache" in host_text
    assert "_section_row_frames" in host_text
    assert "def _rebuild_page_model_cache" in lifecycle_text


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
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    block = _method_block(lifecycle_text, "_refresh_inventory")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block


def test_apply_edit_to_draft_rebuilds_model_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_apply_edit_to_draft")

    assert "_set_merged" in block or "_rebuild_page_model_cache" in block


def _load_test_module(filename: str):
    import importlib.util

    path = ROOT / "tests" / filename
    module_name = filename.removesuffix(".py").replace("-", "_")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_media_section_selection_defers_heavy_details_to_on_demand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from giclee_app.ui import gicleeframe_view_selection_orchestration as selection_module

    selection_test = _load_test_module("test_studio_gicleeframe_view_selection_orchestration.py")
    editor_shell_test = _load_test_module("test_studio_gicleeframe_view_editor_shell.py")
    _SelectionOrchestrationHarness = selection_test._SelectionOrchestrationHarness
    _sample_merged = selection_test._sample_merged
    GicleeFrameEditorShellHarness = editor_shell_test.GicleeFrameEditorShellHarness
    _FakePackable = editor_shell_test._FakePackable
    _editor_sample_merged = editor_shell_test._sample_merged

    harness = _SelectionOrchestrationHarness()
    media = _sample_merged(
        "media-1",
        element_type="media_section",
        section_key="section-media",
    )
    harness._merged_by_id = {"media-1": media}
    harness._minimal_cache_entry_result = None

    selection_events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: selection_events.append((event, kwargs)),
    )

    harness._select_element("media-1")

    assert harness._selected_id == "media-1"
    assert harness._populate_editor_calls == []
    assert len(harness._after_idle_calls) == 1
    assert any(
        item[0] == "studio.gicleeframe.selection.populate_priority_scheduled"
        and item[1].get("atomic_swap") is True
        for item in selection_events
    )
    assert any(
        item[0] == "studio.gicleeframe.selection.populate_scheduled"
        for item in selection_events
    )
    assert not any(item[0].endswith("preview.update.done") for item in selection_events)
    assert not any(item[0].endswith("children.update.done") for item in selection_events)

    harness._after_idle_calls[0]()

    assert len(harness._populate_editor_calls) == 1
    assert harness._populate_editor_calls[0]["element"] is media
    assert harness._populate_editor_calls[0]["atomic_swap"] is True

    editor_harness = GicleeFrameEditorShellHarness()
    editor_harness._edit_panel = _FakePackable()
    editor_harness._selection_generation = harness._selection_generation
    media_element = _editor_sample_merged(
        "media-1",
        element_type="media_section",
        section_key="section-media",
    )
    details_calls: list[Any] = []
    editor_events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: editor_events.append(event),
    )
    monkeypatch.setattr(editor_harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(
        editor_harness,
        "_ensure_minimal_editor_rows_for_fields",
        lambda _fields: None,
    )
    monkeypatch.setattr(editor_harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(editor_harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(
        editor_harness,
        "_show_details_on_demand_block",
        lambda m: details_calls.append(m),
    )
    monkeypatch.setattr(editor_harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(
        editor_harness,
        "_mark_editor_shell_ready_after_click",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        editor_harness,
        "_mark_editor_stable_shell_ready",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(editor_harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(editor_harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(editor_harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    monkeypatch.setattr(editor_harness, "_save_section_visual_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(editor_harness, "_selected_section_label", lambda: "Media")
    monkeypatch.setattr(editor_harness, "_since_selection_click_ms", lambda: None)

    editor_harness._populate_editor(media_element)

    assert details_calls == [media_element]
    assert "studio.gicleeframe.populate_editor.details_deferred" in editor_events
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in editor_events
    assert not any(event.endswith("preview.update.done") for event in editor_events)
    assert not any(event.endswith("children.update.done") for event in editor_events)


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
