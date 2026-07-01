"""Podsumowania i limit DNR (kwartalny od 2026)."""

from __future__ import annotations

from datetime import date
from typing import Any

from .constants import CEIDG_WARNING, DEFAULT_QUARTERLY_LIMIT, MONTHLY_GUARDRAIL, QUARTER_LABELS
from .dates import quarter_from_iso, quarter_from_month
from .limit_sync import canonical_quarterly_limit
from .models import CostEntry, SaleEntry
from .storage import list_costs, list_sales, load_settings

_SUBTRACT_KINDS = frozenset({"refund", "correction", "bonification"})


def _obligation_context(year: int | None = None, quarter: int | None = None) -> dict:
    from .migration_service import obligation_context

    return obligation_context(year=year, quarter=quarter)


def quarter_from_month(month: int) -> int:
    from .dates import quarter_from_month as _qfm

    return _qfm(month)


def quarter_from_iso(iso: str) -> int:
    from .dates import quarter_from_iso as _qfi

    return _qfi(iso)


def _year_from_iso(iso: str) -> int:
    try:
        return int(iso[:4])
    except (TypeError, ValueError):
        return date.today().year


def _month_from_iso(iso: str) -> int:
    try:
        return int(iso[5:7])
    except (TypeError, ValueError):
        return date.today().month


def sale_limit_delta(entry: SaleEntry) -> float:
    """Wpływ wpisu na limit kwartalny (przychód należny netto)."""
    if entry.migrated_to_kpir_at:
        return 0.0
    if entry.merchant_of_record:
        return 0.0
    amt = round(float(entry.amount_pln or 0), 2)
    kind = entry.entry_kind or "sale"
    if kind in _SUBTRACT_KINDS:
        return -amt
    return amt


def _received_pln(entry: SaleEntry) -> float:
    status = entry.payment_status or "paid"
    if status == "unpaid":
        return 0.0
    received = round(float(entry.amount_received_pln or 0), 2)
    if received <= 0 and status in ("paid", "partial"):
        received = round(float(entry.amount_pln or 0), 2)
    return received


def sale_pit_cash_delta(entry: SaleEntry) -> float:
    """Wpływ wpisu na PIT z DNR (kwoty faktycznie otrzymane)."""
    if entry.migrated_to_kpir_at:
        return 0.0
    if entry.merchant_of_record:
        return 0.0
    amt = _received_pln(entry)
    if amt <= 0:
        return 0.0
    kind = entry.entry_kind or "sale"
    if kind in _SUBTRACT_KINDS:
        return -amt
    return amt


def pit_cash_revenue_for_year(year: int) -> float:
    return round(sum(sale_pit_cash_delta(s) for s in sales_for_year(year)), 2)


def pit_cash_revenue_for_quarter(year: int, quarter: int) -> float:
    return round(sum(sale_pit_cash_delta(s) for s in sales_for_quarter(year, quarter)), 2)


def pit_cash_revenue_for_month(year: int, month: int) -> float:
    sales = [s for s in sales_for_year(year) if _month_from_iso(s.event_date) == month]
    return round(sum(sale_pit_cash_delta(s) for s in sales), 2)


def sales_for_year(year: int) -> list[SaleEntry]:
    return [s for s in list_sales() if _year_from_iso(s.event_date) == year]


def costs_for_year(year: int) -> list[CostEntry]:
    return [c for c in list_costs() if _year_from_iso(c.event_date) == year]


def sales_for_quarter(year: int, quarter: int) -> list[SaleEntry]:
    return [
        s for s in sales_for_year(year)
        if quarter_from_iso(s.event_date) == quarter
    ]


def costs_for_quarter(year: int, quarter: int) -> list[CostEntry]:
    return [
        c for c in costs_for_year(year)
        if quarter_from_iso(c.event_date) == quarter
    ]


def quarter_limit_revenue(year: int, quarter: int) -> float:
    return round(sum(sale_limit_delta(s) for s in sales_for_quarter(year, quarter)), 2)


