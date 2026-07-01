"""Weryfikacja przykładów z briefu — python -m Komponenty.passepartout.verify_examples"""

from __future__ import annotations

import sys

from .calculations import (
    CalculationInput,
    SavedLineItem,
    StripeLayout,
    calculate_order_result,
    calculate_single_piece_metrics,
    calculate_total_units,
    combine_saved_lines,
)


def _check(label: str, actual: float, expected: float, tol: float = 0.02) -> None:
    ok = abs(actual - expected) <= tol
    status = "OK" if ok else "FAIL"
    print(f"{status} {label}: {actual} (oczekiwano {expected})")
    if not ok:
        sys.exit(1)


def main() -> None:
    base = CalculationInput(
        outer_width_cm=30,
        outer_height_cm=40,
        window_width_cm=20,
        window_height_cm=28.7,
        quantity=1,
        price_per_m2=100,
        unit_price=2.5,
        free_shipping_threshold=49.9,
        shipping_cost=14.99,
        rounding_mode="per_piece",
    )

    print("--- Przykład 1: A4, 1 sztuka ---")
    m1 = calculate_single_piece_metrics(base)
    _check("powierzchnia", m1.area_m2, 0.12)
    _check("realna cena", m1.real_price, 12)
    _check("jednostki przed zaokr.", m1.units_raw, 4.8)
    _check("jednostki po zaokr. osobno", float(m1.units_rounded_per_piece), 5)
    o1 = calculate_order_result(base)
    _check("cena bez dostawy", o1.price_without_shipping, 12.5)
    _check("strata na zaokrągleniu", o1.rounding_loss, 0.5)

    print("\n--- Przykład 2: A4, 5 sztuk ---")
    per5 = calculate_order_result(
        CalculationInput(**{**base.__dict__, "quantity": 5, "rounding_mode": "per_piece"})
    )
    _check("osobno: jednostki", float(per5.units_total), 25)
    _check("osobno: cena bez dostawy", per5.price_without_shipping, 62.5)
    _check("osobno: strata", per5.rounding_loss, 2.5)

    batch5 = calculate_order_result(
        CalculationInput(**{**base.__dict__, "quantity": 5, "rounding_mode": "batch"})
    )
    _check("razem: jednostki", float(batch5.units_total), 24)
    _check("razem: cena bez dostawy", batch5.price_without_shipping, 60)
    _check("razem: strata", batch5.rounding_loss, 0)

    print("\n--- Przykład 3: A3+, 1 sztuka ---")
    a3 = CalculationInput(
        **{
            **base.__dict__,
            "outer_width_cm": 47,
            "outer_height_cm": 62,
            "window_width_cm": 31.9,
            "window_height_cm": 47.3,
        }
    )
    m3 = calculate_single_piece_metrics(a3)
    _check("powierzchnia", m3.area_m2, 0.2914, 0.0001)
    _check("realna cena", m3.real_price, 29.14, 0.01)
    _check("jednostki przed zaokr.", m3.units_raw, 11.656, 0.001)
    _check("jednostki po zaokr. osobno", float(m3.units_rounded_per_piece), 12)
    o3 = calculate_order_result(a3)
    _check("cena bez dostawy", o3.price_without_shipping, 30)
    _check("strata na zaokrągleniu", o3.rounding_loss, 0.86, 0.01)

    print("\n--- Sanity: tryby zaokrąglania A4 x5 ---")
    _check("per_piece units", float(calculate_total_units(m1.units_raw, 5, "per_piece")), 25)
    _check("batch units", float(calculate_total_units(m1.units_raw, 5, "batch")), 24)

    print("\n--- Łączenie pozycji: batch A4, 3+3 vs 6 ---")
    batch_base = {**base.__dict__, "rounding_mode": "batch"}
    line3a = CalculationInput(**{**batch_base, "quantity": 3})
    line3b = CalculationInput(**{**batch_base, "quantity": 3})
    line6 = CalculationInput(**{**batch_base, "quantity": 6})
    saved_split = [
        SavedLineItem(line3a, "horizontal"),
        SavedLineItem(line3b, "horizontal"),
    ]
    combined_split = combine_saved_lines(
        saved_split,
        free_shipping_threshold=base.free_shipping_threshold,
        shipping_cost=base.shipping_cost,
    )
    single6 = calculate_order_result(line6)
    assert combined_split is not None
    _check("batch split units", float(combined_split.total_units), float(single6.units_total))
    _check("batch split cena", combined_split.price_without_shipping, single6.price_without_shipping)

    print("\n--- Łączenie pozycji: per_piece A4, 3+3 vs 6 ---")
    per_base = {**base.__dict__, "rounding_mode": "per_piece"}
    saved_per = [
        SavedLineItem(CalculationInput(**{**per_base, "quantity": 3}), "horizontal"),
        SavedLineItem(CalculationInput(**{**per_base, "quantity": 3}), "vertical"),
    ]
    combined_per = combine_saved_lines(
        saved_per,
        free_shipping_threshold=base.free_shipping_threshold,
        shipping_cost=base.shipping_cost,
    )
    single6_per = calculate_order_result(CalculationInput(**{**per_base, "quantity": 6}))
    assert combined_per is not None
    _check("per_piece split units", float(combined_per.total_units), float(single6_per.units_total))
    _check("per_piece split cena", combined_per.price_without_shipping, single6_per.price_without_shipping)

    print("\nWszystkie przykłady poprawne.")


if __name__ == "__main__":
    main()
