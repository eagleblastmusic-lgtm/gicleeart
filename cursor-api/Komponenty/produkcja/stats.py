"""Statystyki zestawienia produkcji (bez zaleznosci od Tk)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

_OVERDUE_DAYS = 14


def _parse_order_date(o: dict[str, Any]) -> date | None:
    raw = str(o.get("data_zamowienia") or "").strip()
    if not raw:
        return None
    try:
        if len(raw) >= 10 and raw[4] == "-":
            return date.fromisoformat(raw[:10])
    except ValueError:
        return None
    return None


def _is_overdue(o: dict[str, Any]) -> bool:
    if o.get("wyslane"):
        return False
    d = _parse_order_date(o)
    if not d:
        return False
    return (date.today() - d).days > _OVERDUE_DAYS


def compute_stats(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """Zwraca slownik liczb do wyswietlenia w oknie statystyk."""
    today = date.today()
    week_start = today - timedelta(days=7)

    total = len(orders)
    active = [o for o in orders if not o.get("wyslane")]
    done = [o for o in orders if o.get("wyslane")]

    n_active = len(active)
    n_overdue = sum(1 for o in orders if _is_overdue(o))

    shipped_week = 0
    for o in done:
        raw = str(o.get("data_wyslania") or o.get("data_zamowienia") or "")[:10]
        try:
            if len(raw) >= 10 and raw[4] == "-":
                ds = date.fromisoformat(raw[:10])
                if ds >= week_start:
                    shipped_week += 1
        except ValueError:
            continue

    ages: list[int] = []
    for o in active:
        d = _parse_order_date(o)
        if d:
            ages.append((today - d).days)
    avg_age = sum(ages) / len(ages) if ages else 0.0

    # Proste segmenty postepu (bez dokladnego statusu tekstowego)
    need_print = sum(1 for o in active if int(o.get("wydruk_step") or 0) < 2)
    need_frame = sum(
        1 for o in active
        if int(o.get("wydruk_step") or 0) >= 2 and not o.get("spakowane")
    )

    return {
        "total": total,
        "active": n_active,
        "done": len(done),
        "overdue": n_overdue,
        "shipped_last_7_days": shipped_week,
        "avg_age_active_days": round(avg_age, 1),
        "active_need_print": need_print,
        "active_past_print_not_packed": need_frame,
    }
