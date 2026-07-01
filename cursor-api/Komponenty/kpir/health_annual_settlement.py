"""Roczne rozliczenie składki zdrowotnej (DRA/RCA — termin maj)."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.tax_config import health_annual_settlement_month

from .pit_calculator import estimate_pit
from .storage import load_settings


def health_annual_settlement(year: int | None = None) -> dict[str, Any]:
    """Porównanie składki zdrowotnej wpłaconej miesięcznie z wyliczeniem rocznym."""
    y = year or date.today().year
    settings = load_settings()
    est = estimate_pit(y, settings)
    paid_monthly = float(settings.health_insurance_monthly or 0)
    months = 12
    paid_total = round(paid_monthly * months, 2)
    calculated_annual = round(float(est.get("health_calculated") or 0), 2)
    used_in_pit = round(float(est.get("health_annual") or 0), 2)
    diff = round(calculated_annual - paid_total, 2)
    settle_month = health_annual_settlement_month()
    due_year = y + 1
    due_date = date(due_year, settle_month, 20).isoformat()
    today = date.today()
    if diff > 1.0:
        level = "underpaid"
        message = (
            f"Roczne rozliczenie zdrowotnej za {y}: niedopłata ok. {diff:,.2f} zł "
            f"(wpłacono {paid_total:,.2f} zł, wyliczono {calculated_annual:,.2f} zł). "
            f"Ujęcie w ZUS DRA/RCA do {due_date}."
        )
    elif diff < -1.0:
        level = "overpaid"
        message = (
            f"Roczne rozliczenie zdrowotnej za {y}: nadpłata ok. {abs(diff):,.2f} zł. "
            f"Ujęcie w ZUS DRA/RCA do {due_date}."
        )
    else:
        level = "ok"
        message = f"Roczne rozliczenie zdrowotnej za {y}: wpłaty zgodne z wyliczeniem ({paid_total:,.2f} zł)."
    return {
        "year": y,
        "paid_monthly": paid_monthly,
        "paid_annual": paid_total,
        "calculated_annual": calculated_annual,
        "used_in_pit": used_in_pit,
        "difference_pln": diff,
        "due_date": due_date,
        "due_month": settle_month,
        "level": level,
        "message": message,
        "form": "ZUS DRA / ZUS RCA",
    }
