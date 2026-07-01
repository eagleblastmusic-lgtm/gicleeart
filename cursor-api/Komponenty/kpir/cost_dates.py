"""Daty zdarzeń gospodarczych — memoriał vs kasa (§ 6, objaśnienia załącznika)."""

from __future__ import annotations

from .models import CostRecord, KpirSettings
from .storage import load_settings


def resolve_cost_event_date(cost: CostRecord, settings: KpirSettings | None = None) -> str:
    """Data wpisu w kolumnie 2 dla kosztu."""
    settings = settings or load_settings()
    if settings.cost_method == "cash":
        if cost.payment_date:
            return cost.payment_date[:10]
        if cost.is_paid and cost.issue_date:
            return cost.issue_date[:10]
        return (cost.event_date or cost.issue_date or "")[:10]
    if cost.liability_unpaid:
        return (cost.payment_date or cost.event_date or cost.issue_date or "")[:10]
    return (cost.event_date or cost.issue_date or "")[:10]
