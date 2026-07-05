"""Centrum komponentów — wyszukiwarka i karty."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import (
    INLINE_MESSAGE,
    LaunchOutcome,
    launch,
    open_component_folder,
)
from giclee_app.studio.categories import category_label
from giclee_app.studio.component_index import StudioComponentIndex

from . import theme
from .widgets import ComponentCard, SectionHeader

_SEARCH_DEBOUNCE_MS = 200
_BATCH_SIZE = 2
_FIRST_PAINT_DELAY_MS = 16
_SKELETON_COUNT = 6
_GRID_COLS = 3
_LOADING_TEXT = "Ładowanie komponentów…"
_PREPARE_TEXT = "Przygotowuję widok…"
_EMPTY_TEXT = "Brak komponentów w tej kategorii."


class ComponentHubView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        category_id: str = "products",
        component_index: StudioComponentIndex | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._category_id = category_id
        self._component_index = component_index
        self._on_status = on_status
        self._search_var = tk.StringVar()
        self._search_debounce_id: str | None = None
        self._grid_frame: ctk.CTkFrame | None = None
        self._header_count: ctk.CTkLabel | None = None
        self._loading_label: ctk.CTkLabel | None = None
        self._empty_label: ctk.CTkLabel | None = None
        self._skeleton_frames: list[ctk.CTkFrame] = []
        self._category_components: list[Component] = []
        self._cards: dict[str, ComponentCard] = {}
        self._cards_fully_built = False
        self._render_generation = 0
        self._pending_render_after_id: str | None = None
        self._build_shell()
        self._load_category(category_id)
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
        search_row.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkEntry(
            search_row,
            placeholder_text="Szukaj po nazwie, opisie, folderze…",
            textvariable=self._search_var,
            height=36,
            fg_color=theme.PanelBg,
            border_color=theme.BorderSubtle,
        ).pack(fill="x")

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
            text=_EMPTY_TEXT,
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

    def on_show(self) -> None:
        """Cached hub — natychmiast; nowy — skeleton + opóźnienie jednej klatki."""
        if self._cards_fully_built:
            self._show_skeleton(False)
            self._show_loading(False)
            self._apply_filter_grid()
            return
        self._begin_first_paint()

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
        if self._pending_render_after_id is not None:
            try:
                self.after_cancel(self._pending_render_after_id)
            except (tk.TclError, ValueError):
                pass
            self._pending_render_after_id = None

    def _load_category(self, category_id: str) -> None:
        self._category_id = category_id
        self._section_title.configure(text=category_label(category_id))
        if self._component_index is not None:
            self._category_components = self._component_index.components_for_category(category_id)
        else:
            from giclee_app.studio.categories import components_for_category

            self._category_components = components_for_category(category_id, include_hidden=True)
        self._search_var.set("")

    def _on_search_changed(self, *_args: object) -> None:
        if self._search_debounce_id is not None:
            try:
                self.after_cancel(self._search_debounce_id)
            except (tk.TclError, ValueError):
                pass
        self._search_debounce_id = self.after(_SEARCH_DEBOUNCE_MS, self._debounced_filter)

    def _debounced_filter(self) -> None:
        self._search_debounce_id = None
        self._apply_filter_grid()

    def _show_skeleton(self, visible: bool) -> None:
        for i, sk in enumerate(self._skeleton_frames):
            if visible:
                row, col = divmod(i, _GRID_COLS)
                sk.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            else:
                sk.grid_remove()

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
            return

        self._show_empty(False)
        self._show_loading(True)
        self._show_skeleton(True)
        if self._header_count:
            self._header_count.configure(text=_PREPARE_TEXT)
        self.update_idletasks()
        self._pending_render_after_id = self.after(
            _FIRST_PAINT_DELAY_MS,
            lambda g=gen: self._start_batch_render(g),
        )

    def _start_batch_render(self, gen: int) -> None:
        self._pending_render_after_id = None
        if gen != self._render_generation:
            return
        self._show_loading(False)
        self._batch_build_cards(gen, 0)

    def _batch_build_cards(self, gen: int, start_index: int) -> None:
        if gen != self._render_generation or self._grid_frame is None:
            return

        comps = self._category_components
        while start_index < len(comps) and comps[start_index].folder_name in self._cards:
            start_index += 1

        end = min(start_index + _BATCH_SIZE, len(comps))
        created = 0
        for i in range(start_index, end):
            if gen != self._render_generation:
                return
            comp = comps[i]
            if comp.folder_name in self._cards:
                continue
            card = ComponentCard(
                self._grid_frame,
                comp,
                on_click=self._on_card_click,
                on_right_click=self._on_card_right,
            )
            self._cards[comp.folder_name] = card
            card.grid_remove()
            created += 1

        if created > 0:
            self._show_skeleton(False)
            self._apply_filter_grid(gen, partial=True)

        next_start = end
        while next_start < len(comps) and comps[next_start].folder_name in self._cards:
            next_start += 1

        if next_start < len(comps):
            self._pending_render_after_id = self.after(
                1,
                lambda g=gen, n=next_start: self._batch_build_cards(g, n),
            )
            return

        self._pending_render_after_id = None
        self._cards_fully_built = True
        self._show_skeleton(False)
        self._apply_filter_grid(gen)

    def _filtered_components(self) -> list[Component]:
        q = self._search_var.get().strip().lower()
        if not q:
            return self._category_components
        out: list[Component] = []
        for c in self._category_components:
            hay = f"{c.name} {c.description} {c.folder_name}".lower()
            if q in hay:
                out.append(c)
        return out

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
            if self._cards_fully_built:
                for card in self._cards.values():
                    card.grid_remove()
                self._show_skeleton(False)
                self._show_empty(True)
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

    def _on_card_click(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        result = launch(comp, on_status=self._on_status)
        if result.outcome == LaunchOutcome.BLOCKED_INLINE:
            messagebox.showinfo(comp.name, INLINE_MESSAGE, parent=root)
        elif result.outcome in (LaunchOutcome.ERROR, LaunchOutcome.NO_PYTHON, LaunchOutcome.NO_URL):
            messagebox.showerror(comp.name, result.message, parent=root)

    def _on_card_right(self, comp: Component, _event: object) -> None:
        open_component_folder(comp)
