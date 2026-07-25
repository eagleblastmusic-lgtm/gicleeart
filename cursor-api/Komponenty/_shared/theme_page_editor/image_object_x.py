"""Kadrowanie poziome (object-position X) — tła pytań/odpowiedzi FAQ."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import ttk

from .types import PathKey

# Domyślnie 72% — dotychczasowy stały kadr FAQ (obraz bliżej prawej).
# Zakres szerszy niż 0–100: ujemne = dalej w lewo, >100 = dalej w prawo.
# Shopify range: max 101 kroków → (-50…150)/2+1 = 101.
OBJECT_X_DEFAULT = 72
OBJECT_X_MIN = -50
OBJECT_X_MAX = 150
OBJECT_X_STEP = 2

_OBJECT_X_SETTING_KEYS = frozenset(
    {
        "heading_background_image",
        "answer_background_image",
    }
)

__all__ = [
    "OBJECT_X_DEFAULT",
    "OBJECT_X_MAX",
    "OBJECT_X_MIN",
    "OBJECT_X_STEP",
    "build_object_x_controls",
    "normalize_object_x",
    "object_x_field_id",
    "object_x_path",
    "object_x_setting_key",
    "supports_object_x",
]


def supports_object_x(image_setting_key: str | None) -> bool:
    return bool(image_setting_key) and image_setting_key in _OBJECT_X_SETTING_KEYS


def object_x_field_id(image_field_id: str) -> str:
    return f"{image_field_id}__object_x"


def object_x_setting_key(image_setting_key: str) -> str:
    return f"{image_setting_key}_object_x"


def object_x_path(image_path: PathKey | None) -> PathKey | None:
    if not image_path:
        return None
    *parent, key = image_path
    if not supports_object_x(key):
        return None
    return (*parent, object_x_setting_key(key))


def normalize_object_x(value: Any) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return OBJECT_X_DEFAULT
    n = max(OBJECT_X_MIN, min(OBJECT_X_MAX, n))
    # Dopasuj do kroku Shopify (2), żeby zapis = suwak w Theme Editor.
    n = OBJECT_X_MIN + int(round((n - OBJECT_X_MIN) / OBJECT_X_STEP)) * OBJECT_X_STEP
    return max(OBJECT_X_MIN, min(OBJECT_X_MAX, n))


def build_object_x_controls(
    parent: tk.Widget,
    *,
    initial: Any,
    on_change: Callable[[int], None],
) -> tk.IntVar:
    """Suwak + skróty Lewo / Środek / Prawo pod polem grafiki FAQ."""
    box = ttk.Frame(parent)
    box.pack(fill="x", pady=(2, 0))

    header = ttk.Frame(box)
    header.pack(fill="x")
    ttk.Label(header, text="Kadrowanie lewo–prawo", foreground="#555").pack(side="left")
    var = tk.IntVar(value=normalize_object_x(initial))
    label_var = tk.StringVar(value=_object_x_label(var.get()))
    ttk.Label(header, textvariable=label_var, foreground="#333", width=8).pack(side="right")

    scale_row = ttk.Frame(box)
    scale_row.pack(fill="x", pady=(2, 0))
    ttk.Label(scale_row, text="Lewo", foreground="#888", font=("", 8)).pack(side="left")
    scale = ttk.Scale(
        scale_row,
        from_=OBJECT_X_MIN,
        to=OBJECT_X_MAX,
        orient="horizontal",
        variable=var,
    )
    scale.pack(side="left", fill="x", expand=True, padx=8)
    ttk.Label(scale_row, text="Prawo", foreground="#888", font=("", 8)).pack(side="left")

    preset_row = ttk.Frame(box)
    preset_row.pack(anchor="w", pady=(4, 0))

    def _apply_preset(value: int) -> None:
        var.set(normalize_object_x(value))
        _emit()

    def _emit(*_args: object) -> None:
        value = normalize_object_x(var.get())
        label_var.set(_object_x_label(value))
        on_change(value)

    for text, value in (
        ("Lewo", OBJECT_X_MIN),
        ("Środek", 50),
        ("Prawo", OBJECT_X_MAX),
    ):
        ttk.Button(preset_row, text=text, width=8, command=lambda v=value: _apply_preset(v)).pack(
            side="left", padx=(0, 4)
        )

    var.trace_add("write", _emit)
    _emit()
    return var


def _object_x_label(value: int) -> str:
    value = normalize_object_x(value)
    if value <= OBJECT_X_MIN + 8:
        return "lewo"
    if value >= OBJECT_X_MAX - 8:
        return "prawo"
    if 45 <= value <= 55:
        return "środek"
    return f"{value}%"
