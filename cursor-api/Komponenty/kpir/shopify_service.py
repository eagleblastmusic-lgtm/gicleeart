"""Integracja Shopify → wpisy KPiR."""

from __future__ import annotations

from typing import Any

from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id

from .models import KpirSettings
from .storage import is_order_skipped, posted_entry_for_order, skip_order
from .validation import ValidationError


def can_book_order(order: dict[str, Any]) -> tuple[bool, str]:
    """Księgowanie przychodu wyłącznie z wystawionej faktury — nie bezpośrednio z zamówienia."""
    oid = int(order.get("id") or 0)
    if is_order_skipped(oid):
        return False, "pominięte"
    if order.get("cancelled_at"):
        return False, "anulowane"
    fin = str(order.get("financial_status") or "")
    if fin not in ("paid", "partially_refunded", "refunded"):
        return False, f"status płatności: {fin}"
    if posted_entry_for_order(oid):
        return False, "już ujęte w KPiR"
    inv = invoice_by_order_id(oid)
    if inv and inv.status in ("issued", "corrected"):
        return False, "faktura wystawiona — użyj auto-księgowania lub modułu faktur"
    return False, "wymagana wystawiona faktura (Dokumenty sprzedaży)"


def create_entry_from_order(
    order: dict[str, Any],
    *,
    settings: KpirSettings | None = None,
    post: bool = True,
) -> Any:
    raise ValidationError(
        "Księgowanie zamówienia bez faktury jest wyłączone. "
        "Wystaw dokument w module Dokumenty sprzedaży."
    )


def create_grouped_entries(
    orders: list[dict[str, Any]],
    *,
    settings: KpirSettings,
    post: bool = True,
) -> list[Any]:
    """Wpisy zbiorcze bez faktur — wyłączone."""
    raise ValidationError(
        "Wpisy zbiorcze bez faktur są wyłączone. Wystaw dokumenty w module Dokumenty sprzedaży."
    )


def mark_order_skipped(shopify_order_id: int) -> None:
    skip_order(shopify_order_id)
