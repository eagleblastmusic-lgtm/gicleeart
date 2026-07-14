"""Boundary tests for the extracted GICLÉE FRAME details-on-demand subsystem."""

from __future__ import annotations

import ast
import re
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

from giclee_app.studio.gicleeframe_page_draft import (
    EditorFieldVisibility,
    MergedPageElement,
    editor_field_visibility,
)
from giclee_app.ui import gicleeframe_view_details_on_demand as details_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
    _GF_DETAILS_CACHE_HIT_STATUS,
    _GF_DETAILS_CHILDREN_BATCH_SIZE,
    _GF_DETAILS_CONTAINER_HEIGHT,
    _GF_DETAILS_MODULE_CHILDREN_BUTTON,
    _GF_DETAILS_MODULE_CHILDREN_TITLE,
    _GF_DETAILS_MODULE_IDLE_STATUS,
    _GF_DETAILS_MODULE_LAYER_NAV_BUTTON,
    _GF_DETAILS_MODULE_LAYER_NAV_TITLE,
    _GF_DETAILS_MODULE_LOADED_STATUS,
    _GF_DETAILS_MODULE_LOADING_STATUS,
    _GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON,
    _GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE,
    _GF_DETAILS_MODULE_PREVIEW_BUTTON,
    _GF_DETAILS_MODULE_PREVIEW_TITLE,
    _GF_DETAILS_ON_DEMAND_BUTTON,
    _GF_DETAILS_ON_DEMAND_LOADING_TEXT,
    _GF_DETAILS_ON_DEMAND_TEXT,
    _GF_DETAILS_SHELL_SUBTEXT,
    _GF_DETAILS_SHELL_TITLE,
    _GF_DETAILS_STAGE_GAP_MS,
    _GF_MEDIA_CHILDREN_AFTER_SHELL_MS,
    _GF_MEDIA_DETAILS_ON_DEMAND_BUTTON,
    _GF_MEDIA_DETAILS_ON_DEMAND_TEXT,
    _GF_MEDIA_DETAILS_SHELL_SUBTEXT,
    _GF_MEDIA_DETAILS_STABLE_HEIGHT,
    _GF_MEDIA_DETAILS_STATUS_TEXT,
    _GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS,
    _GF_MEDIA_PREVIEW_AFTER_SHELL_MS,
    _GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS,
    _GF_SELECTION_CHILDREN_DEFER_MS,
    _GF_SELECTION_CHILDREN_LATE_DEFER_MS,
    _GF_SELECTION_LAYER_NAV_DEFER_MS,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)
from giclee_app.ui.gicleeframe_view_page_context import GicleeFramePageContextMixin
from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
)
from giclee_app.ui.gicleeframe_view_models import SectionVisualCacheEntry
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
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
DETAILS_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_details_on_demand.py"
DETAILS_PATCH = "giclee_app.ui.gicleeframe_view_details_on_demand"

_EXPECTED_METHODS = {
    "_since_details_request_ms",
    "_since_details_cta_ms",
    "_log_perf_e_update_done",
    "_ensure_media_details_stable_shell",
    "_hide_media_details_stable_shell",
    "_details_cache_entry",
    "_any_details_module_cached",
    "_details_module_cache_hit",
    "_cached_details_modules",
    "_full_visual_cache_entry",
    "_apply_cached_page_context_summary",
    "_apply_cached_preview_module",
    "_apply_cached_page_context_module",
    "_apply_cached_layer_nav_module",
    "_apply_cached_children_module",
    "_apply_cached_media_details",
    "_ensure_details_on_demand_block_built",
    "_hide_details_on_demand_block",
    "_show_details_on_demand_block",
    "_on_details_on_demand_clicked",
    "_ensure_details_shell_built",
    "_show_details_shell",
    "_hide_details_shell",
    "_hide_details_container",
    "_update_details_module_status",
    "_on_details_module_clicked",
    "_apply_details_module_from_cache",
    "_execute_details_module",
    "_run_children_details_module_batched",
    "_save_details_module_cache",
    "_apply_details_cache_hit",
    "_apply_heavy_details_on_demand",
    "_details_stage_still_valid",
    "_details_on_demand_stages_for",
    "_begin_details_on_demand_stages",
    "_schedule_next_details_stage",
    "_execute_details_on_demand_stage",
    "_run_children_details_stage_batched",
    "_finalize_details_on_demand",
    "_cancel_details_on_demand_jobs",
    "_schedule_details_on_demand_job",
    "_save_section_visual_cache",
    "_should_defer_editor_detail_populate",
    "_populate_editor_preview_deferred",
    "_populate_editor_layer_nav_deferred",
    "_populate_editor_children_deferred",
    "_schedule_media_deferred_details",
    "_populate_editor_media_details_batch",
}

_DETAILS_CONSTANTS = (
    "_GF_DETAILS_ON_DEMAND_TEXT",
    "_GF_DETAILS_ON_DEMAND_BUTTON",
    "_GF_MEDIA_DETAILS_ON_DEMAND_TEXT",
    "_GF_MEDIA_DETAILS_ON_DEMAND_BUTTON",
    "_GF_DETAILS_ON_DEMAND_LOADING_TEXT",
    "_GF_DETAILS_SHELL_TITLE",
    "_GF_DETAILS_SHELL_SUBTEXT",
    "_GF_MEDIA_DETAILS_SHELL_SUBTEXT",
    "_GF_DETAILS_CACHE_HIT_STATUS",
    "_GF_DETAILS_MODULE_PREVIEW_TITLE",
    "_GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE",
    "_GF_DETAILS_MODULE_LAYER_NAV_TITLE",
    "_GF_DETAILS_MODULE_CHILDREN_TITLE",
    "_GF_DETAILS_MODULE_PREVIEW_BUTTON",
    "_GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON",
    "_GF_DETAILS_MODULE_LAYER_NAV_BUTTON",
    "_GF_DETAILS_MODULE_CHILDREN_BUTTON",
    "_GF_DETAILS_MODULE_IDLE_STATUS",
    "_GF_DETAILS_MODULE_LOADED_STATUS",
    "_GF_DETAILS_MODULE_LOADING_STATUS",
    "_GF_DETAILS_STAGE_GAP_MS",
    "_GF_DETAILS_CHILDREN_BATCH_SIZE",
    "_GF_DETAILS_CONTAINER_HEIGHT",
    "_GF_MEDIA_PREVIEW_AFTER_SHELL_MS",
    "_GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS",
    "_GF_MEDIA_CHILDREN_AFTER_SHELL_MS",
    "_GF_MEDIA_DETAILS_STATUS_TEXT",
    "_GF_MEDIA_DETAILS_STABLE_HEIGHT",
    "_GF_SELECTION_LAYER_NAV_DEFER_MS",
    "_GF_SELECTION_CHILDREN_DEFER_MS",
    "_GF_SELECTION_CHILDREN_LATE_DEFER_MS",
    "_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS",
)

