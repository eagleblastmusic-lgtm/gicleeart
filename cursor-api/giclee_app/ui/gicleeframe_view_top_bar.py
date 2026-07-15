"""GICLÉE FRAME™ — top bar subsystem (context bar + command bar, RAM only)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    ADD_VARIANT_RAM_LABEL,
    CHECK_STRUCTURE_LABEL,
    CLEAR_VARIANT_RAM_LABEL,
    DEFAULT_VARIANT_NAME,
    DUPLICATE_VARIANT_LABEL,
    PANEL_STATUS_UNSAVED,
    REFRESH_INVENTORY_LABEL,
    RENAME_VARIANT_LABEL,
)
from giclee_app.studio.perf import log_event, span

from . import theme
from .gicleeframe_view_primitives import (
    _BTN_HEIGHT,
    _CARD_PAD_X,
    _GF_FIELD,
    _GF_GOLD_SOFT,
    _f2_menu_kwargs,
    _make_gf_card,
    _make_secondary_button,
    _make_section_caption,
    _make_status_pill,
)

_BACK_LABEL = "Wróć do huba"
_SHELL_STATUS_CHIP = "RAM-only · bez zapisu"
_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS = 200
_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS = 0
_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS = 30
_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS = 60


class GicleeFrameTopBarMixin:
    """Context bar, command bar and staggered late-build scheduling boundary."""

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
        lifecycle_alive = getattr(self, "_view_lifecycle_alive", None)
        if callable(lifecycle_alive) and not lifecycle_alive():
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._top_bar_actions_late_done or self._context_bar_actions_building:
            return

        row = self._context_bar_row
        slot = self._context_bar_actions_slot
        try:
            if row is None or slot is None or not row.winfo_exists() or not slot.winfo_exists():
                return
        except (AttributeError, tk.TclError):
            return

        self._context_bar_actions_building = True
        try:
            with span("studio.gicleeframe.build.context_bar.actions_late"):
                self._build_context_bar_actions(row)
        except tk.TclError:
            try:
                if not row.winfo_exists() or not slot.winfo_exists():
                    return
            except (AttributeError, tk.TclError):
                return
            raise
        finally:
            self._context_bar_actions_building = False
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


__all__ = (
    "GicleeFrameTopBarMixin",
    "_BACK_LABEL",
    "_SHELL_STATUS_CHIP",
    "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS",
    "_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS",
    "_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS",
    "_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS",
)
