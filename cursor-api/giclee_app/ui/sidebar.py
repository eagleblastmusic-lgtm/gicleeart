"""Lewy sidebar nawigacji Studio."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.studio.categories import NAV_CATEGORIES

from . import theme


class Sidebar(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        version: str,
        on_select: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            width=theme.SidebarWidth,
            fg_color=theme.SidebarBg,
            corner_radius=0,
        )
        self.pack_propagate(False)
        self._on_select = on_select
        self._active_id = "dashboard"
        self._buttons: dict[str, ctk.CTkButton] = {}

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(20, 8))
        ctk.CTkLabel(
            brand,
            text="GicleeApp",
            font=ctk.CTkFont(family=theme.FontBrand[0], size=18, weight="bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            brand,
            text="Studio",
            font=ctk.CTkFont(size=11),
            text_color=theme.AccentGold,
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            brand,
            text=theme.PREVIEW_BADGE,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=64,
            height=22,
        ).pack(anchor="w", pady=(6, 0))

        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(fill="both", expand=True, padx=8, pady=8)

        for cat_id, label, icon in NAV_CATEGORIES:
            btn = ctk.CTkButton(
                nav,
                text=f"  {icon}  {label}",
                anchor="w",
                height=36,
                fg_color="transparent",
                hover_color=theme.SidebarHover,
                text_color=theme.TextPrimary,
                font=ctk.CTkFont(size=13),
                command=lambda cid=cat_id: self._select(cid),
            )
            btn.pack(fill="x", pady=2)
            self._buttons[cat_id] = btn

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(
            foot,
            text="Polling Shopify działa\nw klasycznym launcherze",
            font=ctk.CTkFont(size=10),
            text_color=theme.TextMuted,
            justify="left",
            anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(
            foot,
            text=f"v{version}",
            font=ctk.CTkFont(size=10),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        self._highlight("dashboard")

    def _select(self, category_id: str) -> None:
        self._highlight(category_id)
        self._on_select(category_id)

    def _highlight(self, category_id: str) -> None:
        self._active_id = category_id
        for cid, btn in self._buttons.items():
            if cid == category_id:
                btn.configure(
                    fg_color=theme.SidebarActive,
                    border_width=0,
                )
            else:
                btn.configure(fg_color="transparent")

    def set_active(self, category_id: str) -> None:
        self._highlight(category_id)
