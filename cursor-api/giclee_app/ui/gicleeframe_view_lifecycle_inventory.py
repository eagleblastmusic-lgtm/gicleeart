"""GICLÉE FRAME™ — GF-M18 Lifecycle, Inventory & Shell Orchestration boundary."""

from __future__ import annotations

import os
import time
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.bg import run_async
from giclee_app.studio.perf import log_event, span
from giclee_app.studio.gicleeframe_page_draft import (
    MergedPageElement,
    SectionDropdownOption,
    merge_inventory_with_draft,
    section_dropdown_options,
    section_tree_rows,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    build_gicleeframe_page_inventory,
)
from . import theme
from .gicleeframe_view_section_list_shell import (
    _GF_SECTION_FIRST_BATCH_SIZE,
    _SECTION_LIST_LOADING_TEXT,
    _SECTION_LIST_WIDTH,
)
from .gicleeframe_view_primitives import (
    _make_gf_card,
    _make_secondary_button,
)

__all__ = (
    "GicleeFrameLifecycleInventoryMixin",
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
    "_env_enabled",
    "_progressive_boot_enabled",
    "_lazy_shell_enabled",
)

# ---------------------------------------------------------------------------
# Active constants
# ---------------------------------------------------------------------------

_GF_LOADING_OVERLAY_TEXT = "Przygotowuję GICLÉE FRAME…"
_CONTROL_COL_MINSIZE = 320
_PROGRESSIVE_BOOT_ENV = "GICLEE_GF_PROGRESSIVE_BOOT"
_EAGER_BOOT_ENV = "GICLEE_GF_EAGER_BOOT"
_GF_SECTION_FIRST_VISIBLE_DEFER_MS = 0
_GF_INIT_REFRESH_LIGHT_DEFER_MS = 0
_GF_MICRO_DEFER_MS = 16
_GF_F1_DEFER_MS = 60
_GF_LAZY_SHELL_ENV = "GICLEE_GF_LAZY_SHELL"
_GF_SHELL_EDITOR_DEFER_MS = 16
_GF_SHELL_CONTROL_DEFER_MS = 30
_GF_CONTROL_LATE_BUILD_DEFER_MS = 120
_GF_SKELETON_SECTION_TEXT = "Ładowanie struktury sekcji…"
_GF_SKELETON_EDITOR_TEXT = "Wybierz sekcję po lewej stronie — edytor jest gotowy."
_GF_SKELETON_CONTROL_TEXT = "Kontrola i readiness pojawią się za chwilę."


# ---------------------------------------------------------------------------
# Module-level env helpers
# ---------------------------------------------------------------------------

def _env_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


def _progressive_boot_enabled() -> bool:
    if _env_enabled(_EAGER_BOOT_ENV, default=False):
        return False
    return _env_enabled(_PROGRESSIVE_BOOT_ENV, default=True)


def _lazy_shell_enabled() -> bool:
    return _env_enabled(_GF_LAZY_SHELL_ENV, default=True)


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class GicleeFrameLifecycleInventoryMixin:
    """GF-M18 — Lifecycle, Inventory & Shell Orchestration boundary.

    Owns: cached-view navigation lifecycle, RAM model lookup/cache rebuild,
    visual-session timing, loading overlay, perceived-ready and atomic-reveal
    orchestration, lazy/eager shell and workspace orchestration, deferred
    sections/control-column startup, bounded inventory reading, light/full
    refresh, progressive section-list bootstrap and final-list completion,
    and compatibility shell helpers.

    Constraints:
    - No __init__; no state initialization.
    - No Tk/CTK base class.
    - No reverse import of gicleeframe_view.py.
    - No filesystem writes, network, subprocess, Shopify, deploy.
    - Does not mutate GicleeFramePageDraft.
    - Does not implement _apply_edit_to_draft.
    """

    # ------------------------------------------------------------------
    # A. Public navigation and cached-view lifecycle
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # B. RAM model cache and timing
    # ------------------------------------------------------------------

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

    def _begin_visual_session(self, *, cache_hit: bool) -> None:
        self._visual_enter_mono = time.perf_counter()
        self._visual_idle_logged = False
        log_event(
            "studio.gicleeframe.visual.enter",
            cache_hit=cache_hit,
            source="view_on_show",
        )

    # ------------------------------------------------------------------
    # C. Atomic reveal, loading overlay and readiness
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # D. Shell/workspace/control orchestration
    # ------------------------------------------------------------------

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

    def _log_visible_prewarm_suppressed(self, *, job: str) -> None:
        log_event(
            "studio.gicleeframe.visible_prewarm.suppressed",
            job=job,
            since_enter_ms=self._since_visual_enter_ms(),
            bootstrap_complete=self._visual_bootstrap_complete,
        )

    def _should_suppress_visible_prewarm(self) -> bool:
        return self._visual_bootstrap_complete

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

    def _build_page_editor_section(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.pack(fill="x", padx=24, pady=(0, 12))
        with span("studio.gicleeframe.build.command_bar"):
            self._build_command_bar(panel)
        with span("studio.gicleeframe.build.workspace"):
            self._build_page_workspace(panel)

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

    def _build_control_column(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        col = ctk.CTkFrame(parent, fg_color="transparent")
        self._build_control_structure_card(col)
        self._build_control_readiness_card(col)
        self._build_safety_card(col)
        return col

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

    # ------------------------------------------------------------------
    # E. Inventory and progressive bootstrap
    # ------------------------------------------------------------------

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
