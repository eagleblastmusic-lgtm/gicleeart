"""Exact-head evidence tests for GF-M17 page-context extraction.

This suite supplements the primary boundary suite with paths that must prove
control-flow and telemetry, not merely event-name presence.
"""

from __future__ import annotations

import ast
import sys
import tkinter as tk
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(TESTS_DIR))

from giclee_app.ui import gicleeframe_view_page_context as page_context_module
from giclee_app.ui.gicleeframe_view_models import PageContextRowSpec
from test_studio_gicleeframe_view_page_context import (
    GicleeFramePageContextHarness,
    VIEW_PATH,
    _FakeButton,
    _FakeEntry,
    _FakeFrame,
    _divider_merged,
    _event_payloads,
    _patch_fake_ctk,
    _sample_merged,
    _setting_field,
)


def _capture_events(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        page_context_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    return events


def _run_fake_after_jobs(harness: GicleeFramePageContextHarness) -> None:
    while harness._after_job_map:
        jobs = list(harness._after_job_map.values())
        harness._after_job_map.clear()
        for _delay, callback in jobs:
            callback()


def test_shell_ready_exact_payload_and_summary_row_reuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    harness._selected_id = "m1"
    events = _capture_events(monkeypatch)

    first = _sample_merged("m1", element_type="media_section", status="warn")
    harness._show_page_context_shell_state(first)
    status_row = harness._page_context_row_cache["shell_summary:Status"]

    payloads = _event_payloads(events, "studio.gicleeframe.page_context.shell_ready")
    assert payloads == [
        {
            "element_id": "m1",
            "element_type": "media_section",
            "generation": 1,
            "since_click_ms": 5.0,
        }
    ]

    events.clear()
    second = _sample_merged("m1", element_type="media_section", status="ok")
    harness._show_page_context_shell_state(second)
    assert harness._page_context_row_cache["shell_summary:Status"] is status_row
    assert harness._page_context_value_widgets["shell_summary:Status"]._text == "ok"
    assert len(_event_payloads(events, "studio.gicleeframe.page_context.shell_ready")) == 1


def test_host_initializes_complete_page_context_contract_state() -> None:
    tree = ast.parse(VIEW_PATH.read_text(encoding="utf-8"))
    view_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GicleeFrameView"
    )
    init = next(
        node
        for node in view_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )

    initialized: set[str] = set()
    for node in ast.walk(init):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets.append(node.target)
        for target in targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                initialized.add(target.attr)

    expected = {
        "_page_context_frame",
        "_page_context_inner",
        "_page_setting_widgets",
        "_page_context_row_cache",
        "_page_context_value_widgets",
        "_page_context_visible_keys",
        "_page_context_row_managers",
        "_page_context_settings_layout",
        "_page_context_last_signature",
        "_page_context_readonly_body",
        "_page_context_divider_group_bodies",
        "_page_context_divider_group_grid_opts",
        "_page_context_setting_card_bodies",
        "_page_context_after_ids",
        "_page_context_generation",
        "_page_context_loading_label",
        "_page_context_shell_shown_generation",
        "_page_context_specs_cache",
        "_page_context_collapsed_group_rows",
        "_page_context_collapsed_group_bodies",
        "_page_context_collapsed_group_buttons",
        "_page_context_expanded_group_ids",
        "_active_setting_editor_row",
        "_active_setting_editor_key",
        "_page_context_summary_rows",
        "_page_context_summary_value_labels",
        "_selected_id",
        "_selection_generation",
        "_selection_visual_cache_applied",
        "_atomic_swap_suppress_visible",
        "_merged",
        "_notes_row",
        "_image_ref_row",
        "_edit_panel",
    }
    assert expected <= initialized


