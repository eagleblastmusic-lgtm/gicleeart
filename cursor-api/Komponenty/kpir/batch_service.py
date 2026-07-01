"""Masowe księgowanie przychodów Shopify."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .shopify_service import can_book_order, create_entry_from_order
from .validation import ValidationError


@dataclass
class BatchBookResult:
    booked: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    entry_ids: list[str] = field(default_factory=list)


def book_orders_batch(
    orders: list[dict[str, Any]],
    *,
    order_ids: list[int] | None = None,
    post: bool = True,
) -> BatchBookResult:
    """Księguje wiele zamówień; pomija już ujęte / z fakturą / pominięte."""
    result = BatchBookResult()
    id_set = set(order_ids) if order_ids else None
    for order in orders:
        oid = int(order.get("id") or 0)
        if id_set is not None and oid not in id_set:
            continue
        ok, reason = can_book_order(order)
        if not ok:
            result.skipped += 1
            if reason not in ("już ujęte w KPiR", "pominięte"):
                result.errors.append(f"{order.get('name')}: {reason}")
            continue
        try:
            entry = create_entry_from_order(order, post=post)
            result.booked += 1
            result.entry_ids.append(entry.id)
        except ValidationError as exc:
            result.skipped += 1
            result.errors.append(f"{order.get('name')}: {exc}")
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f"{order.get('name')}: {exc}")
    return result


def filter_bookable_orders(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [o for o in orders if can_book_order(o)[0]]
