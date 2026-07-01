"""Etykiety wpisów KPiR — okres DNR vs JDG."""

from __future__ import annotations

from datetime import date

from .models import KpirEntry


def _parse_iso(iso: str) -> date | None:
    try:
        return date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None


def entry_chain_label(entry: KpirEntry, *, jdg_registered_at: str = "") -> str:
    """DNR / JDG dla przychodów; puste dla kosztów i innych."""
    if entry.entry_type != "revenue":
        return ""
    if entry.source == "dnr_import" or entry.dnr_sale_id:
        return "DNR"
    if entry.source == "invoice" or entry.invoice_id:
        return "JDG"
    if entry.source == "shopify":
        reg = _parse_iso(jdg_registered_at)
        ev = _parse_iso(entry.event_date)
        if reg and ev and ev < reg:
            return "DNR"
        return "JDG"
    if entry.source == "correction":
        if entry.dnr_sale_id or "DNR" in (entry.description or "").upper():
            return "DNR"
        return "JDG"
    return ""
