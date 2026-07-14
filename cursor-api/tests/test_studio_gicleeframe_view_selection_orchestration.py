"""Boundary tests for the extracted GICLÉE FRAME selection orchestration subsystem."""

from __future__ import annotations

import ast
import sys
import time
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_selection_orchestration as selection_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
    _progressive_boot_enabled,
)
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)
from giclee_app.ui.gicleeframe_view_page_context import GicleeFramePageContextMixin
from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
)
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
    _GF_ATOMIC_SWAP_STATUS_TEXT,
    _GF_SELECT_POPULATE_DEFER_MS,
    _GF_SELECTION_PRIORITY_WINDOW_MS,
    _GF_SELECTION_PRIORITY_YIELD_DEFER_MS,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
SELECTION_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_selection_orchestration.py"
)

_EXPECTED_METHODS = {
    "_since_selection_click_ms",
    "_selection_priority_active",
    "_open_selection_priority_window",
    "_preempt_background_for_selection_priority",
    "_cancel_section_list_batch_continuation",
    "_end_selection_priority_window",
    "_defer_background_for_selection",
    "_should_run_immediate_selection_populate",
    "_schedule_selection_populate",
    "_ensure_preserved_selection_populate_after_inventory_light",
    "_select_element",
    "_schedule_atomic_swap_populate",
    "_run_atomic_swap_populate",
    "_flush_atomic_swap_row_visibility",
    "_populate_editor_deferred",
    "_merged_for_selection_generation",
    "_cancel_selection_jobs",
    "_schedule_selection_job",
}

_HOST_OWNERSHIP = {
    "__init__",
    "_editor_micro_defer_ms",
    "_progressive_boot_enabled_for_selection",
    "_highlight_section_row",
    "_update_section_list_trigger",
    "_collapse_section_list",
}

_LIFECYCLE_OWNERSHIP = {
    "_queue_latency_since_ms",
}

_PAGE_CONTEXT_ADAPTER = {
    "_cancel_page_context_jobs",
    "_close_active_setting_editor",
}

_HOST_OWNERSHIP_IN_VIEW = _HOST_OWNERSHIP - {
    "_highlight_section_row",
    "_update_section_list_trigger",
    "_collapse_section_list",
}

_INTERACTION_OWNERSHIP = {
    "_highlight_section_row",
    "_update_section_list_trigger",
    "_collapse_section_list",
}


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _sample_merged(
    element_id: str,
    *,
    element_type: str = "media_section",
    section_key: str = "section-1",
) -> SimpleNamespace:
    return SimpleNamespace(
        element_id=element_id,
        element_type=element_type,
        section_key=section_key,
    )


