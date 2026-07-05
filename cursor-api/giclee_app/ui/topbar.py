"""Górny pasek statusów Studio."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from giclee_app.studio import status_providers

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

        self.refresh(fast=True)

    def set_breadcrumb(self, text: str) -> None:
        self._breadcrumb.configure(text=text)

    def refresh(self, *, fast: bool = False) -> None:
        """fast=True: shopify/github/gpt od razu; theme_dev po after_idle."""
        st_shopify = status_providers.shopify_status()
        st_github = status_providers.github_status()
        st_gpt = status_providers.gpt_snapshot_status()

        self._apply_pill("shopify", st_shopify)
        self._apply_pill("github", st_github)
        self._apply_pill("gpt_snapshot", st_gpt)

        theme_pill = self._pills.get("theme_dev")
        if theme_pill is not None:
            if fast:
                theme_pill.update_status(None, "Theme Dev", "sprawdzanie…")
                root = self.winfo_toplevel()
                try:
                    root.after_idle(self._refresh_theme_dev)
                except tk.TclError:
                    self._refresh_theme_dev()
            else:
                self._refresh_theme_dev()

    def _refresh_theme_dev(self) -> None:
        pill = self._pills.get("theme_dev")
        if pill is None:
            return
        st = status_providers.theme_dev_status()
        pill.update_status(st.ok, st.label, st.detail)

    def _apply_pill(self, key: str, st: status_providers.StatusResult) -> None:
        pill = self._pills.get(key)
        if pill is None:
            return
        pill.update_status(st.ok, st.label, st.detail)
