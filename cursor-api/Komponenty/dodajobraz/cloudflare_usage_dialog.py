"""Okno «Cloudflare» — limity R2 (magazyn, operacje A/B, egress)."""

from __future__ import annotations

import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk
from typing import Any

from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .r2_usage import (
    collect_r2_usage,
    enrich_snapshot_with_uploads,
    format_bytes,
    usage_percent,
    usage_status,
    _fmt_int,
)

APP_TITLE = "Dodaj obraz"


def _add_meter(
    parent: tk.Misc,
    row: int,
    *,
    title: str,
    used: int | None,
    quota: int,
    unit_hint: str,
) -> None:
    frame = ttk.Frame(parent)
    frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
    frame.columnconfigure(0, weight=1)

    head = ttk.Frame(frame)
    head.pack(fill="x")
    ttk.Label(head, text=title, font=("Segoe UI", 10, "bold")).pack(side="left")

    if used is None:
        ttk.Label(head, text="brak danych", foreground="#888").pack(side="right")
        ttk.Label(
            frame,
            text=(
                "Ustaw CLOUDFLARE_API_TOKEN w .env (Analytics / R2 Read), "
                "potem Odśwież."
            ),
            foreground="#666",
            wraplength=520,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
        return

    pct = usage_percent(used, quota)
    status, color = usage_status(pct)
    free = max(0, quota - used)
    ttk.Label(head, text=status, foreground=color).pack(side="right")

    bar = ttk.Progressbar(frame, maximum=100.0, value=pct, mode="determinate")
    bar.pack(fill="x", pady=(4, 2))

    detail = (
        f"{_fmt_int(used)} / {_fmt_int(quota)} {unit_hint} "
        f"({pct:.1f}%) · wolne {_fmt_int(free)}"
    )
    ttk.Label(frame, text=detail, foreground="#444").pack(anchor="w")


def open_cloudflare_usage_dialog(parent: tk.Misc) -> None:
    dlg = tk.Toplevel(parent)
    dlg.title("Cloudflare R2 — limity")
    position_toplevel_screen_center(dlg, 560, 520)
    dlg.minsize(480, 420)
    dlg.transient(parent)

    outer = ttk.Frame(dlg, padding=(14, 12, 14, 12))
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=1)

    status_var = tk.StringVar(value="Ładowanie danych z R2…")
    ttk.Label(
        outer,
        text="Limity planu Free (Cloudflare) — bieżący miesiąc",
        font=("Segoe UI", 11, "bold"),
    ).grid(row=0, column=0, sticky="w")
    ttk.Label(outer, textvariable=status_var, foreground="#555", wraplength=520).grid(
        row=1, column=0, sticky="w", pady=(4, 10)
    )

    body = ttk.Frame(outer)
    body.grid(row=2, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)
    outer.rowconfigure(2, weight=1)

    extra_var = tk.StringVar(value="")
    ttk.Label(
        outer,
        textvariable=extra_var,
        foreground="#444",
        wraplength=520,
        justify="left",
    ).grid(row=3, column=0, sticky="w", pady=(8, 0))

    note = ttk.Label(
        outer,
        text=(
            "Egress (transfer z R2 / r2.dev do internetu) — u Cloudflare bez limitu i bez opłat.\n"
            "Worker upload klienta: customer-uploads/ · Zoom reprodukcji: zoom/\n"
            "Szczegóły usług: USLUGI.md w korzeniu repo."
        ),
        foreground="#666",
        wraplength=520,
        justify="left",
    )
    note.grid(row=4, column=0, sticky="w", pady=(10, 0))

    btn_row = ttk.Frame(outer)
    btn_row.grid(row=5, column=0, sticky="e", pady=(12, 0))

    def render_error(msg: str) -> None:
        for w in body.winfo_children():
            w.destroy()
        status_var.set(f"Błąd: {msg}")
        extra_var.set("")

    def render_snap(snap: Any, extra: dict[str, Any]) -> None:
        for w in body.winfo_children():
            w.destroy()

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        status_var.set(f"Bucket: {snap.bucket} · źródło: {snap.source} · odświeżono {ts}")

        quota_gb = snap.storage_quota_bytes / (1024**3)
        _add_meter(
            body,
            0,
            title=f"Magazyn R2 (limit {quota_gb:.0f} GB / mc)",
            used=snap.storage_bytes,
            quota=snap.storage_quota_bytes,
            unit_hint="B",
        )
        _add_meter(
            body,
            1,
            title="Operacje Class A — zapisy, listy (limit 1 000 000 / mc)",
            used=snap.class_a_used,
            quota=snap.class_a_quota,
            unit_hint="oper.",
        )
        _add_meter(
            body,
            2,
            title="Operacje Class B — odczyty (limit 10 000 000 / mc)",
            used=snap.class_b_used,
            quota=snap.class_b_quota,
            unit_hint="oper.",
        )

        egress = ttk.LabelFrame(body, text="Egress (transfer na stronę)", padding=(8, 6))
        egress.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        ttk.Label(
            egress,
            text="Bez limitu — Cloudflare nie liczy egress z R2 na planie Free.",
            foreground="#2e7d32",
        ).pack(anchor="w")

        lines = [
            f"Plików w bucketcie: {_fmt_int(snap.object_count)}",
            f"  zoom/: {format_bytes(snap.zoom_bytes)} ({_fmt_int(snap.zoom_object_count)} plików)",
            (
                f"  customer-uploads/: {format_bytes(extra['customer_uploads_bytes'])} "
                f"({_fmt_int(extra['customer_uploads_count'])} plików)"
            ),
            f"  inne: {format_bytes(extra['other_bytes'])}",
        ]
        if snap.zoom_estimate_count is not None and snap.zoom_estimate_avg_bytes:
            lines.append(
                f"Szac. kolejnych zoomów HD: ~{_fmt_int(snap.zoom_estimate_count)} "
                f"(śr. {format_bytes(snap.zoom_estimate_avg_bytes)}, {snap.zoom_estimate_source})"
            )
        extra_var.set("\n".join(lines))
        if snap.error:
            extra_var.set(extra_var.get() + f"\n\nUwaga: {snap.error}")
        if snap.note and snap.class_a_used is None:
            extra_var.set(extra_var.get() + f"\n\n{snap.note}")

    def refresh() -> None:
        status_var.set("Ładowanie danych z R2…")
        refresh_btn.configure(state="disabled")

        def worker() -> None:
            try:
                snap = collect_r2_usage()
                extra = enrich_snapshot_with_uploads(snap)
                dlg.after(0, lambda: render_snap(snap, extra))
            except Exception as exc:
                dlg.after(0, lambda: render_error(str(exc)))
            finally:
                dlg.after(0, lambda: refresh_btn.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    refresh_btn = ttk.Button(btn_row, text="Odśwież", command=refresh)
    refresh_btn.pack(side="right", padx=(8, 0))
    ttk.Button(btn_row, text="Zamknij", command=dlg.destroy).pack(side="right")

    refresh()
