"""Dialog udziału procentowego mixu — szacunek sprzedaży na 100 szt."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .calculator import (
    FIXED_SALES_MIX_VARIANTS,
    apply_mix_shares,
    mix_share_weights,
    normalize_sales_mix,
    parse_mix_units,
    scale_units_to_total,
)
from .store import load_sales_mix, save_sales_mix


def _format_pct(weight: float) -> str:
    pct = weight * 100.0
    if abs(pct - round(pct)) < 0.05:
        return f"{pct:.0f} %"
    return f"{pct:.1f} %"


def open_mix_share_dialog(parent: tk.Misc, *, on_apply: Callable[[], None]) -> None:
    win = tk.Toplevel(parent)
    win.title("Udział w sprzedaży")
    win.geometry("480x420")
    win.minsize(420, 380)
    win.transient(parent)
    win.grab_set()

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(
        frame,
        text="Szacunkowa sprzedaż na 100 ramek",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        frame,
        text="Wpisz ile sztuk każdego wariantu przypada na 100 sprzedanych ramek "
        "(np. 22 = 22 % przy sumie 100). Suma nie musi wynosić 100 — procenty liczą się z proporcji.",
        foreground="#666",
        wraplength=440,
    ).pack(anchor="w", pady=(4, 10))

    grid = ttk.Frame(frame)
    grid.pack(fill="x")
    grid.columnconfigure(1, weight=1)

    ttk.Label(grid, text="Wariant", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 6))
    ttk.Label(grid, text="na 100 szt.", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(8, 0))
    ttk.Label(grid, text="Udział", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="e", padx=(12, 0))

    base = normalize_sales_mix(load_sales_mix())
    initial = scale_units_to_total(mix_share_weights(base), 100)

    share_vars: list[tk.StringVar] = []
    pct_vars: list[tk.StringVar] = []
    entries: list[ttk.Entry] = []

    for i, ((wood, fmt), value) in enumerate(zip(FIXED_SALES_MIX_VARIANTS, initial, strict=True), start=1):
        ttk.Label(grid, text=f"{wood} · {fmt}").grid(row=i, column=0, sticky="w", pady=3)
        var = tk.StringVar(value=str(value))
        share_vars.append(var)
        entry = ttk.Entry(grid, textvariable=var, width=8)
        entry.grid(row=i, column=1, sticky="w", padx=(8, 0), pady=3)
        entries.append(entry)
        pct_var = tk.StringVar(value="—")
        pct_vars.append(pct_var)
        ttk.Label(grid, textvariable=pct_var, width=8, anchor="e").grid(
            row=i, column=2, sticky="e", padx=(12, 0), pady=3
        )

    total_var = tk.StringVar(value="")
    ttk.Label(frame, textvariable=total_var, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))

    def refresh_preview(*_args: object) -> None:
        shares = [parse_mix_units(var.get()) or 0 for var in share_vars]
        total = sum(shares)
        total_var.set(f"Suma: {total} / 100")
        if total <= 0:
            for pct_var in pct_vars:
                pct_var.set("—")
            return
        for share, pct_var in zip(shares, pct_vars, strict=True):
            pct_var.set(_format_pct(share / total))

    def normalize_to_hundred() -> None:
        shares = [parse_mix_units(var.get()) or 0 for var in share_vars]
        if sum(shares) <= 0:
            messagebox.showwarning("Udział", "Podaj co najmniej jedną dodatnią wartość.", parent=win)
            return
        scaled = scale_units_to_total(shares, 100)
        for var, value in zip(share_vars, scaled, strict=True):
            var.set(str(value))
        refresh_preview()

    def apply() -> None:
        shares = [parse_mix_units(var.get()) or 0 for var in share_vars]
        if sum(shares) <= 0:
            messagebox.showerror("Udział", "Suma musi być większa od zera.", parent=win)
            return
        save_sales_mix(apply_mix_shares(base, shares))
        on_apply()
        win.destroy()

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(14, 0))
    ttk.Button(btn_row, text="Przeskaluj do sumy 100", command=normalize_to_hundred).pack(side="left")
    ttk.Button(btn_row, text="Anuluj", command=win.destroy).pack(side="right", padx=(6, 0))
    ttk.Button(btn_row, text="Zastosuj", command=apply).pack(side="right")

    for var in share_vars:
        var.trace_add("write", refresh_preview)
    refresh_preview()
    entries[0].focus_set()
    win.bind("<Return>", lambda _evt: apply())
