#!/usr/bin/env python3
"""Ponownie wywołuje webhook orders/paid dla zamówienia (gdy webhook nie był jeszcze zarejestrowany)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Komponenty" / "dodajobraz"))

import shopify_client as sc  # noqa: E402

WORKER_URL = "https://giclee-mockup-orders.eagleblastmusic.workers.dev/webhooks/shopify/orders-paid"


def load_webhook_secret() -> str:
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("SHOPIFY_WEBHOOK_SECRET", "SHOPIFY_API_SECRET") and v:
                os.environ.setdefault(k, v)
    try:
        from Komponenty.nazwijobraz.env_loader import load_env

        load_env()
    except Exception:
        pass
    for key in ("SHOPIFY_WEBHOOK_SECRET", "SHOPIFY_API_SECRET"):
        v = (os.environ.get(key) or "").strip()
        if v:
            return v
    return ""


def shopify_hmac(body: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def main() -> None:
    order_id = sys.argv[1] if len(sys.argv) > 1 else None
    shop, token = sc.load_session()
    if order_id:
        out = sc.rest_get(shop, token, f"orders/{order_id}.json")
        order = (out or {}).get("order")
    else:
        data = sc.rest_get(shop, token, "orders.json", status="any", limit=1, order="created_at desc")
        orders = (data or {}).get("orders") or []
        order = orders[0] if orders else None

    if not order:
        print("Brak zamowienia")
        sys.exit(1)

    secret = load_webhook_secret()
    if not secret:
        print("Brak SHOPIFY_WEBHOOK_SECRET lub SHOPIFY_API_SECRET w cursor-api/.env")
        sys.exit(1)

    body = json.dumps(order, ensure_ascii=False)
    sig = shopify_hmac(body, secret)

    # Cloudflare (1010) blokuje domyślny Python-urllib; Shopify używa tego User-Agent.
    req = urllib.request.Request(
        WORKER_URL,
        data=body.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": sig,
            "User-Agent": "Shopify-Captain-Hook",
            "Accept": "*/*",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print("Worker response:", resp.status, resp.read().decode("utf-8", errors="replace")[:200])
    except urllib.error.HTTPError as e:
        print("Worker HTTP", e.code, e.read().decode("utf-8", errors="replace")[:500])
        sys.exit(1)

    print("OK — wyslano webhook dla", order.get("name"), "-> sprawdz gicleeartpl@gmail.com")


if __name__ == "__main__":
    main()
