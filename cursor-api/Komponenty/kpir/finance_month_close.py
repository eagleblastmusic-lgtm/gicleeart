"""Wspólny widok zamknięcia miesiąca: KPiR + DNR + faktury."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_helpers import is_production_bookable_invoice
from Komponenty.dokumentysprzedazy.storage import list_invoices

from .month_checklist import build_month_checklist
from .summary_service import monthly_summary


@dataclass
class FinanceMonthClose:
    year: int
    month: int
    kpir_revenue: float = 0.0
    kpir_costs: float = 0.0
    kpir_income: float = 0.0
    invoice_count: int = 0
    invoice_total_pln: float = 0.0
    dnr_revenue: float = 0.0
    dnr_costs: float = 0.0
    checklist_items: list[dict[str, Any]] = field(default_factory=list)
    can_close: bool = True
    blocking_count: int = 0
    warning_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "kpir_revenue": self.kpir_revenue,
            "kpir_costs": self.kpir_costs,
            "kpir_income": self.kpir_income,
            "invoice_count": self.invoice_count,
            "invoice_total_pln": self.invoice_total_pln,
            "dnr_revenue": self.dnr_revenue,
            "dnr_costs": self.dnr_costs,
            "checklist_items": self.checklist_items,
            "can_close": self.can_close,
            "blocking_count": self.blocking_count,
            "warning_count": self.warning_count,
        }


def build_finance_month_close(year: int, month: int) -> FinanceMonthClose:
    out = FinanceMonthClose(year=year, month=month)
    summary = monthly_summary(year, month)
    out.kpir_revenue = float(summary.get("revenue_total") or 0)
    out.kpir_costs = float(summary.get("costs_total") or 0)
    out.kpir_income = float(summary.get("income") or 0)

    for inv in list_invoices():
        if not is_production_bookable_invoice(inv):
            continue
        sd = (inv.sale_date or inv.issue_date or "")[:10]
        try:
            iy, im = int(sd[:4]), int(sd[5:7])
        except (ValueError, IndexError):
            continue
        if iy != year or im != month:
            continue
        out.invoice_count += 1
        out.invoice_total_pln += float(inv.exchange.total_amount_pln or inv.order_total or 0)
    out.invoice_total_pln = round(out.invoice_total_pln, 2)

    try:
        from Komponenty.dnr.summary_service import monthly_breakdown

        for row in monthly_breakdown(year):
            if int(row.get("month") or 0) == month:
                out.dnr_revenue = float(row.get("revenue") or 0)
                out.dnr_costs = float(row.get("costs") or 0)
                break
    except ImportError:
        pass

    checklist = build_month_checklist(year, month)
    out.checklist_items = checklist.to_dict().get("items") or []
    out.can_close = checklist.can_close
    out.blocking_count = checklist.blocking_count
    out.warning_count = checklist.warning_count
    return out
