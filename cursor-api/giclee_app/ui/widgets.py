"""Wspólne widgety Studio."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from giclee_app.component_loader import Component

from . import theme


def status_color(ok: bool | None) -> str:
    if ok is True:
        return theme.StatusOk
    if ok is False:
        return theme.StatusErr
    return theme.StatusUnknown


class StatusPill(ctk.CTkFrame):
    """Kompaktowy wskaźnik statusu w topbarze."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        *,
        ok: bool | None = None,
        detail: str = "",
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.PanelBg,
            corner_radius=6,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        self._dot = ctk.CTkLabel(self, text="●", width=16, text_color=status_color(ok))
        self._dot.pack(side="left", padx=(8, 2), pady=6)
        self._title = ctk.CTkLabel(
            self, text=title, font=theme.get_font(12, "bold"),
            text_color=theme.TextPrimary,
        )
        self._title.pack(side="left", padx=(0, 8), pady=6)

    def update_status(self, ok: bool | None, title: str, detail: str = "") -> None:
        self._dot.configure(text_color=status_color(ok))
        self._title.configure(text=title)
        self.tooltip_text = detail


class ComponentCard(ctk.CTkFrame):
    """Karta komponentu w hubie."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        comp: Component,
        *,
        on_click: Callable[[Component], None],
        on_right_click: Callable[[Component, object], None] | None = None,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.CardBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
            height=140,
        )
        self.pack_propagate(False)
        self._comp = comp
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._normal_bg = theme.CardBg
        self._hover_bg = theme.CardHover

        accent = ctk.CTkFrame(
            master=self, width=theme.CardAccentWidth, fg_color=comp.color, corner_radius=0,
        )
        accent.pack(side="left", fill="y")
        accent.pack_propagate(False)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=10)

        title_row = ctk.CTkFrame(body, fg_color="transparent")
        title_row.pack(fill="x")
        if comp.icon:
            ctk.CTkLabel(
                title_row, text=comp.icon, font=theme.get_font(18), width=28,
            ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text=comp.name,
            font=theme.get_font(14, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        desc = (comp.description or "")[:120]
        if len(comp.description or "") > 120:
            desc += "…"
        ctk.CTkLabel(
            body,
            text=desc or comp.folder_name,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=260,
        ).pack(fill="x", pady=(6, 4))

        badges = ctk.CTkFrame(body, fg_color="transparent")
        badges.pack(fill="x", side="bottom")
        ctk.CTkLabel(
            badges,
            text=comp.mode,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            fg_color=theme.AppBg,
            corner_radius=4,
            width=70,
            height=20,
        ).pack(side="left", padx=(0, 6))
        if comp.hidden:
            ctk.CTkLabel(
                badges,
                text="ukryty",
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                fg_color=theme.AppBg,
                corner_radius=4,
                width=50,
                height=20,
            ).pack(side="left")

        for w in (self, body, title_row, badges):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._handle_click)
            if on_right_click:
                w.bind("<Button-3>", self._handle_right)

    @staticmethod
    def _on_enter(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCard):
                w.configure(fg_color=w._hover_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    @staticmethod
    def _on_leave(event: object) -> None:
        w = event.widget  # type: ignore[attr-defined]
        while w is not None:
            if isinstance(w, ComponentCard):
                w.configure(fg_color=w._normal_bg)
                break
            w = w.master  # type: ignore[attr-defined]

    def _handle_click(self, _event: object) -> None:
        self._on_click(self._comp)

    def _handle_right(self, event: object) -> None:
        if self._on_right_click:
            self._on_right_click(self._comp, event)


class StatCard(ctk.CTkFrame):
    """Kafelek statystyki na dashboardzie."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        title: str,
        value: str,
        *,
        muted: bool = False,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        ctk.CTkLabel(
            self,
            text=title,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 0))
        ctk.CTkLabel(
            self,
            text=value,
            font=theme.get_font(22 if not muted else 18, "bold", brand=not muted),
            text_color=theme.TextMuted if muted else theme.TextPrimary,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(4, 12))


class SectionHeader(ctk.CTkLabel):
    def __init__(self, master: ctk.CTkBaseClass, text: str) -> None:
        super().__init__(
            master,
            text=text,
            font=theme.get_font(16, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
