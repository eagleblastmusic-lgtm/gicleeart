"""GICLÉE FRAME™ workflow screen — planning / preview / dry-run (bez writera)."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.studio.gicleeframe_brief import (
    COMPONENT_DESCRIPTION,
    COMPONENT_NAME,
    COMPONENT_ROLE,
    DRY_RUN_BADGE,
    NEXT_PHASE_NOTE,
    PLANNING_BADGE,
    PLACEMENT_SUGGESTIONS,
    WORKFLOW_SUMMARY,
    motion_rules_display,
    status_strip,
    variant_by_id,
    variant_menu_options,
    visual_rules_display,
)
from giclee_app.studio.gicleeframe_draft_state import (
    CHECK_PLAN_LABEL,
    CLEAR_PLAN_LABEL,
    DRAFT_BADGE,
    DRAFT_DISCLAIMER,
    GicleeFrameDraftState,
    PLAN_EMPTY_COPY,
    PLAN_SECTION_TITLE,
    placement_menu_options,
)
from giclee_app.studio.gicleeframe_dry_run import (
    F3_DISCLAIMER,
    SHOPIFY_SCOPE_NOTE,
    build_gicleeframe_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.gicleeframe_readiness import (
    F3_READINESS_DISCLAIMER,
    F5_FUTURE_NOTE,
    evaluate_gicleeframe_readiness,
    format_readiness_block,
    readiness_display_rows,
)

from . import theme
from .widgets import SectionHeader, status_color

_BACK_LABEL = "Wróć do huba"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_PLACEMENT_PLACEHOLDER = "— opcjonalnie: strefa —"


class GicleeFrameView(ctk.CTkScrollableFrame):
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
        self._draft = GicleeFrameDraftState()
        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._placement_menu: ctk.CTkOptionMenu | None = None
        self._variant_map: dict[str, str] = {}
        self._placement_map: dict[str, str] = {}
        self._draft_summary_label: ctk.CTkLabel | None = None
        self._plan_body_label: ctk.CTkLabel | None = None
        self._preview_frame: ctk.CTkFrame | None = None
        self._preview_label: ctk.CTkLabel | None = None
        self._variant_desc_label: ctk.CTkLabel | None = None
        self._readiness_frame: ctk.CTkFrame | None = None
        self._build_shell()

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))
        SectionHeader(header, COMPONENT_NAME).pack(fill="x", side="left")
        if self._on_back is not None:
            ctk.CTkButton(
                header,
                text=_BACK_LABEL,
                width=120,
                height=28,
                fg_color=theme.PanelBg,
                hover_color=theme.CardHover,
                command=self._on_back,
            ).pack(side="right")

        ctk.CTkLabel(
            self,
            text=COMPONENT_ROLE,
            font=theme.get_font(13, "bold"),
            text_color=theme.AccentGold,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=WORKFLOW_SUMMARY,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(fill="x", padx=24, pady=(0, 8))
        for text in (
            PLANNING_BADGE,
            DRY_RUN_BADGE,
            "Shopify: zablokowane",
            "Writer/save: zablokowane",
        ):
            ctk.CTkLabel(
                badges,
                text=text,
                font=theme.get_font(10),
                text_color=theme.TextPrimary,
                fg_color=theme.PanelBg,
                corner_radius=6,
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 8))

        role_panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        role_panel.pack(fill="x", padx=24, pady=(0, 12))
        ctk.CTkLabel(
            role_panel,
            text=COMPONENT_DESCRIPTION,
            font=theme.get_font(12),
            text_color=theme.TextPrimary,
            anchor="nw",
            justify="left",
            wraplength=680,
        ).pack(fill="x", padx=16, pady=12)

        self._build_variants_section()
        self._build_rules_section("Zasady wizualne", visual_rules_display())
        self._build_rules_section("Zasady motion", motion_rules_display())
        self._build_readiness_section()
        self._build_plan_section()

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (
            "Planowanie w aplikacji — bez wdrożenia w Shopify.",
            NEXT_PHASE_NOTE,
            "Klasyczny launcher: legacy editor strony Giclée Frame (poza tym panelem Studio).",
        ):
            ctk.CTkLabel(
                warn,
                text=f"• {line}",
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="w",
                justify="left",
                wraplength=680,
            ).pack(fill="x", padx=12, pady=(6, 0))
        ctk.CTkLabel(warn, text="", height=4).pack()

    def _build_variants_section(self) -> None:
        SectionHeader(self, "Warianty koncepcyjne").pack(fill="x", padx=24, pady=(8, 4))

        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(0, 12))

        variant_opts = variant_menu_options()
        variant_labels = [_VARIANT_PLACEHOLDER] + [label for _, label in variant_opts]
        variant_ids = [""] + [vid for vid, _ in variant_opts]
        self._variant_map = dict(zip(variant_labels, variant_ids, strict=True))

        row = ctk.CTkFrame(panel, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkLabel(
            row,
            text="Wariant:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._variant_menu = ctk.CTkOptionMenu(
            row,
            values=variant_labels,
            command=self._on_variant_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._variant_menu.set(_VARIANT_PLACEHOLDER)
        self._variant_menu.pack(side="left", fill="x", expand=True)

        self._variant_desc_label = ctk.CTkLabel(
            panel,
            text="Wybierz wariant, aby zobaczyć opis i podgląd.",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._variant_desc_label.pack(fill="x", padx=16, pady=(0, 8))

        self._preview_frame = ctk.CTkFrame(
            panel,
            fg_color="#000000",
            corner_radius=6,
            height=72,
        )
        self._preview_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._preview_frame.pack_propagate(False)
        self._preview_label = ctk.CTkLabel(
            self._preview_frame,
            text=COMPONENT_NAME,
            font=theme.get_font(18, "bold", brand=True),
            text_color="#ffffff",
        )
        self._preview_label.place(relx=0.5, rely=0.5, anchor="center")

    def _build_rules_section(self, title: str, rows: list[tuple[str, str]]) -> None:
        SectionHeader(self, title).pack(fill="x", padx=24, pady=(8, 4))
        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(0, 12))
        for prefix, rule in rows:
            row = ctk.CTkFrame(panel, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                row,
                text=prefix,
                font=theme.get_font(11),
                text_color=theme.AccentGoldDim,
                width=24,
                anchor="w",
            ).pack(side="left", anchor="nw")
            ctk.CTkLabel(
                row,
                text=rule,
                font=theme.get_font(11),
                text_color=theme.TextPrimary,
                anchor="w",
                justify="left",
                wraplength=620,
            ).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(panel, text="", height=8).pack()

    def _build_readiness_section(self) -> None:
        SectionHeader(self, "Status gotowości").pack(fill="x", padx=24, pady=(8, 4))
        self._readiness_frame = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._readiness_frame.pack(fill="x", padx=24, pady=(0, 12))
        self._fill_readiness_rows()

    def _fill_readiness_rows(self) -> None:
        if self._readiness_frame is None:
            return
        for child in self._readiness_frame.winfo_children():
            child.destroy()
        for row in readiness_display_rows():
            frame = ctk.CTkFrame(self._readiness_frame, fg_color="transparent")
            frame.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(
                frame,
                text="●",
                font=theme.get_font(12),
                text_color=status_color(row.ok),
                width=20,
            ).pack(side="left")
            ctk.CTkLabel(
                frame,
                text=row.label,
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                width=200,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                frame,
                text=row.value,
                font=theme.get_font(11, "bold"),
                text_color=theme.TextPrimary,
                anchor="w",
            ).pack(side="left")
        ctk.CTkLabel(self._readiness_frame, text="", height=8).pack()

    def _build_plan_section(self) -> None:
        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(8, 8))

        SectionHeader(panel, PLAN_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            panel,
            text=DRAFT_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        placement_opts = placement_menu_options()
        placement_labels = [_PLACEMENT_PLACEHOLDER] + [label for _, label in placement_opts]
        placement_ids = [""] + [pid for pid, _ in placement_opts]
        self._placement_map = dict(zip(placement_labels, placement_ids, strict=True))

        placement_row = ctk.CTkFrame(panel, fg_color="transparent")
        placement_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            placement_row,
            text="Strefa:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._placement_menu = ctk.CTkOptionMenu(
            placement_row,
            values=placement_labels,
            command=self._on_placement_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._placement_menu.set(_PLACEMENT_PLACEHOLDER)
        self._placement_menu.pack(side="left", fill="x", expand=True)

        suggest = ctk.CTkLabel(
            panel,
            text="Sugerowane miejsca: " + " · ".join(PLACEMENT_SUGGESTIONS),
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        suggest.pack(fill="x", padx=16, pady=(0, 8))

        self._draft_summary_label = ctk.CTkLabel(
            panel,
            text=self._draft.format_summary(),
            font=theme.get_font(12),
            text_color=theme.TextPrimary,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._draft_summary_label.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(
            panel,
            text=DRAFT_DISCLAIMER,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            panel,
            text=DRY_RUN_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))

        self._plan_body_label = ctk.CTkLabel(
            panel,
            text=PLAN_EMPTY_COPY,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._plan_body_label.pack(fill="x", padx=16, pady=(0, 8))

        for disclaimer in (F3_DISCLAIMER, SHOPIFY_SCOPE_NOTE, F3_READINESS_DISCLAIMER, F5_FUTURE_NOTE):
            ctk.CTkLabel(
                panel,
                text=disclaimer,
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="nw",
                justify="left",
                wraplength=560,
            ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkButton(
            panel,
            text=CHECK_PLAN_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._run_plan_dry_run,
        ).pack(anchor="w", padx=16, pady=(4, 4))

        ctk.CTkButton(
            panel,
            text=CLEAR_PLAN_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._clear_plan,
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _on_variant_selected(self, label: str) -> None:
        variant_id = self._variant_map.get(label, "")
        self._draft.set_variant(variant_id or None)
        self._update_variant_preview()
        self._refresh_draft_summary()

    def _on_placement_selected(self, label: str) -> None:
        placement_id = self._placement_map.get(label, "")
        self._draft.set_placement(placement_id or None)
        self._refresh_draft_summary()

    def _update_variant_preview(self) -> None:
        variant = variant_by_id(self._draft.variant_id)
        if self._variant_desc_label is not None:
            if variant is None:
                self._variant_desc_label.configure(
                    text="Wybierz wariant, aby zobaczyć opis i podgląd.",
                )
            else:
                self._variant_desc_label.configure(text=variant.description_pl)
        if self._preview_frame is not None and self._preview_label is not None:
            if variant is None:
                self._preview_frame.configure(fg_color="#000000")
                self._preview_label.configure(
                    text=COMPONENT_NAME,
                    text_color="#ffffff",
                    font=theme.get_font(18, "bold", brand=True),
                )
            else:
                self._preview_frame.configure(fg_color=variant.preview_bg)
                size = 14 if variant.variant_id == "compact" else 20
                if variant.variant_id == "hero_label":
                    size = 24
                self._preview_label.configure(
                    text=variant.preview_text,
                    text_color=variant.preview_fg,
                    font=theme.get_font(size, "bold", brand=True),
                )

    def _refresh_draft_summary(self) -> None:
        if self._draft_summary_label is not None:
            self._draft_summary_label.configure(text=self._draft.format_summary())

    def _clear_plan(self) -> None:
        self._draft.clear()
        if self._variant_menu is not None:
            self._variant_menu.set(_VARIANT_PLACEHOLDER)
        if self._placement_menu is not None:
            self._placement_menu.set(_PLACEMENT_PLACEHOLDER)
        if self._plan_body_label is not None:
            self._plan_body_label.configure(text=PLAN_EMPTY_COPY, text_color=theme.TextMuted)
        self._update_variant_preview()
        self._refresh_draft_summary()
        if self._on_status is not None:
            self._on_status("Wybór wyczyszczony · draft lokalny · nic nie zapisano")

    def _run_plan_dry_run(self) -> None:
        dry_run = build_gicleeframe_plan_dry_run(self._draft)
        readiness = evaluate_gicleeframe_readiness(self._draft, dry_run)
        full_text = format_dry_run_summary(dry_run) + "\n\n" + format_readiness_block(readiness)

        if self._plan_body_label is not None:
            self._plan_body_label.configure(
                text=full_text,
                text_color=theme.TextPrimary if dry_run.ok else theme.TextMuted,
            )
        if self._on_status is not None:
            self._on_status(DRY_RUN_BADGE)
