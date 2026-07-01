"""Zestawienie sprzedaży — § 17 rozporządzenia (przychody nieudokumentowane fakturą)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .entry_service import create_entry, post_entry
from .models import SalesRegisterEntry
from .storage import list_sales_register, new_sales_register_id, save_sales_register
from .validation import ValidationError


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def add_sales_register_entry(event_date: str, amount: float, *, description: str = "", document_ref: str = "") -> SalesRegisterEntry:
    if amount <= 0:
        raise ValidationError("Kwota przychodu musi być dodatnia.")
    row = SalesRegisterEntry(
        id=new_sales_register_id(),
        event_date=event_date[:10],
        amount=round(amount, 2),
        description=description,
        document_ref=document_ref,
        created_at=_now(),
    )
    save_sales_register(row)
    return row


def book_sales_register_to_kpir(register_id: str) -> tuple[SalesRegisterEntry, Any]:
    rows = list_sales_register()
    row = next((r for r in rows if r.id == register_id), None)
    if not row:
        raise ValidationError("Nie znaleziono wpisu ewidencji sprzedaży.")
    if row.kpir_entry_id:
        raise ValidationError("Wpis jest już ujęty w KPiR.")
    entry = create_entry(
        event_date=row.event_date,
        document_number=row.document_ref or f"ES/{row.id}",
        description=row.description or "Przychód nieudokumentowany fakturą",
        revenue_goods=row.amount,
        source="sales_register",
        entry_type="revenue",
        amount_pln=row.amount,
    )
    entry = post_entry(entry)
    row.kpir_entry_id = entry.id
    save_sales_register(row)
    return row, entry


def sales_register_for_month(year: int, month: int) -> list[SalesRegisterEntry]:
    out = []
    for row in list_sales_register():
        try:
            if int(row.event_date[:4]) == year and int(row.event_date[5:7]) == month:
                out.append(row)
        except (ValueError, IndexError):
            continue
    return out