def quarter_gross_sales(year: int, quarter: int) -> float:
    return round(
        sum(s.amount_pln for s in sales_for_quarter(year, quarter) if (s.entry_kind or "sale") == "sale"),
        2,
    )


def quarter_adjustments(year: int, quarter: int) -> float:
    return round(
        sum(s.amount_pln for s in sales_for_quarter(year, quarter) if (s.entry_kind or "sale") in _SUBTRACT_KINDS),
        2,
    )


def quarter_costs(year: int, quarter: int) -> float:
    return round(sum(c.amount_pln for c in costs_for_quarter(year, quarter)), 2)


def year_limit_revenue(year: int) -> float:
    return round(sum(quarter_limit_revenue(year, q) for q in range(1, 5)), 2)


def year_revenue(year: int) -> float:
    """Suma brutto sprzedaży (bez odejmowania zwrotów) — do podglądu."""
    return round(
        sum(s.amount_pln for s in sales_for_year(year) if (s.entry_kind or "sale") == "sale"),
        2,
    )


def year_costs(year: int) -> float:
    return round(sum(c.amount_pln for c in costs_for_year(year)), 2)


def year_profit(year: int) -> float:
    return round(year_limit_revenue(year) - year_costs(year), 2)


def quarterly_breakdown(year: int) -> list[dict[str, Any]]:
    limit = canonical_quarterly_limit()
    obligation = _obligation_context(year=year)
    rows: list[dict[str, Any]] = []
    for quarter in range(1, 5):
        rev = quarter_limit_revenue(year, quarter)
        gross = quarter_gross_sales(year, quarter)
        adj = quarter_adjustments(year, quarter)
        cos = quarter_costs(year, quarter)
        remaining = round(max(0.0, limit - rev), 2)
        pct = round((rev / limit * 100) if limit > 0 else 0, 1)
        over = rev > limit
        q_obligation = (
            obligation["obligation_active"]
            and int(obligation.get("first_exceed_year") or 0) == year
            and int(obligation.get("first_exceed_quarter") or 0) == quarter
            and not over
        )
        rows.append({
            "quarter": quarter,
            "label": QUARTER_LABELS[quarter],
            "limit_revenue": rev,
            "gross_sales": gross,
            "adjustments": adj,
            "costs": cos,
            "profit": round(rev - cos, 2),
            "quarterly_limit": limit,
            "remaining": remaining,
            "pct": pct,
            "over_limit": over,
            "obligation_active": q_obligation,
            "sale_count": len(sales_for_quarter(year, quarter)),
            "cost_count": len(costs_for_quarter(year, quarter)),
        })
    return rows


