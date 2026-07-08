"""Kadrowanie pionowe (object-position Y) dla pól grafiki w edytorze stron."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import ttk

from .types import PathKey

OBJECT_Y_DEFAULT = 50
OBJECT_Y_MIN = 0
OBJECT_Y_MAX = 100

__all__ = [
    "OBJECT_Y_DEFAULT",
    "OBJECT_Y_MAX",
    "OBJECT_Y_MIN",
    "build_object_y_controls",
    "normalize_object_y",
    "object_y_css",
    "object_y_field_id",
    "object_y_path",
    "object_y_setting_key",
]


def object_y_field_id(image_field_id: str) -> str:
    return f"{image_field_id}__object_y"


def object_y_setting_key(image_setting_key: str) -> str:
    return f"{image_setting_key}_object_y"


def object_y_path(image_path: PathKey | None) -> PathKey | None:
    if not image_path:
        return None
    *parent, key = image_path
    return (*parent, object_y_setting_key(key))


def normalize_object_y(value: Any) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return OBJECT_Y_DEFAULT
    return max(OBJECT_Y_MIN, min(OBJECT_Y_MAX, n))


def object_y_css(value: Any) -> str:
    return f"center {normalize_object_y(value)}%"


def build_object_y_controls(
    parent: tk.Widget,
    *,
    initial: Any,
    on_change: Callable[[int], None],
) -> tk.IntVar:
    """Suwak + skróty Góra / Środek / Dół pod polem grafiki."""
    row = ttk.Frame(parent)
    row.pack(fill="x", pady=(4, 0))

    ttk.Label(row, text="Kadrowanie góra–dół:", width=18).pack(side="left", anchor="n")

    controls = ttk.Frame(row)
    controls.pack(side="left", fill="x", expand=True)

    var = tk.IntVar(value=normalize_object_y(initial))
    label_var = tk.StringVar(value=_object_y_label(var.get()))

    scale_row = ttk.Frame(controls)
    scale_row.pack(fill="x")
    ttk.Label(scale_row, text="Góra", foreground="#777", font=("", 8)).pack(side="left")
    scale = ttk.Scale(
        scale_row,
        from_=OBJECT_Y_MIN,
        to=OBJECT_Y_MAX,
        orient="horizontal",
        variable=var,
    )
    scale.pack(side="left", fill="x", expand=True, padx=6)
    ttk.Label(scale_row, text="Dół", foreground="#777", font=("", 8)).pack(side="left")
    ttk.Label(scale_row, textvariable=label_var, width=8).pack(side="left", padx=(4, 0))

    preset_row = ttk.Frame(controls)
    preset_row.pack(anchor="w", pady=(4, 0))

    def _apply_preset(value: int) -> None:
        var.set(normalize_object_y(value))
        _emit()

    def _emit(*_args: object) -> None:
        value = normalize_object_y(var.get())
        label_var.set(_object_y_label(value))
        on_change(value)

    for text, value in (("Góra", 0), ("Środek", 50), ("Dół", 100)):
        ttk.Button(preset_row, text=text, width=8, command=lambda v=value: _apply_preset(v)).pack(
            side="left", padx=(0, 4)
        )

    var.trace_add("write", _emit)
    _emit()
    return var


def _object_y_label(value: int) -> str:
    value = normalize_object_y(value)
    if value <= 12:
        return "góra"
    if value >= 88:
        return "dół"
    if 45 <= value <= 55:
        return "środek"
    return f"{value}%"
