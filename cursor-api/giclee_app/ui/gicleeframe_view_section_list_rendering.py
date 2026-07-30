"""GICLÉE FRAME™ — section list rendering and row construction."""

from __future__ import annotations

import time
import tkinter as tk

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import SectionDropdownOption
from giclee_app.studio.perf import log_event, span

from . import theme
from .gicleeframe_view_models import _ellipsize, _section_kind_copy
from .gicleeframe_view_primitives import _GF_FIELD, _GF_GOLD_SOFT, _GF_MUTED
from .gicleeframe_view_film_scroll_context import (
    bind_section_list_context_target,
)
from .gicleeframe_view_section_list_shell import (
    _GF_SECTION_FIRST_BATCH_SIZE,
    _SECTION_PLACEHOLDER,
)

_SECTION_ROW_GRIP = "⋮"
_SECTION_ROW_HEIGHT = 64
_GF_SECTION_BATCH_SIZE = 8
_GF_SECTION_BATCH_DELAY_MS = 0

__all__ = (
    "GicleeFrameSectionListRenderingMixin",
    "_GF_SECTION_BATCH_DELAY_MS",
    "_GF_SECTION_BATCH_SIZE",
    "_SECTION_ROW_GRIP",
    "_SECTION_ROW_HEIGHT",
)


class GicleeFrameSectionListRenderingMixin:
    """Full/incremental section-list rebuild, batching and row construction."""

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
            bind_section_list_context_target(self, target, element_id)

    def _build_section_row(self, index: int, element_id: str, label: str) -> None:
        self._create_section_list_row(index, element_id, label)

    def _render_section_menu(self) -> None:
        self._render_section_list()
