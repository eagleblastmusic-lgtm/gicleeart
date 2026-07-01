"""Kalendarz terminów compliance — PIT, ZUS, CEIDG (2026)."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.tax_config import compliance, ulga_na_start_months, preferential_months


def _parse_iso(iso: str) -> date | None:
    try:
        return date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None


def _deadline_status(due: date, *, today: date | None = None) -> str:
    today = today or date.today()
    if due < today:
        return "overdue"
    if due == today:
        return "today"
    if (due - today).days <= 7:
        return "due_soon"
    return "upcoming"


def _add_deadline(
    rows: list[dict[str, Any]],
    *,
    due: date,
    category: str,
    title: str,
    description: str = "",
    priority: int = 50,
    today: date | None = None,
) -> None:
    today = today or date.today()
    rows.append({
        "due_date": due.isoformat(),
        "category": category,
        "title": title,
        "description": description,
        "status": _deadline_status(due, today=today),
        "priority": priority,
        "days_left": (due - today).days,
    })


def _calendar_months_elapsed(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def zus_stage_reminders(
    *,
    jdg_registered_at: str,
    zus_stage: str,
    zus_stage_started_at: str,
    today: date | None = None,
) -> list[dict[str, Any]]:
    today = today or date.today()
    start = _parse_iso(zus_stage_started_at) or _parse_iso(jdg_registered_at)
    if not start:
        return []
    elapsed = _calendar_months_elapsed(start, today)
    rows: list[dict[str, Any]] = []
    if zus_stage == "ulga_na_start":
        total = ulga_na_start_months()
        remaining = max(0, total - elapsed + 1)
        if remaining <= 1 and remaining >= 0:
            _add_deadline(
                rows,
                due=today,
                category="zus",
                title="Koniec ulgi na start — rozważ preferencyjny ZUS",
                description=f"Minęło {elapsed} mies. uldy (limit {total} mies.).",
                priority=80,
                today=today,
            )
        elif remaining > 0:
            rows.append({
                "due_date": "",
                "category": "zus",
                "title": f"Ulga na start — zostało ok. {remaining} mies.",
                "description": f"Od {start.isoformat()}, etap: ulga na start ({total} mies.).",
                "status": "info",
                "priority": 30,
                "days_left": None,
            })
    elif zus_stage == "preferencyjny":
        total = preferential_months()
        remaining = max(0, total - elapsed + 1)
        if remaining <= 1:
            _add_deadline(
                rows,
                due=today,
                category="zus",
                title="Koniec preferencyjnego ZUS — rozważ pełny ZUS",
                description=f"Minęło {elapsed} mies. preferencyjnego (limit {total} mies.).",
                priority=75,
                today=today,
            )
        elif remaining > 0:
            rows.append({
                "due_date": "",
                "category": "zus",
                "title": f"Preferencyjny ZUS — zostało ok. {remaining} mies.",
                "description": f"Od {start.isoformat()}, etap preferencyjny ({total} mies.).",
                "status": "info",
                "priority": 25,
                "days_left": None,
            })
    return rows


def list_deadlines(
    *,
    year: int | None = None,
    month: int | None = None,
    accounting_mode: str = "jdg_kpir",
    jdg_registered_at: str = "",
    zus_stage: str = "",
    zus_stage_started_at: str = "",
    migration: dict[str, Any] | None = None,
    kpir_settings: Any = None,
) -> list[dict[str, Any]]:
    """Terminy dla JDG (PIT/ZUS) + CEIDG przy migracji DNR."""
    today = date.today()
    y = year or today.year
    cfg = compliance()
    pit_day = int(cfg.get("pit_advance_day") or 20)
    zus_day = int(cfg.get("zus_due_day") or 20)
    dra_day = int(cfg.get("zus_dra_due_day") or 20)
    rows: list[dict[str, Any]] = []

    mig = migration or {}
    if mig.get("status") in ("required", "in_progress"):
        deadline = _parse_iso(str(mig.get("ceidg_deadline") or mig.get("first_exceed_ceidg_deadline") or ""))
        if deadline:
            _add_deadline(
                rows,
                due=deadline,
                category="ceidg",
                title="Wniosek CEIDG (po przekroczeniu limitu DNR)",
                description=f"Data skutku: {mig.get('effective_date', '?')}. Termin {deadline.isoformat()}.",
                priority=100,
                today=today,
            )

    months = [month] if month else list(range(1, 13))
    is_jdg = accounting_mode in ("jdg_kpir", "jdg_ryczalt")

    for m in months:
        if is_jdg:
            if m >= 2:
                due_pit = date(y, m, min(pit_day, 28))
                _add_deadline(
                    rows,
                    due=due_pit,
                    category="pit",
                    title=f"Zaliczka PIT — {m:02d}.{y}",
                    description=f"Do {pit_day}. dnia miesiąca za poprzedni okres (skala/liniowy).",
                    priority=60,
                    today=today,
                )
                due_zus = date(y, m, min(zus_day, 28))
                _add_deadline(
                    rows,
                    due=due_zus,
                    category="zus",
                    title=f"Składki ZUS — {m:02d}.{y}",
                    description=f"Do {zus_day}. dnia miesiąca za poprzedni miesiąc.",
                    priority=55,
                    today=today,
                )
                due_dra = date(y, m, min(dra_day, 28))
                _add_deadline(
                    rows,
                    due=due_dra,
                    category="zus",
                    title=f"ZUS DRA (rozliczenie) — {m:02d}.{y}",
                    description=f"Orientacyjnie do {dra_day}. dnia miesiąca.",
                    priority=50,
                    today=today,
                )

    ann_start_m = int(cfg.get("annual_pit_start_month") or 2)
    ann_start_d = int(cfg.get("annual_pit_start_day") or 15)
    ann_end_m = int(cfg.get("annual_pit_end_month") or 4)
    ann_end_d = int(cfg.get("annual_pit_end_day") or 30)
    if is_jdg and (not month or month in (ann_start_m, ann_end_m)):
        _add_deadline(
            rows,
            due=date(y, ann_start_m, ann_start_d),
            category="pit",
            title=f"Okno zeznania rocznego PIT {y - 1}",
            description="PIT-36 / PIT-36L — od 15 lutego.",
            priority=40,
            today=today,
        )
        _add_deadline(
            rows,
            due=date(y, ann_end_m, ann_end_d),
            category="pit",
            title=f"Termin zeznania rocznego PIT {y - 1}",
            description="Ostateczny termin: 30 kwietnia.",
            priority=70,
            today=today,
        )

    if is_jdg:
        rows.extend(
            zus_stage_reminders(
                jdg_registered_at=jdg_registered_at,
                zus_stage=zus_stage,
                zus_stage_started_at=zus_stage_started_at,
                today=today,
            ),
        )

    if month:
        rows = [r for r in rows if not r["due_date"] or r["due_date"].startswith(f"{y}-{month:02d}")]

    status_order = {"overdue": 0, "today": 1, "due_soon": 2, "upcoming": 3, "info": 4}
    rows.sort(key=lambda r: (status_order.get(r["status"], 9), r.get("priority", 99), r.get("due_date") or "9999"))

    if is_jdg and kpir_settings is not None:
        try:
            from Komponenty.kpir.payment_due import enrich_deadline_amounts

            rows = [enrich_deadline_amounts(r, kpir_settings) for r in rows]
        except ImportError:
            pass

    return rows


def calendar_summary(
    *,
    year: int | None = None,
    accounting_mode: str = "jdg_kpir",
    jdg_registered_at: str = "",
    zus_stage: str = "",
    zus_stage_started_at: str = "",
    migration: dict[str, Any] | None = None,
    kpir_settings: Any = None,
) -> dict[str, Any]:
    today = date.today()
    y = year or today.year
    all_rows = list_deadlines(
        year=y,
        accounting_mode=accounting_mode,
        jdg_registered_at=jdg_registered_at,
        zus_stage=zus_stage,
        zus_stage_started_at=zus_stage_started_at,
        migration=migration,
        kpir_settings=kpir_settings,
    )
    month_rows = list_deadlines(
        year=y,
        month=today.month,
        accounting_mode=accounting_mode,
        jdg_registered_at=jdg_registered_at,
        zus_stage=zus_stage,
        zus_stage_started_at=zus_stage_started_at,
        migration=migration,
        kpir_settings=kpir_settings,
    )
    overdue = [r for r in all_rows if r["status"] == "overdue"]
    due_soon = [r for r in all_rows if r["status"] in ("today", "due_soon")]
    return {
        "year": y,
        "month": today.month,
        "all": all_rows,
        "this_month": month_rows,
        "overdue_count": len(overdue),
        "due_soon_count": len(due_soon),
        "next": next((r for r in all_rows if r.get("due_date")), None),
    }
