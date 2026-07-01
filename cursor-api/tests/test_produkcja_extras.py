"""Testy linkow Shopify, statystyk i eksportu etykiet."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.produkcja.label_html import write_workshop_labels_html  # noqa: E402
from Komponenty.produkcja.shopify_links import admin_order_url  # noqa: E402
from Komponenty.produkcja.stats import compute_stats  # noqa: E402


class TestAdminOrderUrl:
    def test_builds_url(self) -> None:
        u = admin_order_url("moj-sklep.myshopify.com", 12345)
        assert "admin.shopify.com" in u
        assert "moj-sklep" in u
        assert "12345" in u


class TestComputeStats:
    def test_empty(self) -> None:
        s = compute_stats([])
        assert s["total"] == 0
        assert s["active"] == 0

    def test_one_active(self) -> None:
        s = compute_stats(
            [
                {
                    "wyslane": False,
                    "data_zamowienia": "2026-04-20",
                    "wydruk_step": 0,
                    "ramka_step": 0,
                }
            ]
        )
        assert s["active"] == 1
        assert s["done"] == 0


class TestLabelHtml:
    def test_writes_file(self, tmp_path: Path) -> None:
        p = tmp_path / "x.html"
        write_workshop_labels_html(
            p,
            [
                {
                    "id": "ORD-0001",
                    "client": "Jan",
                    "tytul_obrazu": "Test",
                    "ramka_drewno": "Dąb",
                    "ramka_rozmiar": "50x70",
                    "ramka_kolor": "Czarny",
                    "ilosc": 1,
                    "shopify_order_no": "#1",
                }
            ],
        )
        t = p.read_text(encoding="utf-8")
        assert "ORD-0001" in t
        assert "50x70" in t
