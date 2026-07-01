"""Import sprzedaży Shopify → ewidencja DNR (po opłaceniu)."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty.dokumentysprzedazy.country import is_eu_b2c, normalize_country
from Komponenty.dokumentysprzedazy.nbp_service import convert_amounts_to_pln, fetch_rate_for_income_date, income_date_from_order
from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id

from .entry_service import create_adjustment, create_sale
from .import_policy import shopify_dnr_import_blocked
from .storage import sale_for_invoice, sale_for_shopify_order

_BOOKABLE_STATUS = frozenset({"paid", "partially_refunded", "refunded"})


def _float(val: Any) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _shipping_country(order: dict[str, Any]) -> str:
    ship = order.get("shipping_address") or {}
    return normalize_country(str(ship.get("country_code") or ship.get("country") or ""))


def _fulfillment_country(order: dict[str, Any]) -> str:
    for fl in order.get("fulfillments") or []:
        loc = fl.get("location") or {}
        cc = normalize_country(str(loc.get("country_code") or ""))
        if cc:
            return cc
    return "PL"


def _order_amounts_pln(order: dict[str, Any]) -> tuple[float, float, float, float]:
    """(list_price, discount, net_pln, original_total)."""
    currency = str(order.get("currency") or "PLN").upper()
    subtotal = _float(order.get("subtotal_price"))
    discount = round(abs(_float(order.get("total_discounts"))), 2)
    total = _float(order.get("total_price"))
    payment_date = str(order.get("processed_at") or order.get("created_at") or "")
    income_dt = income_date_from_order(payment_date, str(order.get("created_at") or ""))
    rate_info = fetch_rate_for_income_date(currency, income_dt)
    rate = float(rate_info.get("exchange_rate_value") or 1)
    pln = convert_amounts_to_pln(
        products=subtotal,
        shipping=0,
        discounts=discount,
        total=total,
        rate=rate,
    )
    net = pln["total_amount_pln"]
    list_p = round(net + pln["discounts_amount_pln"], 2) if discount else net
    return list_p, pln["discounts_amount_pln"], net, total


def can_import_order(order: dict[str, Any]) -> tuple[bool, str]:
    oid = int(order.get("id") or 0)
    if not oid:
        return False, "brak ID"
    if order.get("cancelled_at"):
        return False, "anulowane"
    fin = str(order.get("financial_status") or "")
    if fin not in _BOOKABLE_STATUS:
        return False, f"status płatności: {fin}"
    if sale_for_shopify_order(oid):
        return False, "już w DNR"
    inv = invoice_by_order_id(oid)
    if inv and inv.id and sale_for_invoice(inv.id):
        return False, "faktura już zaimportowana do DNR"
    return True, "ok"


def _payment_date(order: dict[str, Any]) -> str:
    return str(order.get("processed_at") or order.get("created_at") or "")[:10]


def import_shopify_order(order: dict[str, Any]) -> tuple[bool, str]:
    blocked, block_msg = shopify_dnr_import_blocked()
    if blocked:
        return False, block_msg
    ok, reason = can_import_order(order)
    if not ok:
        return False, reason
    oid = int(order.get("id") or 0)
    name = str(order.get("name") or "")
    list_p, disc, net, orig = _order_amounts_pln(order)
    paid = _payment_date(order)
    dest = _shipping_country(order)
    fulfill = _fulfillment_country(order)
    inv = invoice_by_order_id(oid)
    create_sale(
        event_date=paid,
        amount_pln=net,
        list_price_pln=list_p,
        discount_pln=disc,
        description=f"Shopify {name}",
        document_number=name,
        source="shopify",
        invoice_id=inv.id if inv else "",
        currency=str(order.get("currency") or "PLN"),
        amount_original=orig,
        payment_status="paid",
        paid_at=str(order.get("processed_at") or "")[:19],
        amount_received_pln=net,
        shopify_order_id=oid,
        destination_country=dest,
        fulfillment_country=fulfill,
    )
    return True, f"Zaimportowano {name} ({net:.2f} PLN)."


def _refund_amount_pln(refund: dict[str, Any], order: dict[str, Any]) -> float:
    currency = str(order.get("currency") or "PLN").upper()
    total = _float(refund.get("total_refunded") or refund.get("amount"))
    if total <= 0:
        for tx in refund.get("transactions") or []:
            total += _float(tx.get("amount"))
    if total <= 0:
        return 0.0
    payment_date = str(refund.get("processed_at") or refund.get("created_at") or order.get("processed_at") or "")
    income_dt = income_date_from_order(payment_date, str(order.get("created_at") or ""))
    rate_info = fetch_rate_for_income_date(currency, income_dt)
    rate = float(rate_info.get("exchange_rate_value") or 1)
    return convert_amounts_to_pln(products=0, shipping=0, discounts=0, total=total, rate=rate)["total_amount_pln"]


def import_shopify_refunds(order: dict[str, Any]) -> int:
    """Import zwrotów Shopify jako wpisy korygujące DNR."""
    oid = int(order.get("id") or 0)
    if not oid or not sale_for_shopify_order(oid):
        return 0
    imported = 0
    for refund in order.get("refunds") or []:
        amt = round(_refund_amount_pln(refund, order), 2)
        if amt <= 0:
            continue
        ref_date = str(refund.get("processed_at") or refund.get("created_at") or "")[:10]
        doc = f"{order.get('name')}-REF-{imported + 1}"
        create_adjustment(
            event_date=ref_date or date.today().isoformat(),
            amount_pln=amt,
            entry_kind="refund",
            description=f"Zwrot Shopify {order.get('name')}",
            document_number=doc,
            source="shopify",
            shopify_order_id=oid,
        )
        imported += 1
    return imported


def list_importable_shopify_orders(year: int | None = None) -> list[dict[str, Any]]:
    blocked, _ = shopify_dnr_import_blocked()
    if blocked:
        return []
    try:
        from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
    except ImportError:
        return []
    y = year or date.today().year
    out: list[dict[str, Any]] = []
    for order in fetch_orders(days_back=400, financial_status=None):
        ok, reason = can_import_order(order)
        if not ok:
            continue
        paid = _payment_date(order)
        if paid and int(paid[:4]) != y:
            continue
        _, _, net, _ = _order_amounts_pln(order)
        out.append({
            "shopify_order_id": int(order.get("id") or 0),
            "name": str(order.get("name") or ""),
            "payment_date": paid,
            "amount_pln": net,
            "destination_country": _shipping_country(order),
            "fulfillment_country": _fulfillment_country(order),
            "is_eu_b2c": is_eu_b2c(_shipping_country(order)),
            "financial_status": str(order.get("financial_status") or ""),
        })
    out.sort(key=lambda r: r.get("payment_date") or "", reverse=True)
    return out


def import_all_shopify_for_year(year: int) -> tuple[int, int]:
    blocked, _ = shopify_dnr_import_blocked()
    if blocked:
        return 0, 0
    try:
        from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
    except ImportError:
        return 0, 0
    imported = skipped = 0
    for order in fetch_orders(days_back=400, financial_status=None):
        paid = _payment_date(order)
        if paid and int(paid[:4]) != year:
            continue
        ok, _ = import_shopify_order(order)
        if ok:
            imported += 1
            import_shopify_refunds(order)
        else:
            skipped += 1
    return imported, skipped
