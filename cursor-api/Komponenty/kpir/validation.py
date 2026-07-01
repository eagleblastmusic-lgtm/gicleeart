"""Walidacje wpisów KPiR."""

from __future__ import annotations

from .models import CostRecord, KpirEntry
from .storage import is_month_closed, posted_entry_for_dnr_cost, posted_entry_for_dnr_sale, posted_entry_for_invoice, posted_entry_for_order


class ValidationError(Exception):
    pass


def validate_revenue_entry(entry: KpirEntry) -> None:
    if not entry.event_date:
        raise ValidationError("Nie można zaksięgować przychodu bez daty.")
    if entry.amount_pln <= 0 and entry.total_revenue <= 0:
        raise ValidationError("Nie można zaksięgować przychodu bez kwoty PLN.")
    cur = (entry.original_currency or "PLN").upper()
    if cur != "PLN" and entry.nbp_status in ("missing", "error") and entry.nbp_rate <= 0:
        raise ValidationError("Nie można zaksięgować waluty obcej bez kursu NBP lub ręcznego kursu.")
    if entry.shopify_order_id:
        existing = posted_entry_for_order(entry.shopify_order_id)
        if existing and existing.id != entry.id:
            raise ValidationError(
                f"Zamówienie {entry.shopify_order_name} jest już ujęte w KPiR ({existing.entry_number}).",
            )
    if entry.invoice_id:
        existing = posted_entry_for_invoice(entry.invoice_id)
        if existing and existing.id != entry.id:
            raise ValidationError("Ta faktura jest już ujęta w KPiR.")
    if entry.dnr_sale_id:
        existing = posted_entry_for_dnr_sale(entry.dnr_sale_id)
        if existing and existing.id != entry.id:
            raise ValidationError("Ten wpis DNR jest już ujęty w KPiR.")
    _check_month_open(entry.event_date)


def validate_cost_entry(entry: KpirEntry, cost: CostRecord | None = None) -> None:
    if cost and not cost.document_number and not cost.is_internal_doc:
        raise ValidationError(
            "Nie można zaksięgować kosztu bez numeru dokumentu "
            "(oznacz jako dokument wewnętrzny, jeśli brak numeru).",
        )
    if not entry.event_date:
        raise ValidationError("Nie można zaksięgować kosztu bez daty.")
    cur = (entry.original_currency or "PLN").upper()
    if cur != "PLN" and entry.nbp_status in ("missing", "error") and entry.nbp_rate <= 0:
        raise ValidationError("Nie można zaksięgować waluty obcej bez kursu NBP.")
    if entry.dnr_cost_id:
        existing = posted_entry_for_dnr_cost(entry.dnr_cost_id)
        if existing and existing.id != entry.id:
            raise ValidationError("Ten koszt DNR jest już ujęty w KPiR.")
    _check_month_open(entry.event_date)


def validate_entry_edit(entry: KpirEntry) -> None:
    _check_month_open(entry.event_date)


def _check_month_open(event_date: str) -> None:
    if not event_date or len(event_date) < 7:
        return
    try:
        y = int(event_date[:4])
        m = int(event_date[5:7])
    except ValueError:
        return
    if is_month_closed(y, m):
        raise ValidationError(
            f"Miesiąc {y}-{m:02d} jest zamknięty. Otwórz miesiąc ponownie, aby edytować wpisy.",
        )
