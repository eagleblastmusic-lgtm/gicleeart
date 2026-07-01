"""Ekrany PKPiR — remanent, ST, zamknięcie roku, eksport urzędowy."""

from __future__ import annotations

import os
import subprocess
import tkinter as tk
from collections.abc import Callable
from datetime import date
from tkinter import messagebox, simpledialog, ttk
from typing import TYPE_CHECKING, Any

from Komponenty._shared.toast import show_toast

from .annual_income import annual_income_breakdown
from .constants import COST_METHOD_OPTIONS, INVENTORY_KIND_LABELS, INVENTORY_VALUATION_LABELS, OFFICIAL_COLUMN_HEADERS
from .fixed_assets_service import create_fixed_asset, fixed_assets_summary, post_monthly_depreciation
from .intangible_assets_service import (
    create_intangible_asset,
    intangible_assets_summary,
    post_monthly_depreciation as post_wnip_depreciation,
)
from .internal_doc_service import (
    book_goods_receipt_to_kpir,
    create_goods_receipt_before_invoice,
    create_home_office_internal_cost,
)
from .inventory_service import (
    apply_year_side_cost_markup,
    book_inventory_to_kpir,
    complete_valuation,
    compute_purchase_side_markup_pct,
    create_inventory,
    create_zero_inventory,
    inventories_for_year,
    update_inventory,
    valuation_deadline,
    year_end_inventory_status,
)
from .kpir_compliance import kpir_compliance_monitors
from .ksef_service import list_ksef_sync_rows, set_invoice_ksef, sync_all_ksef_to_kpir
from .models import InventoryLine, InventoryRecord
from .official_export import export_official_pkpir_csv, export_official_pkpir_pdf, export_official_pkpir_xlsx
from .official_columns import entry_to_official_row
from .pkpir_annual_export import export_pkpir_annual_package
from .sales_register_service import add_sales_register_entry, book_sales_register_to_kpir, sales_register_for_month
from .storage import (
    get_inventory,
    list_fixed_assets,
    list_goods_receipts_pending,
    list_inventories,
    list_intangible_assets,
    list_mileage_log,
    list_vehicles,
    load_settings,
    save_settings,
)
from .vehicle_log_service import add_mileage_entry, create_vehicle, mileage_summary
from .validation import ValidationError
from .year_close_service import build_year_close_summary, close_year

if TYPE_CHECKING:
    from .view import KpirView

_BG = "#f4f6f9"


