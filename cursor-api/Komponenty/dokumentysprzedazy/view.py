"""Widok inline — Dokumenty sprzedaży (faktury bez VAT)."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import date
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.accounting_mode_sync import (
    effective_invoice_business_mode,
    kpir_accounting_label,
    load_kpir_accounting_mode,
    persist_business_mode_both,
)
from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .constants import (
    BUSINESS_MODE_DNR,
    BUSINESS_MODE_JDG,
    BUSINESS_MODE_LABELS,
    DEFAULT_FOOTNOTES,
    DEFAULT_NUMBERING,
    business_mode_display,
    numbering_preset_for_mode,
)
from .export_monthly import export_month_csv
from .i18n import INVOICE_LANGUAGES, LANGUAGE_LABELS, manual_doc_label, normalize_language
from .invoice_builder import build_sample_invoice, resolve_footnote
from .invoice_editor import open_invoice_editor
from .invoice_helpers import is_test_invoice
from .invoice_service import (
    create_correction_draft,
    create_draft_for_order,
    create_manual_draft,
    create_test_draft,
    delete_invoice,
    delete_invoice_confirm_message,
    delete_invoices_bulk_confirm_extra,
    delete_invoices_many,
)
from .models import InvoiceSettings, SellerSettings
from .numbering import format_number, reconcile_all_series, reset_series_year
from .pdf_generator import generate_invoice_pdf, pdf_filename
from .order_review import open_order_review
from .orders_sync import pending_orders_count, register_on_new_orders, sync_accounting_orders
from .shopify_orders import fetch_orders, order_to_row
from .ui_labels import issue_button_label
from .storage import documents_dir_for_date, get_invoice, invoice_by_order_id, list_manual_invoices, load_settings, save_settings


def build_view(parent: tk.Widget, on_back: Callable[[], None]) -> tk.Widget:
    root = ttk.Frame(parent)
    root.pack(fill="both", expand=True)

    state: dict[str, Any] = {"orders": [], "order_by_id": {}, "rows": [], "pending_order_ref": []}

    header = ttk.Frame(root, padding=(12, 10, 12, 6))
    header.pack(fill="x")
    ttk.Button(header, text="← Wróć", command=on_back).pack(side="left")
    ttk.Label(header, text="Dokumenty sprzedaży", font=("Segoe UI", 14, "bold")).pack(
        side="left", padx=(12, 0),
    )
    ttk.Label(
        header, text="Faktura bez VAT / Invoice without VAT",
        foreground="#666", font=("Segoe UI", 9),
    ).pack(side="left", padx=(10, 0))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    tab_orders = ttk.Frame(notebook)
    tab_settings = ttk.Frame(notebook)
    tab_export = ttk.Frame(notebook)
    notebook.add(tab_orders, text="Zamówienia")
    notebook.add(tab_settings, text="Ustawienia faktur")
    notebook.add(tab_export, text="Eksport księgowy")

    # --- Sprzedaż poza Shopify ---
    manual_frame = ttk.LabelFrame(tab_orders, text="Sprzedaż poza Shopify", padding=8)
    manual_frame.pack(fill="x", padx=0, pady=(8, 4))

    manual_lang_var = tk.StringVar(value="pl")
    manual_bar = ttk.Frame(manual_frame)
    manual_bar.pack(fill="x", pady=(0, 6))
    ttk.Label(manual_bar, text="Język dokumentu:").pack(side="left")
    _manual_mode = effective_invoice_business_mode(load_settings())
    for code in INVOICE_LANGUAGES:
        ttk.Radiobutton(
            manual_bar,
            text=manual_doc_label(code, mode=_manual_mode),
            value=code,
            variable=manual_lang_var,
        ).pack(side="left", padx=(8, 0))

    manual_cols = ("number", "date", "buyer", "amount", "st")
    manual_tree = ttk.Treeview(manual_frame, columns=manual_cols, show="headings", height=4, selectmode="extended")
    for cid, txt, w in [
        ("number", "Numer", 110), ("date", "Data", 85), ("buyer", "Nabywca", 160),
        ("amount", "Kwota", 90), ("st", "Status", 90),
    ]:
        manual_tree.heading(cid, text=txt)
        manual_tree.column(cid, width=w)
    manual_tree.pack(fill="x", pady=(0, 6))

    def _refresh_manual_table() -> None:
        for i in manual_tree.get_children():
            manual_tree.delete(i)
        status_lbl = {
            "draft": "szkic",
            "issued": "wystawiony",
            "corrected": "skorygowany",
            "cancelled": "anulowany",
        }
        for inv in sorted(list_manual_invoices(), key=lambda x: x.issue_date, reverse=True):
            st = status_lbl.get(inv.status, inv.status)
            if is_test_invoice(inv):
                st = f"test · {st}"
            manual_tree.insert("", "end", iid=inv.id, values=(
                inv.invoice_number or "—",
                (inv.sale_date or inv.issue_date)[:10],
                (inv.buyer.name or "—")[:30],
                f"{inv.order_total:.2f} {inv.currency}",
                st,
            ))

    def _new_manual_invoice() -> None:
        draft = create_manual_draft(language=manual_lang_var.get())
        open_invoice_editor(
            root, draft,
            on_saved=lambda _i: _refresh_manual_table(),
        )

    def _new_test_invoice() -> None:
        draft = create_test_draft(language=manual_lang_var.get())
        open_invoice_editor(
            root, draft,
            on_saved=lambda _i: _refresh_manual_table(),
        )

    def _open_manual_invoice() -> None:
        sel = manual_tree.selection()
        if not sel:
            messagebox.showinfo("Faktury", "Zaznacz dokument z listy.", parent=root)
            return
        inv = get_invoice(sel[0])
        if not inv:
            return
        open_invoice_editor(
            root, inv,
            read_only=inv.status in ("issued", "corrected", "cancelled"),
            on_saved=lambda _i: _refresh_manual_table(),
        )

    manual_tree.bind("<Double-1>", lambda _e: _open_manual_invoice())

    def _delete_manual_invoices() -> None:
        sel = manual_tree.selection()
        if not sel:
            messagebox.showinfo("Faktury", "Zaznacz dokument(y) do usunięcia.", parent=root)
            return
        invoices = [get_invoice(iid) for iid in sel]
        invoices = [i for i in invoices if i]
        if not invoices:
            return
        if len(invoices) == 1:
            msg = delete_invoice_confirm_message(invoices[0])
            if not messagebox.askyesno("Usuń fakturę", msg, parent=root):
                return
            try:
                delete_invoice(invoices[0].id)
            except Exception as exc:
                messagebox.showerror("Faktury", str(exc), parent=root)
                return
            show_toast(root, "Usunięto fakturę.", bg="#c62828")
        else:
            issued = [i for i in invoices if i.status in ("issued", "corrected")]
            msg = f"Usunąć {len(invoices)} dokument(ów)?"
            if issued:
                msg += delete_invoices_bulk_confirm_extra(invoices)
            if not messagebox.askyesno("Usuń faktury", msg, parent=root):
                return
            removed, errors = delete_invoices_many([i.id for i in invoices])
            if errors:
                messagebox.showwarning(
                    "Faktury",
                    f"Usunięto {removed}.\n\n" + "\n".join(errors[:5]),
                    parent=root,
                )
            else:
                show_toast(root, f"Usunięto {removed} dokument(ów).", bg="#c62828")
        _refresh_manual_table()

    manual_btns = ttk.Frame(manual_frame)
    manual_btns.pack(fill="x")
    ttk.Button(manual_btns, text="Nowa faktura bez VAT", command=_new_manual_invoice).pack(side="left", padx=(0, 8))
    ttk.Button(manual_btns, text="Faktura testowa", command=_new_test_invoice).pack(side="left", padx=(0, 8))
    ttk.Button(manual_btns, text="Otwórz zaznaczoną", command=_open_manual_invoice).pack(side="left", padx=(0, 8))
    ttk.Button(manual_btns, text="Usuń zaznaczone", command=_delete_manual_invoices).pack(side="left", padx=(0, 8))
    ttk.Label(
        manual_btns,
        text="Test: numeracja TEST/TST — księgowalna w DNR/KPiR; przy usunięciu czyści też wpisy ewidencji.",
        foreground="#666",
    ).pack(side="left", padx=(12, 0))
    _refresh_manual_table()

    # --- Zamówienia ---
    orders_bar = ttk.Frame(tab_orders, padding=(0, 8, 0, 4))
    orders_bar.pack(fill="x")
    status_var = tk.StringVar(value="Kliknij „Pobierz z Shopify” lub czekaj na automatyczną synchronizację.")
    pending_var = tk.StringVar(value="")
    ttk.Label(orders_bar, textvariable=status_var, foreground="#444").pack(side="left")
    pending_lbl = ttk.Label(orders_bar, textvariable=pending_var, foreground="#c62828", font=("Segoe UI", 9, "bold"))
    pending_lbl.pack(side="left", padx=(12, 0))

    def _selected_order() -> dict[str, Any] | None:
        sel = tree.selection()
        if not sel:
            return None
        oid = int(sel[0])
        return state["order_by_id"].get(oid)

    def _refresh_table() -> None:
        for i in tree.get_children():
            tree.delete(i)
        for row in state["rows"]:
            doc_lbl = {
                "not_issued": "niewystawiony",
                "issued": "wystawiony",
                "corrected": "skorygowany",
                "cancelled": "anulowany",
                "draft": "szkic",
            }.get(row.doc_status, row.doc_status)
            inv_lbl = "—"
            if row.invoice_requested:
                inv_lbl = "Firma" if row.invoice_customer_type == "company" else "Tak"
            iid = str(row.shopify_order_id)
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.shopify_order_name,
                    row.created_at[:10],
                    row.payment_date[:10] if row.payment_date else "",
                    row.financial_status,
                    row.fulfillment_status,
                    row.customer_name,
                    row.customer_email,
                    row.shipping_country,
                    row.currency,
                    f"{row.products_total:.2f}",
                    f"{row.shipping_total:.2f}",
                    f"{row.discounts_total:.2f}",
                    f"{row.order_total:.2f}",
                    inv_lbl,
                    doc_lbl,
                    row.invoice_number or "—",
                ),
            )

    def _load_orders() -> None:
        status_var.set("Pobieram zamówienia z Shopify...")
        btn_refresh.state(["disabled"])

        def worker() -> None:
            try:
                orders = fetch_orders(days_back=365, financial_status=None)
            except Exception as exc:
                root.after(0, lambda e=exc: (
                    status_var.set(f"Błąd: {e}"),
                    btn_refresh.state(["!disabled"]),
                    messagebox.showerror("Shopify", str(e), parent=root),
                ))
                return

            def apply() -> None:
                state["orders"] = orders
                state["order_by_id"] = {int(o.get("id") or 0): o for o in orders}
                state["rows"] = [order_to_row(o) for o in orders]
                _refresh_table()
                _refresh_pending_badge()
                status_var.set(f"Załadowano {len(orders)} zamówień.")
                btn_refresh.state(["!disabled"])
                if state["pending_order_ref"]:
                    oid = state["pending_order_ref"].pop()
                    _select_order_ref(oid)

            root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    btn_refresh = ttk.Button(orders_bar, text="Pobierz z Shopify", command=_load_orders)
    btn_refresh.pack(side="right")

    tree_frame = ttk.Frame(tab_orders)
    tree_frame.pack(fill="both", expand=True)
    cols = (
        "order", "created", "paid", "pay_st", "fulfill", "client", "email",
        "country", "cur", "products", "ship", "disc", "total", "inv_req", "doc_st", "inv_no",
    )
    tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
    headings = [
        ("order", "Zamówienie", 80), ("created", "Data zam.", 85), ("paid", "Data płat.", 85),
        ("pay_st", "Płatność", 80), ("fulfill", "Fulfillment", 80), ("client", "Klient", 120),
        ("email", "E-mail", 140), ("country", "Kraj", 45), ("cur", "Waluta", 45),
        ("products", "Produkty", 70), ("ship", "Wysyłka", 60), ("disc", "Rabaty", 60),
        ("total", "Suma", 70), ("inv_req", "Faktura?", 75), ("doc_st", "Dokument", 90), ("inv_no", "Nr faktury", 100),
    ]
    for cid, txt, w in headings:
        tree.heading(cid, text=txt)
        tree.column(cid, width=w, stretch=cid in ("client", "email"))
    vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    orders_actions = ttk.Frame(tab_orders, padding=(0, 8, 0, 0))
    orders_actions.pack(fill="x")

    def _refresh_pending_badge() -> None:
        n = pending_orders_count()
        pending_var.set(f"· {n} nowych do obsługi" if n else "")

    def _open_editor_for_order(order: dict[str, Any]) -> None:
        oid = int(order.get("id") or 0)
        existing = invoice_by_order_id(oid)
        if existing:
            open_invoice_editor(root, existing, read_only=True, on_saved=lambda _i: _after_orders_change())
            return
        row = next((r for r in state["rows"] if r.shopify_order_id == oid), None)
        if row and (row.is_cancelled or row.has_refund):
            if not messagebox.askyesno(
                "Uwaga",
                "Zamówienie anulowane lub ze zwrotem — wystawić dokument mimo to?",
                parent=root,
            ):
                return
        try:
            from .storage import invoices_for_order

            drafts = [i for i in invoices_for_order(oid) if i.status == "draft"]
            draft = drafts[-1] if drafts else create_draft_for_order(
                order, language=row.suggested_language if row else None,
            )
            open_invoice_editor(root, draft, on_saved=lambda _i: _after_orders_change())
        except Exception as exc:
            messagebox.showerror("Dokument", f"Nie można otworzyć edytora:\n{exc}", parent=root)

    def _after_orders_change() -> None:
        _load_orders()
        _refresh_pending_badge()

    def _open_issue() -> None:
        order = _selected_order()
        if not order:
            messagebox.showinfo("Zamówienia", "Zaznacz zamówienie.", parent=root)
            return
        oid = int(order.get("id") or 0)
        if invoice_by_order_id(oid):
            _open_editor_for_order(order)
            return

        def _proceed() -> None:
            _open_editor_for_order(order)

        open_order_review(root, order, on_issue=_proceed, on_refresh=_after_orders_change)

    def _open_correction() -> None:
        order = _selected_order()
        if not order:
            return
        orig = invoice_by_order_id(int(order.get("id") or 0))
        if not orig:
            messagebox.showinfo("Korekta", "Brak wystawionej faktury do tego zamówienia.", parent=root)
            return
        if not messagebox.askyesno(
            "Korekta",
            f"Wystawić korektę do faktury {orig.invoice_number}?",
            parent=root,
        ):
            return
        draft = create_correction_draft(order, orig)
        open_invoice_editor(root, draft, on_saved=lambda _i: _load_orders())

    def _on_double_click(_e: tk.Event) -> None:
        _open_issue()

    tree.bind("<Double-1>", _on_double_click)

    pending_order_ref = state["pending_order_ref"]

    def _select_order_ref(oid: str) -> None:
        if oid in tree.get_children():
            tree.selection_set(oid)
            tree.focus(oid)
            tree.see(oid)

    def _action_label() -> str:
        order = _selected_order()
        mode = effective_invoice_business_mode(load_settings())
        if not order:
            return issue_button_label(mode)
        if invoice_by_order_id(int(order.get("id") or 0)):
            return "Podgląd dokumentu"
        return issue_button_label(mode)

    btn_issue = ttk.Button(orders_actions, text=issue_button_label(effective_invoice_business_mode(load_settings())), command=_open_issue)
    btn_issue.pack(side="left", padx=(0, 8))
    ttk.Button(orders_actions, text="Wystaw korektę", command=_open_correction).pack(side="left", padx=(0, 8))

    def _on_select(_e: tk.Event | None = None) -> None:
        btn_issue.configure(text=_action_label())

    # --- Status KPiR (podgląd — księgowanie wyłącznie w module KPiR) ---
    kpir_frame = ttk.LabelFrame(tab_orders, text="Status KPiR (podgląd)", padding=8)
    kpir_frame.pack(fill="x", pady=(4, 0))
    kpir_status_var = tk.StringVar(value="Zaznacz zamówienie, aby zobaczyć status KPiR.")
    ttk.Label(kpir_frame, textvariable=kpir_status_var, foreground="#444", wraplength=640).pack(anchor="w")
    ttk.Label(
        kpir_frame,
        text=(
            "Księgowanie w module JDG — KPiR → Przychody → sekcja „Faktury bez VAT”. "
            "Zalecany przepływ: opłacone zamówienie → faktura → DNR → KPiR z faktury."
        ),
        foreground="#1565c0",
        font=("Segoe UI", 8),
        wraplength=640,
        justify="left",
    ).pack(anchor="w", pady=(4, 0))

    def _refresh_kpir_panel() -> None:
        order = _selected_order()
        if not order:
            kpir_status_var.set("Zaznacz zamówienie, aby zobaczyć status KPiR.")
            return
        try:
            from Komponenty.kpir.order_status import get_order_kpir_status

            oid = int(order.get("id") or 0)
            info = get_order_kpir_status(oid)
            labels = {
                "not_booked": "nieujęte w KPiR",
                "booked": "ujęte w KPiR",
                "needs_correction": "wymaga korekty",
                "skipped": "pominięte",
            }
            txt = f"Status: {labels.get(info.status, info.status)}"
            inv = invoice_by_order_id(oid)
            if inv:
                if inv.status == "issued":
                    txt += f" | Faktura: {inv.invoice_number}"
                else:
                    txt += f" | Szkic faktury ({inv.status})"
            else:
                txt += " | Brak faktury"
            if info.entry_number:
                txt += f" | Wpis: {info.entry_number} | PLN: {info.amount_pln:.2f}"
            if info.nbp_rate and info.nbp_rate != 1:
                txt += f" | NBP: {info.nbp_rate} ({info.nbp_rate_date})"
            kpir_status_var.set(txt)
        except Exception as exc:
            kpir_status_var.set(f"KPiR: {exc}")

    def _open_kpir_revenues() -> None:
        from Komponenty.kpir.view import KpirView

        top = root.winfo_toplevel()
        win = tk.Toplevel(top)
        win.title("KPiR — Przychody")
        position_toplevel_screen_center(win, 1040, 760)
        win.minsize(900, 600)
        view = KpirView(win, on_back=win.destroy)
        view.frame.pack(fill="both", expand=True)
        view.show_revenues()

    kpir_btns = ttk.Frame(kpir_frame)
    kpir_btns.pack(fill="x", pady=(6, 0))
    ttk.Button(
        kpir_btns,
        text="Otwórz KPiR → Przychody",
        command=_open_kpir_revenues,
    ).pack(side="left")

    def _on_select_kpir(_e: tk.Event | None = None) -> None:
        _on_select(_e)
        _refresh_kpir_panel()

    tree.bind("<<TreeviewSelect>>", _on_select_kpir)

    # --- Ustawienia ---
    set_canvas = tk.Canvas(tab_settings, highlightthickness=0)
    set_vsb = ttk.Scrollbar(tab_settings, orient="vertical", command=set_canvas.yview)
    set_inner = ttk.Frame(set_canvas, padding=12)
    set_win = set_canvas.create_window((0, 0), window=set_inner, anchor="nw")
    set_canvas.configure(yscrollcommand=set_vsb.set)
    set_canvas.pack(side="left", fill="both", expand=True)
    set_vsb.pack(side="right", fill="y")

    def _set_scroll(_e: tk.Event) -> None:
        set_canvas.configure(scrollregion=set_canvas.bbox("all"))
        set_canvas.itemconfigure(set_win, width=set_canvas.winfo_width())

    set_inner.bind("<Configure>", _set_scroll)
    set_canvas.bind("<Configure>", _set_scroll)
    bind_mousewheel_to_canvas(set_canvas, set_inner)

    settings = load_settings()
    init_mode = effective_invoice_business_mode(settings)
    init_pl_series = (
        settings.numbering_dnr_pl if init_mode == BUSINESS_MODE_DNR else settings.numbering_pl
    )
    seller_vars = {
        "name": tk.StringVar(value=settings.seller.name),
        "owner_name": tk.StringVar(value=settings.seller.owner_name),
        "address": tk.StringVar(value=settings.seller.address),
        "email": tk.StringVar(value=settings.seller.email),
        "phone": tk.StringVar(value=settings.seller.phone),
        "website": tk.StringVar(value=settings.seller.website),
        "nip": tk.StringVar(value=settings.seller.nip),
        "logo_path": tk.StringVar(value=settings.seller.logo_path),
        "footnotes_pl": tk.StringVar(value=resolve_footnote(
            init_mode, settings.seller.footnotes_pl, "pl",
        )),
        "footnotes_en": tk.StringVar(value=resolve_footnote(
            init_mode, settings.seller.footnotes_en, "en",
        )),
    }
    business_var = tk.StringVar(value=init_mode)

    num_pl_p = tk.StringVar(value=init_pl_series.prefix)
    num_pl_n = tk.StringVar(value=str(init_pl_series.next_number))
    num_en_p = tk.StringVar(value=settings.numbering_en.prefix)
    num_en_n = tk.StringVar(value=str(settings.numbering_en.next_number))
    num_year = tk.StringVar(value=str(init_pl_series.year))
    preview_lang_var = tk.StringVar(value="pl")

    ttk.Label(set_inner, text="Dane sprzedawcy", font=("Segoe UI", 11, "bold")).grid(
        row=0, column=0, columnspan=2, sticky="w", pady=(0, 8),
    )
    r = 1
    for key, lbl in [
        ("name", "Nazwa firmy"),
        ("owner_name", "Imię i nazwisko"),
        ("address", "Adres"),
        ("email", "E-mail"),
        ("phone", "Telefon"),
        ("website", "Strona www"),
        ("nip", "NIP sprzedawcy (JDG — nie drukowany na rachunku DNR)"),
        ("logo_path", "Logo (ścieżka)"),
    ]:
        ttk.Label(set_inner, text=lbl + ":").grid(row=r, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Entry(set_inner, textvariable=seller_vars[key], width=52).grid(row=r, column=1, sticky="ew", pady=3)
        r += 1

    ttk.Label(set_inner, text="Tryb działalności:").grid(row=r, column=0, sticky="w", pady=3)
    mode_fr = ttk.Frame(set_inner)
    mode_fr.grid(row=r, column=1, sticky="w")
    rb_dnr = ttk.Radiobutton(
        mode_fr, text=BUSINESS_MODE_LABELS[BUSINESS_MODE_DNR], value=BUSINESS_MODE_DNR, variable=business_var,
    )
    rb_dnr.pack(anchor="w")
    ttk.Radiobutton(
        mode_fr, text=BUSINESS_MODE_LABELS[BUSINESS_MODE_JDG], value=BUSINESS_MODE_JDG, variable=business_var,
    ).pack(anchor="w")
    mode_status_var = tk.StringVar()
    ttk.Label(
        mode_fr, textvariable=mode_status_var, foreground="#1565c0", font=("Segoe UI", 8),
    ).pack(anchor="w", pady=(2, 0))

    _mode_sync = {"active": False}

    def _normalize_business_mode(mode: str) -> str:
        return mode if mode in (BUSINESS_MODE_DNR, BUSINESS_MODE_JDG) else BUSINESS_MODE_DNR

    def _refresh_settings_form() -> None:
        """Ładuje pola z dysku; tryb działalności = ustawienia księgowości (KPiR)."""
        _mode_sync["active"] = True
        try:
            s = load_settings()
            mode = effective_invoice_business_mode(s)
            business_var.set(mode)
            seller_vars["name"].set(s.seller.name)
            seller_vars["owner_name"].set(s.seller.owner_name)
            seller_vars["address"].set(s.seller.address)
            seller_vars["email"].set(s.seller.email)
            seller_vars["phone"].set(s.seller.phone)
            seller_vars["website"].set(s.seller.website)
            seller_vars["nip"].set(s.seller.nip)
            seller_vars["logo_path"].set(s.seller.logo_path)
            seller_vars["footnotes_pl"].set(resolve_footnote(mode, s.seller.footnotes_pl, "pl"))
            seller_vars["footnotes_en"].set(resolve_footnote(mode, s.seller.footnotes_en, "en"))
            pl_series = s.numbering_dnr_pl if mode == BUSINESS_MODE_DNR else s.numbering_pl
            num_pl_p.set(pl_series.prefix)
            num_pl_n.set(str(pl_series.next_number))
            en_series = s.numbering_dnr_en if mode == BUSINESS_MODE_DNR else s.numbering_en
            num_en_p.set(en_series.prefix)
            num_en_n.set(str(en_series.next_number))
            num_year.set(str(pl_series.year))
            acc = load_kpir_accounting_mode()
            if acc:
                mode_status_var.set(
                    f"Zgodnie z księgowością (KPiR: {kpir_accounting_label(acc)}): "
                    f"{business_mode_display(mode)}"
                )
            else:
                mode_status_var.set(f"Zapisany tryb: {business_mode_display(mode)}")
            _refresh_num_hint()
        finally:
            _mode_sync["active"] = False

    def _load_numbering_fields_for_mode() -> None:
        s = load_settings()
        mode = _normalize_business_mode(business_var.get())
        pl_series = s.numbering_dnr_pl if mode == BUSINESS_MODE_DNR else s.numbering_pl
        num_pl_p.set(pl_series.prefix)
        num_pl_n.set(str(pl_series.next_number))
        num_year.set(str(pl_series.year))
        en_series = s.numbering_dnr_en if mode == BUSINESS_MODE_DNR else s.numbering_en
        num_en_p.set(en_series.prefix)
        num_en_n.set(str(en_series.next_number))

    def _on_business_mode_change(*_: object) -> None:
        if _mode_sync["active"]:
            return
        mode = _normalize_business_mode(business_var.get())
        seller_vars["footnotes_pl"].set(resolve_footnote(mode, seller_vars["footnotes_pl"].get(), "pl"))
        seller_vars["footnotes_en"].set(resolve_footnote(mode, seller_vars["footnotes_en"].get(), "en"))
        mode_status_var.set(f"Zapisany tryb: {business_mode_display(mode)}")
        _load_numbering_fields_for_mode()

    business_var.trace_add("write", _on_business_mode_change)
    r += 1

    ttk.Label(set_inner, text="Adnotacja PL:").grid(row=r, column=0, sticky="nw", pady=3)
    ttk.Entry(set_inner, textvariable=seller_vars["footnotes_pl"], width=52).grid(row=r, column=1, sticky="ew", pady=3)
    r += 1
    ttk.Label(set_inner, text="Adnotacja EN:").grid(row=r, column=0, sticky="nw", pady=3)
    ttk.Entry(set_inner, textvariable=seller_vars["footnotes_en"], width=52).grid(row=r, column=1, sticky="ew", pady=3)
    r += 1

    ttk.Separator(set_inner, orient="horizontal").grid(row=r, column=0, columnspan=2, sticky="ew", pady=10)
    r += 1
    ttk.Label(set_inner, text="Numeracja dokumentów", font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=2, sticky="w", pady=(0, 6),
    )
    r += 1
    ttk.Label(set_inner, text="Seria PL (prefix / nast. nr / rok):").grid(row=r, column=0, sticky="w")
    nf = ttk.Frame(set_inner)
    nf.grid(row=r, column=1, sticky="w")
    ttk.Entry(nf, textvariable=num_pl_p, width=8).pack(side="left")
    ttk.Entry(nf, textvariable=num_pl_n, width=6).pack(side="left", padx=4)
    ttk.Entry(nf, textvariable=num_year, width=6).pack(side="left")
    r += 1
    ttk.Label(set_inner, text="Seria zagraniczna (prefix / nast. nr):").grid(row=r, column=0, sticky="w")
    nf2 = ttk.Frame(set_inner)
    nf2.grid(row=r, column=1, sticky="w")
    ttk.Entry(nf2, textvariable=num_en_p, width=8).pack(side="left")
    ttk.Entry(nf2, textvariable=num_en_n, width=6).pack(side="left", padx=4)
    r += 1
    num_hint_var = tk.StringVar()
    ttk.Label(set_inner, textvariable=num_hint_var, foreground="#666", wraplength=520).grid(
        row=r, column=0, columnspan=2, sticky="w", pady=(0, 6),
    )

    def _refresh_num_hint(*_: object) -> None:
        if business_var.get() == BUSINESS_MODE_DNR:
            num_hint_var.set(
                "DNR: PL → DN/n/rok, zagranica → DN-INV/n/rok (rachunki w języku marketu). "
                "Po przekroczeniu limitu kwartalnego — księgowanie w KPiR."
            )
        else:
            num_hint_var.set("JDG: PL → FBV/n/rok, zagranica → INV/n/rok.")

    business_var.trace_add("write", lambda *_: _refresh_num_hint())
    _refresh_num_hint()
    r += 1

    ttk.Label(set_inner, text="Podgląd faktury (język):").grid(row=r, column=0, sticky="w", pady=3)
    prev_lang_fr = ttk.Frame(set_inner)
    prev_lang_fr.grid(row=r, column=1, sticky="w")
    for code in INVOICE_LANGUAGES:
        ttk.Radiobutton(
            prev_lang_fr, text=LANGUAGE_LABELS[code], value=code, variable=preview_lang_var,
        ).pack(side="left", padx=(0, 10))
    r += 1

    def _pick_logo() -> None:
        p = filedialog.askopenfilename(
            parent=root, title="Logo",
            filetypes=[("Obrazy", "*.png *.jpg *.jpeg *.webp"), ("Wszystkie", "*.*")],
        )
        if p:
            seller_vars["logo_path"].set(p)

    def _collect_settings_from_form() -> InvoiceSettings:
        mode = business_var.get()
        foot_pl = resolve_footnote(mode, seller_vars["footnotes_pl"].get().strip(), "pl")
        foot_en = resolve_footnote(mode, seller_vars["footnotes_en"].get().strip(), "en")
        s = load_settings()
        s.seller = SellerSettings(
            name=seller_vars["name"].get().strip(),
            owner_name=seller_vars["owner_name"].get().strip(),
            address=seller_vars["address"].get().strip(),
            email=seller_vars["email"].get().strip(),
            phone=seller_vars["phone"].get().strip(),
            website=seller_vars["website"].get().strip(),
            nip=seller_vars["nip"].get().strip(),
            logo_path=seller_vars["logo_path"].get().strip(),
            business_mode=mode,  # type: ignore[arg-type]
            footnotes_pl=foot_pl,
            footnotes_en=foot_en,
            thank_you_footer_pl=s.seller.thank_you_footer_pl,
            thank_you_footer_en=s.seller.thank_you_footer_en,
        )
        presets = numbering_preset_for_mode(mode)
        pl_prefix = num_pl_p.get().strip() or presets["pl"]["prefix"]
        pl_next = int(num_pl_n.get() or "1")
        pl_year = int(num_year.get() or str(date.today().year))
        if mode == BUSINESS_MODE_DNR:
            s.numbering_dnr_pl.prefix = pl_prefix
            s.numbering_dnr_pl.next_number = pl_next
            s.numbering_dnr_pl.year = pl_year
            s.numbering_dnr_pl.format = "legacy"
            s.numbering_dnr_correction_pl.prefix = presets["correction_pl"]["prefix"]
            s.numbering_dnr_correction_pl.format = "legacy"
        else:
            s.numbering_pl.prefix = pl_prefix
            s.numbering_pl.next_number = pl_next
            s.numbering_pl.year = pl_year
            s.numbering_pl.format = "legacy"
            s.numbering_correction_pl.prefix = presets["correction_pl"]["prefix"]
            s.numbering_correction_pl.format = "legacy"
        en_prefix = num_en_p.get().strip() or (presets["en"]["prefix"] if mode != BUSINESS_MODE_DNR else "DN-INV")
        en_next = int(num_en_n.get() or "1")
        if mode == BUSINESS_MODE_DNR:
            s.numbering_dnr_en.prefix = en_prefix
            s.numbering_dnr_en.next_number = en_next
            s.numbering_dnr_en.year = pl_year
            s.numbering_dnr_en.format = "legacy"
            s.numbering_dnr_correction_en.prefix = presets["correction_en"]["prefix"]
            s.numbering_dnr_correction_en.format = "legacy"
        else:
            s.numbering_en.prefix = en_prefix
            s.numbering_en.next_number = en_next
            s.numbering_en.year = pl_year
            s.numbering_en.format = "legacy"
            s.numbering_correction_en.format = "legacy"
        return reconcile_all_series(s)

    def _save_settings() -> None:
        try:
            s = _collect_settings_from_form()
        except ValueError:
            messagebox.showerror("Ustawienia", "Nieprawidłowa numeracja (wymagane liczby całkowite).", parent=root)
            return
        save_settings(s)
        persist_business_mode_both(_normalize_business_mode(business_var.get()))
        _refresh_settings_form()
        show_toast(root, "Zapisano ustawienia (zsynchronizowano z KPiR)", bg="#1b5e20", fg="white")

    def _preview_invoice() -> None:
        win = root.winfo_toplevel()
        try:
            s = _collect_settings_from_form()
            lang = normalize_language(preview_lang_var.get())
            inv = build_sample_invoice(s, language=lang)
            mode = s.seller.business_mode or BUSINESS_MODE_DNR
            series = s.numbering_dnr_pl if lang == "pl" and mode == BUSINESS_MODE_DNR else (
                s.numbering_pl if lang == "pl" else (
                    s.numbering_dnr_en if mode == BUSINESS_MODE_DNR else s.numbering_en
                )
            )
            inv.invoice_number = format_number(series)
            folder = documents_dir_for_date(inv.issue_date)
            path = folder / f"preview-sample-{pdf_filename(inv)}"
            generate_invoice_pdf(inv, s.seller, path)
        except ValueError:
            messagebox.showerror("Podgląd faktury", "Nieprawidłowa numeracja (wymagane liczby całkowite).", parent=win)
            return
        except Exception as exc:
            messagebox.showerror("Podgląd faktury", str(exc), parent=win)
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # noqa: S606
            else:
                webbrowser.open(path.as_uri())
        except OSError as exc:
            messagebox.showerror("Podgląd faktury", f"Nie można otworzyć PDF:\n{path}\n\n{exc}", parent=win)
            return
        show_toast(root, "Otwarto podgląd PDF", bg="#1565c0", fg="white")

    def _reset_year() -> None:
        y = int(num_year.get() or date.today().year)
        s = load_settings()
        s = reset_series_year(s, y)
        save_settings(s)
        _load_numbering_fields_for_mode()
        num_en_n.set("1")
        show_toast(root, f"Zresetowano numerację na {y}", bg="#1565c0", fg="white")

    ttk.Separator(set_inner, orient="horizontal").grid(row=r, column=0, columnspan=2, sticky="ew", pady=10)
    r += 1
    from Komponenty._shared.tax_config import config_id, vat_exemption_threshold
    from Komponenty._shared.vat_exemption import vat_exemption_status

    vat_status = vat_exemption_status(int(num_year.get() or date.today().year))
    ttk.Label(set_inner, text="Próg zwolnienia z VAT", font=("Segoe UI", 11, "bold")).grid(
        row=r, column=0, columnspan=2, sticky="w", pady=(0, 6),
    )
    r += 1
    vat_msg_var = tk.StringVar(value=str(vat_status.get("message") or ""))
    ttk.Label(set_inner, textvariable=vat_msg_var, wraplength=520).grid(row=r, column=0, columnspan=2, sticky="w")
    r += 1
    ttk.Label(
        set_inner,
        text=(
            f"Obrót z wystawionych faktur + wpisów DNR bez faktury (bez MoR). "
            f"Próg bazowy {vat_exemption_threshold():,.0f} zł — przy starcie JDG w trakcie roku stosowany jest prorata ({config_id()})."
        ),
        foreground="#666",
        wraplength=520,
    ).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 8))
    r += 1

    def _refresh_vat_panel() -> None:
        try:
            y = int(num_year.get() or date.today().year)
        except ValueError:
            y = date.today().year
        st = vat_exemption_status(y)
        vat_msg_var.set(str(st.get("message") or ""))

    num_year.trace_add("write", lambda *_: _refresh_vat_panel())

    comp_frame = ttk.LabelFrame(set_inner, text=" Compliance (WSTO/OSS, KSeF, art. 28b) ", padding=8)
    comp_frame.grid(row=r, column=0, columnspan=2, sticky="ew", pady=(0, 8))
    r += 1

    def _refresh_compliance() -> None:
        for w in comp_frame.winfo_children():
            w.destroy()
        try:
            from Komponenty._shared.compliance_ui import compliance_monitors, level_color

            y = int(num_year.get() or date.today().year)
            for row in compliance_monitors(y):
                ttk.Label(
                    comp_frame,
                    text=f"{row['title']}: {row['message']}",
                    foreground=level_color(str(row.get("level") or "ok")),
                    wraplength=500,
                ).pack(anchor="w", pady=1)
        except ImportError:
            ttk.Label(comp_frame, text="Monitory niedostępne.").pack(anchor="w")

    num_year.trace_add("write", lambda *_: _refresh_compliance())
    _refresh_settings_form()
    _refresh_compliance()

    def _on_settings_tab() -> None:
        try:
            if notebook.index(notebook.select()) == notebook.index(tab_settings):
                _refresh_settings_form()
                _refresh_vat_panel()
        except tk.TclError:
            pass

    notebook.bind("<<NotebookTabChanged>>", lambda _e: _on_settings_tab())

    set_btns = ttk.Frame(set_inner)
    set_btns.grid(row=r, column=0, columnspan=2, sticky="w", pady=10)
    ttk.Button(set_btns, text="Wybierz logo", command=_pick_logo).pack(side="left", padx=(0, 8))
    ttk.Button(set_btns, text="Zapisz ustawienia", command=_save_settings).pack(side="left", padx=(0, 8))
    ttk.Button(set_btns, text="Podgląd faktury", command=_preview_invoice).pack(side="left", padx=(0, 8))
    ttk.Button(set_btns, text="Reset numeracji (rok)", command=_reset_year).pack(side="left")
    set_inner.columnconfigure(1, weight=1)

    # --- Eksport ---
    exp_frame = ttk.Frame(tab_export, padding=16)
    exp_frame.pack(fill="both", expand=True)
    ttk.Label(exp_frame, text="Eksport sprzedaży za miesiąc", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(
        exp_frame,
        text="CSV z ewidencją sprzedaży, kursami NBP i kwotami PLN.",
        foreground="#666",
    ).pack(anchor="w", pady=(4, 12))
    yr_var = tk.StringVar(value=str(date.today().year))
    mo_var = tk.StringVar(value=str(date.today().month))
    row_e = ttk.Frame(exp_frame)
    row_e.pack(anchor="w")
    ttk.Label(row_e, text="Rok:").pack(side="left")
    ttk.Entry(row_e, textvariable=yr_var, width=6).pack(side="left", padx=(4, 12))
    ttk.Label(row_e, text="Miesiąc:").pack(side="left")
    ttk.Entry(row_e, textvariable=mo_var, width=4).pack(side="left", padx=(4, 12))

    def _export() -> None:
        try:
            y = int(yr_var.get())
            m = int(mo_var.get())
            path = export_month_csv(y, m)
        except Exception as exc:
            messagebox.showerror("Eksport", str(exc), parent=root)
            return
        show_toast(root, f"Zapisano {path.name}", bg="#1b5e20", fg="white", duration_ms=3000)
        if sys.platform.startswith("win"):
            os.startfile(str(path.parent))  # noqa: S606

    ttk.Button(exp_frame, text="Eksport sprzedaży za miesiąc", command=_export).pack(anchor="w", pady=12)

    def _apply_finance_nav() -> None:
        from Komponenty._shared.finance_navigation import consume_nav

        nav = consume_nav("dokumentysprzedazy")
        if not nav:
            return
        if nav.screen == "invoice" and nav.ref:
            inv = get_invoice(nav.ref)
            if inv:
                open_invoice_editor(
                    root, inv,
                    read_only=inv.status in ("issued", "corrected", "cancelled"),
                )
            return
        if nav.screen == "orders" and nav.ref:
            notebook.select(tab_orders)
            state["pending_order_ref"].append(nav.ref)
            if state["order_by_id"]:
                root.after_idle(lambda r=nav.ref: _select_order_ref(r))
            else:
                _load_orders()

    root.after_idle(_apply_finance_nav)
    _refresh_pending_badge()

    def _on_sync_notify(new_orders: list) -> None:
        def _ui() -> None:
            n = len(new_orders)
            if n:
                first = new_orders[0].get("shopify_order_name") or "?"
                show_toast(
                    root,
                    f"Księgowość: {n} nowe zamówienie(a) Shopify (np. {first})",
                    bg="#1565c0",
                    fg="white",
                    duration_ms=4000,
                )
            _refresh_pending_badge()
            if not state["orders"]:
                _load_orders()

        root.after(0, _ui)

    register_on_new_orders(_on_sync_notify)

    def _auto_sync() -> None:
        def worker() -> None:
            try:
                sync_accounting_orders(days_back=30)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    root.after(800, _auto_sync)

    return root
