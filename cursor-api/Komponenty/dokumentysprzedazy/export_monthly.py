"""Eksport miesięczny sprzedaży — CSV."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_bytes, data_path

from .country import is_eu_b2c, is_poland
from .invoice_helpers import is_test_invoice
from .storage import list_invoices

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_EXPORT_DIR = _COMPONENT_DIR / "dane" / "exports"
_EXPORT_DIR = _LEGACY_EXPORT_DIR
_EXPORT_ROOT = data_path(
    "Komponenty/dokumentysprzedazy/dane/exports/.path",
    legacy=_LEGACY_EXPORT_DIR / ".path",
)


def _export_dir() -> Path:
    explicit = Path(_EXPORT_DIR)
    if explicit != _LEGACY_EXPORT_DIR:
        return explicit
    return _EXPORT_ROOT.write_path.parent


def export_month_csv(year: int, month: int) -> Path:
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    summary = {
        "poland": 0.0,
        "foreign": 0.0,
        "eu_b2c": 0.0,
        "non_eu": 0.0,
        "pln_total": 0.0,
        "by_currency": defaultdict(float),
    }

    for inv in list_invoices():
        if is_test_invoice(inv):
            continue
        if inv.status not in ("issued", "corrected"):
            continue
        try:
            sd = datetime.fromisoformat(inv.sale_date[:10])
        except ValueError:
            continue
        if sd.year != year or sd.month != month:
            continue

        country = inv.shipping_address.country_code or inv.buyer.country_code
        pln = inv.exchange.total_amount_pln or (
            inv.order_total if inv.currency.upper() == "PLN" else 0.0
        )
        summary["by_currency"][inv.currency] += inv.order_total
        summary["pln_total"] += pln
        if is_poland(country):
            summary["poland"] += pln
        else:
            summary["foreign"] += pln
            if is_eu_b2c(country):
                summary["eu_b2c"] += pln
            else:
                summary["non_eu"] += pln

        rows.append({
            "sale_date": inv.sale_date,
            "shopify_order": inv.shopify_order_name,
            "invoice_number": inv.invoice_number,
            "country": country,
            "client": inv.buyer.name,
            "email": inv.buyer.email,
            "currency": inv.currency,
            "amount_currency": inv.order_total,
            "shipping": inv.shipping_total,
            "discounts": inv.discounts_total,
            "total": inv.order_total,
            "payment_status": inv.financial_status,
            "refund_status": "",
            "document_language": inv.language,
            "pdf_path": inv.pdf_path,
            "nbp_rate": inv.exchange.exchange_rate_value,
            "nbp_rate_date": inv.exchange.exchange_rate_date,
            "nbp_table": inv.exchange.exchange_rate_table_number,
            "amount_pln": pln,
            "rate_source": inv.exchange.exchange_rate_source,
            "rate_status": inv.exchange.exchange_rate_status,
        })

    out = export_dir / f"sales_{year:04d}_{month:02d}.csv"
    fieldnames = list(rows[0].keys()) if rows else [
        "sale_date", "shopify_order", "invoice_number", "country", "client", "email",
        "currency", "amount_currency", "shipping", "discounts", "total",
        "payment_status", "refund_status", "document_language", "pdf_path",
        "nbp_rate", "nbp_rate_date", "nbp_table", "amount_pln", "rate_source", "rate_status",
    ]
    buffer = io.StringIO(newline="")
    w = csv.DictWriter(buffer, fieldnames=fieldnames)
    w.writeheader()
    for row in rows:
        w.writerow(row)
    w.writerow({})
    w.writerow({"sale_date": "PODSUMOWANIE", "shopify_order": f"Polska: {summary['poland']:.2f} PLN"})
    w.writerow({"shopify_order": f"Zagranica: {summary['foreign']:.2f} PLN"})
    w.writerow({"shopify_order": f"UE B2C: {summary['eu_b2c']:.2f} PLN"})
    w.writerow({"shopify_order": f"Poza UE: {summary['non_eu']:.2f} PLN"})
    w.writerow({"shopify_order": f"Suma PLN: {summary['pln_total']:.2f}"})
    for cur, amt in summary["by_currency"].items():
        w.writerow({"shopify_order": f"Suma {cur}: {amt:.2f}"})
    atomic_write_bytes(out, buffer.getvalue().encode("utf-8-sig"))
    return out
