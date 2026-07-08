"""Bezpieczna rejestracja drag-and-drop (tkinterdnd2) — fallback bez crasha w embed Studio."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from tkinterdnd2 import DND_FILES  # type: ignore

    _DND_IMPORTED = True
except ImportError:
    DND_FILES = None  # type: ignore[assignment,misc]
    _DND_IMPORTED = False


def dnd_files_available() -> bool:
    """Pakiet tkinterdnd2 zainstalowany — nie gwarantuje działania w zwykłym tk.Frame."""
    return _DND_IMPORTED


def parse_dnd_files(data: str) -> list[Path]:
    """Parsuje payload zdarzenia <<Drop>> tkdnd na listę ścieżek.

    Ścieżki ze spacjami są opakowane w {klamry}; wiele plików rozdziela spacja.
    """
    out: list[Path] = []
    buf = ""
    in_brace = False
    for ch in data:
        if ch == "{":
            in_brace = True
            buf = ""
        elif ch == "}":
            in_brace = False
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        elif ch == " " and not in_brace:
            if buf.strip():
                out.append(Path(buf.strip()))
            buf = ""
        else:
            buf += ch
    if buf.strip():
        out.append(Path(buf.strip()))
    return out


def register_drop_target(
    widget: Any,
    *,
    on_drop: Callable[..., Any],
    on_drag_enter: Callable[..., Any] | None = None,
    on_drag_leave: Callable[..., Any] | None = None,
) -> bool:
    """Rejestruje DND_FILES na widgecie; łapie TclError gdy tkdnd nie jest aktywne."""
    if not _DND_IMPORTED or DND_FILES is None:
        return False
    try:
        widget.drop_target_register(DND_FILES)
        widget.dnd_bind("<<Drop>>", on_drop)
        if on_drag_enter is not None:
            widget.dnd_bind("<<DragEnter>>", on_drag_enter)
        if on_drag_leave is not None:
            widget.dnd_bind("<<DragLeave>>", on_drag_leave)
    except Exception:
        return False
    return True


__all__ = [
    "DND_FILES",
    "dnd_files_available",
    "parse_dnd_files",
    "register_drop_target",
]