_VISUAL_RENDERER_METHODS = {
    "_update_section_preview",
    "_update_layer_nav",
    "_fill_children_overview_buttons",
    "_fill_children_overview_buttons_range",
    "_ensure_preview_structure",
    "_show_preview_frame",
    "_preview_key_for_element",
    "_get_or_create_layer_nav_header",
    "_get_or_create_layer_nav_row",
    "_update_layer_nav_tile",
    "_sync_layer_nav_visibility",
    "_selected_layer_items",
}

_HOST_PAGE_CONTEXT_RENDERER_EXCLUSIONS = {
    "_fill_page_context",
    "_hide_page_context_rows",
    "_clear_page_context_loading_label",
    "_page_context_pack_kwargs",
    "_get_or_create_readonly_card",
    "_show_page_context_row",
    "_get_or_create_page_context_row",
    "_page_context_shell_summary_lines",
    "_populate_page_context_batch",
    "_populate_page_context_group_batch",
    "_populate_page_context_progressive",
    "_populate_page_context_progressive_stable",
}

_HOST_RENDERER_EXCLUSIONS = _VISUAL_RENDERER_METHODS | _HOST_PAGE_CONTEXT_RENDERER_EXCLUSIONS


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}("
    assert marker in text, name
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _host_defines_constant(name: str, host_text: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(name)}\s*=", host_text, re.MULTILINE))


def _host_defines_method(name: str, host_text: str) -> bool:
    return f"def {name}(" in host_text


def _sample_merged(
    element_id: str,
    *,
    element_type: str = "media_section",
    section_key: str = "section-1",
    **overrides: Any,
) -> MergedPageElement:
    base = dict(
        element_id=element_id,
        section_key=section_key,
        element_type=element_type,
        group="content",
        order=1,
        label="Label",
        title="Title",
        text="Body text",
        image_ref="img.png",
        alt="Alt text",
        notes="Notes",
        editable=True,
        source="inventory",
        status="ok",
        has_draft_patch=False,
        visible=True,
        page_settings=(),
        page_fields=(),
    )
    base.update(overrides)
    return MergedPageElement(**base)


def _sample_cache_entry(
    element_id: str = "elem-a",
    *,
    element_type: str = "media_section",
    **overrides: Any,
) -> SectionVisualCacheEntry:
    base = dict(
        element_type=element_type,
        status="ok",
        has_draft_patch=False,
        title="Cached title",
        text="Cached text",
        alt="Cached alt",
        image_ref="cached.png",
        notes="Cached notes",
        visible=True,
        subtitle_text="Cached subtitle",
        page_context_summary=(("Key", "Value"),),
        fields_title=True,
        fields_text=True,
        fields_alt=False,
        fields_image_ref=False,
        fields_notes=True,
        fields_visible=True,
        fields_children=False,
        fields_page_context=True,
        media_details_built=False,
        preview_key="preview-1",
        layer_nav_visible=False,
        layer_nav_titles=(),
    )
    base.update(overrides)
    return SectionVisualCacheEntry(**base)


class _FakePackable:
    tk = object()

    def __init__(self, *, master: Any | None = None, text: str = "") -> None:
        self.master = master
        self._text = text
        self.configure_calls: list[dict[str, Any]] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.pack_forget_calls = 0
        self.grid_calls: list[dict[str, Any]] = []
        self.destroy_calls = 0
        self._managed = False

    def configure(self, **kwargs: Any) -> None:
        if "text" in kwargs:
            self._text = kwargs["text"]
        self.configure_calls.append(dict(kwargs))

    def cget(self, key: str) -> Any:
        if key == "text":
            return self._text
        return ""

    def pack(self, **kwargs: Any) -> None:
        self._managed = True
        self.pack_calls.append(dict(kwargs))

    def pack_forget(self) -> None:
        self._managed = False
        self.pack_forget_calls += 1

    def pack_propagate(self, _flag: bool) -> None:
        return None

    def grid(self, **kwargs: Any) -> None:
        self.grid_calls.append(dict(kwargs))

    def destroy(self) -> None:
        self.destroy_calls += 1

    def winfo_manager(self) -> str:
        return "pack" if self._managed else ""

    def winfo_exists(self) -> bool:
        return True


def _patch_fake_ctk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.ctk.CTkFrame",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.ctk.CTkLabel",
        lambda *_a, **k: _FakePackable(text=k.get("text", "")),
    )
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.ctk.CTkButton",
        lambda *_a, **k: _FakePackable(text=k.get("text", "")),
    )
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.theme.get_font",
        lambda *_a, **_k: "Arial 10",
    )
    for name, value in (
        ("_GF_FIELD", "#111"),
        ("_GF_CARD_SOFT", "#222"),
        ("_GF_FIELD_HOVER", "#333"),
        ("_BTN_HEIGHT", 28),
    ):
        monkeypatch.setattr(details_module, name, value, raising=False)


