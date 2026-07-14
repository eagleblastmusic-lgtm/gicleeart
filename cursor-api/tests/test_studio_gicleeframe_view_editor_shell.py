"""Boundary tests for the extracted GICLÉE FRAME editor shell subsystem."""

from __future__ import annotations

import ast
import re
import sys
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
from giclee_app.ui import gicleeframe_view_editor_shell as editor_shell_module
from giclee_app.ui.gicleeframe_view import (
    GicleeFrameView,
    _GF_MICRO_DEFER_MS,
)
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import (
    GicleeFrameEditorShellMixin,
    _EDITOR_FORM_WIDTH,
    _EDITOR_HERO_PREVIEW_HEIGHT,
    _EDITOR_PLACEHOLDER_TEXT,
    _GF_EDITOR_IDENTITY_LATE_DEFER_MS,
    _GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS,
    _GF_PREVIEW_BOOTSTRAP_STATUS_TEXT,
    _IMAGE_SOURCE_TITLE,
    _LAYER_NAV_TITLE,
    _LEGACY_READONLY_MSG,
    _PREVIEW_SETTINGS_CAPTION,
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
EDITOR_SHELL_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"

_EXPECTED_METHODS = {
    "_build_editor_column_deferred",
    "_micro_deferred_editor_skeleton",
    "_build_section_identity_placeholder",
    "_schedule_editor_identity_late_build",
    "_schedule_editor_identity_prewarm_after_perceived",
    "_schedule_editor_identity_prewarm",
    "_run_editor_identity_prewarm",
    "_schedule_editor_rows_prewarm",
    "_editor_row_shell_flags",
    "_editor_row_shells_already_built",
    "_ensure_editor_row_shells_for_prewarm",
    "_run_editor_rows_prewarm",
    "_ensure_editor_identity_built",
    "_build_editor_identity_late",
    "_micro_deferred_editor_form_shell",
    "_micro_deferred_editor_fields",
    "_micro_deferred_editor_children",
    "_micro_deferred_editor_page_context",
    "_build_section_identity_card",
    "_build_action_dock",
    "_build_editor_column",
    "_build_setting_group_card",
    "_build_edit_panel",
    "_build_edit_panel_page_context",
    "_ensure_page_context_shell_built",
    "_build_edit_panel_fields",
    "_ensure_title_row_built",
    "_ensure_text_row_built",
    "_ensure_alt_row_built",
    "_ensure_image_ref_row_built",
    "_ensure_notes_row_built",
    "_build_edit_panel_children",
    "_ensure_children_overview_built",
    "_hide_editor_field_placeholder_if_needed",
    "_ensure_editor_rows_for_fields",
    "_ensure_minimal_editor_rows_for_fields",
    "_show_editor_placeholder_state",
    "_log_editor_skeleton_suppressed",
    "_show_editor_refresh_status",
    "_hide_editor_refresh_status",
    "_mark_editor_content_ready",
    "_log_editor_content_swapped",
    "_minimal_cache_entry",
    "_fields_from_cache_entry",
    "_apply_section_visual_cache",
    "_apply_minimal_cache",
    "_log_minimal_editor_ready",
    "_hide_heavy_editor_modules",
    "_show_heavy_editor_modules",
    "_mark_editor_stable_shell_ready",
    "_maybe_log_layout_shift_guard",
    "_show_editor_selection_stable_shell_state",
    "_show_editor_selection_pending_state",
    "_mark_editor_shell_ready_after_click",
    "_populate_editor",
    "_set_row_visible",
    "_set_entry",
    "_set_textbox",
}

_SELECTION_OWNERSHIP = {
    "_defer_background_for_selection",
    "_since_selection_click_ms",
}

_INTERACTION_OWNERSHIP = {
    "_selected_section_label",
}

_HOST_OWNERSHIP = {
    "__init__",
    "_editor_micro_defer_ms",
    "_clear_column_children",
    "_since_visual_enter_ms",
    "_queue_latency_since_ms",
    "_log_visual_gate_ready",
    "_try_mark_perceived_ready",
    "_schedule_atomic_reveal_check",
    "_defer_background_for_selection",
    "_should_suppress_visible_prewarm",
    "_log_visible_prewarm_suppressed",
    "_selected_section_label",
    "_apply_edit_to_draft",
    "_since_selection_click_ms",
    "_show_page_context_shell_state",
    "_hide_page_context_rows",
    "_clear_page_context_loading_label",
    "_page_context_pack_kwargs",
    "_get_or_create_readonly_card",
    "_show_page_context_row",
    "_get_or_create_page_context_row",
}

_MICRO_DEFER_CALLERS = {
    "_micro_deferred_editor_skeleton",
    "_schedule_editor_identity_prewarm",
    "_schedule_editor_rows_prewarm",
    "_micro_deferred_editor_fields",
    "_micro_deferred_editor_children",
}

_NOT_MICRO_DEFER_CALLERS = {
    "_micro_deferred_editor_form_shell",
    "_run_editor_identity_prewarm",
    "_run_editor_rows_prewarm",
    "_micro_deferred_editor_page_context",
}

_EDITOR_CONSTANTS = (
    "_LEGACY_READONLY_MSG",
    "_EDITOR_FORM_WIDTH",
    "_EDITOR_HERO_PREVIEW_HEIGHT",
    "_PREVIEW_SETTINGS_CAPTION",
    "_LAYER_NAV_TITLE",
    "_IMAGE_SOURCE_TITLE",
    "_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS",
    "_GF_EDITOR_IDENTITY_LATE_DEFER_MS",
    "_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT",
    "_EDITOR_PLACEHOLDER_TEXT",
)


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}("
    assert marker in text, name
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _host_defines_constant(name: str, host_text: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(name)}\s*=", host_text, re.MULTILINE))


def _host_defines_method(name: str, host_text: str) -> bool:
    return f"def {name}(" in host_text


def _patch_log_event(monkeypatch: pytest.MonkeyPatch, recorder: Any) -> None:
    monkeypatch.setattr(editor_shell_module, "log_event", recorder)


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


class _FakeBooleanVar:
    def __init__(self, value: bool = True) -> None:
        self._value = value

    def get(self) -> bool:
        return self._value

    def set(self, value: bool) -> None:
        self._value = value


class _FakePackable:
    tk = object()

    def __init__(self, *, master: Any | None = None) -> None:
        self.master = master
        self.configure_calls: list[dict[str, Any]] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.pack_forget_calls = 0
        self.grid_calls: list[dict[str, Any]] = []
        self.destroy_calls = 0
        self._managed = False

    def configure(self, **kwargs: Any) -> None:
        self.configure_calls.append(dict(kwargs))

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


class _FakeEntry:
    def __init__(self) -> None:
        self._state = "normal"
        self._text = ""
        self.configure_calls: list[dict[str, Any]] = []

    def configure(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self._state = kwargs["state"]
        self.configure_calls.append(dict(kwargs))

    def delete(self, _start: Any, _end: Any) -> None:
        self._text = ""

    def insert(self, _pos: Any, value: str) -> None:
        self._text = value


class _FakeTextbox:
    def __init__(self) -> None:
        self._state = "normal"
        self._text = ""
        self.configure_calls: list[dict[str, Any]] = []

    def configure(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self._state = kwargs["state"]
        self.configure_calls.append(dict(kwargs))

    def delete(self, _start: Any, _end: Any) -> None:
        self._text = ""

    def insert(self, _pos: Any, value: str) -> None:
        self._text = value


class GicleeFrameEditorShellHarness(GicleeFrameEditorShellMixin):
    def __init__(self) -> None:
        self._workspace_frame: _FakePackable | None = _FakePackable()
        self._editor_column: _FakePackable | None = None
        self._identity_card: _FakePackable | None = None
        self._edit_panel: _FakePackable | None = None
        self._legacy_msg_label: _FakePackable | None = None
        self._editor_placeholder_label: _FakePackable | None = None
        self._editor_status_dot: _FakePackable | None = None
        self._editor_section_subtitle: _FakePackable | None = None
        self._editor_header_visible_row: _FakePackable | None = None
        self._visible_var: _FakeBooleanVar | None = _FakeBooleanVar(True)
        self._visible_row: Any | None = None
        self._layer_nav_frame: _FakePackable | None = None
        self._section_preview_card: _FakePackable | None = None
        self._section_preview_canvas: _FakePackable | None = None
        self._section_preview_badge: _FakePackable | None = None
        self._preview_bootstrap_panel: _FakePackable | None = None
        self._preview_bootstrap_status_label: _FakePackable | None = None
        self._editor_refresh_status_frame: _FakePackable | None = None
        self._editor_refresh_status_label: _FakePackable | None = None
        self._title_row: _FakePackable | None = None
        self._text_row: _FakePackable | None = None
        self._alt_row: _FakePackable | None = None
        self._image_ref_row: _FakePackable | None = None
        self._notes_row: _FakePackable | None = None
        self._notes_group_frame: _FakePackable | None = None
        self._children_overview_row: _FakePackable | None = None
        self._children_overview_buttons: _FakePackable | None = None
        self._page_context_frame: _FakePackable | None = None
        self._page_context_inner: _FakePackable | None = None
        self._title_entry: _FakeEntry | None = None
        self._text_box: _FakeTextbox | None = None
        self._alt_entry: _FakeEntry | None = None
        self._image_ref_entry: _FakeEntry | None = None
        self._notes_box: _FakeTextbox | None = None
        self._shell_editor_built = False
        self._shell_editor_deferred_scheduled_mono: float | None = 10.0
        self._editor_form_shell_ready = False
        self._editor_identity_late_build_started = False
        self._editor_identity_late_build_done = False
        self._editor_identity_prewarm_scheduled = False
        self._editor_rows_prewarm_scheduled = False
        self._title_row_built = False
        self._text_row_built = False
        self._alt_row_built = False
        self._image_ref_row_built = False
        self._notes_row_built = False
        self._children_overview_built = False
        self._page_context_shell_built = False
        self._editor_has_ready_content = False
        self._editor_last_ready_element_id: str | None = None
        self._editor_stable_shell_logged_for: set[str] = set()
        self._atomic_swap_suppress_visible = False
        self._atomic_swap_deferred_row_visibility: list[tuple[Any, bool]] = []
        self._section_visual_cache: dict[str, SectionVisualCacheEntry] = {}
        self._selection_generation = 0
        self._selection_visual_cache_applied = False
        self._page_context_shell_shown_generation = 0
        self._visual_bootstrap_complete = False
        self._selected_id: str | None = None
        self._merged_by_id: dict[str, MergedPageElement] = {}
        self._winfo_exists = True
        self._micro_defer_ms = 16
        self._after_calls: list[tuple[int, Any]] = []
        self._after_counter = 0
        self._clear_column_children_calls: list[Any] = []
        self._visual_gate_calls: list[dict[str, Any]] = []
        self._perceived_ready_calls: list[str] = []
        self._atomic_reveal_calls: list[str] = []
        self._defer_background_calls: list[dict[str, Any]] = []
        self._defer_background_result = False
        self._suppress_visible_prewarm = False
        self._selected_section_label_result = "Section label"
        self._since_selection_click_result: float | None = 5.0
        self._since_visual_enter_result = 12.5
        self._queue_latency_result = 3.0
        self._apply_cached_page_context_calls: list[Any] = []
        self._show_page_context_shell_calls: list[Any] = []
        self._hide_media_details_calls = 0
        self._show_details_on_demand_calls: list[Any] = []
        self._save_section_visual_cache_calls: list[dict[str, Any]] = []
        self._hide_preview_frames_calls = 0
        self._ensure_identity_built_calls = 0
        self._build_identity_late_calls = 0
        self._build_edit_panel_fields_calls = 0
        self._build_edit_panel_children_calls = 0
        self._build_edit_panel_page_context_calls = 0
        self._ensure_title_row_calls = 0
        self._ensure_text_row_calls = 0
        self._ensure_alt_row_calls = 0
        self._ensure_image_ref_row_calls = 0
        self._ensure_notes_row_calls = 0
        self._ensure_children_overview_calls = 0
        self._ensure_page_context_shell_calls = 0

    def winfo_exists(self) -> bool:
        if not self._winfo_exists:
            raise tk.TclError("invalid command name")
        return self._winfo_exists

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_counter += 1
        after_id = f"after-{self._after_counter}"
        self._after_calls.append((delay_ms, callback))
        return after_id

    def _editor_micro_defer_ms(self) -> int:
        return self._micro_defer_ms

    def _clear_column_children(self, column: Any) -> None:
        self._clear_column_children_calls.append(column)

    def _since_visual_enter_ms(self) -> float:
        return self._since_visual_enter_result

    def _queue_latency_since_ms(self, started_mono: float | None) -> float | None:
        _ = started_mono
        return self._queue_latency_result

    def _log_visual_gate_ready(self, *args: Any, **kwargs: Any) -> None:
        self._visual_gate_calls.append({"args": args, "kwargs": kwargs})

    def _try_mark_perceived_ready(self, *, trigger: str) -> None:
        self._perceived_ready_calls.append(trigger)

    def _schedule_atomic_reveal_check(self, *, trigger: str) -> None:
        self._atomic_reveal_calls.append(trigger)

    def _defer_background_for_selection(
        self,
        *,
        job: str,
        reason: str,
        callback: Any,
        delay_ms: int | None = None,
    ) -> bool:
        self._defer_background_calls.append(
            {"job": job, "reason": reason, "callback": callback, "delay_ms": delay_ms},
        )
        return self._defer_background_result

    def _should_suppress_visible_prewarm(self) -> bool:
        return self._suppress_visible_prewarm

    def _log_visible_prewarm_suppressed(self, *, job: str) -> None:
        _ = job

    def _selected_section_label(self) -> str:
        return self._selected_section_label_result

    def _apply_edit_to_draft(self) -> None:
        return None

    def _since_selection_click_ms(self) -> float | None:
        return self._since_selection_click_result

    def _apply_cached_page_context_summary(self, entry: Any) -> None:
        self._apply_cached_page_context_calls.append(entry)

    def _show_page_context_shell_state(self, m: Any) -> None:
        self._show_page_context_shell_calls.append(m)

    def _hide_media_details_stable_shell(self) -> None:
        self._hide_media_details_calls += 1

    def _show_details_on_demand_block(self, m: Any) -> None:
        self._show_details_on_demand_calls.append(m)

    def _save_section_visual_cache(
        self,
        m: Any,
        fields: EditorFieldVisibility,
        *,
        media_details_built: bool,
    ) -> None:
        self._save_section_visual_cache_calls.append(
            {"element": m, "fields": fields, "media_details_built": media_details_built},
        )

    def _hide_preview_frames(self) -> None:
        self._hide_preview_frames_calls += 1

    def _ensure_editor_identity_built(self) -> None:
        self._ensure_identity_built_calls += 1
        GicleeFrameEditorShellMixin._ensure_editor_identity_built(self)

    def _build_editor_identity_late(self) -> None:
        self._build_identity_late_calls += 1
        GicleeFrameEditorShellMixin._build_editor_identity_late(self)

    def _build_edit_panel_fields(self) -> None:
        self._build_edit_panel_fields_calls += 1
        GicleeFrameEditorShellMixin._build_edit_panel_fields(self)

    def _build_edit_panel_children(self) -> None:
        self._build_edit_panel_children_calls += 1
        GicleeFrameEditorShellMixin._build_edit_panel_children(self)

    def _build_edit_panel_page_context(self) -> None:
        self._build_edit_panel_page_context_calls += 1
        GicleeFrameEditorShellMixin._build_edit_panel_page_context(self)

    def _ensure_title_row_built(self) -> None:
        self._ensure_title_row_calls += 1
        if not self._title_row_built:
            self._title_row = _FakePackable()
            self._title_entry = _FakeEntry()
            self._title_row_built = True

    def _ensure_text_row_built(self) -> None:
        self._ensure_text_row_calls += 1
        if not self._text_row_built:
            self._text_row = _FakePackable()
            self._text_box = _FakeTextbox()
            self._text_row_built = True

    def _ensure_alt_row_built(self) -> None:
        self._ensure_alt_row_calls += 1
        if not self._alt_row_built:
            self._alt_row = _FakePackable()
            self._alt_entry = _FakeEntry()
            self._alt_row_built = True

    def _ensure_image_ref_row_built(self) -> None:
        self._ensure_image_ref_row_calls += 1
        if not self._image_ref_row_built:
            self._image_ref_row = _FakePackable()
            self._image_ref_entry = _FakeEntry()
            self._image_ref_row_built = True

    def _ensure_notes_row_built(self) -> None:
        self._ensure_notes_row_calls += 1
        if not self._notes_row_built:
            self._notes_row = _FakePackable()
            self._notes_group_frame = _FakePackable()
            self._notes_box = _FakeTextbox()
            self._notes_row_built = True

    def _ensure_children_overview_built(self) -> None:
        self._ensure_children_overview_calls += 1
        if not self._children_overview_built:
            self._children_overview_row = _FakePackable()
            self._children_overview_buttons = _FakePackable()
            self._children_overview_built = True

    def _ensure_page_context_shell_built(self) -> None:
        self._ensure_page_context_shell_calls += 1
        if not self._page_context_shell_built and self._edit_panel is not None:
            self._page_context_frame = _FakePackable()
            self._page_context_inner = _FakePackable()
            self._page_context_shell_built = True


# --- Structural / contract tests ---


def test_editor_shell_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameEditorShellMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameEditorShellMixin.__dict__
    assert _EXPECTED_METHODS == {
        name
        for name, value in GicleeFrameEditorShellMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }
    assert len(_EXPECTED_METHODS) == 58


def test_editor_shell_module_has_no_write_network_or_reverse_host_import() -> None:
    source = EDITOR_SHELL_PATH.read_text(encoding="utf-8")
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


def test_editor_shell_public_boundary_contract() -> None:
    assert editor_shell_module.__all__ == (
        "GicleeFrameEditorShellMixin",
        *_EDITOR_CONSTANTS,
    )


def test_editor_shell_constants_exact_values() -> None:
    assert _LEGACY_READONLY_MSG == (
        "Sekcja legacy — nie jest edytowana w Studio. "
        "Tylko notatka robocza opcjonalna."
    )
    assert _EDITOR_FORM_WIDTH == 760
    assert _EDITOR_HERO_PREVIEW_HEIGHT == 118
    assert _PREVIEW_SETTINGS_CAPTION == "Podgląd ustawień"
    assert _LAYER_NAV_TITLE == "Warstwy sekcji"
    assert _IMAGE_SOURCE_TITLE == "Źródło grafiki"
    assert _GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS == 80
    assert _GF_EDITOR_IDENTITY_LATE_DEFER_MS == 160
    assert _GF_PREVIEW_BOOTSTRAP_STATUS_TEXT == "Podgląd sekcji pojawi się po wyborze…"
    assert _EDITOR_PLACEHOLDER_TEXT == (
        "Wybierz sekcję po lewej stronie, aby załadować podgląd i ustawienia."
    )
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EDITOR_CONSTANTS:
        assert not _host_defines_constant(name, host_text), name


def test_gicleeframe_view_has_fourteen_mixins_before_scrollable_frame() -> None:
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
        ctk.CTkScrollableFrame,
    )

    assert GicleeFrameView.__mro__[1 : 1 + len(expected)] == expected


def test_editor_shell_methods_resolve_by_identity_from_mixin_on_gicleeframe_view() -> None:
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameEditorShellMixin,
            name,
        )


def test_host_ownership_for_editor_adapters() -> None:
    for name in _HOST_OWNERSHIP:
        assert name not in GicleeFrameEditorShellMixin.__dict__
    host_in_view = (
        _HOST_OWNERSHIP
        - {"__init__"}
        - _SELECTION_OWNERSHIP
        - _INTERACTION_OWNERSHIP
    )
    for name in host_in_view:
        assert name in GicleeFrameView.__dict__
    for name in _SELECTION_OWNERSHIP:
        assert name in GicleeFrameSelectionOrchestrationMixin.__dict__
    for name in _INTERACTION_OWNERSHIP:
        assert name in GicleeFrameSectionListInteractionMixin.__dict__


def test_editor_micro_defer_ms_delegates_to_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = object.__new__(GicleeFrameView)
    assert view._editor_micro_defer_ms() == _GF_MICRO_DEFER_MS
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view._GF_MICRO_DEFER_MS",
        24,
    )
    assert view._editor_micro_defer_ms() == 24


