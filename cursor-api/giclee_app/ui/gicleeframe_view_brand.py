"""GICLÉE FRAME™ — stateful F1 brand-planning panel boundary (RAM only)."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from giclee_app.studio.gicleeframe_brief import (
    COMPONENT_DESCRIPTION,
    WORKFLOW_SUMMARY,
    motion_rules_display,
    variant_menu_options,
    visual_rules_display,
)
from giclee_app.studio.gicleeframe_draft_state import (
    CHECK_PLAN_LABEL,
    CLEAR_PLAN_LABEL,
    PLAN_EMPTY_COPY,
    PLAN_SECTION_TITLE,
    placement_menu_options,
)
from giclee_app.studio.gicleeframe_dry_run import (
    build_gicleeframe_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.gicleeframe_readiness import (
    GicleeFrameReadiness,
    READINESS_SECTION_LABEL,
    evaluate_gicleeframe_readiness,
    format_readiness_block,
    readiness_display_rows,
)
from giclee_app.studio.perf import span

from . import theme
from .widgets import SectionHeader

_F1_BRAND_TITLE = "Komponent marki (F1)"
_F1_LOADING_TEXT = "Ładowanie panelu F1…"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_PLACEMENT_PLACEHOLDER = "— opcjonalnie: strefa —"


class GicleeFrameBrandPanelMixin:
    """F1-only UI behavior supplied to ``GicleeFrameView`` by composition.

    The host view owns widget lifecycle, the F1 expand/collapse adapter and the
    shared readiness-row renderer. This mixin deliberately has no ``__init__``
    and does not inherit from a Tk widget.
    """

    def _build_f1_brand_section_placeholder(self) -> None:
        toggle_row = ctk.CTkFrame(self, fg_color="transparent")
        toggle_row.pack(fill="x", padx=24, pady=(4, 0))
        ctk.CTkCheckBox(
            toggle_row,
            text=f"Pokaż {_F1_BRAND_TITLE}",
            variable=self._f1_expanded,
            command=self._toggle_f1_section,
            font=theme.get_font(11),
        ).pack(side="left")

        self._f1_panel = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(
            self._f1_panel,
            text=_F1_LOADING_TEXT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=16, pady=12)

    def _build_f1_brand_section_deferred(self) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        if self._f1_deferred_built:
            return
        with span("studio.gicleeframe.build.f1_brand_section.deferred"):
            if self._f1_panel is not None:
                for child in self._f1_panel.winfo_children():
                    child.destroy()
                self._build_f1_brand_section_panel_content()
        self._f1_deferred_built = True
        self._try_mark_progressive_full_ready()

    def _build_f1_brand_section_full(self) -> None:
        toggle_row = ctk.CTkFrame(self, fg_color="transparent")
        toggle_row.pack(fill="x", padx=24, pady=(4, 0))
        ctk.CTkCheckBox(
            toggle_row,
            text=f"Pokaż {_F1_BRAND_TITLE}",
            variable=self._f1_expanded,
            command=self._toggle_f1_section,
            font=theme.get_font(11),
        ).pack(side="left")

        self._f1_panel = ctk.CTkFrame(self, fg_color="transparent")
        self._build_f1_brand_section_panel_content()

    def _build_f1_brand_section_panel_content(self) -> None:
        if self._f1_panel is None:
            return

        role_panel = ctk.CTkFrame(
            self._f1_panel,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        role_panel.pack(fill="x", pady=(4, 8))
        ctk.CTkLabel(
            role_panel,
            text=COMPONENT_DESCRIPTION,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=680,
        ).pack(fill="x", padx=16, pady=10)

        panel = ctk.CTkFrame(
            self._f1_panel,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", pady=(0, 8))

        SectionHeader(panel, PLAN_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            panel,
            text=WORKFLOW_SUMMARY,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 8))

        variant_opts = variant_menu_options()
        variant_labels = [_VARIANT_PLACEHOLDER] + [label for _, label in variant_opts]
        variant_ids = [""] + [vid for vid, _ in variant_opts]
        self._variant_map = dict(zip(variant_labels, variant_ids, strict=True))

        vrow = ctk.CTkFrame(panel, fg_color="transparent")
        vrow.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(vrow, text="Wariant:", width=72, anchor="w").pack(side="left")
        self._variant_menu = ctk.CTkOptionMenu(
            vrow,
            values=variant_labels,
            command=self._on_brand_variant,
            width=360,
        )
        self._variant_menu.set(_VARIANT_PLACEHOLDER)
        self._variant_menu.pack(side="left", fill="x", expand=True)

        placement_opts = placement_menu_options()
        plabels = [_PLACEMENT_PLACEHOLDER] + [label for _, label in placement_opts]
        pids = [""] + [pid for pid, _ in placement_opts]
        self._placement_map = dict(zip(plabels, pids, strict=True))
        prow = ctk.CTkFrame(panel, fg_color="transparent")
        prow.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(prow, text="Strefa:", width=72, anchor="w").pack(side="left")
        self._placement_menu = ctk.CTkOptionMenu(
            prow,
            values=plabels,
            command=self._on_brand_placement,
            width=360,
        )
        self._placement_menu.set(_PLACEMENT_PLACEHOLDER)
        self._placement_menu.pack(side="left", fill="x", expand=True)

        self._plan_body_label = ctk.CTkLabel(
            panel,
            text=PLAN_EMPTY_COPY,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._plan_body_label.pack(fill="x", padx=16, pady=8)

        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            btn_row,
            text=CHECK_PLAN_LABEL,
            height=28,
            command=self._run_brand_dry_run,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text=CLEAR_PLAN_LABEL,
            height=28,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._clear_brand_plan,
        ).pack(side="left")

        self._build_rules_section(panel, "Zasady wizualne", visual_rules_display())
        self._build_rules_section(panel, "Zasady motion", motion_rules_display())

        SectionHeader(panel, READINESS_SECTION_LABEL).pack(fill="x", padx=16, pady=(8, 4))
        self._brand_readiness_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._brand_readiness_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._fill_brand_readiness(None)

    def _build_rules_section(
        self,
        parent: ctk.CTkBaseClass,
        title: str,
        rows: list[tuple[str, str]],
    ) -> None:
        SectionHeader(parent, title).pack(fill="x", padx=16, pady=(8, 4))
        block = ctk.CTkFrame(parent, fg_color=theme.AppBg, corner_radius=6)
        block.pack(fill="x", padx=16, pady=(0, 8))
        for label, value in rows:
            row = ctk.CTkFrame(block, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(
                row,
                text=label,
                width=140,
                anchor="w",
                font=theme.get_font(10),
                text_color=theme.TextMuted,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=value,
                anchor="w",
                font=theme.get_font(10),
                wraplength=420,
            ).pack(side="left", fill="x", expand=True)

    def _clear_brand_plan(self) -> None:
        self._brand_draft.clear()
        if self._variant_menu:
            self._variant_menu.set(_VARIANT_PLACEHOLDER)
        if self._placement_menu:
            self._placement_menu.set(_PLACEMENT_PLACEHOLDER)
        if self._plan_body_label:
            self._plan_body_label.configure(text=PLAN_EMPTY_COPY)
        self._fill_brand_readiness(None)
        if self._on_status:
            self._on_status("Wyczyszczono plan marki · nic nie zapisano")

    def _fill_brand_readiness(self, ready: GicleeFrameReadiness | None) -> None:
        if self._brand_readiness_frame is None:
            return
        for child in self._brand_readiness_frame.winfo_children():
            child.destroy()
        if isinstance(ready, GicleeFrameReadiness):
            for line in format_readiness_block(ready).splitlines()[:6]:
                ctk.CTkLabel(
                    self._brand_readiness_frame,
                    text=line,
                    font=theme.get_font(10),
                    text_color=theme.TextMuted,
                    anchor="w",
                ).pack(fill="x", pady=1)
            return
        for row in readiness_display_rows():
            self._pack_readiness_row(self._brand_readiness_frame, row.label, row.value, row.ok)

    def _on_brand_variant(self, label: str) -> None:
        self._brand_draft.set_variant(self._variant_map.get(label, "") or None)

    def _on_brand_placement(self, label: str) -> None:
        self._brand_draft.set_placement(self._placement_map.get(label, "") or None)

    def _run_brand_dry_run(self) -> None:
        dry = build_gicleeframe_plan_dry_run(self._brand_draft)
        ready = evaluate_gicleeframe_readiness(self._brand_draft, dry)
        full = format_dry_run_summary(dry) + "\n\n" + format_readiness_block(ready)
        if self._plan_body_label:
            self._plan_body_label.configure(
                text=full,
                text_color=theme.TextPrimary if dry.ok else theme.TextMuted,
            )
        self._fill_brand_readiness(ready)
        if self._on_status:
            self._on_status(dry.status_badge)


__all__ = (
    "GicleeFrameBrandPanelMixin",
    "_F1_BRAND_TITLE",
    "_F1_LOADING_TEXT",
    "_PLACEMENT_PLACEHOLDER",
    "_VARIANT_PLACEHOLDER",
)
