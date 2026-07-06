"""Katalog workflow screen (F1) — read-only shell, inventory only."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from giclee_app.studio.katalog_inventory import (
    DATA_MAP_WARNING,
    F1_READ_ONLY_NOTE,
    NEXT_PHASE_NOTE,
    build_katalog_inventory,
    inventory_display_rows,
    status_strip,
    workflow_summary,
)

from . import theme
from .widgets import SectionHeader

_REFRESH_LABEL = "Odśwież inventory"
_BACK_LABEL = "Wróć do huba"


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
        self._rows_frame: ctk.CTkFrame | None = None
        self._build_shell()
        self._refresh_inventory()

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
            text=status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(fill="x", padx=24, pady=(0, 8))
        for text in (
            "Parent workflow",
            "Katalog rebuild: F1",
            "Tło do Bio: absorbed subflow",
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
            width=160,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._refresh_inventory,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        self._rows_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._rows_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (DATA_MAP_WARNING, F1_READ_ONLY_NOTE, NEXT_PHASE_NOTE):
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

    def _refresh_inventory(self) -> None:
        report = build_katalog_inventory(self._components_root)
        rows = inventory_display_rows(report)
        if self._rows_frame is not None:
            for child in self._rows_frame.winfo_children():
                child.destroy()
            for label, value in rows:
                row = ctk.CTkFrame(self._rows_frame, fg_color="transparent")
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
        if self._on_status is not None:
            self._on_status("Katalog inventory odświeżone (read-only)")