def test_editor_shell_micro_defer_callers_exact() -> None:
    source = EDITOR_SHELL_PATH.read_text(encoding="utf-8")
    for name in _MICRO_DEFER_CALLERS:
        body = _method_block(source, name)
        assert "_editor_micro_defer_ms()" in body, name
    for name in _NOT_MICRO_DEFER_CALLERS:
        body = _method_block(source, name)
        assert "_editor_micro_defer_ms()" not in body, name


def test_editor_shell_source_ownership_in_module() -> None:
    text = EDITOR_SHELL_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert _host_defines_method(name, text), name
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert not _host_defines_method(name, host_text), name
    lowered = text.lower()
    assert "def _refresh_inventory" not in text
    assert "def _populate_editor_media_details_batch" not in text
    assert "shopify" not in lowered


# --- Deferred editor startup ---


def test_build_editor_column_deferred_missing_widget_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._winfo_exists = False
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    harness._build_editor_column_deferred()
    assert harness._shell_editor_built is False
    assert harness._after_calls == []


def test_build_editor_column_deferred_already_built_returns() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = True
    harness._build_editor_column_deferred()
    assert harness._after_calls == []


def test_build_editor_column_deferred_missing_workspace_returns() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._workspace_frame = None
    harness._build_editor_column_deferred()
    assert harness._after_calls == []


