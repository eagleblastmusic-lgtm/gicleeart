"""GICLÉE FRAME™ — section list interaction, highlight and RAM reorder."""

from __future__ import annotations

import os
import time

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    merge_inventory_with_draft,
    reorder_page_blocks,
)
from giclee_app.studio.perf import log_event

from .gicleeframe_view_primitives import _GF_BORDER_WARM, _GF_CARD_SOFT
from .gicleeframe_view_section_list_shell import (
    _SECTION_LIST_WIDTH,
    _SECTION_PLACEHOLDER,
)

_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV = "GICLEE_GF_COLLAPSE_SECTION_LIST_ON_CLICK"


def _collapse_section_list_on_click_enabled() -> bool:
    raw = os.environ.get(_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on", "debug"}


__all__ = (
    "GicleeFrameSectionListInteractionMixin",
    "_GF_SECTION_ROW_COLLAPSE_ON_CLICK_ENV",
    "_collapse_section_list_on_click_enabled",
)


class GicleeFrameSectionListInteractionMixin:
    """Dropdown, row click, highlight and drag/reorder for the section list."""

    def _selected_section_label(self) -> str:
        if not self._merged:
            return _SECTION_PLACEHOLDER
        options = self._section_dropdown_options_cache
        target_id = self._top_level_row_id_for_selection() or self._selected_id
        if target_id:
            for opt in options:
                if opt.element_id == target_id:
                    return opt.display_label
        return options[0].display_label if options else _SECTION_PLACEHOLDER

    def _update_section_list_trigger(self) -> None:
        if self._section_list_trigger is None:
            return
        chevron = "▴" if self._section_list_expanded.get() else "▾"
        self._section_list_trigger.configure(text=f"{self._selected_section_label()}  {chevron}")

    def _collapse_section_list(self) -> None:
        self._section_list_expanded.set(False)
        if self._section_dropdown_popup is not None:
            self._section_dropdown_popup.place_forget()
        self._unbind_section_dropdown_outside_close()
        self._update_section_list_trigger()

    def _ensure_section_dropdown_rows(self) -> None:
        if self._section_row_ids and self._section_row_frames:
            self._highlight_section_row()
            log_event(
                "studio.gicleeframe.section_dropdown.rows_reused",
                row_count=len(self._section_row_ids),
            )
            return
        log_event("studio.gicleeframe.section_dropdown.rows_rebuilt")
        self._render_section_list()

    def _open_section_dropdown(self) -> None:
        if (
            self._section_dropdown_popup is None
            or self._section_list_trigger is None
            or self._section_list_column is None
        ):
            return
        self._section_list_expanded.set(True)
        self._ensure_section_dropdown_rows()
        trigger = self._section_list_trigger
        parent = self._section_list_column
        popup_width = max(trigger.winfo_width(), _SECTION_LIST_WIDTH)
        self._section_dropdown_popup.configure(width=popup_width)
        if self._section_list_scroll is not None:
            self._section_list_scroll.configure(width=max(popup_width - 12, 180))
        parent.update_idletasks()
        x = trigger.winfo_rootx() - parent.winfo_rootx()
        y = trigger.winfo_rooty() - parent.winfo_rooty() + trigger.winfo_height() + 2
        self._section_dropdown_popup.place(x=x, y=y)
        self._section_dropdown_popup.lift()
        self.after(80, self._bind_section_dropdown_outside_close)
        self._update_section_list_trigger()

    def _widget_in_section_dropdown(self, widget: ctk.CTkBaseClass | None) -> bool:
        popup = self._section_dropdown_popup
        trigger = self._section_list_trigger
        current: ctk.CTkBaseClass | None = widget
        while current is not None:
            if current is popup or current is trigger:
                return True
            current = current.master  # type: ignore[assignment]
        return False

    def _bind_section_dropdown_outside_close(self) -> None:
        if self._section_outside_close_active:
            return
        self._section_outside_close_active = True
        self.winfo_toplevel().bind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
            add="+",
        )

    def _unbind_section_dropdown_outside_close(self) -> None:
        if not self._section_outside_close_active:
            return
        self._section_outside_close_active = False
        self.winfo_toplevel().unbind(
            "<Button-1>",
            self._on_section_dropdown_outside_click,
        )

    def _on_section_dropdown_outside_click(self, event: object) -> None:
        if not self._section_list_expanded.get():
            return
        widget = getattr(event, "widget", None)
        if self._widget_in_section_dropdown(widget):
            return
        self._collapse_section_list()

    def _toggle_section_list(self) -> None:
        if self._section_list_expanded.get():
            self._collapse_section_list()
        else:
            self._open_section_dropdown()

    def _on_section_row_click(self, element_id: str) -> None:
        self._selection_click_mono = time.perf_counter()
        m_click = self._merged_by_id.get(element_id)
        log_event(
            "studio.gicleeframe.selection.click",
            element_id=element_id,
            element_type=m_click.element_type if m_click is not None else "",
            source="row",
            generation=self._selection_generation + 1,
            static_lane=bool(
                self._section_list_static_lane is not None
                and not self._section_list_scroll_upgrade_done
            ),
            scroll_ready=self._section_list_scroll_upgrade_done,
            selection_generation_next=self._selection_generation + 1,
            since_enter_ms=self._since_visual_enter_ms(),
            perceived_ready_logged=self._perceived_ready_logged,
            shell_control_built=self._shell_control_built,
        )
        self._select_element(
            element_id,
            collapse_list=_collapse_section_list_on_click_enabled(),
        )

    def _top_level_row_id_for_element(self, element_id: str | None) -> str | None:
        if element_id is None:
            return None
        selected = self._merged_by_id.get(element_id)
        if selected is None:
            return None
        if selected.element_type in ("jumbo", "body", "image"):
            for row in self._section_tree_rows_cache:
                if row.section_key == selected.section_key and row.row_kind == "media_section":
                    return row.element_id
            return None
        return element_id

    def _top_level_row_id_for_selection(self) -> str | None:
        return self._top_level_row_id_for_element(self._selected_id)

    def _set_section_row_highlight(self, element_id: str | None, active: bool) -> None:
        if not element_id:
            return
        frame = self._section_row_frames.get(element_id)
        if frame is None:
            return

        try:
            if active:
                frame.configure(
                    fg_color=_GF_CARD_SOFT,
                    border_width=1,
                    border_color=_GF_BORDER_WARM,
                    corner_radius=12,
                )
            else:
                frame.configure(
                    fg_color="transparent",
                    border_width=0,
                    corner_radius=12,
                )
        except Exception:
            return

    def _highlight_section_row(self, previous_id: str | None = None) -> None:
        target = self._top_level_row_id_for_selection()
        previous_target = self._top_level_row_id_for_element(previous_id)
        if previous_target and previous_target != target:
            self._set_section_row_highlight(previous_target, False)
        self._set_section_row_highlight(target, True)
        self._highlighted_section_id = target

    def _highlight_section_rows(self) -> None:
        """Full re-highlight after list rebuild — scans all visible rows."""
        target = self._top_level_row_id_for_selection()
        for element_id in self._section_row_ids:
            self._set_section_row_highlight(element_id, element_id == target)
        self._highlighted_section_id = target

    def _section_row_index_at_root_y(self, y_root: int) -> int | None:
        for index, element_id in enumerate(self._section_row_ids):
            frame = self._section_row_frames.get(element_id)
            if frame is None:
                continue
            top = frame.winfo_rooty()
            if top <= y_root < top + frame.winfo_height():
                return index
        return None

    def _start_section_drag(self, index: int) -> None:
        self._drag_from_index = index
        if 0 <= index < len(self._section_row_ids):
            frame = self._section_row_frames.get(self._section_row_ids[index])
            if frame is not None:
                frame.configure(fg_color=_GF_CARD_SOFT)

    def _finish_section_drag(self, event: object) -> None:
        from_index = self._drag_from_index
        self._drag_from_index = None
        for element_id in self._section_row_ids:
            frame = self._section_row_frames.get(element_id)
            if frame is not None:
                frame.configure(fg_color="transparent")
        y_root = getattr(event, "y_root", None)
        if from_index is None or y_root is None:
            self._highlight_section_rows()
            return
        to_index = self._section_row_index_at_root_y(int(y_root))
        if to_index is None or from_index == to_index:
            self._highlight_section_rows()
            return
        if not reorder_page_blocks(self._page_draft, self._merged, from_index, to_index):
            self._highlight_section_rows()
            return
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        selected = self._selected_id
        self._render_section_list()
        if selected:
            m = self._merged_by_id.get(selected)
            if m is not None:
                self._selected_id = selected
                self._populate_editor(m)
        if self._on_status:
            self._on_status("Kolejność zaktualizowana w RAM · nic nie zapisano")