def monthly_breakdown(year: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for month in range(1, 13):
        sales = [s for s in sales_for_year(year) if _month_from_iso(s.event_date) == month]
        costs = [c for c in costs_for_year(year) if _month_from_iso(c.event_date) == month]
        rev = round(sum(sale_limit_delta(s) for s in sales), 2)
        cos = round(sum(c.amount_pln for c in costs), 2)
        rows.append({
            "month": month,
            "quarter": quarter_from_month(month),
            "revenue": rev,
            "costs": cos,
            "profit": round(rev - cos, 2),
            "sale_count": len(sales),
            "cost_count": len(costs),
        })
    return rows


def limit_status(year: int | None = None, quarter: int | None = None) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    q = quarter or quarter_from_month(today.month)
    limit = canonical_quarterly_limit()
    revenue = quarter_limit_revenue(y, q)
    remaining = round(max(0.0, limit - revenue), 2)
    pct = round((revenue / limit * 100) if limit > 0 else 0, 1)
    over = revenue > limit
    obligation = _obligation_context(year=y, quarter=q)
    obligation_active = bool(obligation.get("quarter_obligation"))
    jdg_obligation = bool(obligation.get("obligation_active"))
    if over:
        level = "over"
        message = (
            f"Przekroczono limit {QUARTER_LABELS[q]} o {revenue - limit:.2f} PLN. "
            f"{CEIDG_WARNING}"
        )
    elif obligation_active:
        level = "obligation"
        fe = obligation.get("first_exceed_date") or "?"
        message = (
            f"{QUARTER_LABELS[q]}: ewidencja poniżej limitu ({revenue:.2f} PLN), "
            f"ale obowiązek JDG od {fe} nadal obowiązuje — korekta nie cofa rejestracji."
        )
    elif pct >= 90:
        level = "warn"
        message = f"Zbliżasz się do limitu {QUARTER_LABELS[q]} — zostało {remaining:.2f} PLN."
    elif pct >= 75:
        level = "caution"
        message = f"Wykorzystano {pct}% limitu {QUARTER_LABELS[q]} — zostało {remaining:.2f} PLN."
    else:
        level = "ok"
        message = f"{QUARTER_LABELS[q]}: wykorzystano {pct}% limitu — zostało {remaining:.2f} PLN."
    return {
        "year": y,
        "quarter": q,
        "quarter_label": QUARTER_LABELS[q],
        "quarterly_limit": limit,
        "quarter_revenue": revenue,
        "quarter_costs": quarter_costs(y, q),
        "quarter_profit": round(revenue - quarter_costs(y, q), 2),
        "year_revenue": year_limit_revenue(y),
        "year_costs": year_costs(y),
        "year_profit": year_profit(y),
        "remaining": remaining,
        "pct": pct,
        "over_limit": over,
        "obligation_active": obligation_active,
        "jdg_obligation": jdg_obligation,
        "first_exceed_date": obligation.get("first_exceed_date") or "",
        "level": level,
        "message": message,
        "ceidg_warning": CEIDG_WARNING if (over or obligation_active) else "",
    }


def monthly_guardrail_status(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    m = month or today.month
    sales = [s for s in sales_for_year(y) if _month_from_iso(s.event_date) == m]
    revenue = round(sum(sale_limit_delta(s) for s in sales), 2)
    guardrail = MONTHLY_GUARDRAIL
    remaining = round(max(0.0, guardrail - revenue), 2)
    pct = round((revenue / guardrail * 100) if guardrail > 0 else 0, 1)
    over = revenue > guardrail
    if over:
        level = "warn"
        message = (
            f"Miesięczny guardrail {guardrail:,.2f} zł przekroczony o {revenue - guardrail:,.2f} zł "
            f"(to nie jest limit prawny — kontroluj kwartał)."
        )
    elif pct >= 90:
        level = "caution"
        message = f"Guardrail miesięczny: zostało {remaining:,.2f} zł ({pct}% wykorzystania)."
    else:
        level = "ok"
        message = f"Guardrail miesięczny: {revenue:,.2f} / {guardrail:,.2f} zł."
    return {
        "year": y,
        "month": m,
        "month_revenue": revenue,
        "guardrail": guardrail,
        "remaining": remaining,
        "pct": pct,
        "over_guardrail": over,
        "level": level,
        "message": message,
    }


def dashboard_summary(year: int | None = None) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    q = quarter_from_month(today.month)
    lim = limit_status(y, q)
    month_sales = [s for s in sales_for_year(y) if _month_from_iso(s.event_date) == today.month]
    month_costs = [c for c in costs_for_year(y) if _month_from_iso(c.event_date) == today.month]
    settings = load_settings()
    pit_year = pit_cash_revenue_for_year(y)
    pit_q = pit_cash_revenue_for_quarter(y, q)
    return {
        "year": y,
        "quarter": q,
        "month_limit_revenue": round(sum(sale_limit_delta(s) for s in month_sales), 2),
        "month_pit_cash_revenue": pit_cash_revenue_for_month(y, today.month),
        "pit_cash_revenue_quarter": pit_q,
        "pit_cash_revenue_year": pit_year,
        "month_costs": round(sum(c.amount_pln for c in month_costs), 2),
        "quarters": quarterly_breakdown(y),
        "eligibility_complete": settings.eligibility_complete(),
        "monthly_guardrail": monthly_guardrail_status(y, today.month),
        **lim,
    }
