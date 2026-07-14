"""GICLÉE FRAME™ — section list column shell and static first-visible lane."""

from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    SECTION_LIST_DRAG_HINT,
    SECTION_LIST_TITLE,
)
from giclee_app.studio.perf import log_event, span

from . import theme
from .gicleeframe_view_primitives import (
    _CARD_PAD_X,
    _make_card_title,
    _make_gf_card,
)

_SECTION_PLACEHOLDER = "— wybierz sekcję —"
_SECTION_LIST_WIDTH = 320
_SECTION_LIST_HEIGHT = 520
_SECTION_LIST_LOADING_TEXT = "Ładowanie struktury sekcji…"
_GF_SECTION_FIRST_BATCH_SIZE = 6
_GF_SECTIONS_COLUMN_EARLY_DEFER_MS = 0
_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS = 40
_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS = 800

__all__ = (
    "GicleeFrameSectionListShellMixin",
    "_GF_SECTION_FIRST_BATCH_SIZE",
    "_GF_SECTIONS_COLUMN_EARLY_DEFER_MS",
    "_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS",
    "_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS",
    "_SECTION_LIST_HEIGHT",
    "_SECTION_LIST_LOADING_TEXT",
    "_SECTION_LIST_WIDTH",
    "_SECTION_PLACEHOLDER",
)


class GicleeFrameSectionListShellMixin:
    """Section-list column shell, static first-visible lane and scroll-upgrade scheduling."""

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
