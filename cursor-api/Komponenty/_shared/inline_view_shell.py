"""Wspólny pasek powrotu dla komponentów inline w GicleeApp."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


def mount_inline_view(
    parent: tk.Widget,
    on_back: Callable[[], None],
    *,
    title: str,
    build_content: Callable[[tk.Widget], None],
) -> ttk.Frame:
    outer = ttk.Frame(parent)
    outer.pack(fill="both", expand=True)

    header = ttk.Frame(outer, padding=(12, 8, 12, 4))
    header.pack(fill="x")
    ttk.Button(header, text="← Powrót", command=on_back).pack(side="left")
    ttk.Label(header, text=title, font=("Segoe UI", 14, "bold")).pack(side="left", padx=(12, 0))

    body = ttk.Frame(outer)
    body.pack(fill="both", expand=True)
    build_content(body)
    return outer