class _SelectionOrchestrationHarness(GicleeFrameSelectionOrchestrationMixin):
    def __init__(self) -> None:
        self._selected_id: str | None = None
        self._merged_by_id: dict[str, Any] = {}
        self._selection_generation = 0
        self._selection_after_ids: list[str] = []
        self._selection_click_mono: float | None = None
        self._selection_populate_scheduled_mono: float | None = None
        self._selection_priority_generation: int | None = None
        self._selection_priority_until_mono: float | None = None
        self._selection_priority_end_after_id: str | None = None
        self._selection_visual_cache_applied = False
        self._section_visual_cache: dict[str, Any] = {}
        self._details_on_demand_expanded = False
        self._details_on_demand_active_element_id: str | None = None
        self._details_on_demand_request_mono: float | None = None
        self._details_cta_click_mono: float | None = None
        self._page_context_generation = 0
        self._editor_has_ready_content = False
        self._editor_last_ready_element_id: str | None = None
        self._atomic_swap_suppress_visible = False
        self._atomic_swap_deferred_row_visibility: list[tuple[Any, bool]] = []
        self._section_list_batch_after_id: str | None = None
        self._media_deferred_done_after_id: str | None = None
        self._shell_editor_built = False
        self._after_calls: list[tuple[int, Any]] = []
        self._after_idle_calls: list[Any] = []
        self._after_cancel_calls: list[str] = []
        self._after_counter = 0
        self._after_cancel_raises: set[str] = set()
        self._progressive_boot_for_selection = True
        self._details_jobs_cancelled = 0
        self._page_context_jobs_cancelled = 0
        self._highlight_calls: list[str | None] = []
        self._trigger_calls = 0
        self._collapse_calls = 0
        self._close_setting_editor_calls = 0
        self._hide_details_container_calls = 0
        self._hide_details_shell_calls = 0
        self._hide_details_on_demand_calls = 0
        self._minimal_cache_entry_result: Any | None = None
        self._apply_minimal_cache_calls: list[Any] = []
        self._show_refresh_status_calls: list[str] = []
        self._hide_media_details_calls = 0
        self._show_stable_shell_calls: list[tuple[Any, bool]] = []
        self._populate_editor_calls: list[dict[str, Any]] = []
        self._hide_refresh_status_calls = 0
        self._set_row_visible_calls: list[tuple[Any, bool]] = []
        self._queue_latency_result = 0.0
        self._since_details_request_result: float | None = None
        self._schedule_atomic_swap_calls: list[tuple[str, int]] = []
        self._schedule_selection_populate_calls: list[tuple[str, int, str]] = []
        self._populate_editor_deferred_calls: list[tuple[str, int]] = []
        self._cancel_section_list_batch_calls = 0

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_counter += 1
        after_id = f"after-{self._after_counter}"
        self._after_calls.append((delay_ms, callback))
        return after_id

    def after_idle(self, callback: Any) -> str:
        self._after_counter += 1
        after_id = f"idle-{self._after_counter}"
        self._after_idle_calls.append(callback)
        return after_id

    def after_cancel(self, after_id: str) -> None:
        if after_id in self._after_cancel_raises:
            raise tk.TclError("invalid command name")
        self._after_cancel_calls.append(after_id)

    def _progressive_boot_enabled_for_selection(self) -> bool:
        return self._progressive_boot_for_selection

    def _cancel_details_on_demand_jobs(self) -> int:
        return self._details_jobs_cancelled

    def _cancel_page_context_jobs(self) -> int:
        return self._page_context_jobs_cancelled

    def _hide_details_container(self) -> None:
        self._hide_details_container_calls += 1

    def _hide_details_shell(self) -> None:
        self._hide_details_shell_calls += 1

    def _hide_details_on_demand_block(self) -> None:
        self._hide_details_on_demand_calls += 1

    def _close_active_setting_editor(self) -> None:
        self._close_setting_editor_calls += 1

    def _highlight_section_row(self, previous_id: str | None = None) -> None:
        self._highlight_calls.append(previous_id)

    def _update_section_list_trigger(self) -> None:
        self._trigger_calls += 1

    def _minimal_cache_entry(self, m: Any) -> Any | None:
        _ = m
        return self._minimal_cache_entry_result

    def _apply_minimal_cache(self, m: Any) -> None:
        self._apply_minimal_cache_calls.append(m)

    def _show_editor_refresh_status(self, text: str) -> None:
        self._show_refresh_status_calls.append(text)

    def _hide_media_details_stable_shell(self) -> None:
        self._hide_media_details_calls += 1

    def _show_editor_selection_stable_shell_state(
        self,
        m: Any,
        *,
        from_cache: bool,
    ) -> None:
        self._show_stable_shell_calls.append((m, from_cache))

    def _collapse_section_list(self) -> None:
        self._collapse_calls += 1

    def _populate_editor(self, m: Any, **kwargs: Any) -> None:
        self._populate_editor_calls.append({"element": m, **kwargs})

    def _hide_editor_refresh_status(self) -> None:
        self._hide_refresh_status_calls += 1

    def _set_row_visible(self, row: Any, visible: bool) -> None:
        self._set_row_visible_calls.append((row, visible))

    def _queue_latency_since_ms(self, started_mono: float | None) -> float | None:
        _ = started_mono
        return self._queue_latency_result

    def _since_details_request_ms(self) -> float | None:
        return self._since_details_request_result

    def _schedule_atomic_swap_populate(self, element_id: str, generation: int) -> None:
        self._schedule_atomic_swap_calls.append((element_id, generation))
        GicleeFrameSelectionOrchestrationMixin._schedule_atomic_swap_populate(
            self,
            element_id,
            generation,
        )

    def _schedule_selection_populate(
        self,
        element_id: str,
        generation: int,
        *,
        element_type: str,
    ) -> None:
        self._schedule_selection_populate_calls.append(
            (element_id, generation, element_type),
        )
        GicleeFrameSelectionOrchestrationMixin._schedule_selection_populate(
            self,
            element_id,
            generation,
            element_type=element_type,
        )

    def _populate_editor_deferred(self, element_id: str, generation: int) -> None:
        self._populate_editor_deferred_calls.append((element_id, generation))
        GicleeFrameSelectionOrchestrationMixin._populate_editor_deferred(
            self,
            element_id,
            generation,
        )

    def _cancel_section_list_batch_continuation(self) -> bool:
        self._cancel_section_list_batch_calls += 1
        return GicleeFrameSelectionOrchestrationMixin._cancel_section_list_batch_continuation(
            self,
        )


