"""Centrum komponentów — wyszukiwarka, filtry, karty, PPM."""

from __future__ import annotations

import os
import tkinter as tk
import time
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import (
    INLINE_MESSAGE,
    LaunchOutcome,
    component_log_path,
    launch,
    open_component_folder,
)
from giclee_app.studio.background_capabilities import capability_for
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.perf import is_enabled, log_event, span
from giclee_app.studio.state import StudioState

from . import theme
from .widgets import ComponentCardShell, SectionHeader

_SEARCH_DEBOUNCE_MS = 200
# Keep the first real batch intentionally small.
# ComponentCardShell is lightweight; full hydration runs in idle ticks.
_FIRST_VISIBLE_CARD_COUNT = 2
_FIRST_VISIBLE_BUDGET_MS = 350
_CARDS_PER_TICK = 3
_IDLE_BATCH_SIZE = 3
_IDLE_BATCH_DELAY_MS = 0
_IDLE_TICK_BUDGET_MS = 55
_HYDRATE_DELAY_MS = 24
_FIRST_PAINT_DELAY_MS = 16
_SKELETON_COUNT = 6
_GRID_COLS = 3
_LOADING_TEXT = "Ładowanie komponentów…"
_PREPARE_TEXT = "Przygotowuję widok…"
_EMPTY_CATEGORY_TEXT = "Brak komponentów w tej kategorii."
_EMPTY_FILTER_TEXT = "Filtr nie znalazł komponentów."
_MODE_FILTERS = ("all", "subprocess", "url", "inline")
_LOG_TAIL_LINES = 40
_AUTO_HYDRATION_ENV = "GICLEE_HUB_AUTO_HYDRATE"
_HOVER_HYDRATION_ENV = "GICLEE_HUB_HYDRATE_ON_HOVER"
_HYDRATE_ON_HOVER_DELAY_MS = 120


