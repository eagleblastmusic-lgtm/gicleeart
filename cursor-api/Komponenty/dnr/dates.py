"""Pomocnicze daty/kwartały dla modułu DNR."""

from __future__ import annotations

from datetime import date


def quarter_from_month(month: int) -> int:
    return (month - 1) // 3 + 1


def quarter_from_iso(iso: str) -> int:
    try:
        month = int(iso[5:7])
    except (TypeError, ValueError):
        month = date.today().month
    return quarter_from_month(month)
