"""Koszty ręczne → KPiR."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from Komponenty.dokumentysprzedazy.nbp_service import fetch_rate_for_income_date, parse_iso_date

from .constants import CATEGORY_TO_KPIR_COLUMN, KpirColumn
from .cost_dates import resolve_cost_event_date
from .entry_service import cancel_entry, create_entry, post_entry, update_entry
from .models import CostRecord
from .storage import delete_cost_record, get_cost, new_cost_id, save_cost
from .validation import ValidationError, validate_cost_entry


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_kpir_column(category: str) -> KpirColumn:
    return CATEGORY_TO_KPIR_COLUMN.get(category, "other_expenses")  # type: ignore[return-value]


def _apply_nbp(cost: CostRecord) -> CostRecord:
    cur = (cost.currency or "PLN").upper()
    if cur == "PLN":
        cost.nbp_rate = 1.0
        cost.amount_pln = round(cost.amount_gross, 2)
        cost.nbp_status = "not_needed"
        return cost
    event_dt = parse_iso_date(cost.event_date or cost.issue_date) or datetime.now().date()
    rate_info = fetch_rate_for_income_date(cur, event_dt)
    rate = float(rate_info.get("exchange_rate_value") or 0)
    cost.nbp_rate = rate
    cost.nbp_rate_date = str(rate_info.get("exchange_rate_date") or "")
    cost.nbp_table_number = str(rate_info.get("exchange_rate_table_number") or "")
    cost.nbp_status = str(rate_info.get("exchange_rate_status") or "missing")
    cost.amount_pln = round(cost.amount_gross * rate, 2) if rate > 0 else 0.0
    return cost


def create_cost(**kwargs: Any) -> CostRecord:
    now = _now()
    category = str(kwargs.get("category") or "inne")
    col = kwargs.get("kpir_column") or default_kpir_column(category)
    cost = CostRecord(
        id=new_cost_id(),
        issue_date=str(kwargs.get("issue_date") or now[:10]),
        event_date=str(kwargs.get("event_date") or kwargs.get("issue_date") or now[:10]),
        payment_date=str(kwargs.get("payment_date") or ""),
        document_number=str(kwargs.get("document_number") or ""),
        seller=str(kwargs.get("seller") or ""),
        seller_nip=str(kwargs.get("seller_nip") or ""),
        seller_country=str(kwargs.get("seller_country") or ""),
        description=str(kwargs.get("description") or ""),
        category=category,
        amount_gross=float(kwargs.get("amount_gross") or 0),
        currency=str(kwargs.get("currency") or "PLN"),
        payment_method=str(kwargs.get("payment_method") or ""),
        is_paid=bool(kwargs.get("is_paid")),
        kpir_column=col,
        is_internal_doc=bool(kwargs.get("is_internal_doc")),
        attachment_path=str(kwargs.get("attachment_path") or ""),
        created_at=now,
        updated_at=now,
    )
    cost = _apply_nbp(cost)
    save_cost(cost)
    return cost


def update_cost(cost: CostRecord) -> CostRecord:
    cost = _apply_nbp(cost)
    cost.updated_at = _now()
    save_cost(cost)
    return cost


def book_cost_to_kpir(cost_id: str) -> tuple[CostRecord, Any]:
    cost = get_cost(cost_id)
    if not cost:
        raise ValidationError("Nie znaleziono kosztu.")
    if cost.kpir_status == "posted" and cost.kpir_entry_id:
        raise ValidationError("Koszt jest już zaksięgowany w KPiR.")

    col = cost.kpir_column
    event_date = resolve_cost_event_date(cost)
    kwargs: dict[str, Any] = {
        "event_date": event_date,
        "document_number": cost.document_number or f"INT/{cost.id}",
        "contractor": cost.seller,
        "contractor_nip": cost.seller_nip,
        "description": cost.description or f"Koszt: {cost.category}",
        "source": "manual_cost",
        "entry_type": "cost",
        "original_currency": cost.currency,
        "original_amount": cost.amount_gross,
        "nbp_rate": cost.nbp_rate,
        "nbp_rate_date": cost.nbp_rate_date,
        "nbp_table_number": cost.nbp_table_number,
        "amount_pln": cost.amount_pln,
        "nbp_status": cost.nbp_status,
        "country": cost.seller_country,
        "cost_id": cost.id,
        "category": cost.category,
        "attachments": [cost.attachment_path] if cost.attachment_path else [],
    }
    if col == "purchase_goods":
        kwargs["purchase_goods"] = cost.amount_pln
    elif col == "purchase_side":
        kwargs["purchase_side"] = cost.amount_pln
    elif col == "wages":
        kwargs["wages"] = cost.amount_pln
    else:
        kwargs["other_expenses"] = cost.amount_pln

    entry = create_entry(**kwargs)
    validate_cost_entry(entry, cost)
    entry = post_entry(entry)

    cost.kpir_entry_id = entry.id
    cost.kpir_status = "posted"
    cost.updated_at = _now()
    save_cost(cost)
    return cost, entry


def delete_cost(cost_id: str, *, cancel_kpir_entry: bool = True) -> bool:
    """Usuwa koszt. Zaksięgowany koszt anuluje powiązany wpis KPiR."""
    cost = get_cost(cost_id)
    if not cost:
        return False
    if cost.kpir_status == "posted" and cost.kpir_entry_id:
        if not cancel_kpir_entry:
            raise ValidationError(
                "Koszt jest zaksięgowany w KPiR — usuń wpis w księdze lub potwierdź anulowanie.",
            )
        cancel_entry(cost.kpir_entry_id)
    return delete_cost_record(cost_id)


def delete_costs_many(cost_ids: list[str]) -> tuple[int, list[str]]:
    """Usuwa wiele kosztów. Zwraca (liczba usuniętych, lista błędów)."""
    deleted = 0
    errors: list[str] = []
    for cost_id in cost_ids:
        cost = get_cost(cost_id)
        label = (cost.document_number or cost_id) if cost else cost_id
        try:
            if delete_cost(cost_id):
                deleted += 1
        except ValidationError as exc:
            errors.append(f"{label}: {exc}")
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    return deleted, errors
