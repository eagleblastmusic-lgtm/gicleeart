"""Katalog workflow screen (F1+F2) — read-only shell, inventory + data map."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from giclee_app.studio.katalog_data_map import (
    F2_NEXT_NOTE,
    build_katalog_data_map,
    data_map_display_rows,
    f2_status_strip,
)
from giclee_app.studio.katalog_inventory import (
    DATA_MAP_WARNING,
    F1_READ_ONLY_NOTE,
    build_katalog_inventory,
    inventory_display_rows,
    workflow_summary,
)

from . import theme
from .widgets import SectionHeader

_REFRESH_LABEL = "Odśwież inventory / mapę danych"
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
        self._inventory_frame: ctk.CTkFrame | None = None
        self._datamap_frame: ctk.CTkFrame | None = None
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
        ).pack(fill="x", padx=24, pady=(0, 8))

        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(fill="x", padx=24, pady=(0, 8))
        for text in (
            "Parent workflow",
            "Katalog F1 inventory",
            "Katalog F2 data map",
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
        if self._inventory_frame is not None:
            inv = build_katalog_inventory(self._components_root)
            self._fill_rows(self._inventory_frame, inventory_display_rows(inv))
        if self._datamap_frame is not None:
            dm = build_katalog_data_map(self._components_root)
            self._fill_rows(self._datamap_frame, data_map_display_rows(dm))
        if self._on_status is not None:
            self._on_status("Katalog inventory + mapa danych odświeżone (read-only)")
