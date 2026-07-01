"""Okno: skan brakow mockupow na Shopify + dogrywanie."""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox, ttk

from Komponenty._shared.activity_log import append_activity
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .audit import MissingMockupRow, scan_missing_mockups
from .publish import publish_mockup_for_row
from .templates import (
    MOCKUP_ALL_VARIANTS_LABEL,
    MockupSet,
    list_mockup_sets,
    mockup_set_choices,
    resolve_mockup_sets,
)


class MissingMockupsDialog:
    def __init__(self, parent: tk.Misc, *, enqueue_log: Callable[[str], None] | None = None) -> None:
        self.parent = parent
        self._enqueue_log = enqueue_log
        self.sets = list_mockup_sets()
        self.rows: list[MissingMockupRow] = []

        self.win = tk.Toplevel(parent)
        self.win.title("Braki mockupow na stronie")
        position_toplevel_screen_center(self.win, 980, 620)
        self.win.minsize(760, 480)

        self.set_var = tk.StringVar(value=MOCKUP_ALL_VARIANTS_LABEL if self.sets else "")
        self.status_var = tk.StringVar(value="Kliknij «Skanuj», aby pobrac liste z Shopify.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_label_var = tk.StringVar(value="")

        self._build_ui()

    def _selected_sets(self) -> list[MockupSet]:
        return resolve_mockup_sets(self.sets, self.set_var.get())

    def _variants_label(self, sets: list[MockupSet]) -> str:
        if len(sets) > 1:
            return ", ".join(s.name_suffix for s in sets if s.name_suffix) or "wszystkie"
        if sets:
            return sets[0].name_suffix or sets[0].name
        return "?"

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        top = ttk.Frame(self.win)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Wariant mockupu do dogrania:").pack(side="left")
        ttk.Combobox(
            top,
            textvariable=self.set_var,
            values=mockup_set_choices(self.sets),
            state="readonly",
            width=42,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Skanuj Shopify", command=self._run_scan).pack(side="left", padx=(12, 0))
        ttk.Button(top, text="Odswiez", command=self._run_scan).pack(side="left", padx=(6, 0))
        ttk.Label(top, textvariable=self.status_var, foreground="#666").pack(side="right")

        cols = ("title", "missing", "handle")
        tree_frame = ttk.Frame(self.win)
        tree_frame.pack(fill="both", expand=True, **pad)
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        self.tree.heading("title", text="Produkt")
        self.tree.heading("missing", text="Brakuje")
        self.tree.heading("handle", text="Handle")
        self.tree.column("title", width=420, stretch=True)
        self.tree.column("missing", width=120, stretch=False)
        self.tree.column("handle", width=200, stretch=False)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_selected_admin)

        prog = ttk.Frame(self.win)
        prog.pack(fill="x", **pad)
        ttk.Progressbar(prog, variable=self.progress_var, maximum=100).pack(fill="x")
        ttk.Label(prog, textvariable=self.progress_label_var, foreground="#666").pack(anchor="w")

        bottom = ttk.Frame(self.win)
        bottom.pack(fill="x", **pad)
        ttk.Button(bottom, text="Otworz w Shopify", command=self._open_selected_admin).pack(side="left")
        ttk.Button(bottom, text="Dograj zaznaczone", command=self._publish_selected).pack(side="right")
        ttk.Button(bottom, text="Dograj wszystkie", command=self._publish_all).pack(side="right", padx=(0, 8))
        ttk.Button(bottom, text="Zamknij", command=self.win.destroy).pack(side="right", padx=(0, 8))

    def _log(self, msg: str) -> None:
        if self._enqueue_log:
            self._enqueue_log(msg)

    def _row_iid(self, row: MissingMockupRow) -> str:
        return str(row.product_id)

    def _run_scan(self) -> None:
        if not self.sets:
            messagebox.showerror("Braki mockupow", "Brak zdefiniowanych szablonow mockupu.", parent=self.win)
            return

        self.status_var.set("Skanuje produkty na Shopify...")
        self.progress_var.set(0)

        def worker() -> None:
            try:
                rows = scan_missing_mockups(
                    self.sets,
                    on_progress=lambda d, t, lbl: self.win.after(
                        0,
                        lambda dd=d, tt=t, lb=lbl: self._scan_progress(dd, tt, lb),
                    ),
                )
            except Exception as exc:
                self.win.after(0, lambda: self._scan_failed(str(exc)))
                return
            self.win.after(0, lambda: self._scan_done(rows))

        threading.Thread(target=worker, daemon=True).start()

    def _scan_progress(self, done: int, total: int, label: str) -> None:
        pct = (done / total * 100) if total else 0
        self.progress_var.set(pct)
        short = label if len(label) <= 40 else label[:37] + "..."
        self.progress_label_var.set(f"{done}/{total}: {short}")

    def _scan_failed(self, err: str) -> None:
        self.status_var.set("Blad skanu.")
        messagebox.showerror("Braki mockupow", err, parent=self.win)

    def _scan_done(self, rows: list[MissingMockupRow]) -> None:
        self.rows = rows
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert(
                "",
                "end",
                iid=self._row_iid(row),
                values=(row.title, ", ".join(row.missing_suffixes), row.handle),
            )
        self.progress_var.set(100 if rows else 0)
        self.progress_label_var.set("")
        self.status_var.set(f"Znaleziono {len(rows)} produkt(ow) bez pelnego zestawu mockupow.")

    def _selected_rows(self) -> list[MissingMockupRow]:
        by_id = {str(r.product_id): r for r in self.rows}
        out: list[MissingMockupRow] = []
        for iid in self.tree.selection():
            row = by_id.get(iid)
            if row:
                out.append(row)
        return out

    def _open_selected_admin(self, _event: object | None = None) -> None:
        rows = self._selected_rows()
        if not rows:
            messagebox.showinfo("Braki mockupow", "Zaznacz produkt na liscie.", parent=self.win)
            return
        webbrowser.open(rows[0].admin_url)

    def _publish_rows(self, rows: list[MissingMockupRow]) -> None:
        mockup_sets = self._selected_sets()
        if not mockup_sets:
            messagebox.showerror("Braki mockupow", "Wybierz wariant mockupu.", parent=self.win)
            return
        if not rows:
            messagebox.showinfo("Braki mockupow", "Brak pozycji do dogrania.", parent=self.win)
            return
        label = self._variants_label(mockup_sets)
        if not messagebox.askyesno(
            "Braki mockupow",
            f"Dograc mockup ({label}) dla {len(rows)} produkt(ow)?",
            parent=self.win,
        ):
            return

        self.status_var.set("Dogrywam mockupy...")
        self.progress_var.set(0)

        def worker() -> None:
            ok = err = skip = 0
            done = 0
            jobs: list[tuple[MissingMockupRow, MockupSet]] = []
            for row in rows:
                for mockup_set in mockup_sets:
                    if mockup_set.name_suffix in row.missing_suffixes:
                        jobs.append((row, mockup_set))
            total = len(jobs)

            def one(
                row: MissingMockupRow, mockup_set: MockupSet
            ) -> tuple[MissingMockupRow, MockupSet, dict | None, str | None]:
                try:
                    res = publish_mockup_for_row(row, mockup_set, logger=self._log)
                    return row, mockup_set, res, None
                except Exception as exc:
                    return row, mockup_set, None, str(exc)

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(one, row, ms): (row, ms) for row, ms in jobs}
                for fut in as_completed(futures):
                    row, mockup_set, res, err_msg = fut.result()
                    done += 1
                    if err_msg:
                        err += 1
                        self._log(
                            f"[mockup audit] BLAD {row.title} ({mockup_set.name_suffix}): {err_msg}"
                        )
                    elif res and res.get("skipped"):
                        skip += 1
                    else:
                        ok += 1
                        append_activity(
                            "mockup",
                            f"Audit: {row.title} -> {mockup_set.name_suffix}",
                            detail=row.admin_url,
                        )
                    self.win.after(
                        0,
                        lambda d=done, t=total, n=row.title: self._publish_progress(d, t, n),
                    )

            def _done() -> None:
                self.status_var.set(f"Gotowe. OK: {ok}, pominiete: {skip}, bledy: {err}.")
                messagebox.showinfo(
                    "Braki mockupow",
                    f"Zakonczono dogrywanie.\nOK: {ok}\nPominiete: {skip}\nBledy: {err}",
                    parent=self.win,
                )
                self._run_scan()

            self.win.after(0, _done)

        threading.Thread(target=worker, daemon=True).start()

    def _publish_progress(self, done: int, total: int, label: str) -> None:
        pct = (done / total * 100) if total else 0
        self.progress_var.set(pct)
        self.progress_label_var.set(f"{done}/{total}: {label[:40]}")

    def _publish_selected(self) -> None:
        self._publish_rows(self._selected_rows())

    def _publish_all(self) -> None:
        self._publish_rows(list(self.rows))


def open_missing_mockups_dialog(parent: tk.Misc, *, enqueue_log: Callable[[str], None] | None = None) -> None:
    MissingMockupsDialog(parent, enqueue_log=enqueue_log)
