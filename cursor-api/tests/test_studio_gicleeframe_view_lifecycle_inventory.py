"""Boundary tests for the extracted GICLÉE FRAME lifecycle/inventory subsystem."""

from __future__ import annotations

import ast
import os
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
    GicleeFramePageDraft,
    MergedPageElement,
    SectionDropdownOption,
    merge_inventory_with_draft,
)
from giclee_app.ui import gicleeframe_view_lifecycle_inventory as lifecycle_module
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from giclee_app.ui.gicleeframe_view_details_on_demand import (
    GicleeFrameDetailsOnDemandMixin,
)
from giclee_app.ui.gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from giclee_app.ui.gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
    _CONTROL_COL_MINSIZE,
    _EAGER_BOOT_ENV,
    _GF_CONTROL_LATE_BUILD_DEFER_MS,
    _GF_F1_DEFER_MS,
    _GF_INIT_REFRESH_LIGHT_DEFER_MS,
    _GF_LAZY_SHELL_ENV,
    _GF_LOADING_OVERLAY_TEXT,
    _GF_MICRO_DEFER_MS,
    _GF_SECTION_FIRST_VISIBLE_DEFER_MS,
    _GF_SHELL_CONTROL_DEFER_MS,
    _GF_SHELL_EDITOR_DEFER_MS,
    _GF_SKELETON_CONTROL_TEXT,
    _GF_SKELETON_EDITOR_TEXT,
    _GF_SKELETON_SECTION_TEXT,
    _PROGRESSIVE_BOOT_ENV,
    _env_enabled,
    _lazy_shell_enabled,
    _progressive_boot_enabled,
)
from giclee_app.ui.gicleeframe_view_page_context import GicleeFramePageContextMixin
from giclee_app.ui.gicleeframe_view_page_readiness import GicleeFramePageReadinessMixin
from giclee_app.ui.gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from giclee_app.ui.gicleeframe_view_readiness_row import GicleeFrameReadinessRowMixin
from giclee_app.ui.gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from giclee_app.ui.gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)
from giclee_app.ui.gicleeframe_view_section_list_shell import GicleeFrameSectionListShellMixin
from giclee_app.ui.gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)
from giclee_app.ui.gicleeframe_view_structure_dry_run import GicleeFrameStructureDryRunMixin
from giclee_app.ui.gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from giclee_app.ui.gicleeframe_view_visual_detail_renderers import (
    GicleeFrameVisualDetailRenderersMixin,
)

ROOT = Path(__file__).resolve().parents[1]
VIEW_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
LIFECYCLE_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
LIFECYCLE_PATCH = "giclee_app.ui.gicleeframe_view_lifecycle_inventory"

_EXPECTED_METHODS = {
    "set_navigation",
    "_handle_back",
    "on_show",
    "on_hide",
    "_view_lifecycle_alive",
    "_cancel_atomic_reveal_check",
    "_activate_view_lifecycle",
    "_deactivate_view_lifecycle",
    "_on_lifecycle_destroy",
    "_rebuild_page_model_cache",
    "_set_merged",
    "_since_visual_enter_ms",
    "_queue_latency_since_ms",
    "_begin_visual_session",
    "_ensure_atomic_reveal_overlay",
    "_atomic_reveal_missing_gates",
    "_ensure_atomic_reveal_prerequisites",
    "_ensure_top_bar_actions_for_atomic_reveal",
    "_schedule_atomic_reveal_check",
    "_try_atomic_reveal",
    "_ensure_loading_overlay",
    "_show_loading_overlay",
    "_hide_loading_overlay",
    "_mark_idle_ready",
    "_mark_visual_ready",
    "_schedule_visual_ready",
    "_log_visual_gate_ready",
    "_try_mark_perceived_ready",
    "_build_shell",
    "_build_page_editor_section_critical",
    "_build_workspace_skeleton_column",
    "_clear_column_children",
    "_build_workspace_critical",
    "_build_sections_column_deferred",
    "_build_sections_column_extras_deferred",
    "_log_visible_prewarm_suppressed",
    "_should_suppress_visible_prewarm",
    "_build_control_column_deferred",
    "_micro_deferred_control_skeleton",
    "_micro_deferred_control_structure",
    "_schedule_control_late_build",
    "_build_control_late_cards",
    "_micro_deferred_control_readiness",
    "_micro_deferred_control_safety",
    "_build_page_editor_section",
    "_build_page_workspace",
    "_upgrade_section_list_scroll",
    "_build_control_column",
    "_build_page_top_bar",
    "_build_toolbar_group",
    "_toggle_f1_section",
    "_schedule_init_refresh_light",
    "_run_init_refresh_light_deferred",
    "_finish_init_refresh_light",
    "_bootstrap_section_list_after_inventory_light",
    "_flush_pending_section_list_if_needed",
    "_schedule_section_list_incremental",
    "_refresh_inventory_light",
    "_show_section_list_loading_state",
    "_run_deferred_bootstrap",
    "_try_mark_progressive_full_ready",
    "_refresh_inventory",
    "_finalize_full_list_render",
}