def test_group_batch_priority_defer_callback_and_full_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    merged = _divider_merged(
        thickness="2",
        width_percent="50",
        alignment_horizontal="center",
    )
    harness._selected_id = merged.element_id
    harness._page_context_collapsed_group_bodies["line"] = _FakeFrame()
    specs = [
        harness._make_page_setting_spec(
            merged,
            setting_id,
            group_id="line",
            group_title="Linia",
        )
        for setting_id in ("thickness", "width_percent", "alignment_horizontal")
    ]
    setting_specs = [spec for spec in specs if spec is not None]
    events = _capture_events(monkeypatch)
    defer_calls: list[dict[str, Any]] = []

    def defer_once(**kwargs: Any) -> bool:
        defer_calls.append(dict(kwargs))
        return len(defer_calls) == 1

    harness._defer_background_for_selection = defer_once  # type: ignore[method-assign]
    harness._populate_page_context_group_batch(merged, "line", setting_specs, 0)

    assert len(defer_calls) == 1
    first = defer_calls[0]
    assert first["job"] == "page_context.group_batch"
    assert first["reason"] == "selection_priority_active"
    assert first["element_id"] == merged.element_id
    assert first["element_type"] == "divider"
    assert callable(first["callback"])
    assert harness._page_context_summary_rows == {}
    assert events == []

    first["callback"]()
    _run_fake_after_jobs(harness)

    assert len(harness._page_context_summary_rows) == 3
    payloads = _event_payloads(
        events,
        "studio.gicleeframe.page_context.group_summary_batch",
    )
    assert [(payload["start"], payload["end"]) for payload in payloads] == [
        (0, 1),
        (1, 2),
        (2, 3),
    ]
    for index, payload in enumerate(payloads):
        assert set(payload) == {
            "element_id",
            "element_type",
            "group_id",
            "start",
            "end",
            "created",
            "total_rows",
            "elapsed_ms",
        }
        assert payload["element_id"] == merged.element_id
        assert payload["element_type"] == "divider"
        assert payload["group_id"] == "line"
        assert payload["created"] == 1
        assert payload["total_rows"] == 3
        assert payload["start"] == index
        assert payload["end"] == index + 1
        assert payload["elapsed_ms"] >= 0


def test_create_row_from_spec_executes_page_setting_kind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    merged = _divider_merged(thickness="2")
    body = _FakeFrame()
    harness._page_context_collapsed_group_bodies["line"] = body
    spec = harness._make_page_setting_spec(
        merged,
        "thickness",
        group_id="line",
        group_title="Linia",
    )
    assert spec is not None and spec.kind == "page_setting"

    harness._create_page_context_row_from_spec(merged, spec)

    assert "setting:thickness" in harness._page_context_value_widgets
    assert harness._page_setting_widgets["thickness"] is harness._page_context_value_widgets[
        "setting:thickness"
    ]
    assert body.winfo_children()


def test_main_batch_priority_partial_reschedule_and_exact_final_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFramePageContextHarness()
    merged = _sample_merged("m1", element_type="media_section")
    harness._selected_id = merged.element_id
    specs = [
        PageContextRowSpec(kind="readonly_row", label=f"L{index}", value=str(index))
        for index in range(10)
    ]
    created: list[str] = []
    harness._create_page_context_row_from_spec = (  # type: ignore[method-assign]
        lambda _m, spec: created.append(spec.label)
    )
    defer_calls: list[dict[str, Any]] = []

    def defer_once(**kwargs: Any) -> bool:
        defer_calls.append(dict(kwargs))
        return len(defer_calls) == 1

    harness._defer_background_for_selection = defer_once  # type: ignore[method-assign]
    events = _capture_events(monkeypatch)

    harness._populate_page_context_batch(merged, specs, 0)
    assert created == []
    assert len(defer_calls) == 1
    assert defer_calls[0]["job"] == "page_context.batch"
    assert defer_calls[0]["reason"] == "selection_priority_active"
    assert callable(defer_calls[0]["callback"])

    defer_calls[0]["callback"]()
    assert created == [f"L{index}" for index in range(8)]
    assert len(harness._after_job_map) == 1
    scheduled_delay, continuation = next(iter(harness._after_job_map.values()))
    assert scheduled_delay == 0
    harness._after_job_map.clear()
    continuation()

    assert created == [f"L{index}" for index in range(10)]
    batch_payloads = _event_payloads(events, "studio.gicleeframe.page_context.batch")
    assert [(payload["start"], payload["end"], payload["created"]) for payload in batch_payloads] == [
        (0, 8, 8),
        (8, 10, 2),
    ]
    for payload in batch_payloads:
        assert set(payload) == {
            "element_id",
            "element_type",
            "start",
            "end",
            "batch_index",
            "created",
            "total_rows",
            "total",
            "elapsed_ms",
            "since_click_ms",
        }
        assert payload["element_id"] == merged.element_id
        assert payload["element_type"] == "media_section"
        assert payload["total_rows"] == 10
        assert payload["total"] == 10
        assert payload["since_click_ms"] == 5.0
        assert payload["elapsed_ms"] >= 0

    assert _event_payloads(events, "studio.gicleeframe.page_context.progressive_done") == [
        {
            "element_id": merged.element_id,
            "element_type": "media_section",
            "total_rows": 10,
        }
    ]
    assert len(_event_payloads(events, "studio.gicleeframe.page_context.reuse")) == 1
    assert len(_event_payloads(events, "studio.gicleeframe.page_context")) == 1


