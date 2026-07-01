"""Śledzenie limitu DNR — delegacja do ewidencji modułu `dnr` (jeden licznik)."""

from __future__ import annotations

from typing import Any

from Komponenty.dnr.constants import CEIDG_WARNING, QUARTER_LABELS
from Komponenty.dnr.limit_sync import canonical_quarterly_limit
from Komponenty.dnr.migration_service import migration_overview
from Komponenty.dnr.summary_service import limit_status


def dnr_status(year: int | None = None, quarter: int | None = None) -> dict[str, Any]:
    """Status limitu DNR z ewidencji `Komponenty.dnr` (nie z wpisów KPiR)."""
    status = limit_status(year, quarter)
    mig = migration_overview()
    level = str(status.get("level") or "ok")
    kpir_level = {
        "ok": "ok",
        "caution": "warning",
        "warn": "critical",
        "over": "exceeded",
        "obligation": "obligation",
    }.get(level, "ok")
    message = str(status.get("message") or "")
    if mig.get("wizard_needed") and level == "ok" and not status.get("jdg_obligation"):
        message += " Otwórz moduł DNR — wymagana migracja DNR → JDG."
    return {
        "year": status["year"],
        "quarter": status["quarter"],
        "quarter_label": status.get("quarter_label") or QUARTER_LABELS.get(status["quarter"], "?"),
        "revenue": status["quarter_revenue"],
        "limit": status["quarterly_limit"],
        "remaining": status["remaining"],
        "used_percent": status["pct"],
        "level": kpir_level,
        "message": message,
        "ceidg_warning": status.get("ceidg_warning") or "",
        "over_limit": status.get("over_limit"),
        "obligation_active": status.get("obligation_active"),
        "jdg_obligation": status.get("jdg_obligation"),
        "wizard_needed": mig.get("wizard_needed"),
        "manual_review_alert": mig.get("manual_review_alert"),
        "source": "dnr_ledger",
        "canonical_limit": canonical_quarterly_limit(),
    }
