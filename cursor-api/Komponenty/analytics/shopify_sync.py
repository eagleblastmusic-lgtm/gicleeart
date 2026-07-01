"""Synchronizacja zamówień Shopify z eventami checkout_completed."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from Komponenty.dodajobraz import shopify_client as sc

from . import sessions, storage
from .privacy import hash_identifier
from .sources import classify_source

_ORDER_FIELDS = (
    "id,name,created_at,processed_at,financial_status,total_price,currency,"
    "customer,shipping_address,billing_address,line_items,landing_site,"
    "referring_site,source_name,client_details,tags"
)

_SESSION_FILE = Path(__file__).resolve().parents[2] / ".shopify_session.json"


class ShopifySyncError(Exception):
    pass


def _session_scopes() -> set[str]:
    if not _SESSION_FILE.is_file():
        return set()
    try:
        data = json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    scope = str(data.get("scope") or "")
    return {s.strip() for s in scope.split(",") if s.strip()}


def _require_orders_scope() -> None:
    scopes = _session_scopes()
    if scopes and "read_orders" not in scopes:
        raise ShopifySyncError(
            "Brak scope read_orders w sesji OAuth. "
            "Ustaw SCOPES w .env (jak w shopify.app.toml) i uruchom ponownie: npm run oauth"
        )


def sync_orders(
    *,
    days_back: int = 30,
    logger: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Pobiera zamówienia i uzupełnia atrybucję + brakujące checkout_completed."""
    log = logger or (lambda _m: None)
    _require_orders_scope()
    shop, token = sc.load_session()
    since_dt = datetime.now(timezone.utc) - timedelta(days=max(1, days_back))
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    log(f"[analytics] Sync zamówień od {since[:10]}...")
    try:
        orders = sc.iter_orders_since(
            shop,
            token,
            created_at_min=since,
            financial_status="paid",
            status="any",
            fields=_ORDER_FIELDS,
        )
    except sc.ShopifyError as exc:
        msg = str(exc)
        if "403" in msg or "Access denied" in msg.lower():
            raise ShopifySyncError(
                "Shopify odmówił dostępu do zamówień (403). "
                "Ponów OAuth z scope read_orders: npm run oauth"
            ) from exc
        raise ShopifySyncError(msg) from exc
    linked = 0
    attributed = 0

    for order in orders:
        oid = str(order.get("id") or "")
        if not oid:
            continue
        total = float(order.get("total_price") or 0)
        currency = str(order.get("currency") or "PLN")
        created = str(order.get("created_at") or "")[:19] + "Z"
        country = _order_country(order)
        utm_source, utm_medium, utm_campaign = _order_utm(order)
        source = classify_source(
            referrer=str(order.get("referring_site") or ""),
            utm_source=utm_source,
            utm_medium=utm_medium,
        )

        if not _order_has_checkout_event(oid):
            _insert_synthetic_checkout(
                order_id=oid,
                total=total,
                currency=currency,
                created_at=created,
                country=country,
                source_bucket=source,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
            )
            linked += 1

        _upsert_attribution(order, country=country, source=source)
        attributed += 1

    log(f"[analytics] Sync: {len(orders)} zamówień, {linked} nowych eventów, {attributed} atrybucji.")
    return {
        "orders_fetched": len(orders),
        "checkout_events_created": linked,
        "attributions_upserted": attributed,
        "oauth_scopes": sorted(_session_scopes()),
        "shop": shop,
    }


def _order_country(order: dict[str, Any]) -> str:
    ship = order.get("shipping_address") or {}
    bill = order.get("billing_address") or {}
    cc = (
        ship.get("country_code")
        or bill.get("country_code")
        or ship.get("country")
        or bill.get("country")
        or ""
    )
    return str(cc or "unknown").upper()[:2]


