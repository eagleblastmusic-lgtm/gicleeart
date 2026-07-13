"""GICLÉE FRAME™ — RAM variant workflow (menu sync, switch, top-bar state, CRUD)."""

from __future__ import annotations

import customtkinter as ctk

from giclee_app.studio.gicleeframe_page_draft import (
    PAGE_SOURCE_FILE,
    RAM_ONLY_STATUS,
    RENAME_VARIANT_LABEL,
    merge_inventory_with_draft,
    working_variant_menu_label,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    variant_environment_tag,
)

__all__ = ("GicleeFrameRamVariantMixin",)


class GicleeFrameRamVariantMixin:
    """Working-variant menu, top-bar metadata sync and RAM-only variant operations."""

    def _sync_working_variant_menu(self) -> None:
        if self._working_variant_menu is None:
            return
        pairs = self._page_draft.variant_names()
        self._working_variant_map = {}
        labels: list[str] = []
        for vid, _name in pairs:
            variant = self._page_draft.variants[vid]
            label = working_variant_menu_label(variant)
            labels.append(label)
            self._working_variant_map[label] = vid
        if not labels:
            return
        menu_values = labels
        self._working_variant_menu.configure(values=menu_values)
        active_label = working_variant_menu_label(self._page_draft.active_variant())
        if active_label in labels:
            self._working_variant_menu.set(active_label)
        else:
            self._working_variant_menu.set(labels[0])

    def _on_working_variant_selected(self, label: str) -> None:
        vid = self._working_variant_map.get(label)
        if not vid:
            return
        self._page_draft.switch_variant(vid)
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        self._render_section_menu()
        if self._selected_id:
            m = self._merged_by_id.get(self._selected_id)
            if m is not None:
                self._populate_editor(m)
            else:
                self._selected_id = None
        if self._on_status:
            self._on_status(
                f"Wariant roboczy: {self._page_draft.draft_name} · {RAM_ONLY_STATUS}"
            )

    def _update_top_bar(self) -> None:
        inv = self._inventory
        source_variant = inv.variant_id if inv else "—"
        count = self._page_draft.draft_edit_count()
        if self._top_meta_label:
            if inv and inv.variant_id:
                source_env = variant_environment_tag(
                    inv.variant_id,
                    active_id=inv.variant_id,
                    live_id=inv.live_variant_id,
                )
                source_line = f"{source_variant} ({source_env}) · {PAGE_SOURCE_FILE}"
            else:
                source_line = f"{source_variant} · {PAGE_SOURCE_FILE}"
            self._top_meta_label.configure(text=source_line)
        self._sync_working_variant_menu()
        if self._change_count_label:
            self._change_count_label.configure(text=f"Zmiany: {count}")

    def _add_ram_variant(self) -> None:
        self._page_draft.add_variant()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Dodano wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _duplicate_ram_variant(self) -> None:
        self._page_draft.duplicate_active_variant()
        self._selected_id = None
        if self._inventory:
            self._set_merged(merge_inventory_with_draft(self._inventory, self._page_draft))
        self._update_top_bar()
        self._render_section_menu()
        if self._on_status:
            self._on_status(
                f"Zduplikowano wariant: {self._page_draft.draft_name} · nic nie zapisano"
            )

    def _rename_ram_variant(self) -> None:
        dialog = ctk.CTkInputDialog(
            text="Nowa nazwa wariantu roboczego (tylko pamięć):",
            title=RENAME_VARIANT_LABEL,
        )
        name = dialog.get_input()
        if name and name.strip():
            self._page_draft.rename_active_variant(name.strip())
            self._update_top_bar()
            if self._on_status:
                self._on_status(
                    f"Zmieniono nazwę wariantu: {self._page_draft.draft_name}"
                )

    def _clear_page_draft(self) -> None:
        self._page_draft.clear()
        self._selected_id = None
        if self._structure_dry_label:
            self._reset_structure_dry_run_display()
        self._refresh_inventory(warn_if_draft=False)
        if self._on_status:
            self._on_status(
                f"Wyczyszczono wariant RAM: {self._page_draft.draft_name} · nic nie zapisano"
            )
