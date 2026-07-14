"""GICLÉE FRAME™ — visual detail renderers (preview, layer nav, children overview)."""

from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    MergedPageElement,
    SectionTreeRow,
    editor_title_for_element,
    parent_row_title,
)
from giclee_app.studio.perf import log_event, span
from . import theme
from .gicleeframe_view_editor_shell import _LAYER_NAV_TITLE
from .gicleeframe_view_models import _ellipsize, _section_kind_copy
from .gicleeframe_view_primitives import (
    _BTN_HEIGHT,
    _CARD_PAD_X,
    _CARD_PAD_Y,
    _GF_BORDER,
    _GF_BORDER_WARM,
    _GF_CARD_SOFT,
    _GF_FIELD,
    _GF_FIELD_HOVER,
    _GF_GOLD,
    _GF_GOLD_SOFT,
    _GF_MUTED,
    _GF_PREVIEW_BG,
    _GF_PREVIEW_MAT,
    _GF_PREVIEW_PAPER,
    _element_pill_colors,
    _make_card,
    _make_card_title,
    _make_gf_card,
    _make_secondary_button,
)

__all__ = ("GicleeFrameVisualDetailRenderersMixin",)


class GicleeFrameVisualDetailRenderersMixin:
    """Preview, layer-navigation and children-overview renderers."""

    def _parent_row_for_element(self, element_id: str | None):
        if not element_id:
            return None
        for row in self._section_tree_rows_cache:
            if row.element_id == element_id:
                return row
            for child in row.children:
                if child.element_id == element_id:
                    return row
        return None
    def _tree_row_for_element(self, element_id: str) -> SectionTreeRow | None:
        return next(
            (row for row in self._section_tree_rows_cache if row.element_id == element_id),
            None,
        )
    def _image_ref_label(self, image_ref: str) -> str:
        if not image_ref:
            return "Brak przypisanej grafiki"
        clean = image_ref.replace("shopify://", "")
        return clean.rsplit("/", 1)[-1] if "/" in clean else clean
    def _preview_meta_lines(self, m: MergedPageElement) -> list[str]:
        lines: list[str] = []
        element_type = m.element_type or "unknown"
        lines.append(f"Typ elementu: {element_type}")
        if m.section_key:
            lines.append(f"Klucz sekcji: {m.section_key}")
        if m.element_id:
            lines.append(f"ID: {m.element_id}")
        tree_row = self._tree_row_for_element(m.element_id)
        if tree_row is not None:
            child_count = len(tree_row.children)
            lines.append(f"Elementy podrzędne: {child_count}")
        settings_count = len(m.page_settings) or len(m.page_fields)
        if settings_count:
            lines.append(f"Ustawienia strony: {settings_count}")
        if m.label:
            lines.append(f"Etykieta: {_ellipsize(m.label, 40)}")
        if m.title and m.title != m.label:
            lines.append(f"Tytuł: {_ellipsize(m.title, 40)}")
        if m.text:
            lines.append(f"Tekst: {_ellipsize(m.text, 60)}")
        if m.notes:
            lines.append(f"Notatka: {_ellipsize(m.notes, 80)}")
        return lines
    def _apply_metadata_preview_content(
        self,
        preview_key: str,
        m: MergedPageElement,
        *,
        heading: str,
        subtitle: str,
        fallback: bool = False,
    ) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        meta_lines = self._preview_meta_lines(m)
        meta_text = "\n".join(meta_lines) if meta_lines else "Brak dodatkowych metadanych."
        if fallback:
            meta_text = (
                "Brak szczegółowego podglądu dla tego typu sekcji.\n\n"
                f"{meta_text}"
            )
            log_event(
                "studio.gicleeframe.preview.fallback_used",
                element_type=m.element_type,
                element_id=m.element_id,
                preview_key=preview_key,
            )
        for widget_key, text in (
            ("heading_label", heading),
            ("subtitle_label", subtitle),
            ("meta_label", meta_text),
        ):
            widget = widgets.get(widget_key)
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=text)
    def _build_section_metadata_preview_structure(
        self,
        frame: ctk.CTkFrame,
        preview_key: str,
        *,
        hint_text: str,
    ) -> None:
        layout = ctk.CTkFrame(frame, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=14, pady=12)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)

        hint_box = ctk.CTkFrame(
            layout,
            fg_color=_GF_CARD_SOFT,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
            width=96,
        )
        hint_box.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        hint_box.grid_propagate(False)

        hint_label = self._get_or_create_preview_label(
            preview_key,
            "hint_label",
            hint_box,
            label=hint_text,
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
        )
        hint_label.place(relx=0.5, rely=0.5, anchor="center")

        meta = ctk.CTkFrame(layout, fg_color="transparent")
        meta.grid(row=0, column=1, sticky="nsew")

        self._get_or_create_preview_label(
            preview_key,
            "heading_label",
            meta,
            label="",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
        ).pack(fill="x", pady=(4, 4))

        self._get_or_create_preview_label(
            preview_key,
            "subtitle_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_GOLD_SOFT,
            wraplength=360,
        ).pack(fill="x", pady=(0, 6))

        self._get_or_create_preview_label(
            preview_key,
            "meta_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            justify="left",
            wraplength=360,
        ).pack(fill="x")
    def _selected_layer_items(self, m: MergedPageElement) -> list[tuple[str, str, str]]:
        parent = self._parent_row_for_element(m.element_id)
        if parent is None or not parent.children:
            return []

        items: list[tuple[str, str, str]] = [
            (parent.element_id, "SEKCJA", parent.display_title),
        ]
        for child in parent.children:
            label = editor_title_for_element(child.merged).replace("Edytor: ", "").upper()
            items.append((child.element_id, label, child.child_label))
        return items
    def _layer_nav_tile_signature(
        self,
        *,
        kind: str,
        title: str,
        meta: str,
        element_id: str | None,
        active: bool,
    ) -> tuple[Any, ...]:
        return (
            kind or "",
            title or "",
            meta or "",
            element_id or "",
            bool(active),
        )
    def _sync_layer_nav_visibility(self, desired_keys: list[str]) -> None:
        desired_set = set(desired_keys)
        previous_set = set(self._layer_nav_visible_order)
        for key in previous_set - desired_set:
            frame = self._layer_nav_tile_cache.get(key)
            if frame is None:
                continue
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
            self._layer_nav_visible_keys.discard(key)
        self._layer_nav_visible_order = tuple(desired_keys)
    def _hide_layer_nav_tiles(self) -> None:
        for key, frame in self._layer_nav_tile_cache.items():
            if not key.startswith("slot:"):
                continue
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
        self._layer_nav_visible_keys = {
            key for key in self._layer_nav_visible_keys if not key.startswith("slot:")
        }
    def _show_layer_nav_tile(self, key: str) -> None:
        if key in self._layer_nav_visible_keys:
            return
        frame = self._layer_nav_tile_cache.get(key)
        if frame is None:
            return
        try:
            frame.pack(side="left", fill="x", expand=True, padx=(0, 6), pady=(0, 4))
            self._layer_nav_visible_keys.add(key)
        except tk.TclError:
            return
    def _get_or_create_layer_nav_header(self) -> ctk.CTkLabel:
        if self._layer_nav_frame is None:
            raise RuntimeError("layer_nav_frame is not initialized")
        if self._layer_nav_header_label is not None:
            return self._layer_nav_header_label
        label = ctk.CTkLabel(
            self._layer_nav_frame,
            text=_LAYER_NAV_TITLE.upper(),
            font=theme.get_font(8, "bold"),
            text_color=_GF_GOLD_SOFT,
            anchor="w",
        )
        self._layer_nav_header_label = label
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key="header:title",
        )
        return label
    def _get_or_create_layer_nav_row(self) -> ctk.CTkFrame:
        if self._layer_nav_frame is None:
            raise RuntimeError("layer_nav_frame is not initialized")
        key = "container:row"
        cached = self._layer_nav_tile_cache.get(key)
        if cached is not None:
            return cached
        row = ctk.CTkFrame(self._layer_nav_frame, fg_color="transparent")
        self._layer_nav_tile_cache[key] = row
        self._layer_nav_row_frame = row
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key=key,
        )
        return row
    def _get_or_create_layer_nav_tile(self, key: str) -> ctk.CTkFrame:
        cached = self._layer_nav_tile_cache.get(key)
        if cached is not None:
            return cached
        row = self._get_or_create_layer_nav_row()
        tile = ctk.CTkFrame(
            row,
            fg_color=_GF_FIELD,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
        )
        kind_label = ctk.CTkLabel(
            tile,
            text="",
            font=theme.get_font(8, "bold"),
            text_color=_GF_MUTED,
            anchor="w",
        )
        kind_label.pack(fill="x", padx=10, pady=(8, 1))
        title_label = ctk.CTkLabel(
            tile,
            text="",
            font=theme.get_font(10, "bold"),
            text_color=theme.TextPrimary,
            anchor="w",
        )
        title_label.pack(fill="x", padx=10, pady=(0, 8))
        self._layer_nav_tile_cache[key] = tile
        self._layer_nav_meta_widgets[key] = kind_label
        self._layer_nav_title_widgets[key] = title_label
        log_event(
            "studio.gicleeframe.layer_nav.tile_created",
            key=key,
        )
        return tile
    def _update_layer_nav_tile(
        self,
        key: str,
        *,
        kind: str = "",
        title: str,
        meta: str = "",
        element_id: str | None = None,
        active: bool = False,
    ) -> None:
        tile = self._get_or_create_layer_nav_tile(key)
        signature = self._layer_nav_tile_signature(
            kind=kind,
            title=title,
            meta=meta,
            element_id=element_id,
            active=active,
        )
        if self._layer_nav_rendered_signatures.get(key) == signature:
            self._show_layer_nav_tile(key)
            log_event(
                "studio.gicleeframe.layer_nav.tile_skipped",
                key=key,
            )
            return

        previous = self._layer_nav_rendered_signatures.get(key)
        kind_widget = self._layer_nav_meta_widgets.get(key)
        if kind_widget is not None and (
            previous is None or previous[0] != kind or previous[4] != active
        ):
            kind_widget.configure(
                text=kind,
                text_color=_GF_GOLD_SOFT if active else _GF_MUTED,
            )
        title_widget = self._layer_nav_title_widgets.get(key)
        if title_widget is not None and (previous is None or previous[1] != title):
            title_widget.configure(text=_ellipsize(title, 24))
        if previous is None or previous[4] != active:
            try:
                tile.configure(
                    fg_color=_GF_CARD_SOFT if active else _GF_FIELD,
                    border_color=_GF_BORDER_WARM if active else _GF_BORDER,
                )
            except tk.TclError:
                pass

        previous_target = self._layer_nav_bound_targets.get(key)
        if element_id and previous_target != element_id:
            click_handler = lambda _e, eid=element_id: self._select_element(eid)
            try:
                tile.bind("<Button-1>", click_handler)
                for child in tile.winfo_children():
                    child.bind("<Button-1>", click_handler)
            except tk.TclError:
                pass
            self._layer_nav_bound_targets[key] = element_id

        self._layer_nav_rendered_signatures[key] = signature
        self._show_layer_nav_tile(key)
        log_event(
            "studio.gicleeframe.layer_nav.tile_updated",
            key=key,
            active=active,
            has_target=bool(element_id),
        )
    def _update_layer_nav(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        if self._layer_nav_frame is None:
            return

        with span(
            "studio.gicleeframe.populate.layer_nav",
            element_type=m.element_type,
            selected_id=m.element_id,
            cached_tiles=len(self._layer_nav_tile_cache),
        ):
            before_children = len(self._layer_nav_frame.winfo_children())
            items = self._selected_layer_items(m)

            if not items:
                if stale_refresh and self._layer_nav_frame is not None and self._layer_nav_frame.winfo_manager():
                    log_event(
                        "studio.gicleeframe.editor.stale_content_kept",
                        element_id=m.element_id,
                        element_type=m.element_type,
                        previous_element_id=self._editor_last_ready_element_id or "",
                        since_click_ms=self._since_selection_click_ms(),
                        region="layer_nav",
                    )
                    return
                self._sync_layer_nav_visibility([])
                self._layer_nav_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.layer_nav.delta",
                    element_type=m.element_type,
                    desired_tiles=0,
                    cached_tiles=len(self._layer_nav_tile_cache),
                    visible_tiles=0,
                    before_children=before_children,
                    after_children=len(self._layer_nav_frame.winfo_children()),
                )
                log_event(
                    "studio.gicleeframe.layer_nav.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._layer_nav_frame.winfo_children()),
                    visible_tiles=0,
                    cached_tiles=len(self._layer_nav_tile_cache),
                )
                log_event(
                    "studio.gicleeframe.layer_nav",
                    element_type=m.element_type,
                    children_before_destroy=before_children,
                    items_built=0,
                )
                return

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
            for index, (element_id, kind, title) in enumerate(items):
                slot_key = f"slot:{index}"
                desired_keys.append(slot_key)
                self._update_layer_nav_tile(
                    slot_key,
                    kind=kind,
                    title=title,
                    element_id=element_id,
                    active=element_id == self._selected_id,
                )

            self._sync_layer_nav_visibility(desired_keys)

            if stale_refresh:
                self._log_editor_content_swapped(m, region="layer_nav")

            log_event(
                "studio.gicleeframe.layer_nav.delta",
                element_type=m.element_type,
                desired_tiles=len(desired_keys),
                cached_tiles=len(self._layer_nav_tile_cache),
                visible_tiles=len(
                    [key for key in self._layer_nav_visible_keys if key.startswith("slot:")]
                ),
                before_children=before_children,
                after_children=len(self._layer_nav_frame.winfo_children()),
            )
            log_event(
                "studio.gicleeframe.layer_nav.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(self._layer_nav_frame.winfo_children()),
                visible_tiles=len(
                    [key for key in self._layer_nav_visible_keys if key.startswith("slot:")]
                ),
                cached_tiles=len(self._layer_nav_tile_cache),
            )
            log_event(
                "studio.gicleeframe.layer_nav",
                element_type=m.element_type,
                children_before_destroy=before_children,
                items_built=len(items),
            )
    def _preview_key_for_element(self, m: MergedPageElement) -> str:
        element_type = m.element_type or "default"
        if element_type in {"divider", "image", "media_section", "section_legacy"}:
            return f"preview:{element_type}"
        if element_type in {"jumbo", "body", "heading", "text", "rich_text"}:
            return "preview:text"
        return "preview:default"
    def _hide_preview_frames(self) -> None:
        for frame in self._preview_frame_cache.values():
            try:
                frame.pack_forget()
            except tk.TclError:
                continue
        self._preview_active_key = None
    def _show_preview_frame(self, key: str) -> None:
        frame = self._preview_frame_cache.get(key)
        if frame is None:
            return
        if self._preview_active_key == key:
            return
        try:
            frame.pack(fill="both", expand=True)
            self._preview_active_key = key
        except tk.TclError:
            return
    def _get_or_create_preview_frame(self, key: str) -> ctk.CTkFrame:
        canvas = self._section_preview_canvas
        if canvas is None:
            raise RuntimeError("section_preview_canvas is not initialized")
        cached = self._preview_frame_cache.get(key)
        if cached is not None:
            return cached
        frame = ctk.CTkFrame(canvas, fg_color="transparent")
        self._preview_frame_cache[key] = frame
        self._preview_value_widgets[key] = {}
        log_event(
            "studio.gicleeframe.preview.frame_created",
            key=key,
        )
        return frame
    def _get_or_create_preview_label(
        self,
        preview_key: str,
        widget_key: str,
        parent: ctk.CTkBaseClass,
        *,
        label: str = "",
        wraplength: int | None = None,
        **kwargs: Any,
    ) -> ctk.CTkLabel:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        cached = widgets.get(widget_key)
        if isinstance(cached, ctk.CTkLabel):
            return cached
        label_kwargs: dict[str, Any] = {
            "text": label,
            "anchor": "w",
            "justify": "left",
        }
        if wraplength is not None:
            label_kwargs["wraplength"] = wraplength
        label_kwargs.update(kwargs)
        widget = ctk.CTkLabel(parent, **label_kwargs)
        widgets[widget_key] = widget
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key=widget_key,
        )
        return widget
    def _clear_preview_shell_bootstrap_once(self) -> None:
        canvas = self._section_preview_canvas
        if canvas is None or self._preview_shell_bootstrapped:
            return
        if self._preview_bootstrap_panel is not None:
            try:
                self._preview_bootstrap_panel.destroy()
            except tk.TclError:
                pass
            self._preview_bootstrap_panel = None
            self._preview_bootstrap_status_label = None
        cached_frames = set(self._preview_frame_cache.values())
        bootstrap_children = [
            child for child in canvas.winfo_children() if child not in cached_frames
        ]
        if not bootstrap_children:
            self._preview_shell_bootstrapped = True
            return
        for child in bootstrap_children:
            try:
                child.destroy()
            except tk.TclError:
                continue
        self._preview_shell_bootstrapped = True
        log_event(
            "studio.gicleeframe.preview.destroy_fallback",
            reason="shell_bootstrap",
        )
    def _divider_preview_dimensions(self, m: MergedPageElement) -> tuple[int, int]:
        height = 2
        width_pad = 52
        for field in m.page_settings:
            if field.key == "thickness":
                try:
                    height = max(1, min(10, int(float(field.value) * 2)))
                except (TypeError, ValueError):
                    height = 2
            elif field.key == "width_percent":
                try:
                    width = max(20, min(100, int(float(field.value))))
                    width_pad = int(52 + ((100 - width) * 0.9))
                except (TypeError, ValueError):
                    width_pad = 52
        return height, width_pad
    def _build_divider_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        ghost_top = ctk.CTkFrame(frame, fg_color=_GF_FIELD_HOVER, corner_radius=999, height=4)
        ghost_top.pack(fill="x", padx=38, pady=(16, 10))
        ghost_top.pack_propagate(False)
        widgets["ghost_top"] = ghost_top

        line = ctk.CTkFrame(
            frame,
            height=2,
            fg_color=_GF_GOLD,
            corner_radius=999,
        )
        line.pack(fill="x", padx=52, pady=(4, 10))
        line.pack_propagate(False)
        widgets["line"] = line
        self._section_preview_line = line

        ghost_bottom = ctk.CTkFrame(frame, fg_color=_GF_FIELD_HOVER, corner_radius=999, height=4)
        ghost_bottom.pack(fill="x", padx=70, pady=(0, 14))
        ghost_bottom.pack_propagate(False)
        widgets["ghost_bottom"] = ghost_bottom
    def _update_divider_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        line = widgets.get("line")
        if not isinstance(line, ctk.CTkFrame):
            return
        height, width_pad = self._divider_preview_dimensions(m)
        line.configure(height=height)
        line.pack_configure(padx=max(18, width_pad))
        self._section_preview_line = line
    def _build_media_section_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="SEKCJA",
        )
    def _update_media_section_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.title or m.label or parent_row_title(m) or "Sekcja edytorska"
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Uproszczony podgląd struktury sekcji",
        )
    def _build_legacy_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="LEGACY",
        )
    def _update_legacy_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.label or parent_row_title(m) or "Sekcja legacy"
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Sekcja legacy · tylko podgląd / notatka",
        )
    def _build_default_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        self._build_section_metadata_preview_structure(
            frame,
            preview_key,
            hint_text="INFO",
        )
    def _update_default_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        heading = m.title or m.label or editor_title_for_element(m)
        self._apply_metadata_preview_content(
            preview_key,
            m,
            heading=_ellipsize(heading, 48),
            subtitle="Podgląd metadanych elementu",
            fallback=True,
        )
    def _build_image_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        layout = ctk.CTkFrame(frame, fg_color="transparent")
        layout.pack(fill="both", expand=True, padx=16, pady=12)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)

        image_box = ctk.CTkFrame(
            layout,
            fg_color=_GF_CARD_SOFT,
            corner_radius=12,
            border_width=1,
            border_color=_GF_BORDER,
            width=96,
        )
        image_box.grid(row=0, column=0, sticky="ns", padx=(0, 14))
        image_box.grid_propagate(False)

        ctk.CTkLabel(
            image_box,
            text="IMAGE",
            font=theme.get_font(9, "bold"),
            text_color=_GF_GOLD_SOFT,
        ).place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            image_box,
            text="RAM",
            font=theme.get_font(8),
            text_color=_GF_MUTED,
        ).place(relx=0.5, rely=0.62, anchor="center")

        meta = ctk.CTkFrame(layout, fg_color="transparent")
        meta.grid(row=0, column=1, sticky="nsew")

        self._get_or_create_preview_label(
            preview_key,
            "heading_label",
            meta,
            label="Grafika sekcji",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
        ).pack(fill="x", pady=(4, 4))

        ref_label = self._get_or_create_preview_label(
            preview_key,
            "ref_label",
            meta,
            label="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            wraplength=360,
        )
        ref_label.pack(fill="x")

        self._get_or_create_preview_label(
            preview_key,
            "footnote_label",
            meta,
            label="Źródło tylko do podglądu · bez zapisu pliku",
            font=theme.get_font(8),
            text_color=_GF_GOLD_SOFT,
        ).pack(fill="x", pady=(8, 0))
    def _update_image_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        ref_label = widgets.get("ref_label")
        if isinstance(ref_label, ctk.CTkLabel):
            ref_label.configure(text=_ellipsize(self._image_ref_label(m.image_ref), 52))
    def _build_text_preview_structure(self, frame: ctk.CTkFrame, preview_key: str) -> None:
        widgets = self._preview_value_widgets.setdefault(preview_key, {})
        box = ctk.CTkFrame(frame, fg_color=_GF_FIELD, corner_radius=10)
        box.pack(fill="both", expand=True, padx=18, pady=14)

        title_label = ctk.CTkLabel(
            box,
            text="",
            font=theme.get_font(11, "bold"),
            text_color=theme.TextPrimary,
            anchor="center",
        )
        title_label.place(relx=0.5, rely=0.42, anchor="center")
        widgets["title_label"] = title_label
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key="title_label",
        )

        kind_label = ctk.CTkLabel(
            box,
            text="",
            font=theme.get_font(9),
            text_color=_GF_MUTED,
            anchor="center",
        )
        kind_label.place(relx=0.5, rely=0.62, anchor="center")
        widgets["kind_label"] = kind_label
        log_event(
            "studio.gicleeframe.preview.widget_created",
            preview_key=preview_key,
            widget_key="kind_label",
        )
    def _update_text_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        widgets = self._preview_value_widgets.get(preview_key, {})
        title_label = widgets.get("title_label")
        kind_label = widgets.get("kind_label")
        label = m.title or m.label or editor_title_for_element(m)
        if isinstance(title_label, ctk.CTkLabel):
            title_label.configure(text=_ellipsize(label, 48))
        if isinstance(kind_label, ctk.CTkLabel):
            kind_label.configure(text=editor_title_for_element(m))
    def _ensure_preview_structure(self, preview_key: str) -> None:
        if preview_key in self._preview_frame_cache:
            frame = self._preview_frame_cache[preview_key]
            if frame.winfo_children():
                return
        frame = self._get_or_create_preview_frame(preview_key)
        if preview_key == "preview:divider":
            self._build_divider_preview_structure(frame, preview_key)
        elif preview_key == "preview:media_section":
            self._build_media_section_preview_structure(frame, preview_key)
        elif preview_key == "preview:section_legacy":
            self._build_legacy_preview_structure(frame, preview_key)
        elif preview_key == "preview:image":
            self._build_image_preview_structure(frame, preview_key)
        elif preview_key == "preview:text":
            self._build_text_preview_structure(frame, preview_key)
        elif preview_key == "preview:default":
            self._build_default_preview_structure(frame, preview_key)
        else:
            self._build_default_preview_structure(frame, preview_key)
    def _update_preview_content(self, preview_key: str, m: MergedPageElement) -> None:
        if preview_key == "preview:divider":
            self._update_divider_preview_content(preview_key, m)
        elif preview_key == "preview:media_section":
            self._update_media_section_preview_content(preview_key, m)
        elif preview_key == "preview:section_legacy":
            self._update_legacy_preview_content(preview_key, m)
        elif preview_key == "preview:image":
            self._update_image_preview_content(preview_key, m)
        elif preview_key == "preview:text":
            self._update_text_preview_content(preview_key, m)
        elif preview_key == "preview:default":
            self._update_default_preview_content(preview_key, m)
        else:
            self._update_default_preview_content(preview_key, m)
    def _update_section_preview(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        canvas = self._section_preview_canvas
        if canvas is None:
            return

        with span(
            "studio.gicleeframe.populate.preview",
            element_type=m.element_type,
            selected_id=m.element_id,
            cached_frames=len(self._preview_frame_cache),
            stale_refresh=stale_refresh,
        ):
            before_children = len(canvas.winfo_children())
            preview_key = self._preview_key_for_element(m)
            previous_key = self._preview_active_key

            if self._section_preview_badge is not None:
                self._section_preview_badge.configure(
                    text=_section_kind_copy(m.element_id, self._merged) or "RAM preview",
                )

            self._ensure_preview_structure(preview_key)
            self._update_preview_content(preview_key, m)

            if stale_refresh and previous_key:
                if previous_key != preview_key:
                    self._show_preview_frame(preview_key)
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )
                else:
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )
            else:
                self._clear_preview_shell_bootstrap_once()
                self._hide_preview_frames()
                self._show_preview_frame(preview_key)
                if previous_key and previous_key != preview_key:
                    self._log_editor_content_swapped(
                        m,
                        region="preview",
                        preview_key=preview_key,
                    )

            log_event(
                "studio.gicleeframe.preview.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(canvas.winfo_children()),
                active_key=preview_key,
                cached_frames=len(self._preview_frame_cache),
                widget_count=len(self._preview_value_widgets.get(preview_key, {})),
            )
            log_event(
                "studio.gicleeframe.section_preview",
                element_type=m.element_type,
                children_before_destroy=before_children,
            )
    def _fill_children_overview_buttons(
        self,
        m: MergedPageElement,
        *,
        stale_refresh: bool = False,
    ) -> None:
        parent_row = self._tree_row_for_element(m.element_id)
        total = len(parent_row.children) if parent_row is not None else 0
        if total == 0:
            if self._children_overview_buttons is None:
                return
            if m.element_type != "media_section":
                log_event(
                    "studio.gicleeframe.children_overview",
                    element_type=m.element_type,
                    children_count=0,
                )
                return
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return
        self._fill_children_overview_buttons_range(
            m,
            0,
            total,
            stale_refresh=stale_refresh,
        )
    def _fill_children_overview_buttons_range(
        self,
        m: MergedPageElement,
        start: int,
        end: int,
        *,
        stale_refresh: bool = False,
    ) -> None:
        if self._children_overview_buttons is None:
            return

        if m.element_type != "media_section":
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return

        parent_row = self._tree_row_for_element(m.element_id)
        if parent_row is None:
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=0,
            )
            return

        children = parent_row.children
        if start == 0:
            if stale_refresh:
                for child in list(self._children_overview_buttons.winfo_children()):
                    try:
                        child.destroy()
                    except tk.TclError:
                        continue
            else:
                for child in self._children_overview_buttons.winfo_children():
                    child.destroy()

        grid: ctk.CTkFrame | None = None
        for child_widget in self._children_overview_buttons.winfo_children():
            if isinstance(child_widget, ctk.CTkFrame):
                grid = child_widget
                break
        if grid is None:
            grid = ctk.CTkFrame(self._children_overview_buttons, fg_color="transparent")
            grid.pack(fill="x")

        for idx in range(start, min(end, len(children))):
            child = children[idx]
            grid.grid_columnconfigure(idx, weight=1)

            tile = _make_gf_card(grid, variant="field", radius=12, bordered=True)
            tile.grid(row=0, column=idx, sticky="ew", padx=(0 if idx == 0 else 6, 0), pady=(0, 2))

            ctk.CTkLabel(
                tile,
                text=editor_title_for_element(child.merged).replace("Edytor: ", "").upper(),
                font=theme.get_font(8, "bold"),
                text_color=_GF_GOLD_SOFT,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(10, 2))

            ctk.CTkLabel(
                tile,
                text=_ellipsize(child.child_label, 26),
                font=theme.get_font(11, "bold"),
                text_color=theme.TextPrimary,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 8))

            ctk.CTkLabel(
                tile,
                text="Kliknij, aby edytować",
                font=theme.get_font(9),
                text_color=_GF_MUTED,
                anchor="w",
            ).pack(fill="x", padx=12, pady=(0, 10))

            for target in (tile,):
                target.bind(
                    "<Button-1>",
                    lambda _e, mid=child.element_id: self._select_element(mid),
                )

            for nested in tile.winfo_children():
                nested.bind(
                    "<Button-1>",
                    lambda _e, mid=child.element_id: self._select_element(mid),
                )

        if end >= len(children):
            log_event(
                "studio.gicleeframe.children_overview",
                element_type=m.element_type,
                children_count=len(children),
            )
            if stale_refresh:
                self._log_editor_content_swapped(m, region="children")
