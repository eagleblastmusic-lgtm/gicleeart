"""Persistence kolejności komponentów launchera po operacji drag-and-drop."""

from __future__ import annotations

from collections.abc import Sequence

from .launcher_layout import LauncherLayout, save_layout
from .launcher_tile_order import reorder_relative, replace_subset_order


def persist_component_reorder(
    layout: LauncherLayout,
    section: str,
    visible_order: Sequence[str],
    source: str,
    target: str,
    *,
    after: bool,
) -> bool:
    """Mutuje i zapisuje kolejność komponentów w sekcji, jeżeli ruch coś zmienia.

    Zwraca ``True``, gdy model został zmutowany i zapisany.
    Zwraca ``False``, gdy operacja jest no-op i zapis nie został wykonany.
    """

    visible = list(visible_order)
    reordered_visible = reorder_relative(visible, source, target, after=after)
    if reordered_visible == visible:
        return False

    all_in_section = [
        entry.folder
        for entry in sorted(
            (
                entry
                for entry in layout.entries.values()
                if entry.section == section
            ),
            key=lambda entry: (entry.sort_key, entry.folder.lower()),
        )
    ]
    full_order = replace_subset_order(all_in_section, reordered_visible)
    for index, folder in enumerate(full_order):
        entry = layout.entries.get(folder)
        if entry is not None:
            entry.sort_key = index * 10

    save_layout(layout)
    return True


__all__ = ["persist_component_reorder"]
