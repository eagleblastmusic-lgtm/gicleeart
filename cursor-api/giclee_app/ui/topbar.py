"""Górny pasek statusów Studio."""

from __future__ import annotations

import customtkinter as ctk

from giclee_app.studio import status_providers
from giclee_app.studio.bg import run_async

from . import theme
from .widgets import StatusPill


class Topbar(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_refresh: object = None,
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
            font=theme.get_font(14, "bold"),
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

        self._refresh_running = False
        self.refresh(fast=True)

    def set_breadcrumb(self, text: str) -> None:
        self._breadcrumb.configure(text=text)

    def refresh(self, *, fast: bool = False) -> None:
        """Statusy zbierane w wątku roboczym — UI nie blokuje się na IO/subprocess."""
        if self._refresh_running:
            return
        self._refresh_running = True
        for key, title in (
            ("shopify", "Shopify"),
            ("theme_dev", "Theme Dev"),
            ("github", "GitHub"),
            ("gpt_snapshot", "GPT"),
        ):
            pill = self._pills.get(key)
            if pill is not None:
                pill.update_status(None, title, "sprawdzanie…")
        run_async(
            self,
            status_providers.refresh_all_topbar,
            self._apply_statuses,
            on_error=lambda _exc: self._finish_refresh(),
        )

    def _apply_statuses(self, statuses: dict[str, status_providers.StatusResult]) -> None:
        for key, st in statuses.items():
            self._apply_pill(key, st)
        self._finish_refresh()

    def _finish_refresh(self) -> None:
        self._refresh_running = False

    def _apply_pill(self, key: str, st: status_providers.StatusResult) -> None:
        pill = self._pills.get(key)
        if pill is None:
            return
        pill.update_status(st.ok, st.label, st.detail)
