"""Import przychodów z modułu Dokumenty sprzedaży."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from Komponenty.dokumentysprzedazy.invoice_helpers import (
    invoice_limit_event_date,
    is_bookable_invoice,
)

from .entry_service import create_sale
from .storage import sale_for_invoice

if TYPE_CHECKING:
    from Komponenty.dokumentysprzedazy.models import InvoiceRecord


def _invoice_already_in_kpir(invoice_id: str) -> bool:
    try:
        from Komponenty.kpir.storage import posted_entry_for_invoice
    except ImportError:
        return False
    return posted_entry_for_invoice(invoice_id) is not None


def _invoice_net_pln(inv: InvoiceRecord) -> float:
    """Przychód należny po rabatach (wartość zamówienia dla klienta)."""
    if inv.status == "corrected" and inv.amount_after_correction:
        return round(float(inv.amount_after_correction), 2)
    if inv.exchange.total_amount_pln > 0:
        return round(float(inv.exchange.total_amount_pln), 2)
    return round(float(inv.order_total), 2)


def _invoice_price_breakdown(inv: InvoiceRecord) -> tuple[float, float, float]:
    """Zwraca (cena przed rabatem, rabat, przychód należny)."""
    net = _invoice_net_pln(inv)
    discount = round(abs(float(inv.discounts_total or 0)), 2)
    if discount > 0:
        list_price = round(net + discount, 2)
        return list_price, discount, net
    gross = round(float(inv.products_total or 0) + float(inv.shipping_total or 0), 2)
    if gross > net > 0:
        return gross, round(gross - net, 2), net
    return 0.0, 0.0, net


def _invoice_description(inv: InvoiceRecord, list_price: float, discount: float, net: float) -> str:
    buyer = (inv.buyer.name or "").strip()
    label = (inv.doc_type_label or "Sprzedaż").strip()
    if list_price > 0 and discount > 0:
        base = f"{label} {list_price:.2f} zł − rabat {discount:.2f} zł = {net:.2f} zł"
    elif discount > 0:
        base = f"{label} po rabacie — {net:.2f} zł"
    else:
        base = label
    if buyer:
        return f"{base} — {buyer}"[:200]
    return base[:200]


def list_importable_invoices(year: int | None = None) -> list[dict]:
    """Wystawione faktury, które nie są jeszcze w ewidencji DNR."""
    try:
        from Komponenty.dokumentysprzedazy.storage import list_invoices
    except ImportError:
        return []

    y = year or date.today().year
    out: list[dict] = []
    for inv in list_invoices():
        if not is_bookable_invoice(inv):
            continue
        if not inv.id or sale_for_invoice(inv.id):
            continue
        if _invoice_already_in_kpir(inv.id):
            continue
        sale_date = invoice_limit_event_date(inv)
        if sale_date and int(sale_date[:4]) != y:
            continue
        list_price, discount, net = _invoice_price_breakdown(inv)
        out.append({
            "id": inv.id,
            "number": inv.invoice_number,
            "issue_date": inv.issue_date or sale_date,
            "sale_date": sale_date,
            "buyer": inv.buyer.name,
            "amount_pln": net,
            "list_price_pln": list_price,
            "discount_pln": discount,
            "description": _invoice_description(inv, list_price, discount, net),
        })
    out.sort(key=lambda x: x.get("sale_date") or "", reverse=True)
    return out


def import_invoice(invoice_id: str) -> tuple[bool, str]:
    if sale_for_invoice(invoice_id):
        return False, "Faktura jest już w ewidencji DNR."
    if _invoice_already_in_kpir(invoice_id):
        return (
            False,
            "Faktura jest już ujęta w KPiR — import DNR pominięty "
            "(przychód jest w księdze; DNR służy limitowi kwartalnemu przed pełnym łańcuchem).",
        )
    try:
        from Komponenty.dokumentysprzedazy.storage import get_invoice
    except ImportError:
        return False, "Moduł dokumentów sprzedaży niedostępny."

    inv = get_invoice(invoice_id)
    if not inv:
        return False, "Nie znaleziono faktury."
    if not is_bookable_invoice(inv):
        return False, "Można importować tylko wystawione faktury."
    list_price, discount, net = _invoice_price_breakdown(inv)
    limit_date = invoice_limit_event_date(inv) or date.today().isoformat()
    create_sale(
        event_date=limit_date,
        amount_pln=net,
        list_price_pln=list_price,
        discount_pln=discount,
        description=_invoice_description(inv, list_price, discount, net),
        document_number=inv.invoice_number,
        source="invoice",
        invoice_id=invoice_id,
        currency=inv.currency or "PLN",
        amount_original=float(inv.order_total or net),
        payment_status="paid" if inv.payment_date else "unpaid",
        paid_at=(inv.payment_date or "")[:19],
        amount_received_pln=net if inv.payment_date else 0.0,
        shopify_order_id=int(inv.shopify_order_id or 0),
        destination_country=str(inv.shipping_address.country_code or inv.buyer.country_code or ""),
        fulfillment_country=str(getattr(inv, "fulfillment_country", "") or "PL"),
    )
    return True, "Zaimportowano fakturę do ewidencji DNR."


def import_all_for_year(year: int) -> tuple[int, int, list[str]]:
    """Zwraca (zaimportowane, pominięte, komunikaty o pominiętych)."""
    imported = 0
    skipped = 0
    errors: list[str] = []
    for row in list_importable_invoices(year):
        ok, msg = import_invoice(row["id"])
        if ok:
            imported += 1
        else:
            skipped += 1
            label = str(row.get("number") or row.get("id") or "?")
            errors.append(f"{label}: {msg}")
    return imported, skipped, errors
