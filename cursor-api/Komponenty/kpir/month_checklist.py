"""Checklist przed zamknięciem miesiąca."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_helpers import is_production_bookable_invoice
from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
from Komponenty.dokumentysprzedazy.storage import list_invoices

from .order_status import get_order_kpir_status
from .sales_chain import uses_dnr_sales_chain
from .storage import is_month_closed, is_year_closed, list_costs, posted_entry_for_invoice, posted_entry_for_order
from .summary_service import collect_alerts, monthly_summary


@dataclass
class ChecklistItem:
    severity: str  # error | warning | info
    message: str
    category: str  # order | invoice | cost | nbp | refund | other
    ref: str = ""


@dataclass
class MonthChecklist:
    year: int
    month: int
    items: list[ChecklistItem] = field(default_factory=list)
    blocking_count: int = 0
    warning_count: int = 0
    can_close: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "items": [{"severity": i.severity, "message": i.message, "category": i.category, "ref": i.ref} for i in self.items],
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
            "can_close": self.can_close,
        }


def build_month_checklist(year: int, month: int) -> MonthChecklist:
    checklist = MonthChecklist(year=year, month=month)
    summary = monthly_summary(year, month)

    from .kpir_compliance import booking_deadline_for_source_month

    deadline = booking_deadline_for_source_month(year, month)
    if deadline.get("level") in ("warning", "error"):
        checklist.items.append(ChecklistItem(
            severity="error" if deadline.get("level") == "error" else "warning",
            message=str(deadline.get("message") or "Termin zapisów (20.)"),
            category="other",
        ))

    for alert in summary.get("alerts") or []:
        if uses_dnr_sales_chain() and "nieujęta w KPiR" in alert:
            continue
        sev = "error" if "Brak kursu" in alert or "Podwójny" in alert else "warning"
        cat = "nbp" if "NBP" in alert else "other"
        if "Faktura" in alert:
            cat = "invoice"
        if "Koszt" in alert:
            cat = "cost"
        if "zamówien" in alert.lower():
            cat = "order"
        checklist.items.append(ChecklistItem(severity=sev, message=alert, category=cat))

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
            st = get_order_kpir_status(oid)
            from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id, invoices_for_order

            inv = invoice_by_order_id(oid)
            has_invoice = inv and is_production_bookable_invoice(inv)
            order_docs = [i for i in invoices_for_order(oid) if i.doc_kind == "invoice"]
            has_draft = any(i.status == "draft" for i in order_docs)
            if st.status == "not_booked":
                if not has_invoice:
                    if has_draft:
                        checklist.items.append(ChecklistItem(
                            severity="info",
                            message=f"Szkic faktury do wystawienia: {order.get('name')}",
                            category="invoice",
                            ref=str(oid),
                        ))
                    else:
                        checklist.items.append(ChecklistItem(
                            severity="warning",
                            message=f"Opłacone bez faktury: {order.get('name')}",
                            category="order",
                            ref=str(oid),
                        ))
                else:
                    if not uses_dnr_sales_chain():
                        checklist.items.append(ChecklistItem(
                            severity="warning",
                            message=f"Faktura bez wpisu KPiR: {order.get('name')} ({inv.invoice_number})",
                            category="invoice",
                            ref=inv.id,
                        ))
            if st.status == "booked" and not has_invoice:
                checklist.items.append(ChecklistItem(
                    severity="error",
                    message=f"KPiR bez faktury (ominięty łańcuch): {order.get('name')}",
                    category="order",
                    ref=str(oid),
                ))
            if order.get("refunds") and posted_entry_for_order(oid):
                from .refund_wizard import orders_needing_correction

                need_ids = {c.shopify_order_id for c in orders_needing_correction(days_back=120)}
                if oid in need_ids:
                    checklist.items.append(ChecklistItem(
                        severity="error",
                        message=f"Zwrot bez korekty: {order.get('name')}",
                        category="refund",
                        ref=str(oid),
                    ))
    except Exception:
        pass

    for inv in list_invoices():
        if not is_production_bookable_invoice(inv):
            continue
        try:
            sd = inv.sale_date[:10]
            iy, im = int(sd[:4]), int(sd[5:7])
        except (ValueError, IndexError):
            continue
        if iy != year or im != month:
            continue
        if not posted_entry_for_invoice(inv.id):
            if not uses_dnr_sales_chain():
                checklist.items.append(ChecklistItem(
                    severity="warning",
                    message=f"Faktura nieujęta w KPiR: {inv.invoice_number}",
                    category="invoice",
                    ref=inv.id,
                ))
        try:
            from Komponenty.dnr.storage import sale_for_invoice
        except ImportError:
            sale_for_invoice = None  # type: ignore[assignment]
        if sale_for_invoice is not None and not sale_for_invoice(inv.id):
            checklist.items.append(ChecklistItem(
                severity="warning",
                message=f"Faktura niezaimportowana do DNR: {inv.invoice_number}",
                category="dnr",
                ref=inv.id,
            ))

    for cost in list_costs():
        if cost.kpir_status != "draft":
            continue
        try:
            ed = (cost.event_date or cost.issue_date)[:10]
            cy, cm = int(ed[:4]), int(ed[5:7])
        except (ValueError, IndexError):
            continue
        if cy == year and cm == month:
            checklist.items.append(ChecklistItem(
                severity="warning",
                message=f"Koszt roboczy: {cost.document_number or cost.id}",
                category="cost",
                ref=cost.id,
            ))

    for item in checklist.items:
        if item.severity == "error":
            checklist.blocking_count += 1
        elif item.severity == "warning":
            checklist.warning_count += 1

    checklist.can_close = checklist.blocking_count == 0
    if is_month_closed(year, month):
        checklist.can_close = False
        checklist.items.insert(0, ChecklistItem("info", "Miesiąc jest już zamknięty.", "other"))

    _ = collect_alerts  # re-export usage kept in summary
    return checklist


def build_year_close_checklist(year: int) -> MonthChecklist:
    """Checklist przed zamknięciem roku podatkowego."""
    from .inventory_service import year_end_inventory_status
    from .kpir_compliance import booking_deadline_status, kpir_form_limit_status

    checklist = MonthChecklist(year=year, month=12)

    for m in range(1, 13):
        if not is_month_closed(year, m):
            checklist.items.append(ChecklistItem(
                severity="error",
                message=f"Miesiąc {year}-{m:02d} nie jest zamknięty.",
                category="other",
            ))

    inv = year_end_inventory_status(year)
    if not inv.get("has_year_end"):
        checklist.items.append(ChecklistItem(
            severity="error",
            message=f"Brak spisu z natury na 31.12.{year} (wymagany § 20).",
            category="inventory",
        ))

    if not inv.get("has_year_start"):
        checklist.items.append(ChecklistItem(
            severity="warning",
            message=f"Brak spisu z natury na 01.01.{year}.",
            category="inventory",
        ))

    deadline = booking_deadline_status(year, 12)
    if deadline.get("level") == "error":
        checklist.items.append(ChecklistItem(
            severity="error",
            message=str(deadline.get("message") or "Przekroczony termin zapisów (20.)."),
            category="other",
        ))

    limit = kpir_form_limit_status(year)
    if limit.get("level") == "error":
        checklist.items.append(ChecklistItem(
            severity="error",
            message=str(limit.get("message")),
            category="other",
        ))

    for item in checklist.items:
        if item.severity == "error":
            checklist.blocking_count += 1
        elif item.severity == "warning":
            checklist.warning_count += 1
    checklist.can_close = checklist.blocking_count == 0
    if is_year_closed(year):
        checklist.can_close = False
        checklist.items.insert(0, ChecklistItem("info", "Rok jest już zamknięty.", "other"))
    return checklist