def test_selection_orchestration_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameSelectionOrchestrationMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameSelectionOrchestrationMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameSelectionOrchestrationMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }


def test_selection_orchestration_module_has_no_write_network_or_reverse_host_import() -> None:
    source = SELECTION_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "giclee_app.ui.gicleeframe_view"
            assert node.module != ".gicleeframe_view"
    lowered = source.lower()
    assert "write_text(" not in lowered
    assert "subprocess" not in lowered
    assert "shopify" not in lowered
    assert "deploy" not in lowered


def test_selection_orchestration_public_boundary_contract() -> None:
    assert selection_module.__all__ == (
        "GicleeFrameSelectionOrchestrationMixin",
        "_GF_ATOMIC_SWAP_STATUS_TEXT",
        "_GF_SELECTION_PRIORITY_WINDOW_MS",
        "_GF_SELECTION_PRIORITY_YIELD_DEFER_MS",
        "_GF_SELECT_POPULATE_DEFER_MS",
    )


def test_selection_orchestration_constants_exact_values() -> None:
    assert _GF_ATOMIC_SWAP_STATUS_TEXT == "Przygotowuję sekcję…"
    assert _GF_SELECT_POPULATE_DEFER_MS == 0
    assert _GF_SELECTION_PRIORITY_WINDOW_MS == 200
    assert _GF_SELECTION_PRIORITY_YIELD_DEFER_MS == 60
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in (
        "_GF_ATOMIC_SWAP_STATUS_TEXT",
        "_GF_SELECT_POPULATE_DEFER_MS",
        "_GF_SELECTION_PRIORITY_WINDOW_MS",
        "_GF_SELECTION_PRIORITY_YIELD_DEFER_MS",
    ):
        assert f"{name} =" not in host_text


def test_gicleeframe_view_has_sixteen_mixins_before_scrollable_frame() -> None:
    mro = GicleeFrameView.__mro__
    for mixin in (
        GicleeFrameBrandPanelMixin,
        GicleeFramePageReadinessMixin,
        GicleeFrameStructureDryRunMixin,
        GicleeFrameSafetyCardMixin,
        GicleeFrameReadinessRowMixin,
        GicleeFrameTopBarMixin,
        GicleeFrameRamVariantMixin,
        GicleeFrameSectionListShellMixin,
        GicleeFrameSectionListRenderingMixin,
        GicleeFrameSectionListInteractionMixin,
        GicleeFrameSelectionOrchestrationMixin,
        GicleeFrameEditorShellMixin,
        GicleeFrameDetailsOnDemandMixin,
        GicleeFrameVisualDetailRenderersMixin,
        GicleeFramePageContextMixin,
        GicleeFrameLifecycleInventoryMixin,
    ):
        assert mixin in mro
    assert mro.index(GicleeFrameSectionListInteractionMixin) < mro.index(
        GicleeFrameSelectionOrchestrationMixin,
    )
    assert mro.index(GicleeFrameSelectionOrchestrationMixin) < mro.index(
        GicleeFrameEditorShellMixin,
    )
    assert mro.index(GicleeFrameEditorShellMixin) < mro.index(
        GicleeFrameDetailsOnDemandMixin,
    )
    assert mro.index(GicleeFrameDetailsOnDemandMixin) < mro.index(
        GicleeFrameVisualDetailRenderersMixin,
    )
    assert mro.index(GicleeFrameVisualDetailRenderersMixin) < mro.index(
        GicleeFramePageContextMixin,
    )
    assert mro.index(GicleeFramePageContextMixin) < mro.index(
        GicleeFrameLifecycleInventoryMixin,
    )
    assert mro.index(GicleeFrameLifecycleInventoryMixin) < mro.index(
        ctk.CTkScrollableFrame,
    )


def test_selection_orchestration_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameSelectionOrchestrationMixin,
            name,
        )


