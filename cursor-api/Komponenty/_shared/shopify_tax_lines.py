"""Zaokrąglanie VAT na poziomie linii — zgodnie z logiką Shopify Tax."""

from __future__ import annotations

from typing import Any

from Komponenty._shared.tax_config import default_vat_rate_pl


def _line_vat_rate_percent(line_item: dict[str, Any], *, fallback: float) -> float:
    rates: list[float] = []
    for tl in line_item.get("tax_lines") or []:
        try:
            r = float(tl.get("rate") or 0)
        except (TypeError, ValueError):
            continue
        if r > 0:
            rates.append(r * 100 if r <= 1 else r)
    if rates:
        return round(max(rates), 4)
    return fallback


def line_amounts(
    line_item: dict[str, Any],
    *,
    taxes_included: bool,
    vat_rate_fallback: float | None = None,
) -> dict[str, float]:
    """Zwraca net, tax, gross (po rabacie na linii), discount."""
    qty = float(line_item.get("quantity") or 0)
    price = float(line_item.get("price") or 0)
    discount = round(float(line_item.get("total_discount") or 0), 2)
    rate = _line_vat_rate_percent(line_item, fallback=vat_rate_fallback or default_vat_rate_pl())
    gross_after_discount = round(qty * price - discount, 2)
    if rate <= 0:
        return {
            "net": gross_after_discount,
            "tax": 0.0,
            "gross": gross_after_discount,
            "discount": discount,
            "vat_rate": 0.0,
        }
    if taxes_included:
        tax = round(gross_after_discount * rate / (100 + rate), 2)
        net = round(gross_after_discount - tax, 2)
        gross = gross_after_discount
    else:
        net = gross_after_discount
        tax = round(net * rate / 100, 2)
        gross = round(net + tax, 2)
    return {
        "net": net,
        "tax": tax,
        "gross": gross,
        "discount": discount,
        "vat_rate": rate,
    }


def order_line_totals(
    order: dict[str, Any],
    *,
    vat_rate_fallback: float | None = None,
) -> dict[str, Any]:
    """Sumuje linie z zaokrągleniem per pozycja."""
    taxes_included = bool(order.get("taxes_included"))
    lines: list[dict[str, Any]] = []
    net_total = tax_total = gross_total = discount_total = 0.0
    for li in order.get("line_items") or []:
        row = line_amounts(li, taxes_included=taxes_included, vat_rate_fallback=vat_rate_fallback)
        lines.append(row)
        net_total += row["net"]
        tax_total += row["tax"]
        gross_total += row["gross"]
        discount_total += row["discount"]
    ship_set = order.get("total_shipping_price_set") or {}
    ship_amt = float((ship_set.get("shop_money") or {}).get("amount") or 0)
    if ship_amt > 0:
        gross_total += ship_amt
        if taxes_included and tax_total > 0 and net_total > 0:
            avg_rate = tax_total / net_total * 100 if net_total else 0
            if avg_rate > 0:
                stax = round(ship_amt * avg_rate / (100 + avg_rate), 2)
                tax_total += stax
                net_total += round(ship_amt - stax, 2)
            else:
                net_total += ship_amt
        else:
            net_total += ship_amt
    return {
        "taxes_included": taxes_included,
        "lines": lines,
        "net_total": round(net_total, 2),
        "tax_total": round(tax_total, 2),
        "gross_total": round(gross_total, 2),
        "discount_total": round(discount_total, 2),
        "order_tax_reported": round(float(order.get("total_tax") or 0), 2),
    }
