"""Spis z natury — § 20–22 rozporządzenia Dz.U. 2025 poz. 1299."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .entry_service import create_entry, post_entry
from .models import InventoryLine, InventoryRecord
from .storage import (
    get_inventory,
    list_inventories,
    new_inventory_id,
    save_inventory,
)
from .validation import ValidationError


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _line_value(line: InventoryLine, markup_pct: float = 0.0) -> float:
    if line.is_foreign_goods:
        return 0.0
    method = line.valuation_method or "purchase_price"
    if method == "production_cost":
        if line.value > 0:
            return round(line.value, 2)
        return round(line.quantity * line.unit_price, 2)
    if method == "scrap_estimate":
        return round(line.value if line.value > 0 else line.quantity * line.unit_price, 2)
    base_price = line.unit_price
    if method == "purchase_price" and markup_pct > 0:
        base_price = round(base_price * (1.0 + markup_pct), 4)
    if line.value > 0 and method != "purchase_price":
        return round(line.value, 2)
    return round(line.quantity * base_price, 2)


def _recalc_total(record: InventoryRecord) -> InventoryRecord:
    total = 0.0
    markup = float(record.side_cost_markup_pct or 0)
    for i, line in enumerate(record.lines, 1):
        line.line_no = i
        line.value = _line_value(line, markup_pct=markup)
        total += line.value
    record.total_value = round(total, 2)
    return record


def create_inventory(
    inventory_date: str,
    kind: str,
    *,
    lines: list[dict[str, Any]] | None = None,
    notes: str = "",
) -> InventoryRecord:
    now = _now()
    inv_lines = []
    for i, raw in enumerate(lines or [], 1):
        inv_lines.append(InventoryLine(
            line_no=i,
            name=str(raw.get("name") or ""),
            unit=str(raw.get("unit") or "szt."),
            quantity=float(raw.get("quantity") or 0),
            unit_price=float(raw.get("unit_price") or 0),
            value=float(raw.get("value") or 0),
            is_foreign_goods=bool(raw.get("is_foreign_goods")),
            owner_note=str(raw.get("owner_note") or ""),
            valuation_method=str(raw.get("valuation_method") or "purchase_price"),
        ))
    record = InventoryRecord(
        id=new_inventory_id(),
        inventory_date=inventory_date[:10],
        kind=kind,  # type: ignore[arg-type]
        lines=inv_lines,
        notes=notes,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    record = _recalc_total(record)
    save_inventory(record)
    return record


def create_zero_inventory(inventory_date: str, kind: str, *, notes: str = "") -> InventoryRecord:
    return create_inventory(inventory_date, kind, lines=[], notes=notes or "Spis zerowy — brak towarów na stanie")


def update_inventory(record: InventoryRecord) -> InventoryRecord:
    record = _recalc_total(record)
    record.updated_at = _now()
    save_inventory(record)
    return record


def complete_valuation(inventory_id: str) -> InventoryRecord:
    record = get_inventory(inventory_id)
    if not record:
        raise ValidationError("Nie znaleziono spisu z natury.")
    record = _recalc_total(record)
    record.valuation_completed_at = _now()
    record.status = "valued"
    record.updated_at = _now()
    save_inventory(record)
    return record


def valuation_deadline(inventory_date: str) -> str:
    try:
        start = datetime.fromisoformat(inventory_date[:10])
    except ValueError:
        return ""
    return (start + timedelta(days=14)).date().isoformat()


def book_inventory_to_kpir(inventory_id: str) -> tuple[InventoryRecord, Any]:
    record = get_inventory(inventory_id)
    if not record:
        raise ValidationError("Nie znaleziono spisu z natury.")
    if record.status not in ("valued", "draft"):
        if record.booked_entry_id:
            raise ValidationError("Spis jest już ujęty w KPiR.")
    if record.status == "draft":
        record = complete_valuation(inventory_id)

    from .constants import INVENTORY_KIND_LABELS

    kind_label = INVENTORY_KIND_LABELS.get(record.kind, record.kind)
    amount = record.total_value
    entry = create_entry(
        event_date=record.inventory_date,
        document_number=f"REM/{record.inventory_date}/{record.id[-6:]}",
        description=f"Spis z natury — {kind_label}",
        purchase_goods=amount,
        source="inventory",
        entry_type="cost",
        amount_pln=amount,
        inventory_id=record.id,
        notes=record.notes or f"Wartość spisu: {amount:.2f} PLN",
    )
    entry = post_entry(entry)
    record.booked_entry_id = entry.id
    record.status = "booked"
    record.updated_at = _now()
    save_inventory(record)
    return record, entry


def inventory_value_on_date(iso_date: str) -> float:
    """Wartość ostatniego zaksięgowanego spisu na dany dzień."""
    target = iso_date[:10]
    best: InventoryRecord | None = None
    for inv in list_inventories():
        if inv.inventory_date[:10] != target:
            continue
        if inv.status not in ("valued", "booked"):
            continue
        best = inv
    if not best:
        return 0.0
    return round(best.total_value, 2)


def inventories_for_year(year: int) -> list[InventoryRecord]:
    return [i for i in list_inventories() if i.inventory_date[:4] == str(year)]


def year_end_inventory_status(year: int) -> dict[str, Any]:
    end_date = f"{year}-12-31"
    start_date = f"{year}-01-01"
    end_inv = next((i for i in list_inventories() if i.inventory_date[:10] == end_date), None)
    start_inv = next((i for i in list_inventories() if i.inventory_date[:10] == start_date), None)
    return {
        "year": year,
        "has_year_end": bool(end_inv and end_inv.status in ("valued", "booked")),
        "has_year_start": bool(start_inv and start_inv.status in ("valued", "booked")),
        "year_end_id": end_inv.id if end_inv else "",
        "year_start_id": start_inv.id if start_inv else "",
        "valuation_deadline": valuation_deadline(end_date) if end_inv else "",
    }


def compute_purchase_side_markup_pct(year: int) -> float:
    """Wskaźnik kosztów ubocznych zakupu (kol. 13 / kol. 12) za rok."""
    from .entry_service import filter_entries

    purchase_goods = 0.0
    purchase_side = 0.0
    for e in filter_entries(year=year):
        if e.status not in ("posted", "corrected") or e.source == "inventory":
            continue
        purchase_goods += e.purchase_goods
        purchase_side += e.purchase_side
    if purchase_goods <= 0:
        return 0.0
    return round(purchase_side / purchase_goods, 4)


def apply_year_side_cost_markup(inventory_id: str, year: int | None = None) -> InventoryRecord:
    """Podwyższa ceny jednostkowe towarów o wskaźnik k. ubocznych (§ wycena remanentu)."""
    record = get_inventory(inventory_id)
    if not record:
        raise ValidationError("Nie znaleziono spisu z natury.")
    y = year or int(record.inventory_date[:4])
    record.side_cost_markup_pct = compute_purchase_side_markup_pct(y)
    record = _recalc_total(record)
    record.updated_at = _now()
    save_inventory(record)
    return record