def test_host_ownership_for_selection_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name not in GicleeFrameSelectionOrchestrationMixin.__dict__
    for name in _HOST_OWNERSHIP_IN_VIEW:
        assert name in GicleeFrameView.__dict__
    for name in _LIFECYCLE_OWNERSHIP:
        assert name not in GicleeFrameView.__dict__
        assert name in GicleeFrameLifecycleInventoryMixin.__dict__
    for name in _INTERACTION_OWNERSHIP:
        assert name in GicleeFrameSectionListInteractionMixin.__dict__
    for name in _PAGE_CONTEXT_ADAPTER:
        assert name not in GicleeFrameSelectionOrchestrationMixin.__dict__
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFramePageContextMixin, name)
    assert "_select_element" not in GicleeFrameView.__dict__


def test_progressive_boot_enabled_for_selection_delegates_to_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = object.__new__(GicleeFrameView)
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view._progressive_boot_enabled",
        lambda: True,
    )
    assert view._progressive_boot_enabled_for_selection() is True
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view._progressive_boot_enabled",
        lambda: False,
    )
    assert view._progressive_boot_enabled_for_selection() is False
    with patch(
        "giclee_app.ui.gicleeframe_view._progressive_boot_enabled",
        return_value=True,
    ):
        assert view._progressive_boot_enabled_for_selection() is True
        assert view._progressive_boot_enabled_for_selection() == _progressive_boot_enabled()


def test_since_selection_click_ms_none_when_absent() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_click_mono = None
    assert harness._since_selection_click_ms() is None


def test_since_selection_click_ms_elapsed_rounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_click_mono = 100.0
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 100.123456)
    assert harness._since_selection_click_ms() == 123.46


def test_selection_priority_active_inactive_when_no_deadline() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_until_mono = None
    assert harness._selection_priority_active() is False


def test_selection_priority_active_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_until_mono = 50.0
    harness._selection_priority_generation = 3
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 50.01)
    assert harness._selection_priority_active() is False


def test_selection_priority_active_generation_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_until_mono = 200.0
    harness._selection_priority_generation = 3
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 100.0)
    assert harness._selection_priority_active(generation=4) is False


def test_selection_priority_active_current_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_until_mono = 200.0
    harness._selection_priority_generation = 3
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 100.0)
    assert harness._selection_priority_active(generation=3) is True


def test_open_selection_priority_window_cancels_previous_end_callback() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_end_after_id = "prio-end-old"
    harness._open_selection_priority_window(
        2,
        element_id="elem-a",
        element_type="media_section",
    )
    assert harness._after_cancel_calls == ["prio-end-old"]
    assert harness._selection_priority_end_after_id is not None
    assert harness._selection_priority_end_after_id != "prio-end-old"


def test_open_selection_priority_window_tclerror_on_cancel_swallowed() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_end_after_id = "broken-id"
    harness._after_cancel_raises.add("broken-id")
    harness._open_selection_priority_window(
        1,
        element_id="elem-a",
        element_type="divider",
    )
    assert harness._selection_priority_generation == 1
    assert harness._selection_priority_end_after_id is not None


def test_open_selection_priority_window_scheduling_deadline_and_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_click_mono = 10.0
    events: list[tuple[str, dict[str, Any]]] = []

    def _log(event: str, **kwargs: Any) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr(selection_module, "log_event", _log)
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 20.0)
    harness._open_selection_priority_window(
        5,
        element_id="elem-x",
        element_type="media_section",
    )
    assert harness._selection_priority_until_mono == pytest.approx(20.2)
    assert harness._after_calls[-1][0] == _GF_SELECTION_PRIORITY_WINDOW_MS
    started = [item for item in events if item[0] == "studio.gicleeframe.selection.priority_start"]
    assert len(started) == 1
    assert started[0][1]["generation"] == 5
    assert started[0][1]["element_id"] == "elem-x"
    assert started[0][1]["window_ms"] == _GF_SELECTION_PRIORITY_WINDOW_MS
    assert harness._cancel_section_list_batch_calls == 1


def test_end_selection_priority_window_stale_generation_no_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_generation = 9
    harness._selection_priority_until_mono = 500.0
    harness._selection_priority_end_after_id = "prio-end"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._end_selection_priority_window(8)
    assert harness._selection_priority_until_mono == 500.0
    assert events == []


def test_end_selection_priority_window_current_clears_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_generation = 4
    harness._selection_priority_until_mono = 500.0
    harness._selection_priority_end_after_id = "prio-end"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._end_selection_priority_window(4)
    assert harness._selection_priority_until_mono is None
    assert harness._selection_priority_end_after_id is None
    assert events[0][0] == "studio.gicleeframe.selection.priority_end"
    assert events[0][1]["generation"] == 4