def test_build_editor_column_deferred_logs_and_schedules_skeleton(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    skeleton_calls: list[None] = []

    def _skeleton() -> None:
        skeleton_calls.append(None)

    monkeypatch.setattr(harness, "_micro_deferred_editor_skeleton", _skeleton)
    harness._build_editor_column_deferred()
    assert any(item[0] == "studio.gicleeframe.editor.skeleton_enter" for item in events)
    assert len(skeleton_calls) == 1


def test_micro_deferred_editor_skeleton_creates_column_and_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell._make_card",
        lambda parent, **_k: _FakePackable(master=parent),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkLabel",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.theme.get_font",
        lambda *_a, **_k: "Arial 10",
    )
    monkeypatch.setattr(
        harness,
        "_build_section_identity_placeholder",
        lambda _p: None,
    )
    harness._micro_deferred_editor_skeleton()
    assert harness._shell_editor_built is True
    assert harness._editor_column is not None
    assert "studio.gicleeframe.editor.skeleton_ready" in events
    assert harness._after_calls[-1][0] == harness._micro_defer_ms
    assert harness._after_calls[-1][1] == harness._micro_deferred_editor_form_shell


def test_micro_deferred_editor_skeleton_reuses_existing_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    existing = _FakePackable()
    harness._editor_column = existing
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkLabel",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.theme.get_font",
        lambda *_a, **_k: "Arial 10",
    )
    monkeypatch.setattr(
        harness,
        "_build_section_identity_placeholder",
        lambda _p: None,
    )
    harness._micro_deferred_editor_skeleton()
    assert harness._editor_column is existing
    assert harness._clear_column_children_calls == [existing]


