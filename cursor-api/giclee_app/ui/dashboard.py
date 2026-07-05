"""Widok Dashboard — read-only F2 (statusy, recent, pinned, safe quick actions)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from giclee_app import __version__
from giclee_app.component_loader import Component
from giclee_app.launcher_delegate import LaunchOutcome, launch
from giclee_app.runtime import get_component_cwd
from giclee_app.studio import status_providers
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.studio.state import StudioState
from giclee_app.studio.status_providers import StatusResult

from . import theme
from .widgets import CompactComponentChip, SectionHeader, StatCard, StatusPill

_DOCS_PATH = Path(__file__).resolve().parents[1] / "docs" / "studio-preview.md"


class DashboardView(ctk.CTkScrollableFrame):
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
        self._activity_box: ctk.CTkTextbox | None = None
        self._status_pills: list[StatusPill] = []
        self._stat_cards: dict[str, StatCard] = {}
        self._pinned_row: ctk.CTkFrame | None = None
        self._recent_row: ctk.CTkFrame | None = None
        self._theme_pill: StatusPill | None = None
        self._build()

    def _build(self) -> None:
        today = date.today().strftime("%A, %d.%m.%Y")
        ctk.CTkLabel(
            self,
            text="Dzień dobry",
            font=theme.get_font(24, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(20, 0))
        ctk.CTkLabel(
            self,
            text=f"{today}  ·  Fine Art Control Center",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(4, 12))

        status_row = ctk.CTkFrame(self, fg_color="transparent")
        status_row.pack(fill="x", padx=24, pady=(0, 12))
        shop_pill = StatusPill(status_row, "Shopify", ok=None, detail="")
        shop_pill.pack(side="left", padx=(0, 8))
        self._status_pills.append(shop_pill)
        self._theme_pill = StatusPill(status_row, "Theme Dev", ok=None, detail="sprawdzanie…")
        self._theme_pill.pack(side="left", padx=(0, 8))
        self._status_pills.append(self._theme_pill)
        studio_pill = StatusPill(
            status_row,
            f"Studio v{__version__}",
            ok=True if status_providers.customtkinter_available() else False,
            detail="CustomTkinter",
        )
        studio_pill.pack(side="left", padx=(0, 8))
        self._status_pills.append(studio_pill)

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.pack(fill="x", padx=24, pady=(0, 16))
        for i in range(4):
            stats_row.columnconfigure(i, weight=1, uniform="stat")
        stat_defs = (
            ("components", "Komponenty"),
            ("shopify", "Shopify"),
            ("theme", "Theme"),
            ("orders", "Zamówienia"),
        )
        for i, (key, title) in enumerate(stat_defs):
            card = StatCard(stats_row, title, "—")
            card.grid(row=0, column=i, padx=(0 if i == 0 else 6, 0), sticky="nsew")
            self._stat_cards[key] = card

        SectionHeader(self, "Przypięte").pack(fill="x", padx=24, pady=(0, 6))
        self._pinned_row = ctk.CTkFrame(self, fg_color="transparent")
        self._pinned_row.pack(fill="x", padx=24, pady=(0, 12))

        SectionHeader(self, "Ostatnio używane").pack(fill="x", padx=24, pady=(0, 6))
        self._recent_row = ctk.CTkFrame(self, fg_color="transparent")
        self._recent_row.pack(fill="x", padx=24, pady=(0, 16))

        columns = ctk.CTkFrame(self, fg_color="transparent")
        columns.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        columns.columnconfigure(0, weight=1)

        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew")
        SectionHeader(left, "Ostatnie akcje").pack(fill="x", pady=(0, 8))
        self._activity_box = ctk.CTkTextbox(
            left,
            height=180,
            fg_color=theme.PanelBg,
            text_color=theme.TextPrimary,
            font=theme.get_font(11, family=theme.FontMono[0]),
        )
        self._activity_box.pack(fill="both", expand=True)

        SectionHeader(self, "Szybkie akcje").pack(fill="x", padx=24, pady=(8, 8))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 24))
        ctk.CTkButton(
            actions,
            text="Odśwież dashboard",
            width=140,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self.on_show,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Dokumentacja Studio",
            width=150,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._open_studio_docs,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Klasyczny launcher",
            width=140,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._open_classic_launcher,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            actions,
            text="Folder Komponenty",
            width=140,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._open_components_folder,
        ).pack(side="left", padx=(0, 8))
        for label in ("Theme dev…", "Token setup", "Deploy / sync"):
            ctk.CTkButton(
                actions,
                text=label,
                state="disabled",
                fg_color=theme.PanelBg,
                text_color=theme.TextMuted,
                width=110,
                height=32,
            ).pack(side="left", padx=(0, 8))

        self.on_show()

    def on_show(self) -> None:
        shop = status_providers.shopify_status()
        theme_st = self._fetch_theme_dev_status()
        self._refresh_status_pills(shop, theme_st)
        self._refresh_stat_cards(shop, theme_st)
        self._refresh_chip_rows()
        self.refresh_activity()

    @staticmethod
    def _fetch_theme_dev_status() -> StatusResult:
        try:
            return status_providers.theme_dev_status()
        except Exception:  # noqa: BLE001
            return StatusResult(None, "Theme Dev", "unknown")

    def _refresh_status_pills(self, shop: StatusResult, theme_st: StatusResult) -> None:
        if not self._status_pills:
            return
        self._status_pills[0].update_status(shop.ok, shop.label, shop.detail)
        if self._theme_pill is not None:
            self._theme_pill.update_status(theme_st.ok, theme_st.label, theme_st.detail)

    def _refresh_stat_cards(self, shop: StatusResult, theme_st: StatusResult) -> None:
        if self._component_index is not None:
            total, visible = self._component_index.component_counts()
            self._stat_cards["components"].update_value(f"{visible}/{total}")
        else:
            total, visible = status_providers.component_counts()
            self._stat_cards["components"].update_value(f"{visible}/{total}")

        self._stat_cards["shopify"].update_value("OK" if shop.ok else (shop.detail[:18] or "—"))
        self._stat_cards["theme"].update_value(
            "Aktywny" if theme_st.ok else "Offline",
        )

        orders = status_providers.production_orders_count()
        self._stat_cards["orders"].update_value(str(orders) if orders is not None else "—")

    def _comp_for_folder(self, folder: str) -> Component | None:
        if self._component_index is None:
            return None
        return self._component_index.by_folder.get(folder)

    def _refresh_chip_rows(self) -> None:
        if self._pinned_row is not None:
            for w in self._pinned_row.winfo_children():
                w.destroy()
            pinned = list(self._studio_state.pinned) if self._studio_state else []
            if not pinned:
                ctk.CTkLabel(
                    self._pinned_row,
                    text="Brak przypiętych — użyj PPM w Component Hub.",
                    font=theme.get_font(11),
                    text_color=theme.TextMuted,
                    anchor="w",
                ).pack(anchor="w")
            else:
                for folder in pinned:
                    comp = self._comp_for_folder(folder)
                    if comp is None:
                        continue
                    chip = CompactComponentChip(
                        self._pinned_row, comp, on_click=self._launch_chip,
                    )
                    chip.pack(side="left", padx=(0, 6), pady=2)

        if self._recent_row is not None:
            for w in self._recent_row.winfo_children():
                w.destroy()
            recent = list(self._studio_state.recent) if self._studio_state else []
            if not recent:
                ctk.CTkLabel(
                    self._recent_row,
                    text="Uruchom komponent z huba — pojawi się tutaj.",
                    font=theme.get_font(11),
                    text_color=theme.TextMuted,
                    anchor="w",
                ).pack(anchor="w")
            else:
                for entry in recent[:8]:
                    comp = self._comp_for_folder(entry.folder_name)
                    if comp is None:
                        continue
                    chip = CompactComponentChip(
                        self._recent_row, comp, on_click=self._launch_chip,
                    )
                    chip.pack(side="left", padx=(0, 6), pady=2)

    def _launch_chip(self, comp: Component) -> None:
        root = self.winfo_toplevel()
        result = launch(comp, on_status=self._on_status)
        if result.outcome == LaunchOutcome.OK and self._studio_state is not None:
            self._studio_state.record_launch(comp)
            self._studio_state.save()
            self._refresh_chip_rows()
        elif result.outcome == LaunchOutcome.BLOCKED_INLINE:
            from giclee_app.launcher_delegate import INLINE_MESSAGE

            messagebox.showinfo(comp.name, INLINE_MESSAGE, parent=root)
        elif result.outcome in (LaunchOutcome.ERROR, LaunchOutcome.NO_PYTHON, LaunchOutcome.NO_URL):
            messagebox.showerror(comp.name, result.message, parent=root)

    def refresh_activity(self) -> None:
        if self._activity_box is None:
            return
        lines = status_providers.activity_log_lines(8)
        text = "\n".join(lines) if lines else "Brak wpisów w dzienniku."
        self._activity_box.configure(state="normal")
        self._activity_box.delete("1.0", "end")
        self._activity_box.insert("1.0", text)
        self._activity_box.configure(state="disabled")

    @staticmethod
    def _open_path(path: Path) -> None:
        if not path.exists():
            return
        try:
            if sys.platform.startswith("win"):
                import os

                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])  # noqa: S607
            else:
                subprocess.Popen(["xdg-open", str(path)])  # noqa: S607
        except OSError:
            pass

    def _open_studio_docs(self) -> None:
        self._open_path(_DOCS_PATH)

    def _open_components_folder(self) -> None:
        cwd = get_component_cwd()
        components = cwd / "Komponenty"
        self._open_path(components if components.is_dir() else cwd)

    def _open_classic_launcher(self) -> None:
        try:
            subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "giclee_app"],
                cwd=str(get_component_cwd()),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            if callable(self._on_status):
                self._on_status("Uruchomiono klasyczny launcher")
        except OSError as exc:
            messagebox.showerror("Launcher", str(exc), parent=self.winfo_toplevel())