def test_cancel_section_list_batch_continuation_absent_returns_false() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._section_list_batch_after_id = None
    assert harness._cancel_section_list_batch_continuation() is False
    assert harness._after_cancel_calls == []


def test_cancel_section_list_batch_continuation_present_clears_before_cancel() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._section_list_batch_after_id = "batch-1"
    assert harness._cancel_section_list_batch_continuation() is True
    assert harness._section_list_batch_after_id is None
    assert harness._after_cancel_calls == ["batch-1"]


def test_cancel_section_list_batch_continuation_tclerror_swallowed() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._section_list_batch_after_id = "broken-batch"
    harness._after_cancel_raises.add("broken-batch")
    assert harness._cancel_section_list_batch_continuation() is True
    assert harness._section_list_batch_after_id is None


def test_preempt_background_no_cancel_no_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._preempt_background_for_selection_priority(
        generation=1,
        element_id="a",
        element_type="divider",
    )
    assert events == []


def test_preempt_background_cancel_logs_deferred_for_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._section_list_batch_after_id = "batch-2"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._preempt_background_for_selection_priority(
        generation=2,
        element_id="elem-b",
        element_type="media_section",
    )
    assert len(events) == 1
    assert events[0][0] == "studio.gicleeframe.background.deferred_for_selection"
    payload = events[0][1]
    assert payload["reason"] == "selection_priority_preempt"
    assert payload["delay_ms"] == 0
    assert payload["job"] == "section_list.incremental_batch"


def test_defer_background_for_selection_inactive_returns_false() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_until_mono = None
    result = harness._defer_background_for_selection(
        job="control.late_cards",
        reason="selection_priority_active",
        callback=lambda: None,
    )
    assert result is False
    assert harness._after_calls == []


def test_defer_background_for_selection_default_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_generation = 7
    harness._selection_priority_until_mono = time.perf_counter() + 1.0
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    callback = object()
    result = harness._defer_background_for_selection(
        job="section_list.incremental",
        reason="selection_priority_active",
        callback=callback,
    )
    assert result is True
    assert harness._after_calls == [(_GF_SELECTION_PRIORITY_YIELD_DEFER_MS, callback)]
    assert events[0][1]["delay_ms"] == _GF_SELECTION_PRIORITY_YIELD_DEFER_MS


def test_defer_background_for_selection_custom_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_priority_generation = 2
    harness._selection_priority_until_mono = time.perf_counter() + 1.0
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    callback = object()
    result = harness._defer_background_for_selection(
        job="custom.job",
        reason="custom_reason",
        callback=callback,
        delay_ms=150,
    )
    assert result is True
    assert harness._after_calls == [(150, callback)]


def test_cancel_selection_jobs_count_and_clears_after_ids() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_after_ids = ["job-1", "job-2", "job-3"]
    cancelled = harness._cancel_selection_jobs()
    assert cancelled == 3
    assert harness._selection_after_ids == []
    assert set(harness._after_cancel_calls) == {"job-1", "job-2", "job-3"}


def test_cancel_selection_jobs_media_deferred_cancelled() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_after_ids = []
    harness._media_deferred_done_after_id = "media-done"
    cancelled = harness._cancel_selection_jobs()
    assert cancelled == 0
    assert harness._media_deferred_done_after_id is None
    assert "media-done" in harness._after_cancel_calls


def test_cancel_selection_jobs_tclerror_swallowed() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_after_ids = ["broken-job"]
    harness._after_cancel_raises.add("broken-job")
    assert harness._cancel_selection_jobs() == 1
    assert harness._selection_after_ids == []


def test_schedule_selection_job_appends_after_id() -> None:
    harness = _SelectionOrchestrationHarness()
    callback = object()
    harness._schedule_selection_job(25, callback)
    assert len(harness._selection_after_ids) == 1
    assert harness._after_calls == [(25, callback)]


def test_schedule_selection_populate_scheduling_and_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    monkeypatch.setattr(selection_module.time, "perf_counter", lambda: 42.0)
    harness._schedule_selection_populate("elem-pop", 3, element_type="divider")
    assert harness._selection_populate_scheduled_mono == 42.0
    assert harness._after_calls[0][0] == _GF_SELECT_POPULATE_DEFER_MS
    scheduled = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.selection.populate_priority_scheduled"
    ]
    assert len(scheduled) == 1
    assert scheduled[0][1]["defer_ms"] == _GF_SELECT_POPULATE_DEFER_MS
    assert scheduled[0][1]["element_id"] == "elem-pop"


