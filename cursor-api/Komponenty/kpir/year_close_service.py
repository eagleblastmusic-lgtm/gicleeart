"""Zamknięcie roku podatkowego PKPiR."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .annual_income import annual_income_breakdown
from .inventory_service import (
    book_inventory_to_kpir,
    create_zero_inventory,
    inventories_for_year,
    year_end_inventory_status,
)
from .models import YearClosure
from .month_checklist import build_year_close_checklist
from .pkpir_annual_export import export_pkpir_annual_package
from .storage import get_year_closure, is_year_closed, load_settings, save_year_closure
from .validation import ValidationError


def build_year_close_summary(year: int) -> dict[str, Any]:
    checklist = build_year_close_checklist(year)
    income = annual_income_breakdown(year)
    inv = year_end_inventory_status(year)
    return {
        "year": year,
        "checklist": checklist.to_dict(),
        "income": income,
        "inventory": inv,
        "is_closed": is_year_closed(year),
    }


def close_year(year: int, *, force: bool = False) -> YearClosure:
    checklist = build_year_close_checklist(year)
    if not force and not checklist.can_close:
        msgs = [i.message for i in checklist.items if i.severity == "error"][:6]
        raise ValidationError("Nie można zamknąć roku — " + "; ".join(msgs))

    settings = load_settings()
    end_date = f"{year}-12-31"
    inv_status = year_end_inventory_status(year)
    end_inv_id = inv_status.get("year_end_id") or ""

    if not end_inv_id:
        zero = create_zero_inventory(end_date, "year_end", notes="Spis zerowy — zamknięcie roku")
        inv, _ = book_inventory_to_kpir(zero.id)
        end_inv_id = inv.id
    else:
        from .storage import get_inventory

        inv = get_inventory(end_inv_id)
        if inv and inv.status == "valued":
            book_inventory_to_kpir(end_inv_id)

    income = annual_income_breakdown(year, settings)
    pkg = export_pkpir_annual_package(year)

    next_year = year + 1
    start_date = f"{next_year}-01-01"
    start_inv = next((i for i in inventories_for_year(next_year) if i.inventory_date[:10] == start_date), None)
    if not start_inv:
        from .inventory_service import get_inventory as _gi

        prev = _gi(end_inv_id) if end_inv_id else None
        if prev:
            from .inventory_service import create_inventory

            lines = [ln.to_dict() for ln in prev.lines]
            start_inv = create_inventory(start_date, "year_start", lines=lines, notes="Przeniesienie z remanentu końcowego")
            book_inventory_to_kpir(start_inv.id)

    closure = get_year_closure(year) or YearClosure(year=year)
    closure.is_closed = True
    closure.closed_at = datetime.now().isoformat(timespec="seconds")
    closure.inventory_end_id = end_inv_id
    closure.inventory_start_next_id = start_inv.id if start_inv else ""
    closure.annual_income = income["income"]
    closure.pkpir_export_path = str(pkg)
    save_year_closure(closure)
    return closure