def test_micro_deferred_editor_skeleton_placeholder_when_no_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._editor_column = _FakePackable()
    placeholder_calls: list[None] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkLabel",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.theme.get_font",
        lambda *_a, **_k: "Arial 10",
    )
    monkeypatch.setattr(
        harness,
        "_build_section_identity_placeholder",
        lambda _p: None,
    )
    monkeypatch.setattr(
        harness,
        "_show_editor_placeholder_state",
        lambda: placeholder_calls.append(None),
    )
    harness._selected_id = None
    harness._micro_deferred_editor_skeleton()
    assert len(placeholder_calls) == 1
    assert harness._perceived_ready_calls == ["editor_skeleton_done"]


# --- Identity late build and prewarm ---


def test_schedule_editor_identity_late_build_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._schedule_editor_identity_late_build()
    harness._schedule_editor_identity_late_build()
    assert harness._editor_identity_late_build_started is True
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_EDITOR_IDENTITY_LATE_DEFER_MS
    scheduled = [
        item for item in events if item[0] == "studio.gicleeframe.editor.identity_card_late_scheduled"
    ]
    assert len(scheduled) == 1


def test_schedule_editor_identity_prewarm_after_perceived_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._schedule_editor_identity_prewarm_after_perceived()
    harness._editor_identity_prewarm_scheduled = True
    harness._schedule_editor_identity_prewarm_after_perceived()
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0][0] == _GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS
    deferred = [
        item
        for item in events
        if item[0] == "studio.gicleeframe.editor.identity_prewarm_deferred_after_perceived"
    ]
    assert len(deferred) == 1