_LIFECYCLE_CONSTANTS = (
    "_GF_LOADING_OVERLAY_TEXT",
    "_CONTROL_COL_MINSIZE",
    "_PROGRESSIVE_BOOT_ENV",
    "_EAGER_BOOT_ENV",
    "_GF_SECTION_FIRST_VISIBLE_DEFER_MS",
    "_GF_INIT_REFRESH_LIGHT_DEFER_MS",
    "_GF_MICRO_DEFER_MS",
    "_GF_F1_DEFER_MS",
    "_GF_LAZY_SHELL_ENV",
    "_GF_SHELL_EDITOR_DEFER_MS",
    "_GF_SHELL_CONTROL_DEFER_MS",
    "_GF_CONTROL_LATE_BUILD_DEFER_MS",
    "_GF_SKELETON_SECTION_TEXT",
    "_GF_SKELETON_EDITOR_TEXT",
    "_GF_SKELETON_CONTROL_TEXT",
)

_DEAD_CONSTANTS = (
    "_SECTION_LABEL_MAX_CHARS",
    "_GF_BOOT_DEFER_MS",
    "_GF_SHELL_SECTIONS_DEFER_MS",
    "_GF_WORKSPACE_LOADING_TEXT",
    "_GF_EDITOR_STALE_REFRESH_STATUS_TEXT",
    "_GF_PERCEIVED_READY_DEFER_MS",
)

_HOST_RETAINED = (
    "__init__",
    "_editor_micro_defer_ms",
    "_progressive_boot_enabled_for_selection",
    "_apply_edit_to_draft",
)

_HOST_STATE_ATTRS = (
    "_visual_bootstrap_complete",
    "_visual_enter_mono",
    "_loading_overlay",
    "_progressive_bootstrap_started",
    "_inventory_light_ready",
    "_shell_sections_built",
    "_shell_editor_built",
    "_shell_control_built",
    "_merged",
    "_merged_by_id",
    "_selected_id",
    "_page_draft",
    "_inventory",
    "_init_refresh_light_scheduled",
    "_pending_section_list_render",
    "_perceived_ready_logged",
    "_atomic_reveal_ready_logged",
)


def _host_defines_method(name: str, host_text: str) -> bool:
    return f"def {name}(" in host_text


