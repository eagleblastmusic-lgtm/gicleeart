"""CRUD sprzedaży i kosztów DNR."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .models import CostEntry, SaleEntry, SaleKind
from .storage import (
    delete_cost_record,
    delete_sale_record,
    get_cost,
    get_sale,
    new_cost_id,
    new_sale_id,
    save_cost,
    save_sale,
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_date(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return date.today().isoformat()
    if len(raw) == 10 and raw[4] == "-":
        return raw
    for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return date.today().isoformat()


def _parse_amount(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return 0.0
    return round(float(raw), 2)


def resolve_sale_amounts(
    *,
    amount_pln: float | str = 0,
    list_price_pln: float | str = 0,
    discount_pln: float | str = 0,
) -> tuple[float, float, float]:
    """Wylicza (cena, rabat, przychód należny). Do limitu idzie kwota należna po rabacie."""
    list_p = _parse_amount(list_price_pln)
    disc = _parse_amount(discount_pln)
    net_in = _parse_amount(amount_pln)
    if list_p > 0 and disc > 0:
        return list_p, disc, round(max(0.0, list_p - disc), 2)
    if list_p > 0 and net_in > 0:
        inferred_disc = round(max(0.0, list_p - net_in), 2)
        return list_p, inferred_disc, net_in
    if list_p > 0:
        return list_p, 0.0, list_p
    if disc > 0 and net_in > 0:
        return round(net_in + disc, 2), disc, net_in
    return 0.0, 0.0, net_in


def _enrich_description(
    description: str,
    *,
    list_price: float,
    discount: float,
    net: float,
    entry_kind: str,
) -> str:
    desc = (description or "").strip()
    if entry_kind != "sale" or net <= 0:
        return desc
    if desc:
        return desc
    if list_price > 0 and discount > 0:
        return f"Sprzedaż {list_price:.2f} zł − rabat {discount:.2f} zł = {net:.2f} zł"
    return f"Sprzedaż po rabacie — {net:.2f} zł" if discount > 0 else desc


def _touch_migration() -> None:
    from .migration_service import persist_migration_sync

    persist_migration_sync()


def create_sale(
    *,
    event_date: str,
    amount_pln: float | str = 0,
    list_price_pln: float | str = 0,
    discount_pln: float | str = 0,
    description: str = "",
    document_number: str = "",
    source: str = "manual",
    entry_kind: str = "sale",
    invoice_id: str = "",
    currency: str = "PLN",
    amount_original: float = 0.0,
    merchant_of_record: bool | None = None,
    payment_status: str = "paid",
    paid_at: str = "",
    amount_received_pln: float | str | None = None,
    shopify_order_id: int = 0,
    destination_country: str = "",
    fulfillment_country: str = "PL",
) -> SaleEntry:
    now = _now_iso()
    kind = entry_kind if entry_kind in ("sale", "refund", "correction", "bonification") else "sale"
    src = source if source in ("manual", "invoice", "shopify", "allegro") else "manual"
    if merchant_of_record is None:
        if src == "allegro":
            from Komponenty._shared.tax_config import merchant_of_record_default
            mor = merchant_of_record_default("allegro")
        else:
            mor = False
    else:
        mor = bool(merchant_of_record)
    list_p, disc, net = resolve_sale_amounts(
        amount_pln=amount_pln,
        list_price_pln=list_price_pln,
        discount_pln=discount_pln,
    )
    if net <= 0:
        raise ValueError("Przychód należny musi być większy od zera.")
    pay_st = payment_status if payment_status in ("unpaid", "paid", "partial") else "paid"
    if amount_received_pln is None:
        received = net if pay_st in ("paid", "partial") else 0.0
    else:
        received = _parse_amount(amount_received_pln)
    paid_iso = (paid_at or "").strip()[:19]
    if pay_st == "paid" and not paid_iso:
        paid_iso = _parse_date(event_date) + "T12:00:00"[:19]
    entry = SaleEntry(
        id=new_sale_id(),
        event_date=_parse_date(event_date),
        amount_pln=net,
        list_price_pln=list_p,
        discount_pln=disc,
        description=_enrich_description(
            description, list_price=list_p, discount=disc, net=net, entry_kind=kind,
        ),
        document_number=(document_number or "").strip(),
        source=src,  # type: ignore[arg-type]
        entry_kind=kind,  # type: ignore[arg-type]
        invoice_id=(invoice_id or "").strip(),
        currency=(currency or "PLN").strip().upper(),
        amount_original=round(float(amount_original or list_p or net), 2),
        merchant_of_record=mor,
        payment_status=pay_st,  # type: ignore[arg-type]
        paid_at=paid_iso,
        amount_received_pln=received,
        shopify_order_id=int(shopify_order_id or 0),
        destination_country=(destination_country or "").strip().upper()[:2],
        fulfillment_country=(fulfillment_country or "PL").strip().upper()[:2] or "PL",
        created_at=now,
        updated_at=now,
    )
    save_sale(entry)
    _touch_migration()
    return entry


def create_adjustment(
    *,
    event_date: str,
    amount_pln: float | str,
    entry_kind: SaleKind = "refund",
    description: str = "",
    document_number: str = "",
    source: str = "manual",
    shopify_order_id: int = 0,
) -> SaleEntry:
    """Zwrot, korekta lub bonifikata — zmniejsza przychód w limicie kwartalnym."""
    return create_sale(
        event_date=event_date,
        amount_pln=amount_pln,
        description=description,
        document_number=document_number,
        source=source,
        entry_kind=entry_kind,
        shopify_order_id=shopify_order_id,
    )


def update_sale(sale_id: str, **fields: Any) -> SaleEntry | None:
    entry = get_sale(sale_id)
    if not entry:
        return None
    if "event_date" in fields:
        entry.event_date = _parse_date(str(fields["event_date"]))
    if "amount_pln" in fields:
        entry.amount_pln = _parse_amount(fields["amount_pln"])
    if "description" in fields:
        entry.description = str(fields["description"] or "").strip()
    if "document_number" in fields:
        entry.document_number = str(fields["document_number"] or "").strip()
    if "entry_kind" in fields:
        kind = str(fields["entry_kind"] or "sale")
        if kind in ("sale", "refund", "correction", "bonification"):
            entry.entry_kind = kind  # type: ignore[assignment]
    if "list_price_pln" in fields or "discount_pln" in fields or "amount_pln" in fields:
        list_p, disc, net = resolve_sale_amounts(
            amount_pln=fields.get("amount_pln", entry.amount_pln),
            list_price_pln=fields.get("list_price_pln", entry.list_price_pln),
            discount_pln=fields.get("discount_pln", entry.discount_pln),
        )
        entry.list_price_pln = list_p
        entry.discount_pln = disc
        entry.amount_pln = net
    if "merchant_of_record" in fields:
        entry.merchant_of_record = bool(fields["merchant_of_record"])
    if "payment_status" in fields:
        ps = str(fields["payment_status"] or "paid")
        if ps in ("unpaid", "paid", "partial"):
            entry.payment_status = ps  # type: ignore[assignment]
    if "paid_at" in fields:
        entry.paid_at = str(fields["paid_at"] or "").strip()[:19]
    if "amount_received_pln" in fields:
        entry.amount_received_pln = _parse_amount(fields["amount_received_pln"])
    if "shopify_order_id" in fields:
        entry.shopify_order_id = int(fields["shopify_order_id"] or 0)
    if "destination_country" in fields:
        entry.destination_country = str(fields["destination_country"] or "").strip().upper()[:2]
    if "fulfillment_country" in fields:
        entry.fulfillment_country = str(fields["fulfillment_country"] or "PL").strip().upper()[:2] or "PL"
    entry.updated_at = _now_iso()
    save_sale(entry)
    _touch_migration()
    return entry


def delete_sale(sale_id: str) -> bool:
    ok = delete_sale_record(sale_id)
    if ok:
        _touch_migration()
    return ok


def delete_sales_many(sale_ids: list[str]) -> int:
    removed = 0
    for sid in sale_ids:
        if delete_sale_record(sid):
            removed += 1
    if removed:
        _touch_migration()
    return removed


def create_cost(
    *,
    event_date: str,
    amount_pln: float | str,
    category: str = "inne",
    description: str = "",
    seller: str = "",
    document_number: str = "",
) -> CostEntry:
    now = _now_iso()
    entry = CostEntry(
        id=new_cost_id(),
        event_date=_parse_date(event_date),
        amount_pln=_parse_amount(amount_pln),
        category=(category or "inne").strip(),
        description=(description or "").strip(),
        seller=(seller or "").strip(),
        document_number=(document_number or "").strip(),
        created_at=now,
        updated_at=now,
    )
    save_cost(entry)
    return entry


def update_cost(cost_id: str, **fields: Any) -> CostEntry | None:
    entry = get_cost(cost_id)
    if not entry:
        return None
    if "event_date" in fields:
        entry.event_date = _parse_date(str(fields["event_date"]))
    if "amount_pln" in fields:
        entry.amount_pln = _parse_amount(fields["amount_pln"])
    if "category" in fields:
        entry.category = str(fields["category"] or "inne").strip()
    if "description" in fields:
        entry.description = str(fields["description"] or "").strip()
    if "seller" in fields:
        entry.seller = str(fields["seller"] or "").strip()
    if "document_number" in fields:
        entry.document_number = str(fields["document_number"] or "").strip()
    entry.updated_at = _now_iso()
    save_cost(entry)
    return entry


def delete_cost(cost_id: str) -> bool:
    return delete_cost_record(cost_id)


def delete_costs_many(cost_ids: list[str]) -> int:
    removed = 0
    for cid in cost_ids:
        if delete_cost_record(cid):
            removed += 1
    return removed
