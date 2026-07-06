"""Panel tła w Studio Preview (F4.2+) — … F5.4d asset ref selection."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.studio.background_asset_catalog import (
    ASSET_SELECTION_BADGE,
    ASSET_SELECTION_EMPTY,
    ASSET_SELECTION_HINT,
    ASSET_SELECTION_SECTION_TITLE,
    BackgroundAssetEntry,
    build_background_asset_catalog,
    catalog_enabled_for_folder,
    filter_entries_for_draft_kind,
    find_entry_by_id,
)
from giclee_app.studio.background_asset_shell import asset_library_rows
from giclee_app.studio.background_asset_types import AssetKind
from giclee_app.studio.background_capabilities import (
    BackgroundCapability,
    tier_display,
)
from giclee_app.studio.background_draft_preview import (
    PREVIEW_BADGE,
    PREVIEW_DISCLAIMER,
    PREVIEW_EMPTY_COPY,
    PREVIEW_SECTION_TITLE,
    format_preview_body,
    placeholder_label_for_kind,
    preview_enabled_for_folder,
)
from giclee_app.studio.background_draft_state import (
    CLEAR_DRAFT_LABEL,
    DRAFT_BADGE,
    DRAFT_DISCLAIMER,
    DRAFT_SECTION_TITLE,
    BackgroundDraftState,
    asset_selection_visible,
    draft_enabled_for_folder,
    kind_menu_options,
    zone_menu_options,
)
from giclee_app.studio.background_save_contract import (
    CHECK_SAVE_LABEL,
    DRY_RUN_BADGE,
    SAVE_PLAN_EMPTY_COPY,
    SAVE_PLAN_SECTION_TITLE,
    build_background_save_dry_run,
    format_dry_run_summary,
    save_plan_enabled_for_folder,
)
from giclee_app.studio.background_save_readiness import (
    CLEAR_PLAN_CHECKBOX,
    F54B0_DISCLAIMER,
    F54B1_FUTURE_NOTE,
    LAST_BACKUP_LABEL,
    SAVE_LOCAL_LABEL,
    SAVE_LOCAL_STATUS,
    UNDO_LAST_SAVE_LABEL,
    UNDO_RESTORE_STATUS,
    SaveReadiness,
    evaluate_save_readiness,
    format_readiness_block,
)
from giclee_app.studio.background_save_writer import (
    SaveWriteResult,
    clear_section_background_with_backup,
    restore_section_background_from_backup,
    set_section_background_with_ref_backup,
)
from giclee_app.studio.background_state import (
    read_stronaglowna_active_variant,
    summarize_background_state,
)

from . import theme
from .widgets import SectionHeader

_HANDOFF_BUTTON_LABEL = "Edytuj w komponencie"
_DRAFT_INSERT_AFTER = "Biblioteka / Assety"
_DRAFT_STATUS_MSG = "Draft lokalny — niezapisany"
_PREVIEW_STATUS_MSG = "Podgląd koncepcyjny — niezastosowany"
_DRY_RUN_STATUS_MSG = DRY_RUN_BADGE

_CO_DALEJ_NOTE = (
    "Użyj przycisku „Edytuj w komponencie”, aby przejść do istniejącego "
    "edytora inline. Ten panel nie zapisuje danych."
)


def panel_rows(
    cap: BackgroundCapability,
    *,
    component_name: str,
    folder_name: str = "",
    package_path: Path | None = None,
) -> list[tuple[str, str]]:
    """Sekcje read-only panelu — testowalne bez Tk. Draft (F5.2) poza tym API."""
    _ = component_name
    state_text = ""
    if folder_name and package_path is not None:
        state_text = summarize_background_state(folder_name, package_path).text
    rows: list[tuple[str, str]] = [
        ("Typ tła", f"{cap.label}\n{tier_display(cap.tier)}"),
        ("Źródło", cap.source_hint),
    ]
    if state_text:
        rows.append(("Aktualny stan", state_text))
    rows.extend(asset_library_rows(folder_name, package_path))
    rows.extend([
        ("Kontekst inline", cap.inline_note),
        ("Status", "read-only"),
        ("Co dalej", _CO_DALEJ_NOTE),
    ])
    return rows


class BackgroundPanelView(ctk.CTkFrame):
    """Widok panelu tła — transient host w launcher_studio."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        cap: BackgroundCapability,
        *,
        on_back: Callable[[], None],
        on_status: Callable[[str], None] | None = None,
        on_open_inline: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._comp = comp
        self._cap = cap
        self._on_back = on_back
        self._on_status = on_status
        self._on_open_inline = on_open_inline
        self._draft = BackgroundDraftState()
        self._draft_summary_label: ctk.CTkLabel | None = None
        self._zone_menu: ctk.CTkOptionMenu | None = None
        self._kind_menu: ctk.CTkOptionMenu | None = None
        self._zone_map: dict[str, str] = {}
        self._kind_map: dict[str, AssetKind] = {}
        self._preview_body_label: ctk.CTkLabel | None = None
        self._preview_placeholder_frame: ctk.CTkFrame | None = None
        self._preview_placeholder_label: ctk.CTkLabel | None = None
        self._preview_disclaimer_label: ctk.CTkLabel | None = None
        self._save_plan_body_label: ctk.CTkLabel | None = None
        self._clear_plan_intent = False
        self._clear_plan_checkbox: ctk.CTkCheckBox | None = None
        self._save_local_button: ctk.CTkButton | None = None
        self._undo_button: ctk.CTkButton | None = None
        self._last_backup_label: ctk.CTkLabel | None = None
        self._last_successful_write: SaveWriteResult | None = None
        self._last_save_variant_id: str | None = None
        self._readonly_body_labels: dict[str, ctk.CTkLabel] = {}
        self._last_readiness: SaveReadiness | None = None
        self._asset_selection_panel: ctk.CTkFrame | None = None
        self._asset_selection_body: ctk.CTkFrame | None = None
        self._asset_selection_summary: ctk.CTkLabel | None = None
        self._asset_buttons: dict[str, ctk.CTkButton] = {}
        self._build_shell()
        if callable(self._on_status):
            self._on_status(f"Tło: {cap.label} — read-only panel")

    @property
    def comp(self) -> Component:
        return self._comp

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=16, pady=10)
        ctk.CTkLabel(
            left,
            text="Tło",
            font=theme.get_font(16, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            left,
            text=f"{self._comp.name}  ·  {self._comp.folder_name}",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))
        ctk.CTkButton(
            header,
            text="Wróć",
            width=120,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            command=self._on_back,
        ).pack(side="right", padx=16, pady=10)

        scroll = ctk.CTkScrollableFrame(self, fg_color=theme.AppBg, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            scroll,
            text="read-only",
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=72,
            height=22,
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        rows = panel_rows(
            self._cap,
            component_name=self._comp.name,
            folder_name=self._comp.folder_name,
            package_path=self._comp.package_path,
        )
        grid_row = 1
        show_draft = draft_enabled_for_folder(self._comp.folder_name)

        for title, body in rows:
            self._render_readonly_section(scroll, grid_row, title, body)
            grid_row += 1
            if show_draft and title == _DRAFT_INSERT_AFTER:
                self._render_draft_section(scroll, grid_row)
                grid_row += 1
                if catalog_enabled_for_folder(self._comp.folder_name):
                    self._render_asset_selection_section(scroll, grid_row)
                    grid_row += 1
                if preview_enabled_for_folder(self._comp.folder_name):
                    self._render_preview_section(scroll, grid_row)
                    grid_row += 1
                if save_plan_enabled_for_folder(self._comp.folder_name):
                    self._render_save_plan_section(scroll, grid_row)
                    grid_row += 1

        if self._on_open_inline is not None and self._comp.mode == "inline":
            action_row = ctk.CTkFrame(scroll, fg_color="transparent")
            action_row.grid(row=grid_row, column=0, sticky="ew", pady=(4, 0))
            ctk.CTkButton(
                action_row,
                text=_HANDOFF_BUTTON_LABEL,
                height=36,
                fg_color=theme.PanelBg,
                hover_color=theme.CardHover,
                border_width=1,
                border_color=theme.BorderSubtle,
                command=self._on_open_inline,
            ).pack(anchor="w")

    def _render_readonly_section(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
        title: str,
        body: str,
    ) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        SectionHeader(panel, title).pack(fill="x", padx=16, pady=(12, 4))
        body_label = ctk.CTkLabel(
            panel,
            text=body,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        body_label.pack(fill="x", padx=16, pady=(0, 12))
        self._readonly_body_labels[title] = body_label

    def _render_draft_section(self, parent: ctk.CTkScrollableFrame, row: int) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)

        SectionHeader(panel, DRAFT_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            panel,
            text=DRAFT_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        zone_opts = zone_menu_options()
        zone_labels = [label for _, label in zone_opts]
        zone_ids = [field_id for field_id, _ in zone_opts]
        self._zone_map = dict(zip(zone_labels, zone_ids, strict=True))

        kind_opts = kind_menu_options()
        kind_labels = [label for _, label in kind_opts]
        kind_ids = [kind for kind, _ in kind_opts]
        self._kind_map = dict(zip(kind_labels, kind_ids, strict=True))

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
        self._zone_menu.set(zone_labels[0])
        self._zone_menu.pack(side="left", fill="x", expand=True)

        kind_row = ctk.CTkFrame(panel, fg_color="transparent")
        kind_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            kind_row,
            text="Typ:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._kind_menu = ctk.CTkOptionMenu(
            kind_row,
            values=kind_labels,
            command=self._on_kind_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._kind_menu.set(kind_labels[0])
        self._kind_menu.pack(side="left", fill="x", expand=True)

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
        ).pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            panel,
            text=CLEAR_DRAFT_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._clear_draft,
        ).pack(anchor="w", padx=16, pady=(0, 12))
        self._refresh_draft_ui(notify=False)

    def _render_asset_selection_section(
        self,
        parent: ctk.CTkScrollableFrame,
        row: int,
    ) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        self._asset_selection_panel = panel

        SectionHeader(panel, ASSET_SELECTION_SECTION_TITLE).pack(
            fill="x", padx=16, pady=(12, 4)
        )
        ctk.CTkLabel(
            panel,
            text=ASSET_SELECTION_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        self._asset_selection_body = ctk.CTkFrame(panel, fg_color="transparent")
        self._asset_selection_body.pack(fill="x", padx=16, pady=(0, 8))

        self._asset_selection_summary = ctk.CTkLabel(
            panel,
            text="",
            font=theme.get_font(12),
            text_color=theme.TextPrimary,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._asset_selection_summary.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            panel,
            text=ASSET_SELECTION_HINT,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 12))

        self._refresh_asset_selection_ui()

    def _selected_asset_label(self) -> str | None:
        if not self._draft.selected_asset_id:
            return None
        catalog = build_background_asset_catalog(self._comp.package_path)
        entry = find_entry_by_id(catalog, self._draft.selected_asset_id)
        if entry is None:
            return None
        return entry.display_label

    def _refresh_asset_selection_ui(self) -> None:
        if self._asset_selection_panel is None or self._asset_selection_body is None:
            return

        for child in self._asset_selection_body.winfo_children():
            child.destroy()
        self._asset_buttons.clear()

        visible = asset_selection_visible(self._draft)
        if visible:
            self._asset_selection_panel.grid()
        else:
            self._asset_selection_panel.grid_remove()
            return

        catalog = build_background_asset_catalog(self._comp.package_path)
        entries = filter_entries_for_draft_kind(catalog, self._draft.asset_kind)

        if not entries:
            ctk.CTkLabel(
                self._asset_selection_body,
                text=ASSET_SELECTION_EMPTY,
                font=theme.get_font(12),
                text_color=theme.TextMuted,
                anchor="w",
                justify="left",
                wraplength=540,
            ).pack(fill="x", pady=(0, 4))
        else:
            for entry in entries:
                self._add_asset_button(entry)

        if self._asset_selection_summary is not None:
            if self._draft.selected_asset_id:
                label = self._selected_asset_label() or "wybrany asset"
                kind = self._draft.kind_label_pl()
                self._asset_selection_summary.configure(
                    text=f"Wybrany asset: {label} · {kind}",
                )
            else:
                self._asset_selection_summary.configure(text="Nie wybrano assetu")

    def _add_asset_button(self, entry: BackgroundAssetEntry) -> None:
        if self._asset_selection_body is None:
            return
        selected = self._draft.selected_asset_id == entry.asset_id
        kind_badge = "obraz" if entry.kind == "image" else "wideo"
        text = f"{entry.display_label} · {kind_badge}"
        if selected:
            text = f"✓ {text}"
        btn = ctk.CTkButton(
            self._asset_selection_body,
            text=text,
            height=30,
            anchor="w",
            fg_color=theme.AccentGoldDim if selected else theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            font=theme.get_font(12),
            command=lambda asset_id=entry.asset_id: self._on_asset_selected(asset_id),
        )
        btn.pack(fill="x", pady=(0, 4))
        self._asset_buttons[entry.asset_id] = btn

    def _on_asset_selected(self, asset_id: str) -> None:
        self._draft.set_selected_asset(asset_id)
        self._refresh_draft_ui()

    def _render_preview_section(self, parent: ctk.CTkScrollableFrame, row: int) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)

        SectionHeader(panel, PREVIEW_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))

        self._preview_body_label = ctk.CTkLabel(
            panel,
            text=PREVIEW_EMPTY_COPY,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._preview_body_label.pack(fill="x", padx=16, pady=(0, 8))

        self._preview_placeholder_frame = ctk.CTkFrame(
            panel,
            fg_color=theme.AppBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=80,
        )
        self._preview_placeholder_frame.pack(fill="x", padx=16, pady=(0, 8))
        self._preview_placeholder_frame.pack_propagate(False)

        self._preview_placeholder_label = ctk.CTkLabel(
            self._preview_placeholder_frame,
            text="",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
        )
        self._preview_placeholder_label.place(relx=0.5, rely=0.5, anchor="center")

        self._preview_disclaimer_label = ctk.CTkLabel(
            panel,
            text=PREVIEW_DISCLAIMER,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._preview_disclaimer_label.pack(fill="x", padx=16, pady=(0, 12))
        self._preview_disclaimer_label.pack_forget()
        self._preview_placeholder_frame.pack_forget()

    def _render_save_plan_section(self, parent: ctk.CTkScrollableFrame, row: int) -> None:
        panel = ctk.CTkFrame(
            parent,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)

        SectionHeader(panel, SAVE_PLAN_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            panel,
            text=DRY_RUN_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        self._save_plan_body_label = ctk.CTkLabel(
            panel,
            text=SAVE_PLAN_EMPTY_COPY,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._save_plan_body_label.pack(fill="x", padx=16, pady=(0, 8))

        self._clear_plan_checkbox = ctk.CTkCheckBox(
            panel,
            text=CLEAR_PLAN_CHECKBOX,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            fg_color=theme.AppBg,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._on_clear_plan_toggled,
        )
        self._clear_plan_checkbox.pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            panel,
            text=F54B0_DISCLAIMER,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            panel,
            text=F54B1_FUTURE_NOTE,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkButton(
            panel,
            text=CHECK_SAVE_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._run_save_dry_run,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._save_local_button = ctk.CTkButton(
            panel,
            text=SAVE_LOCAL_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._on_save_local,
        )
        self._save_local_button.pack(anchor="w", padx=16, pady=(0, 8))
        self._save_local_button.pack_forget()

        self._last_backup_label = ctk.CTkLabel(
            panel,
            text="",
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._last_backup_label.pack(anchor="w", padx=16, pady=(0, 8))
        self._last_backup_label.pack_forget()

        self._undo_button = ctk.CTkButton(
            panel,
            text=UNDO_LAST_SAVE_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._on_undo_last_write,
        )
        self._undo_button.pack(anchor="w", padx=16, pady=(0, 12))
        self._undo_button.pack_forget()

    def _clear_session_undo(self) -> None:
        self._last_successful_write = None
        self._last_save_variant_id = None
        if self._undo_button is not None:
            self._undo_button.pack_forget()
        if self._last_backup_label is not None:
            self._last_backup_label.pack_forget()

    def _set_session_undo(self, result: SaveWriteResult) -> None:
        active = read_stronaglowna_active_variant(self._comp.package_path)
        self._last_successful_write = result
        self._last_save_variant_id = active[0] if active else None
        if self._last_backup_label is not None and result.backup_filename:
            self._last_backup_label.configure(
                text=f"{LAST_BACKUP_LABEL} {result.backup_filename}",
            )
            self._last_backup_label.pack(anchor="w", padx=16, pady=(0, 8))
        if self._undo_button is not None:
            self._undo_button.pack(anchor="w", padx=16, pady=(0, 12))

    def _update_undo_visibility(self) -> None:
        if self._undo_button is None:
            return
        if self._last_successful_write is not None and self._last_successful_write.ok:
            if (
                self._last_backup_label is not None
                and self._last_successful_write.backup_filename
            ):
                self._last_backup_label.configure(
                    text=f"{LAST_BACKUP_LABEL} {self._last_successful_write.backup_filename}",
                )
                self._last_backup_label.pack(anchor="w", padx=16, pady=(0, 8))
            self._undo_button.pack(anchor="w", padx=16, pady=(0, 12))
        else:
            self._clear_session_undo()

    def _refresh_readonly_sections(self) -> None:
        rows = panel_rows(
            self._cap,
            component_name=self._comp.name,
            folder_name=self._comp.folder_name,
            package_path=self._comp.package_path,
        )
        for title, body in rows:
            label = self._readonly_body_labels.get(title)
            if label is not None:
                label.configure(text=body)

    def _update_save_local_button(self, readiness: SaveReadiness) -> None:
        if self._save_local_button is None:
            return
        show_clear = (
            self._clear_plan_intent
            and readiness.ready
            and readiness.operation == "clear"
        )
        show_set_with_ref = (
            readiness.ready
            and readiness.operation == "set_with_ref"
            and bool(self._draft.selected_asset_id)
        )
        if show_clear or show_set_with_ref:
            self._save_local_button.pack(anchor="w", padx=16, pady=(0, 12))
        else:
            self._save_local_button.pack_forget()

    def _compose_save_plan_text(
        self,
        dry_run_summary: str,
        readiness: SaveReadiness,
        *,
        extra_lines: tuple[str, ...] = (),
    ) -> str:
        clear_ready = readiness.ready and readiness.operation == "clear"
        set_with_ref_ready = (
            readiness.ready and readiness.operation == "set_with_ref"
        )
        readiness_block = format_readiness_block(
            readiness.summary,
            clear_ready=clear_ready,
            set_with_ref_ready=set_with_ref_ready,
        )
        parts = [dry_run_summary, "", readiness_block]
        if extra_lines:
            parts.extend(["", *extra_lines])
        return "\n".join(parts)

    def _on_clear_plan_toggled(self) -> None:
        if self._clear_plan_checkbox is not None:
            self._clear_plan_intent = bool(self._clear_plan_checkbox.get())

    def _run_save_dry_run(self) -> None:
        self._on_clear_plan_toggled()
        dry_run = build_background_save_dry_run(self._draft, self._comp.package_path)
        readiness = evaluate_save_readiness(
            self._draft,
            self._comp.package_path,
            clear_intent=self._clear_plan_intent,
        )
        self._last_readiness = readiness
        summary = format_dry_run_summary(dry_run)
        full_text = self._compose_save_plan_text(summary, readiness)
        if self._save_plan_body_label is not None:
            color = theme.TextPrimary if dry_run.ok else theme.TextMuted
            self._save_plan_body_label.configure(text=full_text, text_color=color)
        self._update_save_local_button(readiness)
        if callable(self._on_status):
            self._on_status(_DRY_RUN_STATUS_MSG)

    def _on_save_local(self) -> None:
        self._on_clear_plan_toggled()
        readiness = evaluate_save_readiness(
            self._draft,
            self._comp.package_path,
            clear_intent=self._clear_plan_intent,
        )
        if not readiness.ready or readiness.operation not in ("clear", "set_with_ref"):
            if callable(self._on_status):
                self._on_status("Zapis zablokowany — operacja niedostępna.")
            return

        if readiness.operation == "clear":
            confirmed = messagebox.askyesno(
                "Zapis lokalny",
                "\n".join([
                    f"Operacja: wyczyść tło w strefie {self._draft.zone_display()}",
                    "Dotyczy jednej sekcji section_background.",
                    "Zostanie utworzony backup index.json.",
                    "Bez Shopify · bez deploy.",
                    "",
                    "Kontynuować?",
                ]),
                parent=self.winfo_toplevel(),
            )
            if not confirmed:
                return
            result = clear_section_background_with_backup(
                self._draft,
                self._comp.package_path,
                readiness=readiness,
            )
        else:
            asset_label = self._selected_asset_label() or "wybrany asset"
            kind_pl = self._draft.kind_label_pl()
            confirmed = messagebox.askyesno(
                "Zapis lokalny",
                "\n".join([
                    f"Strefa: {self._draft.zone_display()}",
                    f"Typ: {kind_pl}",
                    f"Asset: {asset_label}",
                    "Dotyczy jednej sekcji section_background.",
                    "Zostanie utworzony backup index.json.",
                    "Bez Shopify · bez deploy.",
                    "",
                    "Kontynuować?",
                ]),
                parent=self.winfo_toplevel(),
            )
            if not confirmed:
                return
            result = set_section_background_with_ref_backup(
                self._draft,
                self._comp.package_path,
                readiness=readiness,
            )

        if not result.ok:
            if callable(self._on_status):
                self._on_status(result.message)
            return

        self._set_session_undo(result)
        self._refresh_readonly_sections()
        self._refresh_asset_selection_ui()
        dry_run = build_background_save_dry_run(self._draft, self._comp.package_path)
        readiness_after = evaluate_save_readiness(
            self._draft,
            self._comp.package_path,
            clear_intent=self._clear_plan_intent,
        )
        self._last_readiness = readiness_after
        extra: list[str] = [SAVE_LOCAL_STATUS]
        if result.backup_filename:
            extra.append(f"Backup: {result.backup_filename}")
        full_text = self._compose_save_plan_text(
            format_dry_run_summary(dry_run),
            readiness_after,
            extra_lines=tuple(extra),
        )
        if self._save_plan_body_label is not None:
            self._save_plan_body_label.configure(
                text=full_text,
                text_color=theme.TextPrimary,
            )
        self._update_save_local_button(readiness_after)
        if callable(self._on_status):
            self._on_status(SAVE_LOCAL_STATUS)

    def _on_undo_last_write(self) -> None:
        saved = self._last_successful_write
        if saved is None or not saved.ok or not saved.backup_filename:
            return

        confirmed = messagebox.askyesno(
            "Cofnij ostatni zapis",
            "\n".join([
                f"Przywróci tło strefy {saved.zone_label}",
                f"z backupu {saved.backup_filename}.",
                "Dotyczy jednej sekcji section_background.",
                "Bez Shopify · bez deploy.",
                "",
                "Kontynuować?",
            ]),
            parent=self.winfo_toplevel(),
        )
        if not confirmed:
            return

        result = restore_section_background_from_backup(
            package_path=self._comp.package_path,
            backup_filename=saved.backup_filename,
            section_key=saved.section_key,
            zone_field_id=saved.zone_field_id,
            zone_label=saved.zone_label,
            expected_variant_id=self._last_save_variant_id,
        )
        if not result.ok:
            if callable(self._on_status):
                self._on_status(result.message)
            return

        self._clear_session_undo()
        try:
            self._refresh_readonly_sections()
        except Exception:
            if callable(self._on_status):
                self._on_status(
                    f"{UNDO_RESTORE_STATUS} · odświeżenie panelu nie powiodło się",
                )
            return

        dry_run = build_background_save_dry_run(self._draft, self._comp.package_path)
        readiness = evaluate_save_readiness(
            self._draft,
            self._comp.package_path,
            clear_intent=self._clear_plan_intent,
        )
        self._last_readiness = readiness
        full_text = self._compose_save_plan_text(
            format_dry_run_summary(dry_run),
            readiness,
            extra_lines=(UNDO_RESTORE_STATUS,),
        )
        if self._save_plan_body_label is not None:
            self._save_plan_body_label.configure(
                text=full_text,
                text_color=theme.TextPrimary,
            )
        self._update_save_local_button(readiness)
        if callable(self._on_status):
            self._on_status(UNDO_RESTORE_STATUS)

    def _on_zone_selected(self, label: str) -> None:
        field_id = self._zone_map.get(label)
        if field_id:
            self._draft.set_zone(field_id)
            self._refresh_draft_ui()

    def _on_kind_selected(self, label: str) -> None:
        kind = self._kind_map.get(label)
        if kind is not None:
            self._draft.set_kind(kind)
            self._refresh_draft_ui()

    def _clear_draft(self) -> None:
        self._draft.clear()
        self._refresh_draft_ui(notify=False)
        if callable(self._on_status):
            self._on_status("Draft wyczyszczony — niezapisany")

    def _refresh_draft_ui(self, *, notify: bool = True) -> None:
        selected_label = self._selected_asset_label()
        if self._draft_summary_label is not None:
            self._draft_summary_label.configure(
                text=self._draft.format_summary(selected_label=selected_label),
            )
        self._refresh_asset_selection_ui()
        self._refresh_draft_preview()
        if notify and callable(self._on_status):
            if self._draft.is_empty():
                self._on_status(_DRAFT_STATUS_MSG)
            else:
                self._on_status(_PREVIEW_STATUS_MSG)

    def _refresh_draft_preview(self) -> None:
        if self._preview_body_label is None:
            return
        if self._draft.is_empty():
            self._preview_body_label.configure(
                text=PREVIEW_EMPTY_COPY,
                text_color=theme.TextMuted,
            )
            if self._preview_placeholder_frame is not None:
                self._preview_placeholder_frame.pack_forget()
            if self._preview_disclaimer_label is not None:
                self._preview_disclaimer_label.pack_forget()
            return

        self._preview_body_label.configure(
            text=format_preview_body(
                self._draft,
                selected_label=self._selected_asset_label(),
            ),
            text_color=theme.TextPrimary,
        )
        if self._preview_placeholder_label is not None:
            placeholder = self._selected_asset_label()
            if placeholder is None:
                placeholder = placeholder_label_for_kind(self._draft.asset_kind)
            self._preview_placeholder_label.configure(text=placeholder)
        if self._preview_placeholder_frame is not None:
            self._preview_placeholder_frame.pack(fill="x", padx=16, pady=(0, 8))
        if self._preview_disclaimer_label is not None:
            self._preview_disclaimer_label.pack(fill="x", padx=16, pady=(0, 12))

    def on_hide(self) -> None:
        self._draft.clear()
        self._clear_session_undo()
