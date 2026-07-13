"""GICLÉE FRAME™ — F2.2.4 premium visual language + F2.2.5 section workbench + F2.2.6 layer navigation (RAM only)."""

from __future__ import annotations

import inspect
import os
import sys
import time
import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.bg import run_async
from giclee_app.studio.perf import log_event, span
from giclee_app.studio.gicleeframe_brief import (
    COMPONENT_NAME,
    NEXT_PHASE_NOTE,
)
from giclee_app.studio.gicleeframe_draft_state import (
    GicleeFrameDraftState,
)
from giclee_app.studio.gicleeframe_page_draft import (
    ADD_VARIANT_RAM_LABEL,
    APPLY_RAM_DRAFT_LABEL,
    APPLY_RAM_MICROCOPY,
    CHECK_STRUCTURE_LABEL,
    CLEAR_VARIANT_RAM_LABEL,
    DEFAULT_VARIANT_NAME,
    DUPLICATE_VARIANT_LABEL,
    DRAFT_RAM_DISCLAIMER,
    GicleeFramePageDraft,
    MergedPageElement,
    PAGE_EDITOR_TITLE,
    PAGE_SOURCE_FILE,
    PANEL_STATUS_UNSAVED,
    RAM_ONLY_STATUS,
    REFRESH_INVENTORY_LABEL,
    RENAME_VARIANT_LABEL,
    SECTION_EDITOR_TITLE,
    SECTION_HIDDEN_RAM,
    SECTION_LIST_DRAG_HINT,
    SECTION_LIST_TITLE,
    SECTION_VISIBLE_RAM,
    STRUCTURE_EMPTY_STATE,
    WORKING_VARIANT_LABEL,
    EditorFieldVisibility,
    editor_context_rows,
    editor_field_visibility,
    editor_title_for_element,
    merge_inventory_with_draft,
    parent_row_title,
    reorder_page_blocks,
    section_dropdown_options,
    section_tree_rows,
    SectionDropdownOption,
    SectionTreeRow,
    working_variant_menu_label,
)
from giclee_app.studio.gicleeframe_page_dry_run import (
    build_page_structure_dry_run,
    format_structure_dry_run_summary,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    PageInventoryReport,
    build_gicleeframe_page_inventory,
    variant_environment_tag,
)
from giclee_app.studio.gicleeframe_page_settings import (
    PageSettingField,
    divider_setting_groups,
)
from giclee_app.studio.gicleeframe_readiness import (
    evaluate_gicleeframe_page_readiness,
    format_page_readiness_block,
)

from . import theme
from .gicleeframe_view_brand import GicleeFrameBrandPanelMixin
from .gicleeframe_view_page_readiness import GicleeFramePageReadinessMixin
from .gicleeframe_view_models import (
    PageContextRowSpec,
    SectionVisualCacheEntry,
    _ellipsize,
    _section_kind_copy,
)
from .gicleeframe_view_primitives import (
    _BTN_HEIGHT,
    _CARD_PAD_X,
    _CARD_PAD_Y,
    _GF_BG,
    _GF_BORDER,
    _GF_BORDER_WARM,
    _GF_CARD,
    _GF_CARD_SOFT,
    _GF_DANGER,
    _GF_FIELD,
    _GF_FIELD_HOVER,
    _GF_GOLD,
    _GF_GOLD_SOFT,
    _GF_MUTED,
    _GF_PANEL,
    _GF_PREVIEW_BG,
    _GF_PREVIEW_MAT,
    _GF_PREVIEW_PAPER,
    _GF_SUCCESS,
    _build_safety_row,
    _element_pill_colors,
    _f2_entry_kwargs,
    _f2_menu_kwargs,
    _make_card,
    _make_card_title,
    _make_empty_state,
    _make_gf_card,
    _make_pill,
    _make_primary_button,
    _make_secondary_button,
    _make_section_caption,
    _make_section_title,
    _make_status_pill,
    _make_surface,
)
from .widgets import status_color

_BACK_LABEL = "Wróć do huba"
_GF_LOADING_OVERLAY_TEXT = "Przygotowuję GICLÉE FRAME…"
_GF_ATOMIC_SWAP_STATUS_TEXT = "Przygotowuję sekcję…"
_GF_DETAILS_ON_DEMAND_TEXT = "Szczegóły sekcji są dostępne na żądanie."
_GF_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły"
_GF_MEDIA_DETAILS_ON_DEMAND_TEXT = (
    "Szczegóły mediów, warstwy i podgląd są dostępne na żądanie."
)
_GF_MEDIA_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły mediów"
_GF_DETAILS_ON_DEMAND_LOADING_TEXT = "Ładowanie szczegółów…"
_GF_DETAILS_SHELL_TITLE = "Szczegóły sekcji"
_GF_DETAILS_SHELL_SUBTEXT = "Wybierz, które szczegóły chcesz wczytać."
_GF_MEDIA_DETAILS_SHELL_SUBTEXT = (
    "Podgląd, warstwy i elementy mediów są dostępne osobno, żeby nie spowalniać edytora."
)
_GF_DETAILS_CACHE_HIT_STATUS = "Szczegóły załadowane"
_GF_DETAILS_MODULE_PREVIEW_TITLE = "Podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE = "Ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_TITLE = "Warstwy"
_GF_DETAILS_MODULE_CHILDREN_TITLE = "Elementy"
_GF_DETAILS_MODULE_PREVIEW_BUTTON = "Wczytaj podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON = "Wczytaj ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_BUTTON = "Wczytaj warstwy"
_GF_DETAILS_MODULE_CHILDREN_BUTTON = "Wczytaj elementy"
_GF_DETAILS_MODULE_IDLE_STATUS = "—"
_GF_DETAILS_MODULE_LOADED_STATUS = "Gotowe"
_GF_DETAILS_MODULE_LOADING_STATUS = "Ładowanie…"
_GF_DETAILS_STAGE_GAP_MS = 16
_GF_DETAILS_CHILDREN_BATCH_SIZE = 2
_GF_DETAILS_CONTAINER_HEIGHT = 148
_SHELL_STATUS_CHIP = "RAM-only · bez zapisu"
_SECTION_PLACEHOLDER = "— wybierz sekcję —"
_LEGACY_READONLY_MSG = (
    "Sekcja legacy — nie jest edytowana w Studio. "
    "Tylko notatka robocza opcjonalna."
)
_F2_FIELD_LABEL_WIDTH = 88
_SECTION_LIST_WIDTH = 320
_SECTION_LIST_HEIGHT = 520
_SECTION_ROW_GRIP = "⋮"
_EDITOR_FORM_WIDTH = 760
_CONTROL_COL_MINSIZE = 320
_EDITOR_HERO_PREVIEW_HEIGHT = 118
_SECTION_ROW_HEIGHT = 64
_SECTION_LABEL_MAX_CHARS = 42
_SAFETY_TITLE = "Bezpieczeństwo"
_PREVIEW_SETTINGS_CAPTION = "Podgląd ustawień"
_LAYER_NAV_TITLE = "Warstwy sekcji"
_IMAGE_SOURCE_TITLE = "Źródło grafiki"
_SAFETY_CHECKLIST: tuple[tuple[str, str], ...] = (
    ("RAM-only", "Zmiany tylko w pamięci sesji"),
    ("Brak zapisu motywu", "Panel nie zapisuje plików motywu"),
    ("Sync/deploy zablokowane", "Synchronizacja i wdrożenie wyłączone"),
    ("F3/F4 osobna decyzja", "Lokalny zapis i writer — po akceptacji"),
)

_PROGRESSIVE_BOOT_ENV = "GICLEE_GF_PROGRESSIVE_BOOT"
_EAGER_BOOT_ENV = "GICLEE_GF_EAGER_BOOT"
_GF_BOOT_DEFER_MS = 50
# Batching agresywniejszy: większe partie, minimalne przerwy — widok składa się
# w kilku klatkach zamiast "wjeżdżać" elementami przez ~2 sekundy.
_GF_SECTION_BATCH_SIZE = 8
_GF_SECTION_FIRST_BATCH_SIZE = 6
_GF_SECTION_BATCH_DELAY_MS = 0
_GF_SECTION_FIRST_VISIBLE_DEFER_MS = 0
_GF_SECTIONS_COLUMN_EARLY_DEFER_MS = 0
_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS = 40
_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS = 800
_GF_INIT_REFRESH_LIGHT_DEFER_MS = 0
_GF_MICRO_DEFER_MS = 16
_GF_F1_DEFER_MS = 60
_GF_LAZY_SHELL_ENV = "GICLEE_GF_LAZY_SHELL"
_GF_SHELL_SECTIONS_DEFER_MS = 10
_GF_SHELL_EDITOR_DEFER_MS = 16
_GF_SHELL_CONTROL_DEFER_MS = 30
_GF_CONTROL_LATE_BUILD_DEFER_MS = 120
_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS = 80
_GF_EDITOR_IDENTITY_LATE_DEFER_MS = 160
_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS = 200
_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS = 0
_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS = 30
_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS = 60
_GF_WORKSPACE_LOADING_TEXT = "Ładowanie edytora Giclée Frame…"
_GF_PROGRESSIVE_PAGE_CONTEXT_ENV = "GICLEE_GF_PROGRESSIVE_PAGE_CONTEXT"
_GF_PAGE_CONTEXT_BATCH_SIZE = 8
_GF_PAGE_CONTEXT_BATCH_DELAY_MS = 0
_GF_PAGE_CONTEXT_DEFER_MS = 10
_GF_SELECT_POPULATE_DEFER_MS = 0
_GF_SELECTION_PRIORITY_WINDOW_MS = 200
_GF_SELECTION_PRIORITY_YIELD_DEFER_MS = 60
_GF_PAGE_CONTEXT_STABLE_DEFER_MS = 80
_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT = "Ustawienia sekcji są aktualizowane…"
_GF_MEDIA_PREVIEW_AFTER_SHELL_MS = 20
_GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS = 40
_GF_MEDIA_CHILDREN_AFTER_SHELL_MS = 80
_GF_MEDIA_DETAILS_STATUS_TEXT = "Szczegóły mediów zostaną zaktualizowane…"
_GF_MEDIA_DETAILS_STABLE_HEIGHT = 88
_GF_EDITOR_STALE_REFRESH_STATUS_TEXT = "Aktualizuję dla wybranej sekcji…"
_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT = "Podgląd sekcji pojawi się po wyborze…"
_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV = "GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK"
_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE = 1
_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS = 0
_GF_PERCEIVED_READY_DEFER_MS = 32
_GF_SKELETON_SECTION_TEXT = "Ładowanie struktury sekcji…"
_GF_SKELETON_EDITOR_TEXT = "Wybierz sekcję po lewej stronie — edytor jest gotowy."
_GF_SKELETON_CONTROL_TEXT = "Kontrola i readiness pojawią się za chwilę."
_GF_SELECTION_LAYER_NAV_DEFER_MS = 16
_GF_SELECTION_CHILDREN_DEFER_MS = 32
_GF_SELECTION_CHILDREN_LATE_DEFER_MS = 80
_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS = 16
_DIVIDER_LAZY_GROUPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "line": ("Linia", ("thickness", "width_percent", "alignment_horizontal")),
    "layout": ("Układ", ("section_width", "padding-block-start", "padding-block-end")),
    "style": ("Styl", ("color_scheme", "corner_radius")),
}
_EDITOR_PLACEHOLDER_TEXT = (
    "Wybierz sekcję po lewej stronie, aby załadować podgląd i ustawienia."
)
_SECTION_LIST_LOADING_TEXT = "Ładowanie struktury sekcji…"


def _env_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


def _progressive_boot_enabled() -> bool:
    if _env_enabled(_EAGER_BOOT_ENV, default=False):
        return False
    return _env_enabled(_PROGRESSIVE_BOOT_ENV, default=True)


def _progressive_page_context_enabled() -> bool:
    return _env_enabled(_GF_PROGRESSIVE_PAGE_CONTEXT_ENV, default=True)


def _collapse_section_list_on_click_enabled() -> bool:
    return _env_enabled(_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV, default=False)


def _lazy_shell_enabled() -> bool:
    return _env_enabled(_GF_LAZY_SHELL_ENV, default=True)


