"""GICLÉE FRAME™ — page context and inline settings engine."""

from __future__ import annotations

import os
import time
import tkinter as tk
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    MergedPageElement,
    editor_context_rows,
    editor_field_visibility,
)
from giclee_app.studio.gicleeframe_page_settings import (
    PageSettingField,
    divider_setting_groups,
)
from giclee_app.studio.perf import log_event, span
from . import theme
from .gicleeframe_view_models import PageContextRowSpec
from .gicleeframe_view_primitives import (
    _GF_MUTED,
    _f2_entry_kwargs,
    _f2_menu_kwargs,
    _make_gf_card,
)

_F2_FIELD_LABEL_WIDTH = 88
_GF_PROGRESSIVE_PAGE_CONTEXT_ENV = "GICLEE_GF_PROGRESSIVE_PAGE_CONTEXT"
_GF_PAGE_CONTEXT_BATCH_SIZE = 8
_GF_PAGE_CONTEXT_BATCH_DELAY_MS = 0
_GF_PAGE_CONTEXT_DEFER_MS = 10
_GF_PAGE_CONTEXT_STABLE_DEFER_MS = 80
_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT = "Ustawienia sekcji są aktualizowane…"
_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE = 1
_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS = 0
_DIVIDER_LAZY_GROUPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "line": ("Linia", ("thickness", "width_percent", "alignment_horizontal")),
    "layout": ("Układ", ("section_width", "padding-block-start", "padding-block-end")),
    "style": ("Styl", ("color_scheme", "corner_radius")),
}

def _progressive_page_context_enabled() -> bool:
    raw = os.environ.get(_GF_PROGRESSIVE_PAGE_CONTEXT_ENV)
    if raw is None:
        return True
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


__all__ = (
    "GicleeFramePageContextMixin",
    "_F2_FIELD_LABEL_WIDTH",
    "_GF_PROGRESSIVE_PAGE_CONTEXT_ENV",
    "_GF_PAGE_CONTEXT_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_BATCH_DELAY_MS",
    "_GF_PAGE_CONTEXT_DEFER_MS",
    "_GF_PAGE_CONTEXT_STABLE_DEFER_MS",
    "_GF_PAGE_CONTEXT_SHELL_STATUS_TEXT",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE",
    "_GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS",
    "_DIVIDER_LAZY_GROUPS",
    "_progressive_page_context_enabled",
)



