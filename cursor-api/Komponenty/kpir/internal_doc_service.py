"""Dowody wewnętrzne — § 8 rozporządzenia (m.in. część kosztów mieszkania)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .cost_service import book_cost_to_kpir, create_cost
from .entry_service import create_entry, post_entry
from .models import GoodsReceiptPending
from .storage import new_goods_receipt_id, save_goods_receipt_pending
from .validation import ValidationError


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_home_office_internal_cost(
    *,
    issue_date: str,
    base_amount: float,
    business_share: float,
    utility_type: str,
    source_document: str,
) -> Any:
    """Koszt mieszkania w części używanej na działalność (§ 8 ust. 2 pkt 6)."""
    if not 0 < business_share <= 1:
        raise ValidationError("Udział działalności musi być między 0 a 1 (np. 0.25).")
    amount = round(base_amount * business_share, 2)
    cost = create_cost(
        issue_date=issue_date,
        event_date=issue_date,
        document_number=f"DW/{utility_type[:8].upper()}/{issue_date[:7]}",
        seller="Dowód wewnętrzny",
        description=f"{utility_type} — {business_share * 100:.0f}% działalności (podstawa: {source_document})",
        category="inne",
        amount_gross=amount,
        is_internal_doc=True,
        is_paid=True,
        payment_date=issue_date,
    )
    return book_cost_to_kpir(cost.id)


def create_goods_receipt_before_invoice(**kwargs: Any) -> GoodsReceiptPending:
    """§ 9 — opis towaru przed fakturą."""
    qty = float(kwargs.get("quantity") or 0)
    price = float(kwargs.get("unit_price") or 0)
    value = float(kwargs.get("value") or round(qty * price, 2))
    item = GoodsReceiptPending(
        id=new_goods_receipt_id(),
        receipt_date=str(kwargs.get("receipt_date") or _now()[:10]),
        supplier_name=str(kwargs.get("supplier_name") or ""),
        supplier_nip=str(kwargs.get("supplier_nip") or ""),
        description=str(kwargs.get("description") or ""),
        quantity=qty,
        unit=str(kwargs.get("unit") or "szt."),
        unit_price=price,
        value=value,
        created_at=_now(),
    )
    save_goods_receipt_pending(item)
    return item


def book_goods_receipt_to_kpir(
    receipt_id: str,
    *,
    invoice_document_number: str = "",
    ksef_number: str = "",
) -> Any:
    from .storage import list_goods_receipts_pending

    item = next((x for x in list_goods_receipts_pending() if x.id == receipt_id), None)
    if not item:
        raise ValidationError("Nie znaleziono opisu przyjęcia.")
    if item.kpir_entry_id:
        raise ValidationError("Opis jest już ujęty w KPiR.")
    entry = create_entry(
        event_date=item.receipt_date,
        document_number=invoice_document_number or f"OPIS/{item.id}",
        ksef_number=ksef_number,
        contractor=item.supplier_name,
        contractor_nip=item.supplier_nip,
        description=item.description or "Przyjęcie towaru przed fakturą",
        purchase_goods=item.value,
        source="internal_doc",
        entry_type="cost",
        amount_pln=item.value,
    )
    entry = post_entry(entry)
    item.invoice_document_number = invoice_document_number
    item.ksef_number = ksef_number
    item.kpir_entry_id = entry.id
    item.status = "booked"
    save_goods_receipt_pending(item)
    return entry
