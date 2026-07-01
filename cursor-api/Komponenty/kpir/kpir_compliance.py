"""Compliance PKPiR — terminy, limity, retencja."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_helpers import is_production_bookable_invoice
from Komponenty.dokumentysprzedazy.storage import list_invoices

from .constants import KPIR_ANNUAL_REVENUE_LIMIT_PLN, KPIR_BOOKING_DEADLINE_DAY, KPIR_RETENTION_YEARS
from .entry_service import filter_entries
from .sales_chain import uses_dnr_sales_chain
from .storage import is_year_closed, list_costs, posted_entry_for_invoice


def booking_deadline_for_source_month(
    year: int,
    source_month: int,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Czy pozycje z danego miesiąca źródłowego są zaksięgowane przed terminem 20."""
    today = today or date.today()
    if source_month == 12:
        deadline_y, deadline_m = year + 1, 1
    else:
        deadline_y, deadline_m = year, source_month + 1
    deadline = date(deadline_y, deadline_m, KPIR_BOOKING_DEADLINE_DAY)
    overdue_invoices: list[str] = []
    overdue_costs: list[str] = []

    for inv in list_invoices():
        if not is_production_bookable_invoice(inv):
            continue
        if uses_dnr_sales_chain():
            continue
        sd = (inv.sale_date or inv.issue_date or "")[:10]
        try:
            iy, im = int(sd[:4]), int(sd[5:7])
        except (ValueError, IndexError):
            continue
        if iy != year or im != source_month:
            continue
        if not posted_entry_for_invoice(inv.id):
            overdue_invoices.append(inv.invoice_number or inv.id)

    for cost in list_costs():
        if cost.kpir_status == "posted":
            continue
        ed = (cost.event_date or cost.issue_date or "")[:10]
        try:
            cy, cm = int(ed[:4]), int(ed[5:7])
        except (ValueError, IndexError):
            continue
        if cy != year or cm != source_month:
            continue
        overdue_costs.append(cost.document_number or cost.id)

    past_deadline = today > deadline
    count = len(overdue_invoices) + len(overdue_costs)
    level = "ok"
    if count and past_deadline:
        level = "error"
    elif count:
        level = "warning"
    return {
        "year": year,
        "source_month": source_month,
        "deadline": deadline.isoformat(),
        "past_deadline": past_deadline,
        "overdue_invoice_count": len(overdue_invoices),
        "overdue_cost_count": len(overdue_costs),
        "level": level,
        "message": (
            f"Po terminie {deadline:%Y-%m-%d}: {count} pozycji z {source_month:02d}/{year} bez wpisu KPiR."
            if past_deadline and count
            else (
                f"Do {deadline:%Y-%m-%d}: {count} pozycji z {source_month:02d}/{year} bez wpisu KPiR."
                if count
                else f"Termin zapisów za {source_month:02d}/{year}: do {deadline:%Y-%m-%d} — OK."
            )
        ),
    }


def booking_deadline_status(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    """§ 11 ust. 2 — alert bieżący: poprzedni miesiąc względem dziś."""
    today = date.today()
    y = year or today.year
    m = month or today.month
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1
    result = booking_deadline_for_source_month(prev_y, prev_m, today=today)
    result["month"] = m
    result["previous_period"] = f"{prev_y}-{prev_m:02d}"
    result["overdue_invoices"] = []
    result["overdue_costs"] = []
    return result


def kpir_form_limit_status(year: int | None = None) -> dict[str, Any]:
    """Monitor progu pełnej księgowości (~10,6 mln zł netto)."""
    y = year or date.today().year
    revenue = 0.0
    for e in filter_entries(year=y):
        if e.status not in ("posted", "corrected") or e.entry_type != "revenue":
            continue
        revenue += e.total_revenue
    revenue = round(revenue, 2)
    threshold = KPIR_ANNUAL_REVENUE_LIMIT_PLN
    ratio = revenue / threshold if threshold else 0
    level = "ok"
    if revenue >= threshold:
        level = "error"
    elif ratio >= 0.85:
        level = "warning"
    return {
        "year": y,
        "revenue_net": revenue,
        "threshold_pln": threshold,
        "ratio": round(ratio, 4),
        "level": level,
        "message": (
            f"Przychód {revenue:,.2f} zł przekroczył limit KPiR ({threshold:,.0f} zł) — wymagane księgi rachunkowe."
            if revenue >= threshold
            else f"Przychód {revenue:,.2f} zł / limit KPiR {threshold:,.0f} zł ({ratio * 100:.1f}%)."
        ),
    }


def retention_reminders(today: date | None = None) -> list[dict[str, Any]]:
    """Przypomnienia o 5-letnim przechowywaniu księgi."""
    today = today or date.today()
    reminders = []
    for y in range(today.year - KPIR_RETENTION_YEARS - 1, today.year):
        keep_until = y + KPIR_RETENTION_YEARS + 1
        if today.year >= keep_until - 1 and not is_year_closed(y):
            reminders.append({
                "year": y,
                "keep_until_end_of": keep_until,
                "message": f"Księga {y}: przechowuj do końca {keep_until} (5 lat od rozliczenia PIT).",
            })
    return reminders


def kpir_compliance_monitors(year: int | None = None) -> list[dict[str, Any]]:
    y = year or date.today().year
    monitors = [
        {"title": "Termin zapisów (20.)", **booking_deadline_status(y)},
        {"title": "Limit formy KPiR", **kpir_form_limit_status(y)},
    ]
    for rem in retention_reminders():
        monitors.append({"title": "Retencja dokumentacji", "level": "info", **rem})
    return monitors