def _env_enabled(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


def _auto_hydration_enabled() -> bool:
    return _env_enabled(_AUTO_HYDRATION_ENV, default=False)


def _hover_hydration_enabled() -> bool:
    # Default OFF — logs show hover hydration can freeze UI for 200ms+.
    return _env_enabled(_HOVER_HYDRATION_ENV, default=False)


def _batch_size_for_start(start_index: int) -> int:
    return _FIRST_VISIBLE_CARD_COUNT if start_index == 0 else _IDLE_BATCH_SIZE


def _batch_delay_for_start(start_index: int) -> int:
    return 0 if start_index == 0 else _IDLE_BATCH_DELAY_MS


def _tick_delay_ms(*, first_visible_phase: bool) -> int:
    return 0 if first_visible_phase else _IDLE_BATCH_DELAY_MS


class ComponentHubView(ctk.CTkScrollableFrame):
    uses_async_first_paint = True

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        category_id: str = "products",
        component_index: StudioComponentIndex | None = None,
        studio_state: StudioState | None = None,
        on_status: Callable[[str], None] | None = None,
        on_open_inline: Callable[[Component, str], None] | None = None,
        on_open_background: Callable[[Component, str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._category_id = category_id
        self._component_index = component_index
        self._studio_state = studio_state
        self._on_status = on_status
        self._on_open_inline = on_open_inline
        self._on_open_background = on_open_background
        self._search_var = tk.StringVar()
        self._mode_filter = tk.StringVar(value="all")
        self._search_debounce_id: str | None = None
        self._grid_frame: ctk.CTkFrame | None = None
        self._header_count: ctk.CTkLabel | None = None
        self._loading_label: ctk.CTkLabel | None = None
        self._empty_label: ctk.CTkLabel | None = None
        self._skeleton_frames: list[ctk.CTkFrame] = []
        self._category_components: list[Component] = []
        self._cards: dict[str, ComponentCardShell] = {}
        self._cards_fully_built = False
        self._render_generation = 0
        self._pending_render_after_id: str | None = None
        self._hydrate_queue: list[str] = []
        self._hydrated_cards: set[str] = set()
        self._hydrate_after_id: str | None = None
        self._hydrate_generation = 0
        self._hydration_queue_started = False
        self._render_started_perf: float | None = None
        self._visual_enter_mono: float | None = None
        self._visual_skeleton_logged = False
        self._visual_first_cards_logged = False
        self._visual_visible_logged = False
        self._visual_full_logged = False
        self._hover_hydration_logged = False
        self._first_visible_cards_built = 0
        self._first_visible_started_mono: float | None = None
        self._filter_cache_key: tuple[object, ...] | None = None
        self._filter_cache_value: list[Component] = []
        self._build_shell()
        self._load_category(category_id)
        log_event(
            "studio.hub.init",
            category=category_id,
            component_count=len(self._category_components),
        )
        # Pierwszy render uruchamia launcher przez on_show() po grid().

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))
        self._section_title = SectionHeader(header, "")
        self._section_title.pack(side="left")
        self._header_count = ctk.CTkLabel(
            header,
            text="",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
        )
        self._header_count.pack(side="left", padx=(12, 0), pady=4)

        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.pack(fill="x", padx=24, pady=(0, 8))
        ctk.CTkEntry(
            search_row,
            placeholder_text="Szukaj po nazwie, opisie, folderze…",
            textvariable=self._search_var,
            height=36,
            fg_color=theme.PanelBg,
            border_color=theme.BorderSubtle,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        filter_row = ctk.CTkFrame(self, fg_color="transparent")
        filter_row.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(
            filter_row,
            text="Tryb:",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        ).pack(side="left", padx=(0, 8))
        self._mode_menu = ctk.CTkOptionMenu(
            filter_row,
            values=list(_MODE_FILTERS),
            variable=self._mode_filter,
            width=120,
            height=28,
            fg_color=theme.PanelBg,
            button_color=theme.CardHover,
            command=self._on_mode_filter_changed,
        )
        self._mode_menu.pack(side="left")

        self._search_var.trace_add("write", self._on_search_changed)

        self._grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._grid_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._loading_label = ctk.CTkLabel(
            self._grid_frame,
            text=_LOADING_TEXT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        )
        self._empty_label = ctk.CTkLabel(
            self._grid_frame,
            text=_EMPTY_CATEGORY_TEXT,
            text_color=theme.TextMuted,
        )
        for i in range(_GRID_COLS):
            self._grid_frame.columnconfigure(i, weight=1, uniform="hub")

        for _ in range(_SKELETON_COUNT):
            sk = self._make_skeleton_card(self._grid_frame)
            self._skeleton_frames.append(sk)
            sk.grid_remove()

    @staticmethod
    def _make_skeleton_card(master: ctk.CTkFrame) -> ctk.CTkFrame:
        """Lekki placeholder — natychmiastowy first paint bez ComponentCard."""
        frame = ctk.CTkFrame(
            master,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=140,
        )
        frame.pack_propagate(False)
        accent = ctk.CTkFrame(
            master=frame,
            width=theme.CardAccentWidth,
            fg_color=theme.BorderSubtle,
            corner_radius=0,
        )
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)
        body = ctk.CTkFrame(frame, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)
        ctk.CTkFrame(
            body, fg_color=theme.PanelBg, height=14, width=28, corner_radius=4,
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkFrame(
            body, fg_color=theme.PanelBg, height=12, width=140, corner_radius=4,
        ).pack(anchor="w", pady=(0, 6))
        ctk.CTkFrame(
            body, fg_color=theme.PanelBg, height=10, width=200, corner_radius=4,
        ).pack(anchor="w", pady=2)
        ctk.CTkFrame(
            body, fg_color=theme.PanelBg, height=10, width=160, corner_radius=4,
        ).pack(anchor="w", pady=2)
        ctk.CTkFrame(
            body, fg_color=theme.AppBg, height=18, width=56, corner_radius=4,
        ).pack(anchor="w", pady=(10, 0))
        return frame

    def on_hide(self) -> None:
        """Wywoływane przez launcher przy grid_remove — anuluj pending after()."""
        self._cancel_pending_render()

    def on_show(self, *, cache_hit: bool = False) -> None:
        """Cached hub — natychmiast; nowy / przerwany render — skeleton + batch."""
        self._begin_visual_session()
        log_event(
            "studio.hub.lifecycle",
            category=self._category_id,
            cache_hit=cache_hit,
            cards_fully_built=self._cards_fully_built,
            cached_cards=len(self._cards),
        )
        log_event(
            "studio.hub.on_show",
            category=self._category_id,
            fully_built=self._cards_fully_built,
            cached_cards=len(self._cards),
            cache_hit=cache_hit,
        )
        if not self._hover_hydration_logged:
            self._hover_hydration_logged = True
            log_event(
                "studio.hub.hydration.hover_disabled_default",
                category=self._category_id,
                enabled=_hover_hydration_enabled(),
            )
        if self._cards_fully_built:
            self._show_skeleton(False)
            self._show_loading(False)
            self._apply_filter_grid()
            if self._cards and not any(c.winfo_ismapped() for c in self._cards.values()):
                self._apply_filter_grid()
            self._mark_visual_visible_ready()
            self._mark_visual_full_ready()
            self._sync_hydrated_state_from_cards()
            if _auto_hydration_enabled():
                self._schedule_hydrate_pump()
            return
        self._begin_first_paint()

    def _since_visual_enter_ms(self) -> float | None:
        if self._visual_enter_mono is None:
            return None
        return round((time.perf_counter() - self._visual_enter_mono) * 1000, 2)

    def _begin_visual_session(self) -> None:
        self._visual_enter_mono = time.perf_counter()
        self._visual_skeleton_logged = False
        self._visual_first_cards_logged = False
        self._visual_visible_logged = False
        self._visual_full_logged = False
        self._hover_hydration_logged = False
        log_event(
            "studio.hub.visual.enter",
            category=self._category_id,
            cards_fully_built=self._cards_fully_built,
            cached_cards=len(self._cards),
        )

    def _mark_visual_skeleton_ready(self) -> None:
        if self._visual_skeleton_logged:
            return
        self._visual_skeleton_logged = True
        log_event(
            "studio.hub.visual.skeleton_ready",
            category=self._category_id,
            since_enter_ms=self._since_visual_enter_ms(),
        )

    def _mark_visual_first_cards_ready(self, *, created: int) -> None:
        if self._visual_first_cards_logged:
            return
        self._visual_first_cards_logged = True
        log_event(
            "studio.hub.visual.first_cards_ready",
            category=self._category_id,
            since_enter_ms=self._since_visual_enter_ms(),
            cards_created=created,
            total_cards=len(self._category_components),
        )

    def _mark_visual_visible_ready(self) -> None:
        if self._visual_visible_logged:
            return
        self._visual_visible_logged = True
        log_event(
            "studio.hub.visual.visible_ready",
            category=self._category_id,
            since_enter_ms=self._since_visual_enter_ms(),
            cached_cards=len(self._cards),
            cards_fully_built=self._cards_fully_built,
        )

    def _mark_visual_full_ready(self) -> None:
        if self._visual_full_logged:
            return
        self._visual_full_logged = True
        log_event(
            "studio.hub.visual.full_ready",
            category=self._category_id,
            since_enter_ms=self._since_visual_enter_ms(),
            total_cards=len(self._category_components),
            cached_cards=len(self._cards),
        )

    def destroy(self) -> None:
        self._cancel_pending_render()
        if self._search_debounce_id is not None:
            try:
                self.after_cancel(self._search_debounce_id)
            except (tk.TclError, ValueError):
                pass
            self._search_debounce_id = None
        super().destroy()

    def _cancel_pending_render(self) -> None:
        self._render_generation += 1
        self._hydrate_generation += 1
        if self._pending_render_after_id is not None:
            try:
                self.after_cancel(self._pending_render_after_id)
            except (tk.TclError, ValueError):
                pass
            self._pending_render_after_id = None
        if self._hydrate_after_id is not None:
            try:
                self.after_cancel(self._hydrate_after_id)
            except (tk.TclError, ValueError):
                pass
            self._hydrate_after_id = None

    def _load_category(self, category_id: str) -> None:
        self._category_id = category_id
        self._section_title.configure(text=category_label(category_id))
        if self._component_index is not None:
            self._category_components = self._component_index.components_for_category(category_id)
        else:
            from giclee_app.studio.categories import components_for_category

            self._category_components = components_for_category(category_id, include_hidden=True)
        self._apply_category_sort()
        self._invalidate_filter_cache()
        self._search_var.set("")

    def _apply_category_sort(self) -> None:
        """Pinned → recent → default przed batch build i po zmianie pin."""
        if self._studio_state is not None and self._category_components:
            self._category_components = self._studio_state.sorted_components(
                list(self._category_components),
            )

    def _on_mode_filter_changed(self, _value: str) -> None:
        self._invalidate_filter_cache()
        self._apply_filter_grid(partial=not self._cards_fully_built)

    def _on_search_changed(self, *_args: object) -> None:
        if self._search_debounce_id is not None:
            try:
                self.after_cancel(self._search_debounce_id)
            except (tk.TclError, ValueError):
                pass
        self._search_debounce_id = self.after(_SEARCH_DEBOUNCE_MS, self._debounced_filter)

    def _debounced_filter(self) -> None:
        self._search_debounce_id = None
        self._invalidate_filter_cache()
        self._apply_filter_grid(partial=not self._cards_fully_built)

    def _show_skeleton(self, visible: bool) -> None:
        for i, sk in enumerate(self._skeleton_frames):
            if visible:
                row, col = divmod(i, _GRID_COLS)
                sk.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            else:
                sk.grid_remove()

    def _sync_skeleton_slots(self) -> None:
        """Ukryj skeleton tylko pod slotami z realnymi kartami; reszta zostaje."""
        if self._cards_fully_built:
            self._show_skeleton(False)
            return
        mapped = self._count_mapped_visible_cards()
        for i, sk in enumerate(self._skeleton_frames):
            if i < mapped:
                sk.grid_remove()
            else:
                row, col = divmod(i, _GRID_COLS)
                sk.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _count_mapped_visible_cards(self) -> int:
        count = 0
        for comp in self._filtered_components():
            card = self._cards.get(comp.folder_name)
            if card is not None and card.winfo_ismapped():
                count += 1
        return count

    def _create_shell_for_component(self, comp: Component) -> ComponentCardShell:
        if self._grid_frame is None:
            raise RuntimeError("grid frame not initialized")
        started = time.perf_counter()
        shell = ComponentCardShell(
            self._grid_frame,
            comp,
            on_click=self._on_card_click,
            on_right_click=self._on_card_right,
            on_open_background=self._on_background_click if self._on_open_background else None,
            on_request_hydration=self.request_card_hydration if _hover_hydration_enabled() else None,
            pinned=self._is_pinned(comp.folder_name),
        )
        self._cards[comp.folder_name] = shell
        shell.grid_remove()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.hub.card.shell_created",
            category=self._category_id,
            folder=comp.folder_name,
            phase="shell",
            elapsed_ms=elapsed_ms,
        )
        self._enqueue_hydration(comp.folder_name)
        return shell

    def _sync_hydrated_state_from_cards(self) -> None:
        for folder, card in self._cards.items():
            if card.is_fully_hydrated:
                self._hydrated_cards.add(folder)

    def _enqueue_hydration(self, folder: str) -> None:
        if not _auto_hydration_enabled():
            log_event(
                "studio.hub.hydration.auto_disabled",
                category=self._category_id,
                folder=folder,
            )
            return

        self.request_card_hydration(folder, source="auto")

    def request_card_hydration(self, folder: str, *, source: str = "hover") -> None:
        if not _hover_hydration_enabled() and source == "hover":
            log_event(
                "studio.hub.hydration.hover_disabled",
                category=self._category_id,
                folder=folder,
            )
            return

        if folder in self._hydrated_cards or folder in self._hydrate_queue:
            return
        if folder not in self._cards:
            return

        self._hydrate_queue.insert(0, folder)
        if not self._hydration_queue_started:
            self._hydration_queue_started = True
            log_event(
                "studio.hub.hydration.queue_start",
                category=self._category_id,
                queue_remaining=len(self._hydrate_queue),
            )
        log_event(
            "studio.hub.card.hydrate_requested",
            category=self._category_id,
            folder=folder,
            source=source,
            queue_remaining=len(self._hydrate_queue),
        )
        delay = _HYDRATE_ON_HOVER_DELAY_MS if source == "hover" else _HYDRATE_DELAY_MS
        self._schedule_hydrate_pump(delay_ms=delay)

    def _schedule_hydrate_pump(self, *, delay_ms: int | None = None) -> None:
        if self._hydrate_after_id is not None:
            return
        if not self._hydrate_queue:
            return
        delay = _HYDRATE_DELAY_MS if delay_ms is None else delay_ms
        self._hydrate_after_id = self.after(delay, self._hydrate_pump)

    def _visible_folders(self) -> set[str]:
        return {c.folder_name for c in self._filtered_components()}

    def _prioritize_hydrate_queue(self) -> None:
        visible = self._visible_folders()
        if not visible:
            return
        front = [f for f in self._hydrate_queue if f in visible]
        back = [f for f in self._hydrate_queue if f not in visible]
        self._hydrate_queue = front + back

    def _requeue_visible_hydrations(self) -> None:
        if not _auto_hydration_enabled():
            return
        visible = self._visible_folders()
        for folder in visible:
            if folder in self._cards and folder not in self._hydrated_cards:
                if folder not in self._hydrate_queue:
                    self._hydrate_queue.insert(0, folder)
        self._schedule_hydrate_pump()

    def _hydrate_pump(self) -> None:
        self._hydrate_after_id = None
        gen = self._hydrate_generation

        self._prioritize_hydrate_queue()
        while self._hydrate_queue:
            if gen != self._hydrate_generation:
                return
            folder = self._hydrate_queue[0]
            card = self._cards.get(folder)
            if card is None:
                self._hydrate_queue.pop(0)
                continue
            if card.is_fully_hydrated:
                self._hydrated_cards.add(folder)
                self._hydrate_queue.pop(0)
                continue

            visible = folder in self._visible_folders()
            if not visible and self._filter_is_active():
                log_event(
                    "studio.hub.card.hydrate_deferred_hidden",
                    category=self._category_id,
                    folder=folder,
                    visible=False,
                    queue_remaining=len(self._hydrate_queue),
                )
                self._hydrate_queue.pop(0)
                continue

            stage = card.hydration_stage()
            next_stage = stage + 1
            log_event(
                "studio.hub.card.hydrate_start",
                category=self._category_id,
                folder=folder,
                stage=next_stage,
                visible=visible,
                queue_remaining=len(self._hydrate_queue),
            )
            started = time.perf_counter()
            if next_stage == 1:
                card.hydrate_stage_1()
            elif next_stage == 2:
                card.hydrate_stage_2()
            else:
                card.hydrate_stage_3()
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

            if card.is_fully_hydrated:
                self._hydrated_cards.add(folder)
                self._hydrate_queue.pop(0)
                log_event(
                    "studio.hub.card.hydrate_done",
                    category=self._category_id,
                    folder=folder,
                    stage=3,
                    elapsed_ms=elapsed_ms,
                    hydrated=True,
                    queue_remaining=len(self._hydrate_queue),
                )
                log_event(
                    "studio.hub.card.full_created",
                    category=self._category_id,
                    folder=folder,
                    phase="hydrated",
                    elapsed_ms=elapsed_ms,
                )
            else:
                log_event(
                    "studio.hub.card.hydrate_done",
                    category=self._category_id,
                    folder=folder,
                    stage=next_stage,
                    elapsed_ms=elapsed_ms,
                    hydrated=False,
                    queue_remaining=len(self._hydrate_queue),
                )
            break

        if self._hydrate_queue:
            self._schedule_hydrate_pump()
        elif self._hydration_queue_started:
            log_event(
                "studio.hub.hydration.queue_done",
                category=self._category_id,
                hydrated=len(self._hydrated_cards),
            )

    def _show_loading(self, visible: bool) -> None:
        if self._loading_label is None:
            return
        if visible:
            self._loading_label.grid(row=0, column=0, columnspan=_GRID_COLS, pady=(0, 8), sticky="w")
        else:
            self._loading_label.grid_remove()

    def _show_empty(self, visible: bool) -> None:
        if self._empty_label is None:
            return
        if visible:
            self._empty_label.grid(row=0, column=0, columnspan=_GRID_COLS, pady=40)
        else:
            self._empty_label.grid_remove()

    def _begin_first_paint(self) -> None:
        """Skeleton natychmiast, budowa kart dopiero po jednej klatce."""
        with span(
            "studio.hub.first_paint",
            category=self._category_id,
            component_count=len(self._category_components),
        ):
            self._cancel_pending_render()
            gen = self._render_generation

            if not self._category_components:
                self._cards_fully_built = True
                self._show_skeleton(False)
                self._show_loading(False)
                self._show_empty(True)
                if self._header_count:
                    self._header_count.configure(text="0 komponentów")
                for card in self._cards.values():
                    card.grid_remove()
                self._mark_visual_full_ready()
                return

            self._show_empty(False)
            self._show_loading(True)
            self._show_skeleton(True)
            self._mark_visual_skeleton_ready()
            if self._header_count:
                self._header_count.configure(text=_PREPARE_TEXT)
            self._first_visible_cards_built = 0
            self._first_visible_started_mono = None
            self._hydrate_queue.clear()
            self._hydrated_cards.clear()
            self._hydration_queue_started = False
            self._pending_render_after_id = self.after(
                _FIRST_PAINT_DELAY_MS,
                lambda g=gen: self._start_batch_render(g),
            )

    def _start_batch_render(self, gen: int) -> None:
        self._pending_render_after_id = None
        if gen != self._render_generation:
            return
        self._show_loading(False)
        if is_enabled():
            self._render_started_perf = time.perf_counter()
        log_event(
            "studio.hub.batch_render.start",
            category=self._category_id,
            total_cards=len(self._category_components),
        )
        self._batch_build_cards(gen, 0)

    def _is_first_visible_phase(self) -> bool:
        if self._first_visible_cards_built >= _FIRST_VISIBLE_CARD_COUNT:
            return False
        if self._first_visible_cards_built >= 1 and self._first_visible_started_mono is not None:
            elapsed_ms = (time.perf_counter() - self._first_visible_started_mono) * 1000
            if elapsed_ms >= _FIRST_VISIBLE_BUDGET_MS:
                return False
        return True

    def _finish_batch_render(self, gen: int, comps: list[Component]) -> None:
        self._pending_render_after_id = None
        self._cards_fully_built = True
        self._show_skeleton(False)
        self._apply_filter_grid(gen)
        elapsed_ms = None
        if self._render_started_perf is not None:
            elapsed_ms = (time.perf_counter() - self._render_started_perf) * 1000
            self._render_started_perf = None
        self._mark_visual_full_ready()
        log_event(
            "studio.hub.batch_render.complete",
            category=self._category_id,
            total_cards=len(comps),
            elapsed_ms=elapsed_ms,
        )
        if _auto_hydration_enabled():
            self._schedule_hydrate_pump()

    def _batch_build_cards(self, gen: int, start_index: int) -> None:
        if gen != self._render_generation or self._grid_frame is None:
            return

        comps = self._category_components
        i = start_index

        while i < len(comps) and comps[i].folder_name in self._cards:
            i += 1

        if i >= len(comps):
            self._finish_batch_render(gen, comps)
            return

        batch_started = time.perf_counter()
        in_first_visible = self._is_first_visible_phase()
        phase = "first_visible" if in_first_visible else "idle"

        max_cards = _FIRST_VISIBLE_CARD_COUNT if in_first_visible else _IDLE_BATCH_SIZE
        budget_ms = _FIRST_VISIBLE_BUDGET_MS if in_first_visible else _IDLE_TICK_BUDGET_MS

        new_folders: list[str] = []
        created = 0
        first_index = i

        while i < len(comps) and created < max_cards:
            if gen != self._render_generation:
                return

            comp = comps[i]
            if comp.folder_name in self._cards:
                i += 1
                continue

            self._create_shell_for_component(comp)
            new_folders.append(comp.folder_name)
            created += 1
            i += 1

            if in_first_visible:
                if self._first_visible_started_mono is None:
                    self._first_visible_started_mono = time.perf_counter()
                self._first_visible_cards_built += 1

            elapsed_ms_now = (time.perf_counter() - batch_started) * 1000
            if elapsed_ms_now >= budget_ms:
                break

        if created <= 0:
            self._finish_batch_render(gen, comps)
            return

        end = i

        if phase == "first_visible":
            self._apply_filter_grid(gen, partial=True)
            if not self._visual_first_cards_logged:
                self._mark_visual_first_cards_ready(created=created)
                self._mark_visual_visible_ready()
        elif self._filter_is_active():
            self._apply_filter_grid(gen, partial=True)
        else:
            placed = self._append_cards_to_grid(new_folders, gen)
            log_event(
                "studio.hub.grid.incremental",
                category=self._category_id,
                placed=placed,
                start_index=first_index,
                created=created,
            )

        self._sync_skeleton_slots()

        elapsed_ms = round((time.perf_counter() - batch_started) * 1000, 2)
        avg_card_ms = round(elapsed_ms / max(created, 1), 2)

        log_event(
            "studio.hub.batch.created",
            category=self._category_id,
            phase=phase,
            start_index=first_index,
            end_index=end,
            created=created,
            elapsed_ms=elapsed_ms,
            avg_card_ms=avg_card_ms,
            total_cards=len(comps),
            batch_size=max_cards,
            cards_per_tick=max_cards,
            tick_budget_ms=budget_ms,
        )

        next_start = end
        while next_start < len(comps) and comps[next_start].folder_name in self._cards:
            next_start += 1

        if next_start < len(comps):
            delay = _tick_delay_ms(first_visible_phase=self._is_first_visible_phase())
            log_event(
                "studio.hub.batch.schedule_next",
                category=self._category_id,
                delay_ms=delay,
                next_start=next_start,
                first_visible_phase=self._is_first_visible_phase(),
            )
            self._pending_render_after_id = self.after(
                delay,
                lambda g=gen, n=next_start: self._batch_build_cards(g, n),
            )
            return

        self._finish_batch_render(gen, comps)

    def _is_pinned(self, folder_name: str) -> bool:
        if self._studio_state is None:
            return False
        return self._studio_state.is_pinned(folder_name)

    def _invalidate_filter_cache(self) -> None:
        self._filter_cache_key = None
        self._filter_cache_value = []

    def _filtered_components(self) -> list[Component]:
        mode = self._mode_filter.get().strip().lower()
        q = self._search_var.get().strip().lower()

        pinned: tuple[str, ...] = ()
        recent: tuple[str, ...] = ()
        if self._studio_state is not None:
            pinned = tuple(self._studio_state.pinned)
            recent = tuple(self._studio_state.recent_folder_order())

        key: tuple[object, ...] = (
            self._category_id,
            mode,
            q,
            tuple(c.folder_name for c in self._category_components),
            pinned,
            recent,
        )

        if self._filter_cache_key == key:
            return self._filter_cache_value

        comps = list(self._category_components)

        if mode and mode != "all":
            comps = [c for c in comps if c.mode == mode]

        if q:
            out: list[Component] = []
            for c in comps:
                hay = f"{c.name} {c.description} {c.folder_name}".lower()
                if q in hay:
                    out.append(c)
            comps = out

        if self._studio_state is not None:
            comps = self._studio_state.sorted_components(comps)

        self._filter_cache_key = key
        self._filter_cache_value = comps
        return comps

    def _filter_is_active(self) -> bool:
        mode = self._mode_filter.get().strip().lower()
        if mode and mode != "all":
            return True
        return bool(self._search_var.get().strip())

    def _append_cards_to_grid(self, new_folders: list[str], gen: int) -> int:
        if gen != self._render_generation or self._grid_frame is None:
            return 0

        visible = self._filtered_components()
        visible_folders = {c.folder_name for c in visible}

        grid_row = 0
        for comp in visible:
            card = self._cards.get(comp.folder_name)
            if card is not None and card.winfo_ismapped():
                grid_row += 1

        placed = 0
        for folder in new_folders:
            if folder not in visible_folders:
                continue
            card = self._cards.get(folder)
            if card is None or card.winfo_ismapped():
                continue
            row, col = divmod(grid_row, _GRID_COLS)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            grid_row += 1
            placed += 1

        if self._header_count and not self._cards_fully_built:
            built = sum(
                1
                for c in visible
                if c.folder_name in self._cards and self._cards[c.folder_name].winfo_ismapped()
            )
            self._header_count.configure(text=f"{built} / {len(visible)} komponentów")

        return placed

    def _apply_filter_grid(self, gen: int | None = None, *, partial: bool = False) -> None:
        if gen is not None and gen != self._render_generation:
            return
        if self._grid_frame is None:
            return
        if not partial and not self._cards_fully_built:
            return

        visible = self._filtered_components()
        visible_folders = {c.folder_name for c in visible}

        if self._header_count:
            if partial and not self._cards_fully_built:
                built = sum(1 for c in visible if c.folder_name in self._cards)
                self._header_count.configure(text=f"{built} / {len(visible)} komponentów")
            else:
                self._header_count.configure(text=f"{len(visible)} komponentów")

        self._show_loading(False)

        if not visible:
            for card in self._cards.values():
                card.grid_remove()
            if partial or self._cards_fully_built:
                self._show_skeleton(False)
                self._show_empty(True)
                if self._empty_label is not None:
                    if not self._category_components:
                        self._empty_label.configure(text=_EMPTY_CATEGORY_TEXT)
                    else:
                        self._empty_label.configure(text=_EMPTY_FILTER_TEXT)
            return

        self._show_empty(False)
        grid_row = 0
        for comp in visible:
            card = self._cards.get(comp.folder_name)
            if card is None:
                if partial:
                    continue
                continue
            row, col = divmod(grid_row, _GRID_COLS)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            grid_row += 1

        for folder, card in self._cards.items():
            if folder not in visible_folders:
                card.grid_remove()

        if partial and not self._cards_fully_built:
            self._sync_skeleton_slots()
            self._requeue_visible_hydrations()

    def _on_background_click(self, comp: Component) -> None:
        if capability_for(comp.folder_name) is None:
            return
        if self._on_open_background is not None:
            self._on_open_background(comp, self._category_id)

    def _on_card_click(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        cap = capability_for(comp.folder_name)
        if cap is not None and callable(self._on_status):
            self._on_status(f"Tło: {cap.label} — {cap.source_hint} (read-only)")
        if comp.mode == "inline":
            if self._on_open_inline is not None:
                self._on_open_inline(comp, self._category_id)
            else:
                messagebox.showinfo(comp.name, INLINE_MESSAGE, parent=root)
            return
        result = launch(comp, on_status=self._on_status)
        if result.outcome == LaunchOutcome.OK:
            if self._studio_state is not None:
                self._studio_state.record_launch(comp)
                self._studio_state.save()
                self._invalidate_filter_cache()
                self._apply_filter_grid()
        elif result.outcome in (LaunchOutcome.ERROR, LaunchOutcome.NO_PYTHON, LaunchOutcome.NO_URL):
            messagebox.showerror(comp.name, result.message, parent=root)

    @staticmethod
    def _read_log_tail(path: Path, max_lines: int = _LOG_TAIL_LINES) -> str:
        if not path.is_file():
            return "Brak pliku logu dla tego komponentu."
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if not lines:
                return "(pusty log)"
            return "\n".join(lines[-max_lines:])
        except OSError as exc:
            return f"Nie można odczytać logu: {exc}"

    def _show_log_dialog(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        text = self._read_log_tail(component_log_path(comp))
        win = ctk.CTkToplevel(root)
        win.title(f"Log — {comp.name}")
        win.geometry("640x360")
        box = ctk.CTkTextbox(
            win,
            font=theme.get_font(10, family=theme.FontMono[0]),
            fg_color=theme.PanelBg,
        )
        box.pack(fill="both", expand=True, padx=12, pady=12)
        box.insert("1.0", text)
        box.configure(state="disabled")

    def _copy_module_path(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        module = f"Komponenty.{comp.folder_name}"
        try:
            root.clipboard_clear()
            root.clipboard_append(module)
            if callable(self._on_status):
                self._on_status(f"Skopiowano: {module}")
        except tk.TclError:
            messagebox.showinfo(comp.name, module, parent=root)

    def _toggle_pin(self, comp: Component) -> None:
        if self._studio_state is None:
            return
        pinned = self._studio_state.toggle_pin(comp.folder_name)
        self._studio_state.save()
        card = self._cards.get(comp.folder_name)
        if card is not None:
            card.set_pinned(pinned)
        self._apply_category_sort()
        self._invalidate_filter_cache()
        self._apply_filter_grid()

    def _on_card_right(self, comp: Component, event: object) -> None:
        root = self.winfo_toplevel()
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="Uruchom", command=lambda: self._on_card_click(comp))
        menu.add_command(label="Otwórz folder", command=lambda: open_component_folder(comp))
        menu.add_command(label="Pokaż log", command=lambda: self._show_log_dialog(comp))
        menu.add_command(label="Kopiuj moduł", command=lambda: self._copy_module_path(comp))
        pin_label = "Odepnij" if self._is_pinned(comp.folder_name) else "Przypnij"
        menu.add_command(label=pin_label, command=lambda: self._toggle_pin(comp))
        if comp.mode == "inline":
            menu.add_separator()
            menu.add_command(
                label="Otwórz inline w Studio",
                command=lambda: self._on_card_click(comp),
            )
            menu.add_command(
                label="Inline info",
                command=lambda: messagebox.showinfo(
                    comp.name,
                    f"Tryb: inline\nModuł: {comp.view_module_path}\n"
                    "Wymaga build_view(parent, on_back) w view.py.",
                    parent=root,
                ),
            )
        try:
            if hasattr(event, "x_root") and hasattr(event, "y_root"):
                menu.tk_popup(int(event.x_root), int(event.y_root))  # type: ignore[attr-defined]
            else:
                menu.tk_popup(root.winfo_pointerx(), root.winfo_pointery())
        finally:
            menu.grab_release()
