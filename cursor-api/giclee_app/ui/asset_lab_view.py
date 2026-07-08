"""Asset Lab workflow screen (F6.2) — read-only shell, launch-only."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import LaunchOutcome, launch
from giclee_app.studio.asset_lab_catalog import (
    AssetLabTool,
    LEGACY_BACKEND_BADGE,
    UNAVAILABLE_LABEL,
    status_strip,
    tools_in_order,
    workflow_summary,
)
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.perf import log_event, span
from giclee_app.studio.state import StudioState

from . import theme
from .widgets import AssetLabToolCard, SectionHeader

_GRID_COLS = 3
_ASSET_LAB_RENDER_BATCH_SIZE = 1
_ASSET_LAB_RENDER_BATCH_DELAY_MS = 16
_ASSET_LAB_FIRST_BATCH_DELAY_MS = 80
_ASSET_LAB_AUTO_FULL_CARDS_ENV = "GICLEE_ASSET_LAB_AUTO_FULL_CARDS"
_SHELL_DETAILS_LABEL = "Szczegóły"


def _asset_lab_auto_full_cards_enabled() -> bool:
    raw = os.environ.get(_ASSET_LAB_AUTO_FULL_CARDS_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


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
    uses_async_first_paint = True

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
        self._cards_grid: ctk.CTkFrame | None = None
        self._shells_rendered = False
        self._full_cards_ready = False
        self._render_card_index = 0
        self._full_upgrade_index = 0
        self._by_folder: dict[str, Component] = {}
        self._shell_meta: dict[int, tuple[AssetLabTool, Component | None, int, int]] = {}
        self._full_cards_upgraded: set[int] = set()
        self._build_shell()
        self.after(_ASSET_LAB_FIRST_BATCH_DELAY_MS, self._start_deferred_render_cards)

    def on_show(self, *, cache_hit: bool = False) -> None:
        log_event(
            "studio.asset_lab.on_show",
            cache_hit=cache_hit,
            tool_count=len(tools_in_order()),
            shells_rendered=self._shells_rendered,
            full_cards_ready=self._full_cards_ready,
        )

    def _build_shell(self) -> None:
        with span("studio.asset_lab.build_shell"):
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

        self._cards_grid = ctk.CTkFrame(self, fg_color="transparent")
        self._cards_grid.pack(fill="both", expand=True, padx=18, pady=(0, 16))
        for col in range(_GRID_COLS):
            self._cards_grid.grid_columnconfigure(col, weight=1, uniform="asset_lab")

        log_event("studio.asset_lab.visual.shell_ready")

    def _start_deferred_render_cards(self) -> None:
        if self._shells_rendered:
            return
        with span("studio.asset_lab.load_inventory"):
            self._by_folder = (
                self._component_index.by_folder if self._component_index is not None else {}
            )
        self._render_card_index = 0
        self._render_shell_batch()

    def _component_for_tool(self, tool: AssetLabTool) -> Component:
        comp = self._by_folder.get(tool.folder)
        if comp is not None:
            return comp
        return Component(
            folder_name=tool.folder,
            package_path=Path("."),
            name=tool.folder,
            description=tool.summary,
            mode="subprocess",
            color=theme.TextMuted,
        )

    def _build_tool_card_shell(
        self,
        parent: ctk.CTkFrame,
        *,
        index: int,
        tool: AssetLabTool,
        comp: Component,
        available: bool,
    ) -> ctk.CTkFrame:
        shell = ctk.CTkFrame(
            parent,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle if available else theme.TextMuted,
            height=140,
        )
        shell.pack_propagate(False)
        accent_color = comp.color if available else theme.TextMuted
        accent = ctk.CTkFrame(
            shell,
            width=theme.CardAccentWidth,
            fg_color=accent_color,
            corner_radius=0,
        )
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)
        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)
        ctk.CTkLabel(
            body,
            text=comp.name,
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary if available else theme.TextMuted,
            anchor="w",
        ).pack(fill="x")
        desc = (tool.summary or "")[:80]
        if len(tool.summary or "") > 80:
            desc += "…"
        ctk.CTkLabel(
            body,
            text=desc or comp.folder_name,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=220,
        ).pack(fill="x", pady=(6, 4))
        badges = ctk.CTkFrame(body, fg_color="transparent")
        badges.pack(fill="x", side="bottom")
        ctk.CTkLabel(
            badges,
            text=f"{comp.mode} · {tool.risk}",
            font=theme.get_font(10),
            text_color=theme.TextMuted,
        ).pack(side="left")
        details_btn = ctk.CTkButton(
            badges,
            text=_SHELL_DETAILS_LABEL,
            width=72,
            height=22,
            font=theme.get_font(9),
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=lambda idx=index: self._request_full_card(idx),
        )
        details_btn.pack(side="right")
        self._wire_shell_interactions(shell, index)
        log_event(
            "studio.asset_lab.card.shell_created",
            folder=tool.folder,
            available=available,
        )
        return shell

    def _wire_shell_interactions(self, shell: ctk.CTkFrame, index: int) -> None:
        def on_click(_event: object | None = None) -> None:
            self._request_full_card(index)

        shell.bind("<Button-1>", on_click)
        for child in shell.winfo_children():
            child.bind("<Button-1>", on_click)
            if isinstance(child, ctk.CTkFrame):
                for grandchild in child.winfo_children():
                    if isinstance(grandchild, ctk.CTkButton):
                        continue
                    grandchild.bind("<Button-1>", on_click)

    def _render_shell_batch(self) -> None:
        if self._cards_grid is None or self._shells_rendered:
            return
        tools = tools_in_order()
        start = self._render_card_index
        end = min(start + _ASSET_LAB_RENDER_BATCH_SIZE, len(tools))
        if start >= end:
            self._shells_rendered = True
            log_event("studio.asset_lab.visual.shell_cards_ready", card_count=len(tools))
            self._finish_shell_render_phase()
            return

        with span("studio.asset_lab.render_cards.shell_batch", start=start, end=end):
            for i in range(start, end):
                tool = tools[i]
                comp = self._component_for_tool(tool)
                available = tool.folder in self._by_folder
                row, col = divmod(i, _GRID_COLS)
                shell = self._build_tool_card_shell(
                    self._cards_grid,
                    index=i,
                    tool=tool,
                    comp=comp,
                    available=available,
                )
                shell.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
                self._shell_meta[i] = (tool, self._by_folder.get(tool.folder), row, col)

        log_event(
            "studio.asset_lab.render_cards.shell_batch",
            start=start,
            end=end,
            total=len(tools),
        )
        self._render_card_index = end
        if self._render_card_index >= len(tools):
            self._shells_rendered = True
            log_event("studio.asset_lab.visual.shell_cards_ready", card_count=len(tools))
            self._finish_shell_render_phase()
            return
        self.after(_ASSET_LAB_RENDER_BATCH_DELAY_MS, self._render_shell_batch)

    def _finish_shell_render_phase(self) -> None:
        if _asset_lab_auto_full_cards_enabled():
            self.after(_ASSET_LAB_RENDER_BATCH_DELAY_MS, self._start_full_card_upgrades)
            return
        log_event("studio.asset_lab.card.full_auto_disabled")
        self._full_cards_ready = True
        log_event("studio.asset_lab.visual.full_ready", card_count=len(tools_in_order()), on_demand=True)

    def _request_full_card(self, index: int) -> None:
        if index in self._full_cards_upgraded:
            return
        log_event(
            "studio.asset_lab.card.full_requested",
            index=index,
            folder=tools_in_order()[index].folder if index < len(tools_in_order()) else "",
        )
        self._upgrade_card_to_full(index, on_demand=True)

    def _start_full_card_upgrades(self) -> None:
        if self._full_cards_ready:
            return
        self._full_upgrade_index = 0
        self.after(_ASSET_LAB_RENDER_BATCH_DELAY_MS, self._upgrade_next_card_to_full)

    def _upgrade_next_card_to_full(self) -> None:
        if self._cards_grid is None or self._full_cards_ready:
            return
        tools = tools_in_order()
        index = self._full_upgrade_index
        if index >= len(tools):
            self._full_cards_ready = True
            log_event("studio.asset_lab.visual.full_ready", card_count=len(tools))
            return
        if index not in self._full_cards_upgraded:
            self._upgrade_card_to_full(index, on_demand=False)
        self._full_upgrade_index += 1
        if self._full_upgrade_index >= len(tools):
            self._full_cards_ready = True
            log_event("studio.asset_lab.visual.full_ready", card_count=len(tools))
            return
        self.after(_ASSET_LAB_RENDER_BATCH_DELAY_MS, self._upgrade_next_card_to_full)

    def _upgrade_card_to_full(self, index: int, *, on_demand: bool) -> None:
        if self._cards_grid is None or index in self._full_cards_upgraded:
            return
        meta = self._shell_meta.get(index)
        if meta is None:
            return
        tool, comp, row, col = meta
        available = comp is not None
        display_comp = comp if comp is not None else self._component_for_tool(tool)
        for child in self._cards_grid.grid_slaves(row=row, column=col):
            child.destroy()
        span_name = (
            "studio.asset_lab.render_cards.full_on_demand"
            if on_demand
            else "studio.asset_lab.render_cards.full_deferred"
        )
        with span(span_name, index=index):
            if available:
                card = AssetLabToolCard(
                    self._cards_grid,
                    display_comp,
                    summary=tool.summary,
                    risk=tool.risk,
                    on_launch=self._on_launch_click,
                    available=True,
                    legacy_badge=LEGACY_BACKEND_BADGE,
                    unavailable_label=UNAVAILABLE_LABEL,
                )
            else:
                card = AssetLabToolCard(
                    self._cards_grid,
                    display_comp,
                    summary=tool.summary,
                    risk=tool.risk,
                    on_launch=self._on_launch_click,
                    available=False,
                    legacy_badge=LEGACY_BACKEND_BADGE,
                    unavailable_label=UNAVAILABLE_LABEL,
                )
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        self._full_cards_upgraded.add(index)
        if on_demand:
            log_event(
                "studio.asset_lab.card.full_created_on_demand",
                folder=tool.folder,
                index=index,
            )
        else:
            log_event(
                "studio.asset_lab.card.full_created",
                folder=tool.folder,
                index=index,
            )
            log_event(
                "studio.asset_lab.render_cards.full_deferred",
                index=index,
                total=len(tools_in_order()),
            )

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