def test_should_run_immediate_selection_populate_returns_true() -> None:
    harness = _SelectionOrchestrationHarness()
    assert harness._should_run_immediate_selection_populate(_sample_merged("a")) is True


def test_ensure_preserved_selection_populate_generation_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 5
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._ensure_preserved_selection_populate_after_inventory_light("a", 4)
    assert harness._populate_editor_deferred_calls == []
    assert harness._schedule_selection_populate_calls == []


def test_ensure_preserved_selection_populate_selected_id_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 3
    harness._selected_id = "other"
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._ensure_preserved_selection_populate_after_inventory_light("a", 3)
    assert harness._populate_editor_deferred_calls == []


def test_ensure_preserved_selection_populate_pending_jobs_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 3
    harness._selected_id = "a"
    harness._selection_after_ids = ["pending"]
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._ensure_preserved_selection_populate_after_inventory_light("a", 3)
    assert harness._populate_editor_deferred_calls == []


def test_ensure_preserved_selection_populate_immediate_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 2
    harness._selected_id = "a"
    harness._merged_by_id = {"a": _sample_merged("a")}
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._ensure_preserved_selection_populate_after_inventory_light("a", 2)
    assert harness._populate_editor_deferred_calls == [("a", 2)]
    immediate = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.selection.populate_priority_scheduled"
        and item[1].get("immediate") is True
    ]
    assert len(immediate) == 1
    repop = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.selection.repopulate_after_inventory_scheduled"
    ]
    assert len(repop) == 1


def test_ensure_preserved_selection_populate_fallback_scheduling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 2
    harness._selected_id = "a"
    harness._merged_by_id = {"a": _sample_merged("a")}
    monkeypatch.setattr(
        harness,
        "_should_run_immediate_selection_populate",
        lambda _m: False,
    )
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._ensure_preserved_selection_populate_after_inventory_light("a", 2)
    assert harness._schedule_selection_populate_calls == [("a", 2, "media_section")]


def test_select_element_missing_element_early_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._select_element("missing")
    assert harness._selected_id == "missing"
    assert any(item[0] == "studio.gicleeframe.select_element.missing" for item in events)
    assert harness._schedule_atomic_swap_calls == []


def test_select_element_cancellation_order_and_generation_increment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._merged_by_id = {"a": _sample_merged("a")}
    harness._selection_after_ids = ["sel-1"]
    harness._page_context_generation = 10
    order: list[str] = []

    def _cancel_selection() -> int:
        order.append("selection")
        return GicleeFrameSelectionOrchestrationMixin._cancel_selection_jobs(harness)

    def _cancel_details() -> int:
        order.append("details")
        harness._details_jobs_cancelled = 2
        return 2

    def _cancel_page_context() -> int:
        order.append("page_context")
        harness._page_context_jobs_cancelled = 1
        return 1

    monkeypatch.setattr(harness, "_cancel_selection_jobs", _cancel_selection)
    monkeypatch.setattr(harness, "_cancel_details_on_demand_jobs", _cancel_details)
    monkeypatch.setattr(harness, "_cancel_page_context_jobs", _cancel_page_context)
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda *_a, **_k: None,
    )
    before = harness._selection_generation
    harness._select_element("a")
    assert harness._selection_generation == before + 1
    assert order == ["selection", "details", "page_context"]
    assert harness._page_context_generation == 11


def test_select_element_details_cancel_reset_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._merged_by_id = {"a": _sample_merged("a")}
    harness._details_jobs_cancelled = 1
    harness._details_on_demand_active_element_id = "old-details"
    harness._details_on_demand_request_mono = 1.0
    harness._details_cta_click_mono = 2.0
    harness._since_details_request_result = 15.0
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda *_a, **_k: None,
    )
    harness._select_element("a")
    assert harness._hide_details_container_calls == 1
    assert harness._details_on_demand_active_element_id is None
    assert harness._details_on_demand_request_mono is None
    assert harness._details_cta_click_mono is None
    cancelled = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.details_on_demand.cancelled"
    ]
    assert len(cancelled) == 1
    assert cancelled[0][1]["request_open_ms"] == 15.0


def test_select_element_highlight_trigger_and_collapse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selected_id = "prev"
    harness._merged_by_id = {"a": _sample_merged("a")}
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda *_a, **_k: None,
    )
    harness._select_element("a", collapse_list=True)
    assert harness._highlight_calls == ["prev"]
    assert harness._trigger_calls == 1
    assert harness._collapse_calls == 1