def test_schedule_editor_identity_prewarm_uses_micro_defer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._micro_defer_ms = 22
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    harness._schedule_editor_identity_prewarm(reason="test")
    assert harness._editor_identity_prewarm_scheduled is True
    assert harness._after_calls == [(22, harness._run_editor_identity_prewarm)]


def test_run_editor_identity_prewarm_defers_for_selection_priority() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._defer_background_result = True
    harness._run_editor_identity_prewarm()
    assert harness._ensure_identity_built_calls == 0


def test_run_editor_identity_prewarm_skips_when_already_built(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = True
    harness._editor_identity_late_build_done = True
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    rows_scheduled: list[None] = []
    monkeypatch.setattr(
        harness,
        "_schedule_editor_rows_prewarm",
        lambda: rows_scheduled.append(None),
    )
    harness._run_editor_identity_prewarm()
    assert "studio.gicleeframe.editor.identity_prewarm_skipped" in events
    assert len(rows_scheduled) == 1


def test_run_editor_identity_prewarm_skips_when_shell_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = False
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._run_editor_identity_prewarm()
    assert "studio.gicleeframe.editor.identity_prewarm_skipped" in events
    assert harness._ensure_identity_built_calls == 0


def test_run_editor_identity_prewarm_builds_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = True
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    rows_scheduled: list[None] = []
    monkeypatch.setattr(
        harness,
        "_schedule_editor_rows_prewarm",
        lambda: rows_scheduled.append(None),
    )
    harness._run_editor_identity_prewarm()
    assert "studio.gicleeframe.editor.identity_prewarm_done" in events
    assert len(rows_scheduled) == 1


def test_schedule_editor_rows_prewarm_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._micro_defer_ms = 18
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    harness._schedule_editor_rows_prewarm()
    harness._schedule_editor_rows_prewarm()
    assert harness._editor_rows_prewarm_scheduled is True
    assert len(harness._after_calls) == 1
    assert harness._after_calls[0] == (18, harness._run_editor_rows_prewarm)


def test_editor_row_shell_flags_and_all_built_policy() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._title_row_built = True
    harness._text_row_built = True
    harness._alt_row_built = False
    flags = harness._editor_row_shell_flags()
    assert flags == {
        "title": True,
        "text": True,
        "alt": False,
        "image_ref": False,
        "notes": False,
    }
    assert harness._editor_row_shells_already_built() is False
    harness._alt_row_built = True
    harness._image_ref_row_built = True
    harness._notes_row_built = True
    assert harness._editor_row_shells_already_built() is True


def test_run_editor_rows_prewarm_visible_suppression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._suppress_visible_prewarm = True
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    harness._run_editor_rows_prewarm()
    assert harness._ensure_title_row_calls == 0


def test_run_editor_rows_prewarm_form_shell_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = True
    harness._editor_form_shell_ready = False
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._run_editor_rows_prewarm()
    assert "studio.gicleeframe.editor.rows_prewarm_skipped" in events
    assert harness._ensure_title_row_calls == 0


def test_run_editor_rows_prewarm_builds_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._shell_editor_built = True
    harness._editor_form_shell_ready = True
    harness._edit_panel = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._run_editor_rows_prewarm()
    assert harness._ensure_title_row_calls == 1
    assert "studio.gicleeframe.editor.rows_prewarm_done" in events


def test_build_editor_identity_late_defers_for_selection() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._defer_background_result = True
    harness._build_editor_identity_late()
    assert harness._editor_identity_late_build_done is False


def test_build_editor_identity_late_restores_selected_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._editor_column = _FakePackable()
    harness._selected_id = "elem-a"
    element = _sample_merged("elem-a")
    harness._merged_by_id = {"elem-a": element}
    harness._editor_section_subtitle = _FakePackable()
    harness._editor_status_dot = _FakePackable()
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        harness,
        "_build_section_identity_card",
        lambda _p, **_k: None,
    )
    harness._build_editor_identity_late()
    assert harness._editor_identity_late_build_done is True
    assert harness._editor_status_dot.configure_calls
    assert harness._editor_section_subtitle.configure_calls


# --- Form shell and micro-deferred chaining ---


def test_micro_deferred_editor_form_shell_sets_ready_and_reveal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._editor_column = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkFrame",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkLabel",
        lambda *_a, **_k: _FakePackable(),
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.theme.get_font",
        lambda *_a, **_k: "Arial 10",
    )
    harness._micro_deferred_editor_form_shell()
    assert harness._editor_form_shell_ready is True
    assert harness._edit_panel is not None
    assert "studio.gicleeframe.editor.deferred_form_shell" in events
    assert harness._atomic_reveal_calls == ["editor_form_shell"]


