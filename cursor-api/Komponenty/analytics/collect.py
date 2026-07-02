"""Przyjmowanie i walidacja eventów z pixela."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from .bots import classify_bot
from .env_config import allowed_shop_domain, collect_secret
from .models import ALL_EVENTS, CUSTOM_EVENTS, CollectPayload
from .privacy import (
    consent_allows_tracking,
    hash_customer_id,
    hash_identifier,
    ip_country_hint,
    sanitize_metadata,
    verify_collect_secret,
)
from .sources import classify_source, parse_utm_from_url
from . import sessions, settings, storage


class CollectError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


_RATE_BUCKETS: dict[str, list[float]] = {}
_RATE_LIMIT_PER_MIN = 120


def _check_rate_limit(ip_hash: str) -> None:
    if not ip_hash:
        return
    now = datetime.now(timezone.utc).timestamp()
    window = _RATE_BUCKETS.setdefault(ip_hash, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= _RATE_LIMIT_PER_MIN:
        raise CollectError("Rate limit exceeded", 429)
    window.append(now)


def _validate_shop_domain(payload: CollectPayload, origin: str) -> None:
    allowed = allowed_shop_domain()
    candidates = {
        payload.shop_domain.lower(),
        urlparse(payload.url).netloc.lower(),
        urlparse(origin).netloc.lower() if origin else "",
    }
    candidates.discard("")
    if not candidates:
        return
    ok = any(
        allowed in c or c.endswith(".myshopify.com") or c == allowed
        for c in candidates
    )
    if not ok and allowed not in "".join(candidates):
        raise CollectError("Shop domain not allowed", 403)


def _normalize_timestamp(ts: str) -> str:
    if not ts:
        return storage.utc_now_iso()
    try:
        if ts.endswith("Z"):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return storage.utc_now_iso()


def _ensure_ids(payload: CollectPayload) -> tuple[str, str, str]:
    event_id = payload.event_id or str(uuid.uuid4())
    visitor_raw = payload.visitor_id or secrets.token_hex(16)
    session_raw = payload.session_id or visitor_raw
    return (
        event_id,
        hash_identifier(visitor_raw, prefix="v"),
        session_raw,
    )


def ingest_event(
    data: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    client_ip: str = "",
) -> dict[str, Any]:
    headers = headers or {}
    secret_hdr = (
        headers.get("x-analytics-secret")
        or headers.get("X-Analytics-Secret")
        or data.get("secret")
        or ""
    )
    expected = collect_secret()
    if not expected:
        raise CollectError("ANALYTICS_COLLECT_SECRET not configured", 503)
    if not verify_collect_secret(str(secret_hdr), expected):
        raise CollectError("Invalid collect secret", 401)

    payload = CollectPayload.from_dict(data)
    if not payload.event_name:
        raise CollectError("event_name required", 400)
    if payload.event_name not in ALL_EVENTS:
        raise CollectError(f"Unknown event: {payload.event_name}", 400)

    if not consent_allows_tracking(payload.consent_status):
        return {"ok": True, "skipped": True, "reason": "consent_denied"}

    origin = headers.get("origin") or headers.get("Origin") or ""
    _validate_shop_domain(payload, origin)

    from .privacy import ip_hash_for_rate_limit

    ip_hash = ip_hash_for_rate_limit(client_ip)
    _check_rate_limit(ip_hash)

    event_id, visitor_hash, session_id = _ensure_ids(payload)
    if storage.event_exists(event_id):
        return {"ok": True, "duplicate": True, "event_id": event_id}

    created_at = _normalize_timestamp(payload.timestamp)
    since_hour = (
        datetime.now(timezone.utc) - timedelta(hours=1)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    session_count = storage.count_session_events(session_id, since_hour)

    utm = parse_utm_from_url(payload.url)
    utm_source = payload.utm_source or utm.get("utm_source", "")
    utm_medium = payload.utm_medium or utm.get("utm_medium", "")
    utm_campaign = payload.utm_campaign or utm.get("utm_campaign", "")
    utm_content = payload.utm_content or utm.get("utm_content", "")
    utm_term = payload.utm_term or utm.get("utm_term", "")

    country = (payload.country or ip_country_hint(headers) or "unknown").upper()[:2]
    if country == "UN":
        country = "unknown"

    path = payload.path or urlparse(payload.url).path
    source_bucket = classify_source(
        referrer=payload.referrer,
        utm_source=utm_source,
        utm_medium=utm_medium,
    )

    bot = classify_bot(
        user_agent=payload.user_agent,
        event_name=payload.event_name,
        session_id=session_id,
        session_event_count=session_count + 1,
    )

    event_type = "custom" if payload.event_name in CUSTOM_EVENTS else "standard"
    meta = dict(payload.metadata)
    if client_ip:
        meta["ip_hash"] = hash_identifier(client_ip.strip(), prefix="ip")
    meta_json = sanitize_metadata(meta)

    exclude_visitors, exclude_ips = settings.get_exclusions()
    visitor_ip_hash = meta.get("ip_hash") or ""
    if visitor_hash in exclude_visitors or (visitor_ip_hash and visitor_ip_hash in exclude_ips):
        return {"ok": True, "skipped": True, "reason": "excluded_traffic"}

    row = {
        "event_id": event_id,
        "event_name": payload.event_name,
        "event_type": event_type,
        "shopify_event_id": payload.metadata.get("shopify_event_id"),
        "visitor_id_hash": visitor_hash,
        "session_id": session_id,
        "customer_id_hash": hash_customer_id(payload.metadata.get("customer_id")),
        "shopify_customer_id_hash": hash_customer_id(
            payload.metadata.get("shopify_customer_id")
        ),
        "shopify_order_id": payload.shopify_order_id or None,
        "shopify_product_id": payload.shopify_product_id or None,
        "shopify_variant_id": payload.shopify_variant_id or None,
        "product_title": payload.product_title or None,
        "collection_id": payload.collection_id or None,
        "url": payload.url or None,
        "path": path or None,
        "page_title": payload.page_title or None,
        "referrer": payload.referrer or None,
        "utm_source": utm_source or None,
        "utm_medium": utm_medium or None,
        "utm_campaign": utm_campaign or None,
        "utm_content": utm_content or None,
        "utm_term": utm_term or None,
        "device_type": payload.device_type or None,
        "browser": payload.browser or None,
        "os": payload.os or None,
        "country": country,
        "region": payload.region or None,
        "language": payload.language or None,
        "currency": payload.currency or None,
        "cart_value": payload.cart_value,
        "checkout_value": payload.checkout_value,
        "order_value": payload.order_value,
        "quantity": payload.metadata.get("quantity"),
        "metadata_json": meta_json,
        "consent_status": payload.consent_status or None,
        "bot_suspected": 1 if bot else 0,
        "source_bucket": source_bucket,
        "ip_hash": visitor_ip_hash or None,
        "created_at": created_at,
    }

    if bot:
        storage.insert_event(row)
        return {"ok": True, "event_id": event_id, "bot_suspected": True}

    storage.insert_event(row)
    sessions.apply_event_to_session(row)
    return {"ok": True, "event_id": event_id}


def make_test_event() -> dict[str, Any]:
    return {
        "event_id": f"test_{uuid.uuid4().hex[:12]}",
        "event_name": "page_viewed",
        "timestamp": storage.utc_now_iso(),
        "visitor_id": "test_visitor",
        "session_id": f"test_session_{secrets.token_hex(4)}",
        "url": f"https://{allowed_shop_domain()}/",
        "path": "/",
        "page_title": "GicleeArt — test",
        "country": "PL",
        "consent_status": "granted",
        "shop_domain": allowed_shop_domain(),
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    }