class GicleeFrameDetailsOnDemandHarness(GicleeFrameDetailsOnDemandMixin):
    def __init__(self) -> None:
        self._identity_card: _FakePackable | None = _FakePackable()
        self._edit_panel: _FakePackable | None = _FakePackable()
        self._layer_nav_frame: _FakePackable | None = None
        self._section_preview_card: _FakePackable | None = None
        self._page_context_frame: _FakePackable | None = None
        self._page_context_inner: _FakePackable | None = None
        self._children_overview_row: _FakePackable | None = _FakePackable()
        self._editor_section_subtitle: _FakePackable | None = _FakePackable(text="Subtitle")
        self._media_details_stable_frame: _FakePackable | None = None
        self._media_details_status_label: _FakePackable | None = None
        self._media_details_stable_built = False
        self._details_on_demand_frame: _FakePackable | None = None
        self._details_on_demand_hint_label: _FakePackable | None = None
        self._details_on_demand_button: _FakePackable | None = None
        self._details_on_demand_status_label: _FakePackable | None = None
        self._details_on_demand_built = False
        self._details_on_demand_element_id: str | None = None
        self._details_on_demand_expanded = False
        self._details_on_demand_after_ids: list[str] = []
        self._details_on_demand_generation = 0
        self._details_on_demand_request_mono: float | None = None
        self._details_cta_click_mono: float | None = None
        self._details_on_demand_active_element_id: str | None = None
        self._details_container_frame: _FakePackable | None = None
        self._details_container_built = False
        self._details_container_title_label: _FakePackable | None = None
        self._details_container_subtext_label: _FakePackable | None = None
        self._details_module_rows: dict[str, _FakePackable] = {}
        self._details_module_buttons: dict[str, _FakePackable] = {}
        self._details_module_status_labels: dict[str, _FakePackable] = {}
        self._layer_nav_visible_keys: set[str] = set()
        self._media_deferred_done_after_id: str | None = None
        self._section_visual_cache: dict[str, SectionVisualCacheEntry] = {}
        self._selected_id: str | None = None
        self._merged_by_id: dict[str, MergedPageElement] = {}
        self._selection_generation = 0
        self._selection_visual_cache_applied = False
        self._editor_has_ready_content = False
        self._editor_last_ready_element_id: str | None = None
        self._atomic_swap_suppress_visible = False
        self._winfo_exists = True
        self._after_calls: list[tuple[int, Any]] = []
        self._after_cancel_calls: list[str] = []
        self._after_cancel_raises: set[str] = set()
        self._after_counter = 0
        self._since_selection_click_result: float | None = 5.0
        self._tree_rows: dict[str, SimpleNamespace] = {}
        self._merged_for_selection_result: MergedPageElement | None = None
        self._ensure_page_context_shell_calls = 0
        self._hide_page_context_rows_calls = 0
        self._clear_page_context_loading_calls = 0
        self._page_context_pack_kwargs_result = {"fill": "x"}
        self._readonly_card: _FakePackable | None = None
        self._page_context_rows: dict[str, tuple[_FakePackable, _FakePackable]] = {}
        self._ensure_preview_structure_calls: list[str] = []
        self._show_preview_frame_calls: list[str] = []
        self._show_heavy_editor_modules_calls = 0
        self._hide_heavy_editor_modules_calls = 0
        self._layer_nav_header: _FakePackable | None = None
        self._layer_nav_row: _FakePackable | None = None
        self._layer_nav_tile_calls: list[dict[str, Any]] = []
        self._sync_layer_nav_calls: list[list[str]] = []
        self._selected_layer_items_result: list[tuple[str, str, str]] = []
        self._set_row_visible_calls: list[tuple[Any, bool]] = []
        self._fill_children_calls: list[dict[str, Any]] = []
        self._fill_children_range_calls: list[dict[str, Any]] = []
        self._update_section_preview_calls: list[dict[str, Any]] = []
        self._fill_page_context_calls: list[dict[str, Any]] = []
        self._update_layer_nav_calls: list[dict[str, Any]] = []
        self._fields_from_cache_calls: list[SectionVisualCacheEntry] = []
        self._hide_editor_refresh_status_calls = 0
        self._mark_editor_content_ready_calls: list[MergedPageElement] = []
        self._preview_key_result = "preview-key"
        self._page_context_summary_lines: list[tuple[str, str]] = [("K", "V")]
        self._schedule_selection_job_calls: list[tuple[int, Any]] = []

    def winfo_exists(self) -> bool:
        return self._winfo_exists

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_counter += 1
        after_id = f"after-{self._after_counter}"
        self._after_calls.append((delay_ms, callback))
        return after_id

    def after_cancel(self, after_id: str) -> None:
        if after_id in self._after_cancel_raises:
            raise tk.TclError("invalid command name")
        self._after_cancel_calls.append(after_id)

    def _since_selection_click_ms(self) -> float | None:
        return self._since_selection_click_result

    def _ensure_page_context_shell_built(self) -> None:
        self._ensure_page_context_shell_calls += 1
        if self._page_context_frame is None:
            self._page_context_frame = _FakePackable()
            self._page_context_inner = _FakePackable()

    def _hide_page_context_rows(self) -> None:
        self._hide_page_context_rows_calls += 1

    def _clear_page_context_loading_label(self) -> None:
        self._clear_page_context_loading_calls += 1

    def _page_context_pack_kwargs(self) -> dict[str, Any]:
        return dict(self._page_context_pack_kwargs_result)

    def _get_or_create_readonly_card(self) -> _FakePackable:
        if self._readonly_card is None:
            self._readonly_card = _FakePackable()
        return self._readonly_card

    def _show_page_context_row(self, row_key: str, **kwargs: Any) -> None:
        _ = row_key, kwargs

    def _get_or_create_page_context_row(
        self,
        row_key: str,
        *,
        label: str,
        kind: str,
    ) -> tuple[_FakePackable, _FakePackable]:
        _ = kind
        if row_key not in self._page_context_rows:
            self._page_context_rows[row_key] = (_FakePackable(text=label), _FakePackable())
        return self._page_context_rows[row_key]

    def _ensure_preview_structure(self, preview_key: str) -> None:
        self._ensure_preview_structure_calls.append(preview_key)

    def _show_preview_frame(self, preview_key: str) -> None:
        self._show_preview_frame_calls.append(preview_key)

    def _show_heavy_editor_modules(self) -> None:
        self._show_heavy_editor_modules_calls += 1

    def _hide_heavy_editor_modules(self) -> None:
        self._hide_heavy_editor_modules_calls += 1

    def _get_or_create_layer_nav_header(self) -> _FakePackable:
        if self._layer_nav_header is None:
            self._layer_nav_header = _FakePackable()
        return self._layer_nav_header

    def _get_or_create_layer_nav_row(self) -> _FakePackable:
        if self._layer_nav_row is None:
            self._layer_nav_row = _FakePackable()
        return self._layer_nav_row

    def _update_layer_nav_tile(
        self,
        slot_key: str,
        *,
        kind: str,
        title: str,
        active: bool,
    ) -> None:
        self._layer_nav_tile_calls.append(
            {"slot_key": slot_key, "kind": kind, "title": title, "active": active},
        )

    def _sync_layer_nav_visibility(self, desired_keys: list[str]) -> None:
        self._sync_layer_nav_calls.append(list(desired_keys))

    def _selected_layer_items(self, m: MergedPageElement) -> list[tuple[str, str, str]]:
        _ = m
        return list(self._selected_layer_items_result)

    def _set_row_visible(self, row: Any, visible: bool) -> None:
        self._set_row_visible_calls.append((row, visible))

    def _fill_children_overview_buttons(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool,
    ) -> None:
        self._fill_children_calls.append({"element": m, "stale_refresh": stale_refresh})

    def _fill_children_overview_buttons_range(
        self,
        m: MergedPageElement,
        start: int,
        end: int,
        *,
        stale_refresh: bool,
    ) -> None:
        self._fill_children_range_calls.append(
            {"element": m, "start": start, "end": end, "stale_refresh": stale_refresh},
        )

    def _update_section_preview(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool,
    ) -> None:
        self._update_section_preview_calls.append(
            {"element": m, "stale_refresh": stale_refresh},
        )

    def _fill_page_context(self, m: MergedPageElement, *, show: bool) -> None:
        self._fill_page_context_calls.append({"element": m, "show": show})

    def _update_layer_nav(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool,
    ) -> None:
        self._update_layer_nav_calls.append(
            {"element": m, "stale_refresh": stale_refresh},
        )

    def _fields_from_cache_entry(
        self,
        entry: SectionVisualCacheEntry,
    ) -> EditorFieldVisibility:
        self._fields_from_cache_calls.append(entry)
        return editor_field_visibility(entry.element_type)

    def _hide_editor_refresh_status(self) -> None:
        self._hide_editor_refresh_status_calls += 1

    def _mark_editor_content_ready(self, m: MergedPageElement) -> None:
        self._mark_editor_content_ready_calls.append(m)
        self._editor_has_ready_content = True
        self._editor_last_ready_element_id = m.element_id

    def _preview_key_for_element(self, m: MergedPageElement) -> str:
        _ = m
        return self._preview_key_result

    def _page_context_shell_summary_lines(
        self,
        m: MergedPageElement,
    ) -> list[tuple[str, str]]:
        _ = m
        return list(self._page_context_summary_lines)

    def _tree_row_for_element(self, element_id: str) -> SimpleNamespace | None:
        return self._tree_rows.get(element_id)

    def _merged_for_selection_generation(
        self,
        element_id: str,
        generation: int,
        *,
        event_prefix: str,
    ) -> MergedPageElement | None:
        _ = element_id, generation, event_prefix
        return self._merged_for_selection_result

    def _schedule_selection_job(self, delay_ms: int, callback: Any) -> None:
        self._schedule_selection_job_calls.append((delay_ms, callback))


