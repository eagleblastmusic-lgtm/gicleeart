"""Mapowanie wpisów KPiR na oficjalny wzór 19 kolumn (Dz.U. 2025 poz. 1299)."""

from __future__ import annotations

from typing import Any

from .constants import OFFICIAL_COLUMN_HEADERS
from .models import KpirEntry, KpirSettings

COLUMN_KEYS = [k for k, _ in OFFICIAL_COLUMN_HEADERS]


def entry_to_official_row(lp: int, entry: KpirEntry, *, settings: KpirSettings | None = None) -> dict[str, Any]:
    """Jedna pozycja księgi — kolumny 1–19."""
    _ = settings
    show_name = not (entry.contractor_nip or "").strip()
    return {
        "lp": lp,
        "event_date": (entry.event_date or "")[:10],
        "ksef_number": entry.ksef_number or "",
        "document_number": entry.document_number or "",
        "contractor_nip": entry.contractor_nip or "",
        "contractor": entry.contractor if show_name else "",
        "contractor_address": entry.contractor_address if show_name else "",
        "description": entry.description or "",
        "revenue_goods": round(entry.revenue_goods, 2),
        "revenue_other": round(entry.revenue_other, 2),
        "total_revenue": entry.total_revenue,
        "purchase_goods": round(entry.purchase_goods, 2),
        "purchase_side": round(entry.purchase_side, 2),
        "wages": round(entry.wages, 2),
        "other_expenses": round(entry.other_expenses, 2),
        "total_expenses": entry.total_expenses,
        "other_events": entry.other_events or "",
        "rd_expenses": round(entry.rd_expenses, 2),
        "notes": entry.notes or "",
    }


def sum_official_columns(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = (
        "revenue_goods", "revenue_other", "total_revenue",
        "purchase_goods", "purchase_side", "wages", "other_expenses",
        "total_expenses", "rd_expenses",
    )
    out = {k: 0.0 for k in keys}
    for row in rows:
        for k in keys:
            out[k] += float(row.get(k) or 0)
    return {k: round(v, 2) for k, v in out.items()}


def monthly_cumulative_rows(
    rows: list[dict[str, Any]],
    *,
    through_month: int,
) -> dict[str, float]:
    """Sumy narastająco od początku roku do końca miesiąca."""
    filtered = []
    for row in rows:
        try:
            m = int(str(row.get("event_date") or "")[5:7])
        except (ValueError, IndexError):
            continue
        if m <= through_month:
            filtered.append(row)
    return sum_official_columns(filtered)
