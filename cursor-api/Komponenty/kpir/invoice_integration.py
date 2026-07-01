"""Integracja faktur bez VAT → wpisy KPiR."""

from __future__ import annotations

from Komponenty.dokumentysprzedazy.invoice_helpers import (
    is_bookable_invoice,
    invoice_kpir_amount_pln,
    invoice_kpir_event_date,
)
from Komponenty.dokumentysprzedazy.models import InvoiceRecord
from Komponenty.dokumentysprzedazy.storage import get_invoice

from .entry_service import create_entry, post_entry
from .ksef_service import apply_ksef_on_booking
from .sales_chain import uses_dnr_sales_chain
from .storage import posted_entry_for_invoice, posted_entry_for_order
from .validation import ValidationError


def can_book_invoice(invoice: InvoiceRecord, *, bypass_dnr_chain: bool = False) -> tuple[bool, str]:
    if uses_dnr_sales_chain() and not bypass_dnr_chain:
        return False, "przychody księguj z DNR (import DNR → KPiR), nie bezpośrednio z faktury"
    if not is_bookable_invoice(invoice):
        return False, f"status faktury: {invoice.status}"
    if posted_entry_for_invoice(invoice.id):
        return False, "już ujęta w KPiR"
    if invoice.shopify_order_id and posted_entry_for_order(invoice.shopify_order_id):
        return False, "zamówienie już ujęte w KPiR (bez faktury)"
    return True, "ok"


def create_entry_from_invoice(invoice: InvoiceRecord, *, post: bool = True, bypass_dnr_chain: bool = False):
    ok, reason = can_book_invoice(invoice, bypass_dnr_chain=bypass_dnr_chain)
    if not ok:
        raise ValidationError(f"Nie można ująć faktury: {reason}")

    ex = invoice.exchange
    from .storage import load_settings

    settings = load_settings()
    amount_pln = invoice_kpir_amount_pln(invoice, vat_status=settings.vat_status)
    country = invoice.shipping_address.country_code or invoice.buyer.country_code
    ksef_number, contractor_nip = apply_ksef_on_booking(invoice)

    entry = create_entry(
        event_date=invoice_kpir_event_date(invoice),
        document_number=invoice.invoice_number or invoice.shopify_order_name,
        ksef_number=ksef_number,
        contractor=invoice.buyer.name or "Klient",
        contractor_nip=contractor_nip,
        contractor_address=invoice.buyer.address_lines,
        description=(
            f"Faktura bez VAT {invoice.invoice_number}"
            + (f" — {invoice.shopify_order_name}" if invoice.shopify_order_name else " — sprzedaż poza Shopify")
        ),
        revenue_goods=amount_pln,
        source="invoice",
        entry_type="revenue",
        original_currency=invoice.currency,
        original_amount=invoice.order_total,
        nbp_rate=ex.exchange_rate_value,
        nbp_rate_date=ex.exchange_rate_date,
        nbp_table_number=ex.exchange_rate_table_number,
        amount_pln=amount_pln,
        nbp_status=ex.exchange_rate_status,
        country=country,
        shopify_order_id=invoice.shopify_order_id,
        shopify_order_name=invoice.shopify_order_name,
        invoice_id=invoice.id,
        attachments=[invoice.pdf_path] if invoice.pdf_path else [],
    )
    if post:
        return post_entry(entry)
    return entry


def create_entry_from_invoice_id(invoice_id: str, *, post: bool = True):
    inv = get_invoice(invoice_id)
    if not inv:
        raise ValidationError("Nie znaleziono faktury.")
    return create_entry_from_invoice(inv, post=post)
