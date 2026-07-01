"""Podgląd zamówienia Shopify przed wystawieniem dokumentu."""

from __future__ import annotations

from typing import Any, Callable

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from Komponenty._shared.accounting_mode_sync import effective_invoice_business_mode
from Komponenty._shared.window_geometry import position_toplevel_screen_center

from .constants import BUSINESS_MODE_DNR
from .country import suggest_language
from .email_compose import compose_hint, open_compose_email, order_confirmation_body, shop_sender_email
from .i18n import LANGUAGE_LABELS, normalize_language
from .invoice_builder import doc_type_label_for
from .order_attributes import parse_invoice_request
from .shopify_orders import order_to_row
from .storage import load_settings
from .ui_labels import issue_button_label


def _format_order_summary(order: dict[str, Any], row) -> str:
    lines = [
        f"Zamówienie: {order.get('name') or '—'}",
        f"Data: {(order.get('created_at') or '')[:19]}",
        f"Płatność: {order.get('financial_status') or '—'} · Fulfillment: {order.get('fulfillment_status') or '—'}",
        f"Klient: {row.customer_name} <{row.customer_email}>",
        f"Kraj dostawy: {row.shipping_country} → język dokumentu: {LANGUAGE_LABELS.get(row.suggested_language, row.suggested_language)}",
        f"Suma: {row.order_total:.2f} {row.currency}",
        "",
        "Pozycje:",
    ]
    for li in order.get("line_items") or []:
        qty = li.get("quantity") or 1
        price = li.get("price") or "0"
        lines.append(f"  · {li.get('name') or li.get('title')} × {qty} @ {price}")
    ship = (order.get("total_shipping_price_set") or {}).get("shop_money", {}).get("amount")
    if ship and float(ship) > 0:
        lines.append(f"  · Wysyłka: {ship}")
    note = (order.get("note") or "").strip()
    if note:
        lines.extend(["", f"Notatka zamówienia: {note}"])
    attrs = parse_invoice_request(order)
    if attrs.requested:
        kind = "firma" if attrs.customer_type == "company" else "osoba prywatna"
        lines.extend([
            "",
            f"★ Klient prosi o fakturę ({kind})",
        ])
        if attrs.company_name:
            lines.append(f"  Firma: {attrs.company_name}")
        if attrs.tax_id:
            lines.append(f"  NIP/VAT: {attrs.tax_id}")
    return "\n".join(lines)


def open_order_review(
    parent: tk.Misc,
    order: dict[str, Any],
    *,
    on_issue: Callable[[], None],
    on_refresh: Callable[[], None] | None = None,
) -> None:
    """Dialog przeglądu zamówienia — przed edytorem faktury/rachunku."""
    settings = load_settings()
    mode = effective_invoice_business_mode(settings)
    row = order_to_row(order)
    lang = normalize_language(row.suggested_language or suggest_language(row.shipping_country))
    doc_title = doc_type_label_for(settings, lang)

    dlg = tk.Toplevel(parent)
    dlg.title(f"Przegląd zamówienia {order.get('name') or ''}")
    position_toplevel_screen_center(dlg, 720, 640)
    dlg.transient(parent.winfo_toplevel())
    dlg.grab_set()

    top = ttk.Frame(dlg, padding=12)
    top.pack(fill="both", expand=True)

    if row.invoice_requested:
        ttk.Label(
            top,
            text="Klient zaznaczył „Chcę fakturę” — po wystawieniu wyślij dokument e-mailem.",
            foreground="#1565c0",
            font=("Segoe UI", 9, "bold"),
            wraplength=660,
        ).pack(anchor="w", pady=(0, 8))

    if row.fulfillment_status and row.fulfillment_status != "unfulfilled":
        ttk.Label(
            top,
            text=f"Uwaga: fulfillment = {row.fulfillment_status} (zamówienie może być już w realizacji).",
            foreground="#e65100",
            wraplength=660,
        ).pack(anchor="w", pady=(0, 6))

    ttk.Label(top, text=f"Planowany dokument: {doc_title} ({LANGUAGE_LABELS.get(lang, lang)})").pack(
        anchor="w", pady=(0, 6),
    )

    summary = scrolledtext.ScrolledText(top, height=14, font=("Consolas", 9), wrap="word")
    summary.pack(fill="both", expand=True, pady=(0, 8))
    summary.insert("1.0", _format_order_summary(order, row))
    summary.configure(state="disabled")

    msg_frame = ttk.LabelFrame(top, text="Wiadomość do kupującego (opcjonalnie)", padding=8)
    msg_frame.pack(fill="x", pady=(0, 8))

    eta_row = ttk.Frame(msg_frame)
    eta_row.pack(fill="x", pady=(0, 6))
    eta_var = tk.BooleanVar(value=False)
    days_var = tk.StringVar(value="3")

    def _sync_eta_controls(*_args: object) -> None:
        state = "readonly" if eta_var.get() else "disabled"
        days_combo.configure(state=state)

    def _refresh_message(*_args: object) -> None:
        days: int | None = None
        if eta_var.get():
            try:
                days = int(days_var.get())
            except ValueError:
                days = 3
        msg_txt.delete("1.0", "end")
        msg_txt.insert(
            "1.0",
            order_confirmation_body(
                str(order.get("name") or ""),
                settings,
                language=lang,
                production_days=days,
            ),
        )

    ttk.Checkbutton(
        eta_row,
        text="Szacowany czas realizacji",
        variable=eta_var,
        command=_refresh_message,
    ).pack(side="left")
    days_combo = ttk.Combobox(
        eta_row,
        textvariable=days_var,
        values=[str(d) for d in range(1, 8)],
        width=3,
        state="disabled",
    )
    days_combo.pack(side="left", padx=(8, 4))
    ttk.Label(eta_row, text="dni").pack(side="left")
    days_combo.bind("<<ComboboxSelected>>", _refresh_message)
    eta_var.trace_add("write", _sync_eta_controls)

    msg_txt = tk.Text(msg_frame, height=5, font=("Segoe UI", 9))
    msg_txt.pack(fill="x")
    _refresh_message()

    btns = ttk.Frame(dlg, padding=12)
    btns.pack(fill="x")

    def _mailto() -> None:
        email = row.customer_email or ""
        if not email:
            messagebox.showinfo("E-mail", "Brak adresu e-mail klienta w zamówieniu.", parent=dlg)
            return
        body = msg_txt.get("1.0", "end").strip()
        subj = f"Zamówienie {order.get('name') or ''} — GicleeArt"
        try:
            result = open_compose_email(
                to=email,
                subject=subj,
                body=body,
                sender=shop_sender_email(settings),
            )
            from Komponenty._shared.toast import show_toast
            show_toast(dlg, compose_hint(result), bg="#1565c0", fg="white", duration_ms=3500)
        except ValueError as exc:
            messagebox.showerror("E-mail", str(exc), parent=dlg)

    def _proceed() -> None:
        dlg.destroy()
        on_issue()

    issue_lbl = issue_button_label(mode, preview=True)
    ttk.Button(btns, text=f"Napisz z {shop_sender_email(settings)}", command=_mailto).pack(side="left", padx=(0, 8))
    ttk.Button(btns, text=issue_lbl, command=_proceed).pack(side="right", padx=(8, 0))
    ttk.Button(btns, text="Anuluj", command=dlg.destroy).pack(side="right")
