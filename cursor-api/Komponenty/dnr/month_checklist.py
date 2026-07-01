"""Checklist końca miesiąca DNR — bez zamknięcia KPiR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_helpers import is_production_bookable_invoice
from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id, list_invoices

from .storage import sale_for_invoice


@dataclass
class DnrChecklistItem:
    severity: str  # error | warning | info
    message: str
    category: str  # order | invoice | export | other
    ref: str = ""


@dataclass
class DnrMonthChecklist:
    year: int
    month: int
    items: list[DnrChecklistItem] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    can_close: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "items": [
                {"severity": i.severity, "message": i.message, "category": i.category, "ref": i.ref}
                for i in self.items
            ],
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "can_close": self.can_close,
        }


def build_dnr_month_checklist(year: int, month: int) -> DnrMonthChecklist:
    checklist = DnrMonthChecklist(year=year, month=month)

    try:
        orders = fetch_orders(days_back=120, financial_status="paid")
        for order in orders:
            payment = str(order.get("processed_at") or order.get("created_at") or "")[:10]
            try:
                oy, om = int(payment[:4]), int(payment[5:7])
            except (ValueError, IndexError):
                continue
            if oy != year or om != month:
                continue
            oid = int(order.get("id") or 0)
            inv = invoice_by_order_id(oid)
            has_issued = inv and is_production_bookable_invoice(inv)
            if not has_issued:
                if inv and inv.status == "draft":
                    checklist.items.append(DnrChecklistItem(
                        severity="info",
                        message=f"Szkic rachunku do wystawienia: {order.get('name')}",
                        category="invoice",
                        ref=str(oid),
                    ))
                else:
                    checklist.items.append(DnrChecklistItem(
                        severity="warning",
                        message=f"Opłacone bez rachunku: {order.get('name')}",
                        category="order",
                        ref=str(oid),
                    ))
            elif not sale_for_invoice(inv.id):
                checklist.items.append(DnrChecklistItem(
                    severity="warning",
                    message=f"Rachunek bez wpisu DNR: {inv.invoice_number}",
                    category="invoice",
                    ref=inv.id,
                ))
    except Exception:
        pass

    for inv in list_invoices():
        if not is_production_bookable_invoice(inv):
            continue
        try:
            sd = (inv.sale_date or inv.issue_date or "")[:10]
            iy, im = int(sd[:4]), int(sd[5:7])
        except (ValueError, IndexError):
            continue
        if iy != year or im != month:
            continue
        if not sale_for_invoice(inv.id):
            checklist.items.append(DnrChecklistItem(
                severity="warning",
                message=f"Wystawiony dokument niezaimportowany do DNR: {inv.invoice_number}",
                category="invoice",
                ref=inv.id,
            ))

    checklist.items.append(DnrChecklistItem(
        severity="info",
        message="Eksport CSV DNR i faktur za miesiąc — archiwum (przycisk poniżej).",
        category="export",
    ))

    for item in checklist.items:
        if item.severity == "error":
            checklist.blocking_count += 1
        elif item.severity == "warning":
            checklist.warning_count += 1

    checklist.can_close = checklist.blocking_count == 0
    return checklist
