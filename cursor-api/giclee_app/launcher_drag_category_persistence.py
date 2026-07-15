"""Persistence kolejności kategorii launchera po operacji drag-and-drop."""

from __future__ import annotations

from collections.abc import Sequence

from .launcher_layout import LauncherLayout, save_layout
from .launcher_tile_order import reorder_relative, replace_subset_order


def persist_category_reorder(
    layout: LauncherLayout,
    visible_titles: Sequence[str],
    source: str,
    target: str,
    *,
    after: bool,
) -> bool:
    """Mutuje i zapisuje pełną kolejność kategorii, jeżeli ruch coś zmienia."""

    visible = list(visible_titles)
    reordered = reorder_relative(visible, source, target, after=after)
    if reordered == visible:
        return False

    existing = layout.section_order or visible
    layout.section_order = replace_subset_order(existing, reordered)
    save_layout(layout)
    return True


__all__ = ["persist_category_reorder"]
