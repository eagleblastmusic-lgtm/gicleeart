"""Czyste obliczenia geometryczne dla drag-and-drop launchera."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class DragPoint:
    """Punkt we współrzędnych ekranu."""

    x: float
    y: float


@dataclass(frozen=True)
class DragRect:
    """Prostokąt widgetu bez zależności od Tk."""

    left: float
    top: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.left + self.width

    @property
    def bottom(self) -> float:
        return self.top + self.height

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2


def drag_threshold_reached(
    start: DragPoint,
    current: DragPoint,
    threshold: float,
) -> bool:
    """Zwraca True, gdy odległość osiągnęła lub przekroczyła próg."""

    if threshold < 0:
        raise ValueError("threshold must be non-negative")
    return math.hypot(current.x - start.x, current.y - start.y) >= threshold


def point_inside(rect: DragRect, point: DragPoint) -> bool:
    """Sprawdza półotwarty obszar: lewa/góra inside, prawa/dół outside."""

    return (
        rect.left <= point.x < rect.right
        and rect.top <= point.y < rect.bottom
    )


def drop_after(
    rect: DragRect,
    point: DragPoint,
    *,
    vertical_ratio: float,
) -> bool:
    """Rozstrzyga, czy upuszczenie ma nastąpić za celem."""

    if vertical_ratio < 0:
        raise ValueError("vertical_ratio must be non-negative")
    vertical_delta = point.y - rect.center_y
    height = max(1, rect.height)
    if abs(vertical_delta) > height * vertical_ratio:
        return vertical_delta > 0
    return point.x > rect.center_x


def nearest_rect_index(
    rects: Sequence[DragRect],
    point: DragPoint,
) -> int | None:
    """Zwraca indeks prostokąta najbliższego punktowi według środka."""

    if not rects:
        return None
    return min(
        range(len(rects)),
        key=lambda index: math.hypot(
            point.x - rects[index].center_x,
            point.y - rects[index].center_y,
        ),
    )


__all__ = [
    "DragPoint",
    "DragRect",
    "drag_threshold_reached",
    "drop_after",
    "nearest_rect_index",
    "point_inside",
]
