"""Różnice kursowe — rozliczenie wg kursu zaksięgowania vs kursu rozliczenia."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from Komponenty.dokumentysprzedazy.nbp_service import fetch_rate_for_income_date, parse_iso_date

from .entry_service import create_entry, filter_entries, post_entry
from .storage import get_fx_settlement_for_entry, list_fx_settlements, new_fx_settlement_id, save_fx_settlement
from .models import FxSettlement


@dataclass
class FxDiffRow:
    entry_id: str
    entry_number: str
    event_date: str
    document_number: str
    entry_type: str
    currency: str
    amount_foreign: float
    booking_rate: float
    amount_pln_booked: float
    settlement_rate: float
    amount_pln_settlement: float
    fx_diff_pln: float
    diff_kind: str
    nbp_status: str
    note: str = ""


@dataclass
class FxDiffSummary:
    year: int
    month: int | None
    rows: list[FxDiffRow] = field(default_factory=list)
    total_foreign_entries: int = 0
    missing_rate_count: int = 0
    total_gain_pln: float = 0.0
    total_loss_pln: float = 0.0
    net_diff_pln: float = 0.0
    disclaimer: str = (
        "Różnica = kwota PLN po kursie rozliczenia minus kwota zaksięgowana. "
        "Dodaj kurs rozliczenia (np. ze Stripe/PayPal lub banku) dla wpisów w walucie obcej."
    )


def register_fx_settlement(
    entry_id: str,
    settlement_date: str,
    settlement_rate: float,
    *,
    note: str = "",
) -> FxSettlement:
    if settlement_rate <= 0:
        raise ValueError("Kurs rozliczenia musi być dodatni.")
    existing = get_fx_settlement_for_entry(entry_id)
    from datetime import datetime

    now = datetime.now().isoformat(timespec="seconds")
    item = FxSettlement(
        id=existing.id if existing else new_fx_settlement_id(),
        entry_id=entry_id,
        settlement_date=settlement_date[:10],
        settlement_rate=round(settlement_rate, 4),
        note=note,
        created_at=existing.created_at if existing else now,
    )
    save_fx_settlement(item)
    return item


def _booking_pln(entry: Any) -> float:
    if entry.entry_type == "revenue":
        return round(entry.total_revenue or entry.amount_pln or 0, 2)
    return round(entry.total_expenses or entry.amount_pln or 0, 2)


def _diff_kind(entry_type: str, diff: float) -> str:
    if abs(diff) < 0.01:
        return "neutral"
    if entry_type == "revenue":
        return "gain" if diff > 0 else "loss"
    return "gain" if diff < 0 else "loss"


def compute_fx_diff_report(*, year: int, month: int | None = None) -> FxDiffSummary:
    summary = FxDiffSummary(year=year, month=month)
    settlements = {s.entry_id: s for s in list_fx_settlements()}

    for e in filter_entries(year=year, month=month):
        if e.status not in ("posted", "corrected"):
            continue
        cur = (e.original_currency or "PLN").upper()
        if cur == "PLN":
            continue
        summary.total_foreign_entries += 1
        foreign = round(float(e.original_amount or 0), 2)
        booking_rate = float(e.nbp_rate or 0)
        booked_pln = _booking_pln(e)

        if e.nbp_status in ("missing", "error") or booking_rate <= 0:
            summary.missing_rate_count += 1

        settlement = settlements.get(e.id)
        settlement_rate = settlement.settlement_rate if settlement else booking_rate
        settlement_pln = round(foreign * settlement_rate, 2) if settlement_rate > 0 else booked_pln
        diff = round(settlement_pln - booked_pln, 2)
        kind = _diff_kind(e.entry_type, diff)

        note = ""
        if not settlement:
            note = "Brak kursu rozliczenia — użyto kursu zaksięgowania"
            evt = parse_iso_date(e.event_date) or date.today()
            fresh = fetch_rate_for_income_date(cur, evt)
            fresh_rate = float(fresh.get("exchange_rate_value") or 0)
            if fresh_rate > 0 and abs(fresh_rate - booking_rate) > 0.0001:
                note = f"Kurs NBP na dzień wpisu: {fresh_rate:.4f} (zaksięgowano {booking_rate:.4f})"
        else:
            note = f"Rozliczenie {settlement.settlement_date}"

        if kind == "gain":
            summary.total_gain_pln = round(summary.total_gain_pln + abs(diff), 2)
        elif kind == "loss":
            summary.total_loss_pln = round(summary.total_loss_pln + abs(diff), 2)

        summary.rows.append(FxDiffRow(
            entry_id=e.id,
            entry_number=e.entry_number,
            event_date=e.event_date[:10],
            document_number=e.document_number,
            entry_type=e.entry_type,
            currency=cur,
            amount_foreign=foreign,
            booking_rate=booking_rate,
            amount_pln_booked=booked_pln,
            settlement_rate=settlement_rate,
            amount_pln_settlement=settlement_pln,
            fx_diff_pln=diff,
            diff_kind=kind,
            nbp_status=e.nbp_status,
            note=note,
        ))

    summary.net_diff_pln = round(summary.total_gain_pln - summary.total_loss_pln, 2)
    return summary


def book_fx_diff_adjustments(*, year: int, month: int) -> list[Any]:
    """Księguje skorygowane różnice kursowe za miesiąc (przychód pozostały / koszt)."""
    report = compute_fx_diff_report(year=year, month=month)
    posted = []
    event_date = f"{year:04d}-{month:02d}-28"
    for row in report.rows:
        if row.diff_kind == "neutral" or abs(row.fx_diff_pln) < 0.01:
            continue
        if not get_fx_settlement_for_entry(row.entry_id):
            continue
        amount = abs(row.fx_diff_pln)
        if row.entry_type == "revenue":
            if row.fx_diff_pln > 0:
                entry = create_entry(
                    event_date=event_date,
                    document_number=f"RK+/{row.document_number}",
                    description=f"Dodatnia różnica kursowa: {row.document_number}",
                    revenue_other=amount,
                    source="system",
                    entry_type="revenue",
                    amount_pln=amount,
                    notes=f"Powiązany wpis: {row.entry_id}",
                )
            else:
                entry = create_entry(
                    event_date=event_date,
                    document_number=f"RK-/{row.document_number}",
                    description=f"Ujemna różnica kursowa: {row.document_number}",
                    revenue_other=-amount,
                    source="system",
                    entry_type="revenue",
                    amount_pln=-amount,
                    notes=f"Powiązany wpis: {row.entry_id}",
                )
        elif row.fx_diff_pln > 0:
            entry = create_entry(
                event_date=event_date,
                document_number=f"RK+/{row.document_number}",
                description=f"Dodatnia różnica kursowa kosztu: {row.document_number}",
                other_expenses=amount,
                source="system",
                entry_type="cost",
                amount_pln=amount,
                notes=f"Powiązany wpis: {row.entry_id}",
            )
        else:
            entry = create_entry(
                event_date=event_date,
                document_number=f"RK-/{row.document_number}",
                description=f"Ujemna różnica kursowa kosztu: {row.document_number}",
                other_expenses=-amount,
                source="system",
                entry_type="cost",
                amount_pln=-amount,
                notes=f"Powiązany wpis: {row.entry_id}",
            )
        posted.append(post_entry(entry))
    return posted
