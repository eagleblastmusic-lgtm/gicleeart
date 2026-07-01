"""Zamykanie i otwieranie miesięcy."""

from __future__ import annotations

from datetime import datetime

from .models import MonthClosure
from .month_checklist import build_month_checklist
from .storage import get_month_closure, save_month_closure
from .validation import ValidationError


def close_month(year: int, month: int, *, force: bool = False) -> MonthClosure:
    checklist = build_month_checklist(year, month)
    if not force and not checklist.can_close:
        msgs = [i.message for i in checklist.items if i.severity == "error"][:5]
        raise ValidationError(
            "Nie można zamknąć miesiąca — " + "; ".join(msgs) if msgs else "są błędy na checkliście.",
        )
    mc = get_month_closure(year, month) or MonthClosure(year=year, month=month)
    mc.is_closed = True
    mc.closed_at = datetime.now().isoformat(timespec="seconds")
    mc.reopened_at = ""
    save_month_closure(mc)
    return mc


def reopen_month(year: int, month: int) -> MonthClosure:
    mc = get_month_closure(year, month) or MonthClosure(year=year, month=month)
    mc.is_closed = False
    mc.reopened_at = datetime.now().isoformat(timespec="seconds")
    save_month_closure(mc)
    return mc
