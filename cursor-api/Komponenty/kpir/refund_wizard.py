"""Kreator korekt zwrotów — zamówienia wymagające korekty."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders

from .correction_service import create_full_refund_correction, create_partial_refund_correction
from .storage import posted_entry_for_order


@dataclass
class RefundCase:
    shopify_order_id: int
    shopify_order_name: str
    refund_total: float
    order_total: float
    financial_status: str
    entry_id: str
    entry_number: str
    is_full_refund: bool
    payment_date: str


def _refund_total(order: dict[str, Any]) -> float:
    total = 0.0
    for refund in order.get("refunds") or []:
        for tx in refund.get("transactions") or []:
            if str(tx.get("kind") or "").lower() == "refund":
                total += float(tx.get("amount") or 0)
    return round(total, 2)


def orders_needing_correction(*, days_back: int = 365) -> list[RefundCase]:
    """Zamówienia zaksięgowane, które mają zwroty bez korekty."""
    cases: list[RefundCase] = []
    try:
        orders = fetch_orders(days_back=days_back, financial_status=None)
    except Exception:
        return cases

    for order in orders:
        oid = int(order.get("id") or 0)
        if not order.get("refunds"):
            continue
        entry = posted_entry_for_order(oid)
        if not entry or entry.status == "corrected":
            continue
        from .storage import list_entries

        has_correction = any(
            e.linked_entry_id == entry.id and e.entry_type == "correction" and e.status == "posted"
            for e in list_entries()
        )
        if has_correction:
            continue
        refund_amt = _refund_total(order)
        order_total = float(order.get("total_price") or 0)
        cases.append(RefundCase(
            shopify_order_id=oid,
            shopify_order_name=str(order.get("name") or ""),
            refund_total=refund_amt,
            order_total=order_total,
            financial_status=str(order.get("financial_status") or ""),
            entry_id=entry.id,
            entry_number=entry.entry_number,
            is_full_refund=refund_amt >= order_total * 0.99 or order.get("financial_status") == "refunded",
            payment_date=str(order.get("processed_at") or order.get("created_at") or "")[:10],
        ))
    return sorted(cases, key=lambda c: c.payment_date, reverse=True)


def apply_refund_correction(
    case: RefundCase,
    *,
    partial_amount_pln: float | None = None,
    post: bool = True,
) -> Any:
    if partial_amount_pln is not None and partial_amount_pln > 0:
        return create_partial_refund_correction(
            case.shopify_order_id,
            partial_amount_pln,
            post=post,
        )
    if case.is_full_refund:
        return create_full_refund_correction(case.shopify_order_id, post=post)
    if case.refund_total > 0:
        entry = posted_entry_for_order(case.shopify_order_id)
        if entry:
            pln = entry.amount_pln or entry.total_revenue
            ratio = case.refund_total / case.order_total if case.order_total else 1
            return create_partial_refund_correction(
                case.shopify_order_id,
                round(pln * ratio, 2),
                post=post,
            )
    return create_full_refund_correction(case.shopify_order_id, post=post)
