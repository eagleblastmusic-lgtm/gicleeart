"""Dialog podglądu/edycji faktury przed wystawieniem."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from Komponenty._shared.tk_scroll import bind_mousewheel_to_canvas
from Komponenty._shared.toast import show_toast
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from Komponenty._shared.accounting_mode_sync import effective_invoice_business_mode

from .constants import BUSINESS_MODE_DNR, DEFAULT_FOOTNOTES
from .email_compose import (
    EmailDeliveryError,
    compose_hint,
    invoice_send_prompt,
    send_invoice_email,
    shop_sender_email,
)
from .i18n import INVOICE_LANGUAGES, LANGUAGE_LABELS, PRODUCT_PLACEHOLDER, all_default_footnotes_for_lang
from .invoice_builder import default_footnote, doc_type_label_for
from .invoice_helpers import is_test_invoice
from .ui_labels import editor_title, send_label_for_mode
from .invoice_service import (
    InvoiceValidationError,
    issue_invoice,
    mark_pdf_downloaded,
    mark_pdf_sent,
    refresh_exchange,
)
from .models import InvoiceItem, InvoiceRecord, PartyDetails
from .pdf_generator import generate_invoice_pdf, pdf_filename
from .storage import documents_dir_for_date, load_settings, save_invoice


def _parse_buyer_text(text: str, current: PartyDetails) -> PartyDetails:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return current
    name = lines[0]
    email = current.email
    address_lines: list[str] = []
    for line in lines[1:]:
        if "@" in line and "." in line.split("@")[-1]:
            email = line
        else:
            address_lines.append(line)
    country = current.country_code or "PL"
    if address_lines:
        last = address_lines[-1].upper()
        if len(last) == 2 and last.isalpha():
            country = last
    return PartyDetails(
        name=name,
        email=email,
        address_lines="\n".join(address_lines),
        country_code=country,
        nip=current.nip,
    )


def open_invoice_editor(
    parent: tk.Misc,
    invoice: InvoiceRecord,
    *,
    on_saved: Callable[[InvoiceRecord], None] | None = None,
    read_only: bool = False,
) -> None:
    settings = load_settings()
    is_test = is_test_invoice(invoice)
    biz_mode = effective_invoice_business_mode(settings)
    dlg = tk.Toplevel(parent)
    if is_test:
        dlg.title("Faktura testowa" if not read_only and not invoice.locked else "Podgląd faktury testowej")
    else:
        dlg.title(editor_title(biz_mode, read_only=read_only or invoice.locked))
    position_toplevel_screen_center(dlg, 900, 720)
    dlg.minsize(760, 560)
    dlg.transient(parent.winfo_toplevel())
    dlg.grab_set()

    state: dict[str, Any] = {"invoice": invoice}

    top = ttk.Frame(dlg, padding=10)
    top.pack(fill="x", side="top")
    if is_test:
        ttk.Label(
            top,
            text="DOKUMENT TESTOWY — można księgować w DNR/KPiR (test przepływu). Nie trafia do eksportu ani licznika VAT. W pełni usuwalny (DNR/KPiR razem z fakturą).",
            foreground="#b71c1c",
            font=("Segoe UI", 9, "bold"),
            wraplength=820,
        ).pack(anchor="w")

    btns = ttk.Frame(dlg, padding=10)
    btns.pack(fill="x", side="bottom")

    body = ttk.Frame(dlg)
    body.pack(fill="both", expand=True)

    canvas = tk.Canvas(body, highlightthickness=0)
    vsb = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
    inner = ttk.Frame(canvas, padding=12)
    inner.columnconfigure(0, weight=0)
    inner.columnconfigure(1, weight=1, minsize=420)
    win = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")

    def _on_cfg(_e: tk.Event | None = None) -> None:
        canvas.configure(scrollregion=canvas.bbox("all"))
        w = max(canvas.winfo_width(), 720)
        canvas.itemconfigure(win, width=w)

    inner.bind("<Configure>", _on_cfg)
    canvas.bind("<Configure>", _on_cfg)
    bind_mousewheel_to_canvas(canvas, inner)

    header_txt = invoice.shopify_order_name or (
        "Sprzedaż poza Shopify" if not invoice.shopify_order_id else invoice.shopify_order_name
    )
    ttk.Label(top, text=header_txt, font=("Segoe UI", 12, "bold")).pack(side="left")
    if invoice.invoice_requested:
        inv_kind = "Firma" if invoice.invoice_customer_type == "company" else "Osoba prywatna"
        ttk.Label(top, text=f"· Klient chce fakturę ({inv_kind})", foreground="#1565c0").pack(
            side="left", padx=(10, 0),
        )

    row = 0
    lang_var = tk.StringVar(value=invoice.language)
    doc_type_var = tk.StringVar(value=invoice.doc_type_label)
    issue_var = tk.StringVar(value=invoice.issue_date)
    sale_var = tk.StringVar(value=invoice.sale_date)
    payment_var = tk.StringVar(value=(invoice.payment_date or "")[:10])
    footnote_var = tk.StringVar(value=invoice.footnote)

    def _sync_footnote_from_settings() -> None:
        if read_only or invoice.locked:
            return
        current = footnote_var.get().strip()
        known = all_default_footnotes_for_lang(invoice.language)
        if not current or current in known:
            footnote_var.set(default_footnote(settings, invoice.language))

    _sync_footnote_from_settings()

    def _grid_label(text: str, r: int) -> None:
        ttk.Label(inner, text=text).grid(row=r, column=0, sticky="nw", padx=(0, 8), pady=4)

    doc_values = [
        doc_type_label_for(settings, code, is_correction=invoice.doc_kind == "correction")
        for code in INVOICE_LANGUAGES
    ]
    _grid_label("Typ dokumentu:", row)
    doc_combo = ttk.Combobox(
        inner, textvariable=doc_type_var, width=40,
        values=sorted(set(doc_values)), state="readonly",
    )
    doc_combo.grid(row=row, column=1, sticky="ew", pady=4)
    row += 1

    _grid_label("Język:", row)
    lang_frame = ttk.Frame(inner)
    lang_frame.grid(row=row, column=1, sticky="w")
    for code in INVOICE_LANGUAGES:
        ttk.Radiobutton(
            lang_frame, text=LANGUAGE_LABELS[code], value=code, variable=lang_var,
            command=lambda c=code: _on_lang(c),
            state="disabled" if read_only else "normal",
        ).pack(side="left", padx=(0, 8))
    row += 1

    def _on_lang(code: str) -> None:
        inv = state["invoice"]
        inv.language = code  # type: ignore[assignment]
        doc_type_var.set(doc_type_label_for(
            settings, code, is_correction=inv.doc_kind == "correction",
        ))
        inv.doc_type_label = doc_type_var.get()
        if not read_only and not invoice.locked:
            footnote_var.set(default_footnote(settings, code))

    _grid_label("Data wystawienia:", row)
    ttk.Entry(inner, textvariable=issue_var, width=16).grid(row=row, column=1, sticky="w", pady=4)
    row += 1
    _grid_label("Data sprzedaży:", row)
    ttk.Entry(inner, textvariable=sale_var, width=16).grid(row=row, column=1, sticky="w", pady=4)
    row += 1
    _grid_label("Data wpływu (opcj.):", row)
    ttk.Entry(inner, textvariable=payment_var, width=16).grid(row=row, column=1, sticky="w", pady=4)
    row += 1
    ttk.Label(
        inner,
        text="Puste = nieopłacone (DNR: brak wpływu kasowego do PIT).",
        foreground="#666",
        font=("Segoe UI", 8),
        wraplength=520,
    ).grid(row=row, column=1, sticky="w", pady=(0, 4))
    row += 1

    _grid_label("Nabywca:", row)
    buyer_txt = tk.Text(inner, height=4, width=60, font=("Segoe UI", 9))
    buyer_txt.grid(row=row, column=1, sticky="ew", pady=4)
    buyer_hint = "Imię i nazwa / firma\nAdres (ulica, kod, miasto, kraj)\nE-mail"
    if invoice.buyer.name or invoice.buyer.address_lines or invoice.buyer.email:
        buyer_txt.insert("1.0", f"{invoice.buyer.name}\n{invoice.buyer.address_lines}\n{invoice.buyer.email}".strip())
    elif not invoice.shopify_order_id and not read_only:
        buyer_txt.insert("1.0", buyer_hint)
        buyer_txt.configure(foreground="#666")
    if read_only:
        buyer_txt.configure(state="disabled")
    row += 1

    ksef_var = tk.StringVar(value=invoice.ksef_number or "")
    buyer_nip_var = tk.StringVar(value=invoice.buyer.nip if invoice.buyer else "")
    ksef_editable = invoice.status in ("issued", "corrected") or (not read_only and not invoice.locked)

    _grid_label("NIP nabywcy (B2B):", row)
    nip_entry = ttk.Entry(inner, textvariable=buyer_nip_var, width=24)
    nip_entry.grid(row=row, column=1, sticky="w", pady=4)
    if not ksef_editable:
        nip_entry.configure(state="disabled")
    row += 1

    _grid_label("Nr KSeF:", row)
    ksef_entry = ttk.Entry(inner, textvariable=ksef_var, width=50)
    ksef_entry.grid(row=row, column=1, sticky="ew", pady=4)
    if not ksef_editable:
        ksef_entry.configure(state="disabled")
    ttk.Label(
        inner,
        text="Numer e-faktury z KSeF (obowiązkowy dla B2B od 2026). Po wystawieniu można uzupełnić i zsynchronizować z KPiR.",
        foreground="#666",
        font=("Segoe UI", 8),
        wraplength=520,
    ).grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
    row += 2

    is_manual = not invoice.shopify_order_id and invoice.doc_kind == "invoice"
    item_name_var = tk.StringVar(value=invoice.items[0].name if invoice.items else "")
    amount_var = tk.StringVar(value=f"{invoice.order_total:.2f}" if invoice.order_total else "0")
    currency_var = tk.StringVar(value=invoice.currency or "PLN")
    country_var = tk.StringVar(value=invoice.buyer.country_code or "PL")

    if is_manual and not read_only:
        _grid_label("Nazwa pozycji:", row)
        ttk.Entry(inner, textvariable=item_name_var, width=50).grid(
            row=row, column=1, sticky="ew", pady=4,
        )
        row += 1
        _grid_label("Kwota:", row)
        amount_row = ttk.Frame(inner)
        amount_row.grid(row=row, column=1, sticky="w", pady=4)
        ttk.Entry(
            amount_row,
            textvariable=amount_var,
            width=16,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(0, 10))
        ttk.Combobox(
            amount_row, textvariable=currency_var, values=["PLN", "EUR", "USD", "GBP"], width=8,
        ).pack(side="left", padx=(0, 10))
        ttk.Label(amount_row, text="Kraj nabywcy:").pack(side="left")
        ttk.Entry(amount_row, textvariable=country_var, width=5).pack(side="left", padx=(6, 0))
        row += 1

    _grid_label("Adnotacja bez VAT:", row)
    ttk.Entry(inner, textvariable=footnote_var, width=60).grid(row=row, column=1, sticky="ew", pady=4)
    row += 1

    _grid_label("Pozycje:", row)
    items_frame = ttk.Frame(inner)
    items_frame.grid(row=row, column=1, sticky="ew", pady=4)
    cols = ("lp", "name", "qty", "price", "disc", "amt")
    tree = ttk.Treeview(items_frame, columns=cols, show="headings", height=6)
    for c, h, w in [
        ("lp", "Lp", 30), ("name", "Nazwa", 220), ("qty", "Ilość", 50),
        ("price", "Cena", 70), ("disc", "Rabat", 60), ("amt", "Wartość", 70),
    ]:
        tree.heading(c, text=h)
        tree.column(c, width=w)
    for it in invoice.items:
        tree.insert("", "end", values=(
            it.position, it.name, it.quantity, f"{it.unit_price:.2f}",
            f"{it.discount:.2f}", f"{it.amount:.2f}",
        ))
    tree.pack(fill="x")
    row += 1

    fx_var = tk.StringVar()
    if invoice.currency.upper() != "PLN":
        fx = invoice.exchange
        fx_var.set(
            f"Kurs NBP: 1 {invoice.currency} = {fx.exchange_rate_value:.4f} PLN "
            f"({fx.exchange_rate_date}, tabela {fx.exchange_rate_table_number or '—'}) · "
            f"Ewidencja PLN: {fx.total_amount_pln:.2f} · status: {fx.exchange_rate_status}"
        )
        _grid_label("Przeliczenie PLN:", row)
        ttk.Label(inner, textvariable=fx_var, wraplength=520, foreground="#1565c0").grid(
            row=row, column=1, sticky="w", pady=4,
        )
        row += 1

    _grid_label("Suma:", row)
    sum_var = tk.StringVar(value=f"{invoice.order_total:.2f} {invoice.currency or 'PLN'}")
    ttk.Label(
        inner,
        textvariable=sum_var,
        font=("Segoe UI", 11, "bold"),
    ).grid(row=row, column=1, sticky="w")
    row += 1

    def _parse_amount_text(raw: str) -> float:
        try:
            return round(float(raw.replace(",", ".").replace(" ", "")), 2)
        except ValueError:
            return 0.0

    def _default_item_name() -> str:
        return item_name_var.get().strip() or (
            PRODUCT_PLACEHOLDER[lang_var.get()] if lang_var.get() in PRODUCT_PLACEHOLDER else PRODUCT_PLACEHOLDER["en"]
        )

    def _refresh_manual_totals(*_args: object) -> None:
        if not is_manual or read_only:
            return
        amount = _parse_amount_text(amount_var.get())
        cur = (currency_var.get() or "PLN").upper()
        sum_var.set(f"{amount:.2f} {cur}")
        name = _default_item_name()
        for i in tree.get_children():
            tree.delete(i)
        tree.insert("", "end", values=(1, name, 1, f"{amount:.2f}", "0.00", f"{amount:.2f}"))

    if is_manual and not read_only:
        for var in (amount_var, item_name_var, currency_var):
            var.trace_add("write", _refresh_manual_totals)
        _refresh_manual_totals()

    def _refresh_canvas_width() -> None:
        _on_cfg()
        dlg.update_idletasks()

    dlg.after_idle(_refresh_canvas_width)

    def _collect() -> InvoiceRecord:
        inv: InvoiceRecord = state["invoice"]
        inv.doc_type_label = doc_type_var.get()
        inv.language = lang_var.get()  # type: ignore[assignment]
        inv.issue_date = issue_var.get().strip()
        inv.sale_date = sale_var.get().strip()
        paid_raw = payment_var.get().strip()
        if paid_raw:
            inv.payment_date = paid_raw[:10] + "T12:00:00"
        else:
            inv.payment_date = ""
        inv.footnote = footnote_var.get().strip()
        if not read_only:
            inv.buyer = _parse_buyer_text(buyer_txt.get("1.0", "end"), inv.buyer)
            inv.shipping_address = inv.buyer
        inv.ksef_number = ksef_var.get().strip()
        if inv.buyer:
            inv.buyer.nip = buyer_nip_var.get().strip()
        if is_manual and not read_only:
            try:
                amount = round(float(amount_var.get().replace(",", ".").replace(" ", "")), 2)
            except ValueError:
                amount = 0.0
            name = item_name_var.get().strip() or PRODUCT_PLACEHOLDER.get(inv.language, PRODUCT_PLACEHOLDER["en"])
            cur = (currency_var.get() or "PLN").upper()
            cc = (country_var.get() or "PL").upper()
            inv.buyer.country_code = cc
            inv.shipping_address.country_code = cc
            inv.items = [InvoiceItem(1, name, 1, amount, 0, amount)]
            inv.products_total = amount
            inv.shipping_total = 0
            inv.discounts_total = 0
            inv.order_total = amount
            inv.currency = cur
            inv.is_foreign = cur != "PLN" or cc != "PL"
            inv.is_eu_b2c = inv.is_foreign
            inv = refresh_exchange(inv)
            state["invoice"] = inv
            for i in tree.get_children():
                tree.delete(i)
            for it in inv.items:
                tree.insert("", "end", values=(
                    it.position, it.name, it.quantity, f"{it.unit_price:.2f}",
                    f"{it.discount:.2f}", f"{it.amount:.2f}",
                ))
            if inv.currency.upper() != "PLN":
                fx = inv.exchange
                fx_var.set(
                    f"Kurs NBP: 1 {inv.currency} = {fx.exchange_rate_value:.4f} PLN "
                    f"({fx.exchange_rate_date}, tabela {fx.exchange_rate_table_number or '—'}) · "
                    f"Ewidencja PLN: {fx.total_amount_pln:.2f} · status: {fx.exchange_rate_status}"
                )
            sum_var.set(f"{inv.order_total:.2f} {inv.currency}")
        inv.updated_at = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        return inv

    def _fetch_nbp() -> None:
        inv = refresh_exchange(_collect())
        state["invoice"] = inv
        if inv.currency.upper() != "PLN":
            fx = inv.exchange
            fx_var.set(
                f"Kurs NBP: 1 {inv.currency} = {fx.exchange_rate_value:.4f} PLN "
                f"({fx.exchange_rate_date}) · PLN: {fx.total_amount_pln:.2f}"
            )
        show_toast(dlg, "Zaktualizowano kurs NBP", bg="#1b5e20", fg="white")

    def _manual_rate() -> None:
        from tkinter import simpledialog
        val = simpledialog.askstring("Kurs ręczny", "PLN za 1 jednostkę waluty:", parent=dlg)
        if not val:
            return
        try:
            rate = float(val.replace(",", "."))
        except ValueError:
            messagebox.showerror("Błąd", "Niepoprawny kurs.", parent=dlg)
            return
        inv = refresh_exchange(_collect(), manual_rate=rate)
        state["invoice"] = inv
        show_toast(dlg, "Ustawiono kurs ręczny", bg="#e65100", fg="white")

    def _issue() -> None:
        inv = _collect()
        if is_manual and inv.order_total <= 0:
            messagebox.showerror("Nie można wystawić", "Podaj kwotę sprzedaży.", parent=dlg)
            return
        try:
            issued = issue_invoice(inv)
        except InvoiceValidationError as exc:
            messagebox.showerror("Nie można wystawić", str(exc), parent=dlg)
            return
        except Exception as exc:
            messagebox.showerror("Nie można wystawić", f"{type(exc).__name__}: {exc}", parent=dlg)
            return
        state["invoice"] = issued
        show_toast(dlg, f"Wystawiono {issued.invoice_number}", bg="#1b5e20", fg="white", duration_ms=2800)
        if on_saved:
            on_saved(issued)
        if issued.invoice_requested and issued.buyer.email:
            if messagebox.askyesno(
                send_label_for_mode(biz_mode),
                invoice_send_prompt(issued.buyer.email),
                parent=dlg,
            ):
                try:
                    result = send_invoice_email(issued)
                    mark_pdf_sent(issued.id)
                    show_toast(dlg, compose_hint(result), bg="#1565c0", fg="white", duration_ms=4000)
                except (ValueError, EmailDeliveryError) as exc:
                    messagebox.showerror("E-mail", str(exc), parent=dlg)
        elif not issued.invoice_requested:
            show_toast(
                dlg,
                "Zapisano wewnętrznie — klient nie prosił o fakturę.",
                bg="#455a64",
                fg="white",
                duration_ms=3500,
            )
        dlg.destroy()

    def _preview_pdf() -> None:
        inv = _collect()
        folder = documents_dir_for_date(inv.issue_date)
        path = folder / f"preview-{pdf_filename(inv)}"
        generate_invoice_pdf(inv, settings.seller, path)
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606
        else:
            webbrowser.open(path.as_uri())

    def _open_pdf() -> None:
        inv = state["invoice"]
        if not inv.pdf_path or not os.path.isfile(inv.pdf_path):
            messagebox.showinfo("PDF", "Brak pliku PDF.", parent=dlg)
            return
        mark_pdf_downloaded(inv.id)
        if sys.platform.startswith("win"):
            os.startfile(inv.pdf_path)  # noqa: S606
        else:
            webbrowser.open(Path(inv.pdf_path).as_uri())

    def _send_email() -> None:
        inv = state["invoice"]
        if not inv.pdf_path:
            messagebox.showinfo("E-mail", "Najpierw wystaw dokument.", parent=dlg)
            return
        try:
            result = send_invoice_email(inv)
        except (ValueError, EmailDeliveryError) as exc:
            messagebox.showerror("E-mail", str(exc), parent=dlg)
            return
        mark_pdf_sent(inv.id)
        show_toast(dlg, compose_hint(result), bg="#1565c0", fg="white")

    def _save_ksef() -> None:
        from Komponenty.kpir.ksef_service import set_invoice_ksef

        inv = state["invoice"]
        if inv.status not in ("issued", "corrected"):
            messagebox.showinfo("KSeF", "Numer KSeF zapisuje się po wystawieniu faktury.", parent=dlg)
            return
        try:
            updated = set_invoice_ksef(
                inv.id,
                ksef_var.get(),
                buyer_nip=buyer_nip_var.get(),
            )
            state["invoice"] = updated
            show_toast(dlg, "Zapisano KSeF i zsynchronizowano z KPiR", bg="#1b5e20", fg="white")
            if on_saved:
                on_saved(updated)
        except Exception as exc:
            messagebox.showerror("KSeF", str(exc), parent=dlg)

    if not read_only and not invoice.locked:
        ttk.Button(btns, text="Pobierz kurs NBP", command=_fetch_nbp).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Kurs ręcznie", command=_manual_rate).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Podgląd PDF", command=_preview_pdf).pack(side="left", padx=(0, 6))
        issue_lbl = "Wystaw (test)" if is_test else (
            "Wystaw rachunek" if biz_mode == BUSINESS_MODE_DNR else "Wystaw fakturę bez VAT"
        )
        ttk.Button(btns, text=issue_lbl, command=_issue).pack(side="right", padx=(6, 0))
    else:
        ttk.Button(btns, text="Otwórz PDF", command=_open_pdf).pack(side="left", padx=(0, 6))
        if invoice.status in ("issued", "corrected"):
            ttk.Button(btns, text="Zapisz KSeF", command=_save_ksef).pack(side="left", padx=(0, 6))
        if not is_test:
            send_lbl = send_label_for_mode(biz_mode)
            ttk.Button(btns, text=send_lbl, command=_send_email).pack(side="left", padx=(0, 6))

    ttk.Button(btns, text="Zamknij", command=dlg.destroy).pack(side="right")
