"""Odczytowa mechanika Tk do wyszukiwania celu drag-and-drop launchera."""

from __future__ import annotations

from collections.abc import Sequence

import tkinter as tk

from .launcher_drag_geometry import (
    DragPoint,
    DragRect,
    nearest_rect_index,
    point_inside,
)


def widget_drag_rect(widget: tk.Misc) -> DragRect | None:
    """Odczytuje prostokąt widgetu we współrzędnych ekranu."""

    try:
        return DragRect(
            left=widget.winfo_rootx(),
            top=widget.winfo_rooty(),
            width=widget.winfo_width(),
            height=widget.winfo_height(),
        )
    except tk.TclError:
        return None


def find_drop_target(
    root: tk.Misc,
    *,
    tiles_area: tk.Misc,
    tiles: Sequence[tk.Frame],
    drag_kind: str,
    point: DragPoint,
    exclude: tk.Frame,
) -> tk.Frame | None:
    """Znajduje kafelek docelowy pod wskaźnikiem lub najbliższy fallback."""

    source_rect = widget_drag_rect(exclude)
    if source_rect is not None and point_inside(source_rect, point):
        return None

    try:
        widget = root.winfo_containing(int(point.x), int(point.y))
    except tk.TclError:
        widget = None

    current: tk.Misc | None = widget
    while current is not None:
        if (
            current is not exclude
            and getattr(current, "_launcher_dnd_kind", None) == drag_kind
        ):
            return current if isinstance(current, tk.Frame) else None
        try:
            current = current.master
        except (AttributeError, tk.TclError):
            break

    area_rect = widget_drag_rect(tiles_area)
    if area_rect is None or not point_inside(area_rect, point):
        return None

    candidates: list[tk.Frame] = []
    candidate_rects: list[DragRect] = []
    for tile in tiles:
        if tile is exclude or getattr(tile, "_launcher_dnd_kind", None) != drag_kind:
            continue
        try:
            exists = bool(tile.winfo_exists())
        except tk.TclError:
            continue
        if not exists:
            continue
        rect = widget_drag_rect(tile)
        if rect is None:
            continue
        candidates.append(tile)
        candidate_rects.append(rect)

    index = nearest_rect_index(candidate_rects, point)
    return candidates[index] if index is not None else None


__all__ = [
    "find_drop_target",
    "widget_drag_rect",
]
