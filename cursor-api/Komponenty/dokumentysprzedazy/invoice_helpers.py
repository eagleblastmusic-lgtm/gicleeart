"""Wspólna logika statusów i dat faktur (KPiR, DNR, pipeline)."""

from __future__ import annotations

from .constants import SALES_CHANNEL_TEST
from .models import InvoiceRecord

BOOKABLE_INVOICE_STATUSES = frozenset({"issued", "corrected"})


def is_test_invoice(inv: InvoiceRecord) -> bool:
    return bool(getattr(inv, "is_test", False)) or inv.sales_channel == SALES_CHANNEL_TEST


def is_bookable_invoice(inv: InvoiceRecord) -> bool:
    """Wystawiona faktura do importu DNR / KPiR (także testowa)."""
    return inv.status in BOOKABLE_INVOICE_STATUSES


def is_production_bookable_invoice(inv: InvoiceRecord) -> bool:
    """Jak is_bookable_invoice, ale bez dokumentów testowych (checklist, zamknięcie miesiąca)."""
    return is_bookable_invoice(inv) and not is_test_invoice(inv)


def invoice_kpir_event_date(inv: InvoiceRecord) -> str:
    """Data wpisu KPiR i kursu NBP — preferuje datę wpływu (PIT kasowy)."""
    if inv.payment_date:
        return inv.payment_date[:10]
    if inv.sale_date:
        return inv.sale_date[:10]
    return (inv.issue_date or "")[:10]


def invoice_limit_event_date(inv: InvoiceRecord) -> str:
    """Data przychodu należnego (limit kwartalny DNR)."""
    if inv.sale_date:
        return inv.sale_date[:10]
    return (inv.issue_date or "")[:10]


def invoice_amount_pln(inv: InvoiceRecord) -> float:
    if inv.status == "corrected" and inv.amount_after_correction:
        return round(float(inv.amount_after_correction), 2)
    if inv.exchange and inv.exchange.total_amount_pln > 0:
        return round(float(inv.exchange.total_amount_pln), 2)
    return round(float(inv.order_total or 0), 2)


def invoice_kpir_amount_pln(inv: InvoiceRecord, *, vat_status: str = "exempt") -> float:
    """Przychód KPiR z faktury — netto gdy czynny VAT (jak Shopify)."""
    gross_pln = invoice_amount_pln(inv)
    if str(vat_status) != "active":
        return gross_pln
    gross_order = float(inv.order_total or 0)
    net_order = float(inv.products_total_net or 0)
    if net_order > 0 and gross_order > 0 and abs(gross_order - net_order) > 0.009:
        return round(gross_pln * (net_order / gross_order), 2)
    if inv.total_tax > 0 and gross_order > 0:
        tax_share = float(inv.total_tax) / gross_order
        return round(gross_pln * (1.0 - tax_share), 2)
    return gross_pln