# --- Structural / contract tests ---


def test_details_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameDetailsOnDemandMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameDetailsOnDemandMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameDetailsOnDemandMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }
    assert len(_EXPECTED_METHODS) == 48


def test_details_module_has_no_write_network_or_reverse_host_import() -> None:
    source = DETAILS_PATH.read_text(encoding="utf-8")
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
    assert "urllib" not in lowered
    assert "requests" not in lowered


def test_details_public_boundary_contract() -> None:
    assert details_module.__all__ == (
        "GicleeFrameDetailsOnDemandMixin",
        *_DETAILS_CONSTANTS,
    )


def test_details_constants_exact_values() -> None:
    assert _GF_DETAILS_ON_DEMAND_TEXT == "Szczegóły sekcji są dostępne na żądanie."
    assert _GF_DETAILS_ON_DEMAND_BUTTON == "Pokaż szczegóły"
    assert _GF_MEDIA_DETAILS_ON_DEMAND_TEXT == (
        "Szczegóły mediów, warstwy i podgląd są dostępne na żądanie."
    )
    assert _GF_MEDIA_DETAILS_ON_DEMAND_BUTTON == "Pokaż szczegóły mediów"
    assert _GF_DETAILS_ON_DEMAND_LOADING_TEXT == "Ładowanie szczegółów…"
    assert _GF_DETAILS_SHELL_TITLE == "Szczegóły sekcji"
    assert _GF_DETAILS_SHELL_SUBTEXT == "Wybierz, które szczegóły chcesz wczytać."
    assert _GF_MEDIA_DETAILS_SHELL_SUBTEXT == (
        "Podgląd, warstwy i elementy mediów są dostępne osobno, "
        "żeby nie spowalniać edytora."
    )
    assert _GF_DETAILS_CACHE_HIT_STATUS == "Szczegóły załadowane"
    assert _GF_DETAILS_MODULE_PREVIEW_TITLE == "Podgląd"
    assert _GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE == "Ustawienia"
    assert _GF_DETAILS_MODULE_LAYER_NAV_TITLE == "Warstwy"
    assert _GF_DETAILS_MODULE_CHILDREN_TITLE == "Elementy"
    assert _GF_DETAILS_MODULE_PREVIEW_BUTTON == "Wczytaj podgląd"
    assert _GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON == "Wczytaj ustawienia"
    assert _GF_DETAILS_MODULE_LAYER_NAV_BUTTON == "Wczytaj warstwy"
    assert _GF_DETAILS_MODULE_CHILDREN_BUTTON == "Wczytaj elementy"
    assert _GF_DETAILS_MODULE_IDLE_STATUS == "—"
    assert _GF_DETAILS_MODULE_LOADED_STATUS == "Gotowe"
    assert _GF_DETAILS_MODULE_LOADING_STATUS == "Ładowanie…"
    assert _GF_DETAILS_STAGE_GAP_MS == 16
    assert _GF_DETAILS_CHILDREN_BATCH_SIZE == 2
    assert _GF_DETAILS_CONTAINER_HEIGHT == 148
    assert _GF_MEDIA_PREVIEW_AFTER_SHELL_MS == 20
    assert _GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS == 40
    assert _GF_MEDIA_CHILDREN_AFTER_SHELL_MS == 80
    assert _GF_MEDIA_DETAILS_STATUS_TEXT == "Szczegóły mediów zostaną zaktualizowane…"
    assert _GF_MEDIA_DETAILS_STABLE_HEIGHT == 88
    assert _GF_SELECTION_LAYER_NAV_DEFER_MS == 16
    assert _GF_SELECTION_CHILDREN_DEFER_MS == 32
    assert _GF_SELECTION_CHILDREN_LATE_DEFER_MS == 80
    assert _GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS == 16
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _DETAILS_CONSTANTS:
        assert not _host_defines_constant(name, host_text), name


