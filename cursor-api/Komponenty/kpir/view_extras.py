"""Rozszerzone ekrany KPiR — mixin dla KpirView."""

from __future__ import annotations

import os
import subprocess
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, Any

from Komponenty._shared.toast import show_toast

from .bank_import import import_bank_csv, parse_bank_csv
from .constants import KPIR_COLUMN_LABELS
from .cost_service import book_cost_to_kpir, create_cost, default_kpir_column, update_cost
from .dnr_tracker import dnr_status
from .export_service import export_accountant_package
from .jpk_export import export_jpk_pkpir_xml
from .fx_diff_service import book_fx_diff_adjustments, compute_fx_diff_report, register_fx_settlement
from .invoice_integration import create_entry_from_invoice_id
from .invoice_list import list_invoices_for_kpir, unbooked_invoices
from .margin_service import gross_margin_summary
from .finance_month_close import build_finance_month_close
from .finance_pipeline import format_dnr_catchup_report, run_dnr_catchup
from .month_checklist import build_month_checklist
from .month_closing import close_month, reopen_month
from .pit_calculator import estimate_pit
from .refund_wizard import apply_refund_correction, orders_needing_correction
from .storage import get_cost, load_settings, save_settings
from .summary_service import monthly_summary, yearly_summary
from .validation import ValidationError

if TYPE_CHECKING:
    from .view import KpirView

_BG = "#f4f6f9"


