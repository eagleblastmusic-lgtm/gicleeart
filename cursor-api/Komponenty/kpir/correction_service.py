"""Korekty — zwroty, anulowania, korekty faktur."""

from __future__ import annotations

from typing import Any

from .entry_service import create_entry, post_entry
from .storage import get_entry, posted_entry_for_order
from .validation import ValidationError


def create_correction_for_order(
    shopify_order_id: int,
    *,
    correction_amount: float,
    reason: str = "",
    document_number: str = "",
    post: bool = True,
) -> Any:
    original = posted_entry_for_order(shopify_order_id)
    if not original:
        raise ValidationError("Brak zaksięgowanego wpisu dla tego zamówienia.")

    before = original.amount_pln or original.total_revenue
    after = round(before + correction_amount, 2)

    entry = create_entry(
        event_date=original.event_date,
        document_number=document_number or f"KOR/{original.document_number}",
        contractor=original.contractor,
        description=f"Korekta — {reason or 'zwrot/anulowanie'}",
        revenue_goods=correction_amount if correction_amount < 0 else 0,
        revenue_other=correction_amount if correction_amount > 0 else 0,
        source="correction",
        entry_type="correction",
        status="draft",
        shopify_order_id=shopify_order_id,
        shopify_order_name=original.shopify_order_name,
        linked_entry_id=original.id,
        correction_reason=reason,
        amount_before_correction=before,
        correction_amount=correction_amount,
        amount_after_correction=after,
        amount_pln=correction_amount,
        original_currency=original.original_currency,
        nbp_rate=original.nbp_rate,
        nbp_rate_date=original.nbp_rate_date,
        nbp_table_number=original.nbp_table_number,
        nbp_status=original.nbp_status,
        country=original.country,
        invoice_id=original.invoice_id,
    )
    original.status = "corrected"
    from .entry_service import update_entry
    update_entry(original, reason="korekta wystawiona")

    if post:
        return post_entry(entry)
    return entry


def create_full_refund_correction(shopify_order_id: int, *, reason: str = "pełny zwrot", post: bool = True):
    original = posted_entry_for_order(shopify_order_id)
    if not original:
        raise ValidationError("Brak wpisu do skorygowania.")
    amount = -(original.amount_pln or original.total_revenue)
    return create_correction_for_order(
        shopify_order_id,
        correction_amount=amount,
        reason=reason,
        post=post,
    )


def create_partial_refund_correction(
    shopify_order_id: int,
    refund_amount_pln: float,
    *,
    reason: str = "częściowy zwrot",
    post: bool = True,
):
    return create_correction_for_order(
        shopify_order_id,
        correction_amount=-abs(refund_amount_pln),
        reason=reason,
        post=post,
    )


def create_cost_correction(
    original_entry_id: str,
    correction_amount: float,
    *,
    reason: str = "",
    document_number: str = "",
    post: bool = True,
) -> Any:
    """Korekta kosztu ze znakiem minus (§ 6 ust. 2)."""
    from .entry_service import update_entry
    from .storage import get_entry

    original = get_entry(original_entry_id)
    if not original or original.entry_type != "cost":
        raise ValidationError("Brak wpisu kosztowego do skorygowania.")

    col = "other_expenses"
    if original.purchase_goods:
        col = "purchase_goods"
    elif original.purchase_side:
        col = "purchase_side"
    elif original.wages:
        col = "wages"

    kwargs: dict[str, Any] = {
        "event_date": original.event_date,
        "document_number": document_number or f"KOR/{original.document_number}",
        "contractor": original.contractor,
        "contractor_nip": original.contractor_nip,
        "description": f"Korekta kosztu — {reason or 'korekta'}",
        "source": "correction",
        "entry_type": "correction",
        "linked_entry_id": original.id,
        "correction_reason": reason,
        "correction_amount": correction_amount,
        "amount_pln": correction_amount,
    }
    if col == "purchase_goods":
        kwargs["purchase_goods"] = correction_amount
    elif col == "purchase_side":
        kwargs["purchase_side"] = correction_amount
    elif col == "wages":
        kwargs["wages"] = correction_amount
    else:
        kwargs["other_expenses"] = correction_amount

    entry = create_entry(**kwargs)
    original.status = "corrected"
    update_entry(original, reason="korekta kosztu")
    if post:
        return post_entry(entry)
    return entry