def test_gicleeframe_view_has_sixteen_mixins_before_scrollable_frame() -> None:
    expected = (
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
        ctk.CTkScrollableFrame,
    )
    assert GicleeFrameView.__mro__[1 : 1 + len(expected)] == expected


def test_details_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameDetailsOnDemandMixin,
            name,
        )


def test_host_ownership_for_excluded_renderer_methods() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _VISUAL_RENDERER_METHODS:
        assert name not in GicleeFrameDetailsOnDemandMixin.__dict__
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameVisualDetailRenderersMixin,
            name,
        )
    for name in _HOST_PAGE_CONTEXT_RENDERER_EXCLUSIONS:
        assert name not in GicleeFrameDetailsOnDemandMixin.__dict__
        assert not _host_defines_method(name, host_text), name
        assert getattr(GicleeFrameView, name) is getattr(GicleeFramePageContextMixin, name)


def test_details_source_ownership_in_module() -> None:
    text = DETAILS_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert _host_defines_method(name, text), name
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert not _host_defines_method(name, host_text), name


def test_details_module_does_not_implement_renderer_engines() -> None:
    text = DETAILS_PATH.read_text(encoding="utf-8")
    for name in _HOST_RENDERER_EXCLUSIONS:
        assert f"def {name}(" not in text, name


# --- Timing ---


def test_since_details_request_ms_none_and_elapsed() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    assert harness._since_details_request_ms() is None
    harness._details_on_demand_request_mono = time.perf_counter() - 0.05
    elapsed = harness._since_details_request_ms()
    assert elapsed is not None
    assert elapsed >= 40.0


def test_since_details_cta_ms_none_and_elapsed() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    assert harness._since_details_cta_ms() is None
    harness._details_cta_click_mono = time.perf_counter() - 0.02
    elapsed = harness._since_details_cta_ms()
    assert elapsed is not None
    assert elapsed >= 10.0


def test_log_perf_e_update_done_delegates_to_log_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    started = time.perf_counter()
    harness._log_perf_e_update_done(
        "preview",
        element_type="media_section",
        started=started,
    )
    assert events[0][0] == "studio.gicleeframe.preview.update.done"
    assert events[0][1]["element_type"] == "media_section"
    assert events[0][1]["since_click_ms"] == 5.0


# --- Stable shell ---


def test_ensure_media_details_stable_shell_builds_and_packs_before_layer_nav(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._layer_nav_frame = _FakePackable()
    harness._layer_nav_frame._managed = True
    _patch_fake_ctk(monkeypatch)
    harness._ensure_media_details_stable_shell()
    assert harness._media_details_stable_built is True
    assert harness._media_details_stable_frame is not None
    assert harness._media_details_stable_frame.pack_calls
    assert harness._media_details_stable_frame.pack_calls[0].get("before") is harness._layer_nav_frame


def test_ensure_media_details_stable_shell_suppressed_when_atomic_swap() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._atomic_swap_suppress_visible = True
    harness._ensure_media_details_stable_shell()
    assert harness._media_details_stable_built is False


def test_hide_media_details_stable_shell_forgets_frame() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    frame = _FakePackable()
    frame._managed = True
    harness._media_details_stable_frame = frame
    harness._hide_media_details_stable_shell()
    assert frame.pack_forget_calls == 1


# --- Cache helpers ---


def test_details_cache_entry_and_module_cache_helpers() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    empty_entry = _sample_cache_entry()
    assert harness._details_cache_entry(element) is None
    assert harness._any_details_module_cached(empty_entry) is False
    assert harness._details_module_cache_hit(empty_entry, "preview") is False
    assert harness._full_visual_cache_entry(element) is None

    cached = _sample_cache_entry(
        details_cache_preview=True,
        details_cache_page_context=True,
        details_cache_layer_nav=True,
        details_cache_children=True,
    )
    harness._section_visual_cache = {"a": cached}
    assert harness._details_cache_entry(element) is cached
    assert harness._any_details_module_cached(cached) is True
    assert harness._details_module_cache_hit(cached, "preview") is True
    assert harness._details_module_cache_hit(cached, "missing") is False

    media_only = _sample_cache_entry(media_details_built=True)
    harness._section_visual_cache = {"a": media_only}
    assert harness._details_cache_entry(element) is media_only


def test_cached_details_modules_preserves_order() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    entry = _sample_cache_entry(
        details_cache_children=True,
        details_cache_preview=True,
        details_cache_layer_nav=True,
        details_cache_page_context=True,
    )
    assert harness._cached_details_modules(entry) == [
        "preview",
        "page_context",
        "layer_nav",
        "children",
    ]


# --- Cached module adapters ---


def test_apply_cached_preview_module_delegates_to_host() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    entry = _sample_cache_entry(details_cache_preview=True, preview_key="pk-1")
    harness._apply_cached_preview_module(entry)
    assert harness._ensure_preview_structure_calls == ["pk-1"]
    assert harness._show_preview_frame_calls == ["pk-1"]
    assert harness._show_heavy_editor_modules_calls == 1


def test_apply_cached_page_context_module_delegates_summary() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    entry = _sample_cache_entry(details_cache_page_context=True)
    harness._apply_cached_page_context_module(entry)
    assert harness._ensure_page_context_shell_calls == 1


def test_apply_cached_layer_nav_module_delegates_to_host() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._layer_nav_frame = _FakePackable()
    entry = _sample_cache_entry(
        details_cache_layer_nav=True,
        layer_nav_visible=True,
        layer_nav_titles=("Root", "Child"),
    )
    harness._apply_cached_layer_nav_module(entry)
    assert len(harness._layer_nav_tile_calls) == 2
    assert harness._sync_layer_nav_calls == [["slot:0", "slot:1"]]


def test_apply_cached_children_module_delegates_to_host() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="section")
    entry = _sample_cache_entry(details_cache_children=True, fields_children=True)
    harness._apply_cached_children_module(element, entry)
    assert harness._set_row_visible_calls == [(harness._children_overview_row, True)]
    assert len(harness._fill_children_calls) == 1


