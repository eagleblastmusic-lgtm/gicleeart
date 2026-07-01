"""Widok inline — moduł KPiR."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from Komponenty._shared.toast import show_toast

from .bank_import import import_bank_csv
from .constants import (
    DEFAULT_COST_CATEGORIES,
    DISCLAIMER_PIT,
    FEE_IMPORT_MONTHLY_HINT,
    FEE_IMPORT_TIPS,
    FX_DIFF_PLACEHOLDER,
    JPK_PKPIR_PLACEHOLDER,
    KPIR_COLUMN_BY_LABEL,
    KPIR_COLUMN_LABELS,
    KPIR_COST_COLUMN_KEYS,
    ACCOUNTING_MODE_OPTIONS,
    COST_KPIR_STATUS_LABELS,
    COST_METHOD_OPTIONS,
    ENTRY_SOURCE_LABELS,
    ENTRY_STATUS_LABELS,
    SALES_GROUPING_OPTIONS,
    TAX_FORM_OPTIONS,
    VAT_STATUS_OPTIONS,
    option_key,
    option_label,
    resolved_accounting_mode,
)
from .cost_service import book_cost_to_kpir, create_cost, default_kpir_column, delete_costs_many, update_cost
from .entry_detail import open_entry_detail
from .fee_import import import_fee_csv, parse_fee_csv
from .correction_service import create_full_refund_correction
from .entry_service import filter_entries, post_entry
from .export_service import (
    export_accountant_csv,
    export_accountant_package,
    export_kpir_csv,
    export_kpir_pdf,
    export_kpir_xlsx,
)
from .jpk_export import export_jpk_pkpir_xml
from .invoice_list import list_invoices_for_kpir, unbooked_invoices
from .sales_chain import uses_dnr_sales_chain
from .margin_service import gross_margin_summary
from .dnr_tracker import dnr_status
from .view_extras import KpirViewExtras, _draw_bar_chart
from .view_official_extras import KpirOfficialExtras
from .invoice_integration import create_entry_from_invoice_id
from .models import CostRecord, KpirSettings
from .month_closing import close_month, reopen_month
from .pit_calculator import estimate_pit
from .recurring_service import (
    create_recurring,
    delete_recurring,
    delete_recurring_many,
    due_recurring_items,
    generate_draft_cost_from_recurring,
)
from .shopify_service import mark_order_skipped
from .storage import get_cost, get_entry, list_costs, list_recurring, load_settings, save_settings
from .summary_service import dashboard_summary, monthly_summary, yearly_summary

_COMPONENT_DIR = Path(__file__).resolve().parent
_BG = "#f4f6f9"


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    view = KpirView(parent, on_back)
    return view.frame


class KpirView(KpirViewExtras, KpirOfficialExtras):
    def __init__(self, parent: tk.Widget, on_back: Callable[[], None]) -> None:
        self.parent = parent
        self.on_back = on_back
        self.frame = tk.Frame(parent, bg=_BG)
        self._screen: tk.Widget | None = None
        self._nav_entry_screen: str | None = None
        self._apply_finance_nav()
        if self._screen is None:
            self.show_dashboard()

    def _apply_finance_nav(self) -> None:
        from Komponenty._shared.finance_navigation import consume_nav

        nav = consume_nav("kpir")
        if not nav:
            return
        self._nav_entry_screen = nav.screen
        routes = {
            "revenue": self.show_revenues,
            "revenues": self.show_revenues,
            "costs": self.show_costs,
            "refunds": self.show_refunds,
            "finance_close": self.show_finance_close,
            "settings": self.show_settings,
        }
        fn = routes.get(nav.screen)
        if fn:
            fn()

    def _back_for(self, screen: str) -> Callable[[], None]:
        from Komponenty._shared.finance_navigation import back_for_nav_entry

        return back_for_nav_entry(
            entry_screen=self._nav_entry_screen,
            current_screen=screen,
            hub_back=self.on_back,
            module_back=self.show_dashboard,
        )

    def _swap(self, screen: tk.Widget) -> None:
        if self._screen:
            self._screen.destroy()
        self._screen = screen
        screen.pack(fill="both", expand=True)

    def _toolbar(self, parent: tk.Widget, title: str, *, back: Callable[[], None] | None = None) -> tk.Frame:
        bar = tk.Frame(parent, bg=_BG, pady=8, padx=12)
        bar.pack(fill="x")
        tk.Button(bar, text="← Wróć", command=back or self.show_dashboard, bg="#fff").pack(side="left")
        tk.Label(bar, text=title, font=("Segoe UI", 14, "bold"), bg=_BG).pack(side="left", padx=12)
        return bar

    def show_dashboard(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "KPiR — Dashboard", back=self.on_back)
        settings = load_settings()
        if settings.accounting_mode == "jdg_ryczalt":
            tk.Label(
                outer,
                text="Ryczałt używa ewidencji przychodów, nie KPiR.",
                fg="#b71c1c", bg=_BG, font=("Segoe UI", 11, "bold"),
            ).pack(pady=8)

        from .zus_service import is_jdg_mode, zus_stage_progress

        if is_jdg_mode(settings):
            zprog = zus_stage_progress(settings)
            if zprog.get("active"):
                z_bg = "#fff8e1" if zprog.get("suggest_next") else "#e8f5e9"
                z_fg = "#e65100" if zprog.get("suggest_next") else "#2e7d32"
                tk.Label(
                    outer,
                    text=str(zprog.get("message") or ""),
                    bg=z_bg,
                    fg=z_fg,
                    font=("Segoe UI", 9, "bold"),
                    padx=8,
                    pady=4,
                    wraplength=720,
                    justify="left",
                ).pack(fill="x", padx=16, pady=(0, 4))

        from .payment_due import upcoming_payment_summary

        pay = upcoming_payment_summary(settings)
        if pay.get("message"):
            pay_bg = "#e8eaf6" if pay.get("active") else "#f5f5f5"
            pay_fg = "#283593" if pay.get("active") else "#666"
            tk.Label(
                outer,
                text=str(pay.get("message")),
                bg=pay_bg,
                fg=pay_fg,
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=4,
                wraplength=720,
                justify="left",
            ).pack(fill="x", padx=16, pady=(0, 4))

        try:
            dash = dashboard_summary()
        except Exception:
            dash = {
                "month_revenue": 0, "month_costs": 0, "month_income": 0,
                "year_revenue": 0, "year_costs": 0, "year_income": 0,
                "unbooked_orders": 0, "unbooked_costs": 0, "missing_nbp": 0,
                "refunds_need_correction": 0, "month_closed": False,
                "sales_flow": {},
            }

        flow = dash.get("sales_flow") or {}
        flow_frame = tk.Frame(outer, bg="#e3f2fd", padx=12, pady=8)
        flow_frame.pack(fill="x", padx=16, pady=(0, 4))
        flow_parts = [
            f"bez dokumentu {flow.get('paid_without_invoice', 0)}",
            f"szkice do wystawienia {flow.get('paid_draft_pending', 0)}",
            f"gotowe do DNR {flow.get('issued_without_dnr', 0)}",
        ]
        if not uses_dnr_sales_chain():
            flow_parts.append(f"bez KPiR {flow.get('issued_without_kpir', 0)}")
        flow_parts.append(f"KPiR bez faktury {flow.get('booked_without_invoice', 0)}")
        tk.Label(
            flow_frame,
            text="Przepływ sprzedaży (Shopify → faktura → DNR → KPiR): " + " · ".join(flow_parts),
            bg="#e3f2fd",
            fg="#0d47a1",
            font=("Segoe UI", 9, "bold"),
            wraplength=720,
            justify="left",
        ).pack(anchor="w")
        tk.Label(
            flow_frame,
            text=(
                "Zalecana kolejność: opłacone zamówienie → faktura → import DNR → "
                "ujęcie w KPiR z ewidencji DNR (moduł DNR → Import do KPiR)."
                if uses_dnr_sales_chain()
                else "Zalecana kolejność: opłacone zamówienie → faktura → import DNR → ujęcie w KPiR z faktury."
            ),
            bg="#e3f2fd",
            fg="#1565c0",
            font=("Segoe UI", 8),
            wraplength=720,
            justify="left",
        ).pack(anchor="w")

        try:
            from Komponenty._shared.compliance_ui import compliance_monitors, level_color

            comp_frame = ttk.LabelFrame(outer, text=" Compliance (WSTO/OSS, KSeF, art. 28b) ", padding=8)
            comp_frame.pack(fill="x", padx=16, pady=(0, 4))
            for row in compliance_monitors(date.today().year):
                tk.Label(
                    comp_frame,
                    text=f"{row['title']}: {row['message']}",
                    fg=level_color(str(row.get("level") or "ok")),
                    font=("Segoe UI", 8),
                    wraplength=700,
                    justify="left",
                ).pack(anchor="w", pady=1)
        except ImportError:
            pass

        cards = tk.Frame(outer, bg=_BG)
        cards.pack(fill="x", padx=16, pady=8)
        metrics = [
            ("Przychód (miesiąc)", f"{dash['month_revenue']:.2f} PLN", "#1565c0"),
            ("Koszty (miesiąc)", f"{dash['month_costs']:.2f} PLN", "#c62828"),
            ("Dochód (miesiąc)", f"{dash['month_income']:.2f} PLN", "#2e7d32"),
            ("Przychód (rok)", f"{dash['year_revenue']:.2f} PLN", "#1565c0"),
            ("Niezaksięgowane zam.", str(dash["unbooked_orders"]), "#ef6c00"),
            ("Niezaksięgowane koszty", str(dash["unbooked_costs"]), "#ef6c00"),
            ("Brak kursów NBP", str(dash["missing_nbp"]), "#b71c1c"),
            ("Zwroty do korekty", str(dash["refunds_need_correction"]), "#b71c1c"),
            ("Miesiąc", "zamknięty" if dash["month_closed"] else "otwarty", "#555"),
        ]
        for i, (lbl, val, color) in enumerate(metrics):
            f = tk.Frame(cards, bg="#fff", relief="solid", bd=1, padx=10, pady=8)
            f.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="nsew")
            cards.columnconfigure(i % 3, weight=1)
            tk.Label(f, text=lbl, bg="#fff", fg="#666", font=("Segoe UI", 9)).pack(anchor="w")
            tk.Label(f, text=val, bg="#fff", fg=color, font=("Segoe UI", 12, "bold")).pack(anchor="w")

        nav = tk.Frame(outer, bg=_BG)
        nav.pack(fill="both", expand=True, padx=16, pady=12)
        buttons = [
            ("📒 KPiR", self.show_kpir_table),
            ("📦 Remanent", self.show_inventory),
            ("📋 Ewidencja sprzedaży", self.show_sales_register),
            ("🔐 KSeF", self.show_ksef_sync),
            ("🏢 Środki trwałe", self.show_fixed_assets),
            ("©️ WNiP", self.show_intangible_assets),
            ("🚗 Przebieg pojazdu", self.show_vehicle_log),
            ("📄 Dowody wewnętrzne", self.show_internal_docs),
            ("🔒 Zamknięcie roku", self.show_year_close),
            ("📑 Eksport urzędowy", self.show_official_exports),
            ("⚖️ Compliance PKPiR", self.show_compliance_pkpir),
            ("💰 Przychody", self.show_revenues),
            ("↩️ Korekty zwrotów", self.show_refunds),
            ("📉 Koszty", self.show_costs),
            ("🔄 Koszty cykliczne", self.show_recurring),
            ("📊 Podsumowanie miesiąca", self.show_month_summary),
            ("📋 Zamknięcie miesiąca (finanse)", self.show_finance_close),
            ("📈 Podsumowanie roku", self.show_year_summary),
            ("🔀 Rok przejściowy (DNR+JDG)", self.show_transition_year),
            ("📐 Marża brutto", self.show_margin),
            ("💱 Waluty obce", self.show_fx_diff),
            ("📤 Eksport księgowy", self.show_exports),
            ("📅 Kalendarz terminów", self.show_calendar),
            ("🧮 Szacunkowy PIT", self.show_pit),
        ]
        if settings.accounting_mode == "dnr":
            dnr = dnr_status()
            dnr_bg = {
                "ok": "#e8f5e9",
                "warning": "#fff8e1",
                "critical": "#fff3e0",
                "exceeded": "#ffebee",
                "obligation": "#f3e5f5",
            }.get(dnr["level"], "#e8f5e9")
            dnr_fg = {
                "ok": "#2e7d32",
                "warning": "#f9a825",
                "critical": "#e65100",
                "exceeded": "#c62828",
                "obligation": "#6a1b9a",
            }.get(dnr["level"], "#2e7d32")
            dnr_bar = tk.Frame(nav, bg=_BG)
            dnr_bar.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))
            tk.Label(
                dnr_bar, text=dnr["message"],
                bg=dnr_bg if dnr["level"] != "ok" else "#e8f5e9",
                fg=dnr_fg,
                font=("Segoe UI", 9), padx=8, pady=4,
            ).pack(fill="x")
            if dnr.get("wizard_needed"):
                tk.Label(
                    dnr_bar,
                    text="Wymagana migracja DNR → JDG — otwórz moduł Działalność nierejestrowana.",
                    bg="#fff3e0",
                    fg="#e65100",
                    font=("Segoe UI", 9, "bold"),
                    padx=8,
                    pady=4,
                ).pack(fill="x")
        qa = tk.Frame(nav, bg=_BG)
        qa.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        ttk.Label(qa, text="Szybkie akcje:").pack(side="left")

        ttk.Button(qa, text="Korekty zwrotów", command=self.show_refunds).pack(side="left", padx=4)
        if dash.get("unbooked_costs", 0) > 0:
            ttk.Button(qa, text="Koszty robocze", command=self.show_costs).pack(side="left", padx=4)

        for i, (txt, cmd) in enumerate(buttons):
            tk.Button(
                nav, text=txt, command=cmd, width=28, pady=8,
                bg="#fff", activebackground="#e3f2fd",
            ).grid(row=2 + i // 3, column=i % 3, padx=6, pady=6, sticky="ew")
        for c in range(3):
            nav.columnconfigure(c, weight=1)
        self._swap(outer)

    def show_kpir_table(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Księga Przychodów i Rozchodów")
        settings = load_settings()

        filt = tk.Frame(outer, bg=_BG, padx=12)
        filt.pack(fill="x")
        year_var = tk.IntVar(value=date.today().year)
        month_var = tk.IntVar(value=date.today().month)
        query_var = tk.StringVar()
        official_var = tk.BooleanVar(value=False)
        ttk.Label(filt, text="Rok:").pack(side="left")
        ttk.Spinbox(filt, from_=2020, to=2035, textvariable=year_var, width=6).pack(side="left", padx=4)
        ttk.Label(filt, text="Miesiąc:").pack(side="left", padx=(8, 0))
        ttk.Spinbox(filt, from_=0, to=12, textvariable=month_var, width=4).pack(side="left", padx=4)
        ttk.Label(filt, text="(0=rok)").pack(side="left")
        ttk.Label(filt, text="Szukaj:").pack(side="left", padx=(12, 0))
        ttk.Entry(filt, textvariable=query_var, width=18).pack(side="left", padx=4)
        ttk.Checkbutton(filt, text="Widok urzędowy (19 kolumn)", variable=official_var).pack(side="left", padx=8)

        from .constants import OFFICIAL_COLUMN_HEADERS
        from .official_columns import entry_to_official_row

        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=8)
        cols_simple = ("lp", "date", "doc", "contractor", "desc", "rev", "cost", "chain", "src", "st")
        cols_official = tuple(k for k, _ in OFFICIAL_COLUMN_HEADERS) + ("src",)
        tree = ttk.Treeview(tree_frame, columns=cols_simple, show="headings", height=18)

        def _setup_columns(official: bool) -> None:
            tree.configure(columns=cols_official if official else cols_simple)
            for c in tree["columns"]:
                tree.heading(c, text="")
            if official:
                specs = [(k, lbl, 72 if k not in ("description", "contractor", "contractor_address") else 110) for k, lbl in OFFICIAL_COLUMN_HEADERS]
                specs.append(("src", "Źr.", 50))
            else:
                specs = [
                    ("lp", "Lp.", 40), ("date", "Data", 85), ("doc", "Dowód", 90),
                    ("contractor", "Kontrahent", 110), ("desc", "Opis", 160),
                    ("rev", "Przychód", 70), ("cost", "Koszty", 65),
                    ("chain", "DNR/JDG", 58), ("src", "Źródło", 65), ("st", "Status", 75),
                ]
            for cid, txt, w in specs:
                tree.heading(cid, text=txt)
                tree.column(cid, width=w, minwidth=40)

        _setup_columns(False)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        def refresh() -> None:
            from .entry_labels import entry_chain_label

            _setup_columns(official_var.get())
            for i in tree.get_children():
                tree.delete(i)
            m = month_var.get() or None
            entries = filter_entries(
                year=year_var.get(), month=m, query=query_var.get().strip() or None,
            )
            for i, e in enumerate(sorted(entries, key=lambda x: x.event_date), 1):
                src = ENTRY_SOURCE_LABELS.get(e.source, e.source)
                st = ENTRY_STATUS_LABELS.get(e.status, e.status)
                chain = entry_chain_label(e, jdg_registered_at=settings.jdg_registered_at)
                if official_var.get():
                    row = entry_to_official_row(i, e, settings=settings)
                    vals = []
                    for k, _ in OFFICIAL_COLUMN_HEADERS:
                        v = row.get(k, "")
                        if isinstance(v, float):
                            vals.append(f"{v:.2f}")
                        else:
                            vals.append(str(v)[:40] if k in ("description", "contractor_address") else str(v)[:20])
                    vals.append(src)
                    tree.insert("", "end", iid=e.id, values=tuple(vals))
                else:
                    tree.insert("", "end", iid=e.id, values=(
                        i, e.event_date[:10], e.document_number,
                        (e.contractor or "")[:30], (e.description or "")[:40],
                        f"{e.total_revenue:.2f}", f"{e.total_costs:.2f}",
                        chain, src, st,
                    ))

        def show_detail(_e: tk.Event | None = None) -> None:
            sel = tree.selection()
            if not sel:
                return
            open_entry_detail(outer, sel[0])

        ttk.Button(filt, text="Odśwież", command=refresh).pack(side="left", padx=8)
        ttk.Button(filt, text="Szczegóły wpisu", command=show_detail).pack(side="left", padx=4)
        official_var.trace_add("write", lambda *_: refresh())
        query_var.trace_add("write", lambda *_: refresh())
        tree.bind("<Double-1>", show_detail)
        refresh()
        self._swap(outer)

    def show_revenues(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Przychody — podgląd zamówień", back=self._back_for("revenue"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        status = tk.StringVar(value="Podgląd statusu zamówień — księgowanie tylko z wystawionej faktury.")
        tk.Label(body, textvariable=status, bg=_BG, fg="#444").pack(anchor="w")
        state: dict[str, Any] = {"orders": []}

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("order", "date", "client", "total", "cur", "country", "invoice", "kpir")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14, selectmode="extended")
        for cid, txt, w in [
            ("order", "Zamówienie", 80), ("date", "Data płat.", 90),
            ("client", "Klient", 120), ("total", "Suma", 70),
            ("cur", "Waluta", 50), ("country", "Kraj", 45),
            ("invoice", "Faktura", 90), ("kpir", "KPiR", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True)

        def refresh_table() -> None:
            from Komponenty.dokumentysprzedazy.shopify_orders import order_to_row
            from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id
            from Komponenty.kpir.order_status import get_order_kpir_status

            for i in tree.get_children():
                tree.delete(i)
            for o in state["orders"]:
                row = order_to_row(o)
                kpir = get_order_kpir_status(row.shopify_order_id)
                st_lbl = {
                    "not_booked": "nieujęte",
                    "booked": "ujęte",
                    "needs_correction": "korekta",
                    "skipped": "pominięte",
                }.get(kpir.status, kpir.status)
                inv = invoice_by_order_id(row.shopify_order_id)
                inv_lbl = "—"
                if inv:
                    inv_lbl = inv.invoice_number if inv.status == "issued" else f"szkic ({inv.status})"
                tree.insert("", "end", iid=str(row.shopify_order_id), values=(
                    row.shopify_order_name, row.payment_date[:10], row.customer_name,
                    f"{row.order_total:.2f}", row.currency, row.shipping_country,
                    inv_lbl, st_lbl,
                ))

        def load_orders() -> None:
            status.set("Pobieram zamówienia...")
            def worker() -> None:
                try:
                    from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
                    orders = fetch_orders(days_back=365, financial_status="paid")
                except Exception as exc:
                    outer.after(0, lambda: (status.set(f"Błąd: {exc}"), messagebox.showerror("Shopify", str(exc))))
                    return
                def apply() -> None:
                    state["orders"] = orders
                    refresh_table()
                    status.set(f"Załadowano {len(orders)} zamówień.")
                outer.after(0, apply)
            threading.Thread(target=worker, daemon=True).start()

        def skip_selected() -> None:
            sel = tree.selection()
            if sel:
                mark_order_skipped(int(sel[0]))
                refresh_table()

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Pobierz zamówienia", command=load_orders).pack(side="left", padx=4)
        if uses_dnr_sales_chain():
            ttk.Label(
                btns,
                text="Księgowanie: Dokumenty sprzedaży → DNR (bez faktury nie księgujemy)",
                foreground="#1565c0",
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(12, 4))
        else:
            ttk.Label(
                btns,
                text="Księgowanie: wystaw fakturę → auto-księgowanie w KPiR",
                foreground="#1565c0",
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(12, 4))
        ttk.Button(btns, text="Pomiń zamówienie", command=skip_selected).pack(side="left", padx=4)

        if not uses_dnr_sales_chain():
            inv_frame = ttk.LabelFrame(body, text="Faktury bez VAT", padding=8)
            inv_frame.pack(fill="both", expand=True, pady=8)
            inv_cols = ("number", "date", "buyer", "amount", "ksef", "order", "kpir")
            inv_tree = ttk.Treeview(inv_frame, columns=inv_cols, show="headings", height=6)
            for cid, txt, w in [
                ("number", "Numer", 110), ("date", "Data", 85), ("buyer", "Nabywca", 120),
                ("amount", "PLN", 70), ("ksef", "KSeF", 90), ("order", "Zamówienie", 80), ("kpir", "KPiR", 80),
            ]:
                inv_tree.heading(cid, text=txt)
                inv_tree.column(cid, width=w)
            inv_tree.pack(fill="both", expand=True)

            def refresh_invoices() -> None:
                for i in inv_tree.get_children():
                    inv_tree.delete(i)
                for row in list_invoices_for_kpir():
                    st = {"not_booked": "nieujęta", "booked": "ujęta"}.get(row.kpir_status, row.kpir_status)
                    inv_tree.insert("", "end", iid=row.invoice_id, values=(
                        row.invoice_number, row.sale_date, row.buyer_name[:30],
                        f"{row.amount_pln:.2f}", row.ksef_number or "—", row.shopify_order_name, st,
                    ))

            def book_inv_selected() -> None:
                sel = inv_tree.selection()
                if not sel:
                    return
                try:
                    entry = create_entry_from_invoice_id(sel[0], post=True)
                    show_toast(outer, f"Faktura ujęta: {entry.entry_number}", bg="#2e7d32")
                    refresh_invoices()
                except Exception as exc:
                    messagebox.showerror("KPiR", str(exc), parent=outer)

            def book_all_invoices() -> None:
                n = 0
                for row in unbooked_invoices():
                    try:
                        create_entry_from_invoice_id(row.invoice_id, post=True)
                        n += 1
                    except Exception:
                        pass
                show_toast(outer, f"Ujęto {n} faktur", bg="#2e7d32")
                refresh_invoices()

            inv_btns = tk.Frame(inv_frame)
            inv_btns.pack(fill="x", pady=4)
            ttk.Button(inv_btns, text="Odśwież listę", command=refresh_invoices).pack(side="left", padx=4)
            ttk.Button(inv_btns, text="Ujmij zaznaczoną", command=book_inv_selected).pack(side="left", padx=4)
            ttk.Button(inv_btns, text="Ujmij wszystkie nieujęte", command=book_all_invoices).pack(side="left", padx=4)
            refresh_invoices()
        else:
            ttk.Label(
                body,
                text=(
                    "Wystawione faktury importuj do DNR (moduł DNR lub pipeline), "
                    "a przychody w KPiR ujmij przez DNR → Import do KPiR."
                ),
                wraplength=680,
                justify="left",
                foreground="#444",
            ).pack(fill="x", pady=8, padx=4)
        self._swap(outer)

    def show_costs(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Koszty", back=self._back_for("costs"))
        body = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        body.pack(fill="both", expand=True)

        form = ttk.LabelFrame(body, text="Nowy koszt", padding=10)
        form.pack(fill="x")
        fields: dict[str, tk.Variable] = {
            "issue_date": tk.StringVar(value=date.today().isoformat()),
            "event_date": tk.StringVar(value=date.today().isoformat()),
            "document_number": tk.StringVar(),
            "seller": tk.StringVar(),
            "description": tk.StringVar(),
            "category": tk.StringVar(value="inne"),
            "amount_gross": tk.StringVar(value="0"),
            "currency": tk.StringVar(value="PLN"),
            "kpir_column": tk.StringVar(value=KPIR_COLUMN_LABELS["other_expenses"]),
            "attachment_path": tk.StringVar(),
        }
        row1 = tk.Frame(form)
        row1.pack(fill="x", pady=2)
        for lbl, key, w in [
            ("Data zakupu", "event_date", 12), ("Nr dokumentu", "document_number", 15),
            ("Sprzedawca", "seller", 20), ("Kwota", "amount_gross", 10), ("Waluta", "currency", 6),
        ]:
            ttk.Label(row1, text=lbl).pack(side="left", padx=(0, 2))
            ttk.Entry(row1, textvariable=fields[key], width=w).pack(side="left", padx=(0, 8))
        row2 = tk.Frame(form)
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Kategoria").pack(side="left")
        ttk.Combobox(row2, textvariable=fields["category"], values=DEFAULT_COST_CATEGORIES, width=22).pack(
            side="left", padx=4,
        )
        ttk.Label(row2, text="Kolumna KPiR").pack(side="left", padx=(8, 0))
        col_values = [KPIR_COLUMN_LABELS[k] for k in KPIR_COST_COLUMN_KEYS]
        ttk.Combobox(row2, textvariable=fields["kpir_column"], values=col_values, width=42).pack(
            side="left", padx=4,
        )

        def sync_kpir_column_from_category(*_: object) -> None:
            col_key = default_kpir_column(fields["category"].get())
            fields["kpir_column"].set(KPIR_COLUMN_LABELS[col_key])

        fields["category"].trace_add("write", sync_kpir_column_from_category)
        ttk.Label(row2, text="Opis").pack(side="left", padx=(8, 0))
        ttk.Entry(row2, textvariable=fields["description"], width=30).pack(side="left", padx=4)
        row3 = tk.Frame(form)
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Załącznik (PDF)").pack(side="left")
        ttk.Entry(row3, textvariable=fields["attachment_path"], width=45).pack(side="left", padx=4)

        def pick_attachment() -> None:
            path = filedialog.askopenfilename(
                parent=outer, title="Faktura kosztowa",
                filetypes=[("PDF", "*.pdf"), ("Wszystkie", "*.*")],
            )
            if path:
                fields["attachment_path"].set(path)

        ttk.Button(row3, text="Wybierz…", command=pick_attachment).pack(side="left", padx=4)

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True, pady=8)
        cols = ("date", "doc", "seller", "cat", "pln", "st")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=12, selectmode="extended")
        for cid, txt, w in [
            ("date", "Data", 90), ("doc", "Dokument", 100), ("seller", "Sprzedawca", 140),
            ("cat", "Kategoria", 120), ("pln", "PLN", 70), ("st", "KPiR", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for c in list_costs():
                st = COST_KPIR_STATUS_LABELS.get(c.kpir_status, c.kpir_status)
                tree.insert("", "end", iid=c.id, values=(
                    c.event_date[:10], c.document_number, c.seller,
                    c.category, f"{c.amount_pln:.2f}", st,
                ))

        def _kpir_column_key(value: str, category: str) -> str:
            raw = (value or "").strip()
            key = KPIR_COLUMN_BY_LABEL.get(raw, raw)
            if key in KPIR_COLUMN_LABELS:
                return key
            return default_kpir_column(category)

        def add_cost() -> None:
            cat = fields["category"].get()
            col = _kpir_column_key(fields["kpir_column"].get(), cat)
            try:
                amount = float(fields["amount_gross"].get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Koszty", "Nieprawidłowa kwota.", parent=outer)
                return
            create_cost(
                issue_date=fields["issue_date"].get(),
                event_date=fields["event_date"].get(),
                document_number=fields["document_number"].get(),
                seller=fields["seller"].get(),
                description=fields["description"].get(),
                category=cat,
                amount_gross=amount,
                currency=fields["currency"].get(),
                kpir_column=col,
                attachment_path=fields["attachment_path"].get().strip(),
            )
            refresh()
            show_toast(outer, "Koszt dodany", bg="#2e7d32")

        def book_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            try:
                book_cost_to_kpir(sel[0])
                refresh()
                show_toast(outer, "Koszt zaksięgowany w KPiR", bg="#2e7d32")
            except Exception as exc:
                messagebox.showerror("KPiR", str(exc), parent=outer)

        def remove_selected() -> None:
            sel = list(tree.selection())
            if not sel:
                messagebox.showinfo(
                    "Koszty",
                    "Zaznacz jedną lub więcej pozycji (Ctrl+klik, Shift+klik).",
                    parent=outer,
                )
                return
            labels = []
            posted = 0
            for item_id in sel:
                row = tree.item(item_id)
                vals = row.get("values") or []
                labels.append(str(vals[1] or vals[0] or item_id))
                cost = get_cost(item_id)
                if cost and cost.kpir_status == "posted":
                    posted += 1
            preview = "\n".join(f"  • {n}" for n in labels[:12])
            if len(labels) > 12:
                preview += f"\n  … i {len(labels) - 12} więcej"
            extra = ""
            if posted:
                extra = (
                    f"\n\n{posted} pozycji jest zaksięgowanych w KPiR — "
                    "powiązane wpisy zostaną anulowane."
                )
            if not messagebox.askyesno(
                "Usuń koszty",
                f"Usunąć {len(sel)} kosztów?\n\n{preview}{extra}\n\nTej operacji nie można cofnąć.",
                parent=outer,
            ):
                return
            deleted, errors = delete_costs_many(sel)
            refresh()
            show_toast(outer, f"Usunięto {deleted} kosztów", bg="#2e7d32")
            if errors:
                messagebox.showwarning("Koszty", "\n".join(errors[:8]), parent=outer)

        list_btns = tk.Frame(body, bg=_BG)
        list_btns.pack(fill="x", pady=(0, 4))
        ttk.Label(
            list_btns,
            text="Lista: Ctrl+klik lub Shift+klik — zaznacz wiele pozycji.",
            foreground="#666",
        ).pack(side="left")
        ttk.Button(list_btns, text="Usuń zaznaczone", command=remove_selected).pack(side="right")

        btns = tk.Frame(form)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Dodaj koszt", command=add_cost).pack(side="left", padx=4)
        ttk.Button(btns, text="Zaksięguj zaznaczony", command=book_selected).pack(side="left", padx=4)

        import_frame = ttk.LabelFrame(body, text="Import prowizji CSV (Stripe / PayPal / Shopify)", padding=10)
        import_frame.pack(fill="x", pady=(0, 8))
        provider_var = tk.StringVar(value="stripe")
        book_var = tk.BooleanVar(value=False)
        monthly_var = tk.BooleanVar(value=True)
        import_status = tk.StringVar(value="Wybierz plik CSV z raportu płatności.")
        import_tip = tk.StringVar(value=FEE_IMPORT_TIPS["stripe"])

        tip_box = tk.Frame(import_frame, bg="#e8f4fd", padx=8, pady=6)
        tip_box.pack(fill="x", pady=(0, 8))
        tk.Label(
            tip_box, textvariable=import_tip, bg="#e8f4fd", fg="#1565c0",
            font=("Segoe UI", 9), justify="left", wraplength=640,
        ).pack(anchor="w")
        tk.Label(
            tip_box, text=FEE_IMPORT_MONTHLY_HINT, bg="#e8f4fd", fg="#37474f",
            font=("Segoe UI", 8), justify="left", wraplength=640,
        ).pack(anchor="w", pady=(4, 0))

        row_imp = tk.Frame(import_frame)
        row_imp.pack(fill="x")
        ttk.Label(row_imp, text="Dostawca:").pack(side="left")
        provider_combo = ttk.Combobox(
            row_imp, textvariable=provider_var, width=14,
            values=["auto", "stripe", "paypal", "shopify"],
        )
        provider_combo.pack(side="left", padx=4)

        def _update_import_tip(*_args: object) -> None:
            key = provider_var.get() or "auto"
            import_tip.set(FEE_IMPORT_TIPS.get(key, FEE_IMPORT_TIPS["auto"]))

        provider_var.trace_add("write", _update_import_tip)
        _update_import_tip()

        ttk.Checkbutton(
            row_imp, text="Zbiorczo per miesiąc (zalecane)", variable=monthly_var,
        ).pack(side="left", padx=8)
        ttk.Checkbutton(row_imp, text="Od razu zaksięguj w KPiR", variable=book_var).pack(side="left", padx=4)

        def do_import() -> None:
            path = filedialog.askopenfilename(
                parent=outer,
                title="Import prowizji CSV",
                filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
            )
            if not path:
                return
            try:
                result = import_fee_csv(
                    path,
                    provider_var.get(),  # type: ignore[arg-type]
                    book=book_var.get(),
                    aggregate_monthly=monthly_var.get(),
                )
                msg = (
                    f"Zaimportowano: {result.created_costs} kosztów, "
                    f"zaksięgowano: {result.booked}, "
                    f"pominięto duplikaty: {result.skipped_duplicates}"
                )
                if result.errors:
                    msg += f"\nBłędy: {len(result.errors)}"
                import_status.set(msg)
                refresh()
                show_toast(outer, f"Dodano {result.created_costs} kosztów prowizji", bg="#2e7d32")
                if result.errors:
                    messagebox.showwarning(
                        "Import prowizji",
                        "\n".join(result.errors[:8]),
                        parent=outer,
                    )
            except Exception as exc:
                messagebox.showerror("Import prowizji", str(exc), parent=outer)

        def preview_import() -> None:
            path = filedialog.askopenfilename(
                parent=outer,
                title="Podgląd CSV prowizji",
                filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
            )
            if not path:
                return
            try:
                rows = parse_fee_csv(path, provider_var.get())  # type: ignore[arg-type]
                total = sum(r.amount for r in rows)
                import_status.set(
                    f"Podgląd: {len(rows)} prowizji, suma {total:.2f} "
                    f"({rows[0].provider if rows else '?'})",
                )
            except Exception as exc:
                messagebox.showerror("Podgląd", str(exc), parent=outer)

        imp_btns = tk.Frame(import_frame)
        imp_btns.pack(fill="x", pady=6)
        ttk.Button(imp_btns, text="Wybierz CSV i importuj", command=do_import).pack(side="left", padx=4)
        ttk.Button(imp_btns, text="Podgląd pliku", command=preview_import).pack(side="left", padx=4)
        ttk.Label(import_frame, textvariable=import_status, foreground="#444", wraplength=600).pack(anchor="w")

        bank_frame = ttk.LabelFrame(body, text="Import wyciągu bankowego (CSV)", padding=10)
        bank_frame.pack(fill="x", pady=(0, 8))
        bank_status = tk.StringVar(value="mBank / PKO / ING / ogólny CSV z kolumną kwoty i daty.")
        bank_book_var = tk.BooleanVar(value=False)
        tk.Label(
            bank_frame, textvariable=bank_status, fg="#444", wraplength=600, justify="left",
        ).pack(anchor="w")
        ttk.Checkbutton(bank_frame, text="Od razu zaksięguj w KPiR", variable=bank_book_var).pack(anchor="w", pady=4)

        def do_bank_import() -> None:
            path = filedialog.askopenfilename(
                parent=outer, title="Import wyciągu bankowego",
                filetypes=[("CSV", "*.csv"), ("Wszystkie", "*.*")],
            )
            if not path:
                return
            try:
                result = import_bank_csv(path, "auto", book=bank_book_var.get())
                bank_status.set(
                    f"Bank: {result.created_costs} kosztów, pominięto {result.skipped}, "
                    f"rozpoznano {result.parsed} wierszy",
                )
                refresh()
                show_toast(outer, f"Dodano {result.created_costs} kosztów z banku", bg="#2e7d32")
            except Exception as exc:
                messagebox.showerror("Import banku", str(exc), parent=outer)

        ttk.Button(bank_frame, text="Wybierz CSV banku", command=do_bank_import).pack(anchor="w", pady=4)

        refresh()
        self._swap(outer)

    def show_recurring(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Koszty cykliczne")
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        due = due_recurring_items()
        if due:
            tk.Label(body, text=f"Do dodania: {len(due)} kosztów cyklicznych", bg="#fff3e0", fg="#e65100").pack(
                fill="x", pady=4,
            )

        form = ttk.LabelFrame(body, text="Dodaj koszt cykliczny", padding=10)
        form.pack(fill="x", pady=(0, 8))
        rec_fields: dict[str, tk.Variable] = {
            "name": tk.StringVar(),
            "vendor": tk.StringVar(),
            "amount": tk.StringVar(value="0"),
            "currency": tk.StringVar(value="PLN"),
            "frequency": tk.StringVar(value="monthly"),
            "day_of_month": tk.StringVar(value="1"),
            "category": tk.StringVar(value="inne"),
        }
        presets = {
            "": {},
            "Abonament Shopify": {
                "name": "Abonament Shopify", "vendor": "Shopify", "amount": "120",
                "currency": "EUR", "category": "abonament Shopify", "day_of_month": "1",
            },
            "Aplikacje Shopify": {
                "name": "Aplikacje Shopify", "vendor": "Shopify", "amount": "30",
                "currency": "USD", "category": "aplikacje Shopify", "day_of_month": "1",
            },
            "Domena": {
                "name": "Domena", "vendor": "OVH", "amount": "50",
                "currency": "PLN", "category": "domena", "day_of_month": "15",
            },
            "Hosting": {
                "name": "Hosting", "vendor": "OVH", "amount": "40",
                "currency": "PLN", "category": "hosting", "day_of_month": "15",
            },
        }

        row_a = tk.Frame(form)
        row_a.pack(fill="x", pady=2)
        ttk.Label(row_a, text="Szablon:").pack(side="left")
        preset_var = tk.StringVar(value="")
        preset_combo = ttk.Combobox(row_a, textvariable=preset_var, width=22, values=list(presets.keys()))
        preset_combo.pack(side="left", padx=4)

        def apply_preset(_e: tk.Event | None = None) -> None:
            data = presets.get(preset_var.get()) or {}
            for key, var in rec_fields.items():
                if key in data:
                    var.set(str(data[key]))

        preset_combo.bind("<<ComboboxSelected>>", apply_preset)

        row_b = tk.Frame(form)
        row_b.pack(fill="x", pady=2)
        for lbl, key, w in [
            ("Nazwa", "name", 22), ("Dostawca", "vendor", 16),
            ("Kwota", "amount", 8), ("Waluta", "currency", 6),
        ]:
            ttk.Label(row_b, text=lbl).pack(side="left", padx=(0, 2))
            ttk.Entry(row_b, textvariable=rec_fields[key], width=w).pack(side="left", padx=(0, 8))

        row_c = tk.Frame(form)
        row_c.pack(fill="x", pady=2)
        ttk.Label(row_c, text="Częstotliwość").pack(side="left")
        ttk.Combobox(
            row_c, textvariable=rec_fields["frequency"], width=10,
            values=["monthly", "yearly"],
        ).pack(side="left", padx=4)
        ttk.Label(row_c, text="Dzień miesiąca").pack(side="left", padx=(8, 0))
        ttk.Spinbox(row_c, from_=1, to=28, textvariable=rec_fields["day_of_month"], width=4).pack(side="left", padx=4)
        ttk.Label(row_c, text="Kategoria").pack(side="left", padx=(8, 0))
        ttk.Combobox(
            row_c, textvariable=rec_fields["category"], width=18,
            values=DEFAULT_COST_CATEGORIES,
        ).pack(side="left", padx=4)

        tree_frame = ttk.Frame(body)
        tree_frame.pack(fill="both", expand=True)
        cols = ("name", "vendor", "amount", "freq", "day", "active", "last")
        tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", height=10, selectmode="extended",
        )
        for cid, txt, w in [
            ("name", "Nazwa", 140), ("vendor", "Dostawca", 100), ("amount", "Kwota", 90),
            ("freq", "Częstotliwość", 80), ("day", "Dzień", 45),
            ("active", "Aktywny", 55), ("last", "Ostatnio", 85),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for r in list_recurring():
                tree.insert("", "end", iid=r.id, values=(
                    r.name, r.vendor, f"{r.amount:.2f} {r.currency}",
                    "miesięcznie" if r.frequency == "monthly" else "rocznie",
                    r.day_of_month,
                    "tak" if r.active else "nie",
                    r.last_generated[:10] if r.last_generated else "—",
                ))

        def add_recurring() -> None:
            name = rec_fields["name"].get().strip()
            if not name:
                messagebox.showerror("Koszty cykliczne", "Podaj nazwę kosztu.", parent=outer)
                return
            try:
                amount = float(rec_fields["amount"].get().replace(",", "."))
            except ValueError:
                messagebox.showerror("Koszty cykliczne", "Nieprawidłowa kwota.", parent=outer)
                return
            try:
                day = int(rec_fields["day_of_month"].get())
            except ValueError:
                day = 1
            cat = rec_fields["category"].get()
            create_recurring(
                name=name,
                vendor=rec_fields["vendor"].get().strip(),
                amount=amount,
                currency=rec_fields["currency"].get().strip().upper() or "PLN",
                frequency=rec_fields["frequency"].get(),
                day_of_month=max(1, min(28, day)),
                category=cat,
                kpir_column=default_kpir_column(cat),
            )
            refresh()
            show_toast(outer, f"Dodano: {name}", bg="#2e7d32")
            rec_fields["name"].set("")
            preset_var.set("")

        def generate_due() -> None:
            items = due_recurring_items()
            if not items:
                messagebox.showinfo("Koszty cykliczne", "Brak zaległych kosztów do wygenerowania.", parent=outer)
                return
            for item in items:
                generate_draft_cost_from_recurring(item)
            show_toast(outer, f"Utworzono {len(items)} kosztów roboczych", bg="#2e7d32")
            refresh()

        def remove_selected() -> None:
            sel = tree.selection()
            if not sel:
                messagebox.showinfo(
                    "Koszty cykliczne",
                    "Zaznacz jedną lub więcej pozycji (Ctrl+klik, Shift+klik).",
                    parent=outer,
                )
                return
            names = []
            for item_id in sel:
                row = tree.item(item_id)
                names.append(str((row.get("values") or ["?"])[0]))
            preview = "\n".join(f"  • {n}" for n in names[:12])
            if len(names) > 12:
                preview += f"\n  … i {len(names) - 12} więcej"
            if not messagebox.askyesno(
                "Usuń koszty cykliczne",
                f"Usunąć {len(sel)} pozycji?\n\n{preview}\n\nTej operacji nie można cofnąć.",
                parent=outer,
            ):
                return
            n = delete_recurring_many(list(sel))
            refresh()
            show_toast(outer, f"Usunięto {n} kosztów cyklicznych", bg="#2e7d32")

        form_btns = tk.Frame(form)
        form_btns.pack(fill="x", pady=(6, 0))
        ttk.Button(form_btns, text="Dodaj koszt cykliczny", command=add_recurring).pack(side="left")

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x", pady=4)
        ttk.Label(
            btns,
            text="Lista: Ctrl+klik lub Shift+klik — zaznacz wiele. „Generuj zaległe” tworzy robocze koszty w module Koszty.",
            foreground="#666",
        ).pack(side="left")
        ttk.Button(btns, text="Generuj zaległe koszty", command=generate_due).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Usuń zaznaczone", command=remove_selected).pack(side="right")
        refresh()
        self._swap(outer)

    def show_month_summary(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Podsumowanie miesiąca")
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        period = tk.Frame(outer, bg=_BG, padx=16)
        period.pack(fill="x")
        self._period_bar(period, y_var, m_var).pack(side="left")
        txt = tk.Text(outer, height=18, width=70, font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=16, pady=8)

        def refresh() -> None:
            summary = monthly_summary(y_var.get(), m_var.get())
            lines = [
                f"Okres: {y_var.get()}-{m_var.get():02d}",
                f"Przychody razem: {summary['revenue_total']:.2f} PLN",
                f"  — towary/usługi: {summary['totals']['revenue_goods']:.2f}",
                f"  — pozostałe: {summary['totals']['revenue_other']:.2f}",
                f"Koszty razem: {summary['costs_total']:.2f} PLN",
                f"  — materiały: {summary['totals']['purchase_goods']:.2f}",
                f"  — uboczne: {summary['totals']['purchase_side']:.2f}",
                f"  — pozostałe: {summary['totals']['other_expenses']:.2f}",
                f"Dochód / strata: {summary['income']:.2f} PLN",
                "",
                f"Zamówienia Shopify: {summary['shopify_orders']}",
                f"Faktury: {summary['invoices']}",
                f"Koszty: {summary['costs']}",
                f"Sprzedaż PL: {summary['sales_poland']:.2f}",
                f"Sprzedaż UE B2C: {summary['sales_eu_b2c']:.2f}",
                f"Sprzedaż poza UE: {summary['sales_non_eu']:.2f}",
                f"Waluty obce: {summary['sales_foreign_currency']:.2f}",
                f"Miesiąc: {'zamknięty' if summary['month_closed'] else 'otwarty'}",
                "",
                "Alerty:",
            ]
            lines.extend(f"  • {a}" for a in summary["alerts"] or ["  (brak)"])
            margin = gross_margin_summary(year=y_var.get(), month=m_var.get())
            lines.extend([
                "",
                f"Marża brutto: {margin['gross_profit']:.2f} PLN ({margin['gross_margin_percent']:.1f}%)",
            ])
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(lines))
            txt.configure(state="disabled")

        btns = tk.Frame(outer, bg=_BG)
        btns.pack(fill="x", padx=16, pady=8)
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(
            btns, text="Zamknij miesiąc",
            command=lambda: self._close_month_with_checklist(outer, y_var.get(), m_var.get(), refresh),
        ).pack(side="left", padx=4)
        ttk.Button(btns, text="Otwórz miesiąc", command=lambda: (
            reopen_month(y_var.get(), m_var.get()), show_toast(outer, "Miesiąc otwarty"), refresh(),
        )).pack(side="left", padx=4)
        refresh()
        self._swap(outer)

    def show_year_summary(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Rok podatkowy")
        y_var = tk.IntVar(value=date.today().year)
        period = tk.Frame(outer, bg=_BG, padx=16)
        period.pack(fill="x")
        ttk.Label(period, text="Rok:").pack(side="left")
        ttk.Spinbox(period, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        chart = tk.Canvas(outer, bg="#fff", height=190, highlightthickness=1, highlightbackground="#ddd")
        chart.pack(fill="x", padx=16, pady=8)
        txt = tk.Text(outer, height=16, width=72, font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=16, pady=8)

        def refresh() -> None:
            y = y_var.get()
            summary = yearly_summary(y)
            chart_data = [
                (f"{m:02d}", summary["by_month"][m]["income"]) for m in range(1, 13)
            ]
            _draw_bar_chart(chart, chart_data)
            lines = [
                f"Rok: {y}",
                f"Przychody: {summary['revenue_total']:.2f} PLN",
                f"Koszty (uproszczone): {summary['costs_total']:.2f} PLN",
                f"Dochód uproszczony: {summary['income']:.2f} PLN",
            ]
            off = summary.get("official_income") or {}
            if off:
                lines.extend([
                    "",
                    "Dochód urzędowy (remanent + kol. 12–16, Dz.U. 2025 poz. 1299):",
                    f"  {off.get('formula', '')}",
                    f"  = {off.get('income', 0):.2f} PLN",
                ])
            lines.extend(["", "Miesięcznie (przychód / koszt / dochód):"])
            for m in range(1, 13):
                d = summary["by_month"][m]
                lines.append(f"  {m:02d}: {d['revenue']:.2f} / {d['costs']:.2f} / {d['income']:.2f}")
            lines.append("\nSprzedaż wg kraju:")
            for country, amt in sorted(summary["by_country"].items(), key=lambda x: -x[1]):
                lines.append(f"  {country}: {amt:.2f} PLN")
            lines.append("\nKoszty wg kategorii:")
            for cat, amt in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
                lines.append(f"  {cat}: {amt:.2f} PLN")
            try:
                from Komponenty._shared.compliance_ui import compliance_monitors

                lines.append("\nCompliance:")
                for row in compliance_monitors(y):
                    lines.append(f"  {row['title']}: {row['message']}")
            except ImportError:
                pass
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(lines))
            txt.configure(state="disabled")

        ttk.Button(period, text="Odśwież", command=refresh).pack(side="left", padx=8)
        refresh()
        self._swap(outer)

    def show_transition_year(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Rok przejściowy DNR → JDG")
        settings = load_settings()
        y_var = tk.IntVar(value=date.today().year)
        top = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        top.pack(fill="x")
        ttk.Label(top, text="Rok:").pack(side="left")
        ttk.Spinbox(top, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        txt = tk.Text(outer, height=24, width=78, font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=16, pady=8)

        def refresh() -> None:
            from .transition_year_report import build_transition_year_report

            report = build_transition_year_report(y_var.get(), settings)
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(report.lines))
            txt.configure(state="disabled")

        ttk.Button(top, text="Odśwież", command=refresh).pack(side="left", padx=8)
        refresh()
        self._swap(outer)

    def show_exports(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Eksport księgowy")
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        y_var = tk.IntVar(value=date.today().year)
        m_var = tk.IntVar(value=date.today().month)
        row = tk.Frame(body, bg=_BG)
        row.pack(fill="x")
        ttk.Label(row, text="Rok").pack(side="left")
        ttk.Spinbox(row, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        ttk.Label(row, text="Miesiąc").pack(side="left")
        ttk.Spinbox(row, from_=1, to=12, textvariable=m_var, width=4).pack(side="left", padx=4)

        result_row = tk.Frame(body, bg=_BG)
        result_row.pack(anchor="w", pady=8)
        saved_prefix = tk.Label(result_row, text="", bg=_BG, fg="#2e7d32", font=("Segoe UI", 10))
        saved_link = tk.Label(
            result_row,
            text="",
            bg=_BG,
            fg="#2e7d32",
            cursor="hand2",
            font=("Segoe UI", 10, "underline"),
        )
        saved_prefix.pack(side="left")
        saved_link.pack(side="left")
        last_export_path: list[Path | None] = [None]

        def _show_saved(path: Path) -> None:
            last_export_path[0] = path
            saved_prefix.config(text="Zapisano: ")
            saved_link.config(text=str(path))

        def _open_saved(_evt: object = None) -> None:
            path = last_export_path[0]
            if path is None:
                return
            if not path.exists():
                messagebox.showwarning("Eksport", f"Ścieżka nie istnieje:\n{path}", parent=outer)
                return
            try:
                if sys.platform == "win32":
                    os.startfile(path)  # noqa: S606
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(path)], check=False)
                else:
                    subprocess.run(["xdg-open", str(path)], check=False)
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        saved_link.bind("<Button-1>", _open_saved)

        def run_export(fn) -> None:
            try:
                path = Path(fn(y_var.get(), m_var.get()))
                _show_saved(path)
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        exports = [
            ("Eksport KPiR CSV", export_kpir_csv),
            ("Eksport KPiR XLSX", export_kpir_xlsx),
            ("Eksport KPiR PDF", export_kpir_pdf),
            ("Eksport dla księgowego CSV", export_accountant_csv),
            ("Eksport JPK_PKPIR XML", export_jpk_pkpir_xml),
            ("Pakiet dla księgowego (folder)", export_accountant_package),
            ("Eksport roczny CSV", lambda y, m: export_kpir_csv(y, None)),
            ("Eksport roczny XLSX", lambda y, m: export_kpir_xlsx(y, None)),
        ]
        for lbl, fn in exports:
            ttk.Button(body, text=lbl, command=lambda f=fn: run_export(f), width=36).pack(anchor="w", pady=3)

        def open_folder() -> None:
            path = last_export_path[0]
            if path is None:
                messagebox.showinfo("Eksport", "Najpierw wygeneruj pakiet księgowy.", parent=outer)
                return
            target = path if path.is_dir() else path.parent
            try:
                if sys.platform == "win32":
                    os.startfile(target)  # noqa: S606
                else:
                    subprocess.run(["xdg-open", str(target)], check=False)
            except Exception as exc:
                messagebox.showerror("Eksport", str(exc), parent=outer)

        ttk.Button(body, text="Otwórz ostatni pakiet księgowy", command=open_folder, width=36).pack(anchor="w", pady=3)
        ttk.Label(body, text=JPK_PKPIR_PLACEHOLDER, foreground="#666").pack(anchor="w", pady=4)
        ttk.Label(body, text=FX_DIFF_PLACEHOLDER, foreground="#666").pack(anchor="w")
        self._swap(outer)

    def show_settings(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Ustawienia księgowości", back=self._back_for("settings"))
        settings = load_settings()
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        from Komponenty._shared.zus_stages import ZUS_STAGES, zus_stage_summary
        from .zus_service import apply_auto_zus, is_jdg_mode, resolve_prior_year_income, zus_stage_progress

        display_accounting_mode = resolved_accounting_mode(settings)
        mode_var = tk.StringVar(value=option_label(ACCOUNTING_MODE_OPTIONS, display_accounting_mode))
        tax_var = tk.StringVar(value=option_label(TAX_FORM_OPTIONS, settings.tax_form))
        vat_var = tk.StringVar(value=option_label(VAT_STATUS_OPTIONS, settings.vat_status))
        grouping_var = tk.StringVar(value=option_label(SALES_GROUPING_OPTIONS, settings.sales_grouping))
        zus_var = tk.StringVar(value=str(settings.zus_monthly))
        health_var = tk.StringVar(value=str(settings.health_insurance_monthly))
        from Komponenty.dnr.limit_sync import canonical_quarterly_limit

        dnr_var = tk.StringVar(value=str(canonical_quarterly_limit()))
        nip_var = tk.StringVar(value=settings.seller_nip)
        name_var = tk.StringVar(value=settings.seller_name)
        cost_method_var = tk.StringVar(value=option_label(COST_METHOD_OPTIONS, settings.cost_method))
        activity_var = tk.StringVar(value=settings.activity_description)
        book_opened_var = tk.StringVar(value=settings.book_opened_at or settings.jdg_registered_at)
        zus_stage_var = tk.StringVar(
            value=next(
                (lbl for k, lbl in ZUS_STAGES if k == settings.zus_stage),
                ZUS_STAGES[0][1],
            ),
        )
        sick_var = tk.BooleanVar(value=settings.voluntary_sickness)
        manual_var = tk.BooleanVar(value=settings.zus_manual_override)
        jdg_reg_var = tk.StringVar(value=settings.jdg_registered_at)
        maly_income_var = tk.StringVar(
            value="" if not settings.maly_zus_prior_year_income else str(settings.maly_zus_prior_year_income),
        )
        maly_days_var = tk.StringVar(value=str(settings.maly_zus_prior_year_activity_days or 365))
        maly_cycle_var = tk.StringVar(value=settings.maly_zus_cycle_start)
        zus_preview_var = tk.StringVar(value="")
        zus_progress_var = tk.StringVar(value="")
        zus_by_label = {lbl: k for k, lbl in ZUS_STAGES}
        prev_zus_stage = settings.zus_stage

        prev_zus_stage = settings.zus_stage
        mode_options = (
            [label for k, label in ACCOUNTING_MODE_OPTIONS if k != "dnr"]
            if settings.jdg_registered_at
            else [label for _, label in ACCOUNTING_MODE_OPTIONS]
        )
        if settings.jdg_registered_at and settings.accounting_mode == "dnr":
            tk.Label(
                body,
                text="Tryb DNR jest w osobnym module — wybrano JDG — KPiR zgodnie z rejestracją.",
                fg="#1565c0",
                font=("Segoe UI", 8, "bold"),
            ).grid(row=0, column=2, sticky="w", padx=8)
        elif display_accounting_mode != settings.accounting_mode:
            try:
                from Komponenty.dokumentysprzedazy.constants import business_mode_display
                from Komponenty.dokumentysprzedazy.storage import load_settings as load_inv_settings

                inv_mode = load_inv_settings().seller.business_mode
                tk.Label(
                    body,
                    text=f"Zgodnie z fakturami ({business_mode_display(inv_mode)}) — wybrano JDG — KPiR.",
                    fg="#1565c0",
                    font=("Segoe UI", 8, "bold"),
                ).grid(row=0, column=2, sticky="w", padx=8)
            except ImportError:
                pass

        ttk.Label(body, text="Tryb księgowości:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            body, textvariable=mode_var,
            values=mode_options, width=28,
        ).grid(row=0, column=1, sticky="w")

        ttk.Label(body, text="Forma opodatkowania:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(
            body, textvariable=tax_var,
            values=[label for _, label in TAX_FORM_OPTIONS], width=28,
        ).grid(row=1, column=1, sticky="w")

        ttk.Label(body, text="Status VAT (księgowanie Shopify):").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(
            body, textvariable=vat_var,
            values=[label for _, label in VAT_STATUS_OPTIONS], width=28, state="readonly",
        ).grid(row=2, column=1, sticky="w")
        ttk.Label(
            body,
            text="Czynny VAT → przychód netto z zamówień; zwolnienie → brutto.",
            font=("Segoe UI", 8),
        ).grid(row=2, column=2, sticky="w", padx=8)

        ttk.Label(body, text="Grupowanie sprzedaży:").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            body, textvariable=grouping_var,
            values=[label for _, label in SALES_GROUPING_OPTIONS], width=28,
        ).grid(row=3, column=1, sticky="w")

        zus_frame = ttk.LabelFrame(body, text=" ZUS (tylko JDG) ", padding=8)
        zus_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        ttk.Label(zus_frame, text="Etap ZUS:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Combobox(
            zus_frame,
            textvariable=zus_stage_var,
            values=[lbl for _, lbl in ZUS_STAGES],
            width=42,
            state="readonly",
        ).grid(row=0, column=1, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(zus_frame, text="Dobrowolna chorobowa", variable=sick_var).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=2,
        )
        ttk.Checkbutton(
            zus_frame, text="Kwoty ręczne (wyłącz auto z tax_config 2026)", variable=manual_var,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(zus_frame, text="ZUS społeczny (PLN/mies.):").grid(row=3, column=0, sticky="w", pady=2)
        zus_entry = ttk.Entry(zus_frame, textvariable=zus_var, width=12)
        zus_entry.grid(row=3, column=1, sticky="w", pady=2)
        ttk.Label(zus_frame, text="Zdrowotna min. (PLN/mies.):").grid(row=4, column=0, sticky="w", pady=2)
        health_entry = ttk.Entry(zus_frame, textvariable=health_var, width=12)
        health_entry.grid(row=4, column=1, sticky="w", pady=2)
        ttk.Label(
            zus_frame, text="(w PIT: max(minimum, 9% dochodu przy skali)", foreground="#666",
        ).grid(row=4, column=2, sticky="w", padx=8)
        ttk.Label(zus_frame, textvariable=zus_preview_var, foreground="#1565c0", wraplength=480).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(4, 0),
        )
        ttk.Label(zus_frame, textvariable=zus_progress_var, foreground="#2e7d32", wraplength=480).grid(
            row=6, column=0, columnspan=3, sticky="w", pady=(2, 0),
        )
        ttk.Label(zus_frame, text="Data rejestracji JDG:").grid(row=7, column=0, sticky="w", pady=2)
        ttk.Entry(zus_frame, textvariable=jdg_reg_var, width=14).grid(row=7, column=1, sticky="w", pady=2)
        ttk.Label(zus_frame, text="(YYYY-MM-DD — start licznika ZUS)", foreground="#666").grid(
            row=7, column=2, sticky="w", padx=8,
        )
        maly_income_lbl = ttk.Label(zus_frame, text="Dochód poprzedni rok (Mały ZUS Plus):")
        maly_income_lbl.grid(row=8, column=0, sticky="w", pady=2)
        maly_income_entry = ttk.Entry(zus_frame, textvariable=maly_income_var, width=12)
        maly_income_entry.grid(row=8, column=1, sticky="w", pady=2)
        ttk.Label(
            zus_frame, text="(puste = auto z KPiR)", foreground="#666",
        ).grid(row=8, column=2, sticky="w", padx=8)
        maly_days_lbl = ttk.Label(zus_frame, text="Dni działalności w poprzednim roku:")
        maly_days_lbl.grid(row=9, column=0, sticky="w", pady=2)
        maly_days_entry = ttk.Entry(zus_frame, textvariable=maly_days_var, width=6)
        maly_days_entry.grid(row=9, column=1, sticky="w", pady=2)

        def _tax_form_key() -> str:
            return option_key(TAX_FORM_OPTIONS, tax_var.get())

        def _refresh_zus_ui(*_: object) -> None:
            mode = option_key(ACCOUNTING_MODE_OPTIONS, mode_var.get())
            if mode not in ("jdg_kpir", "jdg_ryczalt"):
                zus_frame.grid_remove()
                return
            zus_frame.grid()
            stage = zus_by_label.get(zus_stage_var.get(), "ulga_na_start")
            show_maly = stage == "maly_zus_plus"
            for w in (maly_income_lbl, maly_income_entry, maly_days_lbl, maly_days_entry):
                w.grid() if show_maly else w.grid_remove()
            prior_income = 0.0
            try:
                raw_inc = maly_income_var.get().replace(",", ".").strip()
                prior_income = float(raw_inc) if raw_inc else resolve_prior_year_income(settings)
            except ValueError:
                prior_income = resolve_prior_year_income(settings)
            if not manual_var.get():
                summary = zus_stage_summary(
                    zus_stage=stage,
                    tax_form=_tax_form_key(),
                    voluntary_sickness=sick_var.get(),
                    prior_year_income=prior_income,
                )
                zus_var.set(f"{summary['social_monthly']:.2f}")
                health_var.set(f"{summary['health_minimum_monthly']:.2f}")
                extra = ""
                if stage == "pelny" and summary.get("fp_fs_monthly"):
                    extra = f", FP/FS {summary['fp_fs_monthly']:.2f} zł"
                elif stage == "maly_zus_plus" and summary.get("maly_zus_base_monthly"):
                    extra = f", podstawa {summary['maly_zus_base_monthly']:.2f} zł"
                zus_preview_var.set(
                    f"Auto: {summary['label']} → społeczne {summary['social_monthly']:.2f} zł"
                    f"{extra}, zdrowotna min. {summary['health_minimum_monthly']:.2f} zł/mies."
                )
                zus_entry.state(["disabled"])
                health_entry.state(["disabled"])
            else:
                zus_preview_var.set("Tryb ręczny — wpisz kwoty samodzielnie.")
                zus_entry.state(["!disabled"])
                health_entry.state(["!disabled"])
            tmp = settings
            tmp.zus_stage = stage
            tmp.jdg_registered_at = jdg_reg_var.get().strip()
            try:
                tmp.maly_zus_prior_year_income = float(maly_income_var.get().replace(",", ".") or 0)
            except ValueError:
                tmp.maly_zus_prior_year_income = 0.0
            try:
                tmp.maly_zus_prior_year_activity_days = int(maly_days_var.get() or 365)
            except ValueError:
                tmp.maly_zus_prior_year_activity_days = 365
            tmp.zus_stage_started_at = settings.zus_stage_started_at or settings.jdg_registered_at
            zprog = zus_stage_progress(tmp)
            zus_progress_var.set(str(zprog.get("message") or ""))

        for var in (mode_var, tax_var, zus_stage_var):
            var.trace_add("write", _refresh_zus_ui)
        sick_var.trace_add("write", _refresh_zus_ui)
        manual_var.trace_add("write", _refresh_zus_ui)
        jdg_reg_var.trace_add("write", _refresh_zus_ui)
        maly_income_var.trace_add("write", _refresh_zus_ui)
        maly_days_var.trace_add("write", _refresh_zus_ui)
        _refresh_zus_ui()

        ttk.Label(body, text="Limit DNR kwartalnie (PLN):").grid(row=5, column=0, sticky="w", pady=4)
        dnr_entry = ttk.Entry(body, textvariable=dnr_var, width=12, state="readonly")
        dnr_entry.grid(row=5, column=1, sticky="w")
        ttk.Label(
            body,
            text="Edytuj w module Działalność nierejestrowana → Ustawienia (wspólny licznik).",
            font=("Segoe UI", 8),
        ).grid(row=5, column=2, sticky="w", padx=8)
        ttk.Label(body, text="NIP (JPK):").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=nip_var, width=18).grid(row=6, column=1, sticky="w")
        ttk.Label(body, text="Nazwa podmiotu:").grid(row=7, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=name_var, width=36).grid(row=7, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="Metoda kosztów:").grid(row=8, column=0, sticky="w", pady=4)
        ttk.Combobox(
            body, textvariable=cost_method_var,
            values=[label for _, label in COST_METHOD_OPTIONS], width=36, state="readonly",
        ).grid(row=8, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="Rodzaj działalności (strona tytułowa PKPiR):").grid(row=9, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=activity_var, width=36).grid(row=9, column=1, columnspan=2, sticky="w")
        ttk.Label(body, text="Data otwarcia księgi:").grid(row=10, column=0, sticky="w", pady=4)
        ttk.Entry(body, textvariable=book_opened_var, width=18).grid(row=10, column=1, sticky="w")

        def save() -> None:
            new_stage = zus_by_label.get(zus_stage_var.get(), "ulga_na_start")
            mode_key = option_key(ACCOUNTING_MODE_OPTIONS, mode_var.get())
            if settings.jdg_registered_at and mode_key == "dnr":
                messagebox.showerror(
                    "Ustawienia",
                    "Po rejestracji JDG tryb DNR jest w osobnym module — wybierz JDG — KPiR.",
                    parent=outer,
                )
                return
            settings.accounting_mode = mode_key  # type: ignore[assignment]
            settings.tax_form = option_key(TAX_FORM_OPTIONS, tax_var.get())  # type: ignore[assignment]
            settings.vat_status = option_key(VAT_STATUS_OPTIONS, vat_var.get())
            settings.sales_grouping = option_key(SALES_GROUPING_OPTIONS, grouping_var.get())  # type: ignore[assignment]
            settings.zus_stage = new_stage
            settings.voluntary_sickness = sick_var.get()
            settings.zus_manual_override = manual_var.get()
            settings.jdg_registered_at = jdg_reg_var.get().strip()[:10]
            if new_stage != prev_zus_stage:
                settings.zus_stage_started_at = date.today().isoformat()
                if new_stage == "maly_zus_plus" and not settings.maly_zus_cycle_start:
                    settings.maly_zus_cycle_start = settings.zus_stage_started_at
            elif not settings.zus_stage_started_at and settings.jdg_registered_at:
                settings.zus_stage_started_at = settings.jdg_registered_at
            try:
                settings.maly_zus_prior_year_income = float(maly_income_var.get().replace(",", ".") or 0)
                settings.maly_zus_prior_year_activity_days = int(maly_days_var.get() or 365)
            except ValueError:
                pass
            try:
                if manual_var.get():
                    settings.zus_monthly = float(zus_var.get().replace(",", "."))
                    settings.health_insurance_monthly = float(health_var.get().replace(",", "."))
            except ValueError:
                pass
            settings.dnr_limit_quarterly = canonical_quarterly_limit()
            if not manual_var.get():
                apply_auto_zus(settings)
            settings.seller_nip = nip_var.get().strip()
            settings.seller_name = name_var.get().strip()
            settings.cost_method = option_key(COST_METHOD_OPTIONS, cost_method_var.get())  # type: ignore[assignment]
            settings.activity_description = activity_var.get().strip()
            settings.book_opened_at = book_opened_var.get().strip()[:10]
            save_settings(settings)
            try:
                from Komponenty._shared.accounting_mode_sync import (
                    business_mode_from_accounting,
                    persist_business_mode_both,
                )

                persist_business_mode_both(business_mode_from_accounting(mode_key))
            except ImportError:
                pass
            show_toast(outer, "Ustawienia zapisane (zsynchronizowano z fakturami)", bg="#2e7d32")

        ttk.Button(body, text="Zapisz", command=save).grid(row=11, column=0, pady=12, sticky="w")
        self._swap(outer)

    def show_calendar(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Kalendarz terminów")
        settings = load_settings()
        filt = tk.Frame(outer, bg=_BG, padx=16, pady=8)
        filt.pack(fill="x")
        year_var = tk.IntVar(value=date.today().year)
        month_var = tk.IntVar(value=0)
        ttk.Label(filt, text="Rok:").pack(side="left")
        ttk.Spinbox(filt, from_=2020, to=2035, textvariable=year_var, width=6).pack(side="left", padx=4)
        ttk.Label(filt, text="Miesiąc (0=cały rok):").pack(side="left", padx=(8, 0))
        ttk.Spinbox(filt, from_=0, to=12, textvariable=month_var, width=4).pack(side="left", padx=4)

        tree_frame = ttk.Frame(outer)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=8)
        cols = ("due", "cat", "amount", "title", "status", "desc")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=18)
        for c, h, w in (
            ("due", "Termin", 100),
            ("cat", "Kategoria", 72),
            ("amount", "Kwota", 140),
            ("title", "Zadanie", 220),
            ("status", "Status", 90),
            ("desc", "Opis", 360),
        ):
            tree.heading(c, text=h)
            tree.column(c, width=w, anchor="w")
        tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        sb.pack(side="right", fill="y")
        tree.configure(yscrollcommand=sb.set)

        summary_var = tk.StringVar(value="")
        hint = (
            "Kwoty wpłat (ZUS, zaliczka PIT) — tylko w trybie JDG, na podstawie etapu ZUS i danych KPiR."
            if settings.accounting_mode not in ("jdg_kpir", "jdg_ryczalt")
            else "Kwoty orientacyjne — weryfikuj w PUE ZUS / u księgowego przed przelewem."
        )
        ttk.Label(outer, text=hint, foreground="#666", wraplength=720).pack(anchor="w", padx=16, pady=(0, 4))
        ttk.Label(outer, textvariable=summary_var, foreground="#444").pack(anchor="w", padx=16, pady=(0, 8))

        _STATUS_LABELS = {
            "overdue": "Po terminie",
            "today": "Dziś",
            "due_soon": "Wkrótce",
            "upcoming": "Nadchodzące",
            "info": "Info",
        }
        _CAT_LABELS = {
            "pit": "PIT",
            "zus": "ZUS",
            "ceidg": "CEIDG",
        }

        def refresh() -> None:
            from Komponenty._shared.compliance_calendar import list_deadlines
            from Komponenty.dnr.migration_service import migration_overview

            mig_overview = migration_overview()
            m = month_var.get() or None
            rows = list_deadlines(
                year=year_var.get(),
                month=m,
                accounting_mode=settings.accounting_mode,
                jdg_registered_at=settings.jdg_registered_at,
                zus_stage=settings.zus_stage,
                zus_stage_started_at=settings.zus_stage_started_at,
                migration=mig_overview.get("migration") or {},
                kpir_settings=settings,
            )
            tree.delete(*tree.get_children())
            for row in rows:
                amt = row.get("amount_label") or (
                    f"{row['amount_pln']:.2f} zł" if row.get("amount_pln") is not None else "—"
                )
                tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("due_date") or "—",
                        _CAT_LABELS.get(str(row.get("category")), str(row.get("category"))),
                        amt,
                        row.get("title", ""),
                        _STATUS_LABELS.get(str(row.get("status")), str(row.get("status"))),
                        row.get("description", ""),
                    ),
                )
            overdue = sum(1 for r in rows if r.get("status") == "overdue")
            soon = sum(1 for r in rows if r.get("status") in ("today", "due_soon"))
            summary_var.set(
                f"Terminów: {len(rows)} | po terminie: {overdue} | w ciągu 7 dni: {soon}"
            )

        ttk.Button(filt, text="Odśwież", command=refresh).pack(side="left", padx=12)
        refresh()
        self._swap(outer)

    def show_pit(self) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Szacunkowy PIT")
        settings = load_settings()
        y_var = tk.IntVar(value=date.today().year)
        row = tk.Frame(outer, bg=_BG, padx=16)
        row.pack(fill="x")
        ttk.Label(row, text="Rok:").pack(side="left")
        ttk.Spinbox(row, from_=2020, to=2035, textvariable=y_var, width=6).pack(side="left", padx=4)
        txt = tk.Text(outer, height=22, width=68, font=("Consolas", 10))
        txt.pack(fill="both", expand=True, padx=16, pady=12)

        def refresh() -> None:
            est = estimate_pit(y_var.get(), settings)
            cmp_ = est["comparison"]
            lines = [
                f"Rok: {est['year']}",
                f"Etap ZUS: {settings.zus_stage}"
                + (" (auto)" if not settings.zus_manual_override else " (ręcznie)"),
                f"Przychód: {est['revenue']:.2f} PLN",
                f"Koszty: {est['costs']:.2f} PLN",
                f"Dochód: {est['income']:.2f} PLN",
            ]
            if est.get("zus_fp_fs_annual", 0) > 0:
                lines.append(
                    f"ZUS (rocznie): {est['zus_annual']:.2f} PLN "
                    f"(społeczne {est['zus_social_annual']:.2f} + FP/FS {est['zus_fp_fs_annual']:.2f})"
                )
            else:
                lines.append(f"ZUS (rocznie): {est['zus_annual']:.2f} PLN")
            lines.extend([
                f"Zdrowotna (odliczona): {est['health_annual']:.2f} PLN ({est['health_source']})",
                f"  — wyliczona: {est['health_calculated']:.2f} | minimum: {est['health_flat']:.2f}",
                f"Podstawa opodatkowania: {est['taxable_base']:.2f} PLN",
                f"Szacunkowy PIT: {est['estimated_tax']} PLN (przed zaokrągleniem: {est['estimated_tax_raw']:.2f})",
                f"Zaliczka/mies.: {est['estimated_monthly_advance']} PLN "
                f"(przed zaokrągleniem: {est['estimated_monthly_advance_raw']:.2f})",
                (
                    f"Zaliczka: brak obowiązku wpłaty (< {est.get('advance_minimum_exempt_pln', 1000):.0f} zł/rok)"
                    if not est.get("advance_payment_required")
                    else "Zaliczka: obowiązek wpłaty aktywny"
                ),
                f"Metoda: {est['details']}",
                "",
                "Porównanie form (na tych samych danych):",
                f"  Skala: {cmp_['scale_tax']} PLN (surowe {cmp_['scale_tax_raw']:.2f}) — {cmp_['scale_details']}",
                f"  Liniowy: {cmp_['linear_tax']} PLN (surowe {cmp_['linear_tax_raw']:.2f}) — {cmp_['linear_details']}",
                f"    odliczenie zdrowotnej (liniowy): {cmp_.get('linear_health_deductible', 0):.2f} PLN/rok",
                f"  Korzystniejsza: {cmp_['better_form']} (różnica {cmp_['savings']:.2f} PLN)",
            ])
            if est.get("next_advance_deadline"):
                nd = est["next_advance_deadline"]
                lines.append(f"\nNajbliższa zaliczka: {nd['due_date']} (mies. {nd['month']})")
            try:
                from .health_annual_settlement import health_annual_settlement

                ha = health_annual_settlement(y)
                lines.append(f"\nRoczna zdrowotna ({ha['form']}): {ha['message']}")
            except Exception:
                pass
            if est.get("warnings"):
                lines.append("\nUwagi:")
                lines.extend(f"  ! {w}" for w in est["warnings"])
            lines.extend(["", est["disclaimer"]])
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "\n".join(lines))
            txt.configure(state="disabled")

        ttk.Button(row, text="Przelicz", command=refresh).pack(side="left", padx=8)
        refresh()
        self._swap(outer)
