"""Synchronizacja zamówień Shopify → panel księgowy (Dokumenty sprzedaży)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .shopify_orders import fetch_orders, order_to_row
from .storage import invoice_by_order_id

_COMPONENT_DIR = Path(__file__).resolve().parent
_SYNC_STATE_FILE = _COMPONENT_DIR / "dane" / "orders_sync_state.json"

_OnNewOrders = Callable[[list[dict[str, Any]]], None]
_callbacks: list[_OnNewOrders] = []


def register_on_new_orders(callback: _OnNewOrders | None) -> None:
    if callback is None:
        return
    if callback not in _callbacks:
        _callbacks.append(callback)


def _load_state() -> dict[str, Any]:
    if not _SYNC_STATE_FILE.is_file():
        return {}
    try:
        return json.loads(_SYNC_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, Any]) -> None:
    _SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SYNC_STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pending_orders_count() -> int:
    """Opłacone zamówienia bez wystawionego dokumentu (do obsługi w panelu)."""
    state = _load_state()
    pending = state.get("pending_order_ids") or []
    return len(pending)


def mark_order_handled(shopify_order_id: int) -> None:
    """Usuwa zamówienie z kolejki „nowych” po wystawieniu dokumentu."""
    state = _load_state()
    pending = [int(x) for x in (state.get("pending_order_ids") or [])]
    oid = int(shopify_order_id)
    if oid in pending:
        pending.remove(oid)
    state["pending_order_ids"] = pending
    _save_state(state)


def sync_accounting_orders(
    *,
    days_back: int = 30,
    logger: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    """Pobiera nowe opłacone zamówienia bez dokumentu. Zwraca listę do powiadomień."""
    log = logger or (lambda _m: None)
    state = _load_state()
    notified: set[int] = {int(x) for x in (state.get("notified_order_ids") or [])}
    pending: set[int] = {int(x) for x in (state.get("pending_order_ids") or [])}

    orders = fetch_orders(days_back=days_back, financial_status="paid", logger=log)
    new_rows: list[dict[str, Any]] = []

    for order in orders:
        oid = int(order.get("id") or 0)
        if not oid:
            continue
        if order.get("cancelled_at"):
            continue
        if invoice_by_order_id(oid):
            pending.discard(oid)
            continue
        row = order_to_row(order)
        if row.doc_status in ("issued", "corrected"):
            pending.discard(oid)
            continue
        pending.add(oid)
        if oid in notified:
            continue
        new_rows.append({
            "shopify_order_id": oid,
            "shopify_order_name": row.shopify_order_name,
            "customer_name": row.customer_name,
            "customer_email": row.customer_email,
            "shipping_country": row.shipping_country,
            "order_total": row.order_total,
            "currency": row.currency,
            "invoice_requested": row.invoice_requested,
            "suggested_language": row.suggested_language,
        })
        notified.add(oid)

    state["last_sync_iso"] = datetime.now(timezone.utc).isoformat()
    state["notified_order_ids"] = sorted(notified)
    state["pending_order_ids"] = sorted(pending)
    _save_state(state)

    if new_rows:
        for cb in _callbacks:
            try:
                cb(new_rows)
            except Exception:
                pass
    return new_rows