class GicleeFrameView(
    GicleeFrameBrandPanelMixin,
    GicleeFramePageReadinessMixin,
    ctk.CTkScrollableFrame,
):
    uses_async_first_paint = True

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

    def set_navigation(self, *, on_back: Callable[[], None] | None = None) -> None:
        """Update cached view navigation without rebuilding the workbench."""
        self._on_back = on_back
        if self._back_button is None:
            return

        if on_back is None:
            self._back_button.pack_forget()
            return

        if not self._back_button.winfo_manager():
            self._back_button.pack(side="right")

    def _handle_back(self) -> None:
        if self._on_back is not None:
            self._on_back()

    def on_show(self, *, cache_hit: bool = False) -> None:
        if cache_hit:
            self._begin_visual_session(cache_hit=True)
        elif self._visual_enter_mono is None:
            self._begin_visual_session(cache_hit=False)

        if self._visual_bootstrap_complete:
            self._hide_loading_overlay()
        else:
            self._ensure_atomic_reveal_overlay()
            self._schedule_atomic_reveal_check(trigger="on_show")

        log_event(
            "studio.gicleeframe.on_show",
            selected_id=self._selected_id or "",
            merged_count=len(self._merged),
            draft_edits=self._page_draft.draft_edit_count(),
            cache_hit=cache_hit,
        )

    def on_hide(self) -> None:
        self._cancel_selection_jobs()
        self._cancel_page_context_jobs()
        self._cancel_details_on_demand_jobs()
        log_event(
            "studio.gicleeframe.on_hide",
            selected_id=self._selected_id or "",
            merged_count=len(self._merged),
            draft_edits=self._page_draft.draft_edit_count(),
        )

    def _rebuild_page_model_cache(self) -> None:
        """Rebuild derived RAM-only lookup structures for fast section selection."""
        with span("studio.gicleeframe.model_cache.rebuild", merged_count=len(self._merged)):
            self._merged_by_id = {item.element_id: item for item in self._merged}
            self._section_tree_rows_cache = section_tree_rows(self._merged)
            self._section_dropdown_options_cache = section_dropdown_options(
                self._merged,
                rows=self._section_tree_rows_cache,
            )

        log_event(
            "studio.gicleeframe.model_cache.ready",
            merged_count=len(self._merged),
            lookup_count=len(self._merged_by_id),
            tree_rows=len(self._section_tree_rows_cache),
            dropdown_options=len(self._section_dropdown_options_cache),
        )

    def _set_merged(self, merged: list[MergedPageElement]) -> None:
        self._merged = merged
        self._rebuild_page_model_cache()

    def _since_visual_enter_ms(self) -> float | None:
        if self._visual_enter_mono is None:
            return None
        return round((time.perf_counter() - self._visual_enter_mono) * 1000, 2)

    def _queue_latency_since_ms(self, since_mono: float | None) -> float | None:
        if since_mono is None:
            return None
        return round((time.perf_counter() - since_mono) * 1000, 2)

    def _since_selection_click_ms(self) -> float | None:
        if self._selection_click_mono is None:
            return None
        return round((time.perf_counter() - self._selection_click_mono) * 1000, 2)

    def _since_details_request_ms(self) -> float | None:
        if self._details_on_demand_request_mono is None:
            return None
        return round((time.perf_counter() - self._details_on_demand_request_mono) * 1000, 2)

    def _since_details_cta_ms(self) -> float | None:
        if self._details_cta_click_mono is None:
            return None
        return round((time.perf_counter() - self._details_cta_click_mono) * 1000, 2)

    def _log_perf_e_update_done(
        self,
        segment: str,
        *,
        element_type: str,
        started: float,
    ) -> None:
        log_event(
            f"studio.gicleeframe.{segment}.update.done",
            element_type=element_type,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

    def _selection_priority_active(self, generation: int | None = None) -> bool:
        if self._selection_priority_until_mono is None:
            return False
        if time.perf_counter() > self._selection_priority_until_mono:
            return False
        if generation is not None and self._selection_priority_generation != generation:
            return False
        return True

    def _open_selection_priority_window(
        self,
        generation: int,
        *,
        element_id: str,
        element_type: str,
    ) -> None:
        if self._selection_priority_end_after_id is not None:
            try:
                self.after_cancel(self._selection_priority_end_after_id)
            except tk.TclError:
                pass
            self._selection_priority_end_after_id = None

        self._selection_priority_generation = generation
        self._selection_priority_until_mono = (
            time.perf_counter() + (_GF_SELECTION_PRIORITY_WINDOW_MS / 1000.0)
        )
        log_event(
            "studio.gicleeframe.selection.priority_start",
            generation=generation,
            element_id=element_id,
            element_type=element_type,
            window_ms=_GF_SELECTION_PRIORITY_WINDOW_MS,
            since_click_ms=self._since_selection_click_ms(),
        )
        self._selection_priority_end_after_id = self.after(
            _GF_SELECTION_PRIORITY_WINDOW_MS,
            lambda gen=generation: self._end_selection_priority_window(gen),
        )
        self._preempt_background_for_selection_priority(
            generation=generation,
            element_id=element_id,
            element_type=element_type,
        )

    def _preempt_background_for_selection_priority(
        self,
        *,
        generation: int,
        element_id: str,
        element_type: str,
    ) -> None:
        cancelled = self._cancel_section_list_batch_continuation()
        if cancelled:
            log_event(
                "studio.gicleeframe.background.deferred_for_selection",
                generation=generation,
                element_id=element_id,
                element_type=element_type,
                reason="selection_priority_preempt",
                delay_ms=0,
                job="section_list.incremental_batch",
                since_click_ms=self._since_selection_click_ms(),
            )

    def _cancel_section_list_batch_continuation(self) -> bool:
        after_id = self._section_list_batch_after_id
        if after_id is None:
            return False
        self._section_list_batch_after_id = None
        try:
            self.after_cancel(after_id)
        except tk.TclError:
            pass
        return True

    def _schedule_section_list_batch_continuation(
        self,
        options: list[SectionDropdownOption],
        end: int,
    ) -> None:
        self._cancel_section_list_batch_continuation()

        def _continue() -> None:
            self._section_list_batch_after_id = None
            self._render_section_list_batch(options, end)

        self._section_list_batch_after_id = self.after(
            _GF_SECTION_BATCH_DELAY_MS,
            _continue,
        )

    def _end_selection_priority_window(self, generation: int) -> None:
        self._selection_priority_end_after_id = None
        if self._selection_priority_generation != generation:
            return
        self._selection_priority_until_mono = None
        log_event(
            "studio.gicleeframe.selection.priority_end",
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _defer_background_for_selection(
        self,
        *,
        job: str,
        reason: str,
        callback: Callable[[], None],
        delay_ms: int | None = None,
        element_id: str = "",
        element_type: str = "",
    ) -> bool:
        if not self._selection_priority_active():
            return False
        effective_delay = (
            _GF_SELECTION_PRIORITY_YIELD_DEFER_MS if delay_ms is None else delay_ms
        )
        log_event(
            "studio.gicleeframe.background.deferred_for_selection",
            generation=self._selection_priority_generation,
            element_id=element_id,
            element_type=element_type,
            reason=reason,
            delay_ms=effective_delay,
            job=job,
            since_click_ms=self._since_selection_click_ms(),
        )
        self.after(effective_delay, callback)
        return True

    def _should_run_immediate_selection_populate(self, m: MergedPageElement) -> bool:
        # PERF-E.1: shell + pola muszą iść synchronicznie po kliknięciu.
        # Ciężkie preview/layer_nav/children deferujemy wewnątrz _populate_editor.
        _ = m
        return True

    def _schedule_selection_populate(
        self,
        element_id: str,
        generation: int,
        *,
        element_type: str,
    ) -> None:
        self._selection_populate_scheduled_mono = time.perf_counter()
        self._schedule_selection_job(
            _GF_SELECT_POPULATE_DEFER_MS,
            lambda eid=element_id, gen=generation: self._populate_editor_deferred(eid, gen),
        )
        log_event(
            "studio.gicleeframe.selection.populate_priority_scheduled",
            element_id=element_id,
            element_type=element_type,
            generation=generation,
            defer_ms=_GF_SELECT_POPULATE_DEFER_MS,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _begin_visual_session(self, *, cache_hit: bool) -> None:
        self._visual_enter_mono = time.perf_counter()
        self._visual_idle_logged = False
        log_event(
            "studio.gicleeframe.visual.enter",
            cache_hit=cache_hit,
            source="view_on_show",
        )

    def _ensure_atomic_reveal_overlay(self) -> None:
        if self._visual_bootstrap_complete:
            return
        self._show_loading_overlay()
        if self._atomic_reveal_overlay_shown:
            return
        self._atomic_reveal_overlay_shown = True
        log_event(
            "studio.gicleeframe.atomic_reveal.overlay_shown",
            since_enter_ms=self._since_visual_enter_ms(),
        )

    def _atomic_reveal_missing_gates(self) -> list[str]:
        missing: list[str] = []
        if not self._shell_sections_built:
            missing.append("sections")
        if not self._shell_editor_built:
            missing.append("editor")
        if not self._shell_control_built and not self._shell_control_skeleton_built:
            missing.append("control")
        if not self._editor_form_shell_ready:
            missing.append("editor_form")
        if not self._inventory_light_ready:
            missing.append("inventory")
        return missing

    def _ensure_atomic_reveal_prerequisites(self) -> None:
        if self._shell_editor_built and not self._editor_form_shell_ready:
            self._micro_deferred_editor_form_shell()

    def _ensure_top_bar_actions_for_atomic_reveal(self) -> None:
        if self._top_bar_actions_late_done:
            return
        if not self._top_bar_actions_late_started:
            self._top_bar_actions_late_started = True
            log_event(
                "studio.gicleeframe.top_bar.actions_late_scheduled",
                delay_ms=0,
                reason="atomic_reveal",
            )
        self._build_context_bar_actions_late()
        self._build_command_bar_primary_actions_late()
        self._build_command_bar_secondary_actions_late()

    def _schedule_atomic_reveal_check(self, *, trigger: str) -> None:
        self._ensure_atomic_reveal_prerequisites()
        self.after_idle(lambda t=trigger: self._try_atomic_reveal(trigger=t))

    def _try_atomic_reveal(self, *, trigger: str | None = None) -> None:
        if self._visual_bootstrap_complete:
            return
        missing = self._atomic_reveal_missing_gates()
        if missing:
            log_event(
                "studio.gicleeframe.atomic_reveal.waiting_for",
                missing_gates=",".join(missing),
                trigger=trigger or "",
                since_enter_ms=self._since_visual_enter_ms(),
            )
            self._ensure_atomic_reveal_prerequisites()
            return
        # Przyciski top-baru muszą istnieć przed zdjęciem nakładki —
        # inaczej "wskakują" obcięte już po odsłonięciu widoku.
        self._ensure_top_bar_actions_for_atomic_reveal()
        if not self._atomic_reveal_ready_logged:
            self._atomic_reveal_ready_logged = True
            log_event(
                "studio.gicleeframe.atomic_reveal.minimal_ready",
                since_enter_ms=self._since_visual_enter_ms(),
                trigger=trigger or "",
            )
            log_event(
                "studio.gicleeframe.atomic_reveal.ready",
                since_enter_ms=self._since_visual_enter_ms(),
                trigger=trigger or "",
            )
        self._hide_loading_overlay()
        self._visual_bootstrap_complete = True
        log_event(
            "studio.gicleeframe.atomic_reveal.revealed",
            since_enter_ms=self._since_visual_enter_ms(),
            trigger=trigger or "",
        )
        log_event(
            "studio.gicleeframe.visual.visible_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            selected_id=self._selected_id or "",
            merged_count=len(self._merged),
            bootstrap_complete=True,
        )
        self.after_idle(self._mark_idle_ready)

    def _ensure_loading_overlay(self) -> None:
        if self._loading_overlay is not None:
            return
        overlay = ctk.CTkFrame(self, fg_color=theme.AppBg, corner_radius=0)
        ctk.CTkLabel(
            overlay,
            text=_GF_LOADING_OVERLAY_TEXT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        ).pack(expand=True)
        self._loading_overlay = overlay

    def _show_loading_overlay(self) -> None:
        if self._visual_bootstrap_complete:
            return
        self._ensure_loading_overlay()
        if self._loading_overlay is None:
            return
        self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_overlay.lift()

    def _hide_loading_overlay(self) -> None:
        if self._loading_overlay is None:
            return
        try:
            self._loading_overlay.place_forget()
        except tk.TclError:
            pass

    def _mark_idle_ready(self) -> None:
        if self._visual_idle_logged:
            return
        self._visual_idle_logged = True
        log_event(
            "studio.gicleeframe.visual.idle_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            bootstrap_complete=self._visual_bootstrap_complete,
        )

    def _mark_visual_ready(self) -> None:
        """Legacy hook — cold open uses atomic reveal instead."""
        if not self._visual_bootstrap_complete:
            self._try_atomic_reveal(trigger="mark_visual_ready")
            return
        self._hide_loading_overlay()

    def _schedule_visual_ready(self) -> None:
        self._schedule_atomic_reveal_check(trigger="schedule_visual_ready")

    def _build_shell(self) -> None:
        self._ensure_atomic_reveal_overlay()
        with span("studio.gicleeframe.build.context_bar"):
            self._build_context_bar()
        if _lazy_shell_enabled():
            self._build_page_editor_section_critical()
            if _progressive_boot_enabled():
                with span("studio.gicleeframe.build.f1_brand_section.placeholder"):
                    self._build_f1_brand_section_placeholder()
                log_event("studio.gicleeframe.f1.lazy_collapsed")
            else:
                with span("studio.gicleeframe.build.f1_brand_section"):
                    self._build_f1_brand_section_full()
            log_event(
                "studio.gicleeframe.shell.critical_ready",
                since_enter_ms=self._since_visual_enter_ms(),
            )
            self._shell_editor_deferred_scheduled_mono = time.perf_counter()
            log_event(
                "studio.gicleeframe.editor.deferred_scheduled",
                delay_ms=_GF_SHELL_EDITOR_DEFER_MS,
                since_enter_ms=self._since_visual_enter_ms(),
            )
            self.after(_GF_SHELL_EDITOR_DEFER_MS, self._build_editor_column_deferred)
            self._shell_control_deferred_scheduled_mono = time.perf_counter()
            log_event(
                "studio.gicleeframe.control.deferred_scheduled",
                delay_ms=_GF_SHELL_CONTROL_DEFER_MS,
                since_enter_ms=self._since_visual_enter_ms(),
            )
            self.after(_GF_SHELL_CONTROL_DEFER_MS, self._build_control_column_deferred)
        else:
            self._build_page_editor_section()
            if _progressive_boot_enabled():
                with span("studio.gicleeframe.build.f1_brand_section.placeholder"):
                    self._build_f1_brand_section_placeholder()
                self.after(_GF_F1_DEFER_MS, self._build_f1_brand_section_deferred)
            else:
                with span("studio.gicleeframe.build.f1_brand_section"):
                    self._build_f1_brand_section_full()
        log_event(
            "studio.gicleeframe.visual.shell_built",
            since_enter_ms=self._since_visual_enter_ms(),
            lazy_shell=_lazy_shell_enabled(),
        )
        self._schedule_top_bar_actions_late_build()

    def _build_page_editor_section_critical(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.pack(fill="x", padx=24, pady=(0, 12))
        with span("studio.gicleeframe.build.command_bar"):
            self._build_command_bar(panel)
        with span("studio.gicleeframe.build.workspace.critical"):
            self._build_workspace_critical(panel)
        self._schedule_sections_column_early_lane()

    def _build_workspace_skeleton_column(
        self,
        parent: ctk.CTkFrame,
        *,
        column: int,
        text: str,
        min_width: int | None = None,
    ) -> ctk.CTkFrame:
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=0, column=column, sticky="nsew", padx=(0, 8 if column < 2 else 0))

        card = _make_gf_card(col, variant="panel_deep", radius=16)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            card,
            text=text,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="center",
            justify="center",
            wraplength=max((min_width or 240) - 32, 160),
        ).pack(expand=True, fill="both", padx=16, pady=32)

        return col

    def _clear_column_children(self, column: ctk.CTkFrame | None) -> None:
        if column is None:
            return
        for child in column.winfo_children():
            try:
                child.destroy()
            except tk.TclError:
                pass

    def _log_visual_gate_ready(
        self,
        gate: str,
        *,
        source: str,
        since_scheduled_mono: float | None = None,
    ) -> None:
        log_event(
            f"studio.gicleeframe.visual.gate.{gate}_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(since_scheduled_mono),
            source=source,
        )

    def _try_mark_perceived_ready(self, *, trigger: str | None = None) -> None:
        if self._perceived_ready_logged:
            return
        shell_sections_built = self._shell_sections_built
        shell_editor_built = self._shell_editor_built
        shell_control_built = (
            self._shell_control_built or self._shell_control_skeleton_built
        )
        section_list_first_visible_built = self._section_list_first_visible_built
        missing_gates: list[str] = []
        if not shell_sections_built:
            missing_gates.append("sections")
        if not shell_editor_built:
            missing_gates.append("editor")
        if not shell_control_built:
            missing_gates.append("control")
        if not section_list_first_visible_built:
            missing_gates.append("first_visible")
        if missing_gates:
            log_event(
                "studio.gicleeframe.visual.perceived_ready_gate_check",
                since_enter_ms=self._since_visual_enter_ms(),
                shell_sections_built=shell_sections_built,
                shell_editor_built=shell_editor_built,
                shell_control_built=shell_control_built,
                shell_control_skeleton_built=self._shell_control_skeleton_built,
                section_list_first_visible_built=section_list_first_visible_built,
                missing_gates=",".join(missing_gates),
                trigger=trigger or "",
            )
            return
        self._perceived_ready_logged = True
        log_event(
            "studio.gicleeframe.visual.perceived_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            trigger=trigger or "",
        )
        self._schedule_atomic_reveal_check(trigger=trigger or "perceived_ready")

    def _build_workspace_critical(self, parent: ctk.CTkFrame) -> None:
        self._workspace_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._workspace_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._workspace_frame.grid_columnconfigure(0, weight=0, minsize=_SECTION_LIST_WIDTH)
        self._workspace_frame.grid_columnconfigure(1, weight=1)
        self._workspace_frame.grid_columnconfigure(
            2, weight=0, minsize=_CONTROL_COL_MINSIZE,
        )

        self._sections_column = self._build_workspace_skeleton_column(
            self._workspace_frame,
            column=0,
            text=_GF_SKELETON_SECTION_TEXT,
            min_width=_SECTION_LIST_WIDTH,
        )
        self._editor_column = self._build_workspace_skeleton_column(
            self._workspace_frame,
            column=1,
            text=_GF_SKELETON_EDITOR_TEXT,
            min_width=520,
        )
        self._control_column = self._build_workspace_skeleton_column(
            self._workspace_frame,
            column=2,
            text=_GF_SKELETON_CONTROL_TEXT,
            min_width=_CONTROL_COL_MINSIZE,
        )

        self._workspace_placeholder = None
        self._workspace_skeleton_columns_built = True
        log_event("studio.gicleeframe.workspace.skeleton_columns_ready")

    def _schedule_sections_column_early_lane(self) -> None:
        if self._sections_column_early_lane_scheduled or self._shell_sections_built:
            return
        self._sections_column_early_lane_scheduled = True
        self._sections_column_early_lane_scheduled_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.sections_column.early_lane_scheduled",
            delay_ms=_GF_SECTIONS_COLUMN_EARLY_DEFER_MS,
            row_count=len(self._section_dropdown_options_cache),
            first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE,
        )
        self.after(
            _GF_SECTIONS_COLUMN_EARLY_DEFER_MS,
            self._build_sections_column_deferred,
        )

    def _schedule_init_refresh_light(self) -> None:
        if self._init_refresh_light_scheduled:
            return
        self._init_refresh_light_scheduled = True
        log_event(
            "studio.gicleeframe.init_refresh.light_scheduled",
            delay_ms=_GF_INIT_REFRESH_LIGHT_DEFER_MS,
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_scheduled_mono,
            ),
        )
        self.after(
            _GF_INIT_REFRESH_LIGHT_DEFER_MS,
            self._run_init_refresh_light_deferred,
        )

    def _run_init_refresh_light_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        # Skan plików inventory w wątku roboczym — pierwsza klatka widoku bez freeze.
        run_async(
            self,
            lambda: build_gicleeframe_page_inventory(find_components_dir()),
            self._finish_init_refresh_light,
            on_error=lambda _exc: self._finish_init_refresh_light(None),
        )

    def _finish_init_refresh_light(self, prebuilt_inventory: object) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        with span("studio.gicleeframe.init_refresh.light"):
            self._refresh_inventory_light(
                warn_if_draft=False,
                prebuilt_inventory=prebuilt_inventory,
            )
        self._inventory_light_ready = True
        log_event(
            "studio.gicleeframe.inventory.light_ready_for_reveal",
            merged_count=len(self._merged),
        )
        self._bootstrap_section_list_after_inventory_light()
        self._ensure_atomic_reveal_prerequisites()
        self._schedule_atomic_reveal_check(trigger="inventory_light")

    def _bootstrap_section_list_after_inventory_light(self) -> None:
        if not _progressive_boot_enabled() or self._progressive_bootstrap_started:
            return
        if not _lazy_shell_enabled():
            self._schedule_section_list_incremental()
            return
        if self._shell_sections_built and self._section_list_scroll is not None:
            self._schedule_section_list_incremental()

    def _build_sections_column_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._shell_sections_built or self._workspace_frame is None:
            return
        self._sections_column_early_lane_enter_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.sections_column.early_lane_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_scheduled_mono,
            ),
        )
        with span("studio.gicleeframe.build.sections_column.deferred.shell"):
            if self._sections_column is not None and self._workspace_skeleton_columns_built:
                children = list(self._sections_column.winfo_children())
                child_types = ",".join(type(child).__name__ for child in children)
                with span(
                    "studio.gicleeframe.build.sections_column.deferred.clear_children",
                    children_count=len(children),
                    child_types=child_types or None,
                ):
                    self._clear_column_children(self._sections_column)
                with span("studio.gicleeframe.build.sections_column.deferred.shell_build"):
                    card = self._build_sections_column_shell(
                        self._sections_column,
                        use_static_lane=True,
                    )
                with span("studio.gicleeframe.build.sections_column.deferred.card_pack"):
                    card.pack(fill="both", expand=True)
            else:
                with span("studio.gicleeframe.build.sections_column.deferred.shell_build"):
                    self._sections_column = self._build_sections_column_shell(
                        self._workspace_frame,
                        use_static_lane=True,
                    )
                    self._sections_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._shell_sections_built = True
        log_event("studio.gicleeframe.shell.deferred_sections")
        self._log_visual_gate_ready(
            "sections",
            source="sections_column_deferred",
            since_scheduled_mono=self._sections_column_early_lane_scheduled_mono,
        )
        self._try_mark_perceived_ready(trigger="sections_deferred_done")
        self._flush_pending_section_list_if_needed()
        self.after(_GF_MICRO_DEFER_MS, self._build_sections_column_extras_deferred)

    def _build_sections_column_extras_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._sections_column_extras_built or self._section_list_column is None:
            return
        with span("studio.gicleeframe.build.sections_column.deferred.extras"):
            self._build_sections_column_extras(self._section_list_column)

    def _build_editor_column_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._shell_editor_built or self._workspace_frame is None:
            return
        log_event(
            "studio.gicleeframe.editor.skeleton_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_editor_deferred_scheduled_mono,
            ),
        )
        self._micro_deferred_editor_skeleton()

    def _micro_deferred_editor_skeleton(self) -> None:
        if self._workspace_frame is None:
            return
        with span("studio.gicleeframe.build.editor_column.skeleton"):
            with span("studio.gicleeframe.build.editor_column.skeleton.ensure_column"):
                if self._editor_column is None:
                    self._editor_column = _make_card(
                        self._workspace_frame, bordered=False, fg_color="transparent",
                    )
                    self._editor_column.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
                else:
                    self._clear_column_children(self._editor_column)
            with span("studio.gicleeframe.build.editor_column.skeleton.identity_card"):
                self._build_section_identity_placeholder(self._editor_column)
            with span("studio.gicleeframe.build.editor_column.skeleton.legacy_message"):
                self._legacy_msg_label = ctk.CTkLabel(
                    self._editor_column,
                    text="",
                    font=theme.get_font(10),
                    text_color=theme.AccentGoldDim,
                    anchor="w",
                    wraplength=_EDITOR_FORM_WIDTH - 24,
                )
        self._shell_editor_built = True
        log_event("studio.gicleeframe.editor.skeleton_ready")
        log_event(
            "studio.gicleeframe.editor.skeleton_done",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_editor_deferred_scheduled_mono,
            ),
        )
        log_event("studio.gicleeframe.editor.deferred_identity")
        log_event("studio.gicleeframe.editor.identity_card_lazy_startup")
        log_event("studio.gicleeframe.shell.deferred_editor")
        self._log_visual_gate_ready(
            "editor",
            source="editor_skeleton",
            since_scheduled_mono=self._shell_editor_deferred_scheduled_mono,
        )
        self._try_mark_perceived_ready(trigger="editor_skeleton_done")
        self._schedule_editor_identity_late_build()
        if self._selected_id is None:
            with span("studio.gicleeframe.build.editor_column.skeleton.placeholder_state"):
                self._show_editor_placeholder_state()
        self.after(_GF_MICRO_DEFER_MS, self._micro_deferred_editor_form_shell)

    def _build_section_identity_placeholder(self, parent: ctk.CTkFrame) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0))
        self._identity_card = frame

        ctk.CTkLabel(
            frame,
            text="Edytor sekcji",
            font=theme.get_font(12, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x", padx=4, pady=(4, 0))

        self._editor_section_subtitle = ctk.CTkLabel(
            frame,
            text="Wybierz sekcję po lewej",
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._editor_section_subtitle.pack(fill="x", padx=4, pady=(2, 8))

        self._editor_status_dot = None
        self._editor_header_visible_row = None
        self._layer_nav_frame = None
        self._section_preview_line = None
        self._section_preview_card = None
        self._section_preview_canvas = None
        self._section_preview_badge = None

    def _schedule_editor_identity_late_build(self) -> None:
        if self._editor_identity_late_build_started:
            return
        self._editor_identity_late_build_started = True
        log_event(
            "studio.gicleeframe.editor.identity_card_late_scheduled",
            delay_ms=_GF_EDITOR_IDENTITY_LATE_DEFER_MS,
        )
        self.after(_GF_EDITOR_IDENTITY_LATE_DEFER_MS, self._build_editor_identity_late)

    def _schedule_editor_identity_prewarm_after_perceived(self) -> None:
        if self._editor_identity_prewarm_scheduled:
            return
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_deferred_after_perceived",
            delay_ms=_GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS,
            since_enter_ms=self._since_visual_enter_ms(),
        )
        self.after(
            _GF_EDITOR_IDENTITY_PREWARM_AFTER_PERCEIVED_MS,
            lambda: self._schedule_editor_identity_prewarm(reason="after_perceived_ready"),
        )

    def _schedule_editor_identity_prewarm(self, *, reason: str = "editor_skeleton_done") -> None:
        if self._editor_identity_prewarm_scheduled:
            return
        self._editor_identity_prewarm_scheduled = True
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_scheduled",
            since_enter_ms=self._since_visual_enter_ms(),
            reason=reason,
        )
        self.after(_GF_MICRO_DEFER_MS, self._run_editor_identity_prewarm)

    def _run_editor_identity_prewarm(self) -> None:
        if self._defer_background_for_selection(
            job="editor.identity_prewarm",
            reason="selection_priority_active",
            callback=self._run_editor_identity_prewarm,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        prewarm_started = time.perf_counter()
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_enter",
            since_enter_ms=self._since_visual_enter_ms(),
        )
        if self._editor_identity_late_build_done:
            log_event(
                "studio.gicleeframe.editor.identity_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                already_built=True,
                reason="already_built",
            )
            self._schedule_editor_rows_prewarm()
            return
        if not self._shell_editor_built:
            log_event(
                "studio.gicleeframe.editor.identity_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                already_built=False,
                reason="shell_not_ready",
            )
            return
        self._ensure_editor_identity_built()
        log_event(
            "studio.gicleeframe.editor.identity_prewarm_done",
            since_enter_ms=self._since_visual_enter_ms(),
            elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
            already_built=False,
            reason="built",
        )
        self._schedule_editor_rows_prewarm()

    def _schedule_editor_rows_prewarm(self) -> None:
        if self._editor_rows_prewarm_scheduled:
            return
        self._editor_rows_prewarm_scheduled = True
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_scheduled",
            since_enter_ms=self._since_visual_enter_ms(),
            reason="identity_prewarm_done",
        )
        self.after(_GF_MICRO_DEFER_MS, self._run_editor_rows_prewarm)

    def _editor_row_shell_flags(self) -> dict[str, bool]:
        return {
            "title": self._title_row_built,
            "text": self._text_row_built,
            "alt": self._alt_row_built,
            "image_ref": self._image_ref_row_built,
            "notes": self._notes_row_built,
        }

    def _editor_row_shells_already_built(self) -> bool:
        flags = self._editor_row_shell_flags()
        return all(flags.values())

    def _ensure_editor_row_shells_for_prewarm(self) -> None:
        if self._edit_panel is None:
            return
        self._ensure_title_row_built()
        self._ensure_text_row_built()
        self._ensure_alt_row_built()
        self._ensure_image_ref_row_built()
        self._ensure_notes_row_built()

    def _log_visible_prewarm_suppressed(self, *, job: str) -> None:
        log_event(
            "studio.gicleeframe.visible_prewarm.suppressed",
            job=job,
            since_enter_ms=self._since_visual_enter_ms(),
            bootstrap_complete=self._visual_bootstrap_complete,
        )

    def _should_suppress_visible_prewarm(self) -> bool:
        return self._visual_bootstrap_complete

    def _run_editor_rows_prewarm(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="editor.rows_prewarm")
            return
        if self._defer_background_for_selection(
            job="editor.rows_prewarm",
            reason="selection_priority_active",
            callback=self._run_editor_rows_prewarm,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        prewarm_started = time.perf_counter()
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_enter",
            since_enter_ms=self._since_visual_enter_ms(),
        )
        if self._editor_row_shells_already_built():
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=True,
                reason="already_built",
            )
            return
        if not self._shell_editor_built:
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=False,
                reason="shell_not_ready",
            )
            return
        if not self._editor_form_shell_ready or self._edit_panel is None:
            log_event(
                "studio.gicleeframe.editor.rows_prewarm_skipped",
                since_enter_ms=self._since_visual_enter_ms(),
                elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
                already_built=False,
                reason="form_shell_not_ready",
            )
            return
        flags_before = self._editor_row_shell_flags()
        self._ensure_editor_row_shells_for_prewarm()
        flags_after = self._editor_row_shell_flags()
        log_event(
            "studio.gicleeframe.editor.rows_prewarm_done",
            since_enter_ms=self._since_visual_enter_ms(),
            elapsed_ms=round((time.perf_counter() - prewarm_started) * 1000, 2),
            already_built=False,
            reason="built",
            title_row_built=flags_after["title"] and not flags_before["title"],
            text_row_built=flags_after["text"] and not flags_before["text"],
            alt_row_built=flags_after["alt"] and not flags_before["alt"],
            image_ref_row_built=flags_after["image_ref"] and not flags_before["image_ref"],
            notes_row_built=flags_after["notes"] and not flags_before["notes"],
            children_overview_built=False,
        )

    def _ensure_editor_identity_built(self) -> None:
        if self._editor_identity_late_build_done:
            return
        self._build_editor_identity_late()

    def _build_editor_identity_late(self) -> None:
        if self._defer_background_for_selection(
            job="editor.identity_late",
            reason="selection_priority_active",
            callback=self._build_editor_identity_late,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._editor_identity_late_build_done or self._editor_column is None:
            return

        log_event("studio.gicleeframe.editor.identity_card_late_start")

        pack_before = None
        if self._edit_panel is not None:
            pack_before = self._edit_panel.master

        if self._identity_card is not None:
            self._identity_card.destroy()
            self._identity_card = None

        with span("studio.gicleeframe.build.editor_column.identity_card_late"):
            self._build_section_identity_card(self._editor_column, pack_before=pack_before)

        self._editor_identity_late_build_done = True
        log_event("studio.gicleeframe.editor.identity_card_late_done")

        if self._selected_id is None:
            self._show_editor_placeholder_state()
            return

        m = self._merged_by_id.get(self._selected_id)
        if m is None:
            return

        dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
        if self._editor_status_dot:
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=self._selected_section_label())

    def _micro_deferred_editor_form_shell(self) -> None:
        if self._editor_column is None:
            return
        with span("studio.gicleeframe.build.editor_column.form_shell"):
            form_outer = ctk.CTkFrame(self._editor_column, fg_color="transparent")
            form_outer.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
            form_outer.configure(width=_EDITOR_FORM_WIDTH)
            form_outer.pack_propagate(True)
            self._edit_panel = ctk.CTkFrame(form_outer, fg_color="transparent")
            self._edit_panel.pack(fill="x", anchor="w")
            self._editor_placeholder_label = ctk.CTkLabel(
                self._edit_panel,
                text=_EDITOR_PLACEHOLDER_TEXT,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="w",
                wraplength=_EDITOR_FORM_WIDTH - 24,
            )
            self._editor_placeholder_label.pack(fill="x", pady=(4, 8))
        self._editor_form_shell_ready = True
        log_event("studio.gicleeframe.editor.deferred_form_shell")
        log_event("studio.gicleeframe.editor.fields_lazy_startup")
        self._schedule_atomic_reveal_check(trigger="editor_form_shell")

    def _micro_deferred_editor_fields(self) -> None:
        with span("studio.gicleeframe.build.editor_column.fields"):
            self._build_edit_panel_fields()
        log_event("studio.gicleeframe.editor.deferred_fields")
        self.after(_GF_MICRO_DEFER_MS, self._micro_deferred_editor_children)

    def _micro_deferred_editor_children(self) -> None:
        with span("studio.gicleeframe.build.editor_column.children"):
            self._build_edit_panel_children()
        log_event("studio.gicleeframe.editor.deferred_children")
        self.after(_GF_MICRO_DEFER_MS, self._micro_deferred_editor_page_context)

    def _micro_deferred_editor_page_context(self) -> None:
        with span("studio.gicleeframe.build.editor_column.page_context"):
            self._build_edit_panel_page_context()

    def _build_control_column_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._shell_control_built or self._workspace_frame is None:
            return
        log_event(
            "studio.gicleeframe.control.skeleton_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_control_deferred_scheduled_mono,
            ),
        )
        self._micro_deferred_control_skeleton()

    def _micro_deferred_control_skeleton(self) -> None:
        if self._workspace_frame is None:
            return
        with span("studio.gicleeframe.build.control_column.skeleton"):
            if self._control_column is None:
                self._control_column = ctk.CTkFrame(
                    self._workspace_frame, fg_color="transparent",
                )
                self._control_column.grid(row=0, column=2, sticky="nsew")
            else:
                self._clear_column_children(self._control_column)
        log_event("studio.gicleeframe.control.skeleton_ready")
        log_event(
            "studio.gicleeframe.control.skeleton_done",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_control_deferred_scheduled_mono,
            ),
        )
        self._shell_control_skeleton_built = True
        self._log_visual_gate_ready(
            "control_skeleton",
            source="control_skeleton",
            since_scheduled_mono=self._shell_control_deferred_scheduled_mono,
        )
        self._try_mark_perceived_ready(trigger="control_skeleton_done")
        self.after(_GF_MICRO_DEFER_MS, self._micro_deferred_control_structure)

    def _micro_deferred_control_structure(self) -> None:
        if self._control_column is None:
            return
        log_event(
            "studio.gicleeframe.control.structure_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_control_deferred_scheduled_mono,
            ),
        )
        with span("studio.gicleeframe.build.control_column.structure"):
            self._build_control_structure_card(self._control_column)
        log_event(
            "studio.gicleeframe.control.structure_done",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._shell_control_deferred_scheduled_mono,
            ),
        )
        self._shell_control_built = True
        log_event("studio.gicleeframe.control.deferred_structure")
        log_event("studio.gicleeframe.shell.deferred_control")
        self._log_visual_gate_ready(
            "control",
            source="control_structure",
            since_scheduled_mono=self._shell_control_deferred_scheduled_mono,
        )
        self._schedule_atomic_reveal_check(trigger="control_structure")
        self._schedule_control_late_build()

    def _schedule_control_late_build(self) -> None:
        if self._control_late_build_started:
            return
        self._control_late_build_started = True
        self.after(_GF_CONTROL_LATE_BUILD_DEFER_MS, self._build_control_late_cards)

    def _build_control_late_cards(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="control.late_cards")
            return
        if self._defer_background_for_selection(
            job="control.late_cards",
            reason="selection_priority_active",
            callback=self._build_control_late_cards,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._control_column is None or self._control_late_build_done:
            return
        with span("studio.gicleeframe.build.control_column.late_cards"):
            with span("studio.gicleeframe.build.control_column.readiness"):
                self._build_control_readiness_card(self._control_column)
            log_event("studio.gicleeframe.control.deferred_readiness_late")

            with span("studio.gicleeframe.build.control_column.safety"):
                self._build_safety_card(self._control_column)
            log_event("studio.gicleeframe.control.deferred_safety_late")

        self._control_late_build_done = True

    def _micro_deferred_control_readiness(self) -> None:
        if self._control_column is None:
            return
        with span("studio.gicleeframe.build.control_column.readiness"):
            self._build_control_readiness_card(self._control_column)
        log_event("studio.gicleeframe.control.deferred_readiness")
        self.after(_GF_MICRO_DEFER_MS, self._micro_deferred_control_safety)

    def _micro_deferred_control_safety(self) -> None:
        if self._control_column is None:
            return
        with span("studio.gicleeframe.build.control_column.safety"):
            self._build_safety_card(self._control_column)
        self._shell_control_built = True
        log_event("studio.gicleeframe.control.deferred_safety")
        log_event("studio.gicleeframe.shell.deferred_control")
        self._try_mark_perceived_ready()

    def _flush_pending_section_list_if_needed(self) -> None:
        if not self._pending_section_list_render:
            return
        if self._section_list_scroll is None:
            return
        self._pending_section_list_render = False
        self._show_section_list_loading_state()
        if _progressive_boot_enabled() and not self._progressive_bootstrap_started:
            self._schedule_section_list_incremental()

    def _schedule_section_list_incremental(
        self,
        *,
        delay_ms: int | None = None,
    ) -> None:
        effective_delay = (
            _GF_SECTION_FIRST_VISIBLE_DEFER_MS if delay_ms is None else delay_ms
        )
        self._section_list_incremental_scheduled_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.section_list.first_visible_fast_lane",
            delay_ms=effective_delay,
            row_count=len(self._section_dropdown_options_cache),
            first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE,
            queue_latency_ms=self._queue_latency_since_ms(
                self._section_list_column_ready_mono,
            ),
        )
        log_event(
            "studio.gicleeframe.section_list.incremental_scheduled",
            delay_ms=effective_delay,
            row_count=len(self._section_dropdown_options_cache),
            first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE,
            queue_latency_ms=self._queue_latency_since_ms(
                self._section_list_column_ready_mono,
            ),
        )
        self.after(effective_delay, self._run_deferred_bootstrap)

    def _build_context_bar(self) -> None:
        with span("studio.gicleeframe.build.context_bar.frame"):
            bar = _make_gf_card(self, variant="panel_deep", radius=16)
            bar.pack(fill="x", padx=24, pady=(12, 8))

            row = ctk.CTkFrame(bar, fg_color="transparent")
            row.pack(fill="x", padx=_CARD_PAD_X, pady=8)
            self._context_bar_row = row

        with span("studio.gicleeframe.build.context_bar.title"):
            _make_status_pill(
                row,
                _SHELL_STATUS_CHIP,
                accent=True,
            ).pack(side="left", padx=(0, 10))
            self._top_meta_label = ctk.CTkLabel(
                row,
                text="Ładowanie…",
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="w",
            )
            self._top_meta_label.pack(side="left", padx=(0, 16))

        with span("studio.gicleeframe.build.context_bar.actions"):
            self._build_context_bar_actions_placeholder(row)

        with span("studio.gicleeframe.build.context_bar.status"):
            self._change_count_label = _make_status_pill(
                row,
                "Zmiany: 0",
                bold=True,
                text_color=_GF_GOLD_SOFT,
                fg_color=_GF_FIELD,
            )
            self._change_count_label.pack(side="left", padx=(0, 12))

            self._panel_status_label = ctk.CTkLabel(
                row,
                text=PANEL_STATUS_UNSAVED,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
            )
            self._panel_status_label.pack(side="right", padx=(0, 10))

    def _build_context_bar_actions_placeholder(self, row: ctk.CTkFrame) -> None:
        self._context_bar_actions_slot = ctk.CTkFrame(row, fg_color="transparent")
        self._context_bar_actions_slot.pack(side="left", padx=(0, 10))
        self._context_bar_actions_placeholder = ctk.CTkFrame(
            self._context_bar_actions_slot,
            fg_color="transparent",
            width=168,
            height=_BTN_HEIGHT,
        )
        self._context_bar_actions_placeholder.pack(side="left")
        self._context_bar_actions_placeholder.pack_propagate(False)

        if self._on_back is not None:
            self._context_bar_back_slot = ctk.CTkFrame(
                row,
                fg_color="transparent",
                width=112,
                height=_BTN_HEIGHT,
            )
            self._context_bar_back_slot.pack(side="right")
            self._context_bar_back_slot.pack_propagate(False)
            self._context_bar_back_placeholder = ctk.CTkFrame(
                self._context_bar_back_slot,
                fg_color="transparent",
            )
            self._context_bar_back_placeholder.pack(fill="both", expand=True)

        log_event("studio.gicleeframe.context_bar.actions_lazy_startup")

    def _build_context_bar_actions(self, row: ctk.CTkFrame) -> None:
        slot = self._context_bar_actions_slot
        if slot is not None:
            for child in slot.winfo_children():
                child.destroy()
        self._context_bar_actions_placeholder = None

        parent = slot if slot is not None else row
        self._working_variant_menu = ctk.CTkOptionMenu(
            parent,
            values=[DEFAULT_VARIANT_NAME],
            command=self._on_working_variant_selected,
            width=168,
            height=_BTN_HEIGHT,
            **_f2_menu_kwargs(),
        )
        self._working_variant_menu.set(DEFAULT_VARIANT_NAME)
        self._working_variant_menu.pack(side="left")

        back_parent = self._context_bar_back_slot if self._context_bar_back_slot is not None else row
        if self._context_bar_back_slot is not None:
            for child in self._context_bar_back_slot.winfo_children():
                child.destroy()
        self._context_bar_back_placeholder = None

        self._back_button = _make_secondary_button(
            back_parent,
            _BACK_LABEL,
            self._handle_back,
            width=112,
            subtle=True,
        )
        if self._on_back is not None:
            if back_parent is row:
                self._back_button.pack(side="right")
            else:
                self._back_button.pack(fill="both", expand=True)

    def _schedule_top_bar_actions_late_build(self) -> None:
        if self._top_bar_actions_late_started:
            return
        self._top_bar_actions_late_started = True
        log_event(
            "studio.gicleeframe.top_bar.actions_late_scheduled",
            delay_ms=_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS,
        )
        self.after(
            _GF_TOP_BAR_ACTIONS_LATE_DEFER_MS,
            self._start_top_bar_actions_late_build,
        )

    def _start_top_bar_actions_late_build(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._top_bar_actions_late_done:
            return

        log_event("studio.gicleeframe.top_bar.actions_late_start")

        self.after(
            _GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS,
            self._build_context_bar_actions_late,
        )
        self.after(
            _GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS,
            self._build_command_bar_primary_actions_late,
        )
        self.after(
            _GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS,
            self._build_command_bar_secondary_actions_late,
        )

    def _build_context_bar_actions_late(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="top_bar.context_actions_late")
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._top_bar_actions_late_done:
            return

        row = self._context_bar_row
        if row is not None:
            with span("studio.gicleeframe.build.context_bar.actions_late"):
                self._build_context_bar_actions(row)
        log_event("studio.gicleeframe.top_bar.context_actions_late_done")

    def _build_command_bar_primary_actions_late(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="top_bar.primary_actions_late")
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._top_bar_actions_late_done:
            return

        inner = self._command_bar_inner
        if inner is not None:
            with span("studio.gicleeframe.build.command_bar.primary_actions_late"):
                self._build_command_bar_primary_actions(inner)
        log_event("studio.gicleeframe.top_bar.primary_actions_late_done")

    def _build_command_bar_secondary_actions_late(self) -> None:
        if self._should_suppress_visible_prewarm():
            self._log_visible_prewarm_suppressed(job="top_bar.secondary_actions_late")
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._top_bar_actions_late_done:
            return

        inner = self._command_bar_inner
        if inner is not None:
            with span("studio.gicleeframe.build.command_bar.secondary_actions_late"):
                self._build_command_bar_secondary_actions(inner)

        self._top_bar_actions_late_done = True
        log_event("studio.gicleeframe.top_bar.secondary_actions_late_done")
        log_event("studio.gicleeframe.top_bar.actions_late_done")
        self._sync_working_variant_menu()
        self._schedule_atomic_reveal_check(trigger="top_bar_actions")

    def _build_page_editor_section(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.pack(fill="x", padx=24, pady=(0, 12))
        with span("studio.gicleeframe.build.command_bar"):
            self._build_command_bar(panel)
        with span("studio.gicleeframe.build.workspace"):
            self._build_page_workspace(panel)

    def _build_command_bar(self, parent: ctk.CTkFrame) -> None:
        with span("studio.gicleeframe.build.command_bar.frame"):
            bar = _make_gf_card(parent, variant="panel_deep", radius=16)
            bar.pack(fill="x", pady=(0, 10))
            inner = ctk.CTkFrame(bar, fg_color="transparent")
            inner.pack(fill="x", padx=16, pady=(10, 12))
            self._command_bar_inner = inner

        with span("studio.gicleeframe.build.command_bar.primary_actions"):
            self._command_bar_primary_slot = ctk.CTkFrame(inner, fg_color="transparent")
            self._command_bar_primary_slot.pack(
                side="left", fill="x", expand=True, padx=(0, 20),
            )
            self._command_bar_primary_placeholder = ctk.CTkFrame(
                self._command_bar_primary_slot,
                fg_color="transparent",
                height=56,
            )
            self._command_bar_primary_placeholder.pack(fill="x")
            self._command_bar_primary_placeholder.pack_propagate(False)
            log_event("studio.gicleeframe.command_bar.primary_actions_lazy_startup")

        with span("studio.gicleeframe.build.command_bar.secondary_actions"):
            self._command_bar_secondary_slot = ctk.CTkFrame(inner, fg_color="transparent")
            self._command_bar_secondary_slot.pack(side="left", fill="x", expand=True)
            self._command_bar_secondary_placeholder = ctk.CTkFrame(
                self._command_bar_secondary_slot,
                fg_color="transparent",
                height=56,
            )
            self._command_bar_secondary_placeholder.pack(fill="x")
            self._command_bar_secondary_placeholder.pack_propagate(False)
            log_event("studio.gicleeframe.command_bar.secondary_actions_lazy_startup")

    def _build_command_bar_primary_actions(self, inner: ctk.CTkFrame) -> None:
        slot = self._command_bar_primary_slot
        group = slot if slot is not None else ctk.CTkFrame(inner, fg_color="transparent")
        if slot is not None:
            for child in slot.winfo_children():
                child.destroy()
        else:
            group.pack(side="left", fill="x", expand=True, padx=(0, 20))
        self._command_bar_primary_placeholder = None

        caption = _make_section_caption(group, "Warianty RAM")
        caption.configure(text_color=_GF_GOLD_SOFT)
        caption.pack(fill="x", pady=(0, 8))
        btn_row = ctk.CTkFrame(group, fg_color="transparent")
        btn_row.pack(fill="x")
        for label, cmd in (
            (ADD_VARIANT_RAM_LABEL, self._add_ram_variant),
            (DUPLICATE_VARIANT_LABEL, self._duplicate_ram_variant),
            (RENAME_VARIANT_LABEL, self._rename_ram_variant),
            (CLEAR_VARIANT_RAM_LABEL, self._clear_page_draft),
        ):
            _make_secondary_button(btn_row, label, cmd, subtle=False).pack(
                side="left", padx=(0, 6),
            )

    def _build_command_bar_secondary_actions(self, inner: ctk.CTkFrame) -> None:
        slot = self._command_bar_secondary_slot
        group = slot if slot is not None else ctk.CTkFrame(inner, fg_color="transparent")
        if slot is not None:
            for child in slot.winfo_children():
                child.destroy()
        else:
            group.pack(side="left", fill="x", expand=True)
        self._command_bar_secondary_placeholder = None

        caption = _make_section_caption(group, "Inventory i kontrola")
        caption.configure(text_color=_GF_GOLD_SOFT)
        caption.pack(fill="x", pady=(0, 8))
        btn_row = ctk.CTkFrame(group, fg_color="transparent")
        btn_row.pack(fill="x")
        for label, cmd in (
            (REFRESH_INVENTORY_LABEL, lambda: self._refresh_inventory(warn_if_draft=True)),
            (CHECK_STRUCTURE_LABEL, self._run_structure_dry_run),
        ):
            _make_secondary_button(btn_row, label, cmd, subtle=False).pack(
                side="left", padx=(0, 6),
            )

    def _build_page_workspace(self, parent: ctk.CTkFrame) -> None:
        self._workspace_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self._workspace_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._workspace_frame.grid_columnconfigure(0, weight=0, minsize=_SECTION_LIST_WIDTH)
        self._workspace_frame.grid_columnconfigure(1, weight=1)
        self._workspace_frame.grid_columnconfigure(
            2, weight=0, minsize=_CONTROL_COL_MINSIZE,
        )

        with span("studio.gicleeframe.build.sections_column"):
            self._sections_column = self._build_sections_column(self._workspace_frame)
        self._sections_column.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        with span("studio.gicleeframe.build.editor_column"):
            self._editor_column = self._build_editor_column(self._workspace_frame)
        self._editor_column.grid(row=0, column=1, sticky="nsew", padx=(0, 8))

        with span("studio.gicleeframe.build.control_column"):
            self._control_column = self._build_control_column(self._workspace_frame)
        self._control_column.grid(row=0, column=2, sticky="nsew")

    def _log_section_list_column_ready(self) -> None:
        log_event(
            "studio.gicleeframe.section_list.column_shell_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_enter_mono,
            ),
        )
        self._section_list_column_ready_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.section_list.column_ready_for_rows",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_scheduled_mono,
            ),
            since_early_lane_enter_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_enter_mono,
            ),
        )

    def _build_sections_column_shell(
        self,
        parent: ctk.CTkFrame,
        *,
        use_static_lane: bool = False,
    ) -> ctk.CTkFrame:
        with span("studio.gicleeframe.build.sections_column.shell.card"):
            card = _make_gf_card(parent, variant="panel_deep", radius=16)
            self._section_list_column = card

        with span("studio.gicleeframe.build.sections_column.shell.extras_slot"):
            self._section_list_extras_frame = ctk.CTkFrame(card, fg_color="transparent")
            self._section_list_extras_frame.pack(fill="x")

        if use_static_lane:
            with span("studio.gicleeframe.build.sections_column.shell.static_lane_create"):
                self._section_list_static_lane = ctk.CTkFrame(
                    card,
                    fg_color="transparent",
                    width=_SECTION_LIST_WIDTH - 12,
                    height=_SECTION_LIST_HEIGHT,
                )
            with span("studio.gicleeframe.build.sections_column.shell.static_lane_pack"):
                self._section_list_static_lane.pack(
                    fill="both",
                    expand=True,
                    padx=8,
                    pady=(0, 12),
                )
            with span("studio.gicleeframe.build.sections_column.shell.ready_log"):
                self._populate_section_list_static_lane()
                self._log_section_list_column_ready()
            self._ensure_section_list_scroll_upgrade_fallback()
        else:
            self._create_section_list_scroll_frame(card)
            with span("studio.gicleeframe.build.sections_column.shell.ready_log"):
                self._log_section_list_column_ready()
        return card

    def _create_section_list_scroll_frame(self, card: ctk.CTkFrame) -> None:
        with span("studio.gicleeframe.build.sections_column.shell.scroll_create"):
            self._section_list_scroll = ctk.CTkScrollableFrame(
                card,
                width=_SECTION_LIST_WIDTH - 12,
                height=_SECTION_LIST_HEIGHT,
                fg_color="transparent",
                corner_radius=0,
            )
        with span("studio.gicleeframe.build.sections_column.shell.scroll_pack"):
            self._section_list_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 12))

    def _populate_section_list_static_lane(self) -> None:
        lane = self._section_list_static_lane
        if lane is None:
            return
        for child in lane.winfo_children():
            child.destroy()
        self._section_row_frames.clear()
        self._section_row_ids = []

        options = list(self._section_dropdown_options_cache)
        if not options and self._merged:
            if not self._section_tree_rows_cache:
                self._rebuild_page_model_cache()
            options = list(self._section_dropdown_options_cache)

        if options:
            end = min(_GF_SECTION_FIRST_BATCH_SIZE, len(options))
            for idx in range(end):
                opt = options[idx]
                self._section_row_ids.append(opt.element_id)
                self._create_section_list_row(
                    idx,
                    opt.element_id,
                    opt.display_label,
                    parent=lane,
                    static_lane=True,
                )
            self._section_list_static_lane_real_rows = True
            log_event(
                "studio.gicleeframe.section_list.static_lane_ready",
                real_rows=True,
                row_count=end,
                first_batch_size=_GF_SECTION_FIRST_BATCH_SIZE,
                since_enter_ms=self._since_visual_enter_ms(),
                queue_latency_ms=self._queue_latency_since_ms(
                    self._sections_column_early_lane_enter_mono,
                ),
            )
            log_event(
                "studio.gicleeframe.section_list.first_visible_ready",
                since_enter_ms=self._since_visual_enter_ms(),
                created=end,
                source="static_lane",
                queue_latency_ms=self._queue_latency_since_ms(
                    self._sections_column_early_lane_enter_mono,
                ),
            )
            self._section_list_first_visible_built = True
            self._log_visual_gate_ready(
                "first_visible",
                source="static_lane",
                since_scheduled_mono=self._sections_column_early_lane_enter_mono,
            )
            self._try_mark_perceived_ready(trigger="static_lane_first_visible")
            self._schedule_atomic_reveal_check(trigger="static_lane_first_visible")
            return

        self._section_list_static_lane_real_rows = False
        ctk.CTkLabel(
            lane,
            text=_SECTION_LIST_LOADING_TEXT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=10, pady=10)
        log_event(
            "studio.gicleeframe.section_list.static_lane_ready",
            real_rows=False,
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_enter_mono,
            ),
        )

    def _try_refresh_static_lane_before_scroll_upgrade(self) -> None:
        if (
            self._section_list_scroll_upgrade_done
            or self._section_list_static_lane is None
            or self._section_list_static_lane_real_rows
        ):
            return
        self._populate_section_list_static_lane()

    def _cancel_section_list_scroll_upgrade_fallback(self) -> None:
        after_id = self._section_list_scroll_upgrade_fallback_after_id
        if after_id is None:
            return
        try:
            self.after_cancel(after_id)
        except (tk.TclError, ValueError):
            pass
        self._section_list_scroll_upgrade_fallback_after_id = None

    def _ensure_section_list_scroll_upgrade_fallback(self) -> None:
        if (
            self._section_list_scroll_upgrade_scheduled
            or self._section_list_scroll_upgrade_done
            or self._section_list_scroll_upgrade_fallback_after_id is not None
        ):
            return

        def _fire_fallback() -> None:
            self._section_list_scroll_upgrade_fallback_after_id = None
            if (
                self._section_list_scroll_upgrade_scheduled
                or self._section_list_scroll_upgrade_done
            ):
                return
            self._schedule_section_list_scroll_upgrade(reason="fallback_timeout")

        self._section_list_scroll_upgrade_fallback_after_id = self.after(
            _GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS,
            _fire_fallback,
        )

    def _schedule_section_list_scroll_upgrade_after_perceived(self) -> None:
        if self._section_list_static_lane is None:
            return
        if (
            self._section_list_scroll_upgrade_scheduled
            or self._section_list_scroll_upgrade_done
        ):
            return
        self._cancel_section_list_scroll_upgrade_fallback()
        self._schedule_section_list_scroll_upgrade(reason="after_perceived_ready")

    def _schedule_section_list_scroll_upgrade(self, *, reason: str) -> None:
        if self._section_list_scroll_upgrade_scheduled:
            return
        self._section_list_scroll_upgrade_scheduled = True
        delay_ms = (
            0
            if reason in {"before_atomic_reveal", "fallback_timeout"}
            else (
                _GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS
                if reason == "after_perceived_ready"
                else 0
            )
        )
        log_event(
            "studio.gicleeframe.section_list.scroll_upgrade_scheduled",
            reason=reason,
            delay_ms=delay_ms,
            perceived_ready_logged=self._perceived_ready_logged,
            static_lane_real_rows=self._section_list_static_lane_real_rows,
            row_count=len(self._section_row_ids),
        )
        self.after(delay_ms, self._upgrade_section_list_scroll)

    def _upgrade_section_list_scroll(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._section_list_scroll_upgrade_done:
            return
        card = self._section_list_column
        if card is None:
            return
        log_event(
            "studio.gicleeframe.section_list.scroll_upgrade_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            real_rows=self._section_list_static_lane_real_rows,
            row_count=len(self._section_row_ids),
        )
        with span("studio.gicleeframe.build.sections_column.scroll_upgrade"):
            static_lane = self._section_list_static_lane
            if static_lane is not None:
                try:
                    static_lane.pack_forget()
                    static_lane.destroy()
                except tk.TclError:
                    pass
                self._section_list_static_lane = None
            self._section_row_frames.clear()
            self._section_row_ids = []
            self._create_section_list_scroll_frame(card)
        self._section_list_scroll_upgrade_done = True
        log_event(
            "studio.gicleeframe.section_list.scroll_upgrade_ready",
            since_enter_ms=self._since_visual_enter_ms(),
            queue_latency_ms=self._queue_latency_since_ms(
                self._sections_column_early_lane_enter_mono,
            ),
        )
        self._flush_pending_section_list_if_needed()
        if (
            _progressive_boot_enabled()
            and not self._progressive_bootstrap_started
            and self._merged
            and self._section_list_scroll is not None
        ):
            self._schedule_section_list_incremental()
        self._schedule_atomic_reveal_check(trigger="scroll_upgrade_ready")

    def _build_sections_column_extras(self, card: ctk.CTkFrame) -> None:
        if self._sections_column_extras_built:
            return

        extras_slot = self._section_list_extras_frame
        if extras_slot is None:
            log_event(
                "studio.gicleeframe.sections_column.extras_skipped_missing_slot",
                reason="slot_none",
            )
            return
        try:
            if not extras_slot.winfo_exists():
                log_event(
                    "studio.gicleeframe.sections_column.extras_skipped_missing_slot",
                    reason="slot_destroyed",
                )
                return
        except tk.TclError:
            log_event(
                "studio.gicleeframe.sections_column.extras_skipped_missing_slot",
                reason="slot_tcl_error",
            )
            return

        title = _make_card_title(
            extras_slot,
            SECTION_LIST_TITLE,
            SECTION_LIST_DRAG_HINT,
        )
        title.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 8))

        self._section_list_trigger = ctk.CTkButton(
            card,
            text=f"{_SECTION_PLACEHOLDER}  ▾",
            anchor="w",
            height=28,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=0,
            text_color=theme.TextMuted,
            font=theme.get_font(10),
            command=self._toggle_section_list,
        )
        self._section_list_trigger.pack_forget()

        self._section_dropdown_popup = _make_gf_card(
            card,
            variant="panel",
            radius=14,
        )
        self._section_dropdown_popup.pack_forget()
        self._sections_column_extras_built = True

    def _build_sections_column(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        card = self._build_sections_column_shell(parent)
        self._build_sections_column_extras(card)
        return card

    def _build_section_identity_card(
        self,
        parent: ctk.CTkFrame,
        *,
        pack_before: ctk.CTkBaseClass | None = None,
    ) -> None:
        card = _make_gf_card(parent, variant="panel_deep", radius=16)
        if pack_before is not None:
            card.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0), before=pack_before)
        else:
            card.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 0))
        self._identity_card = card

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=_CARD_PAD_X, pady=(12, 4))

        self._editor_status_dot = ctk.CTkLabel(
            top,
            text="●",
            width=18,
            text_color=theme.StatusOk,
            font=theme.get_font(13),
        )
        self._editor_status_dot.pack(side="left")

        title_block = ctk.CTkFrame(top, fg_color="transparent")
        title_block.pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkLabel(
            title_block,
            text="Workbench sekcji",
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x")
        self._editor_section_subtitle = ctk.CTkLabel(
            title_block,
            text=_SECTION_PLACEHOLDER,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._editor_section_subtitle.pack(fill="x", pady=(2, 0))

        actions = ctk.CTkFrame(top, fg_color="transparent")
        actions.pack(side="right", padx=(12, 0))

        self._editor_header_visible_row = ctk.CTkFrame(actions, fg_color="transparent")
        self._editor_header_visible_row.pack(side="top", anchor="e", pady=(0, 6))
        self._visible_row = self._editor_header_visible_row

        if self._visible_var is None:
            self._visible_var = ctk.BooleanVar(value=True)

        ctk.CTkCheckBox(
            self._editor_header_visible_row,
            text="Widoczna",
            variable=self._visible_var,
            font=theme.get_font(11),
        ).pack(side="right")

        _make_primary_button(
            actions,
            APPLY_RAM_DRAFT_LABEL,
            self._apply_edit_to_draft,
            width=160,
        ).pack(side="top", anchor="e", fill="x")

        ctk.CTkLabel(
            actions,
            text=APPLY_RAM_MICROCOPY,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="e",
        ).pack(side="top", anchor="e", pady=(3, 0))

        self._layer_nav_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._layer_nav_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(8, 0))
        self._layer_nav_frame.pack_forget()

        preview = _make_gf_card(card, variant="preview", radius=14)
        self._section_preview_card = preview
        preview.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))
        preview.pack_propagate(False)
        preview.configure(height=_EDITOR_HERO_PREVIEW_HEIGHT)

        preview_head = ctk.CTkFrame(preview, fg_color="transparent")
        preview_head.pack(fill="x", padx=14, pady=(10, 0))

        ctk.CTkLabel(
            preview_head,
            text=_PREVIEW_SETTINGS_CAPTION.upper(),
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
            anchor="w",
        ).pack(side="left")

        self._section_preview_badge = _make_pill(
            preview_head,
            "RAM preview",
            fg_color=_GF_FIELD,
            text_color=_GF_MUTED,
        )
        self._section_preview_badge.pack(side="right")

        stage = ctk.CTkFrame(preview, fg_color="transparent")
        stage.pack(fill="both", expand=True, padx=18, pady=(8, 14))

        paper = ctk.CTkFrame(stage, fg_color=_GF_PREVIEW_PAPER, corner_radius=10)
        paper.pack(fill="both", expand=True)
        paper.pack_propagate(False)

        mat = ctk.CTkFrame(paper, fg_color=_GF_PREVIEW_MAT, corner_radius=8)
        mat.pack(fill="both", expand=True, padx=18, pady=12)
        mat.pack_propagate(False)
        self._section_preview_canvas = mat

        bootstrap = ctk.CTkFrame(
            mat,
            fg_color=_GF_FIELD,
            corner_radius=8,
            border_width=1,
            border_color=_GF_BORDER,
        )
        bootstrap.pack(fill="both", expand=True, padx=12, pady=10)
        self._preview_bootstrap_panel = bootstrap
        self._preview_bootstrap_status_label = ctk.CTkLabel(
            bootstrap,
            text=_GF_PREVIEW_BOOTSTRAP_STATUS_TEXT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="center",
            justify="center",
            wraplength=320,
        )
        self._preview_bootstrap_status_label.pack(expand=True, fill="both", padx=16, pady=16)
        self._section_preview_line = None

    def _build_action_dock(self, parent: ctk.CTkFrame) -> None:
        action_dock = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=10,
        )
        action_dock.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))

        _make_primary_button(
            action_dock,
            APPLY_RAM_DRAFT_LABEL,
            self._apply_edit_to_draft,
        ).pack(side="left", padx=12, pady=12)

        ctk.CTkLabel(
            action_dock,
            text=APPLY_RAM_MICROCOPY,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(side="left", padx=(0, 12))

    def _build_editor_column(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        card = _make_card(parent, bordered=False, fg_color="transparent")

        self._build_section_identity_card(card)

        self._legacy_msg_label = ctk.CTkLabel(
            card,
            text="",
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
            wraplength=_EDITOR_FORM_WIDTH - 24,
        )

        form_outer = ctk.CTkFrame(card, fg_color="transparent")
        form_outer.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
        form_outer.configure(width=_EDITOR_FORM_WIDTH)
        form_outer.pack_propagate(True)

        self._edit_panel = ctk.CTkFrame(form_outer, fg_color="transparent")
        self._edit_panel.pack(fill="x", anchor="w")
        self._build_edit_panel()

        # F2.2.3: główna akcja RAM jest w identity card, żeby była widoczna od razu.
        # self._build_action_dock(card)

        return card

    def _build_setting_group_card(
        self,
        parent: ctk.CTkBaseClass,
        title: str,
    ) -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
        card = _make_gf_card(parent, variant="soft", radius=14)
        _make_card_title(card, title).pack(fill="x", padx=12, pady=(12, 8))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=2, pady=(0, 6))
        return card, body

    def _build_control_column(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        col = ctk.CTkFrame(parent, fg_color="transparent")
        self._build_control_structure_card(col)
        self._build_control_readiness_card(col)
        self._build_safety_card(col)
        return col

    def _build_control_structure_card(self, parent: ctk.CTkFrame) -> None:
        structure_card = _make_gf_card(parent, variant="panel_deep", radius=16)
        structure_card.pack(fill="x", pady=(0, 10))
        _make_card_title(
            structure_card,
            "Podgląd struktury",
            "Kontrola struktury aktualnego wariantu RAM.",
        ).pack(fill="x", padx=_CARD_PAD_X, pady=(12, 6))
        self._structure_dry_run_btn = _make_secondary_button(
            structure_card,
            CHECK_STRUCTURE_LABEL,
            self._run_structure_dry_run,
            subtle=True,
        )
        self._structure_dry_run_btn.pack(anchor="w", padx=_CARD_PAD_X, pady=(0, 8))
        self._structure_dry_label = _make_empty_state(
            structure_card,
            STRUCTURE_EMPTY_STATE,
            wraplength=_CONTROL_COL_MINSIZE - 28,
        )
        self._structure_dry_label.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 12))

    def _build_safety_card(self, parent: ctk.CTkFrame) -> None:
        card = _make_gf_card(parent, variant="panel_deep", radius=16)
        card.pack(fill="x")
        _make_card_title(card, _SAFETY_TITLE).pack(
            fill="x", padx=_CARD_PAD_X, pady=(12, 8),
        )
        for title, detail in _SAFETY_CHECKLIST:
            _build_safety_row(
                card,
                title,
                detail,
                wraplength=_CONTROL_COL_MINSIZE - 44,
            )
        ctk.CTkLabel(card, text="", height=4).pack()

    def _build_page_top_bar(self, parent: ctk.CTkFrame) -> None:
        """Legacy hook — ops bar moved to _build_command_bar."""
        del parent

    def _build_toolbar_group(
        self,
        parent: ctk.CTkFrame,
        title: str,
        actions: tuple[tuple[str, Callable[[], None]], ...],
    ) -> ctk.CTkFrame:
        group = ctk.CTkFrame(
            parent,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        ctk.CTkLabel(
            group,
            text=title,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))
        btn_row = ctk.CTkFrame(group, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        for label, cmd in actions:
            _make_secondary_button(btn_row, label, cmd).pack(side="left", padx=(0, 6))
        return group

    def _build_edit_panel(self) -> None:
        if self._edit_panel is None:
            return
        self._build_edit_panel_page_context()
        self._build_edit_panel_fields()
        self._build_edit_panel_children()

    def _build_edit_panel_page_context(self) -> None:
        self._ensure_page_context_shell_built()

    def _ensure_page_context_shell_built(self) -> None:
        if self._page_context_shell_built or self._edit_panel is None:
            return
        self._page_context_frame = ctk.CTkFrame(
            self._edit_panel, fg_color="transparent",
        )
        self._page_context_inner = ctk.CTkFrame(
            self._page_context_frame, fg_color="transparent",
        )
        self._page_context_inner.pack(fill="x")
        self._page_context_shell_built = True

    def _build_edit_panel_fields(self) -> None:
        if self._edit_panel is None:
            return
        self._ensure_title_row_built()
        self._ensure_text_row_built()
        self._ensure_alt_row_built()
        self._ensure_image_ref_row_built()
        self._ensure_notes_row_built()
        self._visible_row = self._editor_header_visible_row

    def _ensure_title_row_built(self) -> None:
        if self._title_row_built or self._edit_panel is None:
            return
        self._title_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        title_card, title_body = self._build_setting_group_card(self._title_row, "Tytuł")
        title_card.pack(fill="x", pady=(0, 8))
        self._title_entry = ctk.CTkEntry(title_body, **_f2_entry_kwargs())
        self._title_entry.pack(fill="x")
        self._title_row_built = True

    def _ensure_text_row_built(self) -> None:
        if self._text_row_built or self._edit_panel is None:
            return
        self._text_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        text_card, text_body = self._build_setting_group_card(self._text_row, "Tekst")
        text_card.pack(fill="x", pady=(0, 8))
        self._text_box = ctk.CTkTextbox(text_body, height=72, font=theme.get_font(11))
        self._text_box.pack(fill="x")
        self._text_row_built = True

    def _ensure_alt_row_built(self) -> None:
        if self._alt_row_built or self._edit_panel is None:
            return
        self._alt_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        alt_card, alt_body = self._build_setting_group_card(self._alt_row, "Alt")
        alt_card.pack(fill="x", pady=(0, 8))
        self._alt_entry = ctk.CTkEntry(alt_body, **_f2_entry_kwargs())
        self._alt_entry.pack(fill="x")
        self._alt_row_built = True

    def _ensure_image_ref_row_built(self) -> None:
        if self._image_ref_row_built or self._edit_panel is None:
            return
        self._image_ref_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        ref_card, ref_body = self._build_setting_group_card(
            self._image_ref_row, _IMAGE_SOURCE_TITLE,
        )
        ref_card.pack(fill="x", pady=(0, 8))
        self._image_ref_entry = ctk.CTkEntry(ref_body, state="disabled", **_f2_entry_kwargs())
        self._image_ref_entry.pack(fill="x")
        self._image_ref_row_built = True

    def _ensure_notes_row_built(self) -> None:
        if self._notes_row_built or self._edit_panel is None:
            return
        self._notes_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        self._notes_group_frame, notes_body = self._build_setting_group_card(
            self._notes_row, "Notatka",
        )
        self._notes_box = ctk.CTkTextbox(
            notes_body,
            height=42,
            font=theme.get_font(10),
            fg_color=_GF_FIELD,
            border_width=1,
            border_color=_GF_BORDER,
        )
        self._notes_box.pack(fill="x")
        self._notes_row_built = True

    def _build_edit_panel_children(self) -> None:
        self._ensure_children_overview_built()

    def _ensure_children_overview_built(self) -> None:
        if self._children_overview_built or self._edit_panel is None:
            return
        self._children_overview_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        child_card, child_body = self._build_setting_group_card(
            self._children_overview_row, _LAYER_NAV_TITLE,
        )
        child_card.pack(fill="x", pady=(0, 4))
        self._children_overview_buttons = ctk.CTkFrame(child_body, fg_color="transparent")
        self._children_overview_buttons.pack(fill="x")
        self._children_overview_built = True

    def _hide_editor_field_placeholder_if_needed(self) -> None:
        if self._editor_placeholder_label is None:
            return
        try:
            if self._editor_placeholder_label.winfo_manager():
                self._editor_placeholder_label.pack_forget()
        except tk.TclError:
            pass

    def _ensure_editor_rows_for_fields(self, fields: EditorFieldVisibility) -> None:
        if fields.title:
            self._ensure_title_row_built()
        if fields.text:
            self._ensure_text_row_built()
        if fields.alt:
            self._ensure_alt_row_built()
        if fields.image_ref:
            self._ensure_image_ref_row_built()
        if fields.notes:
            self._ensure_notes_row_built()
        if fields.children:
            self._ensure_children_overview_built()
        if fields.page_context:
            self._ensure_page_context_shell_built()
        if fields.visible and self._visible_row is None:
            self._visible_row = self._editor_header_visible_row
        self._hide_editor_field_placeholder_if_needed()

    def _ensure_minimal_editor_rows_for_fields(self, fields: EditorFieldVisibility) -> None:
        if fields.title:
            self._ensure_title_row_built()
        if fields.text:
            self._ensure_text_row_built()
        if fields.alt:
            self._ensure_alt_row_built()
        if fields.image_ref:
            self._ensure_image_ref_row_built()
        if fields.notes:
            self._ensure_notes_row_built()
        if fields.page_context:
            self._ensure_page_context_shell_built()
        if fields.visible and self._visible_row is None:
            self._visible_row = self._editor_header_visible_row
        self._hide_editor_field_placeholder_if_needed()

    def _reset_structure_dry_run_display(self) -> None:
        if self._structure_dry_label:
            self._structure_dry_label.configure(
                text=STRUCTURE_EMPTY_STATE,
                text_color=theme.TextMuted,
            )

    def _toggle_f1_section(self) -> None:
        if self._f1_panel is None:
            return
        if self._f1_expanded.get():
            if (
                not self._f1_deferred_built
                and _lazy_shell_enabled()
                and _progressive_boot_enabled()
            ):
                for child in self._f1_panel.winfo_children():
                    child.destroy()
                with span("studio.gicleeframe.build.f1_brand_section.deferred"):
                    self._build_f1_brand_section_panel_content()
                self._f1_deferred_built = True
                log_event("studio.gicleeframe.f1.build_on_expand")
            self._f1_panel.pack(fill="x", padx=24, pady=(0, 4))
        else:
            self._f1_panel.pack_forget()

    def _sync_working_variant_menu(self) -> None:
        if self._working_variant_menu is None:
            return
        pairs = self._page_draft.variant_names()
        self._working_variant_map = {}
        labels: list[str] = []
        for vid, _name in pairs:
            variant = self._page_draft.variants[vid]
            label = working_variant_menu_label(variant)
            labels.append(label)
            self._working_variant_map[label] = vid
        if not labels:
            return
        menu_values = labels
        self._working_variant_menu.configure(values=menu_values)
        active_label = working_variant_menu_label(self._page_draft.active_variant())
        if active_label in labels:
            self._working_variant_menu.set(active_label)
        else:
            self._working_variant_menu.set(labels[0])

    def _on_working_variant_selected(self, label: str) -> None:
        vid = self._working_variant_map.get(label)
        if not vid:
            return
        self._page_draft.switch_variant(vid)
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        self._render_section_menu()
        if self._selected_id:
            m = self._merged_by_id.get(self._selected_id)
            if m is not None:
                self._populate_editor(m)
            else:
                self._selected_id = None
        if self._on_status:
            self._on_status(
                f"Wariant roboczy: {self._page_draft.draft_name} · {RAM_ONLY_STATUS}"
            )

    def _update_top_bar(self) -> None:
        inv = self._inventory
        source_variant = inv.variant_id if inv else "—"
        count = self._page_draft.draft_edit_count()
        if self._top_meta_label:
            if inv and inv.variant_id:
                source_env = variant_environment_tag(
                    inv.variant_id,
                    active_id=inv.variant_id,
                    live_id=inv.live_variant_id,
                )
                source_line = f"{source_variant} ({source_env}) · {PAGE_SOURCE_FILE}"
            else:
                source_line = f"{source_variant} · {PAGE_SOURCE_FILE}"
            self._top_meta_label.configure(text=source_line)
        self._sync_working_variant_menu()
        if self._change_count_label:
            self._change_count_label.configure(text=f"Zmiany: {count}")

    def _ensure_preserved_selection_populate_after_inventory_light(
        self,
        element_id: str,
        generation: int,
    ) -> None:
        if generation != self._selection_generation:
            return
        if self._selected_id != element_id:
            return
        if self._selection_after_ids:
            return
        m = self._merged_by_id.get(element_id)
        element_type = m.element_type if m is not None else ""
        if m is not None and self._should_run_immediate_selection_populate(m):
            self._selection_populate_scheduled_mono = time.perf_counter()
            log_event(
                "studio.gicleeframe.selection.populate_priority_scheduled",
                element_id=element_id,
                element_type=element_type,
                generation=generation,
                defer_ms=0,
                immediate=True,
                since_click_ms=self._since_selection_click_ms(),
            )
            self._populate_editor_deferred(element_id, generation)
        else:
            self._schedule_selection_populate(
                element_id,
                generation,
                element_type=element_type,
            )
        log_event(
            "studio.gicleeframe.selection.repopulate_after_inventory_scheduled",
            element_id=element_id,
            generation=generation,
            reason="no_pending_populate_job",
            merged_exists=True,
            shell_editor_built=self._shell_editor_built,
        )

    def _refresh_inventory_light(
        self,
        *,
        warn_if_draft: bool = False,
        prebuilt_inventory: object = None,
    ) -> None:
        with span("studio.gicleeframe.refresh_inventory.light"):
            if warn_if_draft and not self._page_draft.is_empty() and self._on_status:
                self._on_status("Odświeżono inventory · RAM draft zachowany")
            selected_before = self._selected_id
            selection_generation = self._selection_generation
            with span("studio.gicleeframe.inventory.load_report"):
                if prebuilt_inventory is not None:
                    self._inventory = prebuilt_inventory  # type: ignore[assignment]
                else:
                    self._inventory = build_gicleeframe_page_inventory(find_components_dir())
            with span("studio.gicleeframe.inventory.merge_draft"):
                self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
            self._update_top_bar()

            preserved_id: str | None = None
            if selected_before is None:
                self._selected_id = None
            elif selected_before in self._merged_by_id:
                preserved_id = selected_before
                self._selected_id = selected_before
                log_event(
                    "studio.gicleeframe.selection.preserved_after_inventory_light",
                    element_id=selected_before,
                    generation=selection_generation,
                    reason="merged_exists",
                    merged_exists=True,
                    shell_editor_built=self._shell_editor_built,
                )
            else:
                self._selected_id = None
                log_event(
                    "studio.gicleeframe.selection.cleared_after_inventory_light",
                    element_id=selected_before,
                    generation=selection_generation,
                    reason="missing_after_merge",
                    merged_exists=False,
                    shell_editor_built=self._shell_editor_built,
                )

            if self._section_list_scroll is None:
                self._pending_section_list_render = True
                log_event("studio.gicleeframe.section_list.defer_until_shell_ready")
                self._try_refresh_static_lane_before_scroll_upgrade()
            elif preserved_id is None:
                self._show_section_list_loading_state()

            if preserved_id is None:
                if self._shell_editor_built or not _lazy_shell_enabled():
                    self._show_editor_placeholder_state()
            else:
                preserved_m = self._merged_by_id.get(preserved_id)
                if preserved_m is not None:
                    self._highlight_section_row()
                    if self._shell_editor_built:
                        self._show_editor_selection_pending_state(preserved_m)
                        self._ensure_preserved_selection_populate_after_inventory_light(
                            preserved_id,
                            selection_generation,
                        )

            if preserved_id is None:
                log_event(
                    "studio.gicleeframe.initial_selection.skipped_progressive",
                    merged_count=len(self._merged),
                )
        log_event(
            "studio.gicleeframe.inventory.light_ready",
            merged_count=len(self._merged),
            tree_rows=len(self._section_tree_rows_cache),
            dropdown_options=len(self._section_dropdown_options_cache),
        )

    def _show_section_list_loading_state(self) -> None:
        if self._section_list_scroll is None:
            if self._section_list_static_lane is not None:
                self._section_list_static_lane_real_rows = False
                for child in self._section_list_static_lane.winfo_children():
                    child.destroy()
                self._section_row_frames.clear()
                self._section_row_ids = []
                ctk.CTkLabel(
                    self._section_list_static_lane,
                    text=_SECTION_LIST_LOADING_TEXT,
                    font=theme.get_font(11),
                    text_color=theme.TextMuted,
                    anchor="w",
                ).pack(fill="x", padx=10, pady=10)
                log_event("studio.gicleeframe.section_list.loading_state")
                return
            self._pending_section_list_render = True
            log_event("studio.gicleeframe.section_list.defer_until_shell_ready")
            return
        for child in self._section_list_scroll.winfo_children():
            child.destroy()
        self._section_row_frames.clear()
        self._section_row_ids = []
        ctk.CTkLabel(
            self._section_list_scroll,
            text=_SECTION_LIST_LOADING_TEXT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=10, pady=10)
        log_event("studio.gicleeframe.section_list.loading_state")

    def _show_editor_placeholder_state(self) -> None:
        if self._editor_status_dot is not None:
            self._editor_status_dot.configure(text="●", text_color=theme.TextMuted)
        if self._editor_section_subtitle is not None:
            self._editor_section_subtitle.configure(text=_EDITOR_PLACEHOLDER_TEXT)
        log_event("studio.gicleeframe.editor.placeholder_state")

    def _run_deferred_bootstrap(self) -> None:
        if self._defer_background_for_selection(
            job="section_list.deferred_bootstrap",
            reason="selection_priority_active",
            callback=self._run_deferred_bootstrap,
        ):
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._progressive_bootstrap_started:
            return
        if self._section_list_scroll is None:
            self._pending_section_list_render = True
            log_event("studio.gicleeframe.section_list.defer_until_shell_ready")
            return
        self._progressive_bootstrap_started = True
        with span("studio.gicleeframe.deferred_bootstrap"):
            self._render_section_list_incremental()

    def _try_mark_progressive_full_ready(self) -> None:
        if self._progressive_full_ready_logged:
            return
        if not _progressive_boot_enabled():
            return
        if not self._progressive_section_list_complete:
            return
        self._progressive_full_ready_logged = True
        log_event(
            "studio.gicleeframe.visual.full_ready_progressive",
            since_enter_ms=self._since_visual_enter_ms(),
            row_count=len(self._section_row_ids),
            f1_deferred=self._f1_deferred_built,
        )

    def _refresh_inventory(self, *, warn_if_draft: bool) -> None:
        with span("studio.gicleeframe.refresh_inventory", warn_if_draft=warn_if_draft):
            if warn_if_draft and not self._page_draft.is_empty() and self._on_status:
                self._on_status("Odświeżono inventory · RAM draft zachowany")
            with span("studio.gicleeframe.inventory.load_report"):
                self._inventory = build_gicleeframe_page_inventory(find_components_dir())
            with span("studio.gicleeframe.inventory.merge_draft"):
                self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
            self._update_top_bar()
            with span("studio.gicleeframe.inventory.render_section_list"):
                self._render_section_menu()
            self._fill_page_readiness(None)
        log_event(
            "studio.gicleeframe.inventory_loaded",
            variant=self._inventory.variant_id if self._inventory else "",
            source_sections=self._inventory.source_section_count if self._inventory else 0,
            elements=len(self._inventory.elements) if self._inventory else 0,
        )
        log_event(
            "studio.gicleeframe.visual.inventory_loaded",
            since_enter_ms=self._since_visual_enter_ms(),
            merged_count=len(self._merged),
        )

    def _selected_section_label(self) -> str:
        if not self._merged:
            return _SECTION_PLACEHOLDER
        options = self._section_dropdown_options_cache
        target_id = self._top_level_row_id_for_selection() or self._selected_id
        if target_id:
            for opt in options:
                if opt.element_id == target_id:
                    return opt.display_label
        return options[0].display_label if options else _SECTION_PLACEHOLDER

    def _update_section_list_trigger(self) -> None:
        if self._section_list_trigger is None:
            return
        chevron = "▴" if self._section_list_expanded.get() else "▾"
        self._section_list_trigger.configure(text=f"{self._selected_section_label()}  {chevron}")

    def _collapse_section_list(self) -> None:
        self._section_list_expanded.set(False)
        if self._section_dropdown_popup is not None:
            self._section_dropdown_popup.place_forget()
        self._unbind_section_dropdown_outside_close()
        self._update_section_list_trigger()

    def _ensure_section_dropdown_rows(self) -> None:
        if self._section_row_ids and self._section_row_frames:
            self._highlight_section_row()
            log_event(
                "studio.gicleeframe.section_dropdown.rows_reused",
                row_count=len(self._section_row_ids),
            )
            return
        log_event("studio.gicleeframe.section_dropdown.rows_rebuilt")
        self._render_section_list()

    def _open_section_dropdown(self) -> None:
        if (
            self._section_dropdown_popup is None
            or self._section_list_trigger is None
            or self._section_list_column is None
        ):
            return
        self._section_list_expanded.set(True)
        self._ensure_section_dropdown_rows()
        trigger = self._section_list_trigger
        parent = self._section_list_column
        popup_width = max(trigger.winfo_width(), _SECTION_LIST_WIDTH)
        self._section_dropdown_popup.configure(width=popup_width)
        if self._section_list_scroll is not None:
            self._section_list_scroll.configure(width=max(popup_width - 12, 180))
        parent.update_idletasks()
        x = trigger.winfo_rootx() - parent.winfo_rootx()
        y = trigger.winfo_rooty() - parent.winfo_rooty() + trigger.winfo_height() + 2
        self._section_dropdown_popup.place(x=x, y=y)
        self._section_dropdown_popup.lift()
        self.after(80, self._bind_section_dropdown_outside_close)
        self._update_section_list_trigger()

    def _widget_in_section_dropdown(self, widget: ctk.CTkBaseClass | None) -> bool:
        popup = self._section_dropdown_popup
        trigger = self._section_list_trigger
        current: ctk.CTkBaseClass | None = widget
        while current is not None:
            if current is popup or current is trigger:
                return True
            current = current.master  # type: ignore[assignment]
        return False

    def _bind_section_dropdown_outside_close(self) -> None:
        if self._section_outside_close_active:
            return
        self._section_outside_close_active = True
        self.winfo_toplevel().bind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
            add="+",
        )

    def _unbind_section_dropdown_outside_close(self) -> None:
        if not self._section_outside_close_active:
            return
        self._section_outside_close_active = False
        self.winfo_toplevel().unbind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
        )

    def _on_section_dropdown_outside_click(self, event: object) -> None:
        if not self._section_list_expanded.get():
            return
        widget = getattr(event, "widget", None)
        if self._widget_in_section_dropdown(widget):
            return
        self._collapse_section_list()

    def _toggle_section_list(self) -> None:
        if self._section_list_expanded.get():
            self._collapse_section_list()
        else:
            self._open_section_dropdown()

    def _render_section_list(self) -> None:
        """Pełny rebuild listy sekcji — partiami między klatkami (bez ~0.5 s freeze)."""
        if self._section_list_scroll is None:
            return
        self._full_list_render_generation = getattr(self, "_full_list_render_generation", 0) + 1
        generation = self._full_list_render_generation
        batch_started = time.perf_counter()
        with span(
            "studio.gicleeframe.render_section_list",
            merged_count=len(self._merged),
            has_selected=bool(self._selected_id),
        ):
            for child in self._section_list_scroll.winfo_children():
                child.destroy()
            self._section_row_frames.clear()
            self._section_row_ids: list[str] = []
            self._highlighted_section_id = None

            if not self._merged:
                ctk.CTkLabel(
                    self._section_list_scroll,
                    text=_SECTION_PLACEHOLDER,
                    font=theme.get_font(11),
                    text_color=theme.TextMuted,
                    anchor="w",
                ).pack(fill="x", padx=8, pady=8)
                return

            if not self._section_tree_rows_cache and self._merged:
                self._rebuild_page_model_cache()

            options = list(self._section_dropdown_options_cache)
            self._render_full_list_chunk(options, 0, generation, batch_started)

    def _render_full_list_chunk(
        self,
        options: list[SectionDropdownOption],
        start: int,
        generation: int,
        batch_started: float,
    ) -> None:
        if generation != getattr(self, "_full_list_render_generation", 0):
            return
        if self._section_list_scroll is None:
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        end = min(start + _GF_SECTION_BATCH_SIZE, len(options))
        for index in range(start, end):
            opt = options[index]
            self._section_row_ids.append(opt.element_id)
            self._build_section_row(index, opt.element_id, opt.display_label)
        if end < len(options):
            self.after(
                _GF_SECTION_BATCH_DELAY_MS,
                lambda: self._render_full_list_chunk(options, end, generation, batch_started),
            )
            return
        self._finalize_full_list_render(options, batch_started)

    def _finalize_full_list_render(
        self,
        options: list[SectionDropdownOption],
        batch_started: float,
    ) -> None:
        if self._selected_id is None and options:
            if _progressive_boot_enabled():
                self._selected_id = None
                self._show_editor_placeholder_state()
                log_event(
                    "studio.gicleeframe.initial_selection.skipped_progressive",
                    merged_count=len(self._merged),
                )
            else:
                with span("studio.gicleeframe.inventory.initial_selection"):
                    self._select_element(options[0].element_id)
        else:
            self._highlight_section_row()
        self._update_section_list_trigger()
        elapsed_ms = round((time.perf_counter() - batch_started) * 1000, 2)
        log_event(
            "studio.gicleeframe.section_list_rendered",
            row_count=len(self._section_row_ids),
            selected_id=self._selected_id or "",
        )
        log_event(
            "studio.gicleeframe.render_section_list.stats",
            row_count=len(self._section_row_ids),
            rows_created=len(options),
            widgets_per_row=5,
            total_rows_created=len(options),
            elapsed_ms=elapsed_ms,
        )

    def _render_section_list_incremental(self) -> None:
        if self._defer_background_for_selection(
            job="section_list.incremental",
            reason="selection_priority_active",
            callback=self._render_section_list_incremental,
        ):
            return
        self._section_list_incremental_enter_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.section_list.incremental_enter",
            since_enter_ms=self._since_visual_enter_ms(),
            row_count=len(self._section_dropdown_options_cache),
            queue_latency_ms=self._queue_latency_since_ms(
                self._section_list_incremental_scheduled_mono,
            ),
        )
        if self._section_list_scroll is None:
            return
        if not self._merged:
            self._progressive_section_list_complete = True
            self._section_list_first_visible_built = True
            self._log_visual_gate_ready(
                "first_visible",
                source="incremental_empty",
                since_scheduled_mono=self._section_list_incremental_enter_mono,
            )
            self._try_mark_perceived_ready(trigger="incremental_empty")
            self._try_mark_progressive_full_ready()
            return

        if not self._section_tree_rows_cache and self._merged:
            self._rebuild_page_model_cache()

        options = list(self._section_dropdown_options_cache)
        self._section_row_frames.clear()
        self._section_row_ids = []
        self._highlighted_section_id = None

        for child in self._section_list_scroll.winfo_children():
            child.destroy()

        log_event(
            "studio.gicleeframe.section_list.incremental_start",
            row_count=len(options),
            batch_size=_GF_SECTION_BATCH_SIZE,
        )
        self._render_section_list_batch(options, 0)

    def _render_section_list_batch(
        self,
        options: list[SectionDropdownOption],
        start: int,
    ) -> None:
        if start > 0 and self._defer_background_for_selection(
            job="section_list.incremental_batch",
            reason="selection_priority_active",
            callback=lambda o=options, s=start: self._render_section_list_batch(o, s),
        ):
            return
        if self._section_list_scroll is None:
            return

        started = time.perf_counter()
        batch_size = _GF_SECTION_FIRST_BATCH_SIZE if start == 0 else _GF_SECTION_BATCH_SIZE
        if start == 0:
            log_event(
                "studio.gicleeframe.section_list.first_batch_start",
                since_enter_ms=self._since_visual_enter_ms(),
            )
            with span("studio.gicleeframe.section_list.first_batch.prepare"):
                end = min(start + batch_size, len(options))
            with span("studio.gicleeframe.section_list.first_batch.rows"):
                for idx in range(start, end):
                    opt = options[idx]
                    self._section_row_ids.append(opt.element_id)
                    self._create_section_list_row(idx, opt.element_id, opt.display_label)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                "studio.gicleeframe.section_list.incremental_batch",
                start=start,
                end=end,
                created=end - start,
                elapsed_ms=elapsed_ms,
                total_rows=len(options),
                batch_size=batch_size,
            )
            with span("studio.gicleeframe.section_list.first_batch.pack_or_layout"):
                if not self._section_list_first_visible_built:
                    log_event(
                        "studio.gicleeframe.section_list.first_visible_ready",
                        since_enter_ms=self._since_visual_enter_ms(),
                        created=end - start,
                        elapsed_ms=elapsed_ms,
                        queue_latency_ms=self._queue_latency_since_ms(
                            self._section_list_incremental_enter_mono,
                        ),
                        source="incremental",
                    )
                    self._section_list_first_visible_built = True
                    self._log_visual_gate_ready(
                        "first_visible",
                        source="incremental",
                        since_scheduled_mono=self._section_list_incremental_enter_mono,
                    )
                    self._try_mark_perceived_ready(trigger="incremental_first_visible")
                    self._schedule_atomic_reveal_check(trigger="section_rows_first_visible")
        else:
            end = min(start + batch_size, len(options))

            for idx in range(start, end):
                opt = options[idx]
                self._section_row_ids.append(opt.element_id)
                self._create_section_list_row(idx, opt.element_id, opt.display_label)

            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                "studio.gicleeframe.section_list.incremental_batch",
                start=start,
                end=end,
                created=end - start,
                elapsed_ms=elapsed_ms,
                total_rows=len(options),
                batch_size=batch_size,
            )

        if end < len(options):
            self._schedule_section_list_batch_continuation(options, end)
            return

        self._selected_id = None
        self._show_editor_placeholder_state()
        log_event(
            "studio.gicleeframe.initial_selection.skipped_progressive",
            merged_count=len(self._merged),
        )
        log_event(
            "studio.gicleeframe.section_list.incremental_done",
            row_count=len(options),
        )
        self.after_idle(self._precompute_page_context_specs_cache)
        self._update_section_list_trigger()
        self._progressive_section_list_complete = True
        self._try_mark_progressive_full_ready()

    def _create_section_list_row(
        self,
        index: int,
        element_id: str,
        label: str,
        *,
        parent: ctk.CTkBaseClass | None = None,
        static_lane: bool = False,
    ) -> None:
        list_parent = parent if parent is not None else self._section_list_scroll
        if list_parent is None:
            return
        row = ctk.CTkFrame(
            list_parent,
            fg_color="transparent",
            corner_radius=12,
            height=_SECTION_ROW_HEIGHT,
        )
        row.pack(fill="x", padx=3, pady=4)
        row.pack_propagate(False)
        self._section_row_frames[element_id] = row

        if not static_lane:
            grip = ctk.CTkLabel(
                row,
                text=_SECTION_ROW_GRIP,
                width=12,
                font=theme.get_font(9),
                text_color=theme.TextMuted,
                cursor="size_ns",
            )
            grip.pack(side="left", padx=(8, 0))
            grip.bind("<ButtonPress-1>", lambda _e, i=index: self._start_section_drag(i))
            grip.bind("<ButtonRelease-1>", self._finish_section_drag)

        index_pill = ctk.CTkLabel(
            row,
            text=f"{index + 1:02d}",
            width=28,
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
            fg_color=_GF_FIELD,
            corner_radius=999,
            padx=6,
            pady=2,
        )
        index_pill.pack(side="left", padx=((14 if static_lane else 6), 4))

        label_block = ctk.CTkFrame(row, fg_color="transparent")
        label_block.pack(side="left", fill="x", expand=True, padx=(4, 8))
        kind = _section_kind_copy(element_id, self._merged)
        if kind:
            ctk.CTkLabel(
                label_block,
                text=kind.upper(),
                font=theme.get_font(8, "bold"),
                text_color=_GF_MUTED,
                anchor="w",
            ).pack(fill="x", pady=(0, 2))
        title = ctk.CTkLabel(
            label_block,
            text=_ellipsize(label, 36),
            anchor="w",
            height=24,
            text_color=theme.TextPrimary,
            font=theme.get_font(11, "bold"),
        )
        title.pack(fill="x")

        for target in (row, label_block, title, index_pill):
            target.bind(
                "<Button-1>",
                lambda _e, eid=element_id: self._on_section_row_click(eid),
            )

    def _on_section_row_click(self, element_id: str) -> None:
        self._selection_click_mono = time.perf_counter()
        m_click = self._merged_by_id.get(element_id)
        log_event(
            "studio.gicleeframe.selection.click",
            element_id=element_id,
            element_type=m_click.element_type if m_click is not None else "",
            source="row",
            generation=self._selection_generation + 1,
            static_lane=bool(
                self._section_list_static_lane is not None
                and not self._section_list_scroll_upgrade_done
            ),
            scroll_ready=self._section_list_scroll_upgrade_done,
            selection_generation_next=self._selection_generation + 1,
            since_enter_ms=self._since_visual_enter_ms(),
            perceived_ready_logged=self._perceived_ready_logged,
            shell_control_built=self._shell_control_built,
        )
        self._select_element(
            element_id,
            collapse_list=_collapse_section_list_on_click_enabled(),
        )

    def _build_section_row(self, index: int, element_id: str, label: str) -> None:
        self._create_section_list_row(index, element_id, label)

    def _top_level_row_id_for_element(self, element_id: str | None) -> str | None:
        if element_id is None:
            return None
        selected = self._merged_by_id.get(element_id)
        if selected is None:
            return None
        if selected.element_type in ("jumbo", "body", "image"):
            for row in self._section_tree_rows_cache:
                if row.section_key == selected.section_key and row.row_kind == "media_section":
                    return row.element_id
            return None
        return element_id

    def _top_level_row_id_for_selection(self) -> str | None:
        return self._top_level_row_id_for_element(self._selected_id)

    def _set_section_row_highlight(self, element_id: str | None, active: bool) -> None:
        if not element_id:
            return
        frame = self._section_row_frames.get(element_id)
        if frame is None:
            return

        try:
            if active:
                frame.configure(
                    fg_color=_GF_CARD_SOFT,
                    border_width=1,
                    border_color=_GF_BORDER_WARM,
                    corner_radius=12,
                )
            else:
                frame.configure(
                    fg_color="transparent",
                    border_width=0,
                    corner_radius=12,
                )
        except Exception:
            return

    def _highlight_section_row(self, previous_id: str | None = None) -> None:
        target = self._top_level_row_id_for_selection()
        previous_target = self._top_level_row_id_for_element(previous_id)
        if previous_target and previous_target != target:
            self._set_section_row_highlight(previous_target, False)
        self._set_section_row_highlight(target, True)
        self._highlighted_section_id = target

    def _highlight_section_rows(self) -> None:
        """Full re-highlight after list rebuild — scans all visible rows."""
        target = self._top_level_row_id_for_selection()
        for element_id in self._section_row_ids:
            self._set_section_row_highlight(element_id, element_id == target)
        self._highlighted_section_id = target

    def _section_row_index_at_root_y(self, y_root: int) -> int | None:
        for index, element_id in enumerate(self._section_row_ids):
            frame = self._section_row_frames.get(element_id)
            if frame is None:
                continue
            top = frame.winfo_rooty()
            if top <= y_root < top + frame.winfo_height():
                return index
        return None

    def _start_section_drag(self, index: int) -> None:
        self._drag_from_index = index
        if 0 <= index < len(self._section_row_ids):
            frame = self._section_row_frames.get(self._section_row_ids[index])
            if frame is not None:
                frame.configure(fg_color=_GF_CARD_SOFT)

    def _finish_section_drag(self, event: object) -> None:
        from_index = self._drag_from_index
        self._drag_from_index = None
        for element_id in self._section_row_ids:
            frame = self._section_row_frames.get(element_id)
            if frame is not None:
                frame.configure(fg_color="transparent")
        y_root = getattr(event, "y_root", None)
        if from_index is None or y_root is None:
            self._highlight_section_rows()
            return
        to_index = self._section_row_index_at_root_y(int(y_root))
        if to_index is None or from_index == to_index:
            self._highlight_section_rows()
            return
        if not reorder_page_blocks(self._page_draft, self._merged, from_index, to_index):
            self._highlight_section_rows()
            return
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        selected = self._selected_id
        self._render_section_list()
        if selected:
            m = self._merged_by_id.get(selected)
            if m is not None:
                self._selected_id = selected
                self._populate_editor(m)
        if self._on_status:
            self._on_status("Kolejność zaktualizowana w RAM · nic nie zapisano")

    def _render_section_menu(self) -> None:
        self._render_section_list()

    def _select_element(
        self,
        element_id: str,
        *,
        collapse_list: bool = False,
    ) -> None:
        previous_id = self._selected_id
        self._selection_generation += 1
        generation = self._selection_generation
        started = time.perf_counter()
        m_preview = self._merged_by_id.get(element_id)

        log_event(
            "studio.gicleeframe.selection.start",
            element_id=element_id,
            element_type=m_preview.element_type if m_preview is not None else "",
            previous_id=previous_id or "",
            generation=generation,
            collapse_list=collapse_list,
            elapsed_ms=0.0,
            since_click_ms=self._since_selection_click_ms(),
        )
        log_event(
            "studio.gicleeframe.select_element.user_or_programmatic",
            element_id=element_id,
            progressive_boot=_progressive_boot_enabled(),
            selected_before=previous_id or "",
        )

        selection_jobs_cancelled = self._cancel_selection_jobs()
        details_jobs_cancelled = self._cancel_details_on_demand_jobs()
        self._page_context_generation += 1
        page_context_jobs_cancelled = self._cancel_page_context_jobs()
        if selection_jobs_cancelled or page_context_jobs_cancelled:
            log_event(
                "studio.gicleeframe.selection.jobs_cancelled",
                selection_jobs_cancelled=selection_jobs_cancelled,
                page_context_jobs_cancelled=page_context_jobs_cancelled,
                generation=generation,
                element_id=element_id,
            )
        if details_jobs_cancelled:
            request_open_ms = self._since_details_request_ms()
            log_event(
                "studio.gicleeframe.details_on_demand.cancelled",
                element_id=element_id,
                previous_details_element_id=self._details_on_demand_active_element_id or "",
                details_jobs_cancelled=details_jobs_cancelled,
                generation=generation,
                request_open_ms=request_open_ms,
            )
            self._hide_details_container()
            self._details_on_demand_active_element_id = None
            self._details_on_demand_request_mono = None
            self._details_cta_click_mono = None

        self._close_active_setting_editor()
        self._selected_id = element_id
        m = self._merged_by_id.get(element_id)
        if m is None:
            log_event("studio.gicleeframe.select_element.missing", element_id=element_id)
            return

        self._highlight_section_row(previous_id)
        log_event(
            "studio.gicleeframe.selection.immediate_highlight_done",
            element_id=element_id,
            element_type=m.element_type,
            previous_id=previous_id or "",
            generation=generation,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        self._update_section_list_trigger()
        minimal_entry = self._minimal_cache_entry(m)
        minimal_cache_hit = minimal_entry is not None
        self._selection_visual_cache_applied = minimal_cache_hit
        self._details_on_demand_expanded = False
        # Schowaj stare panele szczegółów od razu — inaczej panel poprzedniej
        # sekcji i nowy blok on-demand nakładają się podczas ładowania.
        self._hide_details_shell()
        self._hide_details_on_demand_block()
        if minimal_cache_hit:
            self._apply_minimal_cache(m)
            log_event(
                "studio.gicleeframe.selection.minimal_cache_hit",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.selection.cache_hit_skip_visible_refresh",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                since_click_ms=self._since_selection_click_ms(),
            )
        else:
            if self._section_visual_cache.get(m.element_id) is not None:
                log_event(
                    "studio.gicleeframe.selection.cache_hit_partial",
                    element_id=element_id,
                    element_type=m.element_type,
                    generation=generation,
                    since_click_ms=self._since_selection_click_ms(),
                )
            log_event(
                "studio.gicleeframe.selection.minimal_cache_miss",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.selection.cache_miss_stable_shell",
                element_id=element_id,
                element_type=m.element_type,
                since_click_ms=self._since_selection_click_ms(),
            )
            if self._editor_has_ready_content:
                self._show_editor_refresh_status(_GF_ATOMIC_SWAP_STATUS_TEXT)
                log_event(
                    "studio.gicleeframe.editor.stale_content_kept",
                    element_id=element_id,
                    element_type=m.element_type,
                    previous_element_id=self._editor_last_ready_element_id or "",
                    since_click_ms=self._since_selection_click_ms(),
                )
            else:
                self._hide_media_details_stable_shell()
                self._show_editor_selection_stable_shell_state(m, from_cache=False)
            log_event(
                "studio.gicleeframe.selection.atomic_swap.scheduled",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                since_click_ms=self._since_selection_click_ms(),
            )
        log_event(
            "studio.gicleeframe.selection.pending_state_done",
            element_id=element_id,
            element_type=m.element_type,
            previous_id=previous_id or "",
            generation=generation,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        if collapse_list:
            self._collapse_section_list()

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.select_element.immediate_ready",
            element_id=element_id,
            element_type=m.element_type,
            previous_id=previous_id or "",
            elapsed_ms=elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.selection.immediate_ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
            elapsed_ms=elapsed_ms,
        )

        self._open_selection_priority_window(
            generation,
            element_id=element_id,
            element_type=m.element_type,
        )

        if minimal_cache_hit:
            return

        self._selection_populate_scheduled_mono = time.perf_counter()
        log_event(
            "studio.gicleeframe.selection.populate_priority_scheduled",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            defer_ms=0,
            immediate=True,
            atomic_swap=True,
            since_click_ms=self._since_selection_click_ms(),
        )
        log_event(
            "studio.gicleeframe.selection.populate_scheduled",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
            immediate=True,
            atomic_swap=True,
        )
        self._schedule_atomic_swap_populate(element_id, generation)

    def _ensure_media_details_stable_shell(self) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._identity_card is None:
            return
        if not self._media_details_stable_built:
            frame = ctk.CTkFrame(
                self._identity_card,
                fg_color=_GF_FIELD,
                corner_radius=10,
                border_width=1,
                border_color=_GF_BORDER,
                height=_GF_MEDIA_DETAILS_STABLE_HEIGHT,
            )
            frame.pack_propagate(False)
            self._media_details_status_label = ctk.CTkLabel(
                frame,
                text=_GF_MEDIA_DETAILS_STATUS_TEXT,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="w",
            )
            self._media_details_status_label.pack(fill="x", padx=12, pady=10)
            self._media_details_stable_frame = frame
            self._media_details_stable_built = True
        if self._media_details_stable_frame is None:
            return
        if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            self._media_details_stable_frame.pack(
                fill="x",
                padx=_CARD_PAD_X,
                pady=(0, 4),
                before=self._layer_nav_frame,
            )
        else:
            self._media_details_stable_frame.pack(
                fill="x",
                padx=_CARD_PAD_X,
                pady=(0, 4),
            )

    def _hide_media_details_stable_shell(self) -> None:
        if self._media_details_stable_frame is None:
            return
        try:
            self._media_details_stable_frame.pack_forget()
        except tk.TclError:
            pass

    def _log_editor_skeleton_suppressed(
        self,
        *,
        element_id: str,
        element_type: str,
        reason: str,
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.skeleton_suppressed",
            element_id=element_id,
            element_type=element_type,
            reason=reason,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _show_editor_refresh_status(self, text: str) -> None:
        if self._identity_card is None:
            return
        if self._editor_refresh_status_frame is None:
            frame = ctk.CTkFrame(self._identity_card, fg_color="transparent")
            self._editor_refresh_status_label = ctk.CTkLabel(
                frame,
                text=text,
                font=theme.get_font(9),
                text_color=theme.TextMuted,
                anchor="w",
            )
            self._editor_refresh_status_label.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 4))
            self._editor_refresh_status_frame = frame
        elif self._editor_refresh_status_label is not None:
            self._editor_refresh_status_label.configure(text=text)
        if self._editor_refresh_status_frame is None:
            return
        try:
            self._editor_refresh_status_frame.pack(
                fill="x",
                padx=0,
                pady=(0, 2),
                before=self._layer_nav_frame
                if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager()
                else None,
            )
        except tk.TclError:
            try:
                self._editor_refresh_status_frame.pack(fill="x", padx=0, pady=(0, 2))
            except tk.TclError:
                pass

    def _hide_editor_refresh_status(self) -> None:
        if self._editor_refresh_status_frame is None:
            return
        try:
            self._editor_refresh_status_frame.pack_forget()
        except tk.TclError:
            pass

    def _mark_editor_content_ready(self, m: MergedPageElement) -> None:
        self._editor_has_ready_content = True
        self._editor_last_ready_element_id = m.element_id

    def _log_editor_content_swapped(
        self,
        m: MergedPageElement,
        *,
        region: str,
        preview_key: str = "",
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.content_swapped",
            element_id=m.element_id,
            element_type=m.element_type,
            region=region,
            preview_key=preview_key,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _minimal_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        return self._section_visual_cache.get(m.element_id)

    def _details_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        entry = self._section_visual_cache.get(m.element_id)
        if entry is None:
            return None
        if self._any_details_module_cached(entry):
            return entry
        if entry.media_details_built:
            return entry
        return None

    def _any_details_module_cached(self, entry: SectionVisualCacheEntry) -> bool:
        return any(
            (
                entry.details_cache_preview,
                entry.details_cache_page_context,
                entry.details_cache_layer_nav,
                entry.details_cache_children,
            )
        )

    def _details_module_cache_hit(self, entry: SectionVisualCacheEntry, module: str) -> bool:
        return {
            "preview": entry.details_cache_preview,
            "page_context": entry.details_cache_page_context,
            "layer_nav": entry.details_cache_layer_nav,
            "children": entry.details_cache_children,
        }.get(module, False)

    def _cached_details_modules(self, entry: SectionVisualCacheEntry) -> list[str]:
        modules: list[str] = []
        if entry.details_cache_preview:
            modules.append("preview")
        if entry.details_cache_page_context:
            modules.append("page_context")
        if entry.details_cache_layer_nav:
            modules.append("layer_nav")
        if entry.details_cache_children:
            modules.append("children")
        return modules

    def _full_visual_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        """Legacy alias — details cache only."""
        return self._details_cache_entry(m)

    def _fields_from_cache_entry(self, entry: SectionVisualCacheEntry) -> EditorFieldVisibility:
        return EditorFieldVisibility(
            title=entry.fields_title,
            text=entry.fields_text,
            alt=entry.fields_alt,
            image_ref=entry.fields_image_ref,
            notes=entry.fields_notes,
            visible=entry.fields_visible,
            children=entry.fields_children,
            page_context=entry.fields_page_context,
        )

    def _apply_cached_page_context_summary(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.fields_page_context or not entry.page_context_summary:
            if self._page_context_frame is not None:
                self._page_context_frame.pack_forget()
            return
        self._ensure_page_context_shell_built()
        if self._page_context_frame is None or self._page_context_inner is None:
            return
        self._hide_page_context_rows()
        self._clear_page_context_loading_label()
        self._page_context_frame.pack(**self._page_context_pack_kwargs())
        self._get_or_create_readonly_card()
        self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        for label, value in entry.page_context_summary:
            row_key = f"shell_summary:{label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=label,
                kind="shell_summary",
            )
            value_widget.configure(text=value)
            self._show_page_context_row(row_key, fill="x", pady=2)

    def _apply_cached_preview_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_preview or not entry.preview_key:
            return
        preview_key = entry.preview_key
        self._ensure_preview_structure(preview_key)
        self._show_preview_frame(preview_key)
        self._show_heavy_editor_modules()

    def _apply_cached_page_context_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_page_context:
            return
        self._apply_cached_page_context_summary(entry)

    def _apply_cached_layer_nav_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_layer_nav:
            return
        if entry.layer_nav_visible and self._layer_nav_frame is not None:
            if not self._layer_nav_frame.winfo_manager():
                self._layer_nav_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(8, 0))
            header = self._get_or_create_layer_nav_header()
            if "header:title" not in self._layer_nav_visible_keys:
                header.pack(fill="x", pady=(0, 6))
                self._layer_nav_visible_keys.add("header:title")
            row = self._get_or_create_layer_nav_row()
            if "container:row" not in self._layer_nav_visible_keys:
                row.pack(fill="x")
                self._layer_nav_visible_keys.add("container:row")
            desired_keys: list[str] = []
            for index, title in enumerate(entry.layer_nav_titles):
                slot_key = f"slot:{index}"
                desired_keys.append(slot_key)
                self._update_layer_nav_tile(
                    slot_key,
                    kind="SEKCJA" if index == 0 else "WARSTWA",
                    title=title,
                    active=index == 0,
                )
            self._sync_layer_nav_visibility(desired_keys)

    def _apply_cached_children_module(
        self,
        m: MergedPageElement,
        entry: SectionVisualCacheEntry,
    ) -> None:
        if not entry.details_cache_children:
            return
        self._set_row_visible(self._children_overview_row, entry.fields_children)
        if entry.fields_children:
            self._fill_children_overview_buttons(m, stale_refresh=False)

    def _apply_cached_media_details(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.media_details_built and not self._any_details_module_cached(entry):
            return
        self._apply_cached_preview_module(entry)
        self._apply_cached_layer_nav_module(entry)
        self._hide_media_details_stable_shell()

    def _apply_section_visual_cache(self, m: MergedPageElement) -> bool:
        """Legacy alias — minimal cache only."""
        return self._apply_minimal_cache(m)

    def _apply_minimal_cache(self, m: MergedPageElement) -> bool:
        entry = self._section_visual_cache.get(m.element_id)
        if entry is None:
            return False

        self._ensure_editor_identity_built()
        fields = self._fields_from_cache_entry(entry)
        self._ensure_minimal_editor_rows_for_fields(fields)

        dot_color, _ = _element_pill_colors(
            entry.status,
            has_draft_patch=entry.has_draft_patch,
        )
        if self._editor_status_dot:
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=entry.subtitle_text)

        readonly = entry.element_type == "section_legacy"
        self._set_row_visible(self._title_row, fields.title)
        self._set_row_visible(self._text_row, fields.text)
        self._set_row_visible(self._alt_row, fields.alt)
        self._set_row_visible(self._image_ref_row, fields.image_ref)
        self._set_row_visible(self._notes_row, fields.notes)
        self._set_row_visible(self._visible_row, fields.visible)
        self._set_row_visible(self._children_overview_row, False)

        if self._title_entry:
            self._set_entry(self._title_entry, entry.title, readonly=readonly or not fields.title)
        if self._text_box:
            self._set_textbox(self._text_box, entry.text, readonly=readonly or not fields.text)
        if self._alt_entry:
            self._set_entry(self._alt_entry, entry.alt, readonly=readonly or not fields.alt)
        if self._image_ref_entry:
            self._set_entry(self._image_ref_entry, entry.image_ref, readonly=True)
        if self._notes_box:
            self._set_textbox(self._notes_box, entry.notes, readonly=readonly or not fields.notes)
        if self._visible_var is not None and fields.visible:
            self._visible_var.set(entry.visible)

        self._apply_cached_page_context_summary(entry)
        self._hide_heavy_editor_modules()
        self._hide_media_details_stable_shell()
        self._show_details_on_demand_block(m)

        self._page_context_shell_shown_generation = self._selection_generation
        self._mark_editor_stable_shell_ready(m, from_cache=True)
        self._mark_editor_content_ready(m)
        self._hide_editor_refresh_status()
        self._log_minimal_editor_ready(m, from_cache=True)
        return True

    def _log_minimal_editor_ready(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool,
    ) -> None:
        log_event(
            "studio.gicleeframe.selection.minimal_editor_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            since_click_ms=self._since_selection_click_ms(),
            from_cache=from_cache,
        )

    def _hide_heavy_editor_modules(self) -> None:
        self._hide_preview_frames()
        if self._section_preview_card is not None:
            try:
                self._section_preview_card.pack_forget()
            except tk.TclError:
                pass
        if self._layer_nav_frame is not None:
            try:
                self._layer_nav_frame.pack_forget()
            except tk.TclError:
                pass
        self._set_row_visible(self._children_overview_row, False)

    def _show_heavy_editor_modules(self) -> None:
        if self._section_preview_card is not None:
            try:
                if not self._section_preview_card.winfo_manager():
                    self._section_preview_card.pack(fill="x", padx=_CARD_PAD_X, pady=(10, 14))
            except tk.TclError:
                pass

    def _ensure_details_on_demand_block_built(self) -> None:
        parent = self._identity_card or self._edit_panel
        if self._details_on_demand_built or parent is None:
            return
        frame = ctk.CTkFrame(
            parent,
            fg_color=_GF_FIELD,
            corner_radius=10,
            border_width=1,
            border_color=_GF_BORDER,
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        self._details_on_demand_hint_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_ON_DEMAND_TEXT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._details_on_demand_hint_label.pack(fill="x", pady=(0, 8))
        self._details_on_demand_button = ctk.CTkButton(
            inner,
            text=_GF_DETAILS_ON_DEMAND_BUTTON,
            height=_BTN_HEIGHT,
            width=120,
            fg_color=_GF_CARD_SOFT,
            hover_color=_GF_FIELD_HOVER,
            text_color=theme.TextPrimary,
            command=self._on_details_on_demand_clicked,
        )
        self._details_on_demand_button.pack(anchor="w", fill="x")
        self._details_on_demand_status_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._details_on_demand_frame = frame
        self._details_on_demand_built = True

    def _hide_details_on_demand_block(self) -> None:
        if self._details_on_demand_frame is None:
            return
        try:
            self._details_on_demand_frame.pack_forget()
        except tk.TclError:
            pass
        if self._details_on_demand_status_label is not None:
            self._details_on_demand_status_label.configure(text="")

    def _show_details_on_demand_block(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._details_on_demand_expanded:
            self._hide_details_on_demand_block()
            return
        self._ensure_details_on_demand_block_built()
        if self._details_on_demand_frame is None:
            return
        is_media = m.element_type == "media_section"
        hint = _GF_MEDIA_DETAILS_ON_DEMAND_TEXT if is_media else _GF_DETAILS_ON_DEMAND_TEXT
        button_text = (
            _GF_MEDIA_DETAILS_ON_DEMAND_BUTTON if is_media else _GF_DETAILS_ON_DEMAND_BUTTON
        )
        if self._details_on_demand_hint_label is not None:
            self._details_on_demand_hint_label.configure(text=hint)
        if self._details_on_demand_button is not None:
            self._details_on_demand_button.configure(text=button_text)
        self._details_on_demand_element_id = m.element_id
        cache_entry = self._details_cache_entry(m)
        cached_modules = self._cached_details_modules(cache_entry) if cache_entry else []
        if self._details_on_demand_status_label is not None:
            if cached_modules:
                self._details_on_demand_status_label.configure(
                    text=f"Załadowano: {len(cached_modules)} moduł(y)",
                )
                self._details_on_demand_status_label.pack(fill="x", pady=(8, 0))
            else:
                self._details_on_demand_status_label.configure(text="")
                try:
                    self._details_on_demand_status_label.pack_forget()
                except tk.TclError:
                    pass
        pack_before = None
        if self._section_preview_card is not None:
            pack_before = self._section_preview_card
        elif self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            pack_before = self._layer_nav_frame
        try:
            if pack_before is not None:
                self._details_on_demand_frame.pack(
                    fill="x",
                    padx=_CARD_PAD_X,
                    pady=(0, 8),
                    before=pack_before,
                )
            else:
                self._details_on_demand_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
        except tk.TclError:
            try:
                self._details_on_demand_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
            except tk.TclError:
                pass
        log_event(
            "studio.gicleeframe.details_on_demand.available",
            element_id=m.element_id,
            element_type=m.element_type,
            since_click_ms=self._since_selection_click_ms(),
            details_cached=bool(cached_modules),
        )

    def _on_details_on_demand_clicked(self) -> None:
        element_id = self._details_on_demand_element_id or self._selected_id
        if not element_id:
            return
        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            return

        self._cancel_details_on_demand_jobs()
        self._details_on_demand_generation += 1
        details_generation = self._details_on_demand_generation
        request_started = time.perf_counter()
        self._details_on_demand_request_mono = request_started
        self._details_cta_click_mono = request_started
        self._details_on_demand_active_element_id = element_id

        log_event(
            "studio.gicleeframe.details_on_demand.requested",
            element_id=element_id,
            element_type=m.element_type,
            since_details_cta_ms=0.0,
            since_request_ms=0.0,
            generation=details_generation,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.full_auto_suppressed",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            since_request_ms=self._since_details_request_ms(),
        )
        log_event(
            "studio.gicleeframe.details_shell.requested",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            since_request_ms=self._since_details_request_ms(),
        )

        self._hide_details_on_demand_block()
        self._show_details_shell(m)
        self._details_on_demand_expanded = True
        self._hide_editor_refresh_status()

        elapsed_ms = self._since_details_request_ms()
        log_event(
            "studio.gicleeframe.details_shell.ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_shell.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
            shell_only=True,
        )

    def _on_details_module_clicked(self, module: str) -> None:
        element_id = self._details_on_demand_active_element_id or self._selected_id
        if not element_id:
            return
        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            return

        self._cancel_details_on_demand_jobs()
        self._details_on_demand_generation += 1
        module_generation = self._details_on_demand_generation
        self._details_on_demand_request_mono = time.perf_counter()
        self._details_on_demand_active_element_id = element_id

        log_event(
            "studio.gicleeframe.details_module.requested",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=module_generation,
            since_request_ms=0.0,
        )

        cache_entry = self._section_visual_cache.get(element_id)
        if cache_entry is not None and self._details_module_cache_hit(cache_entry, module):
            log_event(
                "studio.gicleeframe.details_module.cache_hit",
                module=module,
                element_id=element_id,
                element_type=m.element_type,
                generation=module_generation,
                since_request_ms=self._since_details_request_ms(),
            )
            self._apply_details_module_from_cache(m, module, cache_entry, module_generation)
            return

        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADING_STATUS)
        if module == "children":
            self._schedule_details_on_demand_job(
                0,
                lambda mod=module, eid=element_id, gen=module_generation: (
                    self._run_children_details_module_batched(
                        eid,
                        gen,
                        mod,
                        start=0,
                    )
                ),
            )
            return

        self._schedule_details_on_demand_job(
            0,
            lambda mod=module, eid=element_id, gen=module_generation: (
                self._execute_details_module(eid, gen, mod)
            ),
        )

    def _apply_details_module_from_cache(
        self,
        m: MergedPageElement,
        module: str,
        entry: SectionVisualCacheEntry,
        generation: int,
    ) -> None:
        if not self._details_stage_still_valid(m.element_id, generation):
            return
        started = time.perf_counter()
        if module == "preview":
            self._apply_cached_preview_module(entry)
        elif module == "page_context":
            self._apply_cached_page_context_module(entry)
        elif module == "layer_nav":
            self._apply_cached_layer_nav_module(entry)
        elif module == "children":
            self._apply_cached_children_module(m, entry)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )

    def _execute_details_module(self, element_id: str, generation: int, module: str) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        stale_refresh = self._editor_has_ready_content
        fields = editor_field_visibility(m.element_type or "unknown")

        if module == "preview":
            self._show_heavy_editor_modules()
            self._update_section_preview(m, stale_refresh=stale_refresh)
        elif module == "page_context":
            if fields.page_context:
                self._fill_page_context(m, show=True)
        elif module == "layer_nav":
            self._update_layer_nav(m, stale_refresh=stale_refresh)
        elif module == "children":
            self._set_row_visible(self._children_overview_row, True)
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)

        self._save_details_module_cache(m, module, fields)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=False,
        )

    def _run_children_details_module_batched(
        self,
        element_id: str,
        generation: int,
        module: str,
        *,
        start: int,
    ) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        parent_row = self._tree_row_for_element(element_id)
        children = parent_row.children if parent_row is not None else ()
        total = len(children)
        end = min(start + _GF_DETAILS_CHILDREN_BATCH_SIZE, total)
        started = time.perf_counter()
        stale_refresh = self._editor_has_ready_content

        self._set_row_visible(self._children_overview_row, True)
        self._fill_children_overview_buttons_range(
            m,
            start,
            end,
            stale_refresh=stale_refresh and start == 0,
        )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if total > 2 or (total > 0 and end < total):
            log_event(
                "studio.gicleeframe.details_module.batch",
                module=module,
                start=start,
                end=end,
                total=total,
                elapsed_ms=elapsed_ms,
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
            )

        if end < total:
            self._schedule_details_on_demand_job(
                _GF_DETAILS_STAGE_GAP_MS,
                lambda s=end: self._run_children_details_module_batched(
                    element_id,
                    generation,
                    module,
                    start=s,
                ),
            )
            return

        fields = editor_field_visibility(m.element_type or "unknown")
        self._save_details_module_cache(m, module, fields)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        total_elapsed_ms = self._since_details_request_ms()
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )

    def _save_details_module_cache(
        self,
        m: MergedPageElement,
        module: str,
        fields: EditorFieldVisibility,
    ) -> None:
        existing = self._section_visual_cache.get(m.element_id)
        preview_key = self._preview_key_for_element(m)
        layer_nav_titles: tuple[str, ...] = ()
        layer_nav_visible = False
        if module == "layer_nav":
            if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                layer_nav_visible = True
                items = self._selected_layer_items(m)
                layer_nav_titles = tuple(title for _, _, title in items)
            elif existing is not None:
                layer_nav_visible = existing.layer_nav_visible
                layer_nav_titles = existing.layer_nav_titles
        elif existing is not None:
            layer_nav_visible = existing.layer_nav_visible
            layer_nav_titles = existing.layer_nav_titles

        effective_preview_key = preview_key if module == "preview" else (
            existing.preview_key if existing is not None else ""
        )
        subtitle = (
            self._editor_section_subtitle.cget("text")
            if self._editor_section_subtitle is not None
            else editor_title_for_element(m)
        )
        page_context_summary = tuple(self._page_context_shell_summary_lines(m))
        if existing is not None and module != "page_context":
            page_context_summary = existing.page_context_summary

        self._section_visual_cache[m.element_id] = SectionVisualCacheEntry(
            element_type=m.element_type or "unknown",
            status=m.status or "ok",
            has_draft_patch=m.has_draft_patch,
            title=m.title,
            text=m.text,
            alt=m.alt,
            image_ref=m.image_ref,
            notes=m.notes,
            visible=m.visible,
            subtitle_text=subtitle,
            page_context_summary=page_context_summary,
            fields_title=fields.title,
            fields_text=fields.text,
            fields_alt=fields.alt,
            fields_image_ref=fields.image_ref,
            fields_notes=fields.notes,
            fields_visible=fields.visible,
            fields_children=fields.children,
            fields_page_context=fields.page_context,
            media_details_built=bool(existing and existing.media_details_built),
            preview_key=effective_preview_key or (existing.preview_key if existing else ""),
            layer_nav_visible=layer_nav_visible,
            layer_nav_titles=layer_nav_titles,
            details_cache_preview=(
                module == "preview" or bool(existing and existing.details_cache_preview)
            ),
            details_cache_page_context=(
                module == "page_context"
                or bool(existing and existing.details_cache_page_context)
            ),
            details_cache_layer_nav=(
                module == "layer_nav" or bool(existing and existing.details_cache_layer_nav)
            ),
            details_cache_children=(
                module == "children" or bool(existing and existing.details_cache_children)
            ),
        )
        log_event(
            "studio.gicleeframe.selection.visual_cache_saved",
            element_id=m.element_id,
            element_type=m.element_type,
            media_details_built=False,
            details_module=module,
            minimal_only=False,
            generation=self._selection_generation,
        )

    def _apply_details_cache_hit(
        self,
        m: MergedPageElement,
        entry: SectionVisualCacheEntry,
        generation: int,
    ) -> None:
        """Legacy — full details cache apply; not used by shell CTA."""
        if not self._details_stage_still_valid(m.element_id, generation):
            return
        started = time.perf_counter()
        fields = self._fields_from_cache_entry(entry)
        stale_refresh = self._editor_has_ready_content

        self._hide_details_on_demand_block()
        self._hide_details_shell()
        self._show_heavy_editor_modules()
        self._apply_cached_media_details(entry)
        if fields.page_context:
            self._apply_cached_page_context_summary(entry)
        self._set_row_visible(self._children_overview_row, fields.children)
        if fields.children:
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)

        self._details_on_demand_expanded = True
        self._hide_editor_refresh_status()
        self._mark_editor_content_ready(m)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        details_cta_ms = self._since_details_cta_ms()
        log_event(
            "studio.gicleeframe.details_on_demand.ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
            shell_only=False,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.all_done",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )

    def _apply_heavy_details_on_demand(self, m: MergedPageElement) -> None:
        """Legacy internal — staged pipeline; not started from shell CTA."""
        self._begin_details_on_demand_stages(m.element_id, self._details_on_demand_generation)

    def _details_stage_still_valid(self, element_id: str, generation: int) -> bool:
        if generation != self._details_on_demand_generation:
            return False
        if self._selected_id != element_id:
            return False
        if self._details_on_demand_active_element_id != element_id:
            return False
        if not self.winfo_exists():
            return False
        return True

    def _details_on_demand_stages_for(self, m: MergedPageElement) -> list[str]:
        fields = editor_field_visibility(m.element_type or "unknown")
        stages: list[str] = ["summary", "preview"]
        if fields.page_context:
            stages.append("page_context")
        stages.append("layer_nav")
        if fields.children:
            stages.append("children")
        return stages

    def _begin_details_on_demand_stages(self, element_id: str, generation: int) -> None:
        """Legacy internal — full auto chain; suppressed after PERF-F.5 shell CTA."""
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        self._show_heavy_editor_modules()
        stages = self._details_on_demand_stages_for(m)
        self._schedule_next_details_stage(element_id, generation, stages, 0)

    def _schedule_next_details_stage(
        self,
        element_id: str,
        generation: int,
        stages: list[str],
        index: int,
    ) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        if index >= len(stages):
            self._schedule_details_on_demand_job(
                0,
                lambda eid=element_id, gen=generation: self._finalize_details_on_demand(
                    eid,
                    gen,
                ),
            )
            return
        stage = stages[index]
        delay_ms = 0 if index == 0 else _GF_DETAILS_STAGE_GAP_MS
        merged = self._merged_by_id.get(element_id)
        log_event(
            "studio.gicleeframe.details_on_demand.stage_scheduled",
            stage=stage,
            element_id=element_id,
            element_type=merged.element_type if merged is not None else "",
            generation=generation,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_details_on_demand_job(
            delay_ms,
            lambda eid=element_id, gen=generation, stg=stage, idx=index, stgs=stages: (
                self._execute_details_on_demand_stage(eid, gen, stgs, idx, stg)
            ),
        )

    def _execute_details_on_demand_stage(
        self,
        element_id: str,
        generation: int,
        stages: list[str],
        index: int,
        stage: str,
    ) -> None:
        """Legacy internal — monolithic staged pipeline stage executor."""
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        log_event(
            "studio.gicleeframe.details_on_demand.stage_start",
            stage=stage,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            since_request_ms=self._since_details_request_ms(),
        )
        stale_refresh = self._editor_has_ready_content
        fields = editor_field_visibility(m.element_type or "unknown")

        if stage == "summary":
            pass
        elif stage == "preview":
            self._update_section_preview(m, stale_refresh=stale_refresh)
            self._update_details_module_status("preview", "")
        elif stage == "page_context":
            if fields.page_context:
                self._fill_page_context(m, show=True)
        elif stage == "layer_nav":
            self._update_layer_nav(m, stale_refresh=stale_refresh)
            self._update_details_module_status("layer_nav", "")
        elif stage == "children":
            self._set_row_visible(self._children_overview_row, True)
            self._run_children_details_stage_batched(
                m,
                generation,
                stale_refresh=stale_refresh,
                start=0,
                stages=stages,
                stage_index=index,
            )
            return

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_on_demand.stage_done",
            stage=stage,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_next_details_stage(element_id, generation, stages, index + 1)

    def _run_children_details_stage_batched(
        self,
        m: MergedPageElement,
        generation: int,
        *,
        stale_refresh: bool,
        start: int,
        stages: list[str],
        stage_index: int,
    ) -> None:
        element_id = m.element_id
        if not self._details_stage_still_valid(element_id, generation):
            return
        parent_row = self._tree_row_for_element(element_id)
        children = parent_row.children if parent_row is not None else ()
        total = len(children)
        end = min(start + _GF_DETAILS_CHILDREN_BATCH_SIZE, total)
        started = time.perf_counter()

        self._fill_children_overview_buttons_range(
            m,
            start,
            end,
            stale_refresh=stale_refresh and start == 0,
        )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if total > 0 and (end < total or elapsed_ms > 80):
            log_event(
                "studio.gicleeframe.details_on_demand.stage_batch",
                stage="children",
                start=start,
                end=end,
                total=total,
                elapsed_ms=elapsed_ms,
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
            )

        if end < total:
            self._schedule_details_on_demand_job(
                _GF_DETAILS_STAGE_GAP_MS,
                lambda s=end: self._run_children_details_stage_batched(
                    m,
                    generation,
                    stale_refresh=stale_refresh,
                    start=s,
                    stages=stages,
                    stage_index=stage_index,
                ),
            )
            return

        self._update_details_module_status("children", "")
        log_event(
            "studio.gicleeframe.details_on_demand.stage_done",
            stage="children",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_next_details_stage(element_id, generation, stages, stage_index + 1)

    def _finalize_details_on_demand(self, element_id: str, generation: int) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        fields = editor_field_visibility(m.element_type or "unknown")

        self._details_on_demand_expanded = True
        self._hide_details_on_demand_block()
        self._hide_details_shell()
        self._hide_media_details_stable_shell()
        self._hide_editor_refresh_status()
        self._save_section_visual_cache(m, fields, media_details_built=True)
        self._mark_editor_content_ready(m)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        total_elapsed_ms = self._since_details_request_ms()
        details_cta_ms = self._since_details_cta_ms()
        log_event(
            "studio.gicleeframe.details_on_demand.all_done",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )

    def _ensure_details_shell_built(self) -> None:
        parent = self._identity_card or self._edit_panel
        if self._details_container_built or parent is None:
            return
        frame = ctk.CTkFrame(
            parent,
            fg_color=_GF_FIELD,
            corner_radius=10,
            border_width=1,
            border_color=_GF_BORDER,
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        self._details_container_title_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_SHELL_TITLE,
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        self._details_container_title_label.pack(fill="x", pady=(0, 4))
        self._details_container_subtext_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_SHELL_SUBTEXT,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._details_container_subtext_label.pack(fill="x", pady=(0, 10))
        modules_parent = ctk.CTkFrame(inner, fg_color="transparent")
        modules_parent.pack(fill="x")
        module_specs = (
            ("preview", _GF_DETAILS_MODULE_PREVIEW_TITLE, _GF_DETAILS_MODULE_PREVIEW_BUTTON),
            (
                "page_context",
                _GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE,
                _GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON,
            ),
            ("layer_nav", _GF_DETAILS_MODULE_LAYER_NAV_TITLE, _GF_DETAILS_MODULE_LAYER_NAV_BUTTON),
            ("children", _GF_DETAILS_MODULE_CHILDREN_TITLE, _GF_DETAILS_MODULE_CHILDREN_BUTTON),
        )
        for module_key, title, button_text in module_specs:
            # Dwie linie: tytuł + status na górze, przycisk na całą szerokość pod spodem —
            # przy wąskiej kolumnie nic nie jest wyciskane ani obcinane.
            row = ctk.CTkFrame(modules_parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 8))
            head = ctk.CTkFrame(row, fg_color="transparent")
            head.pack(fill="x")
            ctk.CTkLabel(
                head,
                text=title,
                font=theme.get_font(9, "bold"),
                text_color=theme.TextPrimary,
                anchor="w",
            ).pack(side="left")
            status = ctk.CTkLabel(
                head,
                text=_GF_DETAILS_MODULE_IDLE_STATUS,
                font=theme.get_font(9),
                text_color=theme.TextMuted,
                anchor="e",
            )
            status.pack(side="right")
            button = ctk.CTkButton(
                row,
                text=button_text,
                height=24,
                width=120,
                fg_color=_GF_CARD_SOFT,
                hover_color=_GF_FIELD_HOVER,
                text_color=theme.TextPrimary,
                command=lambda mod=module_key: self._on_details_module_clicked(mod),
            )
            button.pack(fill="x", pady=(3, 0))
            self._details_module_rows[module_key] = row
            self._details_module_buttons[module_key] = button
            self._details_module_status_labels[module_key] = status
        self._details_container_frame = frame
        self._details_container_built = True

    def _show_details_shell(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        self._ensure_details_shell_built()
        if self._details_container_frame is None:
            return
        is_media = m.element_type == "media_section"
        fields = editor_field_visibility(m.element_type or "unknown")
        if self._details_container_title_label is not None:
            self._details_container_title_label.configure(text=_GF_DETAILS_SHELL_TITLE)
        if self._details_container_subtext_label is not None:
            subtext = _GF_MEDIA_DETAILS_SHELL_SUBTEXT if is_media else _GF_DETAILS_SHELL_SUBTEXT
            self._details_container_subtext_label.configure(text=subtext)
        cache_entry = self._section_visual_cache.get(m.element_id)
        module_visibility = {
            "preview": True,
            "page_context": fields.page_context,
            "layer_nav": True,
            "children": fields.children,
        }
        for module_key, row in self._details_module_rows.items():
            visible = module_visibility.get(module_key, False)
            if visible:
                try:
                    row.pack(fill="x", pady=(0, 8))
                except tk.TclError:
                    pass
                cached = (
                    cache_entry is not None
                    and self._details_module_cache_hit(cache_entry, module_key)
                )
                status_text = _GF_DETAILS_MODULE_LOADED_STATUS if cached else _GF_DETAILS_MODULE_IDLE_STATUS
                self._update_details_module_status(module_key, status_text)
            else:
                try:
                    row.pack_forget()
                except tk.TclError:
                    pass
        pack_before = None
        if self._section_preview_card is not None:
            pack_before = self._section_preview_card
        elif self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            pack_before = self._layer_nav_frame
        try:
            if pack_before is not None:
                self._details_container_frame.pack(
                    fill="x",
                    padx=_CARD_PAD_X,
                    pady=(0, 8),
                    before=pack_before,
                )
            else:
                self._details_container_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
        except tk.TclError:
            try:
                self._details_container_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
            except tk.TclError:
                pass

    def _hide_details_shell(self) -> None:
        if self._details_container_frame is None:
            return
        try:
            self._details_container_frame.pack_forget()
        except tk.TclError:
            pass

    def _hide_details_container(self) -> None:
        """Legacy alias — details shell hide."""
        self._hide_details_shell()

    def _update_details_module_status(self, module_key: str, text: str) -> None:
        label = self._details_module_status_labels.get(module_key)
        if label is None:
            return
        try:
            display = text if text else _GF_DETAILS_MODULE_LOADED_STATUS
            label.configure(text=display)
        except tk.TclError:
            pass

    def _cancel_details_on_demand_jobs(self) -> int:
        cancelled = len(self._details_on_demand_after_ids)
        while self._details_on_demand_after_ids:
            after_id = self._details_on_demand_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        return cancelled

    def _schedule_details_on_demand_job(self, delay_ms: int, callback: Callable[[], None]) -> None:
        after_id = self.after(delay_ms, callback)
        self._details_on_demand_after_ids.append(after_id)

    def _save_section_visual_cache(
        self,
        m: MergedPageElement,
        fields: EditorFieldVisibility,
        *,
        media_details_built: bool,
    ) -> None:
        layer_nav_titles: tuple[str, ...] = ()
        layer_nav_visible = False
        preview_key = self._preview_key_for_element(m)
        subtitle = (
            self._editor_section_subtitle.cget("text")
            if self._editor_section_subtitle is not None
            else editor_title_for_element(m)
        )
        existing = self._section_visual_cache.get(m.element_id)
        if media_details_built:
            if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                layer_nav_visible = True
                items = self._selected_layer_items(m)
                layer_nav_titles = tuple(title for _, _, title in items)
            else:
                layer_nav_visible = existing.layer_nav_visible if existing else False
                layer_nav_titles = existing.layer_nav_titles if existing else ()
            effective_preview_key = preview_key
        else:
            layer_nav_visible = existing.layer_nav_visible if existing else False
            layer_nav_titles = existing.layer_nav_titles if existing else ()
            effective_preview_key = existing.preview_key if existing else ""
        effective_media_details = media_details_built or bool(
            existing and existing.media_details_built
        )
        if media_details_built:
            cache_preview = True
            cache_page_context = fields.page_context
            cache_layer_nav = True
            cache_children = fields.children
        elif existing is not None:
            cache_preview = existing.details_cache_preview
            cache_page_context = existing.details_cache_page_context
            cache_layer_nav = existing.details_cache_layer_nav
            cache_children = existing.details_cache_children
        else:
            cache_preview = False
            cache_page_context = False
            cache_layer_nav = False
            cache_children = False
        self._section_visual_cache[m.element_id] = SectionVisualCacheEntry(
            element_type=m.element_type or "unknown",
            status=m.status or "ok",
            has_draft_patch=m.has_draft_patch,
            title=m.title,
            text=m.text,
            alt=m.alt,
            image_ref=m.image_ref,
            notes=m.notes,
            visible=m.visible,
            subtitle_text=subtitle,
            page_context_summary=tuple(self._page_context_shell_summary_lines(m)),
            fields_title=fields.title,
            fields_text=fields.text,
            fields_alt=fields.alt,
            fields_image_ref=fields.image_ref,
            fields_notes=fields.notes,
            fields_visible=fields.visible,
            fields_children=fields.children,
            fields_page_context=fields.page_context,
            media_details_built=effective_media_details,
            preview_key=effective_preview_key,
            layer_nav_visible=layer_nav_visible,
            layer_nav_titles=layer_nav_titles,
            details_cache_preview=cache_preview,
            details_cache_page_context=cache_page_context,
            details_cache_layer_nav=cache_layer_nav,
            details_cache_children=cache_children,
        )
        log_event(
            "studio.gicleeframe.selection.visual_cache_saved",
            element_id=m.element_id,
            element_type=m.element_type,
            media_details_built=effective_media_details,
            minimal_only=not media_details_built,
            generation=self._selection_generation,
        )

    def _mark_editor_stable_shell_ready(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool = False,
    ) -> None:
        if m.element_id in self._editor_stable_shell_logged_for and not from_cache:
            return
        if not from_cache:
            self._editor_stable_shell_logged_for.add(m.element_id)
        log_event(
            "studio.gicleeframe.editor.stable_shell_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            from_cache=from_cache,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _maybe_log_layout_shift_guard(
        self,
        m: MergedPageElement,
        *,
        phase: str,
        rows_visible: int,
    ) -> None:
        log_event(
            "studio.gicleeframe.editor.layout_shift_guard",
            element_id=m.element_id,
            element_type=m.element_type,
            phase=phase,
            rows_visible=rows_visible,
            generation=self._selection_generation,
        )

    def _show_editor_selection_stable_shell_state(
        self,
        m: MergedPageElement,
        *,
        from_cache: bool = False,
    ) -> None:
        if self._editor_status_dot:
            if from_cache:
                dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
            else:
                dot_color = _GF_GOLD_SOFT
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=editor_title_for_element(m))

        log_event(
            "studio.gicleeframe.editor.selection_stable_shell",
            element_id=m.element_id,
            element_type=m.element_type,
            from_cache=from_cache,
        )

    def _show_editor_selection_pending_state(self, m: MergedPageElement) -> None:
        self._show_editor_selection_stable_shell_state(m, from_cache=False)

        log_event(
            "studio.gicleeframe.editor.selection_pending",
            element_id=m.element_id,
            element_type=m.element_type,
        )

    def _mark_editor_shell_ready_after_click(
        self,
        m: MergedPageElement,
        *,
        page_context_shell: bool,
    ) -> None:
        if self._editor_section_subtitle:
            title = editor_title_for_element(m)
            self._editor_section_subtitle.configure(text=title)
        log_event(
            "studio.gicleeframe.editor.shell_ready_after_click",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            page_context_shell=page_context_shell,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _schedule_atomic_swap_populate(self, element_id: str, generation: int) -> None:
        self.after_idle(
            lambda eid=element_id, gen=generation: self._run_atomic_swap_populate(eid, gen),
        )

    def _run_atomic_swap_populate(self, element_id: str, generation: int) -> None:
        if generation != self._selection_generation:
            log_event(
                "studio.gicleeframe.selection.atomic_swap.stale",
                element_id=element_id,
                generation=generation,
                current_generation=self._selection_generation,
            )
            return
        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            return
        log_event(
            "studio.gicleeframe.selection.atomic_swap.ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )
        had_stale_content = self._editor_has_ready_content
        self._atomic_swap_suppress_visible = had_stale_content
        self._atomic_swap_deferred_row_visibility.clear()
        populate_started = time.perf_counter()
        try:
            with span(
                "studio.gicleeframe.selection.atomic_swap.populate",
                element_id=element_id,
                element_type=m.element_type,
            ):
                self._populate_editor(m, atomic_swap=True)
            if had_stale_content:
                self._flush_atomic_swap_row_visibility()
        finally:
            self._atomic_swap_suppress_visible = False
            self._atomic_swap_deferred_row_visibility.clear()
        if generation == self._selection_generation and self._selected_id == element_id:
            populate_elapsed_ms = round((time.perf_counter() - populate_started) * 1000, 2)
            log_event(
                "studio.gicleeframe.selection.atomic_swap.applied",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=populate_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.selection.populate_done",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=populate_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.selection.populate.done",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=populate_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            self._hide_editor_refresh_status()

    def _flush_atomic_swap_row_visibility(self) -> None:
        deferred = list(self._atomic_swap_deferred_row_visibility)
        self._atomic_swap_deferred_row_visibility.clear()
        self._atomic_swap_suppress_visible = False
        for row, visible in deferred:
            self._set_row_visible(row, visible)

    def _populate_editor_deferred(self, element_id: str, generation: int) -> None:
        queue_latency_ms = self._queue_latency_since_ms(self._selection_populate_scheduled_mono)
        if generation != self._selection_generation:
            log_event(
                "studio.gicleeframe.populate_editor.deferred_stale",
                element_id=element_id,
                generation=generation,
                current_generation=self._selection_generation,
            )
            return

        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            log_event(
                "studio.gicleeframe.populate_editor.deferred_missing_or_stale",
                element_id=element_id,
                selected_id=self._selected_id or "",
            )
            return

        log_event(
            "studio.gicleeframe.selection.populate_enter",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            queue_latency_ms=queue_latency_ms,
            since_click_ms=self._since_selection_click_ms(),
        )
        log_event(
            "studio.gicleeframe.selection.populate.start",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
            queue_latency_ms=queue_latency_ms,
        )
        populate_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._populate_editor(
                m,
                visual_cache_refresh=self._selection_visual_cache_applied,
            )

        if generation == self._selection_generation and self._selected_id == element_id:
            populate_elapsed_ms = round((time.perf_counter() - populate_started) * 1000, 2)
            log_event(
                "studio.gicleeframe.selection.populate_done",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=populate_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.selection.populate.done",
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=populate_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )

    def _should_defer_editor_detail_populate(
        self,
        m: MergedPageElement,
        fields: object,
    ) -> bool:
        _ = (m, fields)
        return True

    def _merged_for_selection_generation(
        self,
        element_id: str,
        generation: int,
        *,
        event_prefix: str,
    ) -> MergedPageElement | None:
        if generation != self._selection_generation:
            log_event(
                f"{event_prefix}.stale",
                element_id=element_id,
                generation=generation,
                current_generation=self._selection_generation,
            )
            return None
        if self._selected_id != element_id:
            log_event(
                f"{event_prefix}.stale_selected",
                element_id=element_id,
                selected_id=self._selected_id or "",
            )
            return None
        m = self._merged_by_id.get(element_id)
        if m is None:
            log_event(f"{event_prefix}.missing", element_id=element_id)
            return None
        return m

    def _populate_editor_preview_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.preview_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.preview_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_section_preview(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("preview", element_type=m.element_type, started=segment_started)

    def _populate_editor_layer_nav_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.layer_nav_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.layer_nav_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_layer_nav(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("layer_nav", element_type=m.element_type, started=segment_started)

    def _populate_editor_children_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.children_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.children_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._fill_children_overview_buttons(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("children", element_type=m.element_type, started=segment_started)

    def _page_context_shell_summary_lines(
        self,
        m: MergedPageElement,
    ) -> list[tuple[str, str]]:
        etype = m.element_type or "unknown"
        lines: list[tuple[str, str]] = [
            ("Typ sekcji", etype),
            ("Status", m.status or "ok"),
        ]
        settings_count = len(m.page_settings)
        if settings_count:
            layout = "divider" if m.element_type == "divider" else "flat"
            lines.append(("Ustawienia", f"{settings_count} · układ {layout}"))
        return lines

    def _show_page_context_shell_state(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._page_context_frame is None or self._page_context_inner is None:
            return
        self._hide_page_context_rows()
        self._clear_page_context_loading_label()
        self._page_context_frame.pack(**self._page_context_pack_kwargs())

        self._get_or_create_readonly_card()
        self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        for label, value in self._page_context_shell_summary_lines(m):
            row_key = f"shell_summary:{label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=label,
                kind="shell_summary",
            )
            value_widget.configure(text=value)
            self._show_page_context_row(row_key, fill="x", pady=2)

        if not self._selection_visual_cache_applied:
            pass
        else:
            self._clear_page_context_loading_label()
        self._page_context_shell_shown_generation = self._selection_generation
        log_event(
            "studio.gicleeframe.page_context.shell_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _schedule_media_deferred_details(
        self,
        m: MergedPageElement,
        generation: int,
    ) -> None:
        if generation != self._selection_generation:
            return
        element_id = m.element_id
        if self._selection_visual_cache_applied:
            return
        started = time.perf_counter()
        log_event(
            "studio.gicleeframe.media_deferred.scheduled",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            jobs="preview,layer_nav,children",
            since_click_ms=self._since_selection_click_ms(),
        )
        self._schedule_selection_job(
            _GF_MEDIA_PREVIEW_AFTER_SHELL_MS,
            lambda eid=element_id, gen=generation, mono=started: self._populate_editor_media_details_batch(
                eid,
                gen,
                started_mono=mono,
            ),
        )
        if self._media_deferred_done_after_id is not None:
            try:
                self.after_cancel(self._media_deferred_done_after_id)
            except tk.TclError:
                pass
            self._media_deferred_done_after_id = None

    def _populate_editor_media_details_batch(
        self,
        element_id: str,
        generation: int,
        *,
        started_mono: float,
    ) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.media_details_batch",
        )
        if m is None:
            return
        stale_refresh = self._editor_has_ready_content
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.media_details_batch",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_section_preview(m, stale_refresh=stale_refresh)
            self._update_layer_nav(m, stale_refresh=stale_refresh)
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)
        self._hide_media_details_stable_shell()
        self._hide_editor_refresh_status()
        fields = editor_field_visibility(m.element_type)
        self._save_section_visual_cache(m, fields, media_details_built=True)
        self._mark_editor_content_ready(m)
        log_event(
            "studio.gicleeframe.media_deferred.done",
            generation=generation,
            elapsed_ms=round((time.perf_counter() - started_mono) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )
        self._log_perf_e_update_done(
            "media_details_batch",
            element_type=m.element_type,
            started=segment_started,
        )

    def _schedule_or_fill_page_context(
        self,
        m: MergedPageElement,
        fields: object,
        etype: str,
    ) -> None:
        readonly_rows = editor_context_rows(m) if fields.page_context else ()
        if (
            fields.page_context
            and _progressive_page_context_enabled()
            and (readonly_rows or m.page_settings)
        ):
            if self._page_context_shell_shown_generation != self._selection_generation:
                self._show_page_context_shell_state(m)
            log_event(
                "studio.gicleeframe.page_context.deferred",
                element_id=m.element_id,
                element_type=etype,
            )
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_STABLE_DEFER_MS,
                lambda el=m, gen=self._selection_generation: self._populate_page_context_progressive_stable(
                    el, gen
                ),
            )
        elif fields.page_context:
            self._fill_page_context(m, show=True)
        else:
            self._fill_page_context(m, show=False)

    def _populate_editor(
        self,
        m: MergedPageElement,
        *,
        visual_cache_refresh: bool = False,
        atomic_swap: bool = False,
    ) -> None:
        etype = m.element_type
        fields = editor_field_visibility(etype)
        readonly = etype == "section_legacy"
        cache_entry = self._section_visual_cache.get(m.element_id)
        generation = self._selection_generation
        _ = (visual_cache_refresh, atomic_swap)

        segment_started = time.perf_counter()
        self._ensure_editor_identity_built()
        log_event(
            "studio.gicleeframe.selection.editor.ensure_identity",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        segment_started = time.perf_counter()
        self._ensure_minimal_editor_rows_for_fields(fields)
        log_event(
            "studio.gicleeframe.selection.editor.ensure_rows",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

        if self._editor_status_dot:
            dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
            self._editor_status_dot.configure(text_color=dot_color)
        if self._editor_section_subtitle:
            self._editor_section_subtitle.configure(text=self._selected_section_label())

        page_context_from_cache = (
            cache_entry is not None
            and cache_entry.fields_page_context
            and bool(cache_entry.page_context_summary)
        )
        if page_context_from_cache and cache_entry is not None:
            self._apply_cached_page_context_summary(cache_entry)
        elif fields.page_context:
            self._show_page_context_shell_state(m)
        elif self._page_context_frame is not None:
            self._page_context_frame.pack_forget()

        with span(
            "studio.gicleeframe.populate_editor",
            element_type=etype,
            element_id=m.element_id,
            defer_details=True,
        ):
            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.populate_editor.preview_deferred_requested",
                element_id=m.element_id,
                element_type=etype,
                scheduled_from="details_on_demand",
            )
            log_event(
                "studio.gicleeframe.selection.editor.preview",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

            segment_started = time.perf_counter()
            with span("studio.gicleeframe.populate_editor.rows_visibility", element_type=etype):
                if self._legacy_msg_label:
                    if readonly:
                        self._legacy_msg_label.configure(text=_LEGACY_READONLY_MSG)
                        self._legacy_msg_label.pack(fill="x", padx=12, pady=(0, 4))
                    else:
                        self._legacy_msg_label.pack_forget()

                self._set_row_visible(self._title_row, fields.title)
                self._set_row_visible(self._text_row, fields.text)
                self._set_row_visible(self._alt_row, fields.alt)
                self._set_row_visible(self._image_ref_row, fields.image_ref)
                self._set_row_visible(self._notes_row, fields.notes)

                if etype == "image" and self._notes_row is not None:
                    self._notes_row.pack_forget()
                    self._notes_row.pack(fill="x", pady=(8, 8))

                self._set_row_visible(self._visible_row, fields.visible)
                self._set_row_visible(self._children_overview_row, False)
            log_event(
                "studio.gicleeframe.selection.editor.rows_visibility",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
            )

            segment_started = time.perf_counter()
            with span("studio.gicleeframe.populate_editor.fields", element_type=etype):
                if self._title_entry:
                    self._set_entry(self._title_entry, m.title, readonly=readonly or not fields.title)
                if self._text_box:
                    self._set_textbox(self._text_box, m.text, readonly=readonly or not fields.text)
                if self._alt_entry:
                    self._set_entry(self._alt_entry, m.alt, readonly=readonly or not fields.alt)
                if self._image_ref_entry:
                    self._set_entry(self._image_ref_entry, m.image_ref, readonly=True)
                if self._notes_box:
                    self._set_textbox(self._notes_box, m.notes, readonly=readonly or not fields.notes)
                if self._visible_var is not None and fields.visible:
                    self._visible_var.set(m.visible)
            log_event(
                "studio.gicleeframe.selection.editor.fields",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
            )

            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.populate_editor.details_deferred",
                element_id=m.element_id,
                element_type=etype,
                scheduled_from="details_on_demand",
            )
            log_event(
                "studio.gicleeframe.selection.editor.layer_nav",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

            segment_started = time.perf_counter()
            log_event(
                "studio.gicleeframe.selection.editor.children",
                element_id=m.element_id,
                element_type=etype,
                generation=generation,
                elapsed_ms=round((time.perf_counter() - segment_started) * 1000, 2),
                since_click_ms=self._since_selection_click_ms(),
                deferred=True,
            )

        page_context_shell = bool(
            fields.page_context
            and (
                editor_context_rows(m)
                or m.page_settings
            )
        )
        log_event(
            "studio.gicleeframe.selection.editor.page_context_schedule_or_fill",
            element_id=m.element_id,
            element_type=etype,
            generation=generation,
            elapsed_ms=0.0,
            since_click_ms=self._since_selection_click_ms(),
            shell_ready=page_context_shell,
            scheduled_early=False,
        )

        self._mark_editor_shell_ready_after_click(
            m,
            page_context_shell=page_context_shell,
        )
        self._mark_editor_stable_shell_ready(m)
        self._hide_heavy_editor_modules()
        self._hide_media_details_stable_shell()
        self._show_details_on_demand_block(m)
        self._hide_editor_refresh_status()

        visible_rows = sum(
            1
            for flag in (
                fields.title,
                fields.text,
                fields.alt,
                fields.image_ref,
                fields.notes,
                fields.page_context,
            )
            if flag
        )
        self._maybe_log_layout_shift_guard(m, phase="populate_done", rows_visible=visible_rows)
        self._save_section_visual_cache(m, fields, media_details_built=False)
        self._mark_editor_content_ready(m)
        self._log_minimal_editor_ready(m, from_cache=False)

        if not self._visual_bootstrap_complete:
            log_event(
                "studio.gicleeframe.visual.first_selection_done",
                since_enter_ms=self._since_visual_enter_ms(),
                element_type=etype,
                element_id=m.element_id,
            )

    def _parent_row_for_element(self, element_id: str | None):
        if not element_id:
            return None
        for row in self._section_tree_rows_cache:
            if row.element_id == element_id:
                return row
            for child in row.children:
                if child.element_id == element_id:
                    return row
        return None

    def _tree_row_for_element(self, element_id: str) -> SectionTreeRow | None:
        return next(
            (row for row in self._section_tree_rows_cache if row.element_id == element_id),
            None,
        )

    def _preview_meta_lines(self, m: MergedPageElement) -> list[str]:
        lines: list[str] = []
        element_type = m.element_type or "unknown"
        lines.append(f"Typ elementu: {element_type}")
        if m.section_key:
            lines.append(f"Klucz sekcji: {m.section_key}")
        if m.element_id:
            lines.append(f"ID: {m.element_id}")
        tree_row = self._tree_row_for_element(m.element_id)
        if tree_row is not None:
            child_count = len(tree_row.children)
            lines.append(f"Elementy podrzędne: {child_count}")
        settings_count = len(m.page_settings) or len(m.page_fields)
        if settings_count:
            lines.append(f"Ustawienia strony: {settings_count}")
        if m.label:
            lines.append(f"Etykieta: {_ellipsize(m.label, 40)}")
        if m.title and m.title != m.label:
            lines.append(f"Tytuł: {_ellipsize(m.title, 40)}")
        if m.text:
            lines.append(f"Tekst: {_ellipsize(m.text, 60)}")
        if m.notes:
            lines.append(f"Notatka: {_ellipsize(m.notes, 80)}")
        return lines

    def _apply_metadata_preview_content(
        self,
        preview_key: str,
        m: MergedPageElement,
        *,
        heading: str,
        subtitle: str,
        fallback: bool = False,
    ) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        meta_lines = self._preview_meta_lines(m)
        meta_text = "\n".join(meta_lines) if meta_lines else "Brak dodatkowych metadanych."
        if fallback:
            meta_text = (
                "Brak szczegółowego podglądu dla tego typu sekcji.\n\n"
                f"{meta_text}"
            )
            log_event(
                "studio.gicleeframe.preview.fallback_used",
                element_type=m.element_type,
                element_id=m.element_id,
                preview_key=preview_key,
            )
        for widget_key, text in (
            ("heading_label", heading),
            ("subtitle_label", subtitle),
            ("meta_label", meta_text),
        ):
            widget = widgets.get(widget_key)
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=text)

    def _build_section_metadata_preview_structure(
        self,
        frame: ctk.CTkFrame,
        preview_key: str,
        *,
        hint_text: str,
    ) -> None:
        layout = ctk.CTkFrame(frame, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=14, pady=12)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)

        hint_box = ctk.CTkFrame(
            layout,
            fg_color=_GF_CARD_SOFT,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
            width=96,
        )
        hint_box.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        hint_box.grid_propagate(False)

        hint_label = self._get_or_create_preview_label(
            preview_key,
            "hint_label",
            hint_box,
            label=hint_text,
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
        )
        hint_label.place(relx=0.5, rely=0.5, anchor="center")

        meta = ctk.CTkFrame(layout, fg_color="transparent")
        meta.grid(row=0, column=1, sticky="nsew")

        self._get_or_create_preview_label(
            preview_key,
            "heading_label",
            meta,
            label="",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
        ).pack(fill="x", pady=(4, 4))

        self._get_or_create_preview_label(
            preview_key,
            "subtitle_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_GOLD_SOFT,
            wraplength=360,
        ).pack(fill="x", pady=(0, 6))

        self._get_or_create_preview_label(
            preview_key,
            "meta_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            justify="left",
            wraplength=360,
        ).pack(fill="x")

    def _selected_layer_items(self, m: MergedPageElement) -> list[tuple[str, str, str]]:
        parent = self._parent_row_for_element(m.element_id)
        if parent is None or not parent.children:
            return []

        items: list[tuple[str, str, str]] = [
            (parent.element_id, "SEKCJA", parent.display_title),
        ]
        for child in parent.children:
            label = editor_title_for_element(child.merged).replace("Edytor: ", "").upper()
            items.append((child.element_id, label, child.child_label))
        return items

    def _layer_nav_tile_signature(
        self,
        *,
        kind: str,
        title: str,
        meta: str,
        element_id: str | None,
        active: bool,
    ) -> tuple[Any, ...]:
        return (
            kind or "",
            title or "",
            meta or "",
            element_id or "",
            bool(active),
        )

    def _sync_layer_nav_visibility(self, desired_keys: list[str]) -> None:
        desired_set = set(desired_keys)
        previous_set = set(self._layer_nav_visible_order)
        for key in previous_set - desired_set:
            frame = self._layer_nav_tile_cache.get(key)
            if frame is None:
                continue
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
            self._layer_nav_visible_keys.discard(key)
        self._layer_nav_visible_order = tuple(desired_keys)

    def _hide_layer_nav_tiles(self) -> None:
        for key, frame in self._layer_nav_tile_cache.items():
            if not key.startswith("slot:"):
                continue
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
        self._layer_nav_visible_keys = {
            key for key in self._layer_nav_visible_keys if not key.startswith("slot:")
        }

    def _show_layer_nav_tile(self, key: str) -> None:
        if key in self._layer_nav_visible_keys:
            return
        frame = self._layer_nav_tile_cache.get(key)
        if frame is None:
            return
        try:
            frame.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=(0, 4))
            self._layer_nav_visible_keys.add(key)
        except tk.TclError:
            return

    def _get_or_create_layer_nav_header(self) -> ctk.CTkLabel:
        if self._layer_nav_frame is None:
            raise RuntimeError("layer_nav_frame is not initialized")
        if self._layer_nav_header_label is not None:
            return self._layer_nav_header_label
        label = ctk.CTkLabel(
            self._layer_nav_frame,
            text=_LAYER_NAV_TITLE.upper(),
            font=theme.get_font(8, "bold"),
            text_color=_GF_GOLD_SOFT,
            anchor="w",
        )
        self._layer_nav_header_label = label
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key="header:title",
        )
        return label

    def _get_or_create_layer_nav_row(self) -> ctk.CTkFrame:
        if self._layer_nav_frame is None:
            raise RuntimeError("layer_nav_frame is not initialized")
        key = "container:row"
        cached = self._layer_nav_tile_cache.get(key)
        if cached is not None:
            return cached
        row = ctk.CTkFrame(self._layer_nav_frame, fg_color="transparent")
        self._layer_nav_tile_cache[key] = row
        self._layer_nav_row_frame = row
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key=key,
        )
        return row

    def _get_or_create_layer_nav_tile(self, key: str) -> ctk.CTkFrame:
        cached = self._layer_nav_tile_cache.get(key)
        if cached is not None:
            return cached
        row = self._get_or_create_layer_nav_row()
        tile = ctk.CTkFrame(
            row,
            fg_color=_GF_FIELD,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
        )
        kind_label = ctk.CTkLabel(
            tile,
            text="",
            font=theme.get_font(8, "bold"),
            text_color=_GF_MUTED,
            anchor="w",
        )
        kind_label.pack(fill="x", padx=10, pady=(8, 1))
        title_label = ctk.CTkLabel(
            tile,
            text="",
            font=theme.get_font(10, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        title_label.pack(fill="x", padx=10, pady=(0, 8))
        self._layer_nav_tile_cache[key] = tile
        self._layer_nav_meta_widgets[key] = kind_label
        self._layer_nav_title_widgets[key] = title_label
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key=key,
        )
        return tile

    def _update_layer_nav_tile(
        self,
        key: str,
        *,
        kind: str = "",
        title: str,
        meta: str = "",
        element_id: str | None = None,
        active: bool = False,
    ) -> None:
        tile = self._get_or_create_layer_nav_tile(key)
        signature = self._layer_nav_tile_signature(
            kind=kind,
            title=title,
            meta=meta,
            element_id=element_id,
            active=active,
        )
        if self._layer_nav_rendered_signatures.get(key) == signature:
            self._show_layer_nav_tile(key)
            log_event(
                "studio.gicleeframe.layer_nav.tile_skipped",
                key=key,
            )
            return

        previous = self._layer_nav_rendered_signatures.get(key)
        kind_widget = self._layer_nav_meta_widgets.get(key)
        if kind_widget is not None and (
            previous is None or previous[0] != kind or previous[4] != active
        ):
            kind_widget.configure(
                text=kind,
                text_color=_GF_GOLD_SOFT if active else _GF_MUTED,
            )
        title_widget = self._layer_nav_title_widgets.get(key)
        if title_widget is not None and (previous is None or previous[1] != title):
            title_widget.configure(text=_ellipsize(title, 24))
        if previous is None or previous[4] != active:
            try:
                tile.configure(
                    fg_color=_GF_CARD_SOFT if active else _GF_FIELD,
                    border_color=_GF_BORDER_WARM if active else _GF_BORDER,
                )
            except tk.TclError:
                pass

        previous_target = self._layer_nav_bound_targets.get(key)
        if element_id and previous_target != element_id:
            click_handler = lambda _e, eid=element_id: self._select_element(eid)
            try:
                tile.bind("<Button-1>", click_handler)
                for child in tile.winfo_children():
                    child.bind("<Button-1>", click_handler)
            except tk.TclError:
                pass
            self._layer_nav_bound_targets[key] = element_id

        self._layer_nav_rendered_signatures[key] = signature
        self._show_layer_nav_tile(key)
        log_event(
            "studio.gicleeframe.layer_nav.tile_updated",
            key=key,
            active=active,
            has_target=bool(element_id),
        )

    def _update_layer_nav(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        if self._layer_nav_frame is None:
            return

        with span(
            "studio.gicleeframe.populate.layer_nav",
            element_type=m.element_type,
            selected_id=m.element_id,
            cached_tiles=len(self._layer_nav_tile_cache),
        ):
            before_children = len(self._layer_nav_frame.winfo_children())
            items = self._selected_layer_items(m)

            if not items:
                if stale_refresh and self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                    log_event(
                        "studio.gicleeframe.editor.stale_content_kept",
                        element_id=m.element_id,
                        element_type=m.element_type,
                        previous_element_id=self._editor_last_ready_element_id or "",
                        since_click_ms=self._since_selection_click_ms(),
                        region="layer_nav",
                    )
                    return
                self._sync_layer_nav_visibility([])
                self._layer_nav_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.layer_nav.delta",
                    element_type=m.element_type,
                    desired_tiles=0,
                    cached_tiles=len(self._layer_nav_tile_cache),
                    visible_tiles=0,
                    before_children=before_children,
                    after_children=len(self._layer_nav_frame.winfo_children()),
                )
                log_event(
                    "studio.gicleeframe.layer_nav.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._layer_nav_frame.winfo_children()),
                    visible_tiles=0,
                    cached_tiles=len(self._layer_nav_tile_cache),
                )
                log_event(
                    "studio.gicleeframe.layer_nav",
                    element_type=m.element_type,
                    children_before_destroy=before_children,
                    items_built=0,
                )
                return

            if not self._layer_nav_frame.winfo_manager():
                self._layer_nav_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(8, 0))

            header = self._get_or_create_layer_nav_header()
            if "header:title" not in self._layer_nav_visible_keys:
                header.pack(fill="x", pady=(0, 6))
                self._layer_nav_visible_keys.add("header:title")

            row = self._get_or_create_layer_nav_row()
            if "container:row" not in self._layer_nav_visible_keys:
                row.pack(fill="x")
                self._layer_nav_visible_keys.add("container:row")

            desired_keys: list[str] = []
            for index, (element_id, kind, title) in enumerate(items):
                slot_key = f"slot:{index}"
                desired_keys.append(slot_key)
                self._update_layer_nav_tile(
                    slot_key,
                    kind=kind,
                    title=title,
                    element_id=element_id,
                    active=element_id == self._selected_id,
                )

            self._sync_layer_nav_visibility(desired_keys)

            if stale_refresh:
                self._log_editor_content_swapped(m, region="layer_nav")

            log_event(
                "studio.gicleeframe.layer_nav.delta",
                element_type=m.element_type,
                desired_tiles=len(desired_keys),
                cached_tiles=len(self._layer_nav_tile_cache),
                visible_tiles=len(
                    [key for key in self._layer_nav_visible_keys if key.startswith("slot:")]
                ),
                before_children=before_children,
                after_children=len(self._layer_nav_frame.winfo_children()),
            )
            log_event(
                "studio.gicleeframe.layer_nav.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(self._layer_nav_frame.winfo_children()),
                visible_tiles=len(
                    [key for key in self._layer_nav_visible_keys if key.startswith("slot:")]
                ),
                cached_tiles=len(self._layer_nav_tile_cache),
            )
            log_event(
                "studio.gicleeframe.layer_nav",
                element_type=m.element_type,
                children_before_destroy=before_children,
                items_built=len(items),
            )

    def _preview_key_for_element(self, m: MergedPageElement) -> str:
        element_type = m.element_type or "default"
        if element_type in {"divider", "image", "media_section", "section_legacy"}:
            return f"preview:{element_type}"
        if element_type in {"jumbo", "body", "heading", "text", "rich_text"}:
            return "preview:text"
        return "preview:default"

    def _hide_preview_frames(self) -> None:
        for frame in self._preview_frame_cache.values():
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
        self._preview_active_key = None

    def _show_preview_frame(self, key: str) -> None:
        frame = self._preview_frame_cache.get(key)
        if frame is None:
            return
        if self._preview_active_key == key:
            return
        try:
            frame.pack(fill="both", expand=True)
            self._preview_active_key = key
        except tk.TclError:
            return

    def _get_or_create_preview_frame(self, key: str) -> ctk.CTkFrame:
        canvas = self._section_preview_canvas
        if canvas is None:
            raise RuntimeError("section_preview_canvas is not initialized")
        cached = self._preview_frame_cache.get(key)
        if cached is not None:
            return cached
        frame = ctk.CTkFrame(canvas, fg_color="transparent")
        self._preview_frame_cache[key] = frame
        self._preview_value_widgets[key] = {}
        log_event(
            "studio.gicleeframe.preview.frame_created",
            key=key,
        )
        return frame

    def _get_or_create_preview_label(
        self,
        preview_key: str,
        widget_key: str,
        parent: ctk.CTkBaseClass,
        *,
        label: str = "",
        wraplength: int | None = None,
        **kwargs: Any,
    ) -> ctk.CTkLabel:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        cached = widgets.get(widget_key)
        if isinstance(cached, ctk.CTkLabel):
            return cached
        label_kwargs: dict[str, Any] = {
            "text": label,
            "anchor": "w",
            "justify": "left",
        }
        if wraplength is not None:
            label_kwargs["wraplength"] = wraplength
        label_kwargs.update(kwargs)
        widget = ctk.CTkLabel(parent, **label_kwargs)
        widgets[widget_key] = widget
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key=widget_key,
        )
        return widget

    def _clear_preview_shell_bootstrap_once(self) -> None:
        canvas = self._section_preview_canvas
        if canvas is None or self._preview_shell_bootstrapped:
            return
        if self._preview_bootstrap_panel is not None:
            try:
                self._preview_bootstrap_panel.destroy()
            except tk.TclError:
                pass
            self._preview_bootstrap_panel = None
            self._preview_bootstrap_status_label = None
        cached_frames = set(self._preview_frame_cache.values())
        bootstrap_children = [
            child for child in canvas.winfo_children() if child not in cached_frames
        ]
        if not bootstrap_children:
            self._preview_shell_bootstrapped = True
            return
        for child in bootstrap_children:
            try:
                child.destroy()
            except tk.TclError:
                continue
        self._preview_shell_bootstrapped = True
        log_event(
            "studio.gicleeframe.preview.destroy_fallback",
            reason="shell_bootstrap",
        )

    def _divider_preview_dimensions(self, m: MergedPageElement) -> tuple[int, int]:
        height = 2
        width_pad = 52
        for field in m.page_settings:
            if field.key == "thickness":
                try:
                    height = max(1, min(10, int(float(field.value) * 2)))
                except (TypeError, ValueError):
                    height = 2
            elif field.key == "width_percent":
                try:
                    width = max(20, min(100, int(float(field.value))))
                    width_pad = int(52 + ((100 - width) * 0.9))
                except (TypeError, ValueError):
                    width_pad = 52
        return height, width_pad

    def _build_divider_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        ghost_top = ctk.CTkFrame(frame, fg_color=_GF_FIELD_HOVER, corner_radius=999, height=4)
        ghost_top.pack(fill="x", padx=38, pady=(16, 10))
        ghost_top.pack_propagate(False)
        widgets["ghost_top"] = ghost_top

        line = ctk.CTkFrame(
            frame,
            height=2,
            fg_color=_GF_GOLD,
            corner_radius=999,
        )
        line.pack(fill="x", padx=52, pady=(4, 10))
        line.pack_propagate(False)
        widgets["line"] = line
        self._section_preview_line = line

        ghost_bottom = ctk.CTkFrame(frame, fg_color=_GF_FIELD_HOVER, corner_radius=999, height=4)
        ghost_bottom.pack(fill="x", padx=70, pady=(0, 14))
        ghost_bottom.pack_propagate(False)
        widgets["ghost_bottom"] = ghost_bottom

    def _update_divider_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        line = widgets.get("line")
        if not isinstance(line, ctk.CTkFrame):
            return
        height, width_pad = self._divider_preview_dimensions(m)
        line.configure(height=height)
        line.pack_configure(padx=max(18, width_pad))
        self._section_preview_line = line

    def _build_media_section_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="SEKCJA",
        )

    def _update_media_section_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.title or m.label or parent_row_title(m) or "Sekcja edytorska"
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Uproszczony podgląd struktury sekcji",
        )

    def _build_legacy_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="LEGACY",
        )

    def _update_legacy_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.label or parent_row_title(m) or "Sekcja legacy"
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Sekcja legacy · tylko podgląd / notatka",
        )

    def _build_default_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="INFO",
        )

    def _update_default_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.title or m.label or editor_title_for_element(m)
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Podgląd metadanych elementu",
            fallback=True,
        )

    def _build_image_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        layout = ctk.CTkFrame(frame, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=16, pady=12)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)

        image_box = ctk.CTkFrame(
            layout,
            fg_color=_GF_CARD_SOFT,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
            width=96,
        )
        image_box.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        image_box.grid_propagate(False)

        ctk.CTkLabel(
            image_box,
            text="IMAGE",
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
        ).place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            image_box,
            text="RAM",
            font=theme.get_font(8),
            text_color=_GF_MUTED,
        ).place(relx=0.5, rely=0.62, anchor="center")

        meta = ctk.CTkFrame(layout, fg_color="transparent")
        meta.grid(row=0, column=1, sticky="nsew")

        self._get_or_create_preview_label(
            preview_key,
            "heading_label",
            meta,
            label="Grafika sekcji",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
        ).pack(fill="x", pady=(4, 4))

        ref_label = self._get_or_create_preview_label(
            preview_key,
            "ref_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            wraplength=360,
        )
        ref_label.pack(fill="x")

        self._get_or_create_preview_label(
            preview_key,
            "footnote_label",
            meta,
            label="Źródło tylko do podglądu · bez zapisu pliku",
            font=theme.get_font(8),
            text_color=_GF_GOLD_SOFT,
        ).pack(fill="x", pady=(8, 0))

    def _update_image_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        ref_label = widgets.get("ref_label")
        if isinstance(ref_label, ctk.CTkLabel):
            ref_label.configure(text=_ellipsize(self._image_ref_label(m.image_ref), 52))

    def _build_text_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        box = ctk.CTkFrame(frame, fg_color=_GF_FIELD, corner_radius=10)
        box.pack(fill="both", expand=True, padx=18, pady=14)

        title_label = ctk.CTkLabel(
            box,
            text="",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
            anchor="center",
        )
        title_label.place(relx=0.5, rely=0.42, anchor="center")
        widgets["title_label"] = title_label
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key="title_label",
        )

        kind_label = ctk.CTkLabel(
            box,
            text="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            anchor="center",
        )
        kind_label.place(relx=0.5, rely=0.62, anchor="center")
        widgets["kind_label"] = kind_label
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key="kind_label",
        )

    def _update_text_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        title_label = widgets.get("title_label")
        kind_label = widgets.get("kind_label")
        label = m.title or m.label or editor_title_for_element(m)
        if isinstance(title_label, ctk.CTkLabel):
            title_label.configure(text=_ellipsize(label, 48))
        if isinstance(kind_label, ctk.CTkLabel):
            kind_label.configure(text=editor_title_for_element(m))

    def _ensure_preview_structure(self, preview_key: str) -> None:
        if preview_key in self._preview_frame_cache:
            frame = self._preview_frame_cache[preview_key]
            if frame.winfo_children():
                return
        frame = self._get_or_create_preview_frame(preview_key)
        if preview_key == "preview:divider":
            self._build_divider_preview_structure(frame, preview_key)
        elif preview_key == "preview:media_section":
            self._build_media_section_preview_structure(frame, preview_key)
        elif preview_key == "preview:section_legacy":
            self._build_legacy_preview_structure(frame, preview_key)
        elif preview_key == "preview:image":
            self._build_image_preview_structure(frame, preview_key)
        elif preview_key == "preview:text":
            self._build_text_preview_structure(frame, preview_key)
        elif preview_key == "preview:default":
            self._build_default_preview_structure(frame, preview_key)
        else:
            self._build_default_preview_structure(frame, preview_key)

    def _update_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        if preview_key == "preview:divider":
            self._update_divider_preview_content(preview_key, m)
        elif preview_key == "preview:media_section":
            self._update_media_section_preview_content(preview_key, m)
        elif preview_key == "preview:section_legacy":
            self._update_legacy_preview_content(preview_key, m)
        elif preview_key == "preview:image":
            self._update_image_preview_content(preview_key, m)
        elif preview_key == "preview:text":
            self._update_text_preview_content(preview_key, m)
        elif preview_key == "preview:default":
            self._update_default_preview_content(preview_key, m)
        else:
            self._update_default_preview_content(preview_key, m)

    def _update_section_preview(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        canvas = self._section_preview_canvas
        if canvas is None:
            return

        with span(
            "studio.gicleeframe.populate.preview",
            element_type=m.element_type,
            selected_id=m.element_id,
            cached_frames=len(self._preview_frame_cache),
            stale_refresh=stale_refresh,
        ):
            before_children = len(canvas.winfo_children())
            preview_key = self._preview_key_for_element(m)
            previous_key = self._preview_active_key

            if self._section_preview_badge is not None:
                self._section_preview_badge.configure(
                    text=_section_kind_copy(m.element_id, self._merged) or "RAM preview",
                )

            self._ensure_preview_structure(preview_key)
            self._update_preview_content(preview_key, m)

            if stale_refresh and previous_key:
                if previous_key != preview_key:
                    self._show_preview_frame(preview_key)
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )
                else:
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )
            else:
                self._clear_preview_shell_bootstrap_once()
                self._hide_preview_frames()
                self._show_preview_frame(preview_key)
                if previous_key and previous_key != preview_key:
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )

            log_event(
                "studio.gicleeframe.preview.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(canvas.winfo_children()),
                active_key=preview_key,
                cached_frames=len(self._preview_frame_cache),
                widget_count=len(self._preview_value_widgets.get(preview_key, {})),
            )
            log_event(
                "studio.gicleeframe.section_preview",
                element_type=m.element_type,
                children_before_destroy=before_children,
            )

    def _image_ref_label(self, image_ref: str) -> str:
        if not image_ref:
            return "Brak przypisanej grafiki"
        clean = image_ref.replace("shopify://", "")
        return clean.rsplit("/", 1)[-1] if "/" in clean else clean

    def _pack_field_vertical(
        self,
        parent: ctk.CTkFrame,
        label: str,
        widget: ctk.CTkBaseClass,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(
            row,
            text=label.upper(),
            font=theme.get_font(8, "bold"),
            text_color=_GF_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        widget.pack(fill="x")

    def _pack_setting_field_row(
        self,
        parent: ctk.CTkFrame,
        field: object,
    ) -> None:
        from giclee_app.studio.gicleeframe_page_settings import PageSettingField

        if not isinstance(field, PageSettingField):
            return
        if field.control == "select" and field.options:
            menu = ctk.CTkOptionMenu(
                parent,
                values=list(field.options),
                height=30,
                **_f2_menu_kwargs(),
            )
            menu.set(field.value if field.value in field.options else field.options[0])
            self._page_setting_widgets[field.key] = menu
            self._pack_field_vertical(parent, field.label, menu)
        else:
            entry = ctk.CTkEntry(
                parent,
                **_f2_entry_kwargs(),
            )
            entry.insert(0, field.value)
            self._page_setting_widgets[field.key] = entry
            self._pack_field_vertical(parent, field.label, entry)

    def _hide_page_context_rows(self) -> None:
        for key, frame in self._page_context_row_cache.items():
            manager = self._page_context_row_managers.get(key, "pack")
            try:
                if manager == "grid":
                    frame.grid_remove()
                else:
                    frame.pack_forget()
            except tk.TclError:
                continue
        self._page_context_visible_keys.clear()

    def _show_page_context_row(self, key: str, **pack_kwargs: object) -> None:
        if key in self._page_context_visible_keys:
            return
        frame = self._page_context_row_cache.get(key)
        if frame is None:
            return
        manager = self._page_context_row_managers.get(key, "pack")
        try:
            if manager == "grid":
                grid_opts = self._page_context_divider_group_grid_opts.get(key, {})
                frame.grid(**grid_opts)
            else:
                frame.pack(**pack_kwargs)
            self._page_context_visible_keys.add(key)
        except tk.TclError:
            return

    def _get_or_create_readonly_card(self) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = "container:readonly"
        if self._page_context_readonly_body is not None:
            return self._page_context_readonly_body
        info_card, info_body = self._build_setting_group_card(
            self._page_context_inner,
            "Kontekst sekcji",
        )
        self._page_context_row_cache[key] = info_card
        self._page_context_row_managers[key] = "pack"
        self._page_context_readonly_body = info_body
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="readonly_card",
        )
        return info_body

    def _get_or_create_page_context_row(
        self,
        key: str,
        *,
        label: str,
        kind: str = "readonly",
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            value_widget = self._page_context_value_widgets.get(key)
            if isinstance(value_widget, ctk.CTkLabel):
                return cached, value_widget

        self._get_or_create_readonly_card()
        row = ctk.CTkFrame(self._page_context_readonly_body, fg_color="transparent")
        ctk.CTkLabel(
            row,
            text=f"{label}:",
            width=_F2_FIELD_LABEL_WIDTH,
            anchor="nw",
            font=theme.get_font(9),
            text_color=theme.TextMuted,
        ).pack(side="left")
        value_widget = ctk.CTkLabel(
            row,
            text="",
            anchor="nw",
            justify="left",
            wraplength=280,
            font=theme.get_font(10),
            text_color=theme.TextPrimary,
        )
        value_widget.pack(side="left", fill="x", expand=True)
        self._page_context_row_cache[key] = row
        self._page_context_value_widgets[key] = value_widget
        self._page_context_row_managers[key] = "pack"
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind=kind,
        )
        return row, value_widget

    def _get_or_create_divider_grid(self) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = "container:divider_grid"
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            return cached
        grid = ctk.CTkFrame(self._page_context_inner, fg_color="transparent")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        self._page_context_row_cache[key] = grid
        self._page_context_row_managers[key] = "pack"
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="divider_grid",
        )
        return grid

    def _get_or_create_divider_group(self, group_title: str, slot: int) -> ctk.CTkFrame:
        key = f"divider_group:{group_title}"
        cached_body = self._page_context_divider_group_bodies.get(key)
        if cached_body is not None:
            return cached_body
        grid = self._get_or_create_divider_grid()
        card, body = self._build_setting_group_card(grid, group_title)
        row_idx, col_idx = divmod(slot, 2)
        grid_opts: dict[str, object] = {
            "row": row_idx,
            "column": col_idx,
            "sticky": "nsew",
            "padx": (0 if col_idx == 0 else 6, 6 if col_idx == 0 else 0),
            "pady": 6,
        }
        card.grid(**grid_opts)
        self._page_context_row_cache[key] = card
        self._page_context_row_managers[key] = "grid"
        self._page_context_divider_group_bodies[key] = body
        self._page_context_divider_group_grid_opts[key] = grid_opts
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="divider_group",
        )
        return body

    def _update_setting_widget(
        self,
        widget: ctk.CTkBaseClass,
        field: PageSettingField,
    ) -> None:
        if isinstance(widget, ctk.CTkOptionMenu):
            options = list(field.options)
            widget.configure(values=options)
            value = (
                field.value
                if field.value in field.options
                else (field.options[0] if field.options else "")
            )
            widget.set(value)
        elif isinstance(widget, ctk.CTkEntry):
            widget.delete(0, "end")
            widget.insert(0, field.value)

    def _create_page_setting_widget(
        self,
        parent: ctk.CTkFrame,
        field: PageSettingField,
    ) -> ctk.CTkBaseClass:
        key = f"setting:{field.key}"
        cached = self._page_context_value_widgets.get(key)
        if cached is not None:
            self._update_setting_widget(cached, field)
            self._page_setting_widgets[field.key] = cached
            return cached

        if field.control == "select" and field.options:
            menu = ctk.CTkOptionMenu(
                parent,
                values=list(field.options),
                height=30,
                **_f2_menu_kwargs(),
            )
            menu.set(field.value if field.value in field.options else field.options[0])
            widget: ctk.CTkBaseClass = menu
        else:
            entry = ctk.CTkEntry(
                parent,
                **_f2_entry_kwargs(),
            )
            entry.insert(0, field.value)
            widget = entry

        self._page_context_value_widgets[key] = widget
        self._page_setting_widgets[field.key] = widget
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="setting",
        )
        return widget

    def _get_or_create_page_setting_row(
        self,
        parent: ctk.CTkFrame,
        field: PageSettingField,
    ) -> ctk.CTkBaseClass:
        key = f"setting:{field.key}"
        cached = self._page_context_value_widgets.get(key)
        if cached is not None:
            self._update_setting_widget(cached, field)
            self._page_setting_widgets[field.key] = cached
            return cached

        widget = self._create_page_setting_widget(parent, field)
        self._pack_field_vertical(parent, field.label, widget)
        return widget

    def _get_or_create_setting_card(self, field: PageSettingField) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = f"setting_card:{field.key}"
        cached_body = self._page_context_setting_card_bodies.get(field.key)
        if cached_body is not None:
            self._get_or_create_page_setting_row(cached_body, field)
            return cached_body
        card, body = self._build_setting_group_card(
            self._page_context_inner,
            field.label,
        )
        self._page_context_row_cache[key] = card
        self._page_context_row_managers[key] = "pack"
        self._page_context_setting_card_bodies[field.key] = body
        self._get_or_create_page_setting_row(body, field)
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="setting_card",
        )
        return body

    def _reset_page_context_settings_on_layout_change(self, new_layout: str) -> None:
        keys_to_remove = [
            key
            for key in list(self._page_context_row_cache)
            if key == "container:divider_grid"
            or key.startswith("divider_group:")
            or key.startswith("collapsed_group:")
            or key.startswith("setting_summary:")
            or key.startswith("setting_card:")
        ]
        for key in keys_to_remove:
            frame = self._page_context_row_cache.pop(key, None)
            if frame is not None:
                try:
                    frame.destroy()
                except tk.TclError:
                    pass
            self._page_context_row_managers.pop(key, None)
            self._page_context_visible_keys.discard(key)
            self._page_context_divider_group_grid_opts.pop(key, None)

        for key in list(self._page_context_value_widgets):
            if key.startswith("setting:"):
                del self._page_context_value_widgets[key]

        self._page_context_divider_group_bodies.clear()
        self._page_context_setting_card_bodies.clear()
        self._page_context_collapsed_group_rows.clear()
        self._page_context_collapsed_group_bodies.clear()
        self._page_context_collapsed_group_buttons.clear()
        self._page_context_expanded_group_ids.clear()
        self._page_context_summary_rows.clear()
        self._page_context_summary_value_labels.clear()
        self._page_setting_widgets.clear()
        self._close_active_setting_editor()
        log_event(
            "studio.gicleeframe.page_context.destroy_fallback",
            reason="settings_layout_change",
            new_layout=new_layout,
        )

    def _edit_panel_pack_anchor(self) -> ctk.CTkBaseClass | None:
        """First visible form row in the edit panel (for inventory block placement)."""
        if self._edit_panel is None:
            return None
        for child in self._edit_panel.winfo_children():
            if child is self._page_context_frame:
                continue
            if isinstance(child, ctk.CTkButton):
                continue
            if child.winfo_manager() == "pack":
                return child
        return None

    def _cancel_selection_jobs(self) -> int:
        cancelled = len(self._selection_after_ids)
        while self._selection_after_ids:
            after_id = self._selection_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        if self._media_deferred_done_after_id is not None:
            try:
                self.after_cancel(self._media_deferred_done_after_id)
            except tk.TclError:
                pass
            self._media_deferred_done_after_id = None
        return cancelled

    def _schedule_selection_job(self, delay_ms: int, callback: Callable[[], None]) -> None:
        after_id = self.after(delay_ms, callback)
        self._selection_after_ids.append(after_id)

    def _cancel_page_context_jobs(self) -> int:
        cancelled = len(self._page_context_after_ids)
        while self._page_context_after_ids:
            after_id = self._page_context_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        return cancelled

    def _schedule_page_context_job(self, delay_ms: int, callback: Callable[[], None]) -> None:
        after_id = self.after(delay_ms, callback)
        self._page_context_after_ids.append(after_id)

    def _page_context_pack_kwargs(self) -> dict[str, object]:
        pack_kwargs: dict[str, object] = {"fill": "x", "pady": (0, 8)}
        preferred_anchor = self._notes_row or self._image_ref_row or self._edit_panel_pack_anchor()
        if preferred_anchor is not None and preferred_anchor.winfo_manager() == "pack":
            pack_kwargs["before"] = preferred_anchor
        else:
            anchor = self._edit_panel_pack_anchor()
            if anchor is not None:
                pack_kwargs["before"] = anchor
        return pack_kwargs

    def _clear_page_context_loading_label(self) -> None:
        if self._page_context_loading_label is None:
            return
        try:
            self._page_context_loading_label.destroy()
        except tk.TclError:
            pass
        self._page_context_loading_label = None

    def _show_page_context_loading_state(self, m: MergedPageElement) -> None:
        """Backward-compatible alias — shell summary replaces heavy loading placeholder."""
        self._show_page_context_shell_state(m)
        log_event(
            "studio.gicleeframe.page_context.loading_state",
            element_id=m.element_id,
            element_type=m.element_type,
        )
        log_event(
            "studio.gicleeframe.selection.page_context.loading_state",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _page_context_row_specs(
        self,
        m: MergedPageElement,
        *,
        show: bool = True,
    ) -> list[PageContextRowSpec]:
        if not show:
            return []
        readonly_rows = editor_context_rows(m)
        if not readonly_rows and not m.page_settings:
            return []

        specs: list[PageContextRowSpec] = []
        if readonly_rows:
            specs.append(PageContextRowSpec(kind="readonly_card"))
            for ro_label, ro_value in readonly_rows:
                specs.append(
                    PageContextRowSpec(
                        kind="readonly_row",
                        label=ro_label,
                        value=ro_value or "—",
                    )
                )

        new_layout = ""
        if m.page_settings:
            new_layout = "divider" if m.element_type == "divider" else "flat"

        fields_by_key = {field.key: field for field in m.page_settings}
        if new_layout == "divider" and fields_by_key:
            for group_id, (group_title, setting_keys) in _DIVIDER_LAZY_GROUPS.items():
                present = tuple(key for key in setting_keys if key in fields_by_key)
                if not present:
                    continue
                specs.append(
                    PageContextRowSpec(
                        kind="collapsed_group",
                        key=f"collapsed_group:{group_id}",
                        group_id=group_id,
                        group_title=group_title,
                        group_settings=present,
                    )
                )
        elif new_layout == "flat":
            for field in m.page_settings:
                specs.append(PageContextRowSpec(kind="setting_card", field=field))

        return specs

    def _reset_page_context_lazy_group_visual_state(
        self,
        m: MergedPageElement | None = None,
    ) -> None:
        self._page_context_expanded_group_ids.clear()
        specs_by_group: dict[str, PageContextRowSpec] = {}
        if m is not None:
            specs = self._page_context_specs_cache.get(m.element_id)
            if specs is None:
                specs = self._page_context_row_specs(m, show=True)
            for spec in specs:
                if spec.kind == "collapsed_group":
                    specs_by_group[spec.group_id] = spec
        for _group_id, body in list(self._page_context_collapsed_group_bodies.items()):
            try:
                body.pack_forget()
            except tk.TclError:
                pass
        for group_id, btn in self._page_context_collapsed_group_buttons.items():
            spec = specs_by_group.get(group_id)
            if spec is None:
                continue
            title = spec.group_title or spec.label
            count = len(spec.group_settings)
            try:
                btn.configure(text=f"▸ {title} · {count} ustawienia")
            except tk.TclError:
                pass

    def _make_page_setting_spec(
        self,
        m: MergedPageElement,
        setting_id: str,
        *,
        group_id: str = "",
        group_title: str = "",
    ) -> PageContextRowSpec | None:
        fields_by_key = {field.key: field for field in m.page_settings}
        field = fields_by_key.get(setting_id)
        if field is None:
            return None
        return PageContextRowSpec(
            kind="page_setting",
            field=field,
            group_id=group_id,
            group_title=group_title,
            setting_id=setting_id,
            label=field.label,
        )

    def _format_page_setting_value(
        self,
        m: MergedPageElement,
        setting_id: str,
    ) -> str:
        for field in m.page_settings:
            if field.key == setting_id:
                return field.value if field.value not in (None, "") else "—"
        return "—"

    def _create_page_context_setting_summary_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if spec.field is None and not spec.setting_id:
            return

        setting_id = spec.setting_id or (spec.field.key if spec.field else "")
        if not setting_id:
            return

        parent = self._page_context_collapsed_group_bodies.get(spec.group_id)
        if parent is None:
            return

        label = spec.label or (spec.field.label if spec.field else setting_id)
        row_key = f"setting_summary:{m.element_id}:{setting_id}"
        value_text = self._format_page_setting_value(m, setting_id)

        cached = self._page_context_row_cache.get(row_key)
        if cached is not None:
            self._page_context_summary_rows[row_key] = cached
            value_label = self._page_context_summary_value_labels.get(row_key)
            if value_label is not None:
                try:
                    value_label.configure(text=f"{label}\n{value_text}")
                except tk.TclError:
                    pass
            try:
                cached.pack(fill="x", padx=10, pady=4)
            except tk.TclError:
                pass
            return

        row = _make_gf_card(parent, variant="soft", radius=8)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)

        text = ctk.CTkLabel(
            row,
            text=f"{label}\n{value_text}",
            justify="left",
            anchor="w",
            font=theme.get_font(11),
            text_color=theme.TextPrimary,
        )
        text.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        btn = ctk.CTkButton(
            row,
            text="Edytuj",
            width=72,
            command=lambda e=m, s=spec, r=row: self._open_inline_setting_editor(e, s, r),
        )
        btn.grid(row=0, column=1, sticky="e", padx=10, pady=8)

        row.pack(fill="x", padx=10, pady=4)
        self._page_context_row_cache[row_key] = row
        self._page_context_summary_rows[row_key] = row
        self._page_context_summary_value_labels[row_key] = text
        log_event(
            "studio.gicleeframe.page_context.setting_summary_created",
            element_id=m.element_id,
            element_type=m.element_type,
            setting_id=setting_id,
        )

    def _close_active_setting_editor(self) -> None:
        if self._active_setting_editor_row is None:
            return

        setting_id = ""
        if self._active_setting_editor_key and ":" in self._active_setting_editor_key:
            setting_id = self._active_setting_editor_key.split(":", 1)[1]

        try:
            for child in self._active_setting_editor_row.winfo_children():
                if getattr(child, "_giclee_inline_setting_editor", False):
                    child.destroy()
        except tk.TclError:
            pass

        if setting_id:
            self._page_context_value_widgets.pop(f"setting:{setting_id}", None)
            self._page_setting_widgets.pop(setting_id, None)

        self._active_setting_editor_row = None
        self._active_setting_editor_key = None

    def _open_inline_setting_editor(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
        row: ctk.CTkFrame,
    ) -> None:
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.setting_editor_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                setting_id=spec.setting_id,
            )
            return

        setting_id = spec.setting_id or (spec.field.key if spec.field else "")
        self._close_active_setting_editor()

        editor_key = f"{m.element_id}:{setting_id}"
        self._active_setting_editor_key = editor_key
        self._active_setting_editor_row = row

        with span(
            "studio.gicleeframe.page_context.setting_editor.open",
            element_type=m.element_type,
            setting_id=setting_id,
        ):
            self._create_full_setting_editor_inside_row(m, spec, row)

        log_event(
            "studio.gicleeframe.page_context.setting_editor.opened",
            element_id=m.element_id,
            element_type=m.element_type,
            setting_id=setting_id,
        )

    def _create_full_setting_editor_inside_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
        row: ctk.CTkFrame,
    ) -> None:
        if spec.field is None:
            fields_by_key = {field.key: field for field in m.page_settings}
            field = fields_by_key.get(spec.setting_id)
            if field is None:
                return
        else:
            field = spec.field

        editor = ctk.CTkFrame(
            row,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        editor._giclee_inline_setting_editor = True  # type: ignore[attr-defined]
        editor.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        widget = self._create_page_setting_widget(editor, field)
        widget.pack(fill="x", padx=8, pady=8)

    def _create_page_context_collapsed_group_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if self._page_context_inner is None:
            return

        key = spec.key or f"collapsed_group:{spec.group_id}"
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            self._page_context_collapsed_group_rows[spec.group_id] = cached
            btn = self._page_context_collapsed_group_buttons.get(spec.group_id)
            if btn is not None:
                count = len(spec.group_settings)
                title = spec.group_title or spec.label
                try:
                    btn.configure(text=f"▸ {title} · {count} ustawienia")
                except tk.TclError:
                    pass
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is not None:
                try:
                    body.pack_forget()
                except tk.TclError:
                    pass
            self._show_page_context_row(key, fill="x", padx=8, pady=4)
            return

        title = spec.group_title or spec.label
        count = len(spec.group_settings)
        row = _make_gf_card(self._page_context_inner, variant="soft", radius=8)
        btn = ctk.CTkButton(
            row,
            text=f"▸ {title} · {count} ustawienia",
            anchor="w",
            fg_color="transparent",
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            font=theme.get_font(11, "bold"),
            command=lambda e=m, s=spec: self._expand_page_context_group(e, s),
        )
        btn.pack(fill="x", padx=8, pady=8)
        self._page_context_row_cache[key] = row
        self._page_context_row_managers[key] = "pack"
        self._page_context_collapsed_group_rows[spec.group_id] = row
        self._page_context_collapsed_group_buttons[spec.group_id] = btn
        self._show_page_context_row(key, fill="x", padx=8, pady=4)
        log_event(
            "studio.gicleeframe.page_context.group_placeholder_created",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=spec.group_id,
            group_title=title,
            settings_count=count,
        )

    def _expand_page_context_group(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.group_expand_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                group_id=spec.group_id,
            )
            return

        if spec.group_id in self._page_context_expanded_group_ids:
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is not None:
                try:
                    body.pack(fill="x", padx=8, pady=(0, 8))
                except tk.TclError:
                    pass
            return

        log_event(
            "studio.gicleeframe.page_context.group_expanded",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=spec.group_id,
            group_title=spec.group_title,
            settings_count=len(spec.group_settings),
        )

        btn = self._page_context_collapsed_group_buttons.get(spec.group_id)
        if btn is not None:
            try:
                btn.configure(text=f"▾ {spec.group_title}")
            except tk.TclError:
                pass

        row = self._page_context_collapsed_group_rows.get(spec.group_id)
        if row is None:
            return

        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(fill="x", padx=8, pady=(0, 8))
        self._page_context_collapsed_group_bodies[spec.group_id] = body
        self._page_context_expanded_group_ids.add(spec.group_id)

        setting_specs: list[PageContextRowSpec] = []
        for setting_id in spec.group_settings:
            setting_spec = self._make_page_setting_spec(
                m,
                setting_id,
                group_id=spec.group_id,
                group_title=spec.group_title,
            )
            if setting_spec is not None:
                setting_specs.append(setting_spec)

        if setting_specs:
            self._populate_page_context_group_batch(m, spec.group_id, setting_specs, 0)

    def _populate_page_context_group_batch(
        self,
        m: MergedPageElement,
        group_id: str,
        specs: list[PageContextRowSpec],
        start: int,
    ) -> None:
        if self._defer_background_for_selection(
            job="page_context.group_batch",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_group_batch(m, group_id, specs, start),
        ):
            return
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.group_batch_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                group_id=group_id,
            )
            return

        started = time.perf_counter()
        end = min(start + _GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE, len(specs))

        for idx in range(start, end):
            self._create_page_context_setting_summary_row(m, specs[idx])

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.page_context.group_summary_batch",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=group_id,
            start=start,
            end=end,
            created=end - start,
            total_rows=len(specs),
            elapsed_ms=elapsed_ms,
        )

        if end < len(specs):
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS,
                lambda e=m, g=group_id, s=specs, n=end: self._populate_page_context_group_batch(
                    e, g, s, n
                ),
            )

    def _precompute_page_context_specs_cache(self) -> None:
        if not _progressive_page_context_enabled():
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        cached_count = 0
        for m in self._merged:
            fields = editor_field_visibility(m.element_type)
            if not fields.page_context:
                continue
            readonly_rows = editor_context_rows(m)
            if not readonly_rows and not m.page_settings:
                continue
            self._page_context_specs_cache[m.element_id] = self._page_context_row_specs(
                m,
                show=True,
            )
            cached_count += 1
        log_event(
            "studio.gicleeframe.page_context.specs_cache_ready",
            cached_count=cached_count,
            merged_count=len(self._merged),
        )

    def _create_page_context_row_from_spec(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if spec.kind == "readonly_card":
            self._get_or_create_readonly_card()
            self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        elif spec.kind == "readonly_row":
            row_key = f"readonly:{spec.label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=spec.label,
                kind="readonly",
            )
            value_widget.configure(text=spec.value or "—")
            self._show_page_context_row(row_key, fill="x", pady=2)
        elif spec.kind == "divider_grid":
            self._get_or_create_divider_grid()
            self._show_page_context_row("container:divider_grid", fill="x")
        elif spec.kind == "divider_group":
            self._get_or_create_divider_group(spec.group_title, spec.slot)
            self._show_page_context_row(f"divider_group:{spec.group_title}")
        elif spec.kind == "collapsed_group":
            self._create_page_context_collapsed_group_row(m, spec)
        elif spec.kind == "page_setting" and spec.field is not None:
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is None and spec.group_title:
                body = self._page_context_divider_group_bodies.get(
                    f"divider_group:{spec.group_title}",
                )
            if body is not None:
                self._get_or_create_page_setting_row(body, spec.field)
        elif spec.kind == "setting_card" and spec.field is not None:
            self._get_or_create_setting_card(spec.field)
            self._show_page_context_row(
                f"setting_card:{spec.field.key}",
                fill="x",
                pady=(0, 8),
            )

    def _populate_page_context_batch(
        self,
        m: MergedPageElement,
        specs: list[PageContextRowSpec],
        start: int,
    ) -> None:
        if self._defer_background_for_selection(
            job="page_context.batch",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_batch(m, specs, start),
        ):
            return
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.batch_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
            )
            return

        started = time.perf_counter()
        end = min(start + _GF_PAGE_CONTEXT_BATCH_SIZE, len(specs))

        for idx in range(start, end):
            self._create_page_context_row_from_spec(m, specs[idx])

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.page_context.batch",
            element_id=m.element_id,
            element_type=m.element_type,
            start=start,
            end=end,
            batch_index=start,
            created=end - start,
            total_rows=len(specs),
            total=len(specs),
            elapsed_ms=elapsed_ms,
            since_click_ms=self._since_selection_click_ms(),
        )

        if end < len(specs):
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_BATCH_DELAY_MS,
                lambda el=m, s=specs, n=end: self._populate_page_context_batch(el, s, n),
            )
            return

        settings_count = len(m.page_settings)
        readonly_rows = editor_context_rows(m)
        before_children = (
            len(self._page_context_inner.winfo_children())
            if self._page_context_inner is not None
            else 0
        )
        log_event(
            "studio.gicleeframe.page_context.progressive_done",
            element_id=m.element_id,
            element_type=m.element_type,
            total_rows=len(specs),
        )
        log_event(
            "studio.gicleeframe.page_context.reuse",
            element_type=m.element_type,
            before_children=before_children,
            after_children=before_children,
            visible_rows=len(self._page_context_visible_keys),
            cached_rows=len(self._page_context_row_cache),
            settings_count=settings_count,
        )
        log_event(
            "studio.gicleeframe.page_context",
            element_type=m.element_type,
            show=True,
            page_settings_count=settings_count,
            readonly_rows_count=len(readonly_rows),
            children_before_destroy=before_children,
        )

    def _populate_page_context_progressive_stable(
        self,
        m: MergedPageElement,
        generation: int,
    ) -> None:
        if generation != self._selection_generation or self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.stable_defer_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                generation=generation,
                current_generation=self._selection_generation,
            )
            log_event(
                "studio.gicleeframe.selection.page_context.stale",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                current_generation=self._selection_generation,
                selected_id=self._selected_id or "",
            )
            return

        log_event(
            "studio.gicleeframe.selection.page_context.populate_enter",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )
        log_event(
            "studio.gicleeframe.page_context.start",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )
        page_context_started = time.perf_counter()
        self._populate_page_context_progressive(m)
        if generation == self._selection_generation and self._selected_id == m.element_id:
            page_context_elapsed_ms = round((time.perf_counter() - page_context_started) * 1000, 2)
            log_event(
                "studio.gicleeframe.selection.page_context.populate_done",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=page_context_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.page_context.done",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=page_context_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )

    def _populate_page_context_progressive(self, m: MergedPageElement) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        if self._defer_background_for_selection(
            job="page_context.progressive",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_progressive(m),
        ):
            return

        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.deferred_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
            )
            return

        if self._page_context_frame is None or self._page_context_inner is None:
            return

        with span(
            "studio.gicleeframe.populate.page_context.progressive_prepare",
            element_type=m.element_type,
            element_id=m.element_id,
        ):
            specs = self._page_context_specs_cache.get(m.element_id)
            if specs is None:
                specs = self._page_context_row_specs(m, show=True)

        self._clear_page_context_loading_label()
        before_children = len(self._page_context_inner.winfo_children())
        self._hide_page_context_rows()
        self._reset_page_context_lazy_group_visual_state(m)

        readonly_rows = editor_context_rows(m)
        if not readonly_rows and not m.page_settings:
            self._page_context_frame.pack_forget()
            return

        new_layout = ""
        if m.page_settings:
            new_layout = "divider" if m.element_type == "divider" else "flat"

        if (
            new_layout
            and new_layout != self._page_context_settings_layout
            and self._page_context_settings_layout in ("divider", "flat")
        ):
            self._reset_page_context_settings_on_layout_change(new_layout)
        if new_layout:
            self._page_context_settings_layout = new_layout

        self._page_context_frame.pack(**self._page_context_pack_kwargs())
        self._page_context_last_signature = (
            m.element_type,
            new_layout,
            tuple(field.key for field in m.page_settings),
        )

        if not specs:
            log_event(
                "studio.gicleeframe.page_context.progressive_done",
                element_id=m.element_id,
                element_type=m.element_type,
                total_rows=0,
            )
            return

        self._populate_page_context_batch(m, specs, 0)

    def _fill_page_context(self, m: MergedPageElement, *, show: bool) -> None:
        if self._page_context_frame is None or self._page_context_inner is None:
            return

        readonly_rows = editor_context_rows(m) if show else ()
        settings_count = len(m.page_settings) if show else 0
        page_context_started = time.perf_counter() if show else None
        if show and (readonly_rows or m.page_settings):
            log_event(
                "studio.gicleeframe.page_context.start",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=self._selection_generation,
                since_click_ms=self._since_selection_click_ms(),
                immediate=True,
            )

        with span(
            "studio.gicleeframe.populate.page_context",
            element_type=m.element_type,
            show=bool(show and (readonly_rows or m.page_settings)),
            cached_rows=len(self._page_context_row_cache),
        ):
            before_children = len(self._page_context_inner.winfo_children())
            self._hide_page_context_rows()

            if not show:
                self._page_context_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.page_context.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._page_context_inner.winfo_children()),
                    visible_rows=0,
                    cached_rows=len(self._page_context_row_cache),
                    settings_count=0,
                )
                log_event(
                    "studio.gicleeframe.page_context",
                    element_type=m.element_type,
                    show=False,
                    page_settings_count=settings_count,
                    readonly_rows_count=0,
                    children_before_destroy=before_children,
                )
                return

            if not readonly_rows and not m.page_settings:
                self._page_context_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.page_context.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._page_context_inner.winfo_children()),
                    visible_rows=0,
                    cached_rows=len(self._page_context_row_cache),
                    settings_count=0,
                )
                log_event(
                    "studio.gicleeframe.page_context",
                    element_type=m.element_type,
                    show=True,
                    page_settings_count=settings_count,
                    readonly_rows_count=0,
                    children_before_destroy=before_children,
                )
                return

            pack_kwargs: dict = {"fill": "x", "pady": (0, 8)}

            preferred_anchor = self._notes_row or self._image_ref_row or self._edit_panel_pack_anchor()
            if preferred_anchor is not None and preferred_anchor.winfo_manager() == "pack":
                pack_kwargs["before"] = preferred_anchor
            else:
                anchor = self._edit_panel_pack_anchor()
                if anchor is not None:
                    pack_kwargs["before"] = anchor

            self._page_context_frame.pack(**pack_kwargs)

            if readonly_rows:
                self._get_or_create_readonly_card()
                self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
                for ro_label, ro_value in readonly_rows:
                    row_key = f"readonly:{ro_label}"
                    _, value_widget = self._get_or_create_page_context_row(
                        row_key,
                        label=ro_label,
                        kind="readonly",
                    )
                    value_widget.configure(text=ro_value or "—")
                    self._show_page_context_row(row_key, fill="x", pady=2)

            new_layout = ""
            if m.page_settings:
                new_layout = "divider" if m.element_type == "divider" else "flat"

            if (
                new_layout
                and new_layout != self._page_context_settings_layout
                and self._page_context_settings_layout in ("divider", "flat")
            ):
                self._reset_page_context_settings_on_layout_change(new_layout)
            if new_layout:
                self._page_context_settings_layout = new_layout

            fields_by_key = {field.key: field for field in m.page_settings}
            if new_layout == "divider" and fields_by_key:
                self._get_or_create_divider_grid()
                self._show_page_context_row("container:divider_grid", fill="x")
                slot = 0
                for group_title, keys in divider_setting_groups():
                    group_fields = [
                        fields_by_key[key] for key in keys if key in fields_by_key
                    ]
                    if not group_fields:
                        continue
                    body = self._get_or_create_divider_group(group_title, slot)
                    self._show_page_context_row(f"divider_group:{group_title}")
                    for field in group_fields:
                        self._get_or_create_page_setting_row(body, field)
                    slot += 1
            elif new_layout == "flat":
                for field in m.page_settings:
                    self._get_or_create_setting_card(field)
                    self._show_page_context_row(
                        f"setting_card:{field.key}",
                        fill="x",
                        pady=(0, 8),
                    )

            self._page_context_last_signature = (
                m.element_type,
                new_layout,
                tuple(field.key for field in m.page_settings),
            )

            log_event(
                "studio.gicleeframe.page_context.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(self._page_context_inner.winfo_children()),
                visible_rows=len(self._page_context_visible_keys),
                cached_rows=len(self._page_context_row_cache),
                settings_count=settings_count,
            )
            log_event(
                "studio.gicleeframe.page_context",
                element_type=m.element_type,
                show=True,
                page_settings_count=settings_count,
                readonly_rows_count=len(readonly_rows),
                children_before_destroy=before_children,
            )
            if page_context_started is not None:
                page_context_elapsed_ms = round((time.perf_counter() - page_context_started) * 1000, 2)
                log_event(
                    "studio.gicleeframe.page_context.done",
                    element_id=m.element_id,
                    element_type=m.element_type,
                    generation=self._selection_generation,
                    elapsed_ms=page_context_elapsed_ms,
                    since_click_ms=self._since_selection_click_ms(),
                    immediate=True,
                )

    def _fill_children_overview_buttons(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        parent_row = self._tree_row_for_element(m.element_id)
        total = len(parent_row.children) if parent_row is not None else 0
        if total == 0:
            if self._children_overview_buttons is None:
                return
            if m.element_type != "media_section":
                log_event(
                    "studio.gicleeframe.children_overview",
                    element_type=m.element_type,
                    children_count=0,
                )
                return
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return
        self._fill_children_overview_buttons_range(
            m,
            0,
            total,
            stale_refresh=stale_refresh,
        )

    def _fill_children_overview_buttons_range(
        self,
        m: MergedPageElement,
        start: int,
        end: int,
        *,
        stale_refresh: bool = False,
    ) -> None:
        if self._children_overview_buttons is None:
            return

        if m.element_type != "media_section":
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return

        parent_row = self._tree_row_for_element(m.element_id)
        if parent_row is None:
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return

        children = parent_row.children
        if start == 0:
            if stale_refresh:
                for child in list(self._children_overview_buttons.winfo_children()):
                    try:
                        child.destroy()
                    except tk.TclError:
                        continue
            else:
                for child in self._children_overview_buttons.winfo_children():
                    child.destroy()

        grid: ctk.CTkFrame | None = None
        for child_widget in self._children_overview_buttons.winfo_children():
            if isinstance(child_widget, ctk.CTkFrame):
                grid = child_widget
                break
        if grid is None:
            grid = ctk.CTkFrame(self._children_overview_buttons, fg_color="transparent")
            grid.pack(fill="x")

        for idx in range(start, min(end, len(children))):
            child = children[idx]
            grid.grid_columnconfigure(idx, weight=1)

            tile = _make_gf_card(grid, variant="field", radius=12, bordered=True)
            tile.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 6, 0), pady=(0, 2))

            ctk.CTkLabel(
                tile,
                text=editor_title_for_element(child.merged).replace("Edytor: ", "").upper(),
                font=theme.get_font(8, "bold"),
                text_color=_GF_GOLD_SOFT,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                tile,
                text=_ellipsize(child.child_label, 26),
                font=theme.get_font(11, "bold"),
                text_color=theme.TextPrimary,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 8))

            ctk.CTkLabel(
                tile,
                text="Kliknij, aby edytować",
                font=theme.get_font(9),
                text_color=_GF_MUTED,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 10))

            for target in (tile,):
                target.bind(
                    "<Button-1>",
                    lambda _e, mid=child.element_id: self._select_element(mid),
                )

            for nested in tile.winfo_children():
                nested.bind(
                    "<Button-1>",
                    lambda _e, mid=child.element_id: self._select_element(mid),
                )

        if end >= len(children):
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=len(children),
            )
            if stale_refresh:
                self._log_editor_content_swapped(m, region="children")

    def _set_row_visible(self, row: ctk.CTkFrame | None, visible: bool) -> None:
        if row is None:
            return
        if self._atomic_swap_suppress_visible:
            self._atomic_swap_deferred_row_visibility.append((row, visible))
            return
        if visible:
            row.pack(fill="x", pady=(0, 8))
            if row is self._notes_row and self._notes_group_frame is not None:
                self._notes_group_frame.pack(fill="x")
        else:
            row.pack_forget()

    def _set_entry(
        self,
        entry: ctk.CTkEntry,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled" if readonly else "normal")

    def _set_textbox(
        self,
        box: ctk.CTkTextbox,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", value)
        box.configure(state="disabled" if readonly else "normal")

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

    def _add_ram_variant(self) -> None:
        self._page_draft.add_variant()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Dodano wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _duplicate_ram_variant(self) -> None:
        self._page_draft.duplicate_active_variant()
        self._selected_id = None
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        self._render_section_menu()
        if self._on_status:
            self._on_status(
                f"Zduplikowano wariant: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _rename_ram_variant(self) -> None:
        dialog = ctk.CTkInputDialog(
            text="Nowa nazwa wariantu roboczego (tylko pamięć):",
            title=RENAME_VARIANT_LABEL,
        )
        name = dialog.get_input()
        if name and name.strip():
            self._page_draft.rename_active_variant(name.strip())
            self._update_top_bar()
            if self._on_status:
                self._on_status(
                    f"Zmieniono nazwę wariantu: {self._page_draft.draft_name}"
                )

    def _clear_page_draft(self) -> None:
        self._page_draft.clear()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Wyczyszczono wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _run_structure_dry_run(self) -> None:
        if self._inventory is None:
            self._refresh_inventory(warn_if_draft=False)
        inv = self._inventory
        if inv is None:
            return
        dry = build_page_structure_dry_run(inv, self._page_draft)
        ready = evaluate_gicleeframe_page_readiness(inv, dry)
        full = format_structure_dry_run_summary(dry) + "\n\n" + format_page_readiness_block(ready)
        if self._structure_dry_label:
            self._structure_dry_label.configure(text=full, text_color=theme.TextPrimary)
        self._fill_page_readiness(ready)
        if self._on_status:
            self._on_status(dry.status_badge)

    def _pack_readiness_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        value: str,
        ok: bool | None,
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text="●", text_color=status_color(ok), width=20).pack(side="left")
        ctk.CTkLabel(
            frame, text=label, width=180, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        ctk.CTkLabel(frame, text=value, anchor="w", font=theme.get_font(11, "bold")).pack(side="left")

