"""Testy liczenia cen rynkowych z uwzglednieniem kursu walut."""

from __future__ import annotations

import sys
from pathlib import Path

# Zeby import z cursor-api/Komponenty dzialal niezaleznie od cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.dodajobraz.markets import compute_market_price  # noqa: E402


class TestComputeMarketPrice:
    """Testuje compute_market_price w roznych scenariuszach."""

    def test_pln_no_markup(self) -> None:
        # 100 zl * (1 + 0%) = 100 zl
        assert compute_market_price(100.0, 0.0, currency="PLN") == 100.0

    def test_pln_with_markup(self) -> None:
        # 100 zl * (1 + 15%) = 115 zl
        assert compute_market_price(100.0, 15.0, currency="PLN") == 115.0

    def test_eur_with_rate_and_markup(self) -> None:
        # 431 PLN / 4.31 * (1 + 10%) = 110 EUR
        result = compute_market_price(431.0, 10.0, currency="EUR", fx_rate=4.31)
        assert result == 110.0

    def test_eur_no_markup(self) -> None:
        # 431 PLN / 4.31 = 100 EUR
        result = compute_market_price(431.0, 0.0, currency="EUR", fx_rate=4.31)
        assert result == 100.0

    def test_eur_no_rate_fallback_to_raw(self) -> None:
        # Brak kursu -> fallback (nie crash)
        result = compute_market_price(100.0, 15.0, currency="EUR", fx_rate=None)
        assert result == 115.0

    def test_eur_zero_rate_fallback(self) -> None:
        result = compute_market_price(100.0, 15.0, currency="EUR", fx_rate=0)
        assert result == 115.0

    def test_rounding_to_2_decimals(self) -> None:
        # 10.005 -> 10.01 lub 10.00 (zaleznie od mode) - testujemy ze jest 2-dec
        result = compute_market_price(10.005, 0.0, currency="PLN")
        assert len(str(result).split(".")[1]) <= 2

    def test_negative_markup(self) -> None:
        # Ujemny markup (discount)
        assert compute_market_price(100.0, -10.0, currency="PLN") == 90.0
