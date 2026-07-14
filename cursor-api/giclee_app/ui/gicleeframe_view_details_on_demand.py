"""GICLÉE FRAME™ — details-on-demand orchestrator and cache."""

from __future__ import annotations

import time
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    EditorFieldVisibility,
    MergedPageElement,
    editor_field_visibility,
    editor_title_for_element,
)
from giclee_app.studio.perf import log_event, span
from . import theme
from .gicleeframe_view_models import SectionVisualCacheEntry
from .gicleeframe_view_primitives import (
    _BTN_HEIGHT,
    _CARD_PAD_X,
    _CARD_PAD_Y,
    _GF_BORDER,
    _GF_CARD_SOFT,
    _GF_FIELD,
    _GF_FIELD_HOVER,
    _GF_MUTED,
    _make_card,
    _make_card_title,
    _make_gf_card,
    _make_secondary_button,
)

_GF_DETAILS_ON_DEMAND_TEXT = "Szczegóły sekcji są dostępne na żądanie."
_GF_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły"
_GF_MEDIA_DETAILS_ON_DEMAND_TEXT = (
    "Szczegóły mediów, warstwy i podgląd są dostępne na żądanie."
)
_GF_MEDIA_DETAILS_ON_DEMAND_BUTTON = "Pokaż szczegóły mediów"
_GF_DETAILS_ON_DEMAND_LOADING_TEXT = "Ładowanie szczegółów…"
_GF_DETAILS_SHELL_TITLE = "Szczegóły sekcji"
_GF_DETAILS_SHELL_SUBTEXT = "Wybierz, które szczegóły chcesz wczytać."
_GF_MEDIA_DETAILS_SHELL_SUBTEXT = (
    "Podgląd, warstwy i elementy mediów są dostępne osobno, żeby nie spowalniać edytora."
)
_GF_DETAILS_CACHE_HIT_STATUS = "Szczegóły załadowane"
_GF_DETAILS_MODULE_PREVIEW_TITLE = "Podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE = "Ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_TITLE = "Warstwy"
_GF_DETAILS_MODULE_CHILDREN_TITLE = "Elementy"
_GF_DETAILS_MODULE_PREVIEW_BUTTON = "Wczytaj podgląd"
_GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON = "Wczytaj ustawienia"
_GF_DETAILS_MODULE_LAYER_NAV_BUTTON = "Wczytaj warstwy"
_GF_DETAILS_MODULE_CHILDREN_BUTTON = "Wczytaj elementy"
_GF_DETAILS_MODULE_IDLE_STATUS = "—"
_GF_DETAILS_MODULE_LOADED_STATUS = "Gotowe"
_GF_DETAILS_MODULE_LOADING_STATUS = "Ładowanie…"
_GF_DETAILS_STAGE_GAP_MS = 16
_GF_DETAILS_CHILDREN_BATCH_SIZE = 2
_GF_DETAILS_CONTAINER_HEIGHT = 148
_GF_MEDIA_PREVIEW_AFTER_SHELL_MS = 20
_GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS = 40
_GF_MEDIA_CHILDREN_AFTER_SHELL_MS = 80
_GF_MEDIA_DETAILS_STATUS_TEXT = "Szczegóły mediów zostaną zaktualizowane…"
_GF_MEDIA_DETAILS_STABLE_HEIGHT = 88
_GF_SELECTION_LAYER_NAV_DEFER_MS = 16
_GF_SELECTION_CHILDREN_DEFER_MS = 32
_GF_SELECTION_CHILDREN_LATE_DEFER_MS = 80
_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS = 16

__all__ = (
    "GicleeFrameDetailsOnDemandMixin",
    "_GF_DETAILS_ON_DEMAND_TEXT",
    "_GF_DETAILS_ON_DEMAND_BUTTON",
    "_GF_MEDIA_DETAILS_ON_DEMAND_TEXT",
    "_GF_MEDIA_DETAILS_ON_DEMAND_BUTTON",
    "_GF_DETAILS_ON_DEMAND_LOADING_TEXT",
    "_GF_DETAILS_SHELL_TITLE",
    "_GF_DETAILS_SHELL_SUBTEXT",
    "_GF_MEDIA_DETAILS_SHELL_SUBTEXT",
    "_GF_DETAILS_CACHE_HIT_STATUS",
    "_GF_DETAILS_MODULE_PREVIEW_TITLE",
    "_GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE",
    "_GF_DETAILS_MODULE_LAYER_NAV_TITLE",
    "_GF_DETAILS_MODULE_CHILDREN_TITLE",
    "_GF_DETAILS_MODULE_PREVIEW_BUTTON",
    "_GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON",
    "_GF_DETAILS_MODULE_LAYER_NAV_BUTTON",
    "_GF_DETAILS_MODULE_CHILDREN_BUTTON",
    "_GF_DETAILS_MODULE_IDLE_STATUS",
    "_GF_DETAILS_MODULE_LOADED_STATUS",
    "_GF_DETAILS_MODULE_LOADING_STATUS",
    "_GF_DETAILS_STAGE_GAP_MS",
    "_GF_DETAILS_CHILDREN_BATCH_SIZE",
    "_GF_DETAILS_CONTAINER_HEIGHT",
    "_GF_MEDIA_PREVIEW_AFTER_SHELL_MS",
    "_GF_MEDIA_LAYER_NAV_AFTER_SHELL_MS",
    "_GF_MEDIA_CHILDREN_AFTER_SHELL_MS",
    "_GF_MEDIA_DETAILS_STATUS_TEXT",
    "_GF_MEDIA_DETAILS_STABLE_HEIGHT",
    "_GF_SELECTION_LAYER_NAV_DEFER_MS",
    "_GF_SELECTION_CHILDREN_DEFER_MS",
    "_GF_SELECTION_CHILDREN_LATE_DEFER_MS",
    "_GF_PREVIEW_DEFER_FOR_HEAVY_TYPES_MS",
)


