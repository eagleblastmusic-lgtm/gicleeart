"""GICLÉE FRAME™ — selection orchestration, priority lane and atomic swap."""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable

from giclee_app.studio.gicleeframe_page_draft import MergedPageElement
from giclee_app.studio.perf import log_event, span

_GF_ATOMIC_SWAP_STATUS_TEXT = "Przygotowuję sekcję…"

_GF_SELECT_POPULATE_DEFER_MS = 0

_GF_SELECTION_PRIORITY_WINDOW_MS = 200

_GF_SELECTION_PRIORITY_YIELD_DEFER_MS = 60



__all__ = (
    "GicleeFrameSelectionOrchestrationMixin",
    "_GF_ATOMIC_SWAP_STATUS_TEXT",
    "_GF_SELECTION_PRIORITY_WINDOW_MS",
    "_GF_SELECTION_PRIORITY_YIELD_DEFER_MS",
    "_GF_SELECT_POPULATE_DEFER_MS",
)


class GicleeFrameSelectionOrchestrationMixin:
    """Selection click timing, priority lane, populate scheduling and atomic swap."""

    def _since_selection_click_ms(self) -> float | None:
        if self._selection_click_mono is None:
            return None
        return round((time.perf_counter() - self._selection_click_mono) * 1000, 2)

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
            progressive_boot=self._progressive_boot_enabled_for_selection(),
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
