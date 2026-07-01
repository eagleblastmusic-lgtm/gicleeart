#!/usr/bin/env python3
"""Rejestruje webhook orders/paid w sklepie Shopify (jednorazowo po deploy Worker)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Komponenty" / "dodajobraz"))

import shopify_client as sc  # noqa: E402

WORKER_WEBHOOK_PATH = "/webhooks/shopify/orders-paid"


def main() -> None:
    if len(sys.argv) < 2:
        print("Uzycie: python scripts/register_webhook.py https://TWOJ-WORKER.workers.dev")
        print("Przyklad: python scripts/register_webhook.py https://giclee-mockup-orders.twoj-konto.workers.dev")
        sys.exit(1)

    worker_base = sys.argv[1].rstrip("/")
    address = worker_base + WORKER_WEBHOOK_PATH

    shop, token = sc.load_session()
    payload = {
        "webhook": {
            "topic": "orders/paid",
            "address": address,
            "format": "json",
        }
    }
    out = sc.rest_post(shop, token, "webhooks.json", payload)
    wh = (out or {}).get("webhook") or {}
    print("OK — webhook orders/paid")
    print("  id:", wh.get("id"))
    print("  address:", wh.get("address"))
    print()
    print("Ustaw ten sam secret w Workerze:")
    print("  wrangler secret put SHOPIFY_WEBHOOK_SECRET")
    print("(Shopify Partner → App → API → Webhook signing secret LUB secret z rejestracji custom app)")


if __name__ == "__main__":
    main()