def test_apply_cached_media_details_runs_preview_and_hides_stable_shell() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    entry = _sample_cache_entry(details_cache_preview=True, preview_key="pk")
    harness._media_details_stable_frame = _FakePackable()
    harness._media_details_stable_frame._managed = True
    harness._apply_cached_media_details(entry)
    assert harness._ensure_preview_structure_calls == ["pk"]
    assert harness._media_details_stable_frame.pack_forget_calls == 1


# --- Availability CTA ---


def test_ensure_details_on_demand_block_built_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    harness._ensure_details_on_demand_block_built()
    first = harness._details_on_demand_frame
    harness._ensure_details_on_demand_block_built()
    assert harness._details_on_demand_frame is first
    assert harness._details_on_demand_built is True


def test_show_details_on_demand_block_media_copy_and_cache_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._section_preview_card = _FakePackable()
    _patch_fake_ctk(monkeypatch)
    element = _sample_merged("media-1", element_type="media_section")
    cached = _sample_cache_entry(
        details_cache_preview=True,
        details_cache_page_context=True,
    )
    harness._section_visual_cache = {"media-1": cached}
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._show_details_on_demand_block(element)
    assert harness._details_on_demand_hint_label is not None
    assert harness._details_on_demand_hint_label._text == _GF_MEDIA_DETAILS_ON_DEMAND_TEXT
    assert harness._details_on_demand_button is not None
    assert harness._details_on_demand_button._text == _GF_MEDIA_DETAILS_ON_DEMAND_BUTTON
    assert harness._details_on_demand_status_label is not None
    assert "2 moduł(y)" in harness._details_on_demand_status_label._text
    assert events[-1][0] == "studio.gicleeframe.details_on_demand.available"
    assert events[-1][1]["details_cached"] is True


def test_show_details_on_demand_block_section_copy_without_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    element = _sample_merged("sec-1", element_type="section")
    harness._show_details_on_demand_block(element)
    assert harness._details_on_demand_hint_label is not None
    assert harness._details_on_demand_hint_label._text == _GF_DETAILS_ON_DEMAND_TEXT
    assert harness._details_on_demand_button is not None
    assert harness._details_on_demand_button._text == _GF_DETAILS_ON_DEMAND_BUTTON


def test_hide_details_on_demand_block_clears_status() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    frame = _FakePackable()
    frame._managed = True
    label = _FakePackable(text="status")
    harness._details_on_demand_frame = frame
    harness._details_on_demand_status_label = label
    harness._hide_details_on_demand_block()
    assert frame.pack_forget_calls == 1
    assert label._text == ""


def test_show_details_on_demand_block_expanded_hides() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._details_on_demand_expanded = True
    harness._details_on_demand_frame = _FakePackable()
    harness._details_on_demand_frame._managed = True
    element = _sample_merged("a")
    harness._show_details_on_demand_block(element)
    assert harness._details_on_demand_frame.pack_forget_calls == 1


# --- CTA click ---


def test_on_details_on_demand_clicked_guards_missing_selection() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._on_details_on_demand_clicked()
    assert harness._details_on_demand_generation == 0


def test_on_details_on_demand_clicked_generation_cancel_and_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_element_id = "a"
    harness._details_on_demand_after_ids = ["job-1"]
    _patch_fake_ctk(monkeypatch)
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._on_details_on_demand_clicked()
    assert harness._details_on_demand_generation == 1
    assert harness._details_on_demand_expanded is True
    assert harness._after_cancel_calls == ["job-1"]
    assert events[:3] == [
        "studio.gicleeframe.details_on_demand.requested",
        "studio.gicleeframe.details_on_demand.full_auto_suppressed",
        "studio.gicleeframe.details_shell.requested",
    ]
    assert events[-3:] == [
        "studio.gicleeframe.details_shell.ready",
        "studio.gicleeframe.details_shell.applied",
        "studio.gicleeframe.details_on_demand.applied",
    ]


# --- Details shell ---


def test_ensure_details_shell_built_idempotent_with_four_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    harness._ensure_details_shell_built()
    first = harness._details_container_frame
    assert set(harness._details_module_rows) == {
        "preview",
        "page_context",
        "layer_nav",
        "children",
    }
    harness._ensure_details_shell_built()
    assert harness._details_container_frame is first


def test_show_details_shell_visibility_and_cached_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    harness._ensure_details_shell_built()
    element = _sample_merged("legacy", element_type="section_legacy")
    harness._section_visual_cache = {
        "legacy": _sample_cache_entry(
            element_type="section_legacy",
            details_cache_preview=True,
        ),
    }
    harness._show_details_shell(element)
    assert harness._details_module_status_labels["preview"]._text == _GF_DETAILS_MODULE_LOADED_STATUS
    assert harness._details_module_status_labels["page_context"]._text == _GF_DETAILS_MODULE_IDLE_STATUS


def test_show_details_shell_media_subtext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    harness._ensure_details_shell_built()
    element = _sample_merged("m", element_type="media_section")
    harness._show_details_shell(element)
    assert harness._details_container_subtext_label is not None
    assert harness._details_container_subtext_label._text == _GF_MEDIA_DETAILS_SHELL_SUBTEXT


