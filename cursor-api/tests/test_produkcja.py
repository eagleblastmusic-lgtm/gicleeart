"""Testy kluczowych funkcji komponentu Produkcja (countdown, status, detekcja ramek)."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Komponenty.produkcja.view import (  # noqa: E402
    _cure_remaining_seconds,
    _cure_remaining_seconds_raw,
    _cure_progress_fraction,
    _cure_color,
    _format_countdown,
    _is_overdue,
    _profit_summary,
    _progress_steps,
    _wydruk_ready,
    _ramka_ready,
)
from Komponenty.produkcja.frame_variant import parse_shopify_variant_title  # noqa: E402
from Komponenty.produkcja.orders_sync import _detect_frame_variant  # noqa: E402
from Komponenty.produkcja.shipping import is_poland, pick_carrier_url  # noqa: E402


class TestCountdownLogic:
    def test_no_start_date_returns_zero(self) -> None:
        assert _cure_remaining_seconds({}) == 0

    def test_fresh_paint_returns_72h(self) -> None:
        now = datetime.now()
        order = {"data_pomalowania": now.isoformat()}
        remaining = _cure_remaining_seconds(order)
        # 72h = 259200s, tolerancja 2s na czas testu
        assert 259198 <= remaining <= 259200

    def test_pomin_schniecie_forces_done(self) -> None:
        now = datetime.now()
        order = {"data_pomalowania": now.isoformat(), "pomin_schniecie": True}
        assert _cure_remaining_seconds(order) == 0
        assert _cure_progress_fraction(order) == 1.0
        assert _cure_remaining_seconds_raw(order) >= 259198

    def test_raw_without_pomin_matches_effective(self) -> None:
        now = datetime.now()
        order = {"data_pomalowania": now.isoformat()}
        assert _cure_remaining_seconds(order) == _cure_remaining_seconds_raw(order)

    def test_24h_ago_returns_48h(self) -> None:
        past = (datetime.now() - timedelta(hours=24)).isoformat()
        order = {"data_pomalowania": past}
        remaining = _cure_remaining_seconds(order)
        assert 48 * 3600 - 5 <= remaining <= 48 * 3600 + 5

    def test_72h_ago_returns_zero(self) -> None:
        past = (datetime.now() - timedelta(hours=72, minutes=1)).isoformat()
        order = {"data_pomalowania": past}
        assert _cure_remaining_seconds(order) == 0

    def test_progress_fraction(self) -> None:
        past = (datetime.now() - timedelta(hours=36)).isoformat()
        order = {"data_pomalowania": past}
        frac = _cure_progress_fraction(order)
        assert 0.49 < frac < 0.51  # 36h z 72h = 50%

    def test_color_red_below_24h(self) -> None:
        past = (datetime.now() - timedelta(hours=50)).isoformat()  # 22h zostało
        order = {"data_pomalowania": past}
        assert _cure_color(order) == "#c62828"

    def test_color_green_above_48h(self) -> None:
        past = (datetime.now() - timedelta(hours=5)).isoformat()  # 67h zostało
        order = {"data_pomalowania": past}
        assert _cure_color(order) == "#43a047"

    def test_color_green_when_done(self) -> None:
        past = (datetime.now() - timedelta(hours=100)).isoformat()
        order = {"data_pomalowania": past}
        assert _cure_color(order) == "#2e7d32"


class TestFormatCountdown:
    def test_days_hours_minutes_seconds(self) -> None:
        s = _format_countdown(2 * 86400 + 5 * 3600 + 43 * 60 + 12)
        assert s == "2d 05g 43m 12s"

    def test_less_than_day(self) -> None:
        s = _format_countdown(5 * 3600 + 43 * 60 + 12)
        assert s == "05g 43m 12s"

    def test_less_than_hour(self) -> None:
        s = _format_countdown(43 * 60 + 12)
        assert s == "43m 12s"

    def test_less_than_minute(self) -> None:
        assert _format_countdown(42) == "42s"

    def test_zero(self) -> None:
        assert _format_countdown(0) == "0s"


class TestOverdue:
    def test_wyslane_never_overdue(self) -> None:
        assert not _is_overdue({"wyslane": True, "data_zamowienia": "2020-01-01"})

    def test_recent_not_overdue(self) -> None:
        today_iso = datetime.now().date().isoformat()
        assert not _is_overdue({"wyslane": False, "data_zamowienia": today_iso})

    def test_old_is_overdue(self) -> None:
        from datetime import date
        old = (date.today() - timedelta(days=20)).isoformat()
        assert _is_overdue({"wyslane": False, "data_zamowienia": old})


class TestProgressSteps:
    def test_fresh_order_zero_progress(self) -> None:
        assert _progress_steps({})[0] == 0

    def test_all_done(self) -> None:
        past = (datetime.now() - timedelta(hours=100)).isoformat()
        order = {
            "wydruk_step": 2,
            "ramka_step": 4,
            "data_pomalowania": past,
            "zlozone": True,
            "spakowane": True,
            "wyslane": True,
        }
        done, total = _progress_steps(order)
        assert total == 5
        assert done == 5

    def test_wydruk_ready(self) -> None:
        assert _wydruk_ready({"wydruk_step": 2})
        assert not _wydruk_ready({"wydruk_step": 1})

    def test_ramka_ready_only_after_cure(self) -> None:
        recent = datetime.now().isoformat()
        old = (datetime.now() - timedelta(hours=100)).isoformat()
        assert not _ramka_ready({"ramka_step": 4, "data_pomalowania": recent})
        assert _ramka_ready({"ramka_step": 4, "data_pomalowania": old})
        assert _ramka_ready(
            {"ramka_step": 4, "data_pomalowania": recent, "pomin_schniecie": True}
        )


class TestProfitSummary:
    def test_empty_order_no_crash(self) -> None:
        s = _profit_summary({})
        assert s["sprzedaz"] == 0
        assert s["marza"] == 0
        assert s["marza_pct"] == 0

    def test_positive_margin(self) -> None:
        order = {
            "cena_sprzedazy": 200.0,
            "koszt_plotno": 20.0,
            "koszt_wydruku": 40.0,
            "koszt_drewna": 30.0,
        }
        s = _profit_summary(order)
        assert s["sprzedaz"] == 200.0
        assert s["koszty"] == 90.0
        assert s["marza"] == 110.0
        assert abs(s["marza_pct"] - 55.0) < 0.01

    def test_negative_margin(self) -> None:
        order = {
            "cena_sprzedazy": 50.0,
            "koszt_plotno": 100.0,
        }
        s = _profit_summary(order)
        assert s["marza"] == -50.0

    def test_string_values_handled(self) -> None:
        order = {"cena_sprzedazy": "100", "koszt_plotno": "25"}
        s = _profit_summary(order)
        assert s["marza"] == 75.0


class TestFrameDetection:
    def test_dab_xl(self) -> None:
        assert _detect_frame_variant("Dąb / XL") == "Dab XL"

    def test_sosna_m(self) -> None:
        assert _detect_frame_variant("Sosna / M") == "Sosna M"
        assert _detect_frame_variant("Sosna / S") == "Sosna M"

    def test_unknown_fallback(self) -> None:
        assert _detect_frame_variant("") == "Dab M"
        assert _detect_frame_variant("Plastic / Medium") == "Dab M"


class TestShopifyVariantParts:
    def test_three_options_like_store(self) -> None:
        d, r, k = parse_shopify_variant_title("Dąb / 50x70 / Czarny mat")
        assert d == "Dąb"
        assert r == "50x70"
        assert k == "Czarny mat"

    def test_wood_only_label(self) -> None:
        d, r, k = parse_shopify_variant_title("Dąb")
        assert d == "Dąb"
        assert r == ""
        assert k == ""


class TestShippingCarrierPicker:
    def test_pl_postcode_is_poland(self) -> None:
        assert is_poland("Jan Kowalski\nul. Testowa 5\n00-001 Warszawa")

    def test_polska_word(self) -> None:
        assert is_poland("Jan Kowalski\nWarszawa, Polska")

    def test_germany_not_poland(self) -> None:
        assert not is_poland("Max Muster\nTestallee 5\n10115 Berlin\nGermany")

    def test_picker_returns_furgonetka_for_pl(self) -> None:
        url, name = pick_carrier_url({"adres_wysylki": "00-001 Warszawa, Polska"})
        assert "furgonetka" in url.lower()
        assert name == "Furgonetka.pl"

    def test_picker_returns_przesylarka_for_de(self) -> None:
        url, name = pick_carrier_url({"adres_wysylki": "10115 Berlin, Germany"})
        assert "przesylarka" in url.lower()
        assert name == "Przesylarka.pl"