def test_select_element_minimal_cache_hit_no_populate_scheduling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._minimal_cache_entry_result = {"cached": True}
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    swap_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda eid, gen: swap_calls.append((eid, gen)),
    )
    harness._select_element("a")
    assert harness._apply_minimal_cache_calls == [element]
    assert harness._selection_visual_cache_applied is True
    assert swap_calls == []
    assert any(
        item[0] == "studio.gicleeframe.selection.minimal_cache_hit" for item in events
    )


def test_select_element_cache_miss_partial_and_stale_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._section_visual_cache = {"a": {"partial": True}}
    harness._editor_has_ready_content = True
    harness._editor_last_ready_element_id = "old"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    swap_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda eid, gen: swap_calls.append((eid, gen)),
    )
    harness._select_element("a")
    assert harness._show_refresh_status_calls == [_GF_ATOMIC_SWAP_STATUS_TEXT]
    assert any(
        item[0] == "studio.gicleeframe.selection.cache_hit_partial" for item in events
    )
    assert any(
        item[0] == "studio.gicleeframe.editor.stale_content_kept" for item in events
    )
    assert len(swap_calls) == 1


def test_select_element_cache_miss_no_ready_content_stable_shell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._editor_has_ready_content = False
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda *_a, **_k: None,
    )
    harness._select_element("a")
    assert harness._hide_media_details_calls == 1
    assert harness._show_stable_shell_calls == [(element, False)]


def test_select_element_immediate_ready_and_populate_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._merged_by_id = {"a": _sample_merged("a")}
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    swap_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda eid, gen: swap_calls.append((eid, gen)),
    )
    harness._select_element("a")
    assert any(item[0] == "studio.gicleeframe.selection.immediate_ready" for item in events)
    assert any(
        item[0] == "studio.gicleeframe.selection.populate_priority_scheduled"
        and item[1].get("atomic_swap") is True
        for item in events
    )
    assert any(item[0] == "studio.gicleeframe.selection.populate_scheduled" for item in events)
    assert len(swap_calls) == 1


def test_select_element_uses_progressive_boot_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._merged_by_id = {"a": _sample_merged("a")}
    harness._progressive_boot_for_selection = False
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    monkeypatch.setattr(
        harness,
        "_schedule_atomic_swap_populate",
        lambda *_a, **_k: None,
    )
    harness._select_element("a")
    user_prog = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.select_element.user_or_programmatic"
    ]
    assert len(user_prog) == 1
    assert user_prog[0][1]["progressive_boot"] is False


def test_schedule_atomic_swap_populate_uses_after_idle() -> None:
    harness = _SelectionOrchestrationHarness()
    harness._schedule_atomic_swap_populate("elem-a", 4)
    assert len(harness._after_idle_calls) == 1


def test_run_atomic_swap_populate_stale_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 5
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._run_atomic_swap_populate("a", 4)
    assert events[0][0] == "studio.gicleeframe.selection.atomic_swap.stale"
    assert harness._populate_editor_calls == []


def test_run_atomic_swap_populate_stale_selected_or_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 4
    harness._selected_id = "other"
    harness._merged_by_id = {"a": _sample_merged("a")}
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._run_atomic_swap_populate("a", 4)
    assert harness._populate_editor_calls == []


def test_run_atomic_swap_populate_current_without_stale_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}
    harness._editor_has_ready_content = False
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._run_atomic_swap_populate("a", 4)
    assert harness._populate_editor_calls == [{"element": element, "atomic_swap": True}]
    assert harness._hide_refresh_status_calls == 1
    assert any(item[0] == "studio.gicleeframe.selection.atomic_swap.applied" for item in events)


def test_run_atomic_swap_populate_with_stale_content_and_flush(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}
    harness._editor_has_ready_content = True
    row_a = object()
    row_b = object()

    def _populate_and_defer(m: Any, **kwargs: Any) -> None:
        harness._atomic_swap_deferred_row_visibility.extend(
            [(row_a, True), (row_b, False)],
        )

    monkeypatch.setattr(harness, "_populate_editor", _populate_and_defer)
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    harness._run_atomic_swap_populate("a", 4)
    assert harness._atomic_swap_suppress_visible is False
    assert harness._atomic_swap_deferred_row_visibility == []
    assert harness._set_row_visible_calls == [(row_a, True), (row_b, False)]


