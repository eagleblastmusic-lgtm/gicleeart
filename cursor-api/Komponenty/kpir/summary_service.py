"""Podsumowania miesięczne i roczne, alerty."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from Komponenty.dokumentysprzedazy.country import is_eu_b2c, is_poland
from Komponenty.dokumentysprzedazy.invoice_helpers import is_production_bookable_invoice
from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders, order_to_row
from Komponenty.dokumentysprzedazy.storage import list_invoices

from .entry_service import filter_entries
from .flow_status import sales_flow_summary
from .annual_income import annual_income_breakdown
from .storage import is_month_closed, list_costs, posted_entry_for_order


def _sum_posted(entries, year: int, month: int | None = None) -> dict[str, float]:
    totals = {
        "revenue_goods": 0.0,
        "revenue_other": 0.0,
        "purchase_goods": 0.0,
        "purchase_side": 0.0,
        "wages": 0.0,
        "other_expenses": 0.0,
    }
    for e in entries:
        if e.status not in ("posted", "corrected"):
            continue
        try:
            y = int(e.event_date[:4])
            m = int(e.event_date[5:7])
        except (ValueError, IndexError):
            continue
        if y != year:
            continue
        if month and m != month:
            continue
        totals["revenue_goods"] += e.revenue_goods
        totals["revenue_other"] += e.revenue_other
        totals["purchase_goods"] += e.purchase_goods
        totals["purchase_side"] += e.purchase_side
        totals["wages"] += e.wages
        totals["other_expenses"] += e.other_expenses
    for k in totals:
        totals[k] = round(totals[k], 2)
    return totals


def monthly_summary(year: int, month: int) -> dict[str, Any]:
    entries = filter_entries(year=year, month=month)
    totals = _sum_posted(entries, year, month)
    revenue_total = round(totals["revenue_goods"] + totals["revenue_other"], 2)
    costs_total = round(
        totals["purchase_goods"] + totals["purchase_side"] + totals["wages"] + totals["other_expenses"],
        2,
    )
    shopify_count = sum(1 for e in entries if e.source == "shopify" and e.status == "posted")
    invoice_count = sum(1 for e in entries if e.source == "invoice" and e.status == "posted")
    cost_count = sum(1 for e in entries if e.entry_type == "cost" and e.status == "posted")

    sales_pl = sales_eu = sales_non_eu = sales_fx = 0.0
    for e in entries:
        if e.entry_type != "revenue" or e.status != "posted":
            continue
        amt = e.amount_pln or e.total_revenue
        if is_poland(e.country):
            sales_pl += amt
        elif is_eu_b2c(e.country):
            sales_eu += amt
        elif e.country:
            sales_non_eu += amt
        if (e.original_currency or "PLN").upper() != "PLN":
            sales_fx += amt

    return {
        "year": year,
        "month": month,
        "totals": totals,
        "revenue_total": revenue_total,
        "costs_total": costs_total,
        "income": round(revenue_total - costs_total, 2),
        "shopify_orders": shopify_count,
        "invoices": invoice_count,
        "costs": cost_count,
        "sales_poland": round(sales_pl, 2),
        "sales_eu_b2c": round(sales_eu, 2),
        "sales_non_eu": round(sales_non_eu, 2),
        "sales_foreign_currency": round(sales_fx, 2),
        "month_closed": is_month_closed(year, month),
        "alerts": collect_alerts(year=year, month=month),
    }


def yearly_summary(year: int) -> dict[str, Any]:
    entries = filter_entries(year=year)
    totals = _sum_posted(entries, year)
    revenue_total = round(totals["revenue_goods"] + totals["revenue_other"], 2)
    costs_total = round(
        totals["purchase_goods"] + totals["purchase_side"] + totals["wages"] + totals["other_expenses"],
        2,
    )
    by_month: dict[int, dict[str, float]] = {}
    for m in range(1, 13):
        mt = _sum_posted(entries, year, m)
        rev = mt["revenue_goods"] + mt["revenue_other"]
        cost = mt["purchase_goods"] + mt["purchase_side"] + mt["wages"] + mt["other_expenses"]
        by_month[m] = {"revenue": rev, "costs": cost, "income": round(rev - cost, 2)}

    by_country: dict[str, float] = defaultdict(float)
    by_category: dict[str, float] = defaultdict(float)
    for e in entries:
        if e.status != "posted":
            continue
        try:
            y = int(e.event_date[:4])
        except (ValueError, IndexError):
            continue
        if y != year:
            continue
        if e.entry_type == "revenue":
            by_country[e.country or "—"] += e.amount_pln or e.total_revenue
        if e.entry_type == "cost" and e.category:
            by_category[e.category] += e.amount_pln or e.total_costs

    return {
        "year": year,
        "totals": totals,
        "revenue_total": revenue_total,
        "costs_total": costs_total,
        "income": round(revenue_total - costs_total, 2),
        "official_income": annual_income_breakdown(year),
        "by_month": by_month,
        "by_country": dict(by_country),
        "by_category": dict(by_category),
        "alerts": collect_alerts(year=year),
    }


def dashboard_summary(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    y, m = today.year, today.month
    month = monthly_summary(y, m)
    year = yearly_summary(y)
    unbooked_orders = 0
    unbooked_costs = sum(1 for c in list_costs() if c.kpir_status == "draft")
    missing_nbp = 0
    refunds_need = 0

    try:
        orders = fetch_orders(days_back=90, financial_status="paid")
        for o in orders:
            oid = int(o.get("id") or 0)
            if not posted_entry_for_order(oid):
                unbooked_orders += 1
            if o.get("refunds") and posted_entry_for_order(oid):
                refunds_need += 1
    except Exception:
        pass

    for e in filter_entries(year=y, month=m):
        if (e.original_currency or "PLN").upper() != "PLN" and e.nbp_status in ("missing", "error"):
            missing_nbp += 1

    return {
        "month_revenue": month["revenue_total"],
        "month_costs": month["costs_total"],
        "month_income": month["income"],
        "year_revenue": year["revenue_total"],
        "year_costs": year["costs_total"],
        "year_income": year["income"],
        "unbooked_orders": unbooked_orders,
        "unbooked_costs": unbooked_costs,
        "missing_nbp": missing_nbp,
        "refunds_need_correction": refunds_need,
        "month_closed": month["month_closed"],
        "sales_flow": sales_flow_summary(year=y).to_dict(),
    }


def collect_alerts(*, year: int, month: int | None = None) -> list[str]:
    alerts: list[str] = []
    entries = filter_entries(year=year, month=month) if month else filter_entries(year=year)

    seen_orders: set[int] = set()
    for e in entries:
        if e.shopify_order_id:
            if e.shopify_order_id in seen_orders and e.status == "posted":
                alerts.append(f"Podwójny wpis dla zamówienia {e.shopify_order_name}")
            seen_orders.add(e.shopify_order_id)
        if not e.document_number and e.status == "posted":
            alerts.append(f"Brak numeru dokumentu: {e.entry_number}")
        if (e.original_currency or "PLN").upper() != "PLN" and e.nbp_status in ("missing", "error"):
            alerts.append(f"Brak kursu NBP: {e.entry_number}")

    for c in list_costs():
        if c.kpir_status == "draft":
            if month:
                try:
                    m = int((c.event_date or c.issue_date)[5:7])
                    y = int((c.event_date or c.issue_date)[:4])
                    if y == year and m == month:
                        alerts.append(f"Koszt niezaksięgowany: {c.document_number or c.id}")
                except (ValueError, IndexError):
                    pass
            else:
                alerts.append(f"Koszt niezaksięgowany: {c.document_number or c.id}")

    for inv in list_invoices():
        if not is_production_bookable_invoice(inv):
            continue
        try:
            sd = datetime.fromisoformat(inv.sale_date[:10])
        except ValueError:
            continue
        if sd.year != year or (month and sd.month != month):
            continue
        from .sales_chain import uses_dnr_sales_chain
        from .storage import posted_entry_for_invoice

        if uses_dnr_sales_chain():
            continue
        if not posted_entry_for_invoice(inv.id):
            alerts.append(f"Faktura nieujęta w KPiR: {inv.invoice_number}")

    return alerts
