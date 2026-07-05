"""Górny pasek statusów Studio."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.studio import status_providers

from . import theme
from .widgets import StatusPill


class Topbar(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_refresh: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            height=theme.TopbarHeight,
            fg_color=theme.PanelBg,
            corner_radius=0,
        )
        self.pack_propagate(False)
        self._breadcrumb = ctk.CTkLabel(
            self,
            text="Dashboard",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        self._breadcrumb.pack(side="left", padx=(20, 12), pady=10)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="right", padx=12, pady=6)

        self._pills: dict[str, StatusPill] = {}
        for key, title in (
            ("shopify", "Shopify"),
            ("theme_dev", "Theme Dev"),
            ("github", "GitHub"),
            ("gpt_snapshot", "GPT"),
        ):
            pill = StatusPill(right, title)
            pill.pack(side="left", padx=4)
            self._pills[key] = pill

        ctk.CTkButton(
            right,
            text="↻",
            width=32,
            height=28,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            command=self.refresh,
        ).pack(side="left", padx=(8, 0))

        self.refresh()

    def set_breadcrumb(self, text: str) -> None:
        self._breadcrumb.configure(text=text)

    def refresh(self) -> None:
        statuses = status_providers.refresh_all_topbar()
        mapping = {
            "shopify": ("Shopify", statuses["shopify"]),
            "theme_dev": ("Theme Dev", statuses["theme_dev"]),
            "github": ("GitHub", statuses["github"]),
            "gpt_snapshot": ("GPT", statuses["gpt_snapshot"]),
        }
        for key, (short, st) in mapping.items():
            pill = self._pills.get(key)
            if pill is None:
                continue
            label = st.label if st.label else short
            pill.update_status(st.ok, label, st.detail)
