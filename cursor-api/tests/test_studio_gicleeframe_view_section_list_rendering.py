"""Boundary tests for the extracted GICLÉE FRAME section list rendering subsystem."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import customtkinter as ctk
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.ui import gicleeframe_view_section_list_rendering as rendering_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_page_readiness import (
    GicleeFramePageReadinessMixin,
)
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_readiness_row import (
    GicleeFrameReadinessRowMixin,
)
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
    _GF_SECTION_BATCH_DELAY_MS,
    _GF_SECTION_BATCH_SIZE,
    _SECTION_ROW_GRIP,
    _SECTION_ROW_HEIGHT,
)
from giclee_app.ui.gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
    _GF_SECTION_FIRST_BATCH_SIZE,
    _SECTION_PLACEHOLDER,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)
from giclee_app.ui.gicleeframe_view_page_context import GicleeFramePageContextMixin
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
RENDERING_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"

_EXPECTED_METHODS = {
    "_render_section_list",
    "_render_full_list_chunk",
    "_render_section_list_incremental",
    "_render_section_list_batch",
    "_schedule_section_list_batch_continuation",
    "_create_section_list_row",
    "_build_section_row",
    "_render_section_menu",
}

_HOST_OWNERSHIP = {
    "__init__",
    "_finalize_full_list_render",
    "_rebuild_page_model_cache",
    "_try_mark_progressive_full_ready",
    "_log_visual_gate_ready",
    "_try_mark_perceived_ready",
    "_schedule_atomic_reveal_check",
    "_since_visual_enter_ms",
    "_queue_latency_since_ms",
    "_upgrade_section_list_scroll",
    "_schedule_section_list_incremental",
    "_run_deferred_bootstrap",
}

_PAGE_CONTEXT_ADAPTER = {
    "_precompute_page_context_specs_cache",
}


class _FakeWidget:
    def __init__(self) -> None:
        self.children: list[Any] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.bind_calls: list[tuple[str, Any]] = []
        self.configure_calls: list[dict[str, Any]] = []
        self.pack_propagate_calls: list[bool] = []
        self._exists = True

    def winfo_children(self) -> list[Any]:
        return list(self.children)

    def winfo_exists(self) -> bool:
        return self._exists

    def pack(self, **kwargs: Any) -> None:
        self.pack_calls.append(dict(kwargs))

    def pack_propagate(self, value: bool) -> None:
        self.pack_propagate_calls.append(value)

    def destroy(self) -> None:
        self._exists = False

    def bind(self, sequence: str, callback: Any) -> None:
        self.bind_calls.append((sequence, callback))

    def configure(self, **kwargs: Any) -> None:
        self.configure_calls.append(dict(kwargs))


class _SectionListRenderingHarness(GicleeFrameSectionListRenderingMixin):
    def __init__(self) -> None:
        self._section_list_scroll: _FakeWidget | None = None
        self._merged: list[Any] = []
        self._merged_by_id: dict[str, Any] = {}
        self._selected_id: str | None = None
        self._section_row_frames: dict[str, Any] = {}
        self._section_row_ids: list[str] = []
        self._highlighted_section_id: str | None = None
        self._full_list_render_generation = 0
        self._section_dropdown_options_cache: list[Any] = []
        self._section_tree_rows_cache: list[Any] = []
        self._section_list_incremental_enter_mono = 0.0
        self._section_list_incremental_scheduled_mono = 0.0
        self._section_list_first_visible_built = False
        self._progressive_section_list_complete = False
        self._section_list_batch_after_id: str | None = None
        self._after_calls: list[tuple[int, Any]] = []
        self._after_idle_calls: list[Any] = []
        self._after_cancel_calls: list[Any] = []
        self._rebuild_cache_calls = 0
        self._finalize_calls: list[tuple[Any, float]] = []
        self._defer_calls: list[dict[str, Any]] = []
        self._visual_gate_calls: list[dict[str, Any]] = []
        self._perceived_ready_calls: list[str] = []
        self._atomic_reveal_calls: list[str] = []
        self._progressive_full_ready_calls = 0
        self._placeholder_calls = 0
        self._precompute_calls = 0
        self._trigger_update_calls = 0
        self._click_calls: list[str] = []
        self._drag_start_calls: list[int] = []
        self._drag_finish_calls = 0
        self._cancel_continuation_calls = 0
        self._render_list_calls = 0
        self._create_row_calls: list[dict[str, Any]] = []
        self._build_row_calls: list[tuple[int, str, str]] = []
        self._batch_calls: list[tuple[Any, int]] = []

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_calls.append((delay_ms, callback))
        return f"after-{len(self._after_calls)}"

    def after_idle(self, callback: Any) -> None:
        self._after_idle_calls.append(callback)

    def after_cancel(self, after_id: Any) -> None:
        self._after_cancel_calls.append(after_id)

    def winfo_exists(self) -> bool:
        return True

    def _rebuild_page_model_cache(self) -> None:
        self._rebuild_cache_calls += 1

    def _finalize_full_list_render(
        self,
        options: list[Any],
        batch_started: float,
    ) -> None:
        self._finalize_calls.append((options, batch_started))

    def _defer_background_for_selection(
        self,
        *,
        job: str,
        reason: str,
        callback: Any,
    ) -> bool:
        self._defer_calls.append(
            {"job": job, "reason": reason, "callback": callback},
        )
        return False

    def _since_visual_enter_ms(self) -> float:
        return 0.0

    def _queue_latency_since_ms(self, _mono: float) -> float:
        return 0.0

    def _log_visual_gate_ready(
        self,
        gate: str,
        *,
        source: str,
        since_scheduled_mono: float,
    ) -> None:
        self._visual_gate_calls.append(
            {
                "gate": gate,
                "source": source,
                "since_scheduled_mono": since_scheduled_mono,
            }
        )

    def _try_mark_perceived_ready(self, *, trigger: str) -> None:
        self._perceived_ready_calls.append(trigger)

    def _schedule_atomic_reveal_check(self, *, trigger: str) -> None:
        self._atomic_reveal_calls.append(trigger)

    def _try_mark_progressive_full_ready(self) -> None:
        self._progressive_full_ready_calls += 1

    def _show_editor_placeholder_state(self) -> None:
        self._placeholder_calls += 1

    def _precompute_page_context_specs_cache(self) -> None:
        self._precompute_calls += 1

    def _update_section_list_trigger(self) -> None:
        self._trigger_update_calls += 1

    def _on_section_row_click(self, element_id: str) -> None:
        self._click_calls.append(element_id)

    def _start_section_drag(self, index: int) -> None:
        self._drag_start_calls.append(index)

    def _finish_section_drag(self, _event: object) -> None:
        self._drag_finish_calls += 1

    def _cancel_section_list_batch_continuation(self) -> bool:
        self._cancel_continuation_calls += 1
        return True


def test_section_list_rendering_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameSectionListRenderingMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameSectionListRenderingMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameSectionListRenderingMixin.__dict__.items()
        if inspect.isfunction(value) and not name.startswith("__")
    }


def test_section_list_rendering_module_has_no_write_network_or_reverse_host_import() -> None:
    source = RENDERING_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("Komponenty") for name in imports)
    assert "giclee_app.ui.gicleeframe_view" not in imports
    for forbidden_import in ("pathlib", "requests", "shutil", "subprocess"):
        assert forbidden_import not in imports
    for forbidden_text in (
        "write_text",
        "open(",
        "filedialog",
        "shopify",
        "deploy",
    ):
        assert forbidden_text not in source.lower()
    assert "after(" in source
    assert "after_idle(" in source


def test_section_list_rendering_public_boundary_contract() -> None:
    assert "GicleeFrameSectionListRenderingMixin" in rendering_module.__all__
    assert "_SECTION_ROW_GRIP" in rendering_module.__all__
    assert "_SECTION_ROW_HEIGHT" in rendering_module.__all__
    assert "_GF_SECTION_BATCH_SIZE" in rendering_module.__all__
    assert "_GF_SECTION_BATCH_DELAY_MS" in rendering_module.__all__


def test_section_list_rendering_exact_constants() -> None:
    assert _SECTION_ROW_GRIP == "⋮"
    assert _SECTION_ROW_HEIGHT == 64
    assert _GF_SECTION_BATCH_SIZE == 8
    assert _GF_SECTION_BATCH_DELAY_MS == 0


def test_host_has_no_duplicate_renderer_constants() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in (
        "_SECTION_ROW_GRIP",
        "_SECTION_ROW_HEIGHT",
        "_GF_SECTION_BATCH_SIZE",
        "_GF_SECTION_BATCH_DELAY_MS",
    ):
        assert f"{name} =" not in host_text


def test_renderer_imports_shell_constants_without_duplication() -> None:
    rendering_text = RENDERING_PATH.read_text(encoding="utf-8")
    shell_text = SHELL_PATH.read_text(encoding="utf-8")
    assert "_GF_SECTION_FIRST_BATCH_SIZE" in rendering_text
    assert "_SECTION_PLACEHOLDER" in rendering_text
    assert "_GF_SECTION_FIRST_BATCH_SIZE =" not in rendering_text
    assert "_SECTION_PLACEHOLDER =" not in rendering_text
    assert _GF_SECTION_FIRST_BATCH_SIZE == 6
    assert _SECTION_PLACEHOLDER == "— wybierz sekcję —"
    assert f"_GF_SECTION_FIRST_BATCH_SIZE = {_GF_SECTION_FIRST_BATCH_SIZE}" in shell_text


def test_gicleeframe_view_has_fifteen_mixins_before_scrollable_frame() -> None:
    mro = GicleeFrameView.__mro__
    assert GicleeFrameBrandPanelMixin in mro
    assert GicleeFramePageReadinessMixin in mro
    assert GicleeFrameStructureDryRunMixin in mro
    assert GicleeFrameSafetyCardMixin in mro
    assert GicleeFrameReadinessRowMixin in mro
    assert GicleeFrameTopBarMixin in mro
    assert GicleeFrameRamVariantMixin in mro
    assert GicleeFrameSectionListShellMixin in mro
    assert GicleeFrameSectionListRenderingMixin in mro
    assert GicleeFrameSectionListInteractionMixin in mro
    assert GicleeFrameSelectionOrchestrationMixin in mro
    assert GicleeFrameEditorShellMixin in mro
    assert GicleeFrameDetailsOnDemandMixin in mro
    assert GicleeFrameVisualDetailRenderersMixin in mro
    assert mro.index(GicleeFrameSectionListShellMixin) < mro.index(
        GicleeFrameSectionListRenderingMixin,
    )
    assert mro.index(GicleeFrameSectionListRenderingMixin) < mro.index(
        GicleeFrameSectionListInteractionMixin,
    )
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
        ctk.CTkScrollableFrame,
    )


def test_section_list_rendering_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameSectionListRenderingMixin,
            name,
        )


def test_host_ownership_for_rendering_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name in GicleeFrameView.__dict__
    for name in _PAGE_CONTEXT_ADAPTER:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(GicleeFramePageContextMixin, name)


def test_render_section_list_noop_without_scroll() -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = None
    harness._render_section_list()
    assert harness._full_list_render_generation == 0


def test_render_section_list_empty_merged_renders_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    scroll = _FakeWidget()
    harness._section_list_scroll = scroll
    harness._merged = []
    pack_parents: list[Any] = []

    class _Label(_FakeWidget):
        def pack(self, **kwargs: Any) -> None:
            pack_parents.append(scroll)
            super().pack(**kwargs)

    monkeypatch.setattr(rendering_module.ctk, "CTkLabel", lambda *args, **kwargs: _Label())
    monkeypatch.setattr(rendering_module.theme, "get_font", lambda *_a, **_k: object())

    harness._render_section_list()

    assert harness._full_list_render_generation == 1
    assert pack_parents == [scroll]
    assert harness._finalize_calls == []


def test_render_section_list_populated_rebuilds_cache_and_starts_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    scroll = _FakeWidget()
    child = _FakeWidget()
    scroll.children.append(child)
    harness._section_list_scroll = scroll
    harness._merged = [SimpleNamespace(element_id="a")]
    harness._section_dropdown_options_cache = [
        SimpleNamespace(element_id="a", display_label="Alpha"),
    ]
    chunk_calls: list[tuple[Any, int, int, float]] = []

    def _chunk(options: Any, start: int, generation: int, batch_started: float) -> None:
        chunk_calls.append((options, start, generation, batch_started))

    monkeypatch.setattr(harness, "_render_full_list_chunk", _chunk)

    harness._render_section_list()

    assert child._exists is False
    assert harness._section_row_ids == []
    assert harness._rebuild_cache_calls == 1
    assert len(chunk_calls) == 1
    assert chunk_calls[0][1] == 0
    assert chunk_calls[0][2] == 1


def test_render_full_list_chunk_stale_generation_guard() -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    harness._full_list_render_generation = 2
    options = [SimpleNamespace(element_id="a", display_label="A")]

    harness._render_full_list_chunk(options, 0, generation=1, batch_started=0.0)

    assert harness._section_row_ids == []
    assert harness._finalize_calls == []


def test_render_full_list_chunk_continues_then_finalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    harness._full_list_render_generation = 1
    options = [
        SimpleNamespace(element_id=f"el-{idx}", display_label=f"Row {idx}")
        for idx in range(10)
    ]
    build_calls: list[tuple[int, str, str]] = []

    def _build(index: int, element_id: str, label: str) -> None:
        build_calls.append((index, element_id, label))

    monkeypatch.setattr(harness, "_build_section_row", _build)

    harness._render_full_list_chunk(options, 0, generation=1, batch_started=1.0)

    assert len(build_calls) == _GF_SECTION_BATCH_SIZE
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_SECTION_BATCH_DELAY_MS
    assert harness._finalize_calls == []

    harness._render_full_list_chunk(options, _GF_SECTION_BATCH_SIZE, generation=1, batch_started=1.0)

    assert len(build_calls) == 10
    assert len(harness._finalize_calls) == 1


def test_render_section_list_incremental_empty_path() -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    harness._merged = []

    harness._render_section_list_incremental()

    assert harness._progressive_section_list_complete
    assert harness._section_list_first_visible_built
    assert harness._visual_gate_calls[0]["source"] == "incremental_empty"
    assert harness._perceived_ready_calls == ["incremental_empty"]
    assert harness._progressive_full_ready_calls == 1


def test_render_section_list_incremental_selection_deferral() -> None:
    harness = _SectionListRenderingHarness()

    def _defer(**kwargs: Any) -> bool:
        harness._defer_calls.append(kwargs)
        return True

    harness._defer_background_for_selection = _defer  # type: ignore[method-assign]
    harness._section_list_scroll = _FakeWidget()
    harness._merged = [SimpleNamespace(element_id="a")]

    harness._render_section_list_incremental()

    assert len(harness._defer_calls) == 1
    assert harness._defer_calls[0]["job"] == "section_list.incremental"


def test_render_section_list_batch_first_vs_steady_batch_sizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    options = [
        SimpleNamespace(element_id=f"el-{idx}", display_label=f"Row {idx}")
        for idx in range(20)
    ]
    row_calls: list[int] = []

    def _row(idx: int, element_id: str, label: str) -> None:
        row_calls.append(idx)

    monkeypatch.setattr(harness, "_create_section_list_row", _row)

    harness._render_section_list_batch(options, 0)
    assert len(row_calls) == _GF_SECTION_FIRST_BATCH_SIZE
    assert len(harness._after_calls) == 1
    assert harness._cancel_continuation_calls == 1

    harness._render_section_list_batch(options, _GF_SECTION_FIRST_BATCH_SIZE)
    assert len(row_calls) == _GF_SECTION_FIRST_BATCH_SIZE + _GF_SECTION_BATCH_SIZE


def test_render_section_list_batch_first_visible_gate_order() -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    harness._section_list_first_visible_built = False
    options = [SimpleNamespace(element_id="a", display_label="A")]

    with patch.object(harness, "_create_section_list_row"):
        harness._render_section_list_batch(options, 0)

    assert harness._section_list_first_visible_built
    assert harness._visual_gate_calls[-1]["source"] == "incremental"
    assert harness._perceived_ready_calls == ["incremental_first_visible"]
    assert harness._atomic_reveal_calls == ["section_rows_first_visible"]


def test_render_section_list_batch_completion_adapters() -> None:
    harness = _SectionListRenderingHarness()
    harness._section_list_scroll = _FakeWidget()
    options = [SimpleNamespace(element_id="a", display_label="A")]

    with patch.object(harness, "_create_section_list_row"):
        harness._render_section_list_batch(options, 0)

    assert harness._selected_id is None
    assert harness._placeholder_calls == 1
    assert len(harness._after_idle_calls) == 1
    assert harness._after_idle_calls[0] == harness._precompute_page_context_specs_cache
    harness._after_idle_calls[0]()
    assert harness._precompute_calls == 1
    assert harness._trigger_update_calls == 1
    assert harness._progressive_section_list_complete
    assert harness._progressive_full_ready_calls == 1


def test_schedule_section_list_batch_continuation() -> None:
    harness = _SectionListRenderingHarness()
    options = [SimpleNamespace(element_id="a", display_label="A")]

    harness._schedule_section_list_batch_continuation(options, 8)

    assert harness._cancel_continuation_calls == 1
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_SECTION_BATCH_DELAY_MS


def test_create_section_list_row_static_vs_non_static_and_callbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    scroll = _FakeWidget()
    harness._section_list_scroll = scroll
    harness._merged = [SimpleNamespace(element_id="a", element_type="divider", section_key="s1")]

    created: list[_FakeWidget] = []

    def _frame(*_args: Any, **_kwargs: Any) -> _FakeWidget:
        widget = _FakeWidget()
        created.append(widget)
        return widget

    def _label(*_args: Any, **_kwargs: Any) -> _FakeWidget:
        widget = _FakeWidget()
        created.append(widget)
        return widget

    monkeypatch.setattr(rendering_module.ctk, "CTkFrame", _frame)
    monkeypatch.setattr(rendering_module.ctk, "CTkLabel", _label)
    monkeypatch.setattr(rendering_module.theme, "get_font", lambda *_a, **_k: object())
    monkeypatch.setattr(
        rendering_module,
        "_section_kind_copy",
        lambda _eid, _merged: "divider",
    )

    harness._create_section_list_row(0, "a", "Alpha", static_lane=True)
    static_grip_binds = [
        bind for widget in created for bind in widget.bind_calls if bind[0] == "<ButtonPress-1>"
    ]
    assert static_grip_binds == []

    harness._create_section_list_row(1, "b", "Beta", static_lane=False)
    non_static_grip_binds = [
        bind
        for widget in created
        for bind in widget.bind_calls
        if bind[0] in ("<ButtonPress-1>", "<ButtonRelease-1>")
    ]
    assert non_static_grip_binds

    click_callbacks = [
        bind[1]
        for widget in created
        for bind in widget.bind_calls
        if bind[0] == "<Button-1>"
    ]
    assert click_callbacks
    click_callbacks[0](None)
    assert harness._click_calls


def test_build_section_row_and_render_section_menu_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _SectionListRenderingHarness()
    create_calls: list[tuple[int, str, str]] = []

    def _create(index: int, element_id: str, label: str) -> None:
        create_calls.append((index, element_id, label))

    render_calls = 0

    def _render() -> None:
        nonlocal render_calls
        render_calls += 1

    monkeypatch.setattr(harness, "_create_section_list_row", _create)
    monkeypatch.setattr(harness, "_render_section_list", _render)

    harness._build_section_row(2, "x", "Label")
    harness._render_section_menu()

    assert create_calls == [(2, "x", "Label")]
    assert render_calls == 1