def test_micro_deferred_editor_fields_chains_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._micro_defer_ms = 11
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_build_edit_panel_fields", lambda: None)
    harness._micro_deferred_editor_fields()
    assert harness._after_calls == [(11, harness._micro_deferred_editor_children)]


def test_micro_deferred_editor_children_chains_page_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._micro_defer_ms = 13
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_build_edit_panel_children", lambda: None)
    harness._micro_deferred_editor_children()
    assert harness._after_calls == [(13, harness._micro_deferred_editor_page_context)]


def test_micro_deferred_editor_page_context_builds_page_context() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._micro_deferred_editor_page_context()
    assert harness._build_edit_panel_page_context_calls == 1


# --- Row construction and placeholder ---


def test_ensure_page_context_shell_built_idempotent() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._edit_panel = _FakePackable()
    harness._ensure_page_context_shell_built()
    first_frame = harness._page_context_frame
    harness._ensure_page_context_shell_built()
    assert harness._page_context_shell_built is True
    assert harness._page_context_frame is first_frame
    assert harness._ensure_page_context_shell_calls == 2


def test_ensure_title_row_built_idempotent() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._edit_panel = _FakePackable()
    harness._ensure_title_row_built()
    first_entry = harness._title_entry
    harness._ensure_title_row_built()
    assert harness._title_row_built is True
    assert harness._title_entry is first_entry


def test_ensure_editor_rows_for_fields_includes_children_and_page_context() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._edit_panel = _FakePackable()
    fields = EditorFieldVisibility(
        title=True,
        text=True,
        children=True,
        page_context=True,
        visible=True,
    )
    harness._ensure_editor_rows_for_fields(fields)
    assert harness._ensure_title_row_calls == 1
    assert harness._ensure_text_row_calls == 1
    assert harness._ensure_children_overview_calls == 1
    assert harness._ensure_page_context_shell_calls == 1


def test_ensure_minimal_editor_rows_for_fields_skips_children() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._edit_panel = _FakePackable()
    fields = EditorFieldVisibility(
        title=True,
        children=True,
        page_context=True,
    )
    harness._ensure_minimal_editor_rows_for_fields(fields)
    assert harness._ensure_title_row_calls == 1
    assert harness._ensure_children_overview_calls == 0


def test_hide_editor_field_placeholder_if_needed_forgets_label() -> None:
    harness = GicleeFrameEditorShellHarness()
    label = _FakePackable()
    label._managed = True
    harness._editor_placeholder_label = label
    harness._hide_editor_field_placeholder_if_needed()
    assert label.pack_forget_calls == 1


def test_hide_editor_field_placeholder_if_needed_swallows_tclerror() -> None:
    harness = GicleeFrameEditorShellHarness()

    class _BrokenLabel:
        def winfo_manager(self) -> str:
            raise tk.TclError("broken")

        def pack_forget(self) -> None:
            raise AssertionError("should not be called")

    harness._editor_placeholder_label = _BrokenLabel()
    harness._hide_editor_field_placeholder_if_needed()


def test_show_editor_placeholder_state_updates_ui_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._editor_status_dot = _FakePackable()
    harness._editor_section_subtitle = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._show_editor_placeholder_state()
    assert events == ["studio.gicleeframe.editor.placeholder_state"]


def test_log_editor_skeleton_suppressed_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._log_editor_skeleton_suppressed(
        element_id="a",
        element_type="media_section",
        reason="already_ready",
    )
    assert events[0][0] == "studio.gicleeframe.editor.skeleton_suppressed"
    assert events[0][1]["reason"] == "already_ready"


# --- Refresh status ---


def test_show_editor_refresh_status_creates_and_packs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._identity_card = _FakePackable()
    harness._layer_nav_frame = _FakePackable()
    harness._layer_nav_frame._managed = True
    frame = _FakePackable()
    label = _FakePackable()
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkFrame",
        lambda *_a, **_k: frame,
    )
    label_kwargs: dict[str, Any] = {}

    def _make_label(*_args: Any, **kwargs: Any) -> _FakePackable:
        label_kwargs.update(kwargs)
        return label

    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.ctk.CTkLabel",
        _make_label,
    )
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.theme.get_font",
        lambda *_a, **_k: "Arial 9",
    )
    harness._show_editor_refresh_status("Loading…")
    assert harness._editor_refresh_status_frame is frame
    assert harness._editor_refresh_status_label is label
    assert label_kwargs["text"] == "Loading…"
    assert label.pack_calls


def test_show_editor_refresh_status_updates_existing_label() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._identity_card = _FakePackable()
    harness._editor_refresh_status_frame = _FakePackable()
    harness._editor_refresh_status_label = _FakePackable()
    harness._show_editor_refresh_status("Updated")
    assert harness._editor_refresh_status_label.configure_calls[-1]["text"] == "Updated"


def test_hide_editor_refresh_status_forgets_frame() -> None:
    harness = GicleeFrameEditorShellHarness()
    frame = _FakePackable()
    frame._managed = True
    harness._editor_refresh_status_frame = frame
    harness._hide_editor_refresh_status()
    assert frame.pack_forget_calls == 1


def test_hide_editor_refresh_status_absent_noop() -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._editor_refresh_status_frame = None
    harness._hide_editor_refresh_status()


# --- Cache and minimal population ---


def test_minimal_cache_entry_lookup() -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    entry = _sample_cache_entry()
    harness._section_visual_cache = {"a": entry}
    assert harness._minimal_cache_entry(element) is entry


def test_fields_from_cache_entry_reconstructs_visibility() -> None:
    harness = GicleeFrameEditorShellHarness()
    entry = _sample_cache_entry(fields_title=True, fields_text=False, fields_notes=True)
    fields = harness._fields_from_cache_entry(entry)
    assert fields.title is True
    assert fields.text is False
    assert fields.notes is True