def test_run_atomic_swap_populate_finally_cleanup_on_populate_raise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}
    harness._editor_has_ready_content = True
    harness._atomic_swap_deferred_row_visibility = [(object(), True)]
    harness._atomic_swap_suppress_visible = True

    def _raise(_m: Any, **kwargs: Any) -> None:
        raise RuntimeError("populate failed")

    monkeypatch.setattr(harness, "_populate_editor", _raise)
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    with pytest.raises(RuntimeError, match="populate failed"):
        harness._run_atomic_swap_populate("a", 4)
    assert harness._atomic_swap_suppress_visible is False
    assert harness._atomic_swap_deferred_row_visibility == []


def test_run_atomic_swap_populate_completion_guard_stale_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}

    def _populate_and_bump(m: Any, **kwargs: Any) -> None:
        harness._selection_generation = 5

    monkeypatch.setattr(harness, "_populate_editor", _populate_and_bump)
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._run_atomic_swap_populate("a", 4)
    assert not any(
        item[0] == "studio.gicleeframe.selection.atomic_swap.applied" for item in events
    )
    assert harness._hide_refresh_status_calls == 0


def test_populate_editor_deferred_stale_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 5
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._populate_editor_deferred("a", 4)
    assert events[0][0] == "studio.gicleeframe.populate_editor.deferred_stale"
    assert harness._populate_editor_calls == []


def test_populate_editor_deferred_missing_or_stale_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 4
    harness._selected_id = "other"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._populate_editor_deferred("a", 4)
    assert events[0][0] == "studio.gicleeframe.populate_editor.deferred_missing_or_stale"


def test_populate_editor_deferred_current_path_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}
    harness._selection_visual_cache_applied = True
    harness._queue_latency_result = 12.5
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._populate_editor_deferred("a", 4)
    assert harness._populate_editor_calls == [
        {"element": element, "visual_cache_refresh": True},
    ]
    assert any(item[0] == "studio.gicleeframe.selection.populate_enter" for item in events)
    assert any(item[0] == "studio.gicleeframe.selection.populate.start" for item in events)
    assert any(item[0] == "studio.gicleeframe.selection.populate_done" for item in events)
    assert any(item[0] == "studio.gicleeframe.selection.populate.done" for item in events)


def test_merged_for_selection_generation_stale_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 5
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    assert (
        harness._merged_for_selection_generation("a", 4, event_prefix="studio.test")
        is None
    )
    assert events[0][0] == "studio.test.stale"


def test_merged_for_selection_generation_stale_selected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 4
    harness._selected_id = "other"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    assert (
        harness._merged_for_selection_generation("a", 4, event_prefix="studio.test")
        is None
    )
    assert events[0][0] == "studio.test.stale_selected"


def test_merged_for_selection_generation_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    harness._selection_generation = 4
    harness._selected_id = "a"
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        selection_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    assert (
        harness._merged_for_selection_generation("a", 4, event_prefix="studio.test")
        is None
    )
    assert events[0][0] == "studio.test.missing"


def test_merged_for_selection_generation_current_returns_element(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SelectionOrchestrationHarness()
    element = _sample_merged("a")
    harness._selection_generation = 4
    harness._selected_id = "a"
    harness._merged_by_id = {"a": element}
    monkeypatch.setattr(selection_module, "log_event", lambda *_a, **_k: None)
    assert (
        harness._merged_for_selection_generation("a", 4, event_prefix="studio.test")
        is element
    )


def test_flush_atomic_swap_row_visibility_order_and_delegation() -> None:
    harness = _SelectionOrchestrationHarness()
    row_a = object()
    row_b = object()
    harness._atomic_swap_deferred_row_visibility = [(row_a, True), (row_b, False)]
    harness._atomic_swap_suppress_visible = True
    harness._flush_atomic_swap_row_visibility()
    assert harness._atomic_swap_deferred_row_visibility == []
    assert harness._atomic_swap_suppress_visible is False
    assert harness._set_row_visible_calls == [(row_a, True), (row_b, False)]


def test_selection_source_ownership_in_module() -> None:
    text = SELECTION_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert f"def {name}" in text
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert f"def {name}" not in host_text
    lowered = text.lower()
    assert "def _populate_editor(" not in text
    assert "def _refresh_inventory" not in text
    assert "shopify" not in lowered
    assert "persist" not in lowered or "preserved_selection" in lowered