class KpirOfficialExtras:
    def show_inventory(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Spis z natury (remanent)", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        year_var = tk.IntVar(value=date.today().year)
        bar = tk.Frame(body, bg=_BG)
        bar.pack(fill="x")
        ttk.Label(bar, text="Rok:").pack(side="left")
        ttk.Spinbox(bar, from_=2020, to=2035, textvariable=year_var, width=6).pack(side="left", padx=4)

        tree = ttk.Treeview(body, columns=("date", "kind", "value", "status", "deadline"), show="headings", height=12)
        for cid, txt, w in [
            ("date", "Data", 90), ("kind", "Rodzaj", 160), ("value", "Wartość", 80),
            ("status", "Status", 80), ("deadline", "Termin wyceny", 100),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for inv in inventories_for_year(year_var.get()):
                tree.insert("", "end", iid=inv.id, values=(
                    inv.inventory_date,
                    INVENTORY_KIND_LABELS.get(inv.kind, inv.kind),
                    f"{inv.total_value:.2f}",
                    inv.status,
                    valuation_deadline(inv.inventory_date) if inv.status == "draft" else "",
                ))

        def add_inventory(kind: str) -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Nowy spis z natury")
            dlg.geometry("520x360")
            date_var = tk.StringVar(value=f"{year_var.get()}-12-31" if kind == "year_end" else f"{year_var.get()}-01-01")
            name_var = tk.StringVar()
            qty_var = tk.StringVar(value="0")
            price_var = tk.StringVar(value="0")
            ttk.Label(dlg, text="Data:").pack(anchor="w", padx=12, pady=4)
            ttk.Entry(dlg, textvariable=date_var).pack(fill="x", padx=12)
            ttk.Label(dlg, text="Pozycja (nazwa):").pack(anchor="w", padx=12, pady=4)
            ttk.Entry(dlg, textvariable=name_var).pack(fill="x", padx=12)
            ttk.Label(dlg, text="Ilość / cena jedn. (0 = spis zerowy):").pack(anchor="w", padx=12, pady=4)
            row = ttk.Frame(dlg)
            row.pack(fill="x", padx=12)
            ttk.Entry(row, textvariable=qty_var, width=10).pack(side="left")
            ttk.Entry(row, textvariable=price_var, width=10).pack(side="left", padx=8)

            val_var = tk.StringVar(value=INVENTORY_VALUATION_LABELS["purchase_price"])
            val_keys = list(INVENTORY_VALUATION_LABELS.keys())
            val_labels = [INVENTORY_VALUATION_LABELS[k] for k in val_keys]
            ttk.Label(dlg, text="Metoda wyceny:").pack(anchor="w", padx=12, pady=(8, 2))
            ttk.Combobox(
                dlg,
                textvariable=val_var,
                values=val_labels,
                state="readonly",
                width=40,
            ).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    qty = float(qty_var.get().replace(",", ".") or 0)
                    price = float(price_var.get().replace(",", ".") or 0)
                    label_to_key = {v: k for k, v in INVENTORY_VALUATION_LABELS.items()}
                    val_method = label_to_key.get(val_var.get(), "purchase_price")
                    if qty == 0 and price == 0:
                        create_zero_inventory(date_var.get(), kind)
                    else:
                        create_inventory(date_var.get(), kind, lines=[{
                            "name": name_var.get() or "Pozycja",
                            "quantity": qty,
                            "unit_price": price,
                            "valuation_method": val_method,
                        }])
                    dlg.destroy()
                    refresh()
                    show_toast(outer, "Spis zapisany", bg="#2e7d32")
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        def book_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            try:
                book_inventory_to_kpir(sel[0])
                refresh()
                show_toast(outer, "Spis ujęty w KPiR (kol. 12)", bg="#2e7d32")
            except ValidationError as exc:
                messagebox.showerror("Błąd", str(exc))

        def apply_markup_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            try:
                inv = apply_year_side_cost_markup(sel[0], year_var.get())
                refresh()
                show_toast(
                    outer,
                    f"Zastosowano wskaźnik k. ubocznych: {inv.side_cost_markup_pct * 100:.2f}%",
                    bg="#2e7d32",
                )
            except ValidationError as exc:
                messagebox.showerror("Błąd", str(exc))

        markup_hint = compute_purchase_side_markup_pct(year_var.get())
        tk.Label(
            body,
            text=f"Wskaźnik kosztów ubocznych zakupu ({year_var.get()}): {markup_hint * 100:.2f}% (kol.13/kol.12)",
            bg=_BG, fg="#555", font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(0, 4))

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Spis 1 I", command=lambda: add_inventory("year_start")).pack(side="left", padx=4)
        ttk.Button(btns, text="Spis 31 XII", command=lambda: add_inventory("year_end")).pack(side="left", padx=4)
        ttk.Button(btns, text="Wskaźnik k. ubocznych", command=apply_markup_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Ujęcie w KPiR", command=book_selected).pack(side="left", padx=4)
        year_var.trace_add("write", lambda *_: refresh())
        refresh()
        self._swap(outer)

    def show_fixed_assets(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Środki trwałe", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        summary = fixed_assets_summary()
        tk.Label(
            body,
            text=f"Aktywne: {summary['active_count']} | Wartość początkowa: {summary['total_initial']:.2f} | Netto: {summary['total_net']:.2f} PLN",
            bg=_BG, font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=4)

        tree = ttk.Treeview(body, columns=("name", "date", "value", "depr", "net"), show="headings", height=10)
        for cid, txt, w in [
            ("name", "Nazwa", 180), ("date", "Data nabycia", 90),
            ("value", "Wartość pocz.", 90), ("depr", "Umorzenie", 80), ("net", "Netto", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        for asset in list_fixed_assets():
            tree.insert("", "end", values=(
                asset.name, asset.acquisition_date[:10],
                f"{asset.initial_value:.2f}", f"{asset.accumulated_depreciation:.2f}", f"{asset.net_value:.2f}",
            ))

        def add_asset() -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Nowy środek trwały")
            name_var = tk.StringVar()
            val_var = tk.StringVar()
            date_var = tk.StringVar(value=date.today().isoformat())
            ttk.Label(dlg, text="Nazwa:").pack(anchor="w", padx=12, pady=4)
            ttk.Entry(dlg, textvariable=name_var).pack(fill="x", padx=12)
            ttk.Label(dlg, text="Wartość początkowa:").pack(anchor="w", padx=12, pady=4)
            ttk.Entry(dlg, textvariable=val_var).pack(fill="x", padx=12)
            ttk.Label(dlg, text="Data nabycia:").pack(anchor="w", padx=12, pady=4)
            ttk.Entry(dlg, textvariable=date_var).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    create_fixed_asset(name=name_var.get(), initial_value=float(val_var.get().replace(",", ".")), acquisition_date=date_var.get())
                    dlg.destroy()
                    self.show_fixed_assets()
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        y, m = date.today().year, date.today().month
        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Dodaj ST", command=add_asset).pack(side="left", padx=4)
        ttk.Button(btns, text=f"Amortyzacja {m:02d}/{y}", command=lambda: (
            post_monthly_depreciation(y, m),
            show_toast(outer, "Amortyzacja zaksięgowana", bg="#2e7d32"),
        )).pack(side="left", padx=4)
        self._swap(outer)

    def show_year_close(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Zamknięcie roku PKPiR", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        year_var = tk.IntVar(value=date.today().year - 1 if date.today().month == 1 else date.today().year)
        self._period_bar(body, year_var, tk.IntVar(value=12)).pack(anchor="w")

        txt = tk.Text(body, height=18, wrap="word", font=("Consolas", 9))
        txt.pack(fill="both", expand=True, pady=8)

        def refresh() -> None:
            summary = build_year_close_summary(year_var.get())
            inc = summary["income"]
            txt.delete("1.0", "end")
            txt.insert("end", f"=== Zamknięcie roku {year_var.get()} ===\n\n")
            txt.insert("end", f"Dochód urzędowy: {inc['income']:.2f} PLN\n")
            txt.insert("end", f"Wzór: {inc['formula']}\n\n")
            txt.insert("end", f"Remanent początkowy: {inc['inventory_opening']:.2f}\n")
            txt.insert("end", f"Zakupy (kol. 12): {inc['purchase_goods']:.2f}\n")
            txt.insert("end", f"Koszty uboczne (kol. 13): {inc['purchase_side']:.2f}\n")
            txt.insert("end", f"Remanent końcowy: {inc['inventory_closing']:.2f}\n")
            txt.insert("end", f"Pozostałe wydatki (kol. 16): {inc['other_expenses_total']:.2f}\n\n")
            for item in summary["checklist"]["items"]:
                txt.insert("end", f"[{item['severity']}] {item['message']}\n")

        def do_close() -> None:
            try:
                closure = close_year(year_var.get(), force=False)
                show_toast(outer, f"Rok zamknięty. Dochód: {closure.annual_income:.2f} PLN", bg="#2e7d32")
                refresh()
            except ValidationError as exc:
                if messagebox.askyesno("Błędy checklisty", f"{exc}\n\nWymusić zamknięcie?"):
                    close_year(year_var.get(), force=True)
                    refresh()

        def export_annual() -> None:
            try:
                pkg = export_pkpir_annual_package(year_var.get())
                if messagebox.askyesno("Eksport", f"Pakiet roczny:\n{pkg}\n\nOtworzyć folder?"):
                    os.startfile(str(pkg))
            except Exception as exc:
                messagebox.showerror("Błąd eksportu", str(exc))

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Zamknij rok", command=do_close).pack(side="left", padx=4)
        ttk.Button(btns, text="Eksport roczny PKPiR", command=export_annual).pack(side="left", padx=4)
        year_var.trace_add("write", lambda *_: refresh())
        refresh()
        self._swap(outer)

    def show_official_exports(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Eksport urzędowy (19 kolumn)", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        year_var = tk.IntVar(value=date.today().year)
        month_var = tk.IntVar(value=date.today().month)
        self._period_bar(body, year_var, month_var).pack(anchor="w", pady=8)

        cols = "\n".join(f"{i+1}. {label}" for i, (_, label) in enumerate(OFFICIAL_COLUMN_HEADERS))
        tk.Label(body, text=f"Kolumny PKPiR:\n{cols}", bg=_BG, justify="left", font=("Segoe UI", 8)).pack(anchor="w")

        def run_export(kind: str) -> None:
            y, m = year_var.get(), month_var.get()
            try:
                if kind == "csv":
                    path = export_official_pkpir_csv(y, m)
                elif kind == "xlsx":
                    path = export_official_pkpir_xlsx(y, m)
                elif kind == "pdf":
                    path = export_official_pkpir_pdf(y, m)
                elif kind == "annual":
                    path = export_pkpir_annual_package(y)
                else:
                    return
                show_toast(outer, f"Zapisano: {path.name}", bg="#2e7d32")
                if messagebox.askyesno("Eksport", f"{path}\n\nOtworzyć?"):
                    os.startfile(str(path if path.is_file() else path))
            except Exception as exc:
                messagebox.showerror("Błąd", str(exc))

        for label, kind in [
            ("CSV urzędowy", "csv"),
            ("XLSX urzędowy", "xlsx"),
            ("PDF urzędowy", "pdf"),
            ("Pakiet roczny PKPiR", "annual"),
        ]:
            ttk.Button(body, text=label, command=lambda k=kind: run_export(k)).pack(anchor="w", pady=4)
        self._swap(outer)

    def show_compliance_pkpir(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Compliance PKPiR", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        for row in kpir_compliance_monitors(date.today().year):
            fg = {"ok": "#2e7d32", "warning": "#e65100", "error": "#c62828", "info": "#1565c0"}.get(
                str(row.get("level") or "ok"), "#333",
            )
            tk.Label(
                body,
                text=f"{row.get('title')}: {row.get('message')}",
                bg=_BG, fg=fg, wraplength=700, justify="left", font=("Segoe UI", 10),
            ).pack(anchor="w", pady=6)
        self._swap(outer)

    def show_sales_register(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Ewidencja sprzedaży (§ 17)", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Przychody nieudokumentowane fakturą — przed ujęciem w KPiR zapisz wpis w ewidencji sprzedaży.",
            bg=_BG, fg="#444", wraplength=720, justify="left", font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        year_var = tk.IntVar(value=date.today().year)
        month_var = tk.IntVar(value=date.today().month)
        self._period_bar(body, year_var, month_var).pack(anchor="w", pady=4)

        tree = ttk.Treeview(
            body,
            columns=("date", "amount", "description", "ref", "kpir"),
            show="headings",
            height=14,
        )
        for cid, txt, w in [
            ("date", "Data", 90), ("amount", "Kwota", 80), ("description", "Opis", 220),
            ("ref", "Dowód", 100), ("kpir", "KPiR", 90),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for row in sales_register_for_month(year_var.get(), month_var.get()):
                kpir_lbl = "ujęte" if row.kpir_entry_id else "nieujęte"
                tree.insert("", "end", iid=row.id, values=(
                    row.event_date,
                    f"{row.amount:.2f}",
                    (row.description or "")[:50],
                    row.document_ref or "",
                    kpir_lbl,
                ))

        def add_entry() -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Nowy wpis ewidencji sprzedaży")
            dlg.geometry("480x280")
            date_var = tk.StringVar(value=date.today().isoformat())
            amount_var = tk.StringVar()
            desc_var = tk.StringVar()
            ref_var = tk.StringVar()
            for label, var in [
                ("Data przychodu:", date_var),
                ("Kwota PLN:", amount_var),
                ("Opis:", desc_var),
                ("Nr dowodu (opcj.):", ref_var),
            ]:
                ttk.Label(dlg, text=label).pack(anchor="w", padx=12, pady=(8, 2))
                ttk.Entry(dlg, textvariable=var).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    add_sales_register_entry(
                        date_var.get(),
                        float(amount_var.get().replace(",", ".")),
                        description=desc_var.get(),
                        document_ref=ref_var.get(),
                    )
                    dlg.destroy()
                    refresh()
                    show_toast(outer, "Wpis zapisany", bg="#2e7d32")
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        def book_selected() -> None:
            sel = tree.selection()
            if not sel:
                return
            try:
                _, entry = book_sales_register_to_kpir(sel[0])
                refresh()
                show_toast(outer, f"Ujęto w KPiR: {entry.entry_number}", bg="#2e7d32")
            except ValidationError as exc:
                messagebox.showerror("Błąd", str(exc))

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Dodaj wpis", command=add_entry).pack(side="left", padx=4)
        ttk.Button(btns, text="Ujęcie w KPiR", command=book_selected).pack(side="left", padx=4)
        year_var.trace_add("write", lambda *_: refresh())
        month_var.trace_add("write", lambda *_: refresh())
        refresh()
        self._swap(outer)

    def show_ksef_sync(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "KSeF — numery e-faktur", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Numery KSeF z faktur są kopiowane do kolumny 3 KPiR. Uzupełnij brakujące numery i zsynchronizuj zaksięgowane wpisy.",
            bg=_BG, fg="#444", wraplength=720, justify="left", font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        year_var = tk.IntVar(value=date.today().year)
        month_var = tk.IntVar(value=date.today().month)
        self._period_bar(body, year_var, month_var).pack(anchor="w", pady=4)

        tree = ttk.Treeview(
            body,
            columns=("number", "date", "buyer", "nip", "ksef", "kpir", "sync"),
            show="headings",
            height=14,
        )
        for cid, txt, w in [
            ("number", "Faktura", 110), ("date", "Data", 85), ("buyer", "Nabywca", 120),
            ("nip", "NIP", 95), ("ksef", "KSeF", 120), ("kpir", "KPiR", 80), ("sync", "Sync", 70),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for row in list_ksef_sync_rows(year=year_var.get(), month=month_var.get()):
                sync_lbl = "OK" if row.sync_ok else ("brak" if not row.ksef_number else "różni się")
                if row.needs_ksef:
                    sync_lbl = "wymagany KSeF"
                tree.insert("", "end", iid=row.invoice_id, values=(
                    row.invoice_number,
                    row.sale_date,
                    row.buyer_name,
                    row.buyer_nip,
                    row.ksef_number or "—",
                    row.kpir_status,
                    sync_lbl,
                ))

        def edit_ksef() -> None:
            sel = tree.selection()
            if not sel:
                return
            invoice_id = sel[0]
            rows = list_ksef_sync_rows(year=year_var.get(), month=month_var.get())
            row = next((r for r in rows if r.invoice_id == invoice_id), None)
            if not row:
                return
            dlg = tk.Toplevel(outer)
            dlg.title(f"KSeF — {row.invoice_number}")
            dlg.geometry("520x200")
            ksef_var = tk.StringVar(value=row.ksef_number)
            nip_var = tk.StringVar(value=row.buyer_nip)
            ttk.Label(dlg, text="Nr KSeF:").pack(anchor="w", padx=12, pady=(12, 2))
            ttk.Entry(dlg, textvariable=ksef_var, width=60).pack(fill="x", padx=12)
            ttk.Label(dlg, text="NIP nabywcy:").pack(anchor="w", padx=12, pady=(8, 2))
            ttk.Entry(dlg, textvariable=nip_var, width=24).pack(anchor="w", padx=12)

            def save() -> None:
                try:
                    set_invoice_ksef(invoice_id, ksef_var.get(), buyer_nip=nip_var.get())
                    dlg.destroy()
                    refresh()
                    show_toast(outer, "Zapisano i zsynchronizowano KSeF", bg="#2e7d32")
                except Exception as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        def sync_all() -> None:
            result = sync_all_ksef_to_kpir(year=year_var.get(), month=month_var.get())
            refresh()
            show_toast(
                outer,
                f"Zsynchronizowano {result['synced']} wpisów (pominięto {result['skipped']})",
                bg="#2e7d32",
            )

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Edytuj KSeF", command=edit_ksef).pack(side="left", padx=4)
        ttk.Button(btns, text="Synchronizuj wszystkie", command=sync_all).pack(side="left", padx=4)
        year_var.trace_add("write", lambda *_: refresh())
        month_var.trace_add("write", lambda *_: refresh())
        refresh()
        self._swap(outer)

    def show_intangible_assets(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "WNiP — wartości niematerialne i prawne", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        summary = intangible_assets_summary()
        tk.Label(
            body,
            text=f"Aktywne WNiP: {summary['active_count']} | Wartość początkowa: {summary['total_initial']:.2f} | Netto: {summary['total_net']:.2f} PLN",
            bg=_BG, font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=4)

        tree = ttk.Treeview(body, columns=("name", "date", "value", "depr", "net"), show="headings", height=10)
        for cid, txt, w in [
            ("name", "Nazwa", 180), ("date", "Data nabycia", 90),
            ("value", "Wartość pocz.", 90), ("depr", "Umorzenie", 80), ("net", "Netto", 80),
        ]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        for asset in list_intangible_assets():
            tree.insert("", "end", values=(
                asset.name, asset.acquisition_date[:10],
                f"{asset.initial_value:.2f}", f"{asset.accumulated_depreciation:.2f}", f"{asset.net_value:.2f}",
            ))

        def add_asset() -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Nowe WNiP")
            name_var = tk.StringVar()
            val_var = tk.StringVar()
            date_var = tk.StringVar(value=date.today().isoformat())
            for label, var in [("Nazwa (licencja, prawo…):", name_var), ("Wartość początkowa:", val_var), ("Data nabycia:", date_var)]:
                ttk.Label(dlg, text=label).pack(anchor="w", padx=12, pady=(8, 2))
                ttk.Entry(dlg, textvariable=var).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    create_intangible_asset(
                        name=name_var.get(),
                        initial_value=float(val_var.get().replace(",", ".")),
                        acquisition_date=date_var.get(),
                    )
                    dlg.destroy()
                    self.show_intangible_assets()
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        y, m = date.today().year, date.today().month
        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Dodaj WNiP", command=add_asset).pack(side="left", padx=4)
        ttk.Button(btns, text=f"Amortyzacja {m:02d}/{y}", command=lambda: (
            post_wnip_depreciation(y, m),
            show_toast(outer, "Amortyzacja WNiP zaksięgowana", bg="#2e7d32"),
        )).pack(side="left", padx=4)
        self._swap(outer)

    def show_vehicle_log(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Ewidencja przebiegu pojazdu", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="Wymagana przy środku trwałym (auto firmowe) i odliczaniu 100% kosztów eksploatacji.",
            bg=_BG, fg="#444", wraplength=720, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        year_var = tk.IntVar(value=date.today().year)
        vehicles = list_vehicles()
        vehicle_labels = [f"{v.name} ({v.registration_number})" for v in vehicles]
        vehicle_ids = [v.id for v in vehicles]
        vehicle_var = tk.StringVar(value=vehicle_labels[0] if vehicle_labels else "")

        top = tk.Frame(body, bg=_BG)
        top.pack(fill="x")
        ttk.Label(top, text="Rok:").pack(side="left")
        ttk.Spinbox(top, from_=2020, to=2035, textvariable=year_var, width=6).pack(side="left", padx=4)
        ttk.Label(top, text="Pojazd:").pack(side="left", padx=(12, 0))
        ttk.Combobox(top, textvariable=vehicle_var, values=vehicle_labels, width=28, state="readonly").pack(side="left", padx=4)

        summary_lbl = tk.Label(body, text="", bg=_BG, font=("Segoe UI", 9, "bold"))
        summary_lbl.pack(anchor="w", pady=4)

        tree = ttk.Treeview(body, columns=("date", "km", "route", "purpose"), show="headings", height=12)
        for cid, txt, w in [("date", "Data", 90), ("km", "Km", 60), ("route", "Trasa", 220), ("purpose", "Cel", 80)]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=8)

        def _selected_vehicle_id() -> str:
            label = vehicle_var.get()
            if label in vehicle_labels:
                return vehicle_ids[vehicle_labels.index(label)]
            return vehicle_ids[0] if vehicle_ids else ""

        def refresh() -> None:
            for i in tree.get_children():
                tree.delete(i)
            vid = _selected_vehicle_id()
            if not vid:
                summary_lbl.config(text="Brak pojazdów — dodaj pojazd firmowy.")
                return
            summ = mileage_summary(vid, year_var.get())
            summary_lbl.config(
                text=f"Rok {summ['year']}: służbowo {summ['business_km']} km | prywatnie {summ['private_km']} km | udział firmowy {summ['business_pct']:.1f}%",
            )
            for row in sorted(list_mileage_log(), key=lambda x: x.log_date, reverse=True):
                if row.vehicle_id != vid or not row.log_date.startswith(f"{year_var.get():04d}"):
                    continue
                tree.insert("", "end", values=(
                    row.log_date, f"{row.trip_km:.1f}", row.route_description[:40],
                    "służbowa" if row.purpose == "business" else "prywatna",
                ))

        def add_vehicle_dlg() -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Nowy pojazd")
            name_var = tk.StringVar()
            reg_var = tk.StringVar()
            pct_var = tk.StringVar(value="100")
            for label, var in [("Nazwa / model:", name_var), ("Nr rejestracyjny:", reg_var), ("Udział firmowy %:", pct_var)]:
                ttk.Label(dlg, text=label).pack(anchor="w", padx=12, pady=(8, 2))
                ttk.Entry(dlg, textvariable=var).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    create_vehicle(name=name_var.get(), registration_number=reg_var.get(), business_use_pct=float(pct_var.get()))
                    dlg.destroy()
                    self.show_vehicle_log()
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        def add_trip() -> None:
            vid = _selected_vehicle_id()
            if not vid:
                messagebox.showinfo("Przebieg", "Najpierw dodaj pojazd.")
                return
            dlg = tk.Toplevel(outer)
            dlg.title("Nowy wpis przebiegu")
            date_var = tk.StringVar(value=date.today().isoformat())
            km_var = tk.StringVar()
            route_var = tk.StringVar()
            purpose_var = tk.StringVar(value="business")
            for label, var in [("Data:", date_var), ("Przebieg (km):", km_var), ("Trasa / cel:", route_var)]:
                ttk.Label(dlg, text=label).pack(anchor="w", padx=12, pady=(8, 2))
                ttk.Entry(dlg, textvariable=var).pack(fill="x", padx=12)
            ttk.Label(dlg, text="Cel (business/private):").pack(anchor="w", padx=12, pady=(8, 2))
            ttk.Combobox(dlg, textvariable=purpose_var, values=["business", "private"], state="readonly").pack(fill="x", padx=12)

            def save() -> None:
                try:
                    add_mileage_entry(
                        vid, date_var.get(),
                        trip_km=float(km_var.get().replace(",", ".")),
                        route_description=route_var.get(),
                        purpose=purpose_var.get(),
                    )
                    dlg.destroy()
                    refresh()
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz", command=save).pack(pady=12)

        btns = tk.Frame(body, bg=_BG)
        btns.pack(fill="x")
        ttk.Button(btns, text="Odśwież", command=refresh).pack(side="left", padx=4)
        ttk.Button(btns, text="Dodaj pojazd", command=add_vehicle_dlg).pack(side="left", padx=4)
        ttk.Button(btns, text="Dodaj przejazd", command=add_trip).pack(side="left", padx=4)
        year_var.trace_add("write", lambda *_: refresh())
        refresh()
        self._swap(outer)

    def show_internal_docs(self: KpirView) -> None:
        outer = tk.Frame(self.frame, bg=_BG)
        self._toolbar(outer, "Dowody wewnętrzne (§ 8, § 9)", back=self.show_dashboard)
        body = tk.Frame(outer, bg=_BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)

        home = ttk.LabelFrame(body, text=" Koszty mieszkania (§ 8) ", padding=8)
        home.pack(fill="x", pady=(0, 8))
        h_date = tk.StringVar(value=date.today().isoformat())
        h_amount = tk.StringVar()
        h_share = tk.StringVar(value="0.25")
        h_type = tk.StringVar(value="Prąd")
        h_doc = tk.StringVar()
        for label, var in [
            ("Data:", h_date), ("Kwota faktury (PLN):", h_amount), ("Udział działalności (0–1):", h_share),
            ("Rodzaj (prąd, czynsz…):", h_type), ("Nr faktury źródłowej:", h_doc),
        ]:
            row = ttk.Frame(home)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label, width=28).pack(side="left")
            ttk.Entry(row, textvariable=var, width=24).pack(side="left")

        def book_home() -> None:
            try:
                create_home_office_internal_cost(
                    issue_date=h_date.get(),
                    base_amount=float(h_amount.get().replace(",", ".")),
                    business_share=float(h_share.get().replace(",", ".")),
                    utility_type=h_type.get(),
                    source_document=h_doc.get(),
                )
                show_toast(outer, "Dowód wewnętrzny zaksięgowany w KPiR", bg="#2e7d32")
            except (ValueError, ValidationError) as exc:
                messagebox.showerror("Błąd", str(exc))

        ttk.Button(home, text="Ujmij w KPiR", command=book_home).pack(anchor="w", pady=6)

        goods = ttk.LabelFrame(body, text=" Opis towaru przed fakturą (§ 9) ", padding=8)
        goods.pack(fill="both", expand=True)
        tree = ttk.Treeview(goods, columns=("date", "supplier", "desc", "value", "st"), show="headings", height=8)
        for cid, txt, w in [("date", "Data", 85), ("supplier", "Dostawca", 120), ("desc", "Opis", 180), ("value", "Wartość", 70), ("st", "KPiR", 70)]:
            tree.heading(cid, text=txt)
            tree.column(cid, width=w)
        tree.pack(fill="both", expand=True, pady=4)

        def refresh_goods() -> None:
            for i in tree.get_children():
                tree.delete(i)
            for item in list_goods_receipts_pending():
                st = "ujęte" if item.kpir_entry_id else "oczekuje"
                tree.insert("", "end", iid=item.id, values=(
                    item.receipt_date, item.supplier_name[:25], item.description[:35], f"{item.value:.2f}", st,
                ))

        def add_goods() -> None:
            dlg = tk.Toplevel(outer)
            dlg.title("Opis przyjęcia towaru")
            d_var = tk.StringVar(value=date.today().isoformat())
            s_var = tk.StringVar()
            desc_var = tk.StringVar()
            qty_var = tk.StringVar(value="1")
            price_var = tk.StringVar()
            for label, var in [
                ("Data przyjęcia:", d_var), ("Dostawca:", s_var), ("Opis:", desc_var),
                ("Ilość:", qty_var), ("Cena jedn.:", price_var),
            ]:
                ttk.Label(dlg, text=label).pack(anchor="w", padx=12, pady=(6, 2))
                ttk.Entry(dlg, textvariable=var).pack(fill="x", padx=12)

            def save() -> None:
                try:
                    create_goods_receipt_before_invoice(
                        receipt_date=d_var.get(),
                        supplier_name=s_var.get(),
                        description=desc_var.get(),
                        quantity=float(qty_var.get().replace(",", ".")),
                        unit_price=float(price_var.get().replace(",", ".")),
                    )
                    dlg.destroy()
                    refresh_goods()
                except (ValueError, ValidationError) as exc:
                    messagebox.showerror("Błąd", str(exc), parent=dlg)

            ttk.Button(dlg, text="Zapisz opis", command=save).pack(pady=10)

        def book_goods() -> None:
            sel = tree.selection()
            if not sel:
                return
            inv_no = simpledialog.askstring("Faktura", "Nr faktury (opcjonalnie):", parent=outer)
            try:
                book_goods_receipt_to_kpir(sel[0], invoice_document_number=inv_no or "")
                refresh_goods()
                show_toast(outer, "Opis ujęty w KPiR (kol. 12)", bg="#2e7d32")
            except ValidationError as exc:
                messagebox.showerror("Błąd", str(exc))

        gbtns = ttk.Frame(goods)
        gbtns.pack(fill="x")
        ttk.Button(gbtns, text="Odśwież", command=refresh_goods).pack(side="left", padx=4)
        ttk.Button(gbtns, text="Dodaj opis", command=add_goods).pack(side="left", padx=4)
        ttk.Button(gbtns, text="Ujęcie w KPiR", command=book_goods).pack(side="left", padx=4)
        refresh_goods()
        self._swap(outer)
