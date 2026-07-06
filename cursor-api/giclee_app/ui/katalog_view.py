"""Katalog workflow screen (F1+F2+F3 planning) — read-only shell + local plan."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from giclee_app.studio.katalog_data_map import (
    F2_NEXT_NOTE,
    KatalogDataMap,
    build_katalog_data_map,
    data_map_display_rows,
    f2_status_strip,
    f3_status_strip,
)
from giclee_app.studio.katalog_draft_state import (
    CHECK_PLAN_LABEL,
    CLEAR_PLAN_LABEL,
    DRAFT_BADGE,
    DRAFT_DISCLAIMER,
    KatalogDraftState,
    PLAN_EMPTY_COPY,
    PLAN_SECTION_TITLE,
    intent_menu_options,
    variant_menu_options,
    zone_menu_options,
)
from giclee_app.studio.katalog_dry_run import (
    DRY_RUN_BADGE,
    F3_DISCLAIMER,
    SHOPIFY_SCOPE_NOTE,
    build_katalog_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.katalog_inventory import (
    DATA_MAP_WARNING,
    F1_READ_ONLY_NOTE,
    KatalogInventoryReport,
    build_katalog_inventory,
    inventory_display_rows,
    workflow_summary,
)
from giclee_app.studio.katalog_readiness import (
    F3_READINESS_DISCLAIMER,
    F5_FUTURE_NOTE,
    evaluate_katalog_plan_readiness,
    format_readiness_block,
)

from . import theme
from .widgets import SectionHeader

_REFRESH_LABEL = "Odśwież inventory / mapę danych"
_BACK_LABEL = "Wróć do huba"
_INTENT_PLACEHOLDER = "— wybierz intencję —"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_ZONE_PLACEHOLDER = "— wybierz strefę —"


class KatalogView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        components_root: Path,
        on_status: Callable[[str], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._components_root = Path(components_root)
        self._on_status = on_status
        self._on_back = on_back
        self._draft = KatalogDraftState()
        self._last_inventory: KatalogInventoryReport | None = None
        self._last_data_map: KatalogDataMap | None = None
        self._inventory_frame: ctk.CTkFrame | None = None
        self._datamap_frame: ctk.CTkFrame | None = None
        self._intent_menu: ctk.CTkOptionMenu | None = None
        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._zone_menu: ctk.CTkOptionMenu | None = None
        self._intent_map: dict[str, str] = {}
        self._variant_map: dict[str, str] = {}
        self._zone_map: dict[str, str] = {}
        self._draft_summary_label: ctk.CTkLabel | None = None
        self._plan_body_label: ctk.CTkLabel | None = None
        self._build_shell()
        self._refresh_all()

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))
        SectionHeader(header, "Katalog").pack(fill="x", side="left")
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
            text=workflow_summary(),
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=f2_status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 2))

        ctk.CTkLabel(
            self,
            text=f3_status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(fill="x", padx=24, pady=(0, 8))
        for text in (
            "Parent workflow",
            "Katalog F1 inventory",
            "Katalog F2 data map",
            "local planning only",
            "Tło do Bio: absorbed",
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

        ctk.CTkButton(
            self,
            text=_REFRESH_LABEL,
            width=220,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._refresh_all,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        SectionHeader(self, "Inventory (F1)").pack(fill="x", padx=24, pady=(0, 4))
        self._inventory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._inventory_frame.pack(fill="x", padx=24, pady=(0, 12))

        SectionHeader(self, "Mapa danych (F2)").pack(fill="x", padx=24, pady=(8, 4))
        self._datamap_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._datamap_frame.pack(fill="x", padx=24, pady=(0, 8))

        self._build_plan_section()

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (DATA_MAP_WARNING, F1_READ_ONLY_NOTE, F2_NEXT_NOTE):
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

        intent_opts = intent_menu_options()
        intent_labels = [_INTENT_PLACEHOLDER] + [label for _, label in intent_opts]
        intent_ids = [""] + [iid for iid, _ in intent_opts]
        self._intent_map = dict(zip(intent_labels, intent_ids, strict=True))

        intent_row = ctk.CTkFrame(panel, fg_color="transparent")
        intent_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            intent_row,
            text="Intencja:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._intent_menu = ctk.CTkOptionMenu(
            intent_row,
            values=intent_labels,
            command=self._on_intent_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._intent_menu.set(_INTENT_PLACEHOLDER)
        self._intent_menu.pack(side="left", fill="x", expand=True)

        variant_row = ctk.CTkFrame(panel, fg_color="transparent")
        variant_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            variant_row,
            text="Wariant:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._variant_menu = ctk.CTkOptionMenu(
            variant_row,
            values=[_VARIANT_PLACEHOLDER],
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

        zone_opts = zone_menu_options()
        zone_labels = [_ZONE_PLACEHOLDER] + [label for _, label in zone_opts]
        zone_ids = [""] + [zid for zid, _ in zone_opts]
        self._zone_map = dict(zip(zone_labels, zone_ids, strict=True))

        zone_row = ctk.CTkFrame(panel, fg_color="transparent")
        zone_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            zone_row,
            text="Strefa:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._zone_menu = ctk.CTkOptionMenu(
            zone_row,
            values=zone_labels,
            command=self._on_zone_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._zone_menu.set(_ZONE_PLACEHOLDER)
        self._zone_menu.pack(side="left", fill="x", expand=True)

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

    def _on_intent_selected(self, label: str) -> None:
        intent_id = self._intent_map.get(label, "")
        self._draft.set_intent(intent_id or None)
        self._refresh_draft_summary()

    def _on_variant_selected(self, label: str) -> None:
        variant_id = self._variant_map.get(label, "")
        self._draft.set_variant(variant_id or None)
        self._refresh_draft_summary()

    def _on_zone_selected(self, label: str) -> None:
        zone_id = self._zone_map.get(label, "")
        self._draft.set_zone(zone_id or None)
        self._refresh_draft_summary()

    def _refresh_draft_summary(self) -> None:
        if self._draft_summary_label is None:
            return
        variant_label: str | None = None
        if self._draft.variant_id and self._last_inventory is not None:
            variant_label = self._last_inventory.katalog.variant_labels.get(
                self._draft.variant_id,
                self._draft.variant_id,
            )
        self._draft_summary_label.configure(
            text=self._draft.format_summary(variant_label=variant_label),
        )

    def _update_variant_menu(self, inventory: KatalogInventoryReport) -> None:
        if self._variant_menu is None:
            return
        katalog = inventory.katalog
        opts = variant_menu_options(katalog.variant_ids, katalog.variant_labels)
        if opts:
            labels = [_VARIANT_PLACEHOLDER] + [label for _, label in opts]
            ids = [""] + [vid for vid, _ in opts]
            self._variant_map = dict(zip(labels, ids, strict=True))
            self._variant_menu.configure(values=labels)
            if self._draft.variant_id and self._draft.variant_id in ids:
                idx = ids.index(self._draft.variant_id)
                self._variant_menu.set(labels[idx])
            else:
                self._variant_menu.set(_VARIANT_PLACEHOLDER)
        else:
            self._variant_map = {_VARIANT_PLACEHOLDER: ""}
            self._variant_menu.configure(values=[_VARIANT_PLACEHOLDER])
            self._variant_menu.set(_VARIANT_PLACEHOLDER)

    def _clear_plan(self) -> None:
        self._draft.clear()
        if self._intent_menu is not None:
            self._intent_menu.set(_INTENT_PLACEHOLDER)
        if self._variant_menu is not None:
            self._variant_menu.set(_VARIANT_PLACEHOLDER)
        if self._zone_menu is not None:
            self._zone_menu.set(_ZONE_PLACEHOLDER)
        if self._plan_body_label is not None:
            self._plan_body_label.configure(text=PLAN_EMPTY_COPY, text_color=theme.TextMuted)
        self._refresh_draft_summary()
        if self._on_status is not None:
            self._on_status("Plan wyczyszczony · draft lokalny · nic nie zapisano")

    def _run_plan_dry_run(self) -> None:
        if self._last_inventory is None or self._last_data_map is None:
            self._refresh_all()
        inventory = self._last_inventory
        data_map = self._last_data_map
        if inventory is None or data_map is None:
            return

        dry_run = build_katalog_plan_dry_run(self._draft, inventory, data_map)
        readiness = evaluate_katalog_plan_readiness(self._draft, dry_run)
        full_text = format_dry_run_summary(dry_run) + "\n\n" + format_readiness_block(readiness)

        if self._plan_body_label is not None:
            self._plan_body_label.configure(
                text=full_text,
                text_color=theme.TextPrimary if dry_run.ok else theme.TextMuted,
            )
        if self._on_status is not None:
            self._on_status(DRY_RUN_BADGE)

    @staticmethod
    def _fill_rows(parent: ctk.CTkFrame, rows: list[tuple[str, str]]) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for label, value in rows:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=label,
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="w",
                width=220,
            ).pack(side="left", anchor="nw")
            ctk.CTkLabel(
                row,
                text=value,
                font=theme.get_font(11),
                text_color=theme.TextPrimary,
                anchor="w",
                justify="left",
                wraplength=480,
            ).pack(side="left", fill="x", expand=True)

    def _refresh_all(self) -> None:
        inv = build_katalog_inventory(self._components_root)
        dm = build_katalog_data_map(self._components_root)
        self._last_inventory = inv
        self._last_data_map = dm
        if self._inventory_frame is not None:
            self._fill_rows(self._inventory_frame, inventory_display_rows(inv))
        if self._datamap_frame is not None:
            self._fill_rows(self._datamap_frame, data_map_display_rows(dm))
        self._update_variant_menu(inv)
        self._refresh_draft_summary()
        if self._on_status is not None:
            self._on_status("Katalog inventory + mapa danych odświeżone (read-only)")
