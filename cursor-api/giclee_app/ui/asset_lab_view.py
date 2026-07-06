"""Asset Lab workflow screen (F6.2) — read-only shell, launch-only."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import LaunchOutcome, launch
from giclee_app.studio.asset_lab_catalog import (
    LEGACY_BACKEND_BADGE,
    UNAVAILABLE_LABEL,
    status_strip,
    tools_in_order,
    workflow_summary,
)
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.state import StudioState

from . import theme
from .widgets import AssetLabToolCard, SectionHeader

_GRID_COLS = 3


def tool_card_rows(
    *,
    by_folder: dict[str, Component] | None = None,
) -> list[dict[str, str | bool]]:
    """Testowalne wiersze kart — bez Tk."""
    rows: list[dict[str, str | bool]] = []
    for tool in tools_in_order():
        comp = (by_folder or {}).get(tool.folder)
        rows.append({
            "folder": tool.folder,
            "summary": tool.summary,
            "risk": tool.risk,
            "available": comp is not None,
            "mode": comp.mode if comp is not None else "",
            "name": comp.name if comp is not None else tool.folder,
        })
    return rows


class AssetLabView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        component_index: StudioComponentIndex | None = None,
        studio_state: StudioState | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._component_index = component_index
        self._studio_state = studio_state
        self._on_status = on_status
        self._build_shell()

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))
        SectionHeader(header, "Asset Lab").pack(fill="x")
        ctk.CTkLabel(
            header,
            text=workflow_summary(),
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x", pady=(6, 4))
        ctk.CTkLabel(
            header,
            text=status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        for col in range(_GRID_COLS):
            grid.grid_columnconfigure(col, weight=1, uniform="asset_lab")

        by_folder = (
            self._component_index.by_folder if self._component_index is not None else {}
        )
        for i, tool in enumerate(tools_in_order()):
            comp = by_folder.get(tool.folder)
            row, col = divmod(i, _GRID_COLS)
            if comp is not None:
                card = AssetLabToolCard(
                    grid,
                    comp,
                    summary=tool.summary,
                    risk=tool.risk,
                    on_launch=self._on_launch_click,
                    available=True,
                    legacy_badge=LEGACY_BACKEND_BADGE,
                    unavailable_label=UNAVAILABLE_LABEL,
                )
            else:
                placeholder = Component(
                    folder_name=tool.folder,
                    package_path=Path("."),
                    name=tool.folder,
                    description=tool.summary,
                    mode="subprocess",
                    color=theme.TextMuted,
                )
                card = AssetLabToolCard(
                    grid,
                    placeholder,
                    summary=tool.summary,
                    risk=tool.risk,
                    on_launch=self._on_launch_click,
                    available=False,
                    legacy_badge=LEGACY_BACKEND_BADGE,
                    unavailable_label=UNAVAILABLE_LABEL,
                )
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

    def _on_launch_click(self, comp: Component) -> None:
        if comp.mode != "subprocess":
            root = self.winfo_toplevel()
            messagebox.showinfo(
                comp.name,
                "Asset Lab obsługuje tylko narzędzia subprocess.",
                parent=root,
            )
            return
        result = launch(comp, on_status=self._on_status)
        if result.outcome == LaunchOutcome.OK:
            if self._studio_state is not None:
                self._studio_state.record_launch(comp)
                self._studio_state.save()
        elif result.outcome in (
            LaunchOutcome.ERROR,
            LaunchOutcome.NO_PYTHON,
            LaunchOutcome.NO_URL,
        ):
            root = self.winfo_toplevel()
            messagebox.showerror(comp.name, result.message, parent=root)
