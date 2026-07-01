"""Pobieranie zamówień Shopify i aktualizacja tagów."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc

from .constants import SHOPIFY_INVOICE_TAGS
from .order_attributes import parse_invoice_request
from .country import is_eu_b2c, is_foreign_order, suggest_language
from .i18n import normalize_language
from .models import OrderRow
from .storage import invoice_by_order_id, invoices_for_order

_ORDER_FIELDS = (
    "id,name,created_at,updated_at,processed_at,cancelled_at,financial_status,"
    "fulfillment_status,email,subtotal_price,total_discounts,total_shipping_price_set,"
    "total_price,total_tax,taxes_included,currency,customer,shipping_address,billing_address,line_items,"
    "note,tags,refunds,payment_gateway_names,note_attributes,fulfillments,tax_lines"
)


def _float(val: Any) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _customer_name(order: dict[str, Any]) -> str:
    cust = order.get("customer") or {}
    first = str(cust.get("first_name") or "").strip()
    last = str(cust.get("last_name") or "").strip()
    name = f"{first} {last}".strip()
    if name:
        return name
    ship = order.get("shipping_address") or {}
    return str(ship.get("name") or "").strip() or "(brak)"


def _shipping_country(order: dict[str, Any]) -> str:
    ship = order.get("shipping_address") or {}
    return str(ship.get("country_code") or ship.get("country") or "").strip()


def _payment_date(order: dict[str, Any]) -> str:
    return str(order.get("processed_at") or order.get("created_at") or "")[:19]


def _shipping_total(order: dict[str, Any]) -> float:
    ship_set = order.get("total_shipping_price_set") or {}
    shop = (ship_set.get("shop_money") or {})
    if shop.get("amount") is not None:
        return _float(shop.get("amount"))
    return _float(order.get("total_shipping_price_set"))


def _doc_status_for_order(order_id: int) -> tuple[str, str, str]:
    inv = invoice_by_order_id(order_id)
    if inv:
        return inv.status, inv.invoice_number, inv.id
    drafts = [i for i in invoices_for_order(order_id) if i.status == "draft"]
    if drafts:
        d = drafts[-1]
        return "draft", d.invoice_number or "", d.id
    cancelled = [i for i in invoices_for_order(order_id) if i.status == "cancelled"]
    if cancelled:
        c = cancelled[-1]
        return "cancelled", c.invoice_number or "", c.id
    return "not_issued", "", ""


def fetch_orders(
    *,
    days_back: int = 365,
    financial_status: str | None = None,
    logger: Callable[[str], None] | None = None,
) -> list[dict[str, Any]]:
    shop, token = sc.load_session()
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, days_back))).isoformat()
    log = logger or (lambda _m: None)
    log(f"[dokumenty] Pobieram zamówienia od {since[:10]}...")
    orders = sc.iter_orders_since(
        shop,
        token,
        created_at_min=since,
        financial_status=financial_status,
        fields=_ORDER_FIELDS,
    )
    log(f"[dokumenty] Pobrano {len(orders)} zamówień.")
    return orders


def order_to_row(order: dict[str, Any]) -> OrderRow:
    oid = int(order.get("id") or 0)
    country = _shipping_country(order)
    subtotal = _float(order.get("subtotal_price"))
    discounts = _float(order.get("total_discounts"))
    shipping = _shipping_total(order)
    total = _float(order.get("total_price"))
    doc_status, inv_no, inv_id = _doc_status_for_order(oid)
    refunds = order.get("refunds") or []
    inv_req = parse_invoice_request(order)
    return OrderRow(
        shopify_order_id=oid,
        shopify_order_name=str(order.get("name") or ""),
        created_at=str(order.get("created_at") or "")[:19],
        payment_date=_payment_date(order),
        financial_status=str(order.get("financial_status") or ""),
        fulfillment_status=str(order.get("fulfillment_status") or "") or "unfulfilled",
        customer_name=_customer_name(order),
        customer_email=str(order.get("email") or (order.get("customer") or {}).get("email") or ""),
        shipping_country=country,
        currency=str(order.get("currency") or "PLN"),
        products_total=round(subtotal, 2),
        shipping_total=round(shipping, 2),
        discounts_total=round(discounts, 2),
        order_total=round(total, 2),
        doc_status=doc_status,  # type: ignore[arg-type]
        invoice_number=inv_no,
        invoice_id=inv_id,
        is_foreign=is_foreign_order(country),
        is_eu_b2c=is_eu_b2c(country),
        is_cancelled=bool(order.get("cancelled_at")),
        has_refund=bool(refunds),
        suggested_language=suggest_language(country),
        invoice_requested=inv_req.requested,
        invoice_customer_type=inv_req.customer_type,
    )


def append_order_tags(shopify_order_id: int, extra_tags: list[str]) -> None:
    shop, token = sc.load_session()
    path = f"orders/{shopify_order_id}.json"
    data = sc.rest_get(shop, token, path)
    order = (data or {}).get("order") or {}
    existing = [t.strip() for t in str(order.get("tags") or "").split(",") if t.strip()]
    merged = existing[:]
    for tag in extra_tags:
        if tag not in merged:
            merged.append(tag)
    sc.rest_put(shop, token, path, {"order": {"id": shopify_order_id, "tags": ", ".join(merged)}})


def mark_invoice_issued_on_shopify(shopify_order_id: int, language: str) -> None:
    tags = list(SHOPIFY_INVOICE_TAGS)
    lang = normalize_language(language)
    tags.append(f"invoice_language_{lang}")
    append_order_tags(shopify_order_id, tags)
