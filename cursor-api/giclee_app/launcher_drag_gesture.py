"""Czyste decyzje przejść gestu drag-and-drop launchera."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DragMotionKind(str, Enum):
    """Decyzja dla kolejnego eventu motion."""

    WAITING = "waiting"
    START = "start"
    CONTINUE = "continue"


class DragReleaseKind(str, Enum):
    """Decyzja kończąca click albo drag."""

    ACTIVATE = "activate"
    REORDER = "reorder"
    NOOP = "noop"


@dataclass(frozen=True)
class DragReleaseDecision:
    """Niemutowalny wynik release bez efektów ubocznych."""

    kind: DragReleaseKind
    drag_kind: str
    source_key: str
    target_key: str
    after: bool


def resolve_drag_motion(
    *,
    dragging: bool,
    threshold_reached: bool,
) -> DragMotionKind:
    """Rozstrzyga oczekiwanie, rozpoczęcie albo kontynuację drag."""

    if dragging:
        return DragMotionKind.CONTINUE
    if threshold_reached:
        return DragMotionKind.START
    return DragMotionKind.WAITING


def resolve_drag_release(
    *,
    dragging: bool,
    drag_kind: str,
    source_key: str,
    target_key: str,
    after: bool,
) -> DragReleaseDecision:
    """Rozstrzyga aktywację, reorder albo brak akcji po release."""

    if not dragging:
        kind = DragReleaseKind.ACTIVATE
    elif not target_key or target_key == source_key:
        kind = DragReleaseKind.NOOP
    elif drag_kind not in {"category", "component"}:
        kind = DragReleaseKind.NOOP
    else:
        kind = DragReleaseKind.REORDER
    return DragReleaseDecision(
        kind=kind,
        drag_kind=drag_kind,
        source_key=source_key,
        target_key=target_key,
        after=after,
    )


__all__ = [
    "DragMotionKind",
    "DragReleaseDecision",
    "DragReleaseKind",
    "resolve_drag_motion",
    "resolve_drag_release",
]
