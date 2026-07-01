"""Operacje na wpisach KPiR — CRUD, księgowanie, historia zmian."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import ChangeLogEntry, KpirEntry
from .storage import (
    append_changelog,
    get_entry,
    list_entries,
    new_changelog_id,
    new_entry_id,
    new_entry_number,
    save_entry,
)
from .validation import ValidationError, validate_entry_edit, validate_revenue_entry


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_entry(**kwargs: Any) -> KpirEntry:
    now = _now()
    try:
        y = int(str(kwargs.get("event_date", ""))[:4])
    except ValueError:
        y = datetime.now().year
    entry = KpirEntry(
        id=new_entry_id(),
        entry_number=new_entry_number(y),
        event_date=kwargs.get("event_date", "") or now[:10],
        document_number=str(kwargs.get("document_number") or ""),
        ksef_number=str(kwargs.get("ksef_number") or ""),
        contractor_nip=str(kwargs.get("contractor_nip") or ""),
        contractor=str(kwargs.get("contractor") or ""),
        contractor_address=str(kwargs.get("contractor_address") or ""),
        description=str(kwargs.get("description") or ""),
        revenue_goods=float(kwargs.get("revenue_goods") or 0),
        revenue_other=float(kwargs.get("revenue_other") or 0),
        purchase_goods=float(kwargs.get("purchase_goods") or 0),
        purchase_side=float(kwargs.get("purchase_side") or 0),
        wages=float(kwargs.get("wages") or 0),
        other_expenses=float(kwargs.get("other_expenses") or 0),
        other_events=str(kwargs.get("other_events") or ""),
        rd_expenses=float(kwargs.get("rd_expenses") or 0),
        notes=str(kwargs.get("notes") or ""),
        source=kwargs.get("source") or "system",
        status=kwargs.get("status") or "draft",
        entry_type=kwargs.get("entry_type") or "revenue",
        original_currency=str(kwargs.get("original_currency") or "PLN"),
        original_amount=float(kwargs.get("original_amount") or 0),
        nbp_rate=float(kwargs.get("nbp_rate") or 1),
        nbp_rate_date=str(kwargs.get("nbp_rate_date") or ""),
        nbp_table_number=str(kwargs.get("nbp_table_number") or ""),
        amount_pln=float(kwargs.get("amount_pln") or 0),
        nbp_status=str(kwargs.get("nbp_status") or "not_needed"),
        country=str(kwargs.get("country") or ""),
        shopify_order_id=int(kwargs.get("shopify_order_id") or 0),
        shopify_order_name=str(kwargs.get("shopify_order_name") or ""),
        invoice_id=str(kwargs.get("invoice_id") or ""),
        dnr_sale_id=str(kwargs.get("dnr_sale_id") or ""),
        dnr_cost_id=str(kwargs.get("dnr_cost_id") or ""),
        cost_id=str(kwargs.get("cost_id") or ""),
        linked_entry_id=str(kwargs.get("linked_entry_id") or ""),
        correction_reason=str(kwargs.get("correction_reason") or ""),
        amount_before_correction=float(kwargs.get("amount_before_correction") or 0),
        correction_amount=float(kwargs.get("correction_amount") or 0),
        amount_after_correction=float(kwargs.get("amount_after_correction") or 0),
        category=str(kwargs.get("category") or ""),
        inventory_id=str(kwargs.get("inventory_id") or ""),
        fixed_asset_id=str(kwargs.get("fixed_asset_id") or ""),
        attachments=list(kwargs.get("attachments") or []),
        created_at=now,
        updated_at=now,
    )
    if entry.amount_pln <= 0:
        entry.amount_pln = entry.total_revenue or entry.total_costs
    save_entry(entry)
    return entry


def update_entry(entry: KpirEntry, *, reason: str = "") -> KpirEntry:
    old = get_entry(entry.id)
    if old and old.status == "posted":
        validate_entry_edit(entry)
        _log_changes(old, entry, reason)
    entry.updated_at = _now()
    save_entry(entry)
    return entry


def post_entry(entry: KpirEntry) -> KpirEntry:
    if entry.entry_type == "revenue":
        validate_revenue_entry(entry)
    entry.status = "posted"
    entry.updated_at = _now()
    save_entry(entry)
    return entry


def cancel_entry(entry_id: str) -> KpirEntry:
    entry = get_entry(entry_id)
    if not entry:
        raise ValidationError("Nie znaleziono wpisu.")
    validate_entry_edit(entry)
    entry.status = "cancelled"
    entry.updated_at = _now()
    save_entry(entry)
    return entry


def filter_entries(
    *,
    year: int | None = None,
    month: int | None = None,
    entry_type: str | None = None,
    source: str | None = None,
    contractor: str | None = None,
    category: str | None = None,
    currency: str | None = None,
    country: str | None = None,
    status: str | None = None,
    query: str | None = None,
) -> list[KpirEntry]:
    out: list[KpirEntry] = []
    q = (query or "").strip().lower()
    for e in list_entries():
        if status and e.status != status:
            continue
        if entry_type and e.entry_type != entry_type:
            continue
        if source and e.source != source:
            continue
        if contractor and contractor.lower() not in (e.contractor or "").lower():
            continue
        if category and category.lower() not in (e.category or "").lower():
            continue
        if currency and (e.original_currency or "PLN").upper() != currency.upper():
            continue
        if country and (e.country or "").upper() != country.upper():
            continue
        if q:
            hay = " ".join([
                e.entry_number, e.document_number, e.contractor or "",
                e.description or "", e.shopify_order_name or "",
                e.invoice_id or "", e.notes or "", e.category or "",
            ]).lower()
            if q not in hay:
                continue
        if e.event_date:
            try:
                y = int(e.event_date[:4])
                m = int(e.event_date[5:7])
            except ValueError:
                continue
            if year and y != year:
                continue
            if month and m != month:
                continue
        out.append(e)
    return sorted(out, key=lambda x: (x.event_date, x.entry_number))


def _log_changes(old: KpirEntry, new: KpirEntry, reason: str) -> None:
    fields = [
        "event_date", "document_number", "contractor", "description",
        "revenue_goods", "revenue_other", "purchase_goods", "purchase_side",
        "wages", "other_expenses", "amount_pln", "status", "notes",
    ]
    now = _now()
    for fname in fields:
        old_v = str(getattr(old, fname, ""))
        new_v = str(getattr(new, fname, ""))
        if old_v != new_v:
            append_changelog(ChangeLogEntry(
                id=new_changelog_id(),
                entry_id=new.id,
                field_name=fname,
                old_value=old_v,
                new_value=new_v,
                changed_at=now,
                reason=reason,
            ))
