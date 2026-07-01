"""Lista faktur do ujęcia w KPiR."""

from __future__ import annotations

from dataclasses import dataclass

from Komponenty.dokumentysprzedazy.invoice_helpers import is_bookable_invoice, invoice_kpir_amount_pln
from Komponenty.dokumentysprzedazy.storage import list_invoices

from .order_status import get_invoice_kpir_status
from .sales_chain import uses_dnr_sales_chain
from .storage import load_settings


@dataclass
class InvoiceKpirRow:
    invoice_id: str
    invoice_number: str
    sale_date: str
    buyer_name: str
    amount_pln: float
    currency: str
    shopify_order_name: str
    kpir_status: str
    entry_number: str
    invoice_status: str = ""
    ksef_number: str = ""
    buyer_nip: str = ""


def list_invoices_for_kpir(*, year: int | None = None, month: int | None = None) -> list[InvoiceKpirRow]:
    rows: list[InvoiceKpirRow] = []
    for inv in list_invoices():
        if not is_bookable_invoice(inv):
            continue
        sale = (inv.sale_date or inv.issue_date or "")[:10]
        if year:
            try:
                iy, im = int(sale[:4]), int(sale[5:7])
            except (ValueError, IndexError):
                continue
            if iy != year:
                continue
            if month and im != month:
                continue
        st = get_invoice_kpir_status(inv.id)
        vat_status = load_settings().vat_status
        rows.append(InvoiceKpirRow(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            sale_date=sale,
            buyer_name=inv.buyer.name if inv.buyer else "",
            amount_pln=invoice_kpir_amount_pln(inv, vat_status=vat_status),
            currency=inv.currency or "PLN",
            shopify_order_name=inv.shopify_order_name or "",
            kpir_status=st.status,
            entry_number=st.entry_number or "",
            invoice_status=inv.status,
            ksef_number=str(inv.ksef_number or ""),
            buyer_nip=str(inv.buyer.nip if inv.buyer else ""),
        ))
    return sorted(rows, key=lambda r: r.sale_date, reverse=True)


def unbooked_invoices(*, year: int | None = None, month: int | None = None) -> list[InvoiceKpirRow]:
    if uses_dnr_sales_chain():
        return []
    return [r for r in list_invoices_for_kpir(year=year, month=month) if r.kpir_status == "not_booked"]
