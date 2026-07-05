"""Read-only panel tła w Studio Preview (F4.2) — bez edycji i zapisu."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import Component
from giclee_app.studio.background_capabilities import (
    BackgroundCapability,
    tier_display,
)

from . import theme
from .widgets import SectionHeader

_F4_3_NOTE = (
    "Edycja tła będzie dostępna w F4.3+. "
    "Ten panel pokazuje wyłącznie informacje o capability — bez zapisu."
)


def panel_rows(
    cap: BackgroundCapability,
    *,
    component_name: str,
) -> list[tuple[str, str]]:
    """Sekcje read-only panelu — testowalne bez Tk."""
    _ = component_name
    return [
        ("Typ tła", f"{cap.label}\n{tier_display(cap.tier)}"),
        ("Źródło", cap.source_hint),
        ("Kontekst inline", cap.inline_note),
        ("Status", "read-only"),
        ("Co dalej", _F4_3_NOTE),
    ]


class BackgroundPanelView(ctk.CTkFrame):
    """Lekki widok informacyjny tła — transient host w launcher_studio."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        cap: BackgroundCapability,
        *,
        on_back: Callable[[], None],
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._comp = comp
        self._cap = cap
        self._on_back = on_back
        self._on_status = on_status
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

        for row_idx, (title, body) in enumerate(
            panel_rows(self._cap, component_name=self._comp.name),
            start=1,
        ):
            panel = ctk.CTkFrame(
                scroll,
                fg_color=theme.PanelBg,
                corner_radius=8,
                border_width=1,
                border_color=theme.BorderSubtle,
            )
            panel.grid(row=row_idx, column=0, sticky="ew", pady=(0, 10))
            panel.grid_columnconfigure(0, weight=1)
            SectionHeader(panel, title).pack(fill="x", padx=16, pady=(12, 4))
            ctk.CTkLabel(
                panel,
                text=body,
                font=theme.get_font(12),
                text_color=theme.TextMuted,
                anchor="nw",
                justify="left",
                wraplength=560,
            ).pack(fill="x", padx=16, pady=(0, 12))

    def on_hide(self) -> None:
        pass
