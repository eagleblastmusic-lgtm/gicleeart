"""Dialog celu finansowego — szacunek sprzedaży ramek do osiągnięcia zysku."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .calculator import (
    fmt_money,
    format_frame_count,
    frames_for_financial_goal,
    redistribute_mix_total,
    resolved_sales_mix,
)
from .store import load_sales_mix, load_settings, save_sales_mix


def _parse_money(raw: str) -> float | None:
    text = raw.strip().replace(" ", "").replace(",", ".")
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > 0 else None


def open_financial_goal_dialog(parent: tk.Misc, *, on_apply: Callable[[], None]) -> None:
    win = tk.Toplevel(parent)
    win.title("Cel finansowy")
    win.geometry("460x300")
    win.minsize(400, 260)
    win.transient(parent)
    win.grab_set()

    frame = ttk.Frame(win, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="Cel zysku ze sprzedaży", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(
        frame,
        text="Podaj kwotę zysku do osiągnięcia. Aplikacja policzy, ile ramek trzeba sprzedać "
        "przy średnim zysku ważonym mixem (ceny z Kalkulatora, udział z mixu).",
        foreground="#666",
        wraplength=420,
    ).pack(anchor="w", pady=(4, 12))

    row = ttk.Frame(frame)
    row.pack(fill="x")
    ttk.Label(row, text="Cel (zł):").pack(side="left")
    goal_var = tk.StringVar(value="")
    goal_entry = ttk.Entry(row, textvariable=goal_var, width=14)
    goal_entry.pack(side="left", padx=(8, 0))

    result_var = tk.StringVar(value="Wpisz kwotę celu.")
    detail_var = tk.StringVar(value="")
    ttk.Label(frame, textvariable=result_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(14, 4))
    ttk.Label(frame, textvariable=detail_var, foreground="#666", wraplength=420).pack(anchor="w")

    state: dict[str, object] = {"frames_needed": None}

    def refresh_preview(*_args: object) -> None:
        goal = _parse_money(goal_var.get())
        if goal is None:
            result_var.set("Wpisz dodatnią kwotę zysku.")
            detail_var.set("")
            state["frames_needed"] = None
            return
        est = frames_for_financial_goal(goal, settings=load_settings())
        avg_profit = float(est["avg_profit"] or 0)
        frames = est["frames_needed"]
        if frames is None or avg_profit <= 0:
            result_var.set("Nie można policzyć — brak zysku w mixie.")
            detail_var.set("Ustaw ceny w Kalkulatorze i udział w mixie.")
            state["frames_needed"] = None
            return
        state["frames_needed"] = int(frames)
        result_var.set(f"Potrzeba: {format_frame_count(int(frames))}")
        detail_var.set(
            f"Średni zysk na ramkę (mix): {fmt_money(avg_profit)} · "
            f"prognoza przy tym wolumenie: {fmt_money(float(est['projected_profit'] or 0))}"
        )

    def apply_to_mix() -> None:
        frames = state.get("frames_needed")
        if frames is None:
            messagebox.showwarning("Cel finansowy", "Najpierw podaj prawidłową kwotę celu.", parent=win)
            return
        rows = load_sales_mix()
        updated = redistribute_mix_total(rows, int(frames))
        save_sales_mix(updated)
        on_apply()
        win.destroy()

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill="x", pady=(18, 0))
    ttk.Button(btn_row, text="Ustaw w mixie", command=apply_to_mix).pack(side="left")
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack(side="right")

    goal_var.trace_add("write", refresh_preview)
    goal_entry.focus_set()
    win.bind("<Return>", lambda _evt: apply_to_mix())