def test_hide_details_shell_and_legacy_alias() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    frame = _FakePackable()
    frame._managed = True
    harness._details_container_frame = frame
    harness._hide_details_shell()
    assert frame.pack_forget_calls == 1
    frame.pack_forget_calls = 0
    harness._hide_details_container()
    assert frame.pack_forget_calls == 1


def test_update_details_module_status_empty_uses_loaded() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    label = _FakePackable()
    harness._details_module_status_labels["preview"] = label
    harness._update_details_module_status("preview", "")
    assert label._text == _GF_DETAILS_MODULE_LOADED_STATUS


# --- Module click and execution ---


def test_on_details_module_clicked_guard_wrong_selection() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._selected_id = "other"
    harness._details_on_demand_active_element_id = "a"
    harness._merged_by_id = {"a": _sample_merged("a")}
    harness._on_details_module_clicked("preview")
    assert harness._after_calls == []


def test_on_details_module_clicked_cache_hit_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._section_visual_cache = {
        "a": _sample_cache_entry(details_cache_preview=True, preview_key="pk"),
    }
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._on_details_module_clicked("preview")
    assert "studio.gicleeframe.details_module.cache_hit" in events
    assert harness._ensure_preview_structure_calls == ["pk"]
    assert "studio.gicleeframe.details_module.applied" in events


def test_on_details_module_clicked_schedules_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    _patch_fake_ctk(monkeypatch)
    harness._ensure_details_shell_built()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._on_details_module_clicked("preview")
    assert events[0] == "studio.gicleeframe.details_module.requested"
    assert harness._details_module_status_labels["preview"]._text == _GF_DETAILS_MODULE_LOADING_STATUS
    assert harness._after_calls[0][0] == 0


def test_execute_details_module_all_four_types() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="section")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1

    for module in ("preview", "page_context", "layer_nav", "children"):
        harness._execute_details_module("a", 1, module)

    assert len(harness._update_section_preview_calls) == 1
    assert len(harness._fill_page_context_calls) == 1
    assert len(harness._update_layer_nav_calls) == 1
    assert len(harness._fill_children_calls) == 1
    assert "a" in harness._section_visual_cache


def test_run_children_details_module_batched_continuation_and_finalize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="section")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1
    harness._details_on_demand_request_mono = time.perf_counter()
    harness._tree_rows["a"] = SimpleNamespace(children=("c1", "c2", "c3"))
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._run_children_details_module_batched("a", 1, "children", start=0)
    assert len(harness._fill_children_range_calls) == 1
    assert harness._after_calls[0][0] == _GF_DETAILS_STAGE_GAP_MS
    harness._after_calls.clear()
    harness._run_children_details_module_batched("a", 1, "children", start=2)
    assert "studio.gicleeframe.details_module.applied" in events


def test_save_details_module_cache_preserves_previous_flags() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    existing = _sample_cache_entry(
        details_cache_preview=True,
        details_cache_page_context=True,
        preview_key="old-key",
        layer_nav_visible=True,
        layer_nav_titles=("A",),
    )
    harness._section_visual_cache = {"a": existing}
    fields = editor_field_visibility("section")
    harness._save_details_module_cache(element, "layer_nav", fields)
    saved = harness._section_visual_cache["a"]
    assert saved.details_cache_preview is True
    assert saved.details_cache_page_context is True
    assert saved.details_cache_layer_nav is True


# --- Full cache hit ---


def test_apply_details_cache_hit_full_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="section")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 2
    harness._details_cta_click_mono = time.perf_counter()
    harness._details_on_demand_request_mono = harness._details_cta_click_mono
    entry = _sample_cache_entry(
        details_cache_preview=True,
        details_cache_page_context=True,
        details_cache_layer_nav=True,
        fields_page_context=True,
        fields_children=True,
        preview_key="pk",
    )
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._apply_details_cache_hit(element, entry, 2)
    assert harness._details_on_demand_expanded is True
    assert harness._mark_editor_content_ready_calls == [element]
    assert events[-3:] == [
        "studio.gicleeframe.details_on_demand.ready",
        "studio.gicleeframe.details_on_demand.applied",
        "studio.gicleeframe.details_on_demand.all_done",
    ]


# --- Stale guards ---


def test_details_stage_still_valid_rejects_stale_generation() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._details_on_demand_generation = 2
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    assert harness._details_stage_still_valid("a", 1) is False


def test_details_stage_still_valid_rejects_selection_mismatch() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._details_on_demand_generation = 1
    harness._selected_id = "b"
    harness._details_on_demand_active_element_id = "a"
    assert harness._details_stage_still_valid("a", 1) is False


def test_details_stage_still_valid_rejects_destroyed_widget() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._details_on_demand_generation = 1
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._winfo_exists = False
    assert harness._details_stage_still_valid("a", 1) is False


# --- Legacy staged pipeline ---


def test_details_on_demand_stages_for_ordering() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    media = _sample_merged("m", element_type="media_section")
    assert harness._details_on_demand_stages_for(media) == [
        "summary",
        "preview",
        "page_context",
        "layer_nav",
        "children",
    ]
    legacy = _sample_merged("l", element_type="section_legacy")
    assert harness._details_on_demand_stages_for(legacy) == [
        "summary",
        "preview",
        "layer_nav",
    ]


def test_begin_details_on_demand_stages_schedules_first_stage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._begin_details_on_demand_stages("a", 1)
    assert harness._show_heavy_editor_modules_calls == 1
    assert "studio.gicleeframe.details_on_demand.stage_scheduled" in events
    assert harness._after_calls[0][0] == 0


def test_execute_details_on_demand_stage_preview_and_chain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1
    stages = ["summary", "preview"]
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda *_a, **_k: None,
    )
    harness._execute_details_on_demand_stage("a", 1, stages, 0, "summary")
    assert harness._after_calls[-1][0] == _GF_DETAILS_STAGE_GAP_MS