class GicleeFrameDetailsOnDemandMixin:
    """Details-on-demand orchestrator, cache and deferred population wrappers."""

    def _since_details_request_ms(self) -> float | None:
        if self._details_on_demand_request_mono is None:
            return None
        return round((time.perf_counter() - self._details_on_demand_request_mono) * 1000, 2)

    def _since_details_cta_ms(self) -> float | None:
        if self._details_cta_click_mono is None:
            return None
        return round((time.perf_counter() - self._details_cta_click_mono) * 1000, 2)

    def _log_perf_e_update_done(
        self,
        segment: str,
        *,
        element_type: str,
        started: float,
    ) -> None:
        log_event(
            f"studio.gicleeframe.{segment}.update.done",
            element_type=element_type,
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )

    def _ensure_media_details_stable_shell(self) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._identity_card is None:
            return
        if not self._media_details_stable_built:
            frame = ctk.CTkFrame(
                self._identity_card,
                fg_color=_GF_FIELD,
                corner_radius=10,
                border_width=1,
                border_color=_GF_BORDER,
                height=_GF_MEDIA_DETAILS_STABLE_HEIGHT,
            )
            frame.pack_propagate(False)
            self._media_details_status_label = ctk.CTkLabel(
                frame,
                text=_GF_MEDIA_DETAILS_STATUS_TEXT,
                font=theme.get_font(10),
                text_color=theme.TextMuted,
                anchor="w",
            )
            self._media_details_status_label.pack(fill="x", padx=12, pady=10)
            self._media_details_stable_frame = frame
            self._media_details_stable_built = True
        if self._media_details_stable_frame is None:
            return
        if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            self._media_details_stable_frame.pack(
                fill="x",
                padx=_CARD_PAD_X,
                pady=(0, 4),
                before=self._layer_nav_frame,
            )
        else:
            self._media_details_stable_frame.pack(
                fill="x",
                padx=_CARD_PAD_X,
                pady=(0, 4),
            )

    def _hide_media_details_stable_shell(self) -> None:
        if self._media_details_stable_frame is None:
            return
        try:
            self._media_details_stable_frame.pack_forget()
        except tk.TclError:
            pass

    def _details_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        entry = self._section_visual_cache.get(m.element_id)
        if entry is None:
            return None
        if self._any_details_module_cached(entry):
            return entry
        if entry.media_details_built:
            return entry
        return None

    def _any_details_module_cached(self, entry: SectionVisualCacheEntry) -> bool:
        return any(
            (
                entry.details_cache_preview,
                entry.details_cache_page_context,
                entry.details_cache_layer_nav,
                entry.details_cache_children,
            )
        )

    def _details_module_cache_hit(self, entry: SectionVisualCacheEntry, module: str) -> bool:
        return {
            "preview": entry.details_cache_preview,
            "page_context": entry.details_cache_page_context,
            "layer_nav": entry.details_cache_layer_nav,
            "children": entry.details_cache_children,
        }.get(module, False)

    def _cached_details_modules(self, entry: SectionVisualCacheEntry) -> list[str]:
        modules: list[str] = []
        if entry.details_cache_preview:
            modules.append("preview")
        if entry.details_cache_page_context:
            modules.append("page_context")
        if entry.details_cache_layer_nav:
            modules.append("layer_nav")
        if entry.details_cache_children:
            modules.append("children")
        return modules

    def _full_visual_cache_entry(
        self,
        m: MergedPageElement,
    ) -> SectionVisualCacheEntry | None:
        """Legacy alias — details cache only."""
        return self._details_cache_entry(m)

    def _apply_cached_page_context_summary(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.fields_page_context or not entry.page_context_summary:
            if self._page_context_frame is not None:
                self._page_context_frame.pack_forget()
            return
        self._ensure_page_context_shell_built()
        if self._page_context_frame is None or self._page_context_inner is None:
            return
        self._hide_page_context_rows()
        self._clear_page_context_loading_label()
        self._page_context_frame.pack(**self._page_context_pack_kwargs())
        self._get_or_create_readonly_card()
        self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        for label, value in entry.page_context_summary:
            row_key = f"shell_summary:{label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=label,
                kind="shell_summary",
            )
            value_widget.configure(text=value)
            self._show_page_context_row(row_key, fill="x", pady=2)

    def _apply_cached_preview_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_preview or not entry.preview_key:
            return
        preview_key = entry.preview_key
        self._ensure_preview_structure(preview_key)
        self._show_preview_frame(preview_key)
        self._show_heavy_editor_modules()

    def _apply_cached_page_context_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_page_context:
            return
        self._apply_cached_page_context_summary(entry)

    def _apply_cached_layer_nav_module(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.details_cache_layer_nav:
            return
        if entry.layer_nav_visible and self._layer_nav_frame is not None:
            if not self._layer_nav_frame.winfo_manager():
                self._layer_nav_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(8, 0))
            header = self._get_or_create_layer_nav_header()
            if "header:title" not in self._layer_nav_visible_keys:
                header.pack(fill="x", pady=(0, 6))
                self._layer_nav_visible_keys.add("header:title")
            row = self._get_or_create_layer_nav_row()
            if "container:row" not in self._layer_nav_visible_keys:
                row.pack(fill="x")
                self._layer_nav_visible_keys.add("container:row")
            desired_keys: list[str] = []
            for index, title in enumerate(entry.layer_nav_titles):
                slot_key = f"slot:{index}"
                desired_keys.append(slot_key)
                self._update_layer_nav_tile(
                    slot_key,
                    kind="SEKCJA" if index == 0 else "WARSTWA",
                    title=title,
                    active=index == 0,
                )
            self._sync_layer_nav_visibility(desired_keys)

    def _apply_cached_children_module(
        self,
        m: MergedPageElement,
        entry: SectionVisualCacheEntry,
    ) -> None:
        if not entry.details_cache_children:
            return
        self._set_row_visible(self._children_overview_row, entry.fields_children)
        if entry.fields_children:
            self._fill_children_overview_buttons(m, stale_refresh=False)

    def _apply_cached_media_details(self, entry: SectionVisualCacheEntry) -> None:
        if not entry.media_details_built and not self._any_details_module_cached(entry):
            return
        self._apply_cached_preview_module(entry)
        self._apply_cached_layer_nav_module(entry)
        self._hide_media_details_stable_shell()

    def _ensure_details_on_demand_block_built(self) -> None:
        parent = self._identity_card or self._edit_panel
        if self._details_on_demand_built or parent is None:
            return
        frame = ctk.CTkFrame(
            parent,
            fg_color=_GF_FIELD,
            corner_radius=10,
            border_width=1,
            border_color=_GF_BORDER,
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        self._details_on_demand_hint_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_ON_DEMAND_TEXT,
            font=theme.get_font(10),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._details_on_demand_hint_label.pack(fill="x", pady=(0, 8))
        self._details_on_demand_button = ctk.CTkButton(
            inner,
            text=_GF_DETAILS_ON_DEMAND_BUTTON,
            height=_BTN_HEIGHT,
            width=120,
            fg_color=_GF_CARD_SOFT,
            hover_color=_GF_FIELD_HOVER,
            text_color=theme.TextPrimary,
            command=self._on_details_on_demand_clicked,
        )
        self._details_on_demand_button.pack(anchor="w", fill="x")
        self._details_on_demand_status_label = ctk.CTkLabel(
            inner,
            text="",
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
        )
        self._details_on_demand_frame = frame
        self._details_on_demand_built = True

    def _hide_details_on_demand_block(self) -> None:
        if self._details_on_demand_frame is None:
            return
        try:
            self._details_on_demand_frame.pack_forget()
        except tk.TclError:
            pass
        if self._details_on_demand_status_label is not None:
            self._details_on_demand_status_label.configure(text="")

    def _show_details_on_demand_block(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._details_on_demand_expanded:
            self._hide_details_on_demand_block()
            return
        self._ensure_details_on_demand_block_built()
        if self._details_on_demand_frame is None:
            return
        is_media = m.element_type == "media_section"
        hint = _GF_MEDIA_DETAILS_ON_DEMAND_TEXT if is_media else _GF_DETAILS_ON_DEMAND_TEXT
        button_text = (
            _GF_MEDIA_DETAILS_ON_DEMAND_BUTTON if is_media else _GF_DETAILS_ON_DEMAND_BUTTON
        )
        if self._details_on_demand_hint_label is not None:
            self._details_on_demand_hint_label.configure(text=hint)
        if self._details_on_demand_button is not None:
            self._details_on_demand_button.configure(text=button_text)
        self._details_on_demand_element_id = m.element_id
        cache_entry = self._details_cache_entry(m)
        cached_modules = self._cached_details_modules(cache_entry) if cache_entry else []
        if self._details_on_demand_status_label is not None:
            if cached_modules:
                self._details_on_demand_status_label.configure(
                    text=f"Załadowano: {len(cached_modules)} moduł(y)",
                )
                self._details_on_demand_status_label.pack(fill="x", pady=(8, 0))
            else:
                self._details_on_demand_status_label.configure(text="")
                try:
                    self._details_on_demand_status_label.pack_forget()
                except tk.TclError:
                    pass
        pack_before = None
        if self._section_preview_card is not None:
            pack_before = self._section_preview_card
        elif self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            pack_before = self._layer_nav_frame
        try:
            if pack_before is not None:
                self._details_on_demand_frame.pack(
                    fill="x",
                    padx=_CARD_PAD_X,
                    pady=(0, 8),
                    before=pack_before,
                )
            else:
                self._details_on_demand_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
        except tk.TclError:
            try:
                self._details_on_demand_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
            except tk.TclError:
                pass
        log_event(
            "studio.gicleeframe.details_on_demand.available",
            element_id=m.element_id,
            element_type=m.element_type,
            since_click_ms=self._since_selection_click_ms(),
            details_cached=bool(cached_modules),
        )

    def _on_details_on_demand_clicked(self) -> None:
        element_id = self._details_on_demand_element_id or self._selected_id
        if not element_id:
            return
        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            return

        self._cancel_details_on_demand_jobs()
        self._details_on_demand_generation += 1
        details_generation = self._details_on_demand_generation
        request_started = time.perf_counter()
        self._details_on_demand_request_mono = request_started
        self._details_cta_click_mono = request_started
        self._details_on_demand_active_element_id = element_id

        log_event(
            "studio.gicleeframe.details_on_demand.requested",
            element_id=element_id,
            element_type=m.element_type,
            since_details_cta_ms=0.0,
            since_request_ms=0.0,
            generation=details_generation,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.full_auto_suppressed",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            since_request_ms=self._since_details_request_ms(),
        )
        log_event(
            "studio.gicleeframe.details_shell.requested",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            since_request_ms=self._since_details_request_ms(),
        )

        self._hide_details_on_demand_block()
        self._show_details_shell(m)
        self._details_on_demand_expanded = True
        self._hide_editor_refresh_status()

        elapsed_ms = self._since_details_request_ms()
        log_event(
            "studio.gicleeframe.details_shell.ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_shell.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=details_generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=elapsed_ms,
            since_request_ms=elapsed_ms,
            shell_only=True,
        )

    def _ensure_details_shell_built(self) -> None:
        parent = self._identity_card or self._edit_panel
        if self._details_container_built or parent is None:
            return
        frame = ctk.CTkFrame(
            parent,
            fg_color=_GF_FIELD,
            corner_radius=10,
            border_width=1,
            border_color=_GF_BORDER,
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        self._details_container_title_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_SHELL_TITLE,
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        self._details_container_title_label.pack(fill="x", pady=(0, 4))
        self._details_container_subtext_label = ctk.CTkLabel(
            inner,
            text=_GF_DETAILS_SHELL_SUBTEXT,
            font=theme.get_font(9),
            text_color=theme.TextMuted,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self._details_container_subtext_label.pack(fill="x", pady=(0, 10))
        modules_parent = ctk.CTkFrame(inner, fg_color="transparent")
        modules_parent.pack(fill="x")
        module_specs = (
            ("preview", _GF_DETAILS_MODULE_PREVIEW_TITLE, _GF_DETAILS_MODULE_PREVIEW_BUTTON),
            (
                "page_context",
                _GF_DETAILS_MODULE_PAGE_CONTEXT_TITLE,
                _GF_DETAILS_MODULE_PAGE_CONTEXT_BUTTON,
            ),
            ("layer_nav", _GF_DETAILS_MODULE_LAYER_NAV_TITLE, _GF_DETAILS_MODULE_LAYER_NAV_BUTTON),
            ("children", _GF_DETAILS_MODULE_CHILDREN_TITLE, _GF_DETAILS_MODULE_CHILDREN_BUTTON),
        )
        for module_key, title, button_text in module_specs:
            # Dwie linie: tytuł + status na górze, przycisk na całą szerokość pod spodem —
            # przy wąskiej kolumnie nic nie jest wyciskane ani obcinane.
            row = ctk.CTkFrame(modules_parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 8))
            head = ctk.CTkFrame(row, fg_color="transparent")
            head.pack(fill="x")
            ctk.CTkLabel(
                head,
                text=title,
                font=theme.get_font(9, "bold"),
                text_color=theme.TextPrimary,
                anchor="w",
            ).pack(side="left")
            status = ctk.CTkLabel(
                head,
                text=_GF_DETAILS_MODULE_IDLE_STATUS,
                font=theme.get_font(9),
                text_color=theme.TextMuted,
                anchor="e",
            )
            status.pack(side="right")
            button = ctk.CTkButton(
                row,
                text=button_text,
                height=24,
                width=120,
                fg_color=_GF_CARD_SOFT,
                hover_color=_GF_FIELD_HOVER,
                text_color=theme.TextPrimary,
                command=lambda mod=module_key: self._on_details_module_clicked(mod),
            )
            button.pack(fill="x", pady=(3, 0))
            self._details_module_rows[module_key] = row
            self._details_module_buttons[module_key] = button
            self._details_module_status_labels[module_key] = status
        self._details_container_frame = frame
        self._details_container_built = True

    def _show_details_shell(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        self._ensure_details_shell_built()
        if self._details_container_frame is None:
            return
        is_media = m.element_type == "media_section"
        fields = editor_field_visibility(m.element_type or "unknown")
        if self._details_container_title_label is not None:
            self._details_container_title_label.configure(text=_GF_DETAILS_SHELL_TITLE)
        if self._details_container_subtext_label is not None:
            subtext = _GF_MEDIA_DETAILS_SHELL_SUBTEXT if is_media else _GF_DETAILS_SHELL_SUBTEXT
            self._details_container_subtext_label.configure(text=subtext)
        cache_entry = self._section_visual_cache.get(m.element_id)
        module_visibility = {
            "preview": True,
            "page_context": fields.page_context,
            "layer_nav": True,
            "children": fields.children,
        }
        for module_key, row in self._details_module_rows.items():
            visible = module_visibility.get(module_key, False)
            if visible:
                try:
                    row.pack(fill="x", pady=(0, 8))
                except tk.TclError:
                    pass
                cached = (
                    cache_entry is not None
                    and self._details_module_cache_hit(cache_entry, module_key)
                )
                status_text = _GF_DETAILS_MODULE_LOADED_STATUS if cached else _GF_DETAILS_MODULE_IDLE_STATUS
                self._update_details_module_status(module_key, status_text)
            else:
                try:
                    row.pack_forget()
                except tk.TclError:
                    pass
        pack_before = None
        if self._section_preview_card is not None:
            pack_before = self._section_preview_card
        elif self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
            pack_before = self._layer_nav_frame
        try:
            if pack_before is not None:
                self._details_container_frame.pack(
                    fill="x",
                    padx=_CARD_PAD_X,
                    pady=(0, 8),
                    before=pack_before,
                )
            else:
                self._details_container_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
        except tk.TclError:
            try:
                self._details_container_frame.pack(fill="x", padx=_CARD_PAD_X, pady=(0, 8))
            except tk.TclError:
                pass

    def _hide_details_shell(self) -> None:
        if self._details_container_frame is None:
            return
        try:
            self._details_container_frame.pack_forget()
        except tk.TclError:
            pass

    def _hide_details_container(self) -> None:
        """Legacy alias — details shell hide."""
        self._hide_details_shell()

    def _update_details_module_status(self, module_key: str, text: str) -> None:
        label = self._details_module_status_labels.get(module_key)
        if label is None:
            return
        try:
            display = text if text else _GF_DETAILS_MODULE_LOADED_STATUS
            label.configure(text=display)
        except tk.TclError:
            pass

    def _on_details_module_clicked(self, module: str) -> None:
        element_id = self._details_on_demand_active_element_id or self._selected_id
        if not element_id:
            return
        m = self._merged_by_id.get(element_id)
        if m is None or self._selected_id != element_id:
            return

        self._cancel_details_on_demand_jobs()
        self._details_on_demand_generation += 1
        module_generation = self._details_on_demand_generation
        self._details_on_demand_request_mono = time.perf_counter()
        self._details_on_demand_active_element_id = element_id

        log_event(
            "studio.gicleeframe.details_module.requested",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=module_generation,
            since_request_ms=0.0,
        )

        cache_entry = self._section_visual_cache.get(element_id)
        if cache_entry is not None and self._details_module_cache_hit(cache_entry, module):
            log_event(
                "studio.gicleeframe.details_module.cache_hit",
                module=module,
                element_id=element_id,
                element_type=m.element_type,
                generation=module_generation,
                since_request_ms=self._since_details_request_ms(),
            )
            self._apply_details_module_from_cache(m, module, cache_entry, module_generation)
            return

        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADING_STATUS)
        if module == "children":
            self._schedule_details_on_demand_job(
                0,
                lambda mod=module, eid=element_id, gen=module_generation: (
                    self._run_children_details_module_batched(
                        eid,
                        gen,
                        mod,
                        start=0,
                    )
                ),
            )
            return

        self._schedule_details_on_demand_job(
            0,
            lambda mod=module, eid=element_id, gen=module_generation: (
                self._execute_details_module(eid, gen, mod)
            ),
        )

    def _apply_details_module_from_cache(
        self,
        m: MergedPageElement,
        module: str,
        entry: SectionVisualCacheEntry,
        generation: int,
    ) -> None:
        if not self._details_stage_still_valid(m.element_id, generation):
            return
        started = time.perf_counter()
        if module == "preview":
            self._apply_cached_preview_module(entry)
        elif module == "page_context":
            self._apply_cached_page_context_module(entry)
        elif module == "layer_nav":
            self._apply_cached_layer_nav_module(entry)
        elif module == "children":
            self._apply_cached_children_module(m, entry)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )

    def _execute_details_module(self, element_id: str, generation: int, module: str) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        stale_refresh = self._editor_has_ready_content
        fields = editor_field_visibility(m.element_type or "unknown")

        if module == "preview":
            self._show_heavy_editor_modules()
            self._update_section_preview(m, stale_refresh=stale_refresh)
        elif module == "page_context":
            if fields.page_context:
                self._fill_page_context(m, show=True)
        elif module == "layer_nav":
            self._update_layer_nav(m, stale_refresh=stale_refresh)
        elif module == "children":
            self._set_row_visible(self._children_overview_row, True)
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)

        self._save_details_module_cache(m, module, fields)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=False,
        )

    def _run_children_details_module_batched(
        self,
        element_id: str,
        generation: int,
        module: str,
        *,
        start: int,
    ) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        parent_row = self._tree_row_for_element(element_id)
        children = parent_row.children if parent_row is not None else ()
        total = len(children)
        end = min(start + _GF_DETAILS_CHILDREN_BATCH_SIZE, total)
        started = time.perf_counter()
        stale_refresh = self._editor_has_ready_content

        self._set_row_visible(self._children_overview_row, True)
        self._fill_children_overview_buttons_range(
            m,
            start,
            end,
            stale_refresh=stale_refresh and start == 0,
        )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if total > 2 or (total > 0 and end < total):
            log_event(
                "studio.gicleeframe.details_module.batch",
                module=module,
                start=start,
                end=end,
                total=total,
                elapsed_ms=elapsed_ms,
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
            )

        if end < total:
            self._schedule_details_on_demand_job(
                _GF_DETAILS_STAGE_GAP_MS,
                lambda s=end: self._run_children_details_module_batched(
                    element_id,
                    generation,
                    module,
                    start=s,
                ),
            )
            return

        fields = editor_field_visibility(m.element_type or "unknown")
        self._save_details_module_cache(m, module, fields)
        self._update_details_module_status(module, _GF_DETAILS_MODULE_LOADED_STATUS)
        total_elapsed_ms = self._since_details_request_ms()
        log_event(
            "studio.gicleeframe.details_module.ready",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_module.applied",
            module=module,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )

    def _save_details_module_cache(
        self,
        m: MergedPageElement,
        module: str,
        fields: EditorFieldVisibility,
    ) -> None:
        existing = self._section_visual_cache.get(m.element_id)
        preview_key = self._preview_key_for_element(m)
        layer_nav_titles: tuple[str, ...] = ()
        layer_nav_visible = False
        if module == "layer_nav":
            if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                layer_nav_visible = True
                items = self._selected_layer_items(m)
                layer_nav_titles = tuple(title for _, _, title in items)
            elif existing is not None:
                layer_nav_visible = existing.layer_nav_visible
                layer_nav_titles = existing.layer_nav_titles
        elif existing is not None:
            layer_nav_visible = existing.layer_nav_visible
            layer_nav_titles = existing.layer_nav_titles

        effective_preview_key = preview_key if module == "preview" else (
            existing.preview_key if existing is not None else ""
        )
        subtitle = (
            self._editor_section_subtitle.cget("text")
            if self._editor_section_subtitle is not None
            else editor_title_for_element(m)
        )
        page_context_summary = tuple(self._page_context_shell_summary_lines(m))
        if existing is not None and module != "page_context":
            page_context_summary = existing.page_context_summary

        self._section_visual_cache[m.element_id] = SectionVisualCacheEntry(
            element_type=m.element_type or "unknown",
            status=m.status or "ok",
            has_draft_patch=m.has_draft_patch,
            title=m.title,
            text=m.text,
            alt=m.alt,
            image_ref=m.image_ref,
            notes=m.notes,
            visible=m.visible,
            subtitle_text=subtitle,
            page_context_summary=page_context_summary,
            fields_title=fields.title,
            fields_text=fields.text,
            fields_alt=fields.alt,
            fields_image_ref=fields.image_ref,
            fields_notes=fields.notes,
            fields_visible=fields.visible,
            fields_children=fields.children,
            fields_page_context=fields.page_context,
            media_details_built=bool(existing and existing.media_details_built),
            preview_key=effective_preview_key or (existing.preview_key if existing else ""),
            layer_nav_visible=layer_nav_visible,
            layer_nav_titles=layer_nav_titles,
            details_cache_preview=(
                module == "preview" or bool(existing and existing.details_cache_preview)
            ),
            details_cache_page_context=(
                module == "page_context"
                or bool(existing and existing.details_cache_page_context)
            ),
            details_cache_layer_nav=(
                module == "layer_nav" or bool(existing and existing.details_cache_layer_nav)
            ),
            details_cache_children=(
                module == "children" or bool(existing and existing.details_cache_children)
            ),
        )
        log_event(
            "studio.gicleeframe.selection.visual_cache_saved",
            element_id=m.element_id,
            element_type=m.element_type,
            media_details_built=False,
            details_module=module,
            minimal_only=False,
            generation=self._selection_generation,
        )

    def _apply_details_cache_hit(
        self,
        m: MergedPageElement,
        entry: SectionVisualCacheEntry,
        generation: int,
    ) -> None:
        """Legacy — full details cache apply; not used by shell CTA."""
        if not self._details_stage_still_valid(m.element_id, generation):
            return
        started = time.perf_counter()
        fields = self._fields_from_cache_entry(entry)
        stale_refresh = self._editor_has_ready_content

        self._hide_details_on_demand_block()
        self._hide_details_shell()
        self._show_heavy_editor_modules()
        self._apply_cached_media_details(entry)
        if fields.page_context:
            self._apply_cached_page_context_summary(entry)
        self._set_row_visible(self._children_overview_row, fields.children)
        if fields.children:
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)

        self._details_on_demand_expanded = True
        self._hide_editor_refresh_status()
        self._mark_editor_content_ready(m)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        details_cta_ms = self._since_details_cta_ms()
        log_event(
            "studio.gicleeframe.details_on_demand.ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
            shell_only=False,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.all_done",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
            from_cache=True,
        )

    def _apply_heavy_details_on_demand(self, m: MergedPageElement) -> None:
        """Legacy internal — staged pipeline; not started from shell CTA."""
        self._begin_details_on_demand_stages(m.element_id, self._details_on_demand_generation)

    def _details_stage_still_valid(self, element_id: str, generation: int) -> bool:
        if generation != self._details_on_demand_generation:
            return False
        if self._selected_id != element_id:
            return False
        if self._details_on_demand_active_element_id != element_id:
            return False
        if not self.winfo_exists():
            return False
        return True

    def _details_on_demand_stages_for(self, m: MergedPageElement) -> list[str]:
        fields = editor_field_visibility(m.element_type or "unknown")
        stages: list[str] = ["summary", "preview"]
        if fields.page_context:
            stages.append("page_context")
        stages.append("layer_nav")
        if fields.children:
            stages.append("children")
        return stages

    def _begin_details_on_demand_stages(self, element_id: str, generation: int) -> None:
        """Legacy internal — full auto chain; suppressed after PERF-F.5 shell CTA."""
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        self._show_heavy_editor_modules()
        stages = self._details_on_demand_stages_for(m)
        self._schedule_next_details_stage(element_id, generation, stages, 0)

    def _schedule_next_details_stage(
        self,
        element_id: str,
        generation: int,
        stages: list[str],
        index: int,
    ) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        if index >= len(stages):
            self._schedule_details_on_demand_job(
                0,
                lambda eid=element_id, gen=generation: self._finalize_details_on_demand(
                    eid,
                    gen,
                ),
            )
            return
        stage = stages[index]
        delay_ms = 0 if index == 0 else _GF_DETAILS_STAGE_GAP_MS
        merged = self._merged_by_id.get(element_id)
        log_event(
            "studio.gicleeframe.details_on_demand.stage_scheduled",
            stage=stage,
            element_id=element_id,
            element_type=merged.element_type if merged is not None else "",
            generation=generation,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_details_on_demand_job(
            delay_ms,
            lambda eid=element_id, gen=generation, stg=stage, idx=index, stgs=stages: (
                self._execute_details_on_demand_stage(eid, gen, stgs, idx, stg)
            ),
        )

    def _execute_details_on_demand_stage(
        self,
        element_id: str,
        generation: int,
        stages: list[str],
        index: int,
        stage: str,
    ) -> None:
        """Legacy internal — monolithic staged pipeline stage executor."""
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        log_event(
            "studio.gicleeframe.details_on_demand.stage_start",
            stage=stage,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            since_request_ms=self._since_details_request_ms(),
        )
        stale_refresh = self._editor_has_ready_content
        fields = editor_field_visibility(m.element_type or "unknown")

        if stage == "summary":
            pass
        elif stage == "preview":
            self._update_section_preview(m, stale_refresh=stale_refresh)
            self._update_details_module_status("preview", "")
        elif stage == "page_context":
            if fields.page_context:
                self._fill_page_context(m, show=True)
        elif stage == "layer_nav":
            self._update_layer_nav(m, stale_refresh=stale_refresh)
            self._update_details_module_status("layer_nav", "")
        elif stage == "children":
            self._set_row_visible(self._children_overview_row, True)
            self._run_children_details_stage_batched(
                m,
                generation,
                stale_refresh=stale_refresh,
                start=0,
                stages=stages,
                stage_index=index,
            )
            return

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.details_on_demand.stage_done",
            stage=stage,
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_next_details_stage(element_id, generation, stages, index + 1)

    def _run_children_details_stage_batched(
        self,
        m: MergedPageElement,
        generation: int,
        *,
        stale_refresh: bool,
        start: int,
        stages: list[str],
        stage_index: int,
    ) -> None:
        element_id = m.element_id
        if not self._details_stage_still_valid(element_id, generation):
            return
        parent_row = self._tree_row_for_element(element_id)
        children = parent_row.children if parent_row is not None else ()
        total = len(children)
        end = min(start + _GF_DETAILS_CHILDREN_BATCH_SIZE, total)
        started = time.perf_counter()

        self._fill_children_overview_buttons_range(
            m,
            start,
            end,
            stale_refresh=stale_refresh and start == 0,
        )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        if total > 0 and (end < total or elapsed_ms > 80):
            log_event(
                "studio.gicleeframe.details_on_demand.stage_batch",
                stage="children",
                start=start,
                end=end,
                total=total,
                elapsed_ms=elapsed_ms,
                element_id=element_id,
                element_type=m.element_type,
                generation=generation,
            )

        if end < total:
            self._schedule_details_on_demand_job(
                _GF_DETAILS_STAGE_GAP_MS,
                lambda s=end: self._run_children_details_stage_batched(
                    m,
                    generation,
                    stale_refresh=stale_refresh,
                    start=s,
                    stages=stages,
                    stage_index=stage_index,
                ),
            )
            return

        self._update_details_module_status("children", "")
        log_event(
            "studio.gicleeframe.details_on_demand.stage_done",
            stage="children",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=elapsed_ms,
            since_request_ms=self._since_details_request_ms(),
        )
        self._schedule_next_details_stage(element_id, generation, stages, stage_index + 1)

    def _finalize_details_on_demand(self, element_id: str, generation: int) -> None:
        if not self._details_stage_still_valid(element_id, generation):
            return
        m = self._merged_by_id.get(element_id)
        if m is None:
            return
        started = time.perf_counter()
        fields = editor_field_visibility(m.element_type or "unknown")

        self._details_on_demand_expanded = True
        self._hide_details_on_demand_block()
        self._hide_details_shell()
        self._hide_media_details_stable_shell()
        self._hide_editor_refresh_status()
        self._save_section_visual_cache(m, fields, media_details_built=True)
        self._mark_editor_content_ready(m)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        total_elapsed_ms = self._since_details_request_ms()
        details_cta_ms = self._since_details_cta_ms()
        log_event(
            "studio.gicleeframe.details_on_demand.all_done",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_request_ms=total_elapsed_ms,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.ready",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )
        log_event(
            "studio.gicleeframe.details_on_demand.applied",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            elapsed_ms=total_elapsed_ms,
            since_details_cta_ms=details_cta_ms,
            since_request_ms=total_elapsed_ms,
            from_cache=False,
        )

    def _cancel_details_on_demand_jobs(self) -> int:
        cancelled = len(self._details_on_demand_after_ids)
        while self._details_on_demand_after_ids:
            after_id = self._details_on_demand_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        return cancelled

    def _schedule_details_on_demand_job(self, delay_ms: int, callback: Callable[[], None]) -> None:
        after_id = self.after(delay_ms, callback)
        self._details_on_demand_after_ids.append(after_id)

    def _save_section_visual_cache(
        self,
        m: MergedPageElement,
        fields: EditorFieldVisibility,
        *,
        media_details_built: bool,
    ) -> None:
        layer_nav_titles: tuple[str, ...] = ()
        layer_nav_visible = False
        preview_key = self._preview_key_for_element(m)
        subtitle = (
            self._editor_section_subtitle.cget("text")
            if self._editor_section_subtitle is not None
            else editor_title_for_element(m)
        )
        existing = self._section_visual_cache.get(m.element_id)
        if media_details_built:
            if self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                layer_nav_visible = True
                items = self._selected_layer_items(m)
                layer_nav_titles = tuple(title for _, _, title in items)
            else:
                layer_nav_visible = existing.layer_nav_visible if existing else False
                layer_nav_titles = existing.layer_nav_titles if existing else ()
            effective_preview_key = preview_key
        else:
            layer_nav_visible = existing.layer_nav_visible if existing else False
            layer_nav_titles = existing.layer_nav_titles if existing else ()
            effective_preview_key = existing.preview_key if existing else ""
        effective_media_details = media_details_built or bool(
            existing and existing.media_details_built
        )
        if media_details_built:
            cache_preview = True
            cache_page_context = fields.page_context
            cache_layer_nav = True
            cache_children = fields.children
        elif existing is not None:
            cache_preview = existing.details_cache_preview
            cache_page_context = existing.details_cache_page_context
            cache_layer_nav = existing.details_cache_layer_nav
            cache_children = existing.details_cache_children
        else:
            cache_preview = False
            cache_page_context = False
            cache_layer_nav = False
            cache_children = False
        self._section_visual_cache[m.element_id] = SectionVisualCacheEntry(
            element_type=m.element_type or "unknown",
            status=m.status or "ok",
            has_draft_patch=m.has_draft_patch,
            title=m.title,
            text=m.text,
            alt=m.alt,
            image_ref=m.image_ref,
            notes=m.notes,
            visible=m.visible,
            subtitle_text=subtitle,
            page_context_summary=tuple(self._page_context_shell_summary_lines(m)),
            fields_title=fields.title,
            fields_text=fields.text,
            fields_alt=fields.alt,
            fields_image_ref=fields.image_ref,
            fields_notes=fields.notes,
            fields_visible=fields.visible,
            fields_children=fields.children,
            fields_page_context=fields.page_context,
            media_details_built=effective_media_details,
            preview_key=effective_preview_key,
            layer_nav_visible=layer_nav_visible,
            layer_nav_titles=layer_nav_titles,
            details_cache_preview=cache_preview,
            details_cache_page_context=cache_page_context,
            details_cache_layer_nav=cache_layer_nav,
            details_cache_children=cache_children,
        )
        log_event(
            "studio.gicleeframe.selection.visual_cache_saved",
            element_id=m.element_id,
            element_type=m.element_type,
            media_details_built=effective_media_details,
            minimal_only=not media_details_built,
            generation=self._selection_generation,
        )

    def _should_defer_editor_detail_populate(
        self,
        m: MergedPageElement,
        fields: object,
    ) -> bool:
        _ = (m, fields)
        return True

    def _populate_editor_preview_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.preview_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.preview_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_section_preview(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("preview", element_type=m.element_type, started=segment_started)

    def _populate_editor_layer_nav_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.layer_nav_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.layer_nav_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_layer_nav(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("layer_nav", element_type=m.element_type, started=segment_started)

    def _populate_editor_children_deferred(self, element_id: str, generation: int) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.children_deferred",
        )
        if m is None:
            return
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.children_deferred",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._fill_children_overview_buttons(m, stale_refresh=self._editor_has_ready_content)
        self._log_perf_e_update_done("children", element_type=m.element_type, started=segment_started)

    def _schedule_media_deferred_details(
        self,
        m: MergedPageElement,
        generation: int,
    ) -> None:
        if generation != self._selection_generation:
            return
        element_id = m.element_id
        if self._selection_visual_cache_applied:
            return
        started = time.perf_counter()
        log_event(
            "studio.gicleeframe.media_deferred.scheduled",
            element_id=element_id,
            element_type=m.element_type,
            generation=generation,
            jobs="preview,layer_nav,children",
            since_click_ms=self._since_selection_click_ms(),
        )
        self._schedule_selection_job(
            _GF_MEDIA_PREVIEW_AFTER_SHELL_MS,
            lambda eid=element_id, gen=generation, mono=started: self._populate_editor_media_details_batch(
                eid,
                gen,
                started_mono=mono,
            ),
        )
        if self._media_deferred_done_after_id is not None:
            try:
                self.after_cancel(self._media_deferred_done_after_id)
            except tk.TclError:
                pass
            self._media_deferred_done_after_id = None

    def _populate_editor_media_details_batch(
        self,
        element_id: str,
        generation: int,
        *,
        started_mono: float,
    ) -> None:
        m = self._merged_for_selection_generation(
            element_id,
            generation,
            event_prefix="studio.gicleeframe.populate_editor.media_details_batch",
        )
        if m is None:
            return
        stale_refresh = self._editor_has_ready_content
        segment_started = time.perf_counter()
        with span(
            "studio.gicleeframe.populate_editor.media_details_batch",
            element_id=element_id,
            element_type=m.element_type,
        ):
            self._update_section_preview(m, stale_refresh=stale_refresh)
            self._update_layer_nav(m, stale_refresh=stale_refresh)
            self._fill_children_overview_buttons(m, stale_refresh=stale_refresh)
        self._hide_media_details_stable_shell()
        self._hide_editor_refresh_status()
        fields = editor_field_visibility(m.element_type)
        self._save_section_visual_cache(m, fields, media_details_built=True)
        self._mark_editor_content_ready(m)
        log_event(
            "studio.gicleeframe.media_deferred.done",
            generation=generation,
            elapsed_ms=round((time.perf_counter() - started_mono) * 1000, 2),
            since_click_ms=self._since_selection_click_ms(),
        )
        self._log_perf_e_update_done(
            "media_details_batch",
            element_type=m.element_type,
            started=segment_started,
        )
