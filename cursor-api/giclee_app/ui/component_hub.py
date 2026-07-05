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
        self._category_components: list[Component] = []
        self._build_shell()
        self.set_category(category_id)

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

    def _on_search_changed(self, *_args: object) -> None:
        if self._search_debounce_id is not None:
            try:
                self.after_cancel(self._search_debounce_id)
            except (tk.TclError, ValueError):
                pass
        self._search_debounce_id = self.after(_SEARCH_DEBOUNCE_MS, self._debounced_render)

    def _debounced_render(self) -> None:
        self._search_debounce_id = None
        self._render_grid()

    def set_category(self, category_id: str) -> None:
        self._category_id = category_id
        title = category_label(category_id)
        self._section_title.configure(text=title)
        if self._component_index is not None:
            self._category_components = self._component_index.components_for_category(category_id)
        else:
            from giclee_app.studio.categories import components_for_category

            self._category_components = components_for_category(category_id, include_hidden=True)
        self._search_var.set("")
        self._render_grid()

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

    def _render_grid(self) -> None:
        if self._grid_frame is None:
            return
        for child in self._grid_frame.winfo_children():
            child.destroy()

        comps = self._filtered_components()
        if self._header_count:
            self._header_count.configure(text=f"{len(comps)} komponentów")

        if not comps:
            ctk.CTkLabel(
                self._grid_frame,
                text="Brak komponentów w tej kategorii.",
                text_color=theme.TextMuted,
            ).pack(pady=40)
            return

        cols = 3
        for i in range(cols):
            self._grid_frame.columnconfigure(i, weight=1, uniform="hub")

        for i, comp in enumerate(comps):
            row, col = divmod(i, cols)
            card = ComponentCard(
                self._grid_frame,
                comp,
                on_click=self._on_card_click,
                on_right_click=self._on_card_right,
            )
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _on_card_click(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        result = launch(comp, on_status=self._on_status)
        if result.outcome == LaunchOutcome.BLOCKED_INLINE:
            messagebox.showinfo(comp.name, INLINE_MESSAGE, parent=root)
        elif result.outcome in (LaunchOutcome.ERROR, LaunchOutcome.NO_PYTHON, LaunchOutcome.NO_URL):
            messagebox.showerror(comp.name, result.message, parent=root)

    def _on_card_right(self, comp: Component, _event: object) -> None:
        open_component_folder(comp)
