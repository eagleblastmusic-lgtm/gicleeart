"""Dochód roczny wg wzoru z załącznika do Dz.U. 2025 poz. 1299 (pkt 22)."""

from __future__ import annotations

from typing import Any

from .entry_service import filter_entries
from .inventory_service import inventory_value_on_date
from .models import KpirSettings


def _sum_posted_columns(year: int) -> dict[str, float]:
    totals = {
        "revenue_goods": 0.0,
        "revenue_other": 0.0,
        "purchase_goods": 0.0,
        "purchase_side": 0.0,
        "wages": 0.0,
        "other_expenses": 0.0,
        "rd_expenses": 0.0,
    }
    for e in filter_entries(year=year):
        if e.status not in ("posted", "corrected"):
            continue
        if e.source == "inventory":
            continue
        totals["revenue_goods"] += e.revenue_goods
        totals["revenue_other"] += e.revenue_other
        totals["purchase_goods"] += e.purchase_goods
        totals["purchase_side"] += e.purchase_side
        totals["wages"] += e.wages
        totals["other_expenses"] += e.other_expenses
        totals["rd_expenses"] += e.rd_expenses
    return {k: round(v, 2) for k, v in totals.items()}


def annual_income_breakdown(year: int, settings: KpirSettings | None = None) -> dict[str, Any]:
    """Oficjalny wzór kosztów uzyskania przychodu."""
    _ = settings
    cols = _sum_posted_columns(year)
    revenue = round(cols["revenue_goods"] + cols["revenue_other"], 2)

    opening = inventory_value_on_date(f"{year}-01-01")
    closing = inventory_value_on_date(f"{year}-12-31")

    cost_of_goods = round(
        opening
        + cols["purchase_goods"]
        + cols["purchase_side"]
        - closing,
        2,
    )
    other_expenses_total = round(cols["wages"] + cols["other_expenses"], 2)
    total_costs = round(cost_of_goods + other_expenses_total, 2)
    income = round(revenue - total_costs, 2)

    return {
        "year": year,
        "revenue": revenue,
        "inventory_opening": opening,
        "purchase_goods": cols["purchase_goods"],
        "purchase_side": cols["purchase_side"],
        "inventory_closing": closing,
        "cost_of_goods": cost_of_goods,
        "wages": cols["wages"],
        "other_expenses": cols["other_expenses"],
        "other_expenses_total": other_expenses_total,
        "rd_expenses": cols["rd_expenses"],
        "total_costs": total_costs,
        "income": income,
        "formula": (
            f"{revenue:.2f} − ({opening:.2f} + {cols['purchase_goods']:.2f} + "
            f"{cols['purchase_side']:.2f} − {closing:.2f} + {other_expenses_total:.2f})"
        ),
        "missing_opening_inventory": opening == 0.0 and not _has_inventory_on(f"{year}-01-01"),
        "missing_closing_inventory": closing == 0.0 and not _has_inventory_on(f"{year}-12-31"),
    }


def _has_inventory_on(iso_date: str) -> bool:
    from .storage import list_inventories

    for inv in list_inventories():
        if inv.inventory_date[:10] == iso_date[:10] and inv.status in ("valued", "booked"):
            return True
    return False
