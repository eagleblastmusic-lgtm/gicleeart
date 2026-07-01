"""Status przepływu sprzedaży: Shopify → faktura → DNR → KPiR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Komponenty.dokumentysprzedazy.models import InvoiceRecord
from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
from Komponenty.dokumentysprzedazy.storage import invoices_for_order

from .invoice_list import unbooked_invoices
from .sales_chain import uses_dnr_sales_chain
from .storage import posted_entry_for_order


@dataclass
class SalesFlowSummary:
    paid_without_invoice: int = 0
    paid_draft_pending: int = 0
    issued_without_dnr: int = 0
    issued_without_kpir: int = 0
    booked_without_invoice: int = 0
    sample_orders_no_invoice: list[str] = field(default_factory=list)
    sample_orders_draft_pending: list[str] = field(default_factory=list)
    sample_invoices_no_dnr: list[str] = field(default_factory=list)
    sample_invoices_no_kpir: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "paid_without_invoice": self.paid_without_invoice,
            "paid_draft_pending": self.paid_draft_pending,
            "issued_without_dnr": self.issued_without_dnr,
            "issued_without_kpir": self.issued_without_kpir,
            "booked_without_invoice": self.booked_without_invoice,
            "sample_orders_no_invoice": self.sample_orders_no_invoice,
            "sample_orders_draft_pending": self.sample_orders_draft_pending,
            "sample_invoices_no_dnr": self.sample_invoices_no_dnr,
            "sample_invoices_no_kpir": self.sample_invoices_no_kpir,
        }


def _invoice_docs_for_order(shopify_order_id: int) -> list[InvoiceRecord]:
    return [i for i in invoices_for_order(shopify_order_id) if i.doc_kind == "invoice"]


def _issued_invoice(docs: list[InvoiceRecord]) -> InvoiceRecord | None:
    for inv in docs:
        if inv.status in ("issued", "corrected"):
            return inv
    return None


def _pending_draft(docs: list[InvoiceRecord]) -> InvoiceRecord | None:
    for inv in docs:
        if inv.status == "draft":
            return inv
    return None


def sales_flow_summary(*, days_back: int = 365, year: int | None = None) -> SalesFlowSummary:
    """Liczniki luk w łańcuchu faktura → DNR → KPiR."""
    out = SalesFlowSummary()
    try:
        from Komponenty.dnr.invoice_integration import list_importable_invoices
    except ImportError:
        list_importable_invoices = None  # type: ignore[assignment]

    y = year
    if list_importable_invoices is not None:
        inv_rows = list_importable_invoices(y)
        out.issued_without_dnr = len(inv_rows)
        out.sample_invoices_no_dnr = [str(r.get("number") or "") for r in inv_rows[:5]]

    unbooked = unbooked_invoices(year=y)
    if not uses_dnr_sales_chain():
        out.issued_without_kpir = len(unbooked)
        out.sample_invoices_no_kpir = [r.invoice_number for r in unbooked[:5]]

    try:
        orders = fetch_orders(days_back=days_back, financial_status="paid")
    except Exception:
        return out

    for order in orders:
        oid = int(order.get("id") or 0)
        if not oid:
            continue
        payment = str(order.get("processed_at") or order.get("created_at") or "")[:10]
        if y and payment and int(payment[:4]) != y:
            continue
        name = str(order.get("name") or oid)
        docs = _invoice_docs_for_order(oid)
        issued = _issued_invoice(docs)
        if issued:
            pass
        elif _pending_draft(docs):
            out.paid_draft_pending += 1
            if len(out.sample_orders_draft_pending) < 5:
                out.sample_orders_draft_pending.append(name)
        else:
            out.paid_without_invoice += 1
            if len(out.sample_orders_no_invoice) < 5:
                out.sample_orders_no_invoice.append(name)
        if posted_entry_for_order(oid) and not issued:
            out.booked_without_invoice += 1

    return out
