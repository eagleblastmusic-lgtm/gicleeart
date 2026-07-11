"""Poprawne jednostki pól liczbowych w panelu faz HOME FLOW."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import home_flow_phase_inline as inline


def install_inline_phase_units() -> None:
    current = inline._add_screens
    if getattr(current, "_giclee_units_fixed", False):
        return

    def add_numeric(
        parent: ttk.Frame,
        label: str,
        variable: tk.IntVar,
        *,
        minimum: int,
        maximum: int,
        hint: str = "",
    ) -> None:
        if "(%)" not in label:
            current(
                parent,
                label,
                variable,
                minimum=minimum,
                maximum=maximum,
                hint=hint,
            )
            return

        clean_label = label.replace(" (%)", "")
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text=clean_label + ":", width=30).pack(side="left", anchor="n")
        col = ttk.Frame(row)
        col.pack(side="left", fill="x", expand=True)
        top = ttk.Frame(col)
        top.pack(anchor="w")
        ttk.Spinbox(
            top,
            from_=minimum,
            to=maximum,
            textvariable=variable,
            width=7,
        ).pack(side="left")
        value_label = tk.StringVar()

        def refresh(*_args: object) -> None:
            try:
                value = max(minimum, min(maximum, int(variable.get())))
            except (tk.TclError, TypeError, ValueError):
                value = minimum
            value_label.set(f"{value}%")

        variable.trace_add("write", refresh)
        refresh()
        ttk.Label(top, textvariable=value_label, foreground="#666").pack(
            side="left", padx=(8, 0)
        )
        if hint:
            ttk.Label(col, text=hint, foreground="#777", wraplength=560).pack(
                anchor="w", pady=(3, 0)
            )

    setattr(add_numeric, "_giclee_units_fixed", True)
    setattr(add_numeric, "__wrapped__", current)
    inline._add_screens = add_numeric
