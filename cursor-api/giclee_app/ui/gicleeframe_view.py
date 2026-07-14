"""GICLÉE FRAME™ — F2.2.4 premium visual language + F2.2.5 section workbench + F2.2.6 layer navigation (RAM only)."""

from __future__ import annotations

import inspect
import os
import sys
import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from giclee_app.studio.perf import log_event, span
from giclee_app.studio.gicleeframe_draft_state import (
    GicleeFrameDraftState,
)
from giclee_app.studio.gicleeframe_page_draft import (
    DRAFT_RAM_DISCLAIMER,
    GicleeFramePageDraft,
    MergedPageElement,
    editor_field_visibility,
    merge_inventory_with_draft,
    SectionDropdownOption,
    SectionTreeRow,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    PageInventoryReport,
)
from . import theme
from .gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from .gicleeframe_view_page_readiness import GicleeFramePageReadinessMixin
from .gicleeframe_view_structure_dry_run import (
    GicleeFrameStructureDryRunMixin,
)
from .gicleeframe_view_safety import GicleeFrameSafetyCardMixin
from .gicleeframe_view_readiness_row import GicleeFrameReadinessRowMixin
from .gicleeframe_view_top_bar import GicleeFrameTopBarMixin
from .gicleeframe_view_ram_variants import GicleeFrameRamVariantMixin
from .gicleeframe_view_section_list_shell import (
    GicleeFrameSectionListShellMixin,
)
from .gicleeframe_view_section_list_rendering import (
    GicleeFrameSectionListRenderingMixin,
)
from .gicleeframe_view_section_list_interaction import (
    GicleeFrameSectionListInteractionMixin,
)
from .gicleeframe_view_selection_orchestration import (
    GicleeFrameSelectionOrchestrationMixin,
)
from .gicleeframe_view_editor_shell import GicleeFrameEditorShellMixin
from .gicleeframe_view_details_on_demand import GicleeFrameDetailsOnDemandMixin
from .gicleeframe_view_visual_detail_renderers import GicleeFrameVisualDetailRenderersMixin
from .gicleeframe_view_page_context import GicleeFramePageContextMixin
from .gicleeframe_view_lifecycle_inventory import (
    GicleeFrameLifecycleInventoryMixin,
    _GF_MICRO_DEFER_MS,
    _progressive_boot_enabled,
)
from .gicleeframe_view_models import (
    PageContextRowSpec,
    SectionVisualCacheEntry,
)


