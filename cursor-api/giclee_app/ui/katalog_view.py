"""Katalog workflow screen (F1+F2+F3 planning) — read-only shell + local plan."""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk

from giclee_app.studio.perf import log_event, span

from giclee_app.studio.katalog_data_map import (
    F2_NEXT_NOTE,
    KatalogDataMap,
    build_katalog_data_map,
    data_map_display_rows,
    f2_status_strip,
    f3_status_strip,
)
from giclee_app.studio.katalog_draft_state import (
    CHECK_PLAN_LABEL,
    CLEAR_PLAN_LABEL,
    DRAFT_BADGE,
    DRAFT_DISCLAIMER,
    KatalogDraftState,
    PLAN_EMPTY_COPY,
    PLAN_SECTION_TITLE,
    intent_menu_options,
    variant_menu_options,
    zone_menu_options,
)
from giclee_app.studio.katalog_dry_run import (
    DRY_RUN_BADGE,
    F3_DISCLAIMER,
    SHOPIFY_SCOPE_NOTE,
    build_katalog_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.katalog_inventory import (
    DATA_MAP_WARNING,
    F1_READ_ONLY_NOTE,
    KatalogInventoryReport,
    build_katalog_inventory,
    inventory_display_rows,
    workflow_summary,
)
from giclee_app.studio.katalog_readiness import (
    F3_READINESS_DISCLAIMER,
    F5_FUTURE_NOTE,
    evaluate_katalog_plan_readiness,
    format_readiness_block,
)

from . import theme
from .widgets import SectionHeader

_REFRESH_LABEL = "Odśwież inventory / mapę danych"
_BACK_LABEL = "Wróć do huba"
_INTENT_PLACEHOLDER = "— wybierz intencję —"
_VARIANT_PLACEHOLDER = "— wybierz wariant —"
_ZONE_PLACEHOLDER = "— wybierz strefę —"
_KATALOG_INITIAL_REFRESH_DELAY_MS = 50
_KATALOG_ROW_BATCH_SIZE = 8
_KATALOG_ROW_BATCH_DELAY_MS = 0


class KatalogView(ctk.CTkScrollableFrame):
    uses_async_first_paint = True

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        components_root: Path,
        on_status: Callable[[str], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, fg_color=theme.AppBg, corner_radius=0)
        self._components_root = Path(components_root)
        self._on_status = on_status
        self._on_back = on_back
        self._back_button: ctk.CTkButton | None = None
        self._draft = KatalogDraftState()
        self._last_inventory: KatalogInventoryReport | None = None
        self._last_data_map: KatalogDataMap | None = None
        self._pending_inventory: KatalogInventoryReport | None = None
        self._pending_data_map: KatalogDataMap | None = None
        self._data_loaded = False
        self._refresh_in_progress = False
        self._refresh_scheduled = False
        self._katalog_after_ids: list[str] = []
        self._inventory_frame: ctk.CTkFrame | None = None
        self._datamap_frame: ctk.CTkFrame | None = None
        self._intent_menu: ctk.CTkOptionMenu | None = None
        self._variant_menu: ctk.CTkOptionMenu | None = None
        self._zone_menu: ctk.CTkOptionMenu | None = None
        self._intent_map: dict[str, str] = {}
        self._variant_map: dict[str, str] = {}
        self._zone_map: dict[str, str] = {}
        self._draft_summary_label: ctk.CTkLabel | None = None
        self._plan_body_label: ctk.CTkLabel | None = None
        with span("studio.katalog.build_shell"):
            self._build_shell()
        log_event("studio.katalog.shell.visible")
        self._schedule_initial_refresh()

    def set_navigation(self, *, on_back: Callable[[], None] | None = None) -> None:
        """Update cached view navigation without rebuilding the shell."""
        self._on_back = on_back
        if self._back_button is None:
            return
        if on_back is None:
            self._back_button.pack_forget()
            return
        if not self._back_button.winfo_manager():
            self._back_button.pack(side="right")

    def _safe_after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        try:
            after_id = self.after(delay_ms, lambda: self._run_if_alive(callback))
            self._katalog_after_ids.append(after_id)
        except tk.TclError:
            pass

    def _run_if_alive(self, callback: Callable[[], None]) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return
        callback()

    def _cancel_deferred_katalog_jobs(self) -> None:
        while self._katalog_after_ids:
            after_id = self._katalog_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        self._reset_refresh_pipeline_state()

    def _reset_refresh_pipeline_state(self) -> None:
        self._refresh_in_progress = False
        self._pending_inventory = None
        self._pending_data_map = None

    def on_hide(self) -> None:
        self._cancel_deferred_katalog_jobs()

    def destroy(self) -> None:
        self._cancel_deferred_katalog_jobs()
        super().destroy()

    def on_show(self, *, cache_hit: bool = False) -> None:
        log_event(
            "studio.katalog.on_show.cache_hit",
            cache_hit=cache_hit,
            data_loaded=self._data_loaded,
        )
        log_event(
            "studio.katalog.on_show",
            cache_hit=cache_hit,
            data_loaded=self._data_loaded,
        )
        if cache_hit and self._data_loaded:
            log_event("studio.katalog.refresh.skipped_cache_fresh")
            log_event("studio.katalog.visual.ready", cache_hit=True, data_loaded=True)
            return
        if not self._data_loaded and not self._refresh_scheduled:
            log_event("studio.katalog.refresh.deferred_start")
            self._schedule_initial_refresh()

    def _schedule_initial_refresh(self) -> None:
        if self._refresh_scheduled or self._data_loaded:
            return
        self._refresh_scheduled = True
        self._safe_after(_KATALOG_INITIAL_REFRESH_DELAY_MS, self._deferred_initial_refresh)

    def _deferred_initial_refresh(self) -> None:
        self._refresh_scheduled = False
        if self._data_loaded:
            return
        self._refresh_all()

    def _build_shell(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))
        SectionHeader(header, "Katalog").pack(fill="x", side="left")
        if self._on_back is not None:
            self._back_button = ctk.CTkButton(
                header,
                text=_BACK_LABEL,
                width=120,
                height=28,
                fg_color=theme.PanelBg,
                hover_color=theme.CardHover,
                command=self._on_back,
            )
            self._back_button.pack(side="right")

        ctk.CTkLabel(
            self,
            text=workflow_summary(),
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="w",
            justify="left",
            wraplength=720,
        ).pack(fill="x", padx=24, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=f2_status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 2))

        ctk.CTkLabel(
            self,
            text=f3_status_strip(),
            font=theme.get_font(11, "bold"),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=24, pady=(0, 8))

        badges = ctk.CTkFrame(self, fg_color="transparent")
        badges.pack(fill="x", padx=24, pady=(0, 8))
        for text in (
            "Parent workflow",
            "Katalog F1 inventory",
            "Katalog F2 data map",
            "local planning only",
            "Tło do Bio: absorbed",
        ):
            ctk.CTkLabel(
                badges,
                text=text,
                font=theme.get_font(10),
                text_color=theme.TextPrimary,
                fg_color=theme.PanelBg,
                corner_radius=6,
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            self,
            text=_REFRESH_LABEL,
            width=220,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            command=self._refresh_all,
        ).pack(anchor="w", padx=24, pady=(0, 12))

        SectionHeader(self, "Inventory (F1)").pack(fill="x", padx=24, pady=(0, 4))
        self._inventory_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._inventory_frame.pack(fill="x", padx=24, pady=(0, 12))

        SectionHeader(self, "Mapa danych (F2)").pack(fill="x", padx=24, pady=(8, 4))
        self._datamap_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._datamap_frame.pack(fill="x", padx=24, pady=(0, 8))

        self._build_plan_section()

        warn = ctk.CTkFrame(self, fg_color=theme.PanelBg, corner_radius=8)
        warn.pack(fill="x", padx=24, pady=(8, 16))
        for line in (DATA_MAP_WARNING, F1_READ_ONLY_NOTE, F2_NEXT_NOTE):
            ctk.CTkLabel(
                warn,
                text=f"• {line}",
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="w",
                justify="left",
                wraplength=680,
            ).pack(fill="x", padx=12, pady=(6, 0))
        ctk.CTkLabel(warn, text="", height=4).pack()

    def _build_plan_section(self) -> None:
        panel = ctk.CTkFrame(
            self,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        panel.pack(fill="x", padx=24, pady=(8, 8))

        SectionHeader(panel, PLAN_SECTION_TITLE).pack(fill="x", padx=16, pady=(12, 4))
        ctk.CTkLabel(
            panel,
            text=DRAFT_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        intent_opts = intent_menu_options()
        intent_labels = [_INTENT_PLACEHOLDER] + [label for _, label in intent_opts]
        intent_ids = [""] + [iid for iid, _ in intent_opts]
        self._intent_map = dict(zip(intent_labels, intent_ids, strict=True))

        intent_row = ctk.CTkFrame(panel, fg_color="transparent")
        intent_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            intent_row,
            text="Intencja:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._intent_menu = ctk.CTkOptionMenu(
            intent_row,
            values=intent_labels,
            command=self._on_intent_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._intent_menu.set(_INTENT_PLACEHOLDER)
        self._intent_menu.pack(side="left", fill="x", expand=True)

        variant_row = ctk.CTkFrame(panel, fg_color="transparent")
        variant_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            variant_row,
            text="Wariant:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._variant_menu = ctk.CTkOptionMenu(
            variant_row,
            values=[_VARIANT_PLACEHOLDER],
            command=self._on_variant_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._variant_menu.set(_VARIANT_PLACEHOLDER)
        self._variant_menu.pack(side="left", fill="x", expand=True)

        zone_opts = zone_menu_options()
        zone_labels = [_ZONE_PLACEHOLDER] + [label for _, label in zone_opts]
        zone_ids = [""] + [zid for zid, _ in zone_opts]
        self._zone_map = dict(zip(zone_labels, zone_ids, strict=True))

        zone_row = ctk.CTkFrame(panel, fg_color="transparent")
        zone_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            zone_row,
            text="Strefa:",
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            width=72,
            anchor="w",
        ).pack(side="left")
        self._zone_menu = ctk.CTkOptionMenu(
            zone_row,
            values=zone_labels,
            command=self._on_zone_selected,
            fg_color=theme.AppBg,
            button_color=theme.PanelBg,
            button_hover_color=theme.CardHover,
            dropdown_fg_color=theme.PanelBg,
            font=theme.get_font(12),
            width=420,
        )
        self._zone_menu.set(_ZONE_PLACEHOLDER)
        self._zone_menu.pack(side="left", fill="x", expand=True)

        self._draft_summary_label = ctk.CTkLabel(
            panel,
            text=self._draft.format_summary(),
            font=theme.get_font(12),
            text_color=theme.TextPrimary,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._draft_summary_label.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(
            panel,
            text=DRAFT_DISCLAIMER,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(
            panel,
            text=DRY_RUN_BADGE,
            font=theme.get_font(10),
            text_color=theme.AccentGoldDim,
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))

        self._plan_body_label = ctk.CTkLabel(
            panel,
            text=PLAN_EMPTY_COPY,
            font=theme.get_font(12),
            text_color=theme.TextMuted,
            anchor="nw",
            justify="left",
            wraplength=560,
        )
        self._plan_body_label.pack(fill="x", padx=16, pady=(0, 8))

        for disclaimer in (F3_DISCLAIMER, SHOPIFY_SCOPE_NOTE, F3_READINESS_DISCLAIMER, F5_FUTURE_NOTE):
            ctk.CTkLabel(
                panel,
                text=disclaimer,
                font=theme.get_font(11),
                text_color=theme.TextMuted,
                anchor="nw",
                justify="left",
                wraplength=560,
            ).pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkButton(
            panel,
            text=CHECK_PLAN_LABEL,
            height=32,
            fg_color=theme.AppBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._run_plan_dry_run,
        ).pack(anchor="w", padx=16, pady=(4, 4))

        ctk.CTkButton(
            panel,
            text=CLEAR_PLAN_LABEL,
            height=32,
            fg_color=theme.PanelBg,
            hover_color=theme.CardHover,
            border_width=1,
            border_color=theme.BorderSubtle,
            command=self._clear_plan,
        ).pack(anchor="w", padx=16, pady=(0, 12))

    def _on_intent_selected(self, label: str) -> None:
        intent_id = self._intent_map.get(label, "")
        self._draft.set_intent(intent_id or None)
        self._refresh_draft_summary()

    def _on_variant_selected(self, label: str) -> None:
        variant_id = self._variant_map.get(label, "")
        self._draft.set_variant(variant_id or None)
        self._refresh_draft_summary()

    def _on_zone_selected(self, label: str) -> None:
        zone_id = self._zone_map.get(label, "")
        self._draft.set_zone(zone_id or None)
        self._refresh_draft_summary()

    def _refresh_draft_summary(self) -> None:
        if self._draft_summary_label is None:
            return
        variant_label: str | None = None
        if self._draft.variant_id and self._last_inventory is not None:
            variant_label = self._last_inventory.katalog.variant_labels.get(
                self._draft.variant_id,
                self._draft.variant_id,
            )
        self._draft_summary_label.configure(
            text=self._draft.format_summary(variant_label=variant_label),
        )

    def _update_variant_menu(self, inventory: KatalogInventoryReport) -> None:
        if self._variant_menu is None:
            return
        katalog = inventory.katalog
        opts = variant_menu_options(katalog.variant_ids, katalog.variant_labels)
        if opts:
            labels = [_VARIANT_PLACEHOLDER] + [label for _, label in opts]
            ids = [""] + [vid for vid, _ in opts]
            self._variant_map = dict(zip(labels, ids, strict=True))
            self._variant_menu.configure(values=labels)
            if self._draft.variant_id and self._draft.variant_id in ids:
                idx = ids.index(self._draft.variant_id)
                self._variant_menu.set(labels[idx])
            else:
                self._variant_menu.set(_VARIANT_PLACEHOLDER)
        else:
            self._variant_map = {_VARIANT_PLACEHOLDER: ""}
            self._variant_menu.configure(values=[_VARIANT_PLACEHOLDER])
            self._variant_menu.set(_VARIANT_PLACEHOLDER)

    def _clear_plan(self) -> None:
        self._draft.clear()
        if self._intent_menu is not None:
            self._intent_menu.set(_INTENT_PLACEHOLDER)
        if self._variant_menu is not None:
            self._variant_menu.set(_VARIANT_PLACEHOLDER)
        if self._zone_menu is not None:
            self._zone_menu.set(_ZONE_PLACEHOLDER)
        if self._plan_body_label is not None:
            self._plan_body_label.configure(text=PLAN_EMPTY_COPY, text_color=theme.TextMuted)
        self._refresh_draft_summary()
        if self._on_status is not None:
            self._on_status("Plan wyczyszczony · draft lokalny · nic nie zapisano")

    def _run_plan_dry_run(self) -> None:
        if self._refresh_in_progress:
            log_event("studio.katalog.plan_dry_run.deferred_refresh_in_progress")
            if self._plan_body_label is not None:
                self._plan_body_label.configure(
                    text="Dane Katalogu są jeszcze odświeżane. Uruchom ponownie po zakończeniu.",
                    text_color=theme.TextMuted,
                )
            if self._on_status is not None:
                self._on_status("Katalog: dane jeszcze się odświeżają — spróbuj za chwilę")
            return
        if self._last_inventory is None or self._last_data_map is None:
            log_event("studio.katalog.plan_dry_run.waiting_for_data")
            self._refresh_all()
            if self._plan_body_label is not None:
                self._plan_body_label.configure(
                    text="Dane Katalogu są jeszcze odświeżane. Uruchom ponownie po zakończeniu.",
                    text_color=theme.TextMuted,
                )
            if self._on_status is not None:
                self._on_status("Katalog: dane jeszcze się odświeżają — spróbuj za chwilę")
            return
        inventory = self._last_inventory
        data_map = self._last_data_map

        dry_run = build_katalog_plan_dry_run(self._draft, inventory, data_map)
        readiness = evaluate_katalog_plan_readiness(self._draft, dry_run)
        full_text = format_dry_run_summary(dry_run) + "\n\n" + format_readiness_block(readiness)

        if self._plan_body_label is not None:
            self._plan_body_label.configure(
                text=full_text,
                text_color=theme.TextPrimary if dry_run.ok else theme.TextMuted,
            )
        if self._on_status is not None:
            self._on_status(DRY_RUN_BADGE)

    @staticmethod
    def _append_display_row(parent: ctk.CTkFrame, label: str, value: str) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(
            row,
            text=label,
            font=theme.get_font(11),
            text_color=theme.TextMuted,
            anchor="w",
            width=220,
        ).pack(side="left", anchor="nw")
        ctk.CTkLabel(
            row,
            text=value,
            font=theme.get_font(11),
            text_color=theme.TextPrimary,
            anchor="w",
            justify="left",
            wraplength=480,
        ).pack(side="left", fill="x", expand=True)

    @staticmethod
    def _fill_rows(parent: ctk.CTkFrame, rows: list[tuple[str, str]]) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for label, value in rows:
            KatalogView._append_display_row(parent, label, value)

    def _start_fill_rows_stage(
        self,
        kind: str,
        parent: ctk.CTkFrame,
        rows: list[tuple[str, str]],
        next_callback: Callable[[], None],
    ) -> None:
        self._fill_rows_batch(kind, parent, rows, 0, next_callback)

    def _fill_rows_batch(
        self,
        kind: str,
        parent: ctk.CTkFrame,
        rows: list[tuple[str, str]],
        start: int,
        next_callback: Callable[[], None],
    ) -> None:
        if self._refresh_abort_if_gone():
            return
        event_prefix = f"studio.katalog.refresh.{kind}_rows"
        total = len(rows)
        try:
            t0 = time.perf_counter()
            if start == 0:
                for child in parent.winfo_children():
                    child.destroy()
            end = min(start + _KATALOG_ROW_BATCH_SIZE, total)
            created = 0
            for label, value in rows[start:end]:
                self._append_display_row(parent, label, value)
                created += 1
            elapsed_ms = (time.perf_counter() - t0) * 1000
            log_event(
                f"{event_prefix}.batch",
                start=start,
                end=end,
                total=total,
                created=created,
                elapsed_ms=elapsed_ms,
            )
            if end < total:
                self._safe_after(
                    _KATALOG_ROW_BATCH_DELAY_MS,
                    lambda: self._fill_rows_batch(kind, parent, rows, end, next_callback),
                )
                return
            log_event(f"{event_prefix}.done", total=total)
            next_callback()
        except Exception as exc:  # noqa: BLE001
            self._refresh_pipeline_error(exc)

    def _refresh_abort_if_gone(self) -> bool:
        try:
            if not self.winfo_exists():
                self._reset_refresh_pipeline_state()
                return True
        except tk.TclError:
            self._reset_refresh_pipeline_state()
            return True
        return False

    def _refresh_pipeline_error(self, exc: BaseException) -> None:
        self._reset_refresh_pipeline_state()
        log_event("studio.katalog.refresh_pipeline.error", error_type=type(exc).__name__)
        if self._on_status is not None:
            self._on_status("Katalog: odświeżanie przerwane — sprawdź log")

    def _refresh_all(self) -> None:
        if self._refresh_in_progress:
            log_event("studio.katalog.refresh.skipped_in_progress")
            if self._on_status is not None:
                self._on_status("Katalog: odświeżanie już trwa")
            return
        self._refresh_in_progress = True
        self._pending_inventory = None
        self._pending_data_map = None
        if self._on_status is not None:
            self._on_status("Katalog: odświeżam inventory…")
        log_event("studio.katalog.refresh_pipeline.start")
        self._safe_after(0, self._refresh_inventory_stage)

    def _refresh_inventory_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        try:
            with span("studio.katalog.refresh.inventory"):
                self._pending_inventory = build_katalog_inventory(self._components_root)
            if self._on_status is not None:
                self._on_status("Katalog: odświeżam mapę danych…")
            self._safe_after(0, self._refresh_data_map_stage)
        except Exception as exc:  # noqa: BLE001 — soft-fail UI refresh pipeline
            self._refresh_pipeline_error(exc)

    def _refresh_data_map_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        try:
            with span("studio.katalog.refresh.data_map"):
                self._pending_data_map = build_katalog_data_map(self._components_root)
            if self._on_status is not None:
                self._on_status("Katalog: wypełniam inventory…")
            self._safe_after(0, self._refresh_inventory_rows_stage)
        except Exception as exc:  # noqa: BLE001
            self._refresh_pipeline_error(exc)

    def _refresh_inventory_rows_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        inv = self._pending_inventory
        if inv is not None and self._inventory_frame is not None:
            self._start_fill_rows_stage(
                "inventory",
                self._inventory_frame,
                inventory_display_rows(inv),
                self._after_inventory_rows_stage,
            )
            return
        self._after_inventory_rows_stage()

    def _after_inventory_rows_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        if self._on_status is not None:
            self._on_status("Katalog: wypełniam mapę danych…")
        self._safe_after(0, self._refresh_data_map_rows_stage)

    def _refresh_data_map_rows_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        dm = self._pending_data_map
        if dm is not None and self._datamap_frame is not None:
            self._start_fill_rows_stage(
                "data_map",
                self._datamap_frame,
                data_map_display_rows(dm),
                self._after_data_map_rows_stage,
            )
            return
        self._after_data_map_rows_stage()

    def _after_data_map_rows_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        self._safe_after(0, self._refresh_finalize_stage)

    def _refresh_finalize_stage(self) -> None:
        if self._refresh_abort_if_gone():
            return
        try:
            with span("studio.katalog.refresh.finalize"):
                inv = self._pending_inventory
                dm = self._pending_data_map
                self._last_inventory = inv
                self._last_data_map = dm
                self._pending_inventory = None
                self._pending_data_map = None
                if inv is not None:
                    self._update_variant_menu(inv)
                self._refresh_draft_summary()
            self._data_loaded = True
            self._refresh_in_progress = False
            log_event("studio.katalog.visual.ready", cache_hit=False, data_loaded=True)
            log_event("studio.katalog.refresh_pipeline.done")
            log_event("studio.katalog.refresh.deferred_done")
            if self._on_status is not None:
                self._on_status("Katalog inventory + mapa danych odświeżone (read-only)")
        except Exception as exc:  # noqa: BLE001
            self._refresh_pipeline_error(exc)
