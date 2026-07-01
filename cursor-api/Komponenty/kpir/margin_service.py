"""Marża brutto — przychód vs koszty materiałowe."""

from __future__ import annotations

from typing import Any

from .entry_service import filter_entries


def gross_margin_summary(*, year: int, month: int | None = None) -> dict[str, Any]:
    entries = filter_entries(year=year, month=month)
    revenue = 0.0
    materials = 0.0
    other_costs = 0.0
    for e in entries:
        if e.status not in ("posted", "corrected"):
            continue
        revenue += e.total_revenue
        materials += e.purchase_goods + e.purchase_side
        other_costs += e.wages + e.other_expenses
    revenue = round(revenue, 2)
    materials = round(materials, 2)
    other_costs = round(other_costs, 2)
    gross_profit = round(revenue - materials, 2)
    net_income = round(revenue - materials - other_costs, 2)
    margin_pct = round(gross_profit / revenue * 100, 1) if revenue > 0 else 0.0
    return {
        "year": year,
        "month": month,
        "revenue": revenue,
        "materials_cost": materials,
        "other_costs": other_costs,
        "gross_profit": gross_profit,
        "net_income": net_income,
        "gross_margin_percent": margin_pct,
    }