def test_progressive_stable_current_generation_exact_event_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFramePageContextHarness()
    merged = _divider_merged(thickness="2")
    harness._selected_id = merged.element_id
    harness._selection_generation = 7
    populate_calls: list[str] = []
    harness._populate_page_context_progressive = (  # type: ignore[method-assign]
        lambda element: populate_calls.append(element.element_id)
    )
    ticks = iter((100.0, 100.025))
    monkeypatch.setattr(page_context_module.time, "perf_counter", lambda: next(ticks))
    events = _capture_events(monkeypatch)

    harness._populate_page_context_progressive_stable(merged, generation=7)

    assert populate_calls == [merged.element_id]
    assert [name for name, _payload in events] == [
        "studio.gicleeframe.selection.page_context.populate_enter",
        "studio.gicleeframe.page_context.start",
        "studio.gicleeframe.selection.page_context.populate_done",
        "studio.gicleeframe.page_context.done",
    ]
    assert events[0][1] == {
        "element_id": merged.element_id,
        "element_type": "divider",
        "generation": 7,
        "since_click_ms": 5.0,
    }
    assert events[1][1] == events[0][1]
    assert events[2][1] == {
        "element_id": merged.element_id,
        "element_type": "divider",
        "generation": 7,
        "elapsed_ms": 25.0,
        "since_click_ms": 5.0,
    }
    assert events[3][1] == events[2][1]


@pytest.mark.parametrize("failure_mode", ["missing", "tcl"])
def test_precompute_cache_exits_cleanly_when_widget_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    harness = GicleeFramePageContextHarness()
    harness._merged = [_divider_merged(thickness="2")]
    events = _capture_events(monkeypatch)

    if failure_mode == "missing":
        harness.winfo_exists = lambda: False  # type: ignore[method-assign]
    else:
        def raise_tcl() -> bool:
            raise tk.TclError("gone")

        harness.winfo_exists = raise_tcl  # type: ignore[method-assign]

    harness._precompute_page_context_specs_cache()

    assert harness._page_context_specs_cache == {}
    assert events == []


def test_progressive_spec_cache_miss_then_hit_and_priority_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFramePageContextHarness()
    merged = _sample_merged(
        "m1",
        element_type="media_section",
        page_settings=(_setting_field("section_width"),),
    )
    harness._selected_id = merged.element_id
    computed = [PageContextRowSpec(kind="setting_card", field=merged.page_settings[0])]
    cached = [PageContextRowSpec(kind="readonly_card")]
    spec_calls: list[str] = []
    batch_calls: list[tuple[list[PageContextRowSpec], int]] = []
    defer_calls: list[dict[str, Any]] = []

    def row_specs(element: Any, *, show: bool = True) -> list[PageContextRowSpec]:
        spec_calls.append(element.element_id)
        assert show is True
        return computed

    def defer_once(**kwargs: Any) -> bool:
        defer_calls.append(dict(kwargs))
        return len(defer_calls) == 1

    harness._page_context_row_specs = row_specs  # type: ignore[method-assign]
    harness._populate_page_context_batch = (  # type: ignore[method-assign]
        lambda _m, specs, start: batch_calls.append((list(specs), start))
    )
    harness._defer_background_for_selection = defer_once  # type: ignore[method-assign]
    harness._clear_page_context_loading_label = lambda: None  # type: ignore[method-assign]
    harness._hide_page_context_rows = lambda: None  # type: ignore[method-assign]
    harness._reset_page_context_lazy_group_visual_state = lambda _m=None: None  # type: ignore[method-assign]

    harness._populate_page_context_progressive(merged)
    assert spec_calls == []
    assert batch_calls == []
    assert defer_calls[0]["job"] == "page_context.progressive"
    assert callable(defer_calls[0]["callback"])

    defer_calls[0]["callback"]()
    assert spec_calls == [merged.element_id]
    assert batch_calls == [(computed, 0)]

    harness._page_context_specs_cache[merged.element_id] = cached
    harness._populate_page_context_progressive(merged)
    assert spec_calls == [merged.element_id]
    assert batch_calls[-1] == (cached, 0)