def _draw_bar_chart(canvas: tk.Canvas, data: list[tuple[str, float]], *, width: int = 700, height: int = 180) -> None:
    canvas.delete("all")
    if not data:
        canvas.create_text(width // 2, height // 2, text="Brak danych", fill="#888")
        return
    max_val = max(v for _, v in data) or 1
    bar_w = max(12, (width - 40) // len(data) - 4)
    x0 = 30
    for label, val in data:
        h = int((val / max_val) * (height - 50))
        y1 = height - 25
        y0 = y1 - h
        canvas.create_rectangle(x0, y0, x0 + bar_w, y1, fill="#1565c0", outline="")
        canvas.create_text(x0 + bar_w // 2, y1 + 10, text=label, font=("Segoe UI", 7))
        if val > 0:
            canvas.create_text(x0 + bar_w // 2, y0 - 8, text=f"{val:.0f}", font=("Segoe UI", 7))
        x0 += bar_w + 4


class KpirViewExtras:
    """Dodatkowe ekrany i rozszerzenia nawigacji."""

    def _period_bar(self, parent: tk.Widget, y_var: tk.IntVar, m_var: tk.IntVar) -> tk.Frame:
        bar = tk.Frame(parent, bg=_BG)
        ttk.Label(bar, text="Rok:").pack(side="left")
        ttk.Spinbox(bar, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        ttk.Label(bar, text="Miesiąc:").pack(side="left", padx=(8, 0))
        ttk.Spinbox(bar, from_=1, to=12, textvariable=m_var, width=4).pack(side="left", padx=4)
        return bar

    def show_refunds(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Korekty zwrotów", back=self._back_for("refunds"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        status = tk.StringVar(value="Ładuję…")
        tk.Label(body, textvariable=status, bg=_BG, fg="#444").pack(anchor="w")
        state: dict[str, Any] = {"cases": []}

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("order", "date", "refund", "total", "entry", "type")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        for cid, txt, w in [
            ("order", "Zamówienie", 90), ("date", "Data", 90), ("refund", "Zwrot", 70),
            ("total", "Suma zam.", 70), ("entry", "Wpis KPiR", 90), ("type", "Typ", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True)

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            cases = orders_needing_correction()
            state["cases"] = cases
            for c in cases:
                tree.insert("", "end", iid=str(c.shopify_order_id), values=(
                    c.shopify_order_name, c.payment_date,
                    f"{c.refund_total:.2f}", f"{c.order_total:.2f}",
                    c.entry_number,
                    "pełny" if c.is_full_refund else "częściowy",
                ))
            status.set(f"Zamówienia wymagające korekty: {len(cases)}")

        def correct_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            oid = int(sel[0])
            case = next((c for c in state["cases"] if c.shopify_order_id == oid), None)
            if not case:
                return
            try:
                entry = apply_refund_correction(case)
                show_toast(outer, f"Korekta: {entry.entry_number}", bg="#2e7d32")
                refresh()
            except Exception as exc:
                messagebox.showerror("Korekta", str(exc), parent=outer)

        def correct_all() -> None:
            n = 0
            for case in list(state["cases"]):
                try:
                    apply_refund_correction(case)
                    n += 1
                except Exception:
                    pass
            show_toast(outer, f"Utworzono {n} korekt", bg="#2e7d32")
            refresh()

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Korekta zaznaczonego", command=correct_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Korekta wszystkich", command=correct_all).pack(side="left", padx=4)
        threading.Thread(target=lambda: outer.after(0, refresh), daemon=True).start()
        self._swap(outer)

    def show_margin(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Marża brutto")
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        self._period_bar(body, y_var, m_var).pack(anchor="w", pady=(0, 8))
        txt = tk.Text(body, height=12, width=60, font=("Consolas", 10))
        txt.pack(fill="x")

        def refresh() -> None:
            s = gross_margin_summary(year=y_var.get(), month=m_var.get())
            lines = [
                f"Okres: {s['year']}-{s['month']:02d}",
                f"Przychód: {s['revenue']:.2f} PLN",
                f"Koszty materiałowe (kol. zakup): {s['materials_cost']:.2f} PLN",
                f"Pozostałe koszty: {s['other_costs']:.2f} PLN",
                f"Marża brutto: {s['gross_profit']:.2f} PLN ({s['gross_margin_percent']:.1f}%)",
                f"Dochód (po wszystkich kosztach): {s['net_income']:.2f} PLN",
            ]
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(lines))
            txt.configure(state="disabled")

        ttk.Button(body, text="Odśwież", command=refresh).pack(anchor="w", pady=4)
        refresh()
        self._swap(outer)

    def show_fx_diff(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Waluty obce / różnice kursowe")
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        self._period_bar(body, y_var, m_var).pack(anchor="w")

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("date", "doc", "cur", "foreign", "book_rate", "book_pln", "settle_rate", "diff", "kind")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12)
        for cid, txt, w in [
            ("date", "Data", 85), ("doc", "Dowód", 95), ("cur", "Wal.", 45),
            ("foreign", "Waluta", 65), ("book_rate", "Kurs ks.", 60), ("book_pln", "PLN ks.", 65),
            ("settle_rate", "Kurs roz.", 60), ("diff", "Różnica", 65), ("kind", "Typ", 55),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True)
        disc = tk.Label(body, bg=_BG, fg="#666", font=("Segoe UI", 9), wraplength=720, justify="left")
        disc.pack(anchor="w")

        state: dict[str, Any] = {"rows": []}

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            report = compute_fx_diff_report(year=y_var.get(), month=m_var.get())
            state["rows"] = report.rows
            for row in report.rows:
                tree.insert("", "end", iid=row.entry_id, values=(
                    row.event_date, row.document_number, row.currency,
                    f"{row.amount_foreign:.2f}", f"{row.booking_rate:.4f}", f"{row.amount_pln_booked:.2f}",
                    f"{row.settlement_rate:.4f}", f"{row.fx_diff_pln:+.2f}", row.diff_kind,
                ))
            disc.config(
                text=(
                    f"{report.disclaimer} | Wpisy: {report.total_foreign_entries}, brak NBP: {report.missing_rate_count} | "
                    f"Zyski: +{report.total_gain_pln:.2f} PLN, straty: -{report.total_loss_pln:.2f} PLN, netto: {report.net_diff_pln:+.2f} PLN"
                ),
            )

        def set_settlement() -> None:
            sel = tree.selection()
            if not sel:
                return
            rate_s = simpledialog.askstring("Kurs rozliczenia", "PLN za 1 jednostkę waluty:", parent=outer)
            if not rate_s:
                return
            date_s = simpledialog.askstring("Data rozliczenia", "YYYY-MM-DD:", parent=outer, initialvalue=date.today().isoformat())
            if not date_s:
                return
            try:
                register_fx_settlement(sel[0], date_s, float(rate_s.replace(",", ".")))
                refresh()
                show_toast(outer, "Zapisano kurs rozliczenia", bg="#2e7d32")
            except (ValueError, TypeError) as exc:
                messagebox.showerror("Błąd", str(exc), parent=outer)

        def book_diffs() -> None:
            try:
                posted = book_fx_diff_adjustments(year=y_var.get(), month=m_var.get())
                show_toast(outer, f"Zaksięgowano {len(posted)} korekt różnic kursowych", bg="#2e7d32")
            except Exception as exc:
                messagebox.showerror("KPiR", str(exc), parent=outer)

        btns = ttk.Frame(body)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Ustaw kurs rozliczenia", command=set_settlement).pack(side="left", padx=4)
        ttk.Button(btns, text="Zaksięguj różnice miesiąca", command=book_diffs).pack(side="left", padx=4)
        refresh()
        self._swap(outer)

    def _close_month_with_checklist(self: KpirView, outer: tk.Widget, year: int, month: int, on_done: Callable[[], None]) -> None:
        from Komponenty._shared.finance_navigation import checklist_nav_target, open_finance_module, set_nav

        checklist = build_month_checklist(year, month)
        win = tk.Toplevel(outer)
        win.title(f"Zamknięcie miesiąca {year}-{month:02d}")
        win.geometry("640x440")
        ttk.Label(
            win,
            text=f"Błędy: {checklist.blocking_count} · Ostrzeżenia: {checklist.warning_count}",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 4))
        frame = ttk.Frame(win)
        frame.pack(fill="both", expand=True, padx=10, pady=4)
        tree = ttk.Treeview(frame, columns=("sev", "cat", "msg"), show="headings", height=14)
        for cid, txt, w in [("sev", "!", 28), ("cat", "Typ", 70), ("msg", "Opis", 420)]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        refs: dict[str, tuple[str, str]] = {}
        for idx, item in enumerate(checklist.items):
            iid = f"c-{idx}"
            icon = {"error": "✗", "warning": "!", "info": "i"}.get(item.severity, "•")
            tree.insert("", "end", iid=iid, values=(icon, item.category, item.message))
            refs[iid] = (item.category, item.ref)

        def open_item() -> None:
            sel = tree.selection()
            if not sel:
                return
            cat, ref = refs.get(sel[0], ("", ""))
            target = checklist_nav_target(cat, ref)
            if not target:
                messagebox.showinfo("Checklist", "Brak linku dla tej pozycji.", parent=win)
                return
            set_nav(target.module, target.screen, target.ref)
            if open_finance_module(target.module):
                win.destroy()
            else:
                messagebox.showinfo(
                    "Checklist",
                    f"Otwórz moduł: {target.module} (np. z panelu Księgowość).",
                    parent=win,
                )

        tree.bind("<Double-1>", lambda _e: open_item())

        def do_close(force: bool = False) -> None:
            try:
                close_month(year, month, force=force)
                show_toast(outer, "Miesiąc zamknięty", bg="#2e7d32")
                win.destroy()
                on_done()
            except ValidationError as exc:
                if not force and messagebox.askyesno(
                    "Zamknięcie miesiąca",
                    f"{exc}\n\nZamknąć mimo ostrzeżeń?",
                    parent=win,
                ):
                    do_close(force=True)
                else:
                    messagebox.showerror("Zamknięcie", str(exc), parent=win)

        bf = tk.Frame(win)
        bf.pack(fill="x", padx=10, pady=8)
        tk.Button(bf, text="Otwórz pozycję", command=open_item, bg="#1565c0", fg="#fff").pack(side="left", padx=4)
        tk.Button(bf, text="Zamknij miesiąc", command=lambda: do_close(False), bg="#2e7d32", fg="#fff").pack(side="left", padx=4)
        tk.Button(bf, text="Anuluj", command=win.destroy).pack(side="left")

    def show_finance_close(self: KpirView) -> None:
        """Wspólny widok zamknięcia miesiąca: KPiR + DNR + faktury + checklist."""
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Zamknięcie miesiąca — finanse", back=self._back_for("finance_close"))
        top = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        top.pack(fill="x")
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        ttk.Label(top, text="Rok:").pack(side="left")
        ttk.Spinbox(top, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        ttk.Label(top, text="Miesiąc:").pack(side="left", padx=(8, 0))
        ttk.Spinbox(top, from_=1, to=12, textvariable=m_var, width=4).pack(side="left", padx=4)

        summary_var = tk.StringVar(value="")
        ttk.Label(outer, textvariable=summary_var, wraplength=720, justify="left").pack(
            anchor="w", padx=16, pady=(0, 4),
        )
        checklist_txt = tk.Text(outer, height=14, width=80, font=("Consolas", 9), wrap="word")
        checklist_txt.pack(fill="both", expand=True, padx=16, pady=8)

        def refresh() -> None:
            data = build_finance_month_close(y_var.get(), m_var.get())
            summary_var.set(
                f"KPiR: przychód {data.kpir_revenue:.2f} PLN, koszty {data.kpir_costs:.2f} PLN, "
                f"dochód {data.kpir_income:.2f} PLN · "
                f"Faktury: {data.invoice_count} ({data.invoice_total_pln:.2f} PLN) · "
                f"DNR: przychód {data.dnr_revenue:.2f} PLN, koszty {data.dnr_costs:.2f} PLN · "
                f"Checklist: {data.blocking_count} błędów, {data.warning_count} ostrzeżeń"
            )
            lines = []
            for item in data.checklist_items:
                icon = {"error": "✗", "warning": "!", "info": "i"}.get(item.get("severity"), "•")
                lines.append(f"  {icon} [{item.get('category')}] {item.get('message')}")
            if not lines:
                lines.append("  (brak problemów w checklist)")
            checklist_txt.configure(state="normal")
            checklist_txt.delete("1.0", "end")
            checklist_txt.insert("1.0", "\n".join(lines))
            checklist_txt.configure(state="disabled")

        def import_dnr_catchup() -> None:
            y = y_var.get()
            if not messagebox.askyesno(
                "Import DNR (zaległe)",
                f"Zaimportować wystawione faktury z {y} bez wpisu DNR?\n\n"
                "Tylko domknięcie braków — bez szkiców i bez KPiR.",
                parent=outer,
            ):
                return
            imported, skipped, errors = run_dnr_catchup(y)
            show_toast(outer, f"DNR: zaimportowano {imported}", bg="#2e7d32")
            messagebox.showinfo(
                "Import DNR",
                format_dnr_catchup_report(imported, skipped, errors),
                parent=outer,
            )
            refresh()

        def export_invoices() -> None:
            try:
                from Komponenty.dokumentysprzedazy.export_monthly import export_month_csv
                path = export_month_csv(y_var.get(), m_var.get())
                show_toast(outer, f"Eksport: {path.name}", bg="#1565c0")
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        btns = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Import DNR (zaległe)", command=import_dnr_catchup).pack(side="left", padx=4)
        ttk.Button(btns, text="Eksport faktur (CSV)", command=export_invoices).pack(side="left", padx=4)
        ttk.Button(
            btns,
            text="Zamknij miesiąc KPiR",
            command=lambda: self._close_month_with_checklist(outer, y_var.get(), m_var.get(), refresh),
        ).pack(side="left", padx=4)
        refresh()
        self._swap(outer)
