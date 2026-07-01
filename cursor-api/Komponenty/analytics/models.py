"""Typy i stałe modułu analityki."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Standardowe eventy Shopify Customer Events
STANDARD_EVENTS = frozenset({
    "page_viewed",
    "product_viewed",
    "collection_viewed",
    "search_submitted",
    "product_added_to_cart",
    "product_removed_from_cart",
    "cart_viewed",
    "checkout_started",
    "checkout_contact_info_submitted",
    "checkout_shipping_info_submitted",
    "payment_info_submitted",
    "checkout_completed",
})

CUSTOM_EVENTS = frozenset({
    "giclee_app:frame_config_started",
    "giclee_app:frame_size_selected",
    "giclee_app:frame_color_selected",
    "giclee_app:passepartout_selected",
    "giclee_app:print_size_selected",
    "giclee_app:product_customized",
    "giclee_app:price_calculated",
    "giclee_app:cta_clicked",
})

ALL_EVENTS = STANDARD_EVENTS | CUSTOM_EVENTS

FUNNEL_STAGES = (
    "page_viewed",
    "product_viewed",
    "product_added_to_cart",
    "checkout_started",
    "checkout_completed",
)

SOURCE_BUCKETS = (
    "direct",
    "organic_search",
    "paid",
    "social",
    "referral",
    "email",
    "unknown",
)


@dataclass
class CollectPayload:
    event_id: str
    event_name: str
    timestamp: str
    visitor_id: str = ""
    session_id: str = ""
    url: str = ""
    path: str = ""
    page_title: str = ""
    referrer: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""
    shopify_product_id: str = ""
    shopify_variant_id: str = ""
    collection_id: str = ""
    product_title: str = ""
    cart_value: float | None = None
    checkout_value: float | None = None
    order_value: float | None = None
    shopify_order_id: str = ""
    currency: str = ""
    country: str = ""
    region: str = ""
    language: str = ""
    device_type: str = ""
    browser: str = ""
    os: str = ""
    consent_status: str = ""
    user_agent: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    shop_domain: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CollectPayload:
        meta = data.get("metadata") or data.get("metadata_json") or {}
        if not isinstance(meta, dict):
            meta = {}
        return cls(
            event_id=str(data.get("event_id") or "").strip(),
            event_name=str(data.get("event_name") or "").strip(),
            timestamp=str(data.get("timestamp") or "").strip(),
            visitor_id=str(data.get("visitor_id") or data.get("client_id") or "").strip(),
            session_id=str(data.get("session_id") or "").strip(),
            url=str(data.get("url") or "").strip(),
            path=str(data.get("path") or "").strip(),
            page_title=str(data.get("page_title") or "").strip(),
            referrer=str(data.get("referrer") or "").strip(),
            utm_source=str(data.get("utm_source") or "").strip(),
            utm_medium=str(data.get("utm_medium") or "").strip(),
            utm_campaign=str(data.get("utm_campaign") or "").strip(),
            utm_content=str(data.get("utm_content") or "").strip(),
            utm_term=str(data.get("utm_term") or "").strip(),
            shopify_product_id=str(
                data.get("shopify_product_id") or data.get("product_id") or ""
            ).strip(),
            shopify_variant_id=str(
                data.get("shopify_variant_id") or data.get("variant_id") or ""
            ).strip(),
            collection_id=str(data.get("collection_id") or "").strip(),
            product_title=str(data.get("product_title") or "").strip(),
            cart_value=_opt_float(data.get("cart_value")),
            checkout_value=_opt_float(data.get("checkout_value")),
            order_value=_opt_float(data.get("order_value")),
            shopify_order_id=str(data.get("shopify_order_id") or data.get("order_id") or "").strip(),
            currency=str(data.get("currency") or "").strip(),
            country=str(data.get("country") or "").strip(),
            region=str(data.get("region") or "").strip(),
            language=str(data.get("language") or "").strip(),
            device_type=str(data.get("device_type") or "").strip(),
            browser=str(data.get("browser") or "").strip(),
            os=str(data.get("os") or "").strip(),
            consent_status=str(data.get("consent_status") or "").strip(),
            user_agent=str(data.get("user_agent") or "").strip(),
            metadata=meta,
            shop_domain=str(data.get("shop_domain") or "").strip(),
        )


def _opt_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