def test_run_children_details_stage_batched_continuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="section")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1
    harness._tree_rows["a"] = SimpleNamespace(children=("c1", "c2", "c3"))
    stages = ["summary", "preview", "children"]
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda *_a, **_k: None,
    )
    harness._run_children_details_stage_batched(
        element,
        1,
        stale_refresh=False,
        start=0,
        stages=stages,
        stage_index=2,
    )
    assert harness._after_calls[0][0] == _GF_DETAILS_STAGE_GAP_MS


def test_finalize_details_on_demand_ordering_and_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_by_id = {"a": element}
    harness._selected_id = "a"
    harness._details_on_demand_active_element_id = "a"
    harness._details_on_demand_generation = 1
    harness._details_on_demand_request_mono = time.perf_counter()
    harness._details_cta_click_mono = harness._details_on_demand_request_mono
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._finalize_details_on_demand("a", 1)
    assert harness._details_on_demand_expanded is True
    assert harness._hide_editor_refresh_status_calls == 1
    assert "a" in harness._section_visual_cache
    assert events[-3:] == [
        "studio.gicleeframe.details_on_demand.all_done",
        "studio.gicleeframe.details_on_demand.ready",
        "studio.gicleeframe.details_on_demand.applied",
    ]


# --- Scheduler ---


def test_cancel_details_on_demand_jobs_pop_before_cancel_and_tclerror() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._details_on_demand_after_ids = ["a", "b"]
    harness._after_cancel_raises.add("b")
    cancelled = harness._cancel_details_on_demand_jobs()
    assert cancelled == 2
    assert harness._after_cancel_calls == ["a"]
    assert harness._details_on_demand_after_ids == []


def test_schedule_details_on_demand_job_appends_after_id() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._schedule_details_on_demand_job(16, lambda: None)
    assert len(harness._details_on_demand_after_ids) == 1
    assert harness._after_calls[0][0] == 16


# --- Shared visual cache ---


def test_save_section_visual_cache_minimal_preserves_heavy_flags() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    existing = _sample_cache_entry(
        details_cache_preview=True,
        details_cache_layer_nav=True,
        media_details_built=True,
        preview_key="keep-key",
    )
    harness._section_visual_cache = {"a": existing}
    fields = editor_field_visibility("media_section")
    harness._save_section_visual_cache(element, fields, media_details_built=False)
    saved = harness._section_visual_cache["a"]
    assert saved.details_cache_preview is True
    assert saved.media_details_built is True
    assert saved.preview_key == "keep-key"


def test_save_section_visual_cache_full_sets_all_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._layer_nav_frame = _FakePackable()
    harness._layer_nav_frame._managed = True
    harness._selected_layer_items_result = [("id", "k", "Title")]
    element = _sample_merged("a", element_type="media_section")
    fields = editor_field_visibility("media_section")
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._save_section_visual_cache(element, fields, media_details_built=True)
    saved = harness._section_visual_cache["a"]
    assert saved.details_cache_preview is True
    assert saved.details_cache_layer_nav is True
    assert saved.media_details_built is True
    assert events[-1][1]["minimal_only"] is False


# --- Deferred wrappers ---


def test_should_defer_editor_detail_populate_always_true() -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    fields = editor_field_visibility("media_section")
    assert harness._should_defer_editor_detail_populate(element, fields) is True


def test_populate_editor_preview_deferred_delegates_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_for_selection_result = element
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    with patch(f"{DETAILS_PATCH}.span"):
        harness._populate_editor_preview_deferred("a", 0)
    assert len(harness._update_section_preview_calls) == 1
    assert "studio.gicleeframe.preview.update.done" in events


def test_populate_editor_layer_nav_deferred_delegates_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_for_selection_result = element
    monkeypatch.setattr(f"{DETAILS_PATCH}.log_event", lambda *_a, **_k: None)
    with patch(f"{DETAILS_PATCH}.span"):
        harness._populate_editor_layer_nav_deferred("a", 0)
    assert len(harness._update_layer_nav_calls) == 1


def test_populate_editor_children_deferred_delegates_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    harness._merged_for_selection_result = element
    monkeypatch.setattr(f"{DETAILS_PATCH}.log_event", lambda *_a, **_k: None)
    with patch(f"{DETAILS_PATCH}.span"):
        harness._populate_editor_children_deferred("a", 0)
    assert len(harness._fill_children_calls) == 1


def test_schedule_media_deferred_details_skips_when_cache_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    harness._selection_visual_cache_applied = True
    element = _sample_merged("a")
    harness._schedule_media_deferred_details(element, 0)
    assert harness._schedule_selection_job_calls == []


def test_schedule_media_deferred_details_schedules_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a")
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._schedule_media_deferred_details(element, harness._selection_generation)
    assert harness._schedule_selection_job_calls[0][0] == _GF_MEDIA_PREVIEW_AFTER_SHELL_MS
    assert events[0] == "studio.gicleeframe.media_deferred.scheduled"


def test_populate_editor_media_details_batch_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameDetailsOnDemandHarness()
    element = _sample_merged("a", element_type="media_section")
    harness._merged_for_selection_result = element
    order: list[str] = []

    def _preview(m: MergedPageElement, *, stale_refresh: bool) -> None:
        _ = stale_refresh
        order.append("preview")

    def _layer(m: MergedPageElement, *, stale_refresh: bool) -> None:
        _ = stale_refresh
        order.append("layer_nav")

    def _children(m: MergedPageElement, *, stale_refresh: bool) -> None:
        _ = stale_refresh
        order.append("children")

    harness._update_section_preview = _preview  # type: ignore[method-assign]
    harness._update_layer_nav = _layer  # type: ignore[method-assign]
    harness._fill_children_overview_buttons = _children  # type: ignore[method-assign]
    events: list[str] = []
    monkeypatch.setattr(
        f"{DETAILS_PATCH}.log_event",
        lambda event, **_k: events.append(event),
    )
    with patch(f"{DETAILS_PATCH}.span"):
        harness._populate_editor_media_details_batch("a", 3, started_mono=time.perf_counter())
    assert order == ["preview", "layer_nav", "children"]
    assert harness._mark_editor_content_ready_calls == [element]
    assert "studio.gicleeframe.media_deferred.done" in events