def test_apply_section_visual_cache_delegates_to_minimal_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    calls: list[Any] = []
    monkeypatch.setattr(
        harness,
        "_apply_minimal_cache",
        lambda m: calls.append(m) or True,
    )
    assert harness._apply_section_visual_cache(element) is True
    assert calls == [element]


def test_apply_minimal_cache_miss_returns_false() -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("missing")
    assert harness._apply_minimal_cache(element) is False


def test_apply_minimal_cache_hit_applies_fields_and_host_adapters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    entry = _sample_cache_entry(
        title="T",
        text="X",
        notes="N",
        visible=False,
        fields_title=True,
        fields_text=True,
        fields_notes=True,
        fields_visible=True,
    )
    harness._section_visual_cache = {"a": entry}
    harness._edit_panel = _FakePackable()
    harness._title_row = _FakePackable()
    harness._text_row = _FakePackable()
    harness._notes_row = _FakePackable()
    harness._visible_row = _FakePackable()
    harness._title_entry = _FakeEntry()
    harness._text_box = _FakeTextbox()
    harness._notes_box = _FakeTextbox()
    harness._visible_var = _FakeBooleanVar(False)
    harness._editor_status_dot = _FakePackable()
    harness._editor_section_subtitle = _FakePackable()
    harness._title_row_built = True
    harness._text_row_built = True
    harness._notes_row_built = True
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    assert harness._apply_minimal_cache(element) is True
    assert harness._title_entry._text == "T"
    assert harness._text_box._text == "X"
    assert harness._notes_box._text == "N"
    assert harness._visible_var.get() is False
    assert harness._apply_cached_page_context_calls == [entry]
    assert harness._hide_media_details_calls == 1
    assert harness._show_details_on_demand_calls == [element]
    assert harness._editor_has_ready_content is True
    assert "studio.gicleeframe.selection.minimal_editor_ready" in events


def test_apply_minimal_cache_legacy_readonly_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("legacy", element_type="section_legacy")
    entry = _sample_cache_entry(
        element_type="section_legacy",
        title="Legacy title",
        fields_title=True,
        fields_text=True,
        fields_notes=True,
    )
    harness._section_visual_cache = {"legacy": entry}
    harness._edit_panel = _FakePackable()
    harness._title_row = _FakePackable()
    harness._text_row = _FakePackable()
    harness._notes_row = _FakePackable()
    harness._title_entry = _FakeEntry()
    harness._text_box = _FakeTextbox()
    harness._notes_box = _FakeTextbox()
    harness._title_row_built = True
    harness._text_row_built = True
    harness._notes_row_built = True
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    harness._apply_minimal_cache(element)
    assert harness._title_entry._state == "disabled"
    assert harness._text_box._state == "disabled"


def test_mark_editor_content_ready_sets_state() -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._mark_editor_content_ready(element)
    assert harness._editor_has_ready_content is True
    assert harness._editor_last_ready_element_id == "a"


def test_log_editor_content_swapped_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._log_editor_content_swapped(element, region="preview", preview_key="k1")
    assert events[0][0] == "studio.gicleeframe.editor.content_swapped"
    assert events[0][1]["region"] == "preview"


def test_hide_heavy_editor_modules_and_show_roundtrip() -> None:
    harness = GicleeFrameEditorShellHarness()
    preview = _FakePackable()
    preview._managed = True
    layer = _FakePackable()
    layer._managed = True
    children = _FakePackable()
    harness._section_preview_card = preview
    harness._layer_nav_frame = layer
    harness._children_overview_row = children
    harness._hide_heavy_editor_modules()
    assert preview.pack_forget_calls == 1
    assert layer.pack_forget_calls == 1
    assert harness._hide_preview_frames_calls == 1
    preview._managed = False
    harness._show_heavy_editor_modules()
    assert preview.pack_calls


def test_mark_editor_stable_shell_ready_one_time_and_from_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._mark_editor_stable_shell_ready(element)
    harness._mark_editor_stable_shell_ready(element)
    assert events.count("studio.gicleeframe.editor.stable_shell_ready") == 1
    events.clear()
    harness._mark_editor_stable_shell_ready(element, from_cache=True)
    assert events.count("studio.gicleeframe.editor.stable_shell_ready") == 1


def test_maybe_log_layout_shift_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._maybe_log_layout_shift_guard(element, phase="populate_done", rows_visible=3)
    assert events[0][1]["rows_visible"] == 3


def test_show_editor_selection_stable_shell_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._editor_status_dot = _FakePackable()
    harness._editor_section_subtitle = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._show_editor_selection_stable_shell_state(element, from_cache=False)
    assert "studio.gicleeframe.editor.selection_stable_shell" in events


def test_show_editor_selection_pending_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._editor_status_dot = _FakePackable()
    harness._editor_section_subtitle = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._show_editor_selection_pending_state(element)
    assert "studio.gicleeframe.editor.selection_pending" in events


