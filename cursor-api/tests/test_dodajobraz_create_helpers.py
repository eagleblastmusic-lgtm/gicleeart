"""Testy kluczy wariantow i sortowania cen (create.py)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestVariantKeyFromRest:
    def test_three_options(self) -> None:
        from Komponenty.dodajobraz.create import _variant_key_from_rest

        v = {"option1": "Dab", "option2": "50x70", "option3": "Czarny", "id": 1}
        assert _variant_key_from_rest(v) == ("Dab", "50x70", "Czarny")

    def test_skips_empty(self) -> None:
        from Komponenty.dodajobraz.create import _variant_key_from_rest

        v = {"option1": "  X ", "option2": None, "option3": "Y"}
        assert _variant_key_from_rest(v) == ("X", "Y")


class TestPriceSortKey:
    def test_numeric_order(self) -> None:
        from Komponenty.dodajobraz.create import _price_sort_key

        prices = ["10.00", "2.50", "9.00"]
        sorted_p = sorted(prices, key=lambda p: _price_sort_key(p))
        assert sorted_p == ["2.50", "9.00", "10.00"]

    def test_comma_decimal(self) -> None:
        from Komponenty.dodajobraz.create import _price_sort_key

        assert _price_sort_key("3,5")[0] == 0
