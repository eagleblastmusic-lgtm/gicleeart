"""Koszty cykliczne — przypomnienia i automatyczne wpisy robocze."""

from __future__ import annotations

from datetime import date, datetime

from .cost_service import create_cost
from .models import RecurringCost
from .storage import delete_recurring as _delete_recurring
from .storage import list_recurring, new_recurring_id, save_recurring


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_recurring(**kwargs) -> RecurringCost:
    now = _now()
    item = RecurringCost(
        id=new_recurring_id(),
        name=str(kwargs.get("name") or ""),
        vendor=str(kwargs.get("vendor") or ""),
        amount=float(kwargs.get("amount") or 0),
        currency=str(kwargs.get("currency") or "PLN"),
        frequency=str(kwargs.get("frequency") or "monthly"),
        day_of_month=int(kwargs.get("day_of_month") or 1),
        category=str(kwargs.get("category") or ""),
        kpir_column=kwargs.get("kpir_column") or "other_expenses",
        active=bool(kwargs.get("active", True)),
        created_at=now,
        updated_at=now,
    )
    save_recurring(item)
    return item


def delete_recurring(item_id: str) -> bool:
    """Usuwa koszt cykliczny. Zwraca False, gdy nie znaleziono."""
    if not any(i.id == item_id for i in list_recurring()):
        return False
    _delete_recurring(item_id)
    return True


def delete_recurring_many(item_ids: list[str]) -> int:
    """Usuwa wiele kosztów cyklicznych. Zwraca liczbę usuniętych."""
    deleted = 0
    for item_id in item_ids:
        if delete_recurring(item_id):
            deleted += 1
    return deleted


def due_recurring_items(today: date | None = None) -> list[RecurringCost]:
    today = today or date.today()
    due: list[RecurringCost] = []
    for item in list_recurring():
        if not item.active:
            continue
        if item.frequency == "monthly" and today.day >= item.day_of_month:
            last = item.last_generated[:7] if item.last_generated else ""
            current = f"{today.year:04d}-{today.month:02d}"
            if last != current:
                due.append(item)
        elif item.frequency == "yearly" and today.month == item.day_of_month:
            last = item.last_generated[:4] if item.last_generated else ""
            if last != str(today.year):
                due.append(item)
    return due


def generate_draft_cost_from_recurring(item: RecurringCost, today: date | None = None) -> RecurringCost:
    today = today or date.today()
    event_date = today.isoformat()
    create_cost(
        issue_date=event_date,
        event_date=event_date,
        document_number=f"CYK/{item.id}/{today.year}{today.month:02d}",
        seller=item.vendor,
        description=f"{item.name} (cykliczny)",
        category=item.category or "inne",
        amount_gross=item.amount,
        currency=item.currency,
        kpir_column=item.kpir_column,
        is_internal_doc=True,
    )
    item.last_generated = _now()
    item.updated_at = _now()
    save_recurring(item)
    return item
