"""Panel tła w Studio Preview (F4.2+) — read-only, draft F5.2, preview F5.3, dry-run F5.4a, readiness F5.4b0, writer F5.4b1."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.studio.background_asset_types import AssetKind
from giclee_app.studio.background_asset_shell import asset_library_rows
from giclee_app.studio.background_capabilities import (
    BackgroundCapability,
    tier_display,
)
from giclee_app.studio.background_draft_preview import (
    PREVIEW_BADGE,
    PREVIEW_DISCLAIMER,
    PREVIEW_EMPTY_COPY,
    PREVIEW_SECTION_TITLE,
    placeholder_label_for_kind,
    preview_enabled_for_folder,
)
from giclee_app.studio.background_draft_state import (
    CLEAR_DRAFT_LABEL,
    DRAFT_BADGE,
    DRAFT_DISCLAIMER,
    DRAFT_SECTION_TITLE,
    BackgroundDraftState,
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
    SAVE_LOCAL_LABEL,
    SAVE_LOCAL_STATUS,
    SaveReadiness,
    evaluate_save_readiness,
    format_readiness_block,
)
from giclee_app.studio.background_save_writer import clear_section_background_with_backup
from giclee_app.studio.background_state import summarize_background_state

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
        self._readonly_body_labels: dict[str, ctk.CTkLabel] = {}
        self._last_readiness: SaveReadiness | None = None
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
            command=self._on_save_local_clear,
        )
        self._save_local_button.pack(anchor="w", padx=16, pady=(0, 12))
        self._save_local_button.pack_forget()

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
        show = (
            self._clear_plan_intent
            and readiness.ready
            and readiness.operation == "clear"
        )
        if show:
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
        readiness_block = format_readiness_block(
            readiness.summary,
            clear_ready=clear_ready,
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

    def _on_save_local_clear(self) -> None:
        self._on_clear_plan_toggled()
        readiness = evaluate_save_readiness(
            self._draft,
            self._comp.package_path,
            clear_intent=self._clear_plan_intent,
        )
        if not (readiness.ready and readiness.operation == "clear"):
            if callable(self._on_status):
                self._on_status("Zapis zablokowany — tylko operacja clear.")
            return

        zone_label = self._draft.zone_display()
        confirmed = messagebox.askyesno(
            "Zapis lokalny",
            "\n".join([
                f"Operacja: wyczyść tło w strefie {zone_label}",
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
        if not result.ok:
            if callable(self._on_status):
                self._on_status(result.message)
            return

        self._refresh_readonly_sections()
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
        if self._draft_summary_label is not None:
            self._draft_summary_label.configure(text=self._draft.format_summary())
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

        meta = "\n".join([
            PREVIEW_BADGE,
            f"Strefa: {self._draft.zone_display()}",
            f"Typ: {self._draft.kind_label_pl()}",
        ])
        self._preview_body_label.configure(text=meta, text_color=theme.TextPrimary)
        if self._preview_placeholder_label is not None:
            self._preview_placeholder_label.configure(
                text=placeholder_label_for_kind(self._draft.asset_kind),
            )
        if self._preview_placeholder_frame is not None:
            self._preview_placeholder_frame.pack(fill="x", padx=16, pady=(0, 8))
        if self._preview_disclaimer_label is not None:
            self._preview_disclaimer_label.pack(fill="x", padx=16, pady=(0, 12))

    def on_hide(self) -> None:
        self._draft.clear()