def test_setting_summary_reuse_updates_value_and_edit_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    harness._selected_id = "d1"
    parent = _FakeFrame()
    harness._page_context_collapsed_group_bodies["line"] = parent
    opened: list[tuple[str, str]] = []
    harness._open_inline_setting_editor = (  # type: ignore[method-assign]
        lambda merged, spec, _row: opened.append((merged.element_id, spec.setting_id))
    )

    first = _divider_merged(thickness="2")
    first_spec = harness._make_page_setting_spec(
        first,
        "thickness",
        group_id="line",
        group_title="Linia",
    )
    assert first_spec is not None
    harness._create_page_context_setting_summary_row(first, first_spec)
    row_key = "setting_summary:d1:thickness"
    row = harness._page_context_row_cache[row_key]
    button = next(child for child in row.winfo_children() if isinstance(child, _FakeButton))
    assert callable(button._command)
    button._command()
    assert opened == [("d1", "thickness")]

    second = _divider_merged(thickness="3")
    second_spec = harness._make_page_setting_spec(
        second,
        "thickness",
        group_id="line",
        group_title="Linia",
    )
    assert second_spec is not None
    harness._create_page_context_setting_summary_row(second, second_spec)

    assert harness._page_context_row_cache[row_key] is row
    assert harness._page_context_summary_value_labels[row_key]._text == "thickness\n3"


def test_collapsed_group_reuse_and_already_expanded_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    merged = _divider_merged(
        thickness="2",
        width_percent="50",
        alignment_horizontal="center",
    )
    spec = next(
        item
        for item in harness._page_context_row_specs(merged, show=True)
        if item.kind == "collapsed_group" and item.group_id == "line"
    )
    events = _capture_events(monkeypatch)

    harness._create_page_context_collapsed_group_row(merged, spec)
    row = harness._page_context_collapsed_group_rows["line"]
    button = harness._page_context_collapsed_group_buttons["line"]
    body = _FakeFrame()
    body.pack(fill="x")
    harness._page_context_collapsed_group_bodies["line"] = body

    events.clear()
    harness._create_page_context_collapsed_group_row(merged, spec)
    assert harness._page_context_collapsed_group_rows["line"] is row
    assert body.pack_forget_calls == 1
    assert button._text == "▸ Linia · 3 ustawienia"
    assert not _event_payloads(events, "studio.gicleeframe.page_context.group_placeholder_created")

    harness._selected_id = merged.element_id
    harness._page_context_expanded_group_ids.add("line")
    events.clear()
    harness._expand_page_context_group(merged, spec)
    assert body.pack_calls[-1] == {"fill": "x", "padx": 8, "pady": (0, 8)}
    assert not _event_payloads(events, "studio.gicleeframe.page_context.group_expanded")


def test_cancel_jobs_and_layout_reset_swallow_tcl_with_exact_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    harness._page_context_after_ids = ["after-a", "after-b"]

    def raise_cancel(_after_id: str) -> None:
        raise tk.TclError("gone")

    harness.after_cancel = raise_cancel  # type: ignore[method-assign]
    assert harness._cancel_page_context_jobs() == 2
    assert harness._page_context_after_ids == []

    doomed = _FakeFrame()
    doomed.destroy = lambda: (_ for _ in ()).throw(tk.TclError("gone"))  # type: ignore[method-assign]
    harness._page_context_row_cache = {
        "setting_card:thickness": doomed,
        "container:readonly": _FakeFrame(),
    }
    harness._page_context_row_managers = {
        "setting_card:thickness": "pack",
        "container:readonly": "pack",
    }
    harness._page_context_visible_keys = set(harness._page_context_row_cache)
    harness._page_setting_widgets = {"thickness": _FakeEntry()}
    events = _capture_events(monkeypatch)

    harness._reset_page_context_settings_on_layout_change("flat")

    assert "setting_card:thickness" not in harness._page_context_row_cache
    assert "container:readonly" in harness._page_context_row_cache
    assert harness._page_setting_widgets == {}
    assert _event_payloads(events, "studio.gicleeframe.page_context.destroy_fallback") == [
        {"reason": "settings_layout_change", "new_layout": "flat"}
    ]


def test_immediate_fill_reuses_cached_rows_without_normal_path_destroy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFramePageContextHarness()
    merged = _sample_merged(
        "flat",
        element_type="media_section",
        page_settings=(_setting_field("section_width"),),
    )
    events = _capture_events(monkeypatch)

    harness._fill_page_context(merged, show=True)
    card = harness._page_context_row_cache["setting_card:section_width"]
    widget = harness._page_setting_widgets["section_width"]
    harness._fill_page_context(merged, show=True)

    assert harness._page_context_row_cache["setting_card:section_width"] is card
    assert harness._page_setting_widgets["section_width"] is widget
    assert card.destroy_calls == 0
    assert not _event_payloads(events, "studio.gicleeframe.page_context.destroy_fallback")
