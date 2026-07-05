"""Widok Dashboard — read-only + mocki F1."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

import customtkinter as ctk

from giclee_app import __version__
from giclee_app.studio import status_providers

from . import theme
from .widgets import SectionHeader, StatCard, StatusPill


class DashboardView(ctk.CTkScrollableFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_refresh_activity: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._on_refresh_activity = on_refresh_activity
        self._activity_box: ctk.CTkTextbox | None = None
        self._status_pills: list[StatusPill] = []
        self._build()

    def _build(self) -> None:
        today = date.today().strftime("%A, %d.%m.%Y")
        ctk.CTkLabel(
            self,
            text="Dzień dobry",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(
            self,
            text=f"{today}  ·  Fine Art Control Center",
            font=ctk.CTkFont(size=12),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(4, 16))

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=24, pady=(0, 16))
        for i in range(4):
            stats_row.columnconfigure(i, weight=1, uniform="stat")

        total, visible = status_providers.component_counts()
        cards = [
            ("Komponenty", str(total), False),
            ("Widoczne", str(visible), False),
            ("Wersja", __version__, False),
            ("Alerty", "0 krytycznych", True),
        ]
        for i, (title, val, muted) in enumerate(cards):
            card = StatCard(stats_row, title, val, muted=muted)
            card.grid(row=0, column=i, padx=(0 if i == 0 else 6, 0), sticky="nsew")

        columns = ctk.CTkFrame(self, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        columns.columnconfigure(0, weight=3)
        columns.columnconfigure(1, weight=2)

        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        SectionHeader(left, "Ostatnie akcje").pack(fill="x", pady=(0, 8))
        self._activity_box = ctk.CTkTextbox(
            left, height=200, fg_color=theme.PanelBg, text_color=theme.TextPrimary,
            font=ctk.CTkFont(family=theme.FontMono[0], size=11),
        )
        self._activity_box.pack(fill="both", expand=True)
        ctk.CTkButton(
            left,
            text="Odśwież",
            width=80,
            height=28,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self.refresh_activity,
        ).pack(anchor="e", pady=(6, 0))

        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        SectionHeader(right, "Dzisiejsze priorytety").pack(fill="x", pady=(0, 8))
        mock_frame = ctk.CTkFrame(
            right, fg_color=theme.PanelBg, corner_radius=8,
            border_width=1, border_color=theme.BorderSubtle,
        )
        mock_frame.pack(fill="both", expand=True)
        for line in (
            "— Plan marketingowy (F2)",
            "— Zamówienia oczekujące (F2)",
            "— Review snapshot motywu (F2)",
        ):
            ctk.CTkLabel(
                mock_frame,
                text=line,
                font=ctk.CTkFont(size=12),
                text_color=theme.TextMuted,
                anchor="w",
            ).pack(fill="x", padx=14, pady=6)

        SectionHeader(self, "Status operacyjny").pack(fill="x", padx=24, pady=(8, 8))
        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=24, pady=(0, 12))
        for fn in (
            status_providers.shopify_status,
            status_providers.theme_dev_status,
            status_providers.github_status,
            status_providers.gpt_snapshot_status,
        ):
            st = fn()
            pill = StatusPill(status_row, st.label, ok=st.ok, detail=st.detail)
            pill.pack(side="left", padx=(0, 8))
            self._status_pills.append(pill)

        SectionHeader(self, "Szybkie akcje").pack(fill="x", padx=24, pady=(8, 8))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 24))
        for label in ("Theme dev…", "Token setup", "Dziennik akcji"):
            ctk.CTkButton(
                actions,
                text=label,
                state="disabled",
                fg_color=theme.PanelBg,
                text_color=theme.TextMuted,
                width=120,
                height=32,
            ).pack(side="left", padx=(0, 8))

        self.refresh_activity()

    def refresh_activity(self) -> None:
        if self._activity_box is None:
            return
        lines = status_providers.activity_log_lines(8)
        text = "\n".join(lines) if lines else "Brak wpisów w dzienniku."
        self._activity_box.configure(state="normal")
        self._activity_box.delete("1.0", "end")
        self._activity_box.insert("1.0", text)
        self._activity_box.configure(state="disabled")