class GicleeFramePageContextMixin:
    """Page-context shell, caches, lazy groups and inline setting editors."""

    def _page_context_shell_summary_lines(
        self,
        m: MergedPageElement,
    ) -> list[tuple[str, str]]:
        etype = m.element_type or "unknown"
        lines: list[tuple[str, str]] = [
            ("Typ sekcji", etype),
            ("Status", m.status or "ok"),
        ]
        settings_count = len(m.page_settings)
        if settings_count:
            layout = "divider" if m.element_type == "divider" else "flat"
            lines.append(("Ustawienia", f"{settings_count} · układ {layout}"))
        return lines

    def _show_page_context_shell_state(self, m: MergedPageElement) -> None:
        if self._atomic_swap_suppress_visible:
            return
        if self._page_context_frame is None or self._page_context_inner is None:
            return
        self._hide_page_context_rows()
        self._clear_page_context_loading_label()
        self._page_context_frame.pack(**self._page_context_pack_kwargs())

        self._get_or_create_readonly_card()
        self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        for label, value in self._page_context_shell_summary_lines(m):
            row_key = f"shell_summary:{label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=label,
                kind="shell_summary",
            )
            value_widget.configure(text=value)
            self._show_page_context_row(row_key, fill="x", pady=2)

        if not self._selection_visual_cache_applied:
            pass
        else:
            self._clear_page_context_loading_label()
        self._page_context_shell_shown_generation = self._selection_generation
        log_event(
            "studio.gicleeframe.page_context.shell_ready",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _schedule_or_fill_page_context(
        self,
        m: MergedPageElement,
        fields: object,
        etype: str,
    ) -> None:
        readonly_rows = editor_context_rows(m) if fields.page_context else ()
        if (
            fields.page_context
            and _progressive_page_context_enabled()
            and (readonly_rows or m.page_settings)
        ):
            if self._page_context_shell_shown_generation != self._selection_generation:
                self._show_page_context_shell_state(m)
            log_event(
                "studio.gicleeframe.page_context.deferred",
                element_id=m.element_id,
                element_type=etype,
            )
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_STABLE_DEFER_MS,
                lambda el=m, gen=self._selection_generation: self._populate_page_context_progressive_stable(
                    el, gen
                ),
            )
        elif fields.page_context:
            self._fill_page_context(m, show=True)
        else:
            self._fill_page_context(m, show=False)

    def _pack_field_vertical(
        self,
        parent: ctk.CTkFrame,
        label: str,
        widget: ctk.CTkBaseClass,
    ) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 12))
        ctk.CTkLabel(
            row,
            text=label.upper(),
            font=theme.get_font(8, "bold"),
            text_color=_GF_MUTED,
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        widget.pack(fill="x")

    def _pack_setting_field_row(
        self,
        parent: ctk.CTkFrame,
        field: object,
    ) -> None:
        from giclee_app.studio.gicleeframe_page_settings import PageSettingField

        if not isinstance(field, PageSettingField):
            return
        if field.control == "select" and field.options:
            menu = ctk.CTkOptionMenu(
                parent,
                values=list(field.options),
                height=30,
                **_f2_menu_kwargs(),
            )
            menu.set(field.value if field.value in field.options else field.options[0])
            self._page_setting_widgets[field.key] = menu
            self._pack_field_vertical(parent, field.label, menu)
        else:
            entry = ctk.CTkEntry(
                parent,
                **_f2_entry_kwargs(),
            )
            entry.insert(0, field.value)
            self._page_setting_widgets[field.key] = entry
            self._pack_field_vertical(parent, field.label, entry)

    def _hide_page_context_rows(self) -> None:
        for key, frame in self._page_context_row_cache.items():
            manager = self._page_context_row_managers.get(key, "pack")
            try:
                if manager == "grid":
                    frame.grid_remove()
                else:
                    frame.pack_forget()
            except tk.TclError:
                continue
        self._page_context_visible_keys.clear()

    def _show_page_context_row(self, key: str, **pack_kwargs: object) -> None:
        if key in self._page_context_visible_keys:
            return
        frame = self._page_context_row_cache.get(key)
        if frame is None:
            return
        manager = self._page_context_row_managers.get(key, "pack")
        try:
            if manager == "grid":
                grid_opts = self._page_context_divider_group_grid_opts.get(key, {})
                frame.grid(**grid_opts)
            else:
                frame.pack(**pack_kwargs)
            self._page_context_visible_keys.add(key)
        except tk.TclError:
            return

    def _get_or_create_readonly_card(self) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = "container:readonly"
        if self._page_context_readonly_body is not None:
            return self._page_context_readonly_body
        info_card, info_body = self._build_setting_group_card(
            self._page_context_inner,
            "Kontekst sekcji",
        )
        self._page_context_row_cache[key] = info_card
        self._page_context_row_managers[key] = "pack"
        self._page_context_readonly_body = info_body
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="readonly_card",
        )
        return info_body

    def _get_or_create_page_context_row(
        self,
        key: str,
        *,
        label: str,
        kind: str = "readonly",
    ) -> tuple[ctk.CTkFrame, ctk.CTkLabel]:
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            value_widget = self._page_context_value_widgets.get(key)
            if isinstance(value_widget, ctk.CTkLabel):
                return cached, value_widget

        self._get_or_create_readonly_card()
        row = ctk.CTkFrame(self._page_context_readonly_body, fg_color="transparent")
        ctk.CTkLabel(
            row,
            text=f"{label}:",
            width=_F2_FIELD_LABEL_WIDTH,
            anchor="nw",
            font=theme.get_font(9),
            text_color=theme.TextMuted,
        ).pack(side="left")
        value_widget = ctk.CTkLabel(
            row,
            text="",
            anchor="nw",
            justify="left",
            wraplength=280,
            font=theme.get_font(10),
            text_color=theme.TextPrimary,
        )
        value_widget.pack(side="left", fill="x", expand=True)
        self._page_context_row_cache[key] = row
        self._page_context_value_widgets[key] = value_widget
        self._page_context_row_managers[key] = "pack"
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind=kind,
        )
        return row, value_widget

    def _get_or_create_divider_grid(self) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = "container:divider_grid"
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            return cached
        grid = ctk.CTkFrame(self._page_context_inner, fg_color="transparent")
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        self._page_context_row_cache[key] = grid
        self._page_context_row_managers[key] = "pack"
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="divider_grid",
        )
        return grid

    def _get_or_create_divider_group(self, group_title: str, slot: int) -> ctk.CTkFrame:
        key = f"divider_group:{group_title}"
        cached_body = self._page_context_divider_group_bodies.get(key)
        if cached_body is not None:
            return cached_body
        grid = self._get_or_create_divider_grid()
        card, body = self._build_setting_group_card(grid, group_title)
        row_idx, col_idx = divmod(slot, 2)
        grid_opts: dict[str, object] = {
            "row": row_idx,
            "column": col_idx,
            "sticky": "nsew",
            "padx": (0 if col_idx == 0 else 6, 6 if col_idx == 0 else 0),
            "pady": 6,
        }
        card.grid(**grid_opts)
        self._page_context_row_cache[key] = card
        self._page_context_row_managers[key] = "grid"
        self._page_context_divider_group_bodies[key] = body
        self._page_context_divider_group_grid_opts[key] = grid_opts
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="divider_group",
        )
        return body

    def _update_setting_widget(
        self,
        widget: ctk.CTkBaseClass,
        field: PageSettingField,
    ) -> None:
        if isinstance(widget, ctk.CTkOptionMenu):
            options = list(field.options)
            widget.configure(values=options)
            value = (
                field.value
                if field.value in field.options
                else (field.options[0] if field.options else "")
            )
            widget.set(value)
        elif isinstance(widget, ctk.CTkEntry):
            widget.delete(0, "end")
            widget.insert(0, field.value)

    def _create_page_setting_widget(
        self,
        parent: ctk.CTkFrame,
        field: PageSettingField,
    ) -> ctk.CTkBaseClass:
        key = f"setting:{field.key}"
        cached = self._page_context_value_widgets.get(key)
        if cached is not None:
            self._update_setting_widget(cached, field)
            self._page_setting_widgets[field.key] = cached
            return cached

        if field.control == "select" and field.options:
            menu = ctk.CTkOptionMenu(
                parent,
                values=list(field.options),
                height=30,
                **_f2_menu_kwargs(),
            )
            menu.set(field.value if field.value in field.options else field.options[0])
            widget: ctk.CTkBaseClass = menu
        else:
            entry = ctk.CTkEntry(
                parent,
                **_f2_entry_kwargs(),
            )
            entry.insert(0, field.value)
            widget = entry

        self._page_context_value_widgets[key] = widget
        self._page_setting_widgets[field.key] = widget
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="setting",
        )
        return widget

    def _get_or_create_page_setting_row(
        self,
        parent: ctk.CTkFrame,
        field: PageSettingField,
    ) -> ctk.CTkBaseClass:
        key = f"setting:{field.key}"
        cached = self._page_context_value_widgets.get(key)
        if cached is not None:
            self._update_setting_widget(cached, field)
            self._page_setting_widgets[field.key] = cached
            return cached

        widget = self._create_page_setting_widget(parent, field)
        self._pack_field_vertical(parent, field.label, widget)
        return widget

    def _get_or_create_setting_card(self, field: PageSettingField) -> ctk.CTkFrame:
        if self._page_context_inner is None:
            raise RuntimeError("page_context_inner is not initialized")
        key = f"setting_card:{field.key}"
        cached_body = self._page_context_setting_card_bodies.get(field.key)
        if cached_body is not None:
            self._get_or_create_page_setting_row(cached_body, field)
            return cached_body
        card, body = self._build_setting_group_card(
            self._page_context_inner,
            field.label,
        )
        self._page_context_row_cache[key] = card
        self._page_context_row_managers[key] = "pack"
        self._page_context_setting_card_bodies[field.key] = body
        self._get_or_create_page_setting_row(body, field)
        log_event(
            "studio.gicleeframe.page_context.row_created",
            key=key,
            kind="setting_card",
        )
        return body

    def _reset_page_context_settings_on_layout_change(self, new_layout: str) -> None:
        keys_to_remove = [
            key
            for key in list(self._page_context_row_cache)
            if key == "container:divider_grid"
            or key.startswith("divider_group:")
            or key.startswith("collapsed_group:")
            or key.startswith("setting_summary:")
            or key.startswith("setting_card:")
        ]
        for key in keys_to_remove:
            frame = self._page_context_row_cache.pop(key, None)
            if frame is not None:
                try:
                    frame.destroy()
                except tk.TclError:
                    pass
            self._page_context_row_managers.pop(key, None)
            self._page_context_visible_keys.discard(key)
            self._page_context_divider_group_grid_opts.pop(key, None)

        for key in list(self._page_context_value_widgets):
            if key.startswith("setting:"):
                del self._page_context_value_widgets[key]

        self._page_context_divider_group_bodies.clear()
        self._page_context_setting_card_bodies.clear()
        self._page_context_collapsed_group_rows.clear()
        self._page_context_collapsed_group_bodies.clear()
        self._page_context_collapsed_group_buttons.clear()
        self._page_context_expanded_group_ids.clear()
        self._page_context_summary_rows.clear()
        self._page_context_summary_value_labels.clear()
        self._page_setting_widgets.clear()
        self._close_active_setting_editor()
        log_event(
            "studio.gicleeframe.page_context.destroy_fallback",
            reason="settings_layout_change",
            new_layout=new_layout,
        )

    def _edit_panel_pack_anchor(self) -> ctk.CTkBaseClass | None:
        """First visible form row in the edit panel (for inventory block placement)."""
        if self._edit_panel is None:
            return None
        for child in self._edit_panel.winfo_children():
            if child is self._page_context_frame:
                continue
            if isinstance(child, ctk.CTkButton):
                continue
            if child.winfo_manager() == "pack":
                return child
        return None

    def _cancel_page_context_jobs(self) -> int:
        cancelled = len(self._page_context_after_ids)
        while self._page_context_after_ids:
            after_id = self._page_context_after_ids.pop()
            try:
                self.after_cancel(after_id)
            except tk.TclError:
                pass
        return cancelled

    def _schedule_page_context_job(self, delay_ms: int, callback: Callable[[], None]) -> None:
        after_id = self.after(delay_ms, callback)
        self._page_context_after_ids.append(after_id)

    def _page_context_pack_kwargs(self) -> dict[str, object]:
        pack_kwargs: dict[str, object] = {"fill": "x", "pady": (0, 8)}
        preferred_anchor = self._notes_row or self._image_ref_row or self._edit_panel_pack_anchor()
        if preferred_anchor is not None and preferred_anchor.winfo_manager() == "pack":
            pack_kwargs["before"] = preferred_anchor
        else:
            anchor = self._edit_panel_pack_anchor()
            if anchor is not None:
                pack_kwargs["before"] = anchor
        return pack_kwargs

    def _clear_page_context_loading_label(self) -> None:
        if self._page_context_loading_label is None:
            return
        try:
            self._page_context_loading_label.destroy()
        except tk.TclError:
            pass
        self._page_context_loading_label = None

    def _show_page_context_loading_state(self, m: MergedPageElement) -> None:
        """Backward-compatible alias — shell summary replaces heavy loading placeholder."""
        self._show_page_context_shell_state(m)
        log_event(
            "studio.gicleeframe.page_context.loading_state",
            element_id=m.element_id,
            element_type=m.element_type,
        )
        log_event(
            "studio.gicleeframe.selection.page_context.loading_state",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=self._selection_generation,
            since_click_ms=self._since_selection_click_ms(),
        )

    def _page_context_row_specs(
        self,
        m: MergedPageElement,
        *,
        show: bool = True,
    ) -> list[PageContextRowSpec]:
        if not show:
            return []
        readonly_rows = editor_context_rows(m)
        if not readonly_rows and not m.page_settings:
            return []

        specs: list[PageContextRowSpec] = []
        if readonly_rows:
            specs.append(PageContextRowSpec(kind="readonly_card"))
            for ro_label, ro_value in readonly_rows:
                specs.append(
                    PageContextRowSpec(
                        kind="readonly_row",
                        label=ro_label,
                        value=ro_value or "—",
                    )
                )

        new_layout = ""
        if m.page_settings:
            new_layout = "divider" if m.element_type == "divider" else "flat"

        fields_by_key = {field.key: field for field in m.page_settings}
        if new_layout == "divider" and fields_by_key:
            for group_id, (group_title, setting_keys) in _DIVIDER_LAZY_GROUPS.items():
                present = tuple(key for key in setting_keys if key in fields_by_key)
                if not present:
                    continue
                specs.append(
                    PageContextRowSpec(
                        kind="collapsed_group",
                        key=f"collapsed_group:{group_id}",
                        group_id=group_id,
                        group_title=group_title,
                        group_settings=present,
                    )
                )
        elif new_layout == "flat":
            for field in m.page_settings:
                specs.append(PageContextRowSpec(kind="setting_card", field=field))

        return specs

    def _reset_page_context_lazy_group_visual_state(
        self,
        m: MergedPageElement | None = None,
    ) -> None:
        self._page_context_expanded_group_ids.clear()
        specs_by_group: dict[str, PageContextRowSpec] = {}
        if m is not None:
            specs = self._page_context_specs_cache.get(m.element_id)
            if specs is None:
                specs = self._page_context_row_specs(m, show=True)
            for spec in specs:
                if spec.kind == "collapsed_group":
                    specs_by_group[spec.group_id] = spec
        for _group_id, body in list(self._page_context_collapsed_group_bodies.items()):
            try:
                body.pack_forget()
            except tk.TclError:
                pass
        for group_id, btn in self._page_context_collapsed_group_buttons.items():
            spec = specs_by_group.get(group_id)
            if spec is None:
                continue
            title = spec.group_title or spec.label
            count = len(spec.group_settings)
            try:
                btn.configure(text=f"▸ {title} · {count} ustawienia")
            except tk.TclError:
                pass

    def _make_page_setting_spec(
        self,
        m: MergedPageElement,
        setting_id: str,
        *,
        group_id: str = "",
        group_title: str = "",
    ) -> PageContextRowSpec | None:
        fields_by_key = {field.key: field for field in m.page_settings}
        field = fields_by_key.get(setting_id)
        if field is None:
            return None
        return PageContextRowSpec(
            kind="page_setting",
            field=field,
            group_id=group_id,
            group_title=group_title,
            setting_id=setting_id,
            label=field.label,
        )

    def _format_page_setting_value(
        self,
        m: MergedPageElement,
        setting_id: str,
    ) -> str:
        for field in m.page_settings:
            if field.key == setting_id:
                return field.value if field.value not in (None, "") else "—"
        return "—"

    def _create_page_context_setting_summary_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if spec.field is None and not spec.setting_id:
            return

        setting_id = spec.setting_id or (spec.field.key if spec.field else "")
        if not setting_id:
            return

        parent = self._page_context_collapsed_group_bodies.get(spec.group_id)
        if parent is None:
            return

        label = spec.label or (spec.field.label if spec.field else setting_id)
        row_key = f"setting_summary:{m.element_id}:{setting_id}"
        value_text = self._format_page_setting_value(m, setting_id)

        cached = self._page_context_row_cache.get(row_key)
        if cached is not None:
            self._page_context_summary_rows[row_key] = cached
            value_label = self._page_context_summary_value_labels.get(row_key)
            if value_label is not None:
                try:
                    value_label.configure(text=f"{label}\n{value_text}")
                except tk.TclError:
                    pass
            try:
                cached.pack(fill="x", padx=10, pady=4)
            except tk.TclError:
                pass
            return

        row = _make_gf_card(parent, variant="soft", radius=8)
        row.grid_columnconfigure(0, weight=1)
        row.grid_columnconfigure(1, weight=0)

        text = ctk.CTkLabel(
            row,
            text=f"{label}\n{value_text}",
            justify="left",
            anchor="w",
            font=theme.get_font(11),
            text_color=theme.TextPrimary,
        )
        text.grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        btn = ctk.CTkButton(
            row,
            text="Edytuj",
            width=72,
            command=lambda e=m, s=spec, r=row: self._open_inline_setting_editor(e, s, r),
        )
        btn.grid(row=0, column=1, sticky="e", padx=10, pady=8)

        row.pack(fill="x", padx=10, pady=4)
        self._page_context_row_cache[row_key] = row
        self._page_context_summary_rows[row_key] = row
        self._page_context_summary_value_labels[row_key] = text
        log_event(
            "studio.gicleeframe.page_context.setting_summary_created",
            element_id=m.element_id,
            element_type=m.element_type,
            setting_id=setting_id,
        )

    def _close_active_setting_editor(self) -> None:
        if self._active_setting_editor_row is None:
            return

        setting_id = ""
        if self._active_setting_editor_key and ":" in self._active_setting_editor_key:
            setting_id = self._active_setting_editor_key.split(":", 1)[1]

        try:
            for child in self._active_setting_editor_row.winfo_children():
                if getattr(child, "_giclee_inline_setting_editor", False):
                    child.destroy()
        except tk.TclError:
            pass

        if setting_id:
            self._page_context_value_widgets.pop(f"setting:{setting_id}", None)
            self._page_setting_widgets.pop(setting_id, None)

        self._active_setting_editor_row = None
        self._active_setting_editor_key = None

    def _open_inline_setting_editor(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
        row: ctk.CTkFrame,
    ) -> None:
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.setting_editor_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                setting_id=spec.setting_id,
            )
            return

        setting_id = spec.setting_id or (spec.field.key if spec.field else "")
        self._close_active_setting_editor()

        editor_key = f"{m.element_id}:{setting_id}"
        self._active_setting_editor_key = editor_key
        self._active_setting_editor_row = row

        with span(
            "studio.gicleeframe.page_context.setting_editor.open",
            element_type=m.element_type,
            setting_id=setting_id,
        ):
            self._create_full_setting_editor_inside_row(m, spec, row)

        log_event(
            "studio.gicleeframe.page_context.setting_editor.opened",
            element_id=m.element_id,
            element_type=m.element_type,
            setting_id=setting_id,
        )

    def _create_full_setting_editor_inside_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
        row: ctk.CTkFrame,
    ) -> None:
        if spec.field is None:
            fields_by_key = {field.key: field for field in m.page_settings}
            field = fields_by_key.get(spec.setting_id)
            if field is None:
                return
        else:
            field = spec.field

        editor = ctk.CTkFrame(
            row,
            fg_color=theme.PanelBg,
            corner_radius=8,
            border_width=1,
            border_color=theme.BorderSubtle,
        )
        editor._giclee_inline_setting_editor = True  # type: ignore[attr-defined]
        editor.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        widget = self._create_page_setting_widget(editor, field)
        widget.pack(fill="x", padx=8, pady=8)

    def _create_page_context_collapsed_group_row(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if self._page_context_inner is None:
            return

        key = spec.key or f"collapsed_group:{spec.group_id}"
        cached = self._page_context_row_cache.get(key)
        if cached is not None:
            self._page_context_collapsed_group_rows[spec.group_id] = cached
            btn = self._page_context_collapsed_group_buttons.get(spec.group_id)
            if btn is not None:
                count = len(spec.group_settings)
                title = spec.group_title or spec.label
                try:
                    btn.configure(text=f"▸ {title} · {count} ustawienia")
                except tk.TclError:
                    pass
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is not None:
                try:
                    body.pack_forget()
                except tk.TclError:
                    pass
            self._show_page_context_row(key, fill="x", padx=8, pady=4)
            return

        title = spec.group_title or spec.label
        count = len(spec.group_settings)
        row = _make_gf_card(self._page_context_inner, variant="soft", radius=8)
        btn = ctk.CTkButton(
            row,
            text=f"▸ {title} · {count} ustawienia",
            anchor="w",
            fg_color="transparent",
            hover_color=theme.CardHover,
            text_color=theme.TextPrimary,
            font=theme.get_font(11, "bold"),
            command=lambda e=m, s=spec: self._expand_page_context_group(e, s),
        )
        btn.pack(fill="x", padx=8, pady=8)
        self._page_context_row_cache[key] = row
        self._page_context_row_managers[key] = "pack"
        self._page_context_collapsed_group_rows[spec.group_id] = row
        self._page_context_collapsed_group_buttons[spec.group_id] = btn
        self._show_page_context_row(key, fill="x", padx=8, pady=4)
        log_event(
            "studio.gicleeframe.page_context.group_placeholder_created",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=spec.group_id,
            group_title=title,
            settings_count=count,
        )

    def _expand_page_context_group(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.group_expand_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                group_id=spec.group_id,
            )
            return

        if spec.group_id in self._page_context_expanded_group_ids:
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is not None:
                try:
                    body.pack(fill="x", padx=8, pady=(0, 8))
                except tk.TclError:
                    pass
            return

        log_event(
            "studio.gicleeframe.page_context.group_expanded",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=spec.group_id,
            group_title=spec.group_title,
            settings_count=len(spec.group_settings),
        )

        btn = self._page_context_collapsed_group_buttons.get(spec.group_id)
        if btn is not None:
            try:
                btn.configure(text=f"▾ {spec.group_title}")
            except tk.TclError:
                pass

        row = self._page_context_collapsed_group_rows.get(spec.group_id)
        if row is None:
            return

        body = ctk.CTkFrame(row, fg_color="transparent")
        body.pack(fill="x", padx=8, pady=(0, 8))
        self._page_context_collapsed_group_bodies[spec.group_id] = body
        self._page_context_expanded_group_ids.add(spec.group_id)

        setting_specs: list[PageContextRowSpec] = []
        for setting_id in spec.group_settings:
            setting_spec = self._make_page_setting_spec(
                m,
                setting_id,
                group_id=spec.group_id,
                group_title=spec.group_title,
            )
            if setting_spec is not None:
                setting_specs.append(setting_spec)

        if setting_specs:
            self._populate_page_context_group_batch(m, spec.group_id, setting_specs, 0)

    def _populate_page_context_group_batch(
        self,
        m: MergedPageElement,
        group_id: str,
        specs: list[PageContextRowSpec],
        start: int,
    ) -> None:
        if self._defer_background_for_selection(
            job="page_context.group_batch",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_group_batch(m, group_id, specs, start),
        ):
            return
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.group_batch_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                group_id=group_id,
            )
            return

        started = time.perf_counter()
        end = min(start + _GF_PAGE_CONTEXT_GROUP_SETTING_BATCH_SIZE, len(specs))

        for idx in range(start, end):
            self._create_page_context_setting_summary_row(m, specs[idx])

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.page_context.group_summary_batch",
            element_id=m.element_id,
            element_type=m.element_type,
            group_id=group_id,
            start=start,
            end=end,
            created=end - start,
            total_rows=len(specs),
            elapsed_ms=elapsed_ms,
        )

        if end < len(specs):
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_GROUP_SETTING_DELAY_MS,
                lambda e=m, g=group_id, s=specs, n=end: self._populate_page_context_group_batch(
                    e, g, s, n
                ),
            )

    def _precompute_page_context_specs_cache(self) -> None:
        if not _progressive_page_context_enabled():
            return
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        cached_count = 0
        for m in self._merged:
            fields = editor_field_visibility(m.element_type)
            if not fields.page_context:
                continue
            readonly_rows = editor_context_rows(m)
            if not readonly_rows and not m.page_settings:
                continue
            self._page_context_specs_cache[m.element_id] = self._page_context_row_specs(
                m,
                show=True,
            )
            cached_count += 1
        log_event(
            "studio.gicleeframe.page_context.specs_cache_ready",
            cached_count=cached_count,
            merged_count=len(self._merged),
        )

    def _create_page_context_row_from_spec(
        self,
        m: MergedPageElement,
        spec: PageContextRowSpec,
    ) -> None:
        if spec.kind == "readonly_card":
            self._get_or_create_readonly_card()
            self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
        elif spec.kind == "readonly_row":
            row_key = f"readonly:{spec.label}"
            _, value_widget = self._get_or_create_page_context_row(
                row_key,
                label=spec.label,
                kind="readonly",
            )
            value_widget.configure(text=spec.value or "—")
            self._show_page_context_row(row_key, fill="x", pady=2)
        elif spec.kind == "divider_grid":
            self._get_or_create_divider_grid()
            self._show_page_context_row("container:divider_grid", fill="x")
        elif spec.kind == "divider_group":
            self._get_or_create_divider_group(spec.group_title, spec.slot)
            self._show_page_context_row(f"divider_group:{spec.group_title}")
        elif spec.kind == "collapsed_group":
            self._create_page_context_collapsed_group_row(m, spec)
        elif spec.kind == "page_setting" and spec.field is not None:
            body = self._page_context_collapsed_group_bodies.get(spec.group_id)
            if body is None and spec.group_title:
                body = self._page_context_divider_group_bodies.get(
                    f"divider_group:{spec.group_title}",
                )
            if body is not None:
                self._get_or_create_page_setting_row(body, spec.field)
        elif spec.kind == "setting_card" and spec.field is not None:
            self._get_or_create_setting_card(spec.field)
            self._show_page_context_row(
                f"setting_card:{spec.field.key}",
                fill="x",
                pady=(0, 8),
            )

    def _populate_page_context_batch(
        self,
        m: MergedPageElement,
        specs: list[PageContextRowSpec],
        start: int,
    ) -> None:
        if self._defer_background_for_selection(
            job="page_context.batch",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_batch(m, specs, start),
        ):
            return
        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.batch_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
            )
            return

        started = time.perf_counter()
        end = min(start + _GF_PAGE_CONTEXT_BATCH_SIZE, len(specs))

        for idx in range(start, end):
            self._create_page_context_row_from_spec(m, specs[idx])

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            "studio.gicleeframe.page_context.batch",
            element_id=m.element_id,
            element_type=m.element_type,
            start=start,
            end=end,
            batch_index=start,
            created=end - start,
            total_rows=len(specs),
            total=len(specs),
            elapsed_ms=elapsed_ms,
            since_click_ms=self._since_selection_click_ms(),
        )

        if end < len(specs):
            self._schedule_page_context_job(
                _GF_PAGE_CONTEXT_BATCH_DELAY_MS,
                lambda el=m, s=specs, n=end: self._populate_page_context_batch(el, s, n),
            )
            return

        settings_count = len(m.page_settings)
        readonly_rows = editor_context_rows(m)
        before_children = (
            len(self._page_context_inner.winfo_children())
            if self._page_context_inner is not None
            else 0
        )
        log_event(
            "studio.gicleeframe.page_context.progressive_done",
            element_id=m.element_id,
            element_type=m.element_type,
            total_rows=len(specs),
        )
        log_event(
            "studio.gicleeframe.page_context.reuse",
            element_type=m.element_type,
            before_children=before_children,
            after_children=before_children,
            visible_rows=len(self._page_context_visible_keys),
            cached_rows=len(self._page_context_row_cache),
            settings_count=settings_count,
        )
        log_event(
            "studio.gicleeframe.page_context",
            element_type=m.element_type,
            show=True,
            page_settings_count=settings_count,
            readonly_rows_count=len(readonly_rows),
            children_before_destroy=before_children,
        )

    def _populate_page_context_progressive_stable(
        self,
        m: MergedPageElement,
        generation: int,
    ) -> None:
        if generation != self._selection_generation or self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.stable_defer_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
                generation=generation,
                current_generation=self._selection_generation,
            )
            log_event(
                "studio.gicleeframe.selection.page_context.stale",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                current_generation=self._selection_generation,
                selected_id=self._selected_id or "",
            )
            return

        log_event(
            "studio.gicleeframe.selection.page_context.populate_enter",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )
        log_event(
            "studio.gicleeframe.page_context.start",
            element_id=m.element_id,
            element_type=m.element_type,
            generation=generation,
            since_click_ms=self._since_selection_click_ms(),
        )
        page_context_started = time.perf_counter()
        self._populate_page_context_progressive(m)
        if generation == self._selection_generation and self._selected_id == m.element_id:
            page_context_elapsed_ms = round((time.perf_counter() - page_context_started) * 1000, 2)
            log_event(
                "studio.gicleeframe.selection.page_context.populate_done",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=page_context_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )
            log_event(
                "studio.gicleeframe.page_context.done",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=generation,
                elapsed_ms=page_context_elapsed_ms,
                since_click_ms=self._since_selection_click_ms(),
            )

    def _populate_page_context_progressive(self, m: MergedPageElement) -> None:
        try:
            if not self.winfo_exists():
                return
        except tk.TclError:
            return

        if self._defer_background_for_selection(
            job="page_context.progressive",
            reason="selection_priority_active",
            element_id=m.element_id,
            element_type=m.element_type,
            callback=lambda: self._populate_page_context_progressive(m),
        ):
            return

        if self._selected_id != m.element_id:
            log_event(
                "studio.gicleeframe.page_context.deferred_stale",
                element_id=m.element_id,
                selected_id=self._selected_id or "",
            )
            return

        if self._page_context_frame is None or self._page_context_inner is None:
            return

        with span(
            "studio.gicleeframe.populate.page_context.progressive_prepare",
            element_type=m.element_type,
            element_id=m.element_id,
        ):
            specs = self._page_context_specs_cache.get(m.element_id)
            if specs is None:
                specs = self._page_context_row_specs(m, show=True)

        self._clear_page_context_loading_label()
        before_children = len(self._page_context_inner.winfo_children())
        self._hide_page_context_rows()
        self._reset_page_context_lazy_group_visual_state(m)

        readonly_rows = editor_context_rows(m)
        if not readonly_rows and not m.page_settings:
            self._page_context_frame.pack_forget()
            return

        new_layout = ""
        if m.page_settings:
            new_layout = "divider" if m.element_type == "divider" else "flat"

        if (
            new_layout
            and new_layout != self._page_context_settings_layout
            and self._page_context_settings_layout in ("divider", "flat")
        ):
            self._reset_page_context_settings_on_layout_change(new_layout)
        if new_layout:
            self._page_context_settings_layout = new_layout

        self._page_context_frame.pack(**self._page_context_pack_kwargs())
        self._page_context_last_signature = (
            m.element_type,
            new_layout,
            tuple(field.key for field in m.page_settings),
        )

        if not specs:
            log_event(
                "studio.gicleeframe.page_context.progressive_done",
                element_id=m.element_id,
                element_type=m.element_type,
                total_rows=0,
            )
            return

        self._populate_page_context_batch(m, specs, 0)

    def _fill_page_context(self, m: MergedPageElement, *, show: bool) -> None:
        if self._page_context_frame is None or self._page_context_inner is None:
            return

        readonly_rows = editor_context_rows(m) if show else ()
        settings_count = len(m.page_settings) if show else 0
        page_context_started = time.perf_counter() if show else None
        if show and (readonly_rows or m.page_settings):
            log_event(
                "studio.gicleeframe.page_context.start",
                element_id=m.element_id,
                element_type=m.element_type,
                generation=self._selection_generation,
                since_click_ms=self._since_selection_click_ms(),
                immediate=True,
            )

        with span(
            "studio.gicleeframe.populate.page_context",
            element_type=m.element_type,
            show=bool(show and (readonly_rows or m.page_settings)),
            cached_rows=len(self._page_context_row_cache),
        ):
            before_children = len(self._page_context_inner.winfo_children())
            self._hide_page_context_rows()

            if not show:
                self._page_context_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.page_context.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._page_context_inner.winfo_children()),
                    visible_rows=0,
                    cached_rows=len(self._page_context_row_cache),
                    settings_count=0,
                )
                log_event(
                    "studio.gicleeframe.page_context",
                    element_type=m.element_type,
                    show=False,
                    page_settings_count=settings_count,
                    readonly_rows_count=0,
                    children_before_destroy=before_children,
                )
                return

            if not readonly_rows and not m.page_settings:
                self._page_context_frame.pack_forget()
                log_event(
                    "studio.gicleeframe.page_context.reuse",
                    element_type=m.element_type,
                    before_children=before_children,
                    after_children=len(self._page_context_inner.winfo_children()),
                    visible_rows=0,
                    cached_rows=len(self._page_context_row_cache),
                    settings_count=0,
                )
                log_event(
                    "studio.gicleeframe.page_context",
                    element_type=m.element_type,
                    show=True,
                    page_settings_count=settings_count,
                    readonly_rows_count=0,
                    children_before_destroy=before_children,
                )
                return

            pack_kwargs: dict = {"fill": "x", "pady": (0, 8)}

            preferred_anchor = self._notes_row or self._image_ref_row or self._edit_panel_pack_anchor()
            if preferred_anchor is not None and preferred_anchor.winfo_manager() == "pack":
                pack_kwargs["before"] = preferred_anchor
            else:
                anchor = self._edit_panel_pack_anchor()
                if anchor is not None:
                    pack_kwargs["before"] = anchor

            self._page_context_frame.pack(**pack_kwargs)

            if readonly_rows:
                self._get_or_create_readonly_card()
                self._show_page_context_row("container:readonly", fill="x", pady=(0, 8))
                for ro_label, ro_value in readonly_rows:
                    row_key = f"readonly:{ro_label}"
                    _, value_widget = self._get_or_create_page_context_row(
                        row_key,
                        label=ro_label,
                        kind="readonly",
                    )
                    value_widget.configure(text=ro_value or "—")
                    self._show_page_context_row(row_key, fill="x", pady=2)

            new_layout = ""
            if m.page_settings:
                new_layout = "divider" if m.element_type == "divider" else "flat"

            if (
                new_layout
                and new_layout != self._page_context_settings_layout
                and self._page_context_settings_layout in ("divider", "flat")
            ):
                self._reset_page_context_settings_on_layout_change(new_layout)
            if new_layout:
                self._page_context_settings_layout = new_layout

            fields_by_key = {field.key: field for field in m.page_settings}
            if new_layout == "divider" and fields_by_key:
                self._get_or_create_divider_grid()
                self._show_page_context_row("container:divider_grid", fill="x")
                slot = 0
                for group_title, keys in divider_setting_groups():
                    group_fields = [
                        fields_by_key[key] for key in keys if key in fields_by_key
                    ]
                    if not group_fields:
                        continue
                    body = self._get_or_create_divider_group(group_title, slot)
                    self._show_page_context_row(f"divider_group:{group_title}")
                    for field in group_fields:
                        self._get_or_create_page_setting_row(body, field)
                    slot += 1
            elif new_layout == "flat":
                for field in m.page_settings:
                    self._get_or_create_setting_card(field)
                    self._show_page_context_row(
                        f"setting_card:{field.key}",
                        fill="x",
                        pady=(0, 8),
                    )

            self._page_context_last_signature = (
                m.element_type,
                new_layout,
                tuple(field.key for field in m.page_settings),
            )

            log_event(
                "studio.gicleeframe.page_context.reuse",
                element_type=m.element_type,
                before_children=before_children,
                after_children=len(self._page_context_inner.winfo_children()),
                visible_rows=len(self._page_context_visible_keys),
                cached_rows=len(self._page_context_row_cache),
                settings_count=settings_count,
            )
            log_event(
                "studio.gicleeframe.page_context",
                element_type=m.element_type,
                show=True,
                page_settings_count=settings_count,
                readonly_rows_count=len(readonly_rows),
                children_before_destroy=before_children,
            )
            if page_context_started is not None:
                page_context_elapsed_ms = round((time.perf_counter() - page_context_started) * 1000, 2)
                log_event(
                    "studio.gicleeframe.page_context.done",
                    element_id=m.element_id,
                    element_type=m.element_type,
                    generation=self._selection_generation,
                    elapsed_ms=page_context_elapsed_ms,
                    since_click_ms=self._since_selection_click_ms(),
                    immediate=True,
                )

