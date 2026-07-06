"""GICLÉE FRAME™ — F2 page structure inventory + F1 brand planning (RAM only)."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_brief import (
    COMPONENT_DESCRIPTION,
    COMPONENT_NAME,
    COMPONENT_ROLE,
    DRY_RUN_BADGE,
    NEXT_PHASE_NOTE,
    PLANNING_BADGE,
    WORKFLOW_SUMMARY,
    motion_rules_display,
    variant_menu_options,
    visual_rules_display,
)
from giclee_app.studio.gicleeframe_draft_state import (
    CHECK_PLAN_LABEL,
    CLEAR_PLAN_LABEL,
    GicleeFrameDraftState,
    PLAN_EMPTY_COPY,
    PLAN_SECTION_TITLE,
    placement_menu_options,
)
from giclee_app.studio.gicleeframe_dry_run import (
    build_gicleeframe_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.gicleeframe_page_draft import (
    APPLY_RAM_DRAFT_LABEL,
    CHECK_STRUCTURE_LABEL,
    CLEAR_DRAFT_LABEL,
    DRAFT_RAM_DISCLAIMER,
    GicleeFramePageDraft,
    MergedPageElement,
    REFRESH_INVENTORY_LABEL,
    draft_status_menu_options,
    merge_inventory_with_draft,
)
from giclee_app.studio.gicleeframe_page_dry_run import (
    build_page_structure_dry_run,
    format_structure_dry_run_summary,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    F2_STATUS_STRIP,
    GROUP_LABELS_PL,
    PageInventoryReport,
    build_gicleeframe_page_inventory,
    inventory_display_rows,
    inventory_elements_by_group,
)
from giclee_app.studio.gicleeframe_readiness import (
    GicleeFrameReadiness,
    READINESS_SECTION_LABEL,
    evaluate_gicleeframe_page_readiness,
    evaluate_gicleeframe_readiness,
    format_page_readiness_block,
    format_readiness_block,
    readiness_display_rows,
    readiness_page_display_rows,
)

from . import theme
from .widgets import SectionHeader, status_color

_BACK_LABEL = "Wróć do huba"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_PLACEMENT_PLACEHOLDER = "— opcjonalnie: strefa —"
_PAGE_STRUCTURE_TITLE = "Struktura strony GICLÉE FRAME™"
_F1_BRAND_TITLE = "Komponent marki (F1)"


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
        self._brand_draft = GicleeFrameDraftState()
        self._page_draft = GicleeFramePageDraft()
        self._inventory: PageInventoryReport | None = None
        self._merged: list[MergedPageElement] = []
        self._selected_id: str | None = None

        self._stats_label: ctk.CTkLabel | None = None
        self._groups_frame: ctk.CTkFrame | None = None
        self._edit_panel: ctk.CTkFrame | None = None
        self._structure_dry_label: ctk.CTkLabel | None = None
        self._page_readiness_frame: ctk.CTkFrame | None = None
        self._title_entry: ctk.CTkEntry | None = None
        self._text_box: ctk.CTkTextbox | None = None
        self._alt_entry: ctk.CTkEntry | None = None
        self._notes_box: ctk.CTkTextbox | None = None
        self._status_menu: ctk.CTkOptionMenu | None = None
        self._visible_var: ctk.BooleanVar | None = None
        self._order_entry: ctk.CTkEntry | None = None
        self._status_map: dict[str, str] = {}

        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._placement_menu: ctk.CTkOptionMenu | None = None
        self._variant_map: dict[str, str] = {}
        self._placement_map: dict[str, str] = {}
        self._plan_body_label: ctk.CTkLabel | None = None
        self._brand_readiness_frame: ctk.CTkFrame | None = None

        self._build_shell()
        self._refresh_inventory(warn_if_draft=False)

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
            text=F2_STATUS_STRIP,
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        for text in (
            PLANNING_BADGE,
            DRY_RUN_BADGE,
            "RAM draft only",
            "Writer/save: zablokowane",
        ):
            ctk.CTkLabel(
                self,
                text=text,
                font=theme.get_font(10),
                text_color=theme.TextPrimary,
                fg_color=theme.PanelBg,
                corner_radius=6,
                padx=10,
                pady=4,
            ).pack(anchor="w", padx=24, pady=(0, 4))

        self._build_page_structure_section()
        self._build_f1_brand_section()

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (
            DRAFT_RAM_DISCLAIMER,
            "Ten panel przygotowuje specyfikację i mapę strony. Nie zapisuje plików motywu.",
            NEXT_PHASE_NOTE,
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

    def _build_page_structure_section(self) -> None:
        SectionHeader(self, _PAGE_STRUCTURE_TITLE).pack(fill="x", padx=24, pady=(12, 4))

        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(0, 12))

        btn_row = ctk.CTkFrame(panel, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(12, 8))
        ctk.CTkButton(
            btn_row,
            text=REFRESH_INVENTORY_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=lambda: self._refresh_inventory(warn_if_draft=True),
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text=CHECK_STRUCTURE_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._run_structure_dry_run,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_row,
            text=CLEAR_DRAFT_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._clear_page_draft,
        ).pack(side="left")

        self._stats_label = ctk.CTkLabel(
            panel,
            text="Ładowanie inventory…",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=640,
        )
        self._stats_label.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            panel,
            text=DRAFT_RAM_DISCLAIMER,
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
            wraplength=640,
        ).pack(fill="x", padx=16, pady=(0, 8))

        self._groups_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._groups_frame.pack(fill="x", padx=16, pady=(0, 8))

        SectionHeader(panel, "Edycja RAM (wybrany element)").pack(fill="x", padx=16, pady=(8, 4))
        self._edit_panel = ctk.CTkFrame(panel, fg_color=theme.AppBg, corner_radius=6)
        self._edit_panel.pack(fill="x", padx=16, pady=(0, 8))
        self._build_edit_panel()

        self._structure_dry_label = ctk.CTkLabel(
            panel,
            text="Kliknij „Sprawdź strukturę (dry-run)”.",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=640,
        )
        self._structure_dry_label.pack(fill="x", padx=16, pady=(4, 8))

        SectionHeader(panel, "Readiness (strona)").pack(fill="x", padx=16, pady=(4, 4))
        self._page_readiness_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._page_readiness_frame.pack(fill="x", padx=16, pady=(0, 12))
        self._fill_page_readiness(None)

    def _build_edit_panel(self) -> None:
        if self._edit_panel is None:
            return
        ctk.CTkLabel(
            self._edit_panel,
            text="Wybierz element z listy poniżej.",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        ).pack(fill="x", padx=12, pady=8)

        def row(label: str, widget: ctk.CTkBaseClass) -> None:
            r = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(
                r, text=label, width=80, anchor="w",
                font=theme.get_font(11), text_color=theme.TextMuted,
            ).pack(side="left")
            widget.pack(side="left", fill="x", expand=True)

        self._title_entry = ctk.CTkEntry(self._edit_panel, height=28)
        row("Tytuł:", self._title_entry)

        self._text_box = ctk.CTkTextbox(self._edit_panel, height=60, font=theme.get_font(11))
        row("Tekst:", self._text_box)

        self._alt_entry = ctk.CTkEntry(self._edit_panel, height=28)
        row("Alt:", self._alt_entry)

        self._notes_box = ctk.CTkTextbox(self._edit_panel, height=48, font=theme.get_font(11))
        row("Notatka:", self._notes_box)

        status_opts = draft_status_menu_options()
        status_labels = [label for _, label in status_opts]
        self._status_map = dict(zip(status_labels, [sid for sid, _ in status_opts], strict=True))
        self._status_menu = ctk.CTkOptionMenu(
            self._edit_panel,
            values=status_labels,
            command=self._on_status_selected,
            fg_color=theme.PanelBg,
            button_color=theme.PanelBg,
            width=200,
        )
        self._status_menu.set(status_labels[0])
        row("Status:", self._status_menu)

        self._visible_var = ctk.BooleanVar(value=True)
        vis_row = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
        vis_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkCheckBox(
            vis_row,
            text="Widoczność robocza",
            variable=self._visible_var,
            command=self._apply_edit_to_draft,
            font=theme.get_font(11),
        ).pack(side="left")

        self._order_entry = ctk.CTkEntry(self._edit_panel, height=28, width=80)
        row("Kolejność:", self._order_entry)

        ctk.CTkButton(
            self._edit_panel,
            text=APPLY_RAM_DRAFT_LABEL,
            height=28,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._apply_edit_to_draft,
        ).pack(anchor="w", padx=12, pady=(4, 12))

    def _build_f1_brand_section(self) -> None:
        SectionHeader(self, _F1_BRAND_TITLE).pack(fill="x", padx=24, pady=(8, 4))

        role_panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        role_panel.pack(fill="x", padx=24, pady=(0, 8))
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
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(0, 12))

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

    def _refresh_inventory(self, *, warn_if_draft: bool) -> None:
        if warn_if_draft and not self._page_draft.is_empty() and self._on_status:
            self._on_status("Odświeżono inventory · RAM draft zachowany")
        self._inventory = build_gicleeframe_page_inventory(find_components_dir())
        self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
        self._render_inventory()
        self._fill_page_readiness(None)

    def _render_inventory(self) -> None:
        if self._inventory is None or self._stats_label is None or self._groups_frame is None:
            return

        rows = inventory_display_rows(self._inventory)
        lines = [f"{k}: {v}" for k, v in rows]
        if self._inventory.warnings:
            lines.append("")
            for w in self._inventory.warnings:
                lines.append(f"• {w}")
        self._stats_label.configure(text="\n".join(lines))

        for child in self._groups_frame.winfo_children():
            child.destroy()

        by_group: dict[str, list[MergedPageElement]] = {}
        for m in self._merged:
            if not m.visible:
                continue
            by_group.setdefault(m.group, []).append(m)

        for group_id in inventory_elements_by_group(self._inventory).keys():
            items = by_group.get(group_id, [])
            if not items:
                continue
            gtitle = GROUP_LABELS_PL.get(group_id, group_id)
            ctk.CTkLabel(
                self._groups_frame,
                text=gtitle,
                font=theme.get_font(12, "bold"),
                text_color=theme.AccentGoldDim,
                anchor="w",
            ).pack(fill="x", pady=(8, 4))

            for m in items:
                self._add_element_row(m)

    def _add_element_row(self, m: MergedPageElement) -> None:
        if self._groups_frame is None:
            return
        row = ctk.CTkFrame(
            self._groups_frame,
            fg_color=theme.AppBg if m.element_id != self._selected_id else theme.CardHover,
            corner_radius=4,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        row.pack(fill="x", pady=2)
        row.bind("<Button-1>", lambda _e, mid=m.element_id: self._select_element(mid))

        summary = _merged_element_summary(m)
        prefix = "● " if m.has_draft_patch else ""
        txt = f"{prefix}{m.order:02d} · {m.label} · [{m.status}] · {summary}"
        lbl = ctk.CTkLabel(
            row,
            text=txt,
            font=theme.get_font(10),
            text_color=theme.TextPrimary,
            anchor="w",
            wraplength=600,
        )
        lbl.pack(fill="x", padx=8, pady=6)
        lbl.bind("<Button-1>", lambda _e, mid=m.element_id: self._select_element(mid))

    def _select_element(self, element_id: str) -> None:
        self._selected_id = element_id
        m = next((x for x in self._merged if x.element_id == element_id), None)
        if m is None:
            return
        self._render_inventory()
        if self._title_entry:
            self._title_entry.delete(0, "end")
            self._title_entry.insert(0, m.title)
        if self._text_box:
            self._text_box.delete("1.0", "end")
            self._text_box.insert("1.0", m.text)
        if self._alt_entry:
            self._alt_entry.delete(0, "end")
            self._alt_entry.insert(0, m.alt)
        if self._notes_box:
            self._notes_box.delete("1.0", "end")
            self._notes_box.insert("1.0", m.notes)
        if self._status_menu and m.status in self._status_map.values():
            for label, sid in self._status_map.items():
                if sid == m.status:
                    self._status_menu.set(label)
                    break
        if self._visible_var is not None:
            self._visible_var.set(m.visible)
        if self._order_entry:
            self._order_entry.delete(0, "end")
            self._order_entry.insert(0, str(m.order))

    def _apply_edit_to_draft(self) -> None:
        if self._selected_id is None:
            return
        title = self._title_entry.get().strip() if self._title_entry else ""
        text = self._text_box.get("1.0", "end").strip() if self._text_box else ""
        alt = self._alt_entry.get().strip() if self._alt_entry else ""
        notes = self._notes_box.get("1.0", "end").strip() if self._notes_box else ""
        status_label = self._status_menu.get() if self._status_menu else "ok"
        status = self._status_map.get(status_label, "draft_edited")
        visible = bool(self._visible_var.get()) if self._visible_var else True
        order_raw = self._order_entry.get().strip() if self._order_entry else ""
        order = int(order_raw) if order_raw.isdigit() else None

        self._page_draft.set_patch(
            self._selected_id,
            title=title or None,
            text=text or None,
            alt=alt or None,
            notes=notes or None,
            status=status,
            visible=visible,
            order=order,
        )
        if self._inventory:
            self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
            self._render_inventory()
        if self._on_status:
            self._on_status(DRAFT_RAM_DISCLAIMER)

    def _on_status_selected(self, _label: str) -> None:
        self._apply_edit_to_draft()

    def _clear_page_draft(self) -> None:
        self._page_draft.clear()
        self._selected_id = None
        if self._structure_dry_label:
            self._structure_dry_label.configure(text="Kliknij „Sprawdź strukturę (dry-run)”.")
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status("Wyczyszczono draft RAM strony · nic nie zapisano")

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

    def _run_structure_dry_run(self) -> None:
        if self._inventory is None:
            self._refresh_inventory(warn_if_draft=False)
        inv = self._inventory
        if inv is None:
            return
        dry = build_page_structure_dry_run(inv, self._page_draft)
        ready = evaluate_gicleeframe_page_readiness(inv, dry)
        full = format_structure_dry_run_summary(dry) + "\n\n" + format_page_readiness_block(ready)
        if self._structure_dry_label:
            self._structure_dry_label.configure(text=full, text_color=theme.TextPrimary)
        self._fill_page_readiness(ready)
        if self._on_status:
            self._on_status(dry.status_badge)

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

    def _pack_readiness_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        value: str,
        ok: bool | None,
    ) -> None:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=2)
        ctk.CTkLabel(frame, text="●", text_color=status_color(ok), width=20).pack(side="left")
        ctk.CTkLabel(
            frame, text=label, width=180, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        ctk.CTkLabel(frame, text=value, anchor="w", font=theme.get_font(11, "bold")).pack(side="left")

    def _fill_page_readiness(self, ready: object | None) -> None:
        if self._page_readiness_frame is None:
            return
        for child in self._page_readiness_frame.winfo_children():
            child.destroy()
        from giclee_app.studio.gicleeframe_readiness import GicleeFramePageReadiness

        r = ready if isinstance(ready, GicleeFramePageReadiness) else None
        for row in readiness_page_display_rows(r):
            self._pack_readiness_row(self._page_readiness_frame, row.label, row.value, row.ok)

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


def _merged_element_summary(m: MergedPageElement) -> str:
    parts: list[str] = []
    if m.title:
        parts.append(m.title[:60] + ("…" if len(m.title) > 60 else ""))
    if m.text:
        parts.append(m.text[:80] + ("…" if len(m.text) > 80 else ""))
    if m.image_ref:
        ref = m.image_ref
        if len(ref) > 48:
            ref = ref[:45] + "…"
        parts.append(ref)
    return " · ".join(parts) if parts else "—"
