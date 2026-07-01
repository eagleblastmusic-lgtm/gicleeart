"""Linki do panelu Shopify Admin."""
from __future__ import annotations


def admin_order_url(shop_domain: str, order_numeric_id: int) -> str:
    """`shop_domain` np. 'moj-sklep.myshopify.com' -> URL zamowienia w Admin."""
    raw = (shop_domain or "").strip().lower()
    if not raw:
        return ""
    sub = raw.split(".")[0]
    if not sub:
        return ""
    return f"https://admin.shopify.com/store/{sub}/orders/{int(order_numeric_id)}"