def test_mark_editor_shell_ready_after_click(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._editor_section_subtitle = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    harness._mark_editor_shell_ready_after_click(element, page_context_shell=True)
    assert "studio.gicleeframe.editor.shell_ready_after_click" in events


# --- _populate_editor branches ---


def test_populate_editor_ensure_identity_and_rows_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._edit_panel = _FakePackable()
    order: list[str] = []

    def _identity() -> None:
        order.append("identity")

    def _rows(_fields: EditorFieldVisibility) -> None:
        order.append("rows")

    monkeypatch.setattr(harness, "_ensure_editor_identity_built", _identity)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", _rows)
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert order == ["identity", "rows"]


def test_populate_editor_page_context_from_cache_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    entry = _sample_cache_entry(page_context_summary=(("A", "B"),), fields_page_context=True)
    harness._section_visual_cache = {"a": entry}
    harness._edit_panel = _FakePackable()
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert harness._apply_cached_page_context_calls == [entry]
    assert harness._show_page_context_shell_calls == []


def test_populate_editor_page_context_shell_state_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("jumbo", element_type="jumbo")
    harness._edit_panel = _FakePackable()
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert harness._show_page_context_shell_calls == [element]


def test_populate_editor_legacy_message_and_readonly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("legacy", element_type="section_legacy")
    harness._edit_panel = _FakePackable()
    harness._legacy_msg_label = _FakePackable()
    harness._title_row = _FakePackable()
    harness._notes_row = _FakePackable()
    harness._title_entry = _FakeEntry()
    harness._notes_box = _FakeTextbox()
    harness._title_row_built = True
    harness._notes_row_built = True
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert harness._legacy_msg_label.pack_calls
    assert harness._title_entry._state == "disabled"


def test_populate_editor_image_row_repack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("img", element_type="image")
    harness._edit_panel = _FakePackable()
    harness._notes_row = _FakePackable()
    harness._alt_row = _FakePackable()
    harness._image_ref_row = _FakePackable()
    harness._alt_entry = _FakeEntry()
    harness._image_ref_entry = _FakeEntry()
    harness._notes_box = _FakeTextbox()
    harness._alt_row_built = True
    harness._image_ref_row_built = True
    harness._notes_row_built = True
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert harness._notes_row.pack_forget_calls >= 1
    assert harness._notes_row.pack_calls


def test_populate_editor_final_host_adapter_ordering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._edit_panel = _FakePackable()
    order: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(
        harness,
        "_hide_heavy_editor_modules",
        lambda: order.append("hide_heavy"),
    )
    monkeypatch.setattr(
        harness,
        "_hide_media_details_stable_shell",
        lambda: order.append("hide_media"),
    )
    monkeypatch.setattr(
        harness,
        "_show_details_on_demand_block",
        lambda _m: order.append("details_on_demand"),
    )
    monkeypatch.setattr(
        harness,
        "_hide_editor_refresh_status",
        lambda: order.append("hide_refresh"),
    )
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert order == ["hide_heavy", "hide_media", "details_on_demand", "hide_refresh"]
    assert len(harness._save_section_visual_cache_calls) == 1
    assert harness._save_section_visual_cache_calls[0]["media_details_built"] is False


def test_populate_editor_first_selection_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._edit_panel = _FakePackable()
    harness._visual_bootstrap_complete = False
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert "studio.gicleeframe.visual.first_selection_done" in events


def test_populate_editor_deferred_detail_telemetry_without_heavy_population(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    element = _sample_merged("a")
    harness._edit_panel = _FakePackable()
    events: list[str] = []
    monkeypatch.setattr(
        "giclee_app.ui.gicleeframe_view_editor_shell.log_event",
        lambda event, **_k: events.append(event),
    )
    monkeypatch.setattr(harness, "_ensure_editor_identity_built", lambda: None)
    monkeypatch.setattr(harness, "_ensure_minimal_editor_rows_for_fields", lambda _f: None)
    monkeypatch.setattr(harness, "_hide_heavy_editor_modules", lambda: None)
    monkeypatch.setattr(harness, "_hide_media_details_stable_shell", lambda: None)
    monkeypatch.setattr(harness, "_show_details_on_demand_block", lambda _m: None)
    monkeypatch.setattr(harness, "_hide_editor_refresh_status", lambda: None)
    monkeypatch.setattr(harness, "_mark_editor_shell_ready_after_click", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_stable_shell_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_mark_editor_content_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_log_minimal_editor_ready", lambda *_a, **_k: None)
    monkeypatch.setattr(harness, "_maybe_log_layout_shift_guard", lambda *_a, **_k: None)
    harness._populate_editor(element)
    assert "studio.gicleeframe.populate_editor.details_deferred" in events
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in events


# --- Atomic swap row visibility and field setters ---


def test_set_row_visible_atomic_swap_queues_visibility() -> None:
    harness = GicleeFrameEditorShellHarness()
    row = _FakePackable()
    harness._atomic_swap_suppress_visible = True
    harness._set_row_visible(row, True)
    assert harness._atomic_swap_deferred_row_visibility == [(row, True)]
    assert row.pack_calls == []


def test_set_row_visible_direct_pack_and_notes_group() -> None:
    harness = GicleeFrameEditorShellHarness()
    row = _FakePackable()
    notes_group = _FakePackable()
    harness._notes_row = row
    harness._notes_group_frame = notes_group
    harness._set_row_visible(row, True)
    assert row.pack_calls
    assert notes_group.pack_calls


def test_set_row_visible_direct_pack_forget() -> None:
    harness = GicleeFrameEditorShellHarness()
    row = _FakePackable()
    row._managed = True
    harness._set_row_visible(row, False)
    assert row.pack_forget_calls == 1


def test_set_entry_readonly_and_editable_states() -> None:
    harness = GicleeFrameEditorShellHarness()
    entry = _FakeEntry()
    harness._set_entry(entry, "hello", readonly=True)
    assert entry._text == "hello"
    assert entry._state == "disabled"
    harness._set_entry(entry, "world", readonly=False)
    assert entry._text == "world"
    assert entry._state == "normal"


def test_set_textbox_readonly_and_editable_states() -> None:
    harness = GicleeFrameEditorShellHarness()
    box = _FakeTextbox()
    harness._set_textbox(box, "notes", readonly=True)
    assert box._text == "notes"
    assert box._state == "disabled"
    harness._set_textbox(box, "updated", readonly=False)
    assert box._text == "updated"
    assert box._state == "normal"


def test_build_edit_panel_composition_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameEditorShellHarness()
    harness._edit_panel = _FakePackable()
    order: list[str] = []

    def _page_context() -> None:
        order.append("page_context")

    def _fields() -> None:
        order.append("fields")

    def _children() -> None:
        order.append("children")

    monkeypatch.setattr(harness, "_build_edit_panel_page_context", _page_context)
    monkeypatch.setattr(harness, "_build_edit_panel_fields", _fields)
    monkeypatch.setattr(harness, "_build_edit_panel_children", _children)
    harness._build_edit_panel()
    assert order == ["page_context", "fields", "children"]
