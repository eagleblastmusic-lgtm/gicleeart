"""GICLÉE FRAME™ — F2.1 page editor workflow + F1 brand planning (RAM only)."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_brief import (
    COMPONENT_DESCRIPTION,
    COMPONENT_NAME,
    NEXT_PHASE_NOTE,
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
    ADD_VARIANT_RAM_LABEL,
    APPLY_RAM_DRAFT_LABEL,
    CHECK_STRUCTURE_LABEL,
    CLEAR_VARIANT_RAM_LABEL,
    DEFAULT_VARIANT_NAME,
    DUPLICATE_VARIANT_LABEL,
    DRAFT_RAM_DISCLAIMER,
    GicleeFramePageDraft,
    MergedPageElement,
    PAGE_EDITOR_TITLE,
    PAGE_SOURCE_FILE,
    RAM_ONLY_STATUS,
    REFRESH_INVENTORY_LABEL,
    RENAME_VARIANT_LABEL,
    SECTION_EDITOR_TITLE,
    SECTION_LIST_DRAG_HINT,
    WORKING_VARIANT_LABEL,
    editor_context_rows,
    editor_field_visibility,
    merge_inventory_with_draft,
    reorder_page_blocks,
    section_dropdown_options,
    section_tree_rows,
    working_variant_menu_label,
)
from giclee_app.studio.gicleeframe_page_dry_run import (
    build_page_structure_dry_run,
    format_structure_dry_run_summary,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    PageInventoryReport,
    build_gicleeframe_page_inventory,
    variant_environment_tag,
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
_SHELL_STATUS_CHIP = "RAM-only · bez zapisu"
_SECTION_PLACEHOLDER = "— wybierz sekcję —"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_PLACEMENT_PLACEHOLDER = "— opcjonalnie: strefa —"
_F1_BRAND_TITLE = "Komponent marki (F1)"
_PAGE_READINESS_TITLE = "Readiness (strona)"
_LEGACY_READONLY_MSG = (
    "Sekcja legacy — nie jest edytowana w Studio. "
    "Tylko notatka robocza opcjonalna."
)
_F2_FIELD_LABEL_WIDTH = 96
_SECTION_LIST_WIDTH = 340
_SECTION_LIST_HEIGHT = 240
_SECTION_ROW_GRIP = "⋮⋮"


def _f2_menu_kwargs() -> dict:
    return {
        "fg_color": theme.AppBg,
        "button_color": theme.PanelBg,
        "button_hover_color": theme.CardHover,
        "dropdown_fg_color": theme.PanelBg,
        "dropdown_hover_color": theme.CardHover,
        "font": theme.get_font(12),
    }


def _element_pill_colors(status: str, *, has_draft_patch: bool) -> tuple[str, str]:
    if has_draft_patch or status in ("draft_edited", "hidden_draft"):
        return theme.AccentGoldDim, theme.TextPrimary
    if status == "ok":
        return theme.StatusOk, theme.AppBg
    if status == "needs_review":
        return theme.StatusWarn, theme.AppBg
    if status == "missing_content":
        return theme.StatusErr, theme.TextPrimary
    if status == "legacy_disabled":
        return theme.StatusUnknown, theme.TextPrimary
    return theme.PanelBg, theme.TextMuted


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

        self._top_meta_label: ctk.CTkLabel | None = None
        self._working_variant_menu: ctk.CTkOptionMenu | None = None
        self._working_variant_map: dict[str, str] = {}
        self._change_count_label: ctk.CTkLabel | None = None
        self._section_list_scroll: ctk.CTkScrollableFrame | None = None
        self._section_dropdown_popup: ctk.CTkFrame | None = None
        self._section_list_trigger: ctk.CTkButton | None = None
        self._section_list_column: ctk.CTkFrame | None = None
        self._section_list_expanded = ctk.BooleanVar(value=False)
        self._section_outside_close_active = False
        self._section_row_frames: list[ctk.CTkFrame] = []
        self._section_row_ids: list[str] = []
        self._drag_from_index: int | None = None
        self._edit_panel: ctk.CTkFrame | None = None
        self._editor_status_dot: ctk.CTkLabel | None = None
        self._legacy_msg_label: ctk.CTkLabel | None = None
        self._structure_dry_label: ctk.CTkLabel | None = None
        self._structure_dry_run_btn: ctk.CTkButton | None = None
        self._page_readiness_frame: ctk.CTkFrame | None = None
        self._page_readiness_body: ctk.CTkFrame | None = None
        self._page_readiness_toggle: ctk.CTkButton | None = None
        self._page_readiness_summary: ctk.CTkLabel | None = None
        self._page_readiness_expanded = ctk.BooleanVar(value=False)

        self._title_row: ctk.CTkFrame | None = None
        self._text_row: ctk.CTkFrame | None = None
        self._alt_row: ctk.CTkFrame | None = None
        self._image_ref_row: ctk.CTkFrame | None = None
        self._page_context_frame: ctk.CTkFrame | None = None
        self._page_context_inner: ctk.CTkFrame | None = None
        self._page_setting_widgets: dict[str, ctk.CTkBaseClass] = {}
        self._notes_row: ctk.CTkFrame | None = None
        self._visible_row: ctk.CTkFrame | None = None
        self._children_overview_row: ctk.CTkFrame | None = None
        self._children_overview_buttons: ctk.CTkFrame | None = None

        self._title_entry: ctk.CTkEntry | None = None
        self._text_box: ctk.CTkTextbox | None = None
        self._alt_entry: ctk.CTkEntry | None = None
        self._image_ref_entry: ctk.CTkEntry | None = None
        self._notes_box: ctk.CTkTextbox | None = None
        self._visible_var: ctk.BooleanVar | None = None

        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._placement_menu: ctk.CTkOptionMenu | None = None
        self._variant_map: dict[str, str] = {}
        self._placement_map: dict[str, str] = {}
        self._plan_body_label: ctk.CTkLabel | None = None
        self._brand_readiness_frame: ctk.CTkFrame | None = None
        self._f1_panel: ctk.CTkFrame | None = None
        self._f1_expanded = ctk.BooleanVar(value=False)

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
            text=_SHELL_STATUS_CHIP,
            font=theme.get_font(10),
            text_color=theme.TextPrimary,
            fg_color=theme.PanelBg,
            corner_radius=6,
            padx=10,
            pady=4,
        ).pack(anchor="w", padx=24, pady=(0, 8))

        self._build_page_editor_section()
        self._build_f1_brand_section()

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (
            DRAFT_RAM_DISCLAIMER,
            "Ten panel przygotowuje specyfikację i mapę strony. Nie zapisuje plików motywu.",
            "Synchronizacja/wdrożenie zablokowane.",
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

    def _build_page_editor_section(self) -> None:
        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(12, 12))

        SectionHeader(panel, PAGE_EDITOR_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        self._build_page_top_bar(panel)
        self._build_page_workspace(panel)
        self._build_dry_run_panel(panel)
        self._build_page_readiness_panel(panel)

    def _build_page_top_bar(self, parent: ctk.CTkFrame) -> None:
        context_card = ctk.CTkFrame(
            parent,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        context_card.pack(fill="x", padx=16, pady=(0, 8))

        self._top_meta_label = ctk.CTkLabel(
            context_card,
            text="Ładowanie…",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
            justify="left",
        )
        self._top_meta_label.pack(fill="x", padx=12, pady=(10, 4))

        variant_row = ctk.CTkFrame(context_card, fg_color="transparent")
        variant_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            variant_row,
            text=f"{WORKING_VARIANT_LABEL}:",
            width=110,
            anchor="w",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        ).pack(side="left")
        self._working_variant_menu = ctk.CTkOptionMenu(
            variant_row,
            values=[DEFAULT_VARIANT_NAME],
            command=self._on_working_variant_selected,
            width=200,
            **_f2_menu_kwargs(),
        )
        self._working_variant_menu.set(DEFAULT_VARIANT_NAME)
        self._working_variant_menu.pack(side="left", padx=(0, 12))
        self._change_count_label = ctk.CTkLabel(
            variant_row,
            text="Zmiany w wariancie: 0",
            font=theme.get_font(10, "bold"),
            text_color=theme.AccentGoldDim,
            fg_color=theme.PanelBg,
            corner_radius=6,
            padx=10,
            pady=4,
            anchor="w",
        )
        self._change_count_label.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            variant_row,
            text=RAM_ONLY_STATUS,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="e",
        ).pack(side="right")

        toolbar = ctk.CTkFrame(parent, fg_color="transparent")
        toolbar.pack(fill="x", padx=16, pady=(0, 8))
        self._build_toolbar_group(
            toolbar,
            "Warianty RAM",
            (
                (ADD_VARIANT_RAM_LABEL, self._add_ram_variant),
                (DUPLICATE_VARIANT_LABEL, self._duplicate_ram_variant),
                (RENAME_VARIANT_LABEL, self._rename_ram_variant),
                (CLEAR_VARIANT_RAM_LABEL, self._clear_page_draft),
            ),
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._build_toolbar_group(
            toolbar,
            "Inventory i struktura",
            (
                (REFRESH_INVENTORY_LABEL, lambda: self._refresh_inventory(warn_if_draft=True)),
                (CHECK_STRUCTURE_LABEL, self._run_structure_dry_run),
            ),
        ).pack(side="left", fill="x", expand=True)

    def _build_toolbar_group(
        self,
        parent: ctk.CTkFrame,
        title: str,
        actions: tuple[tuple[str, Callable[[], None]], ...],
    ) -> ctk.CTkFrame:
        group = ctk.CTkFrame(
            parent,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        ctk.CTkLabel(
            group,
            text=title,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))
        btn_row = ctk.CTkFrame(group, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))
        for label, cmd in actions:
            ctk.CTkButton(
                btn_row,
                text=label,
                height=28,
                fg_color=theme.PanelBg,
                hover_color=theme.CardHover,
                border_width=1,
                border_color=theme.BorderSubtle,
                font=theme.get_font(11),
                command=cmd,
            ).pack(side="left", padx=(0, 6))
        return group

    def _build_page_workspace(self, parent: ctk.CTkFrame) -> None:
        workspace = ctk.CTkFrame(parent, fg_color="transparent")
        workspace.pack(fill="x", padx=16, pady=(0, 8))

        editor_panel = ctk.CTkFrame(
            workspace,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        editor_panel.pack(fill="x")
        self._section_list_column = editor_panel

        editor_title_row = ctk.CTkFrame(editor_panel, fg_color="transparent")
        editor_title_row.pack(fill="x", padx=12, pady=(10, 6))
        self._editor_status_dot = ctk.CTkLabel(
            editor_title_row,
            text="●",
            font=theme.get_font(14),
            text_color=theme.TextMuted,
            width=18,
        )
        self._editor_status_dot.pack(side="left")
        ctk.CTkLabel(
            editor_title_row,
            text=SECTION_EDITOR_TITLE,
            font=theme.get_font(13, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(side="left", padx=(0, 12))
        self._section_list_trigger = ctk.CTkButton(
            editor_title_row,
            text=f"{_SECTION_PLACEHOLDER}  ▾",
            anchor="w",
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            text_color=theme.TextPrimary,
            font=theme.get_font(12),
            command=self._toggle_section_list,
        )
        self._section_list_trigger.pack(side="left", fill="x", expand=True)

        self._section_dropdown_popup = ctk.CTkFrame(
            editor_panel,
            fg_color=theme.PanelBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
            width=_SECTION_LIST_WIDTH,
        )
        ctk.CTkLabel(
            self._section_dropdown_popup,
            text=SECTION_LIST_DRAG_HINT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=_SECTION_LIST_WIDTH - 24,
        ).pack(fill="x", padx=10, pady=(8, 6))
        self._section_list_scroll = ctk.CTkScrollableFrame(
            self._section_dropdown_popup,
            width=_SECTION_LIST_WIDTH - 4,
            height=_SECTION_LIST_HEIGHT,
            fg_color=theme.AppBg,
            corner_radius=4,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._section_list_scroll.pack(fill="x", padx=6, pady=(0, 8))

        self._legacy_msg_label = ctk.CTkLabel(
            editor_panel,
            text="",
            font=theme.get_font(11),
            text_color=theme.AccentGoldDim,
            anchor="w",
            wraplength=400,
        )

        self._edit_panel = ctk.CTkFrame(
            editor_panel,
            fg_color=theme.PanelBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._edit_panel.pack(fill="x", padx=12, pady=(0, 12))
        self._build_edit_panel()

    def _build_edit_panel(self) -> None:
        if self._edit_panel is None:
            return

        def row_holder() -> ctk.CTkFrame:
            r = ctk.CTkFrame(self._edit_panel, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=5)
            return r

        self._page_context_frame = ctk.CTkFrame(
            self._edit_panel,
            fg_color=theme.AppBg,
            corner_radius=4,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        ctk.CTkLabel(
            self._page_context_frame,
            text="Ustawienia ze strony",
            font=theme.get_font(10, "bold"),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))
        self._page_context_inner = ctk.CTkFrame(
            self._page_context_frame, fg_color="transparent",
        )
        self._page_context_inner.pack(fill="x", padx=10, pady=(0, 8))

        self._title_row = row_holder()
        ctk.CTkLabel(
            self._title_row, text="Tytuł:", width=_F2_FIELD_LABEL_WIDTH, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._title_entry = ctk.CTkEntry(self._title_row, height=28)
        self._title_entry.pack(side="left", fill="x", expand=True)

        self._text_row = row_holder()
        ctk.CTkLabel(
            self._text_row, text="Tekst:", width=_F2_FIELD_LABEL_WIDTH, anchor="nw",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._text_box = ctk.CTkTextbox(self._text_row, height=60, font=theme.get_font(11))
        self._text_box.pack(side="left", fill="x", expand=True)

        self._alt_row = row_holder()
        ctk.CTkLabel(
            self._alt_row, text="Alt:", width=_F2_FIELD_LABEL_WIDTH, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._alt_entry = ctk.CTkEntry(self._alt_row, height=28)
        self._alt_entry.pack(side="left", fill="x", expand=True)

        self._image_ref_row = row_holder()
        ctk.CTkLabel(
            self._image_ref_row, text="Image ref:", width=_F2_FIELD_LABEL_WIDTH, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._image_ref_entry = ctk.CTkEntry(
            self._image_ref_row, height=28, state="disabled",
        )
        self._image_ref_entry.pack(side="left", fill="x", expand=True)

        self._notes_row = row_holder()
        ctk.CTkLabel(
            self._notes_row, text="Notatka:", width=_F2_FIELD_LABEL_WIDTH, anchor="w",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._notes_box = ctk.CTkTextbox(self._notes_row, height=28, font=theme.get_font(11))
        self._notes_box.pack(side="left", fill="x", expand=True)

        self._visible_row = row_holder()
        self._visible_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self._visible_row,
            text="Widoczność robocza",
            variable=self._visible_var,
            font=theme.get_font(11),
        ).pack(side="left")

        self._children_overview_row = row_holder()
        ctk.CTkLabel(
            self._children_overview_row, text="Komponenty:", width=_F2_FIELD_LABEL_WIDTH, anchor="nw",
            font=theme.get_font(11), text_color=theme.TextMuted,
        ).pack(side="left")
        self._children_overview_buttons = ctk.CTkFrame(
            self._children_overview_row, fg_color="transparent",
        )
        self._children_overview_buttons.pack(side="left", fill="x", expand=True)

        ctk.CTkButton(
            self._edit_panel,
            text=APPLY_RAM_DRAFT_LABEL,
            width=200,
            height=32,
            fg_color=theme.AccentGoldDim,
            hover_color=theme.AccentGold,
            text_color=theme.AppBg,
            font=theme.get_font(11, "bold"),
            command=self._apply_edit_to_draft,
        ).pack(anchor="w", padx=12, pady=(6, 12))

    def _build_dry_run_panel(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        card.pack(fill="x", padx=16, pady=(0, 8))
        SectionHeader(card, "Podgląd struktury").pack(fill="x", padx=12, pady=(10, 4))
        self._structure_dry_run_btn = ctk.CTkButton(
            card,
            text=CHECK_STRUCTURE_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            font=theme.get_font(11),
            command=self._run_structure_dry_run,
        )
        self._structure_dry_run_btn.pack(anchor="w", padx=12, pady=(0, 8))
        self._structure_dry_label = ctk.CTkLabel(
            card,
            text="",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=720,
        )
        self._structure_dry_label.pack(fill="x", padx=12, pady=(0, 12))

    def _reset_structure_dry_run_display(self) -> None:
        if self._structure_dry_label:
            self._structure_dry_label.configure(text="", text_color=theme.TextMuted)

    def _build_page_readiness_panel(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        card.pack(fill="x", padx=16, pady=(0, 12))

        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=8, pady=(6, 6))
        self._page_readiness_toggle = ctk.CTkButton(
            header_row,
            text=f"▸ {_PAGE_READINESS_TITLE}",
            anchor="w",
            height=32,
            fg_color="transparent",
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            font=theme.get_font(12, "bold"),
            command=self._toggle_page_readiness,
        )
        self._page_readiness_toggle.pack(side="left", fill="x", expand=True)
        self._page_readiness_summary = ctk.CTkLabel(
            header_row,
            text="Rozwiń checklistę",
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="e",
        )
        self._page_readiness_summary.pack(side="right", padx=(8, 4))

        self._page_readiness_body = ctk.CTkFrame(card, fg_color="transparent")
        self._page_readiness_frame = ctk.CTkFrame(
            self._page_readiness_body,
            fg_color=theme.PanelBg,
            corner_radius=4,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._page_readiness_frame.pack(fill="x", padx=12, pady=(0, 12))
        self._fill_page_readiness(None)

    def _toggle_page_readiness(self) -> None:
        if self._page_readiness_body is None or self._page_readiness_toggle is None:
            return
        expanded = not self._page_readiness_expanded.get()
        self._page_readiness_expanded.set(expanded)
        if expanded:
            self._page_readiness_body.pack(fill="x")
            self._page_readiness_toggle.configure(text=f"▾ {_PAGE_READINESS_TITLE}")
        else:
            self._page_readiness_body.pack_forget()
            self._page_readiness_toggle.configure(text=f"▸ {_PAGE_READINESS_TITLE}")

    def _page_readiness_summary_text(self, ready: object | None) -> str:
        from giclee_app.studio.gicleeframe_readiness import GicleeFramePageReadiness

        r = ready if isinstance(ready, GicleeFramePageReadiness) else None
        rows = readiness_page_display_rows(r)
        ready_n = sum(1 for row in rows if row.ok is True)
        blocked_n = sum(1 for row in rows if row.ok is False)
        if r is not None:
            return f"{r.status_label} · {ready_n} gotowe · {blocked_n} zablokowane"
        return f"{ready_n} gotowe · {blocked_n} zablokowane · rozwiń szczegóły"

    def _build_f1_brand_section(self) -> None:
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

    def _toggle_f1_section(self) -> None:
        if self._f1_panel is None:
            return
        if self._f1_expanded.get():
            self._f1_panel.pack(fill="x", padx=24, pady=(0, 4))
        else:
            self._f1_panel.pack_forget()

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

    def _sync_working_variant_menu(self) -> None:
        if self._working_variant_menu is None:
            return
        pairs = self._page_draft.variant_names()
        self._working_variant_map = {}
        labels: list[str] = []
        for vid, _name in pairs:
            variant = self._page_draft.variants[vid]
            label = working_variant_menu_label(variant)
            labels.append(label)
            self._working_variant_map[label] = vid
        if not labels:
            return
        menu_values = labels
        self._working_variant_menu.configure(values=menu_values)
        active_label = working_variant_menu_label(self._page_draft.active_variant())
        if active_label in labels:
            self._working_variant_menu.set(active_label)
        else:
            self._working_variant_menu.set(labels[0])

    def _on_working_variant_selected(self, label: str) -> None:
        vid = self._working_variant_map.get(label)
        if not vid:
            return
        self._page_draft.switch_variant(vid)
        if self._inventory:
            self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
        self._update_top_bar()
        self._render_section_menu()
        if self._selected_id:
            m = next((x for x in self._merged if x.element_id == self._selected_id), None)
            if m is not None:
                self._populate_editor(m)
            else:
                self._selected_id = None
        if self._on_status:
            self._on_status(
                f"Wariant roboczy: {self._page_draft.draft_name} · {RAM_ONLY_STATUS}"
            )

    def _update_top_bar(self) -> None:
        inv = self._inventory
        source_variant = inv.variant_id if inv else "—"
        count = self._page_draft.draft_edit_count()
        if self._top_meta_label:
            if inv and inv.variant_id:
                source_env = variant_environment_tag(
                    inv.variant_id,
                    active_id=inv.variant_id,
                    live_id=inv.live_variant_id,
                )
                source_line = f"Wariant źródłowy: {source_variant} ({source_env})"
            else:
                source_line = f"Wariant źródłowy: {source_variant}"
            self._top_meta_label.configure(
                text=f"{source_line}  ·  Plik: {PAGE_SOURCE_FILE}"
            )
        self._sync_working_variant_menu()
        if self._change_count_label:
            self._change_count_label.configure(text=f"Zmiany w wariancie: {count}")

    def _refresh_inventory(self, *, warn_if_draft: bool) -> None:
        if warn_if_draft and not self._page_draft.is_empty() and self._on_status:
            self._on_status("Odświeżono inventory · RAM draft zachowany")
        self._inventory = build_gicleeframe_page_inventory(find_components_dir())
        self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
        self._update_top_bar()
        self._render_section_menu()
        self._fill_page_readiness(None)

    def _selected_section_label(self) -> str:
        if not self._merged:
            return _SECTION_PLACEHOLDER
        options = section_dropdown_options(self._merged)
        target_id = self._top_level_row_id_for_selection() or self._selected_id
        if target_id:
            for opt in options:
                if opt.element_id == target_id:
                    return opt.display_label
        return options[0].display_label if options else _SECTION_PLACEHOLDER

    def _update_section_list_trigger(self) -> None:
        if self._section_list_trigger is None:
            return
        chevron = "▴" if self._section_list_expanded.get() else "▾"
        self._section_list_trigger.configure(text=f"{self._selected_section_label()}  {chevron}")

    def _collapse_section_list(self) -> None:
        self._section_list_expanded.set(False)
        if self._section_dropdown_popup is not None:
            self._section_dropdown_popup.place_forget()
        self._unbind_section_dropdown_outside_close()
        self._update_section_list_trigger()

    def _open_section_dropdown(self) -> None:
        if (
            self._section_dropdown_popup is None
            or self._section_list_trigger is None
            or self._section_list_column is None
        ):
            return
        self._section_list_expanded.set(True)
        self._render_section_list()
        trigger = self._section_list_trigger
        parent = self._section_list_column
        popup_width = max(trigger.winfo_width(), _SECTION_LIST_WIDTH)
        self._section_dropdown_popup.configure(width=popup_width)
        if self._section_list_scroll is not None:
            self._section_list_scroll.configure(width=max(popup_width - 12, 180))
        parent.update_idletasks()
        x = trigger.winfo_rootx() - parent.winfo_rootx()
        y = trigger.winfo_rooty() - parent.winfo_rooty() + trigger.winfo_height() + 2
        self._section_dropdown_popup.place(x=x, y=y)
        self._section_dropdown_popup.lift()
        self.after(80, self._bind_section_dropdown_outside_close)
        self._update_section_list_trigger()

    def _widget_in_section_dropdown(self, widget: ctk.CTkBaseClass | None) -> bool:
        popup = self._section_dropdown_popup
        trigger = self._section_list_trigger
        current: ctk.CTkBaseClass | None = widget
        while current is not None:
            if current is popup or current is trigger:
                return True
            current = current.master  # type: ignore[assignment]
        return False

    def _bind_section_dropdown_outside_close(self) -> None:
        if self._section_outside_close_active:
            return
        self._section_outside_close_active = True
        self.winfo_toplevel().bind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
            add="+",
        )

    def _unbind_section_dropdown_outside_close(self) -> None:
        if not self._section_outside_close_active:
            return
        self._section_outside_close_active = False
        self.winfo_toplevel().unbind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
        )

    def _on_section_dropdown_outside_click(self, event: object) -> None:
        if not self._section_list_expanded.get():
            return
        widget = getattr(event, "widget", None)
        if self._widget_in_section_dropdown(widget):
            return
        self._collapse_section_list()

    def _toggle_section_list(self) -> None:
        if self._section_list_expanded.get():
            self._collapse_section_list()
        else:
            self._open_section_dropdown()

    def _render_section_list(self) -> None:
        if self._section_list_scroll is None:
            return
        for child in self._section_list_scroll.winfo_children():
            child.destroy()
        self._section_row_frames.clear()
        self._section_row_ids: list[str] = []

        if not self._merged:
            ctk.CTkLabel(
                self._section_list_scroll,
                text=_SECTION_PLACEHOLDER,
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="w",
            ).pack(fill="x", padx=8, pady=8)
            return

        options = section_dropdown_options(self._merged)
        for index, opt in enumerate(options):
            self._section_row_ids.append(opt.element_id)
            self._build_section_row(index, opt.element_id, opt.display_label)

        if self._selected_id is None and options:
            self._select_element(options[0].element_id)
        else:
            self._highlight_section_rows()
        self._update_section_list_trigger()

    def _build_section_row(self, index: int, element_id: str, label: str) -> None:
        if self._section_list_scroll is None:
            return
        row = ctk.CTkFrame(
            self._section_list_scroll,
            fg_color="transparent",
            corner_radius=4,
            height=28,
        )
        row.pack(fill="x", padx=4, pady=1)
        self._section_row_frames.append(row)

        grip = ctk.CTkLabel(
            row,
            text=_SECTION_ROW_GRIP,
            width=22,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            cursor="size_ns",
        )
        grip.pack(side="left", padx=(4, 0))
        grip.bind("<ButtonPress-1>", lambda _e, i=index: self._start_section_drag(i))
        grip.bind("<ButtonRelease-1>", self._finish_section_drag)

        ctk.CTkButton(
            row,
            text=label,
            anchor="w",
            height=26,
            fg_color="transparent",
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            font=theme.get_font(11),
            command=lambda eid=element_id: self._select_element(eid, collapse_list=True),
        ).pack(side="left", fill="x", expand=True, padx=(2, 6))

    def _top_level_row_id_for_selection(self) -> str | None:
        if self._selected_id is None:
            return None
        selected = next(
            (m for m in self._merged if m.element_id == self._selected_id),
            None,
        )
        if selected is None:
            return None
        if selected.element_type in ("jumbo", "body", "image"):
            for row in section_tree_rows(self._merged):
                if row.section_key == selected.section_key and row.row_kind == "media_section":
                    return row.element_id
            return None
        return self._selected_id

    def _highlight_section_rows(self) -> None:
        target = self._top_level_row_id_for_selection()
        for frame, element_id in zip(
            self._section_row_frames,
            self._section_row_ids,
            strict=True,
        ):
            if element_id == target:
                frame.configure(fg_color=theme.PanelBg)
            else:
                frame.configure(fg_color="transparent")

    def _section_row_index_at_root_y(self, y_root: int) -> int | None:
        for index, frame in enumerate(self._section_row_frames):
            top = frame.winfo_rooty()
            if top <= y_root < top + frame.winfo_height():
                return index
        return None

    def _start_section_drag(self, index: int) -> None:
        self._drag_from_index = index
        if 0 <= index < len(self._section_row_frames):
            self._section_row_frames[index].configure(fg_color=theme.CardHover)

    def _finish_section_drag(self, event: object) -> None:
        from_index = self._drag_from_index
        self._drag_from_index = None
        for frame in self._section_row_frames:
            frame.configure(fg_color="transparent")
        y_root = getattr(event, "y_root", None)
        if from_index is None or y_root is None:
            self._highlight_section_rows()
            return
        to_index = self._section_row_index_at_root_y(int(y_root))
        if to_index is None or from_index == to_index:
            self._highlight_section_rows()
            return
        if not reorder_page_blocks(self._page_draft, self._merged, from_index, to_index):
            self._highlight_section_rows()
            return
        if self._inventory:
            self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
        self._update_top_bar()
        selected = self._selected_id
        self._render_section_list()
        if selected:
            m = next((x for x in self._merged if x.element_id == selected), None)
            if m is not None:
                self._selected_id = selected
                self._populate_editor(m)
        if self._on_status:
            self._on_status("Kolejność zaktualizowana w RAM · nic nie zapisano")

    def _render_section_menu(self) -> None:
        self._render_section_list()

    def _select_element(
        self,
        element_id: str,
        *,
        rerender: bool = True,
        collapse_list: bool = False,
    ) -> None:
        del rerender
        self._selected_id = element_id
        m = next((x for x in self._merged if x.element_id == element_id), None)
        if m is None:
            return
        self._highlight_section_rows()
        self._populate_editor(m)
        self._update_section_list_trigger()
        if collapse_list:
            self._collapse_section_list()

    def _populate_editor(self, m: MergedPageElement) -> None:
        dot_color, _ = _element_pill_colors(m.status, has_draft_patch=m.has_draft_patch)
        if self._editor_status_dot:
            self._editor_status_dot.configure(text_color=dot_color)

        is_legacy = m.element_type == "section_legacy"
        if self._legacy_msg_label:
            if is_legacy:
                self._legacy_msg_label.configure(text=_LEGACY_READONLY_MSG)
                self._legacy_msg_label.pack(fill="x", padx=12, pady=(0, 4))
            else:
                self._legacy_msg_label.pack_forget()

        etype = m.element_type
        fields = editor_field_visibility(etype)

        self._set_row_visible(self._title_row, fields.title)
        self._set_row_visible(self._text_row, fields.text)
        self._set_row_visible(self._alt_row, fields.alt)
        self._set_row_visible(self._image_ref_row, fields.image_ref)
        self._set_row_visible(self._notes_row, fields.notes)
        self._set_row_visible(self._visible_row, fields.visible)
        self._set_row_visible(self._children_overview_row, fields.children)
        self._fill_children_overview_buttons(m)

        self._fill_page_context(m, show=fields.page_context)

        readonly = is_legacy
        if self._title_entry:
            self._set_entry(self._title_entry, m.title, readonly=readonly or not fields.title)
        if self._text_box:
            self._set_textbox(self._text_box, m.text, readonly=readonly or not fields.text)
        if self._alt_entry:
            self._set_entry(self._alt_entry, m.alt, readonly=readonly or not fields.alt)
        if self._image_ref_entry:
            self._set_entry(self._image_ref_entry, m.image_ref, readonly=True)
        if self._notes_box:
            self._set_textbox(self._notes_box, m.notes, readonly=is_legacy or not fields.notes)
        if self._visible_var is not None and fields.visible:
            self._visible_var.set(m.visible)

    def _edit_panel_pack_anchor(self) -> ctk.CTkBaseClass | None:
        """First visible form row in the edit panel (for inventory block placement)."""
        if self._edit_panel is None:
            return None
        for child in self._edit_panel.winfo_children():
            if child is self._page_context_frame:
                continue
            if isinstance(child, ctk.CTkButton):
                continue
            if child.winfo_manager() == "pack":
                return child
        return None

    def _fill_page_context(self, m: MergedPageElement, *, show: bool) -> None:
        if self._page_context_frame is None or self._page_context_inner is None:
            return
        for child in self._page_context_inner.winfo_children():
            child.destroy()
        self._page_setting_widgets.clear()
        if not show:
            self._page_context_frame.pack_forget()
            return
        readonly_rows = editor_context_rows(m)
        if not readonly_rows and not m.page_settings:
            self._page_context_frame.pack_forget()
            return
        anchor = self._edit_panel_pack_anchor()
        pack_kwargs: dict = {"fill": "x", "padx": 12, "pady": (8, 4)}
        if anchor is not None:
            pack_kwargs["before"] = anchor
        self._page_context_frame.pack(**pack_kwargs)

        for label, value in readonly_rows:
            row = ctk.CTkFrame(self._page_context_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(
                row,
                text=f"{label}:",
                width=_F2_FIELD_LABEL_WIDTH,
                anchor="nw",
                font=theme.get_font(10),
                text_color=theme.TextMuted,
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=value or "—",
                anchor="nw",
                justify="left",
                wraplength=360,
                font=theme.get_font(10),
                text_color=theme.TextPrimary,
            ).pack(side="left", fill="x", expand=True)

        for field in m.page_settings:
            row = ctk.CTkFrame(self._page_context_inner, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(
                row,
                text=f"{field.label}:",
                width=_F2_FIELD_LABEL_WIDTH,
                anchor="w",
                font=theme.get_font(10),
                text_color=theme.TextMuted,
            ).pack(side="left")
            if field.control == "select" and field.options:
                menu = ctk.CTkOptionMenu(
                    row,
                    values=list(field.options),
                    width=180,
                    height=28,
                    **_f2_menu_kwargs(),
                )
                menu.set(field.value if field.value in field.options else field.options[0])
                menu.pack(side="left")
                self._page_setting_widgets[field.key] = menu
            else:
                entry = ctk.CTkEntry(row, height=28, width=180)
                entry.insert(0, field.value)
                entry.pack(side="left")
                self._page_setting_widgets[field.key] = entry

    def _fill_children_overview_buttons(self, m: MergedPageElement) -> None:
        if self._children_overview_buttons is None:
            return
        for child in self._children_overview_buttons.winfo_children():
            child.destroy()
        if m.element_type != "media_section":
            return
        parent_row = next(
            (r for r in section_tree_rows(self._merged) if r.element_id == m.element_id),
            None,
        )
        if parent_row is None:
            return
        for child in parent_row.children:
            ctk.CTkButton(
                self._children_overview_buttons,
                text=f"→ {child.child_label}",
                height=24,
                width=100,
                font=theme.get_font(10),
                fg_color=theme.AppBg,
                hover_color=theme.CardHover,
                command=lambda mid=child.element_id: self._select_element(mid),
            ).pack(side="left", padx=(0, 6), pady=2)

    def _set_row_visible(self, row: ctk.CTkFrame | None, visible: bool) -> None:
        if row is None:
            return
        if visible:
            row.pack(fill="x", padx=12, pady=4)
        else:
            row.pack_forget()

    def _set_entry(
        self,
        entry: ctk.CTkEntry,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled" if readonly else "normal")

    def _set_textbox(
        self,
        box: ctk.CTkTextbox,
        value: str,
        *,
        readonly: bool,
    ) -> None:
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("1.0", value)
        box.configure(state="disabled" if readonly else "normal")

    def _apply_edit_to_draft(self) -> None:
        if self._selected_id is None:
            if self._on_status:
                self._on_status("Wybierz element z listy sekcji.")
            return
        m = next((x for x in self._merged if x.element_id == self._selected_id), None)
        if m is None:
            return

        fields: dict[str, object] = {}
        etype = m.element_type
        vis = editor_field_visibility(etype)

        if vis.title and self._title_entry:
            title = self._title_entry.get().strip()
            if title != m.title:
                fields["title"] = title or None
        if vis.text and self._text_box:
            text = self._text_box.get("1.0", "end").strip()
            if text != m.text:
                fields["text"] = text or None
        if vis.alt and self._alt_entry:
            alt = self._alt_entry.get().strip()
            if alt != m.alt:
                fields["alt"] = alt or None
        if vis.notes and self._notes_box:
            notes = self._notes_box.get("1.0", "end").strip()
            if notes != m.notes:
                fields["notes"] = notes or None
        if vis.visible and self._visible_var:
            visible = bool(self._visible_var.get())
            if visible != m.visible:
                fields["visible"] = visible

        settings_changes: dict[str, str] = {}
        for field in m.page_settings:
            widget = self._page_setting_widgets.get(field.key)
            if widget is None:
                continue
            if isinstance(widget, ctk.CTkOptionMenu):
                new_value = widget.get()
            elif isinstance(widget, ctk.CTkEntry):
                new_value = widget.get().strip()
            else:
                continue
            if new_value != field.value:
                settings_changes[field.key] = new_value
        if settings_changes:
            fields["settings"] = settings_changes

        if fields:
            self._page_draft.set_patch(self._selected_id, **fields)
        if self._inventory:
            self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
            self._update_top_bar()
            self._render_section_menu()
            self._populate_editor(
                next(x for x in self._merged if x.element_id == self._selected_id)
            )
        if self._on_status:
            self._on_status(DRAFT_RAM_DISCLAIMER)

    def _add_ram_variant(self) -> None:
        self._page_draft.add_variant()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Dodano wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _duplicate_ram_variant(self) -> None:
        self._page_draft.duplicate_active_variant()
        self._selected_id = None
        if self._inventory:
            self._merged = merge_inventory_with_draft(self._inventory, self._page_draft)
        self._update_top_bar()
        self._render_section_menu()
        if self._on_status:
            self._on_status(
                f"Zduplikowano wariant: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _rename_ram_variant(self) -> None:
        dialog = ctk.CTkInputDialog(
            text="Nowa nazwa wariantu roboczego (tylko pamięć):",
            title=RENAME_VARIANT_LABEL,
        )
        name = dialog.get_input()
        if name and name.strip():
            self._page_draft.rename_active_variant(name.strip())
            self._update_top_bar()
            if self._on_status:
                self._on_status(
                    f"Zmieniono nazwę wariantu: {self._page_draft.draft_name}"
                )

    def _clear_page_draft(self) -> None:
        self._page_draft.clear()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Wyczyszczono wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )

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
        if self._page_readiness_summary is not None:
            self._page_readiness_summary.configure(
                text=self._page_readiness_summary_text(ready)
            )
        for child in self._page_readiness_frame.winfo_children():
            child.destroy()
        from giclee_app.studio.gicleeframe_readiness import GicleeFramePageReadiness

        r = ready if isinstance(ready, GicleeFramePageReadiness) else None
        inner = ctk.CTkFrame(self._page_readiness_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        for row in readiness_page_display_rows(r):
            self._pack_readiness_row(inner, row.label, row.value, row.ok)

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