def _host_defines_constant(name: str, host_text: str) -> bool:
    return bool(re.search(rf"^\s*{re.escape(name)}\s*=", host_text, re.MULTILINE))


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}("
    assert marker in text, name
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def _sample_merged(element_id: str, **overrides: Any) -> MergedPageElement:
    base = dict(
        element_id=element_id,
        section_key="section-1",
        element_type="media_section",
        group="content",
        order=1,
        label="Label",
        title="Title",
        text="Body",
        image_ref="img.png",
        alt="Alt",
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


class _FakeBooleanVar:
    def __init__(self, value: bool = False) -> None:
        self._value = value

    def get(self) -> bool:
        return self._value

    def set(self, value: bool) -> None:
        self._value = value


class _FakeWidget:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.master = args[0] if args else kwargs.get("master")
        self.kwargs = dict(kwargs)
        self.children: list[Any] = []
        self.pack_calls: list[dict[str, Any]] = []
        self.pack_forget_calls = 0
        self.place_calls: list[dict[str, Any]] = []
        self.place_forget_calls = 0
        self.lift_calls = 0
        self.destroy_calls = 0
        self._exists = True
        self._manager = ""

    def pack(self, **kwargs: Any) -> None:
        self.pack_calls.append(dict(kwargs))
        self._manager = "pack"

    def pack_forget(self) -> None:
        self.pack_forget_calls += 1
        self._manager = ""

    def place(self, **kwargs: Any) -> None:
        self.place_calls.append(dict(kwargs))
        self._manager = "place"

    def place_forget(self) -> None:
        self.place_forget_calls += 1
        self._manager = ""

    def lift(self) -> None:
        self.lift_calls += 1

    def destroy(self) -> None:
        self.destroy_calls += 1
        self._exists = False

    def winfo_children(self) -> list[Any]:
        return list(self.children)

    def winfo_exists(self) -> bool:
        return self._exists

    def winfo_manager(self) -> str:
        return self._manager


class _FakeSpan:
    def __init__(self, _name: str, **_kwargs: Any) -> None:
        pass

    def __enter__(self) -> "_FakeSpan":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def _patch_fake_ctk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.ctk.CTkFrame", _FakeWidget)
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.ctk.CTkLabel", _FakeWidget)
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.ctk.CTkButton", _FakeWidget)
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.theme.get_font", lambda *_a, **_k: "Arial 10")
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.theme.AppBg", "#000")
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.theme.TextMuted", "#888")
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.theme.TextPrimary", "#fff")
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.theme.BorderSubtle", "#222")
    monkeypatch.setattr(f"{LIFECYCLE_PATCH}.span", _FakeSpan)
    monkeypatch.setattr(
        f"{LIFECYCLE_PATCH}._make_gf_card",
        lambda parent, **_k: _FakeWidget(master=parent),
    )
    monkeypatch.setattr(
        f"{LIFECYCLE_PATCH}._make_secondary_button",
        lambda parent, _label, _cmd: _FakeWidget(master=parent),
    )


class GicleeFrameLifecycleHarness(GicleeFrameLifecycleInventoryMixin):
    def __init__(self) -> None:
        self._on_back = None
        self._back_button: _FakeWidget | None = None
        self._on_status = None
        self._page_draft = GicleeFramePageDraft()
        self._inventory = None
        self._merged: list[MergedPageElement] = []
        self._merged_by_id: dict[str, MergedPageElement] = {}
        self._section_tree_rows_cache: list[Any] = []
        self._section_dropdown_options_cache: list[Any] = []
        self._selected_id: str | None = None
        self._selection_generation = 0
        self._visual_bootstrap_complete = False
        self._visual_enter_mono: float | None = None
        self._visual_idle_logged = False
        self._loading_overlay: _FakeWidget | None = None
        self._atomic_reveal_overlay_shown = False
        self._atomic_reveal_ready_logged = False
        self._perceived_ready_logged = False
        self._inventory_light_ready = False
        self._shell_sections_built = False
        self._shell_editor_built = False
        self._shell_control_built = False
        self._shell_control_skeleton_built = False
        self._editor_form_shell_ready = False
        self._section_list_first_visible_built = False
        self._top_bar_actions_late_started = False
        self._top_bar_actions_late_done = False
        self._control_late_build_started = False
        self._control_late_build_done = False
        self._progressive_bootstrap_started = False
        self._progressive_full_ready_logged = False
        self._progressive_section_list_complete = False
        self._f1_deferred_built = False
        self._f1_panel: _FakeWidget | None = None
        self._f1_expanded = _FakeBooleanVar(value=False)
        self._workspace_frame = None
        self._sections_column = None
        self._editor_column = None
        self._control_column = None
        self._section_list_scroll = None
        self._section_list_static_lane = None
        self._section_list_static_lane_real_rows = False
        self._section_list_scroll_upgrade_done = False
        self._section_list_column = None
        self._section_row_frames: dict[str, Any] = {}
        self._section_row_ids: list[str] = []
        self._pending_section_list_render = False
        self._init_refresh_light_scheduled = False
        self._sections_column_early_lane_scheduled_mono = None
        self._section_list_column_ready_mono = None
        self._sections_column_early_lane_enter_mono = None
        self._shell_editor_deferred_scheduled_mono = None
        self._shell_control_deferred_scheduled_mono = None
        self._visible_prewarm_suppressed_logged = False
        self._after_calls: list[tuple[int, Any]] = []
        self._after_idle_calls: list[Any] = []
        self._cancel_selection_calls = 0
        self._cancel_page_context_calls = 0
        self._cancel_details_calls = 0
        self._update_top_bar_calls = 0
        self._render_section_menu_calls = 0
        self._highlight_calls = 0
        self._placeholder_calls = 0
        self._select_element_calls: list[str] = []
        self._populate_pending_calls: list[tuple[str, int]] = []
        self._defer_background_calls: list[dict[str, Any]] = []
        self._winfo_exists = True

    def after(self, delay_ms: int, callback: Any) -> str:
        self._after_calls.append((delay_ms, callback))
        return f"after-{len(self._after_calls)}"

    def after_idle(self, callback: Any) -> None:
        self._after_idle_calls.append(callback)

    def winfo_exists(self) -> bool:
        return self._winfo_exists

    def _cancel_selection_jobs(self) -> None:
        self._cancel_selection_calls += 1

    def _cancel_page_context_jobs(self) -> None:
        self._cancel_page_context_calls += 1

    def _cancel_details_on_demand_jobs(self) -> None:
        self._cancel_details_calls += 1

    def _update_top_bar(self) -> None:
        self._update_top_bar_calls += 1

    def _render_section_menu(self) -> None:
        self._render_section_menu_calls += 1

    def _highlight_section_row(self) -> None:
        self._highlight_calls += 1

    def _show_editor_placeholder_state(self) -> None:
        self._placeholder_calls += 1

    def _show_editor_selection_pending_state(self, _m: MergedPageElement) -> None:
        return None

    def _ensure_preserved_selection_populate_after_inventory_light(
        self,
        element_id: str,
        generation: int,
    ) -> None:
        self._populate_pending_calls.append((element_id, generation))

    def _select_element(self, element_id: str) -> None:
        self._select_element_calls.append(element_id)
        self._selected_id = element_id

    def _update_section_list_trigger(self) -> None:
        return None

    def _defer_background_for_selection(self, **kwargs: Any) -> bool:
        self._defer_background_calls.append(dict(kwargs))
        return False

    def _should_suppress_visible_prewarm(self) -> bool:
        return False

    def _build_context_bar(self) -> None:
        return None

    def _build_command_bar(self, _parent: Any) -> None:
        return None

    def _build_f1_brand_section_placeholder(self) -> None:
        return None

    def _build_f1_brand_section_full(self) -> None:
        return None

    def _build_f1_brand_section_deferred(self) -> None:
        return None

    def _build_f1_brand_section_panel_content(self) -> None:
        return None

    def _build_editor_column_deferred(self) -> None:
        return None

    def _build_control_column_deferred(self) -> None:
        return None

    def _schedule_top_bar_actions_late_build(self) -> None:
        return None

    def _schedule_sections_column_early_lane(self) -> None:
        return None

    def _build_sections_column(self, _parent: Any) -> _FakeWidget:
        return _FakeWidget()

    def _build_editor_column(self, _parent: Any) -> _FakeWidget:
        return _FakeWidget()

    def _build_control_structure_card(self, _col: Any) -> None:
        return None

    def _build_control_readiness_card(self, _col: Any) -> None:
        return None

    def _build_safety_card(self, _col: Any) -> None:
        return None

    def _build_context_bar_actions_late(self) -> None:
        self._top_bar_actions_late_done = True

    def _build_command_bar_primary_actions_late(self) -> None:
        return None

    def _build_command_bar_secondary_actions_late(self) -> None:
        return None

    def _micro_deferred_editor_form_shell(self) -> None:
        self._editor_form_shell_ready = True

    def _render_section_list_incremental(self) -> None:
        return None

    def _try_refresh_static_lane_before_scroll_upgrade(self) -> None:
        return None

    def _create_section_list_scroll_frame(self, _card: Any) -> None:
        self._section_list_scroll = _FakeWidget()

    def _fill_page_readiness(self, _m: Any) -> None:
        return None


# --- Structural / contract ---


def test_lifecycle_exact_current_method_ownership_and_identity() -> None:
    assert len(_EXPECTED_METHODS) == 63
    mixin_methods = {
        name
        for name, value in GicleeFrameLifecycleInventoryMixin.__dict__.items()
        if callable(value) and not name.startswith("__")
    }
    assert mixin_methods == _EXPECTED_METHODS
    for name in _EXPECTED_METHODS:
        assert name not in GicleeFrameView.__dict__
        assert getattr(GicleeFrameView, name) is getattr(
            GicleeFrameLifecycleInventoryMixin,
            name,
        )


def test_lifecycle_module_exports_constants_and_helpers() -> None:
    expected_all = (
        "GicleeFrameLifecycleInventoryMixin",
        *_LIFECYCLE_CONSTANTS,
        "_env_enabled",
        "_progressive_boot_enabled",
        "_lazy_shell_enabled",
    )
    assert lifecycle_module.__all__ == expected_all
    assert _GF_LOADING_OVERLAY_TEXT == "Przygotowuję GICLÉE FRAME…"
    assert _CONTROL_COL_MINSIZE == 320
    assert _PROGRESSIVE_BOOT_ENV == "GICLEE_GF_PROGRESSIVE_BOOT"
    assert _EAGER_BOOT_ENV == "GICLEE_GF_EAGER_BOOT"
    assert _GF_SECTION_FIRST_VISIBLE_DEFER_MS == 0
    assert _GF_INIT_REFRESH_LIGHT_DEFER_MS == 0
    assert _GF_MICRO_DEFER_MS == 16
    assert _GF_F1_DEFER_MS == 60
    assert _GF_LAZY_SHELL_ENV == "GICLEE_GF_LAZY_SHELL"
    assert _GF_SHELL_EDITOR_DEFER_MS == 16
    assert _GF_SHELL_CONTROL_DEFER_MS == 30
    assert _GF_CONTROL_LATE_BUILD_DEFER_MS == 120
    assert _GF_SKELETON_SECTION_TEXT == "Ładowanie struktury sekcji…"
    assert _GF_SKELETON_EDITOR_TEXT == (
        "Wybierz sekcję po lewej stronie — edytor jest gotowy."
    )
    assert _GF_SKELETON_CONTROL_TEXT == "Kontrola i readiness pojawią się za chwilę."


def test_dead_constants_absent_from_host_mixin_and_all() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    for name in _DEAD_CONSTANTS:
        assert not _host_defines_constant(name, host_text), name
        assert not _host_defines_constant(name, lifecycle_text), name
        assert name not in lifecycle_module.__all__, name


def test_lifecycle_mixin_is_narrow_non_widget_boundary() -> None:
    assert GicleeFrameLifecycleInventoryMixin.__bases__ == (object,)
    assert "__init__" not in GicleeFrameLifecycleInventoryMixin.__dict__


def test_lifecycle_module_has_no_reverse_host_import() -> None:
    source = LIFECYCLE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "giclee_app.ui.gicleeframe_view"
            assert node.module != ".gicleeframe_view"


def test_lifecycle_module_has_no_write_network_or_deploy() -> None:
    source = LIFECYCLE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_roots = {"subprocess", "requests", "urllib", "socket", "http"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in forbidden_roots
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden_roots
    lowered = source.lower()
    assert "write_text(" not in lowered
    assert "deploy(" not in lowered


def test_lifecycle_module_does_not_mutate_page_draft() -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    assert "set_patch" not in lifecycle_text
    assert "def _apply_edit_to_draft" not in lifecycle_text


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


def test_host_retains_four_behavioral_methods() -> None:
    for name in _HOST_RETAINED:
        assert name in GicleeFrameView.__dict__
        assert name not in GicleeFrameLifecycleInventoryMixin.__dict__


def test_host_init_initializes_lifecycle_state() -> None:
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    init_block = _method_block(host_text, "__init__")
    for attr in _HOST_STATE_ATTRS:
        assert f"self.{attr}" in init_block, attr


def test_lifecycle_source_ownership_in_module() -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    host_text = VIEW_PATH.read_text(encoding="utf-8")
    for name in _EXPECTED_METHODS:
        assert _host_defines_method(name, lifecycle_text), name
        assert not _host_defines_method(name, host_text), name


# --- Env helpers ---


@pytest.mark.parametrize(
    ("env_value", "default", "expected"),
    [
        (None, False, False),
        (None, True, True),
        ("1", False, True),
        ("true", False, True),
        ("YES", False, True),
        ("on", False, True),
        ("debug", False, True),
        ("0", True, False),
        ("false", True, False),
        ("off", True, False),
    ],
)
def test_env_enabled_truth_table(
    env_value: str | None,
    default: bool,
    expected: bool,
) -> None:
    env_name = "GICLEE_GF_TEST_ENV_FLAG"
    with patch.dict(os.environ, {}, clear=True):
        if env_value is not None:
            os.environ[env_name] = env_value
        assert _env_enabled(env_name, default=default) is expected


def test_progressive_boot_enabled_eager_override() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert _progressive_boot_enabled() is True
    with patch.dict(os.environ, {_EAGER_BOOT_ENV: "1"}, clear=True):
        assert _progressive_boot_enabled() is False
    with patch.dict(
        os.environ,
        {_EAGER_BOOT_ENV: "1", _PROGRESSIVE_BOOT_ENV: "1"},
        clear=True,
    ):
        assert _progressive_boot_enabled() is False
    with patch.dict(os.environ, {_PROGRESSIVE_BOOT_ENV: "0"}, clear=True):
        assert _progressive_boot_enabled() is False


def test_lazy_shell_enabled_defaults_and_explicit_off() -> None:
    with patch.dict(os.environ, {}, clear=True):
        assert _lazy_shell_enabled() is True
    with patch.dict(os.environ, {_GF_LAZY_SHELL_ENV: "0"}, clear=True):
        assert _lazy_shell_enabled() is False


def test_host_progressive_boot_adapter_delegates() -> None:
    view = object.__new__(GicleeFrameView)
    with patch.dict(os.environ, {}, clear=True):
        assert view._progressive_boot_enabled_for_selection() is True
    with patch.dict(os.environ, {_EAGER_BOOT_ENV: "true"}, clear=True):
        assert view._progressive_boot_enabled_for_selection() is False


def test_host_editor_micro_defer_ms_delegates() -> None:
    view = object.__new__(GicleeFrameView)
    assert view._editor_micro_defer_ms() == _GF_MICRO_DEFER_MS


# --- Lifecycle show/hide/back ---


def test_set_navigation_hides_back_when_none() -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._back_button = _FakeWidget()
    harness._back_button._manager = "pack"
    harness.set_navigation(on_back=None)
    assert harness._on_back is None
    assert harness._back_button.pack_forget_calls == 1


def test_set_navigation_shows_back_when_callback() -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._back_button = _FakeWidget()
    called: list[str] = []

    def _back() -> None:
        called.append("back")

    harness.set_navigation(on_back=_back)
    assert harness._back_button.pack_calls == [{"side": "right"}]
    harness._handle_back()
    assert called == ["back"]


def test_on_show_does_not_refresh_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    block = _method_block(lifecycle_text, "on_show")
    assert "_refresh_inventory" not in block
    assert "build_gicleeframe_page_inventory" not in block


def test_on_show_schedules_atomic_reveal_when_not_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameLifecycleHarness()
    harness._visual_bootstrap_complete = False
    schedule_calls: list[str] = []
    harness._schedule_atomic_reveal_check = lambda *, trigger: schedule_calls.append(trigger)  # type: ignore[method-assign]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness.on_show(cache_hit=True)
    assert schedule_calls == ["on_show"]
    assert "studio.gicleeframe.on_show" in events


def test_on_hide_cancels_jobs_and_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameLifecycleHarness()
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness.on_hide()
    assert harness._cancel_selection_calls == 1
    assert harness._cancel_page_context_calls == 1
    assert harness._cancel_details_calls == 1
    assert "studio.gicleeframe.on_hide" in events


# --- Model cache and timing ---


def test_set_merged_rebuilds_model_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameLifecycleHarness()
    merged = [_sample_merged("a1"), _sample_merged("b2")]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._set_merged(merged)
    assert harness._merged == merged
    assert "a1" in harness._merged_by_id
    assert "studio.gicleeframe.model_cache.ready" in events


def test_timing_helpers_return_ms() -> None:
    harness = GicleeFrameLifecycleHarness()
    assert harness._since_visual_enter_ms() is None
    harness._visual_enter_mono = time.perf_counter() - 0.01
    since = harness._since_visual_enter_ms()
    assert since is not None
    assert since >= 5.0
    start = time.perf_counter() - 0.005
    latency = harness._queue_latency_since_ms(start)
    assert latency is not None
    assert latency >= 1.0


def test_begin_visual_session_resets_idle_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._visual_idle_logged = True
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._begin_visual_session(cache_hit=True)
    assert harness._visual_idle_logged is False
    assert harness._visual_enter_mono is not None
    assert any(
        event == "studio.gicleeframe.visual.enter" and payload.get("cache_hit") is True
        for event, payload in events
    )


# --- Atomic reveal and loading overlay ---


def test_atomic_reveal_missing_gates() -> None:
    harness = GicleeFrameLifecycleHarness()
    assert harness._atomic_reveal_missing_gates() == [
        "sections",
        "editor",
        "control",
        "editor_form",
        "inventory",
    ]
    harness._shell_sections_built = True
    harness._shell_editor_built = True
    harness._shell_control_skeleton_built = True
    harness._editor_form_shell_ready = True
    harness._inventory_light_ready = True
    assert harness._atomic_reveal_missing_gates() == []


def test_try_atomic_reveal_logs_waiting_when_gates_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    events: list[tuple[str, dict[str, Any]]] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append((event, kwargs)),
    )
    harness._try_atomic_reveal(trigger="test")
    waiting = [
        (event, payload)
        for event, payload in events
        if event == "studio.gicleeframe.atomic_reveal.waiting_for"
    ]
    assert waiting
    assert "sections" in waiting[0][1]["missing_gates"]


def test_try_atomic_reveal_idempotent_when_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._visual_bootstrap_complete = True
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._try_atomic_reveal(trigger="again")
    assert events == []


def test_atomic_reveal_success_telemetry_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._shell_sections_built = True
    harness._shell_editor_built = True
    harness._shell_control_built = True
    harness._editor_form_shell_ready = True
    harness._inventory_light_ready = True
    harness._visual_enter_mono = time.perf_counter()
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._try_atomic_reveal(trigger="ready")
    assert events.index("studio.gicleeframe.atomic_reveal.minimal_ready") < events.index(
        "studio.gicleeframe.atomic_reveal.ready"
    )
    assert events.index("studio.gicleeframe.atomic_reveal.ready") < events.index(
        "studio.gicleeframe.atomic_reveal.revealed"
    )
    assert "studio.gicleeframe.visual.visible_ready" in events
    assert harness._visual_bootstrap_complete is True


def test_loading_overlay_show_hide_and_tcl_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fake_ctk(monkeypatch)
    harness = GicleeFrameLifecycleHarness()
    harness._show_loading_overlay()
    assert harness._loading_overlay is not None
    assert harness._loading_overlay.place_calls

    class _TclOverlay(_FakeWidget):
        def place_forget(self) -> None:
            raise tk.TclError("gone")

    harness._loading_overlay = _TclOverlay()
    harness._hide_loading_overlay()


def test_mark_idle_ready_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._visual_enter_mono = time.perf_counter()
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._mark_idle_ready()
    harness._mark_idle_ready()
    assert events.count("studio.gicleeframe.visual.idle_ready") == 1


def test_try_mark_perceived_ready_missing_and_ready_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._visual_enter_mono = time.perf_counter()
    events: list[str] = []
    schedule_triggers: list[str] = []
    harness._schedule_atomic_reveal_check = lambda *, trigger: schedule_triggers.append(trigger)  # type: ignore[method-assign]
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._try_mark_perceived_ready(trigger="gate")
    assert "studio.gicleeframe.visual.perceived_ready_gate_check" in events
    harness._shell_sections_built = True
    harness._shell_editor_built = True
    harness._shell_control_skeleton_built = True
    harness._section_list_first_visible_built = True
    harness._try_mark_perceived_ready(trigger="ready")
    assert "studio.gicleeframe.visual.perceived_ready" in events
    assert schedule_triggers == ["ready"]


# --- Shell routing and deferred scheduling ---


def test_build_shell_lazy_path_schedules_deferred_columns() -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    block = _method_block(lifecycle_text, "_build_shell")
    lazy_block = block.split("if _lazy_shell_enabled():", 1)[1].split("\n        else:", 1)[0]
    assert "_build_page_editor_section_critical()" in lazy_block
    assert "_GF_SHELL_EDITOR_DEFER_MS" in lazy_block
    assert "_GF_SHELL_CONTROL_DEFER_MS" in lazy_block
    assert "studio.gicleeframe.shell.critical_ready" in lazy_block


def test_build_shell_eager_non_lazy_schedules_f1_defer() -> None:
    lifecycle_text = LIFECYCLE_PATH.read_text(encoding="utf-8")
    block = _method_block(lifecycle_text, "_build_shell")
    eager_block = block.split("\n        else:", 1)[1]
    assert "_build_page_editor_section()" in eager_block
    assert "_GF_F1_DEFER_MS" in eager_block
    assert "after(_GF_F1_DEFER_MS, self._build_f1_brand_section_deferred)" in eager_block


def test_clear_column_children_tcl_fallback() -> None:
    harness = GicleeFrameLifecycleHarness()
    parent = _FakeWidget()

    class _BadChild(_FakeWidget):
        def destroy(self) -> None:
            raise tk.TclError("destroy failed")

    parent.children = [_BadChild()]
    harness._clear_column_children(parent)
    harness._clear_column_children(None)


# --- Inventory async and selection ---


def test_schedule_init_refresh_light_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    harness = GicleeFrameLifecycleHarness()
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._schedule_init_refresh_light()
    harness._schedule_init_refresh_light()
    assert events.count("studio.gicleeframe.init_refresh.light_scheduled") == 1


def test_run_init_refresh_light_deferred_uses_run_async(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    async_calls: list[Any] = []

    def _fake_run_async(_self, worker, on_success, on_error=None) -> None:
        async_calls.append((worker, on_success, on_error))
        on_success(SimpleNamespace(elements=()))

    monkeypatch.setattr(lifecycle_module, "run_async", _fake_run_async)
    monkeypatch.setattr(
        lifecycle_module,
        "build_gicleeframe_page_inventory",
        lambda _dir: SimpleNamespace(elements=()),
    )
    monkeypatch.setattr(lifecycle_module, "find_components_dir", lambda: Path("."))
    harness._run_init_refresh_light_deferred()
    assert async_calls


def test_finish_init_refresh_light_error_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    refresh_calls: list[Any] = []
    harness._refresh_inventory_light = lambda **kwargs: refresh_calls.append(kwargs)  # type: ignore[method-assign]
    harness._bootstrap_section_list_after_inventory_light = lambda: None  # type: ignore[method-assign]
    harness._ensure_atomic_reveal_prerequisites = lambda: None  # type: ignore[method-assign]
    harness._schedule_atomic_reveal_check = lambda *, trigger: None  # type: ignore[method-assign]
    monkeypatch.setattr(lifecycle_module, "log_event", lambda *_a, **_k: None)
    harness._finish_init_refresh_light(None)
    assert harness._inventory_light_ready is True
    assert refresh_calls


def test_refresh_inventory_light_preserves_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._selected_id = "keep-me"
    inv = SimpleNamespace(elements=())
    merged = [_sample_merged("keep-me")]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "build_gicleeframe_page_inventory",
        lambda _dir: inv,
    )
    monkeypatch.setattr(
        lifecycle_module,
        "merge_inventory_with_draft",
        lambda _inv, _draft: merged,
    )
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._refresh_inventory_light(warn_if_draft=False)
    assert harness._selected_id == "keep-me"
    assert "studio.gicleeframe.selection.preserved_after_inventory_light" in events


def test_refresh_inventory_light_clears_missing_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._selected_id = "gone"
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "build_gicleeframe_page_inventory",
        lambda _dir: SimpleNamespace(elements=()),
    )
    monkeypatch.setattr(
        lifecycle_module,
        "merge_inventory_with_draft",
        lambda _inv, _draft: [_sample_merged("other")],
    )
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._refresh_inventory_light(warn_if_draft=False)
    assert harness._selected_id is None
    assert "studio.gicleeframe.selection.cleared_after_inventory_light" in events


def test_run_init_refresh_light_skips_destroyed_widget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._winfo_exists = False
    called = {"async": False}

    def _fake_run_async(*_args: Any, **_kwargs: Any) -> None:
        called["async"] = True

    monkeypatch.setattr(lifecycle_module, "run_async", _fake_run_async)
    harness._run_init_refresh_light_deferred()
    assert called["async"] is False


# --- Progressive bootstrap and final list ---


def test_schedule_section_list_incremental_defers_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._section_dropdown_options_cache = [SimpleNamespace(element_id="x")]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._schedule_section_list_incremental()
    assert harness._after_calls
    assert harness._after_calls[0][0] == _GF_SECTION_FIRST_VISIBLE_DEFER_MS
    assert "studio.gicleeframe.section_list.incremental_scheduled" in events


def test_run_deferred_bootstrap_priority_guard() -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._defer_background_for_selection = lambda **kwargs: True  # type: ignore[method-assign, return-value]
    harness._run_deferred_bootstrap()
    assert harness._progressive_bootstrap_started is False


def test_try_mark_progressive_full_ready_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._progressive_section_list_complete = True
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    with patch.dict(os.environ, {}, clear=True):
        harness._try_mark_progressive_full_ready()
        harness._try_mark_progressive_full_ready()
    assert events.count("studio.gicleeframe.visual.full_ready_progressive") == 1


def test_finalize_full_list_render_progressive_skips_initial_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    options = [
        SectionDropdownOption(element_id="e1", display_label="One"),
    ]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    with patch.dict(os.environ, {}, clear=True):
        harness._finalize_full_list_render(options, time.perf_counter())
    assert harness._selected_id is None
    assert harness._placeholder_calls == 1
    assert "studio.gicleeframe.initial_selection.skipped_progressive" in events


def test_finalize_full_list_render_eager_selects_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    options = [
        SectionDropdownOption(element_id="e1", display_label="One"),
    ]
    monkeypatch.setattr(lifecycle_module, "log_event", lambda *_a, **_k: None)
    with patch.dict(os.environ, {_EAGER_BOOT_ENV: "1"}, clear=True):
        harness._finalize_full_list_render(options, time.perf_counter())
    assert harness._select_element_calls == ["e1"]


def test_prewarm_suppression_and_control_late_priority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = GicleeFrameLifecycleHarness()
    harness._control_column = _FakeWidget()
    harness._control_late_build_done = False
    harness._should_suppress_visible_prewarm = lambda: True  # type: ignore[method-assign, return-value]
    events: list[str] = []
    monkeypatch.setattr(
        lifecycle_module,
        "log_event",
        lambda event, **kwargs: events.append(event),
    )
    harness._build_control_late_cards()
    assert "studio.gicleeframe.visible_prewarm.suppressed" in events
