"""Widok Dashboard — read-only F2 (statusy, recent, pinned, safe quick actions)."""

from __future__ import annotations

import subprocess
import sys
import time
import tkinter as tk
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
from giclee_app.studio.perf import log_event, span
from giclee_app.studio.state import StudioState
from giclee_app.studio.status_providers import StatusResult

from . import theme
from .widgets import CompactComponentChip, SectionHeader, StatCard, StatusPill

_DOCS_PATH = Path(__file__).resolve().parents[1] / "docs" / "studio-preview.md"
_DASHBOARD_INITIAL_REFRESH_DELAY_MS = 50
_THEME_STATUS_DELAY_MS = 400
_GIT_STATUS_DELAY_MS = 480


class DashboardView(ctk.CTkScrollableFrame):
    uses_async_first_paint = True

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        component_index: StudioComponentIndex | None = None,
        studio_state: StudioState | None = None,
        on_status: Callable[[str], None] | None = None,
        on_open_inline: Callable[[Component, str], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._component_index = component_index
        self._studio_state = studio_state
        self._on_status = on_status
        self._on_open_inline = on_open_inline
        self._activity_box: ctk.CTkTextbox | None = None
        self._status_pills: list[StatusPill] = []
        self._stat_cards: dict[str, StatCard] = {}
        self._pinned_row: ctk.CTkFrame | None = None
        self._recent_row: ctk.CTkFrame | None = None
        self._theme_pill: StatusPill | None = None
        self._git_pill: StatusPill | None = None
        self._gpt_pill: StatusPill | None = None
        self._build_after_ids: list[str] = []
        self._refresh_after_ids: list[str] = []
        self._last_shop_status: StatusResult | None = None
        self._last_theme_status: StatusResult | None = None
        self._last_git_status: StatusResult | None = None
        self._last_gpt_status: StatusResult | None = None
        self._deferred_sections_built = False
        self._visual_enter_mono = time.perf_counter()
        self._visual_skeleton_logged = False
        self._visual_visible_logged = False
        self._visual_full_logged = False
        self._visible_lane_ready = False
        self._pending_on_show = False
        self._safe_after_build(0, self._build_critical_shell)

    def _since_visual_enter_ms(self) -> float:
        return round((time.perf_counter() - self._visual_enter_mono) * 1000, 2)

    def _mark_visual_skeleton_ready(self) -> None:
        if self._visual_skeleton_logged:
            return
        self._visual_skeleton_logged = True
        log_event(
            "studio.dashboard.visual.skeleton_ready",
            since_enter_ms=self._since_visual_enter_ms(),
        )

    def _mark_visual_visible_ready(self) -> None:
        if self._visual_visible_logged:
            return
        self._visual_visible_logged = True
        log_event(
            "studio.dashboard.visual.visible_ready",
            since_enter_ms=self._since_visual_enter_ms(),
        )

    def _mark_visual_full_ready(self) -> None:
        if self._visual_full_logged:
            return
        self._visual_full_logged = True
        log_event(
            "studio.dashboard.visual.full_ready",
            since_enter_ms=self._since_visual_enter_ms(),
        )

    def _build_critical_shell(self) -> None:
        with span("studio.dashboard.build.critical"):
            self._build_critical_header()
        self._mark_visual_skeleton_ready()
        self._safe_after_build(0, self._build_visible_lane)

    def _build_visible_lane(self) -> None:
        with span("studio.dashboard.build.visible"):
            self._build_status_row()
            self._build_stats_row()
        self._visible_lane_ready = True
        self._mark_visual_visible_ready()
        self._safe_after_build(30, self._build_deferred_chip_sections)
        self._safe_after_build(60, self._build_deferred_activity_section)
        self._safe_after_build(90, self._build_deferred_actions_section)
        if self._pending_on_show:
            self._pending_on_show = False
            self._run_on_show_body()
        else:
            self._schedule_initial_refresh()

    def _build_critical_header(self) -> None:
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

    def _build_status_row(self) -> None:
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
        self._git_pill = StatusPill(status_row, "Git", ok=None, detail="")
        self._git_pill.pack(side="left", padx=(0, 8))
        self._status_pills.append(self._git_pill)
        self._gpt_pill = StatusPill(status_row, "GPT", ok=None, detail="")
        self._gpt_pill.pack(side="left", padx=(0, 8))
        self._status_pills.append(self._gpt_pill)

    def _build_stats_row(self) -> None:
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

    def _build_deferred_chip_sections(self) -> None:
        with span("studio.dashboard.build.deferred_chips"):
            SectionHeader(self, "Przypięte").pack(fill="x", padx=24, pady=(0, 6))
            self._pinned_row = ctk.CTkFrame(self, fg_color="transparent")
            self._pinned_row.pack(fill="x", padx=24, pady=(0, 12))

            SectionHeader(self, "Ostatnio używane").pack(fill="x", padx=24, pady=(0, 6))
            self._recent_row = ctk.CTkFrame(self, fg_color="transparent")
            self._recent_row.pack(fill="x", padx=24, pady=(0, 16))
            self._deferred_sections_built = True
            self._refresh_chip_rows()

    def _build_deferred_activity_section(self) -> None:
        with span("studio.dashboard.build.deferred_activity"):
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
            self.refresh_activity()

    def _build_deferred_actions_section(self) -> None:
        with span("studio.dashboard.build.deferred_actions"):
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

        self._mark_visual_full_ready()

    def _schedule_initial_refresh(self) -> None:
        self._safe_after_refresh(_DASHBOARD_INITIAL_REFRESH_DELAY_MS, self._run_on_show_body)

    def _safe_after_build(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self._schedule_after(delay_ms, callback, self._build_after_ids)

    def _safe_after_refresh(self, delay_ms: int, callback: Callable[[], None]) -> None:
        self._schedule_after(delay_ms, callback, self._refresh_after_ids)

    def _schedule_after(
        self,
        delay_ms: int,
        callback: Callable[[], None],
        bucket: list[str],
    ) -> None:
        try:
            after_id = self.after(delay_ms, lambda: self._run_if_alive(callback))
            bucket.append(after_id)
        except tk.TclError:
            pass

    def _run_if_alive(self, callback: Callable[[], None]) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        callback()

    def _cancel_after_bucket(self, bucket: list[str]) -> None:
        while bucket:
            after_id = bucket.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass

    def _cancel_deferred_refresh_jobs(self) -> None:
        self._cancel_after_bucket(self._refresh_after_ids)

    def _cancel_deferred_build_jobs(self) -> None:
        self._cancel_after_bucket(self._build_after_ids)

    def on_hide(self) -> None:
        self._cancel_deferred_refresh_jobs()

    def destroy(self) -> None:
        self._cancel_deferred_refresh_jobs()
        self._cancel_deferred_build_jobs()
        super().destroy()

    def on_show(self) -> None:
        if not self._visible_lane_ready:
            self._pending_on_show = True
            return
        self._cancel_deferred_refresh_jobs()
        self._run_on_show_body()

    def _run_on_show_body(self) -> None:
        with span("studio.dashboard.on_show.fast"):
            shop = status_providers.shopify_status()
            gpt_st = status_providers.gpt_snapshot_status()

            theme_pending = StatusResult(None, "Theme Dev", "sprawdzanie…")
            git_pending = StatusResult(None, "Git", "sprawdzanie…")

            self._last_shop_status = shop
            self._last_theme_status = theme_pending
            self._last_git_status = git_pending
            self._last_gpt_status = gpt_st

            self._refresh_status_pills(shop, theme_pending, git_pending, gpt_st)
            self._refresh_stat_cards(shop, theme_pending)
            self._refresh_chip_rows()
            self.refresh_activity()

        self._schedule_theme_status_check()
        self._safe_after_refresh(_GIT_STATUS_DELAY_MS, self._refresh_git_status_deferred)

    def _schedule_theme_status_check(self) -> None:
        log_event(
            "studio.dashboard.status.theme_dev.scheduled",
            delay_ms=_THEME_STATUS_DELAY_MS,
        )
        self._safe_after_refresh(_THEME_STATUS_DELAY_MS, self._refresh_theme_status_deferred)

    def _refresh_theme_status_deferred(self) -> None:
        with span("studio.dashboard.status.theme_dev.deferred"):
            theme_st = self._fetch_theme_dev_status()
        self._last_theme_status = theme_st

        if self._theme_pill is not None:
            self._theme_pill.update_status(theme_st.ok, theme_st.label, theme_st.detail)

        if "theme" in self._stat_cards:
            self._stat_cards["theme"].update_value(
                "Aktywny" if theme_st.ok else "Offline",
            )
        log_event("studio.dashboard.status.theme_dev.done")

    def _refresh_git_status_deferred(self) -> None:
        with span("studio.dashboard.status.git.deferred"):
            git_st = status_providers.github_status()
        self._last_git_status = git_st

        if self._git_pill is not None:
            self._git_pill.update_status(git_st.ok, git_st.label, git_st.detail)

    @staticmethod
    def _fetch_theme_dev_status() -> StatusResult:
        try:
            return status_providers.theme_dev_status()
        except Exception:  # noqa: BLE001
            return StatusResult(None, "Theme Dev", "unknown")

    def _refresh_status_pills(
        self,
        shop: StatusResult,
        theme_st: StatusResult,
        git_st: StatusResult,
        gpt_st: StatusResult,
    ) -> None:
        if not self._status_pills:
            return
        self._status_pills[0].update_status(shop.ok, shop.label, shop.detail)
        if self._theme_pill is not None:
            self._theme_pill.update_status(theme_st.ok, theme_st.label, theme_st.detail)
        if self._git_pill is not None:
            self._git_pill.update_status(git_st.ok, git_st.label, git_st.detail)
        if self._gpt_pill is not None:
            self._gpt_pill.update_status(gpt_st.ok, gpt_st.label, gpt_st.detail)

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
        if comp.mode == "inline" and self._on_open_inline is not None:
            cat = "dashboard"
            if self._component_index is not None:
                from giclee_app.studio.categories import category_for_folder

                cat = category_for_folder(comp.folder_name)
            self._on_open_inline(comp, cat)
            return
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
