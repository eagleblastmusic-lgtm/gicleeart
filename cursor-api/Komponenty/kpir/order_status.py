"""Status KPiR dla zamówień i faktur — integracja z dokumentysprzedazy."""

from __future__ import annotations

from .models import InvoiceKpirInfo, OrderKpirInfo
from .storage import is_order_skipped, posted_entry_for_invoice, posted_entry_for_order


def get_order_kpir_status(shopify_order_id: int) -> OrderKpirInfo:
    if is_order_skipped(shopify_order_id):
        return OrderKpirInfo(shopify_order_id=shopify_order_id, status="skipped")
    entry = posted_entry_for_order(shopify_order_id)
    if entry:
        return OrderKpirInfo(
            shopify_order_id=shopify_order_id,
            status="booked",
            entry_id=entry.id,
            entry_number=entry.entry_number,
            amount_pln=entry.amount_pln or entry.total_revenue,
            nbp_rate=entry.nbp_rate,
            nbp_rate_date=entry.nbp_rate_date,
        )
    return OrderKpirInfo(shopify_order_id=shopify_order_id, status="not_booked")


def get_invoice_kpir_status(invoice_id: str) -> InvoiceKpirInfo:
    entry = posted_entry_for_invoice(invoice_id)
    if entry:
        return InvoiceKpirInfo(
            invoice_id=invoice_id,
            status="booked",
            entry_id=entry.id,
            entry_number=entry.entry_number,
        )
    return InvoiceKpirInfo(invoice_id=invoice_id, status="not_booked")
