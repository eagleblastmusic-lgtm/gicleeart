"""Test parsowania Shop.currencySettings (EUR)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.dodajobraz import shopify_client as sc  # noqa: E402


def test_get_presentment_currency_setting_finds_eur() -> None:
    fake = {
        "shop": {
            "currencyCode": "PLN",
            "currencySettings": {
                "edges": [
                    {
                        "node": {
                            "currencyCode": "USD",
                            "currencyName": "US Dollar",
                            "enabled": True,
                            "manualRate": None,
                            "rateUpdatedAt": "2026-01-01T10:00:00Z",
                        },
                    },
                    {
                        "node": {
                            "currencyCode": "EUR",
                            "currencyName": "Euro",
                            "enabled": True,
                            "manualRate": "0.231",
                            "rateUpdatedAt": "2026-04-20T12:00:00+02:00",
                        },
                    },
                ],
            },
        },
    }
    with patch.object(sc, "graphql", return_value=fake):
        out = sc.get_presentment_currency_setting("x.myshopify.com", "tok", "EUR")
    assert out["found"] is True
    assert out["shop_currency"] == "PLN"
    assert out["manual_rate"] == 0.231
    assert out["enabled"] is True


def test_get_presentment_currency_setting_missing() -> None:
    fake = {
        "shop": {
            "currencyCode": "PLN",
            "currencySettings": {"edges": []},
        },
    }
    with patch.object(sc, "graphql", return_value=fake):
        out = sc.get_presentment_currency_setting("x.myshopify.com", "tok", "EUR")
    assert out["found"] is False