def _order_utm(order: dict[str, Any]) -> tuple[str, str, str]:
    landing = str(order.get("landing_site") or "")
    from urllib.parse import parse_qs, urlparse

    try:
        qs = parse_qs(urlparse(landing).query)
    except Exception:
        return "", "", ""
    return (
        (qs.get("utm_source") or [""])[0],
        (qs.get("utm_medium") or [""])[0],
        (qs.get("utm_campaign") or [""])[0],
    )


def _order_has_checkout_event(order_id: str) -> bool:
    with storage.connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM analytics_events
            WHERE shopify_order_id = ? AND event_name = 'checkout_completed'
            LIMIT 1
            """,
            (order_id,),
        ).fetchone()
        return row is not None


def _insert_synthetic_checkout(
    *,
    order_id: str,
    total: float,
    currency: str,
    created_at: str,
    country: str,
    source_bucket: str,
    utm_source: str,
    utm_medium: str,
    utm_campaign: str,
) -> None:
    event_id = f"shopify_order_{order_id}"
    if storage.event_exists(event_id):
        return
    session_id = f"shopify_sync_{order_id}"
    visitor_hash = hash_identifier(f"order_{order_id}", prefix="v")
    storage.insert_event({
        "event_id": event_id,
        "event_name": "checkout_completed",
        "event_type": "standard",
        "shopify_event_id": None,
        "visitor_id_hash": visitor_hash,
        "session_id": session_id,
        "customer_id_hash": None,
        "shopify_customer_id_hash": None,
        "shopify_order_id": order_id,
        "shopify_product_id": None,
        "shopify_variant_id": None,
        "product_title": None,
        "collection_id": None,
        "url": None,
        "path": "/checkout",
        "page_title": "Shopify sync",
        "referrer": None,
        "utm_source": utm_source or None,
        "utm_medium": utm_medium or None,
        "utm_campaign": utm_campaign or None,
        "utm_content": None,
        "utm_term": None,
        "device_type": None,
        "browser": None,
        "os": None,
        "country": country,
        "region": None,
        "language": None,
        "currency": currency,
        "cart_value": None,
        "checkout_value": total,
        "order_value": total,
        "quantity": None,
        "metadata_json": json.dumps({"source": "shopify_sync", "match_type": "estimated"}),
        "consent_status": None,
        "bot_suspected": 0,
        "source_bucket": source_bucket,
        "created_at": created_at if "T" in created_at else storage.utc_now_iso(),
    })
    sessions.apply_event_to_session({
        "session_id": session_id,
        "visitor_id_hash": visitor_hash,
        "event_name": "checkout_completed",
        "created_at": created_at,
        "country": country,
        "source_bucket": source_bucket,
        "path": "/checkout",
        "order_value": total,
        "checkout_value": total,
        "shopify_order_id": order_id,
        "bot_suspected": 0,
    })


def _upsert_attribution(order: dict[str, Any], *, country: str, source: str) -> None:
    oid = str(order.get("id") or "")
    total = float(order.get("total_price") or 0)
    utm_source, utm_medium, utm_campaign = _order_utm(order)
    landing = str(order.get("landing_site") or "")
    path_json = json.dumps([landing] if landing else [], ensure_ascii=False)
    created = str(order.get("created_at") or "")[:19] + "Z"

    with storage.connect() as conn:
        conn.execute(
            """
            INSERT INTO analytics_attribution (
                order_id, session_id, visitor_id_hash,
                first_touch_source, first_touch_medium, first_touch_campaign,
                last_touch_source, last_touch_medium, last_touch_campaign,
                landing_page, conversion_path_json, revenue, country, match_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                revenue = excluded.revenue,
                last_touch_source = excluded.last_touch_source,
                last_touch_medium = excluded.last_touch_medium,
                last_touch_campaign = excluded.last_touch_campaign
            """,
            (
                oid,
                None,
                hash_identifier(f"order_{oid}", prefix="v"),
                utm_source or source,
                utm_medium or "",
                utm_campaign or "",
                utm_source or source,
                utm_medium or "",
                utm_campaign or "",
                landing or None,
                path_json,
                total,
                country,
                "shopify_order",
                created,
            ),
        )