class GicleeFrameView(
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
):
    uses_async_first_paint = True

    def _editor_micro_defer_ms(self) -> int:
        return _GF_MICRO_DEFER_MS

    def _progressive_boot_enabled_for_selection(self) -> bool:
        return _progressive_boot_enabled()

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_status: Callable[[str], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._on_status = on_status
        self._on_back = on_back
        self._back_button: ctk.CTkButton | None = None
        self._brand_draft = GicleeFrameDraftState()
        self._page_draft = GicleeFramePageDraft()
        self._inventory: PageInventoryReport | None = None
        self._merged: list[MergedPageElement] = []
        self._merged_by_id: dict[str, MergedPageElement] = {}
        self._section_tree_rows_cache: list[SectionTreeRow] = []
        self._section_dropdown_options_cache: list[SectionDropdownOption] = []
        self._highlighted_section_id: str | None = None
        self._selected_id: str | None = None

        self._top_meta_label: ctk.CTkLabel | None = None
        self._panel_status_label: ctk.CTkLabel | None = None
        self._working_variant_menu: ctk.CTkOptionMenu | None = None
        self._working_variant_map: dict[str, str] = {}
        self._change_count_label: ctk.CTkLabel | None = None
        self._workspace_frame: ctk.CTkFrame | None = None
        self._sections_column: ctk.CTkFrame | None = None
        self._editor_column: ctk.CTkFrame | None = None
        self._control_column: ctk.CTkFrame | None = None
        self._section_list_scroll: ctk.CTkScrollableFrame | None = None
        self._section_list_static_lane: ctk.CTkFrame | None = None
        self._section_list_static_lane_real_rows = False
        self._section_list_scroll_upgrade_scheduled = False
        self._section_list_scroll_upgrade_done = False
        self._section_list_scroll_upgrade_fallback_after_id: str | None = None
        self._section_list_extras_frame: ctk.CTkFrame | None = None
        self._section_dropdown_popup: ctk.CTkFrame | None = None
        self._section_list_trigger: ctk.CTkButton | None = None
        self._section_list_column: ctk.CTkFrame | None = None
        self._section_list_expanded = ctk.BooleanVar(value=False)
        self._section_outside_close_active = False
        self._section_row_frames: dict[str, ctk.CTkFrame] = {}
        self._section_row_ids: list[str] = []
        self._drag_from_index: int | None = None
        self._edit_panel: ctk.CTkFrame | None = None
        self._editor_status_dot: ctk.CTkLabel | None = None
        self._editor_section_subtitle: ctk.CTkLabel | None = None
        self._editor_ram_visibility_label: ctk.CTkLabel | None = None
        self._editor_header_visible_row: ctk.CTkFrame | None = None
        self._legacy_msg_label: ctk.CTkLabel | None = None
        self._section_preview_line: ctk.CTkFrame | None = None
        self._section_preview_card: ctk.CTkFrame | None = None
        self._section_preview_canvas: ctk.CTkFrame | None = None
        self._section_preview_badge: ctk.CTkLabel | None = None
        self._layer_nav_frame: ctk.CTkFrame | None = None
        self._identity_card: ctk.CTkFrame | None = None
        self._structure_dry_label: ctk.CTkLabel | None = None
        self._structure_dry_run_btn: ctk.CTkButton | None = None
        self._page_readiness_frame: ctk.CTkFrame | None = None
        self._page_readiness_body: ctk.CTkFrame | None = None
        self._page_readiness_toggle: ctk.CTkButton | None = None
        self._page_readiness_summary: ctk.CTkLabel | None = None
        self._page_readiness_badge: ctk.CTkLabel | None = None
        self._page_readiness_expanded = ctk.BooleanVar(value=False)
        self._notes_group_frame: ctk.CTkFrame | None = None

        self._title_row: ctk.CTkFrame | None = None
        self._text_row: ctk.CTkFrame | None = None
        self._alt_row: ctk.CTkFrame | None = None
        self._image_ref_row: ctk.CTkFrame | None = None
        self._page_context_frame: ctk.CTkFrame | None = None
        self._page_context_inner: ctk.CTkFrame | None = None
        self._page_setting_widgets: dict[str, ctk.CTkBaseClass] = {}
        self._page_context_row_cache: dict[str, ctk.CTkFrame] = {}
        self._page_context_value_widgets: dict[str, ctk.CTkBaseClass] = {}
        self._page_context_visible_keys: set[str] = set()
        self._page_context_row_managers: dict[str, str] = {}
        self._page_context_settings_layout: str = ""
        self._page_context_last_signature: tuple[str, ...] = ()
        self._page_context_readonly_body: ctk.CTkFrame | None = None
        self._page_context_divider_group_bodies: dict[str, ctk.CTkFrame] = {}
        self._page_context_divider_group_grid_opts: dict[str, dict[str, object]] = {}
        self._page_context_setting_card_bodies: dict[str, ctk.CTkFrame] = {}
        self._page_context_after_ids: list[str] = []
        self._page_context_generation = 0
        self._selection_generation = 0
        self._selection_after_ids: list[str] = []
        self._selection_click_mono: float | None = None
        self._selection_populate_scheduled_mono: float | None = None
        self._selection_priority_generation: int | None = None
        self._selection_priority_until_mono: float | None = None
        self._selection_priority_end_after_id: str | None = None
        self._page_context_loading_label: ctk.CTkLabel | None = None
        self._page_context_shell_shown_generation = 0
        self._media_deferred_done_after_id: str | None = None
        self._page_context_specs_cache: dict[str, list[PageContextRowSpec]] = {}
        self._page_context_collapsed_group_rows: dict[str, ctk.CTkFrame] = {}
        self._page_context_collapsed_group_bodies: dict[str, ctk.CTkFrame] = {}
        self._page_context_collapsed_group_buttons: dict[str, ctk.CTkButton] = {}
        self._page_context_expanded_group_ids: set[str] = set()
        self._active_setting_editor_row: ctk.CTkFrame | None = None
        self._active_setting_editor_key: str | None = None
        self._page_context_summary_rows: dict[str, ctk.CTkFrame] = {}
        self._page_context_summary_value_labels: dict[str, ctk.CTkLabel] = {}
        self._layer_nav_tile_cache: dict[str, ctk.CTkFrame] = {}
        self._layer_nav_title_widgets: dict[str, ctk.CTkLabel] = {}
        self._layer_nav_meta_widgets: dict[str, ctk.CTkLabel] = {}
        self._layer_nav_visible_keys: set[str] = set()
        self._layer_nav_row_frame: ctk.CTkFrame | None = None
        self._layer_nav_header_label: ctk.CTkLabel | None = None
        self._layer_nav_rendered_signatures: dict[str, tuple[Any, ...]] = {}
        self._layer_nav_bound_targets: dict[str, str] = {}
        self._layer_nav_visible_order: tuple[str, ...] = ()
        self._preview_frame_cache: dict[str, ctk.CTkFrame] = {}
        self._preview_value_widgets: dict[str, dict[str, ctk.CTkBaseClass]] = {}
        self._preview_active_key: str | None = None
        self._preview_shell_bootstrapped: bool = False
        self._preview_bootstrap_panel: ctk.CTkFrame | None = None
        self._preview_bootstrap_status_label: ctk.CTkLabel | None = None
        self._notes_row: ctk.CTkFrame | None = None
        self._visible_row: ctk.CTkFrame | None = None
        self._children_overview_row: ctk.CTkFrame | None = None
        self._children_overview_buttons: ctk.CTkFrame | None = None

        self._title_entry: ctk.CTkEntry | None = None
        self._text_box: ctk.CTkTextbox | None = None
        self._alt_entry: ctk.CTkEntry | None = None
        self._image_ref_entry: ctk.CTkEntry | None = None
        self._notes_box: ctk.CTkTextbox | None = None
        self._visible_var: ctk.BooleanVar | None = None

        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._placement_menu: ctk.CTkOptionMenu | None = None
        self._variant_map: dict[str, str] = {}
        self._placement_map: dict[str, str] = {}
        self._plan_body_label: ctk.CTkLabel | None = None
        self._brand_readiness_frame: ctk.CTkFrame | None = None
        self._f1_panel: ctk.CTkFrame | None = None
        self._f1_expanded = ctk.BooleanVar(value=False)
        self._visual_bootstrap_complete: bool = False
        self._visual_enter_mono: float | None = None
        self._visual_idle_logged: bool = False
        self._loading_overlay: ctk.CTkFrame | None = None
        self._progressive_bootstrap_started = False
        self._progressive_full_ready_logged = False
        self._progressive_section_list_complete = False
        self._f1_deferred_built = False
        self._shell_sections_built = False
        self._shell_editor_built = False
        self._shell_control_built = False
        self._shell_control_skeleton_built = False
        self._section_list_first_visible_built = False
        self._control_late_build_started = False
        self._control_late_build_done = False
        self._editor_identity_late_build_started = False
        self._editor_identity_late_build_done = False
        self._editor_identity_prewarm_scheduled = False
        self._editor_rows_prewarm_scheduled = False
        self._top_bar_actions_late_started = False
        self._top_bar_actions_late_done = False
        self._context_bar_row: ctk.CTkFrame | None = None
        self._context_bar_actions_slot: ctk.CTkFrame | None = None
        self._context_bar_actions_placeholder: ctk.CTkFrame | None = None
        self._context_bar_back_slot: ctk.CTkFrame | None = None
        self._context_bar_back_placeholder: ctk.CTkFrame | None = None
        self._command_bar_inner: ctk.CTkFrame | None = None
        self._command_bar_primary_slot: ctk.CTkFrame | None = None
        self._command_bar_primary_placeholder: ctk.CTkFrame | None = None
        self._command_bar_secondary_slot: ctk.CTkFrame | None = None
        self._command_bar_secondary_placeholder: ctk.CTkFrame | None = None
        self._workspace_skeleton_columns_built = False
        self._perceived_ready_logged = False
        self._atomic_reveal_ready_logged = False
        self._atomic_reveal_overlay_shown = False
        self._inventory_light_ready = False
        self._atomic_swap_suppress_visible = False
        self._atomic_swap_deferred_row_visibility: list[tuple[ctk.CTkFrame | None, bool]] = []
        self._sections_column_early_lane_scheduled = False
        self._sections_column_early_lane_scheduled_mono: float | None = None
        self._sections_column_early_lane_enter_mono: float | None = None
        self._section_list_column_ready_mono: float | None = None
        self._section_list_incremental_scheduled_mono: float | None = None
        self._section_list_incremental_enter_mono: float | None = None
        self._section_list_batch_after_id: str | None = None
        self._shell_editor_deferred_scheduled_mono: float | None = None
        self._shell_control_deferred_scheduled_mono: float | None = None
        self._sections_column_extras_built = False
        self._init_refresh_light_scheduled = False
        self._pending_section_list_render = False
        self._workspace_placeholder: ctk.CTkLabel | None = None
        self._editor_form_shell_ready = False
        self._editor_placeholder_label: ctk.CTkLabel | None = None
        self._title_row_built = False
        self._text_row_built = False
        self._alt_row_built = False
        self._image_ref_row_built = False
        self._notes_row_built = False
        self._children_overview_built = False
        self._page_context_shell_built = False
        self._section_visual_cache: dict[str, SectionVisualCacheEntry] = {}
        self._media_details_stable_frame: ctk.CTkFrame | None = None
        self._media_details_status_label: ctk.CTkLabel | None = None
        self._media_details_stable_built = False
        self._editor_stable_shell_logged_for: set[str] = set()
        self._selection_visual_cache_applied = False
        self._editor_has_ready_content = False
        self._editor_last_ready_element_id: str | None = None
        self._editor_refresh_status_frame: ctk.CTkFrame | None = None
        self._editor_refresh_status_label: ctk.CTkLabel | None = None
        self._details_on_demand_frame: ctk.CTkFrame | None = None
        self._details_on_demand_hint_label: ctk.CTkLabel | None = None
        self._details_on_demand_button: ctk.CTkButton | None = None
        self._details_on_demand_status_label: ctk.CTkLabel | None = None
        self._details_on_demand_built = False
        self._details_on_demand_element_id: str | None = None
        self._details_on_demand_expanded = False
        self._details_on_demand_after_ids: list[str] = []
        self._details_on_demand_generation = 0
        self._details_on_demand_request_mono: float | None = None
        self._details_cta_click_mono: float | None = None
        self._details_on_demand_active_element_id: str | None = None
        self._details_container_frame: ctk.CTkFrame | None = None
        self._details_container_built = False
        self._details_container_title_label: ctk.CTkLabel | None = None
        self._details_container_subtext_label: ctk.CTkLabel | None = None
        self._details_module_rows: dict[str, ctk.CTkFrame] = {}
        self._details_module_buttons: dict[str, ctk.CTkButton] = {}
        self._details_module_status_labels: dict[str, ctk.CTkLabel] = {}
        self._visible_prewarm_suppressed_logged = False

        _has_schedule_init_refresh_light = hasattr(
            type(self),
            "_schedule_init_refresh_light",
        )
        _has_init_refresh_light_scheduled_event = False
        if _has_schedule_init_refresh_light:
            try:
                _has_init_refresh_light_scheduled_event = (
                    "studio.gicleeframe.init_refresh.light_scheduled"
                    in inspect.getsource(type(self)._schedule_init_refresh_light)
                )
            except (OSError, TypeError):
                _has_init_refresh_light_scheduled_event = False
        log_event(
            "studio.gicleeframe.runtime_marker",
            phase_marker="6G.5-M",
            module_file=__file__,
            cwd=os.getcwd(),
            sys_executable=sys.executable,
            sys_path_0=sys.path[0] if len(sys.path) > 0 else "",
            sys_path_1=sys.path[1] if len(sys.path) > 1 else "",
            sys_path_2=sys.path[2] if len(sys.path) > 2 else "",
            has_schedule_init_refresh_light=_has_schedule_init_refresh_light,
            has_init_refresh_light_scheduled_event=_has_init_refresh_light_scheduled_event,
            sections_split_enabled=True,
        )
        log_event(
            "studio.gicleeframe.visual.enter",
            cache_hit=False,
            source="view_init",
        )
        self._visual_enter_mono = time.perf_counter()

        with span("studio.gicleeframe.init"):
            with span("studio.gicleeframe.build_shell"):
                self._build_shell()
            if _progressive_boot_enabled():
                log_event("studio.gicleeframe.progressive_boot.enabled")
                self._ensure_atomic_reveal_overlay()
                self._schedule_init_refresh_light()
            else:
                log_event("studio.gicleeframe.progressive_boot.disabled")
                self._ensure_atomic_reveal_overlay()
                with span("studio.gicleeframe.init_refresh"):
                    self._refresh_inventory(warn_if_draft=False)
                self._inventory_light_ready = True
                self._ensure_atomic_reveal_prerequisites()
                self._schedule_atomic_reveal_check(trigger="init_eager")

    def _apply_edit_to_draft(self) -> None:
        if self._selected_id is None:
            if self._on_status:
                self._on_status("Wybierz element z listy sekcji.")
            return
        m = self._merged_by_id.get(self._selected_id)
        if m is None:
            return

        fields: dict[str, object] = {}
        etype = m.element_type
        vis = editor_field_visibility(etype)

        if vis.title and self._title_entry:
            title = self._title_entry.get().strip()
            if title != m.title:
                fields["title"] = title or None
        if vis.text and self._text_box:
            text = self._text_box.get("1.0", "end").strip()
            if text != m.text:
                fields["text"] = text or None
        if vis.alt and self._alt_entry:
            alt = self._alt_entry.get().strip()
            if alt != m.alt:
                fields["alt"] = alt or None
        if vis.notes and self._notes_box:
            notes = self._notes_box.get("1.0", "end").strip()
            if notes != m.notes:
                fields["notes"] = notes or None
        if vis.visible and self._visible_var:
            visible = bool(self._visible_var.get())
            if visible != m.visible:
                fields["visible"] = visible

        settings_changes: dict[str, str] = {}
        for field in m.page_settings:
            widget = self._page_setting_widgets.get(field.key)
            if widget is None:
                continue
            if isinstance(widget, ctk.CTkOptionMenu):
                new_value = widget.get()
            elif isinstance(widget, ctk.CTkEntry):
                new_value = widget.get().strip()
            else:
                continue
            if new_value != field.value:
                settings_changes[field.key] = new_value
        if settings_changes:
            fields["settings"] = settings_changes

        if fields:
            self._page_draft.set_patch(self._selected_id, **fields)
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
            self._update_top_bar()
            self._render_section_menu()
            selected = self._merged_by_id.get(self._selected_id or "")
            if selected is not None:
                self._populate_editor(selected)
        if self._on_status:
            self._on_status(DRAFT_RAM_DISCLAIMER)
