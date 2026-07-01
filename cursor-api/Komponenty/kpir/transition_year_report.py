"""Raport roku przejściowego DNR → JDG."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .models import KpirSettings
from .summary_service import yearly_summary
from .zus_service import is_jdg_mode


def _parse_iso(iso: str) -> date | None:
    try:
        return date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None


@dataclass
class TransitionYearReport:
    year: int
    jdg_registered_at: str = ""
    split_month: int = 0
    is_transition_year: bool = False
    dnr_months: list[int] = field(default_factory=list)
    kpir_months: list[int] = field(default_factory=list)
    dnr_limit_revenue: float = 0.0
    dnr_pit_cash: float = 0.0
    dnr_costs: float = 0.0
    kpir_revenue: float = 0.0
    kpir_costs: float = 0.0
    kpir_income: float = 0.0
    lines: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "jdg_registered_at": self.jdg_registered_at,
            "split_month": self.split_month,
            "is_transition_year": self.is_transition_year,
            "dnr_months": self.dnr_months,
            "kpir_months": self.kpir_months,
            "dnr_limit_revenue": self.dnr_limit_revenue,
            "dnr_pit_cash": self.dnr_pit_cash,
            "dnr_costs": self.dnr_costs,
            "kpir_revenue": self.kpir_revenue,
            "kpir_costs": self.kpir_costs,
            "kpir_income": self.kpir_income,
            "lines": self.lines,
            "notes": self.notes,
        }


def _dnr_month_totals(year: int, months: list[int]) -> tuple[float, float, float]:
    try:
        from Komponenty.dnr.summary_service import pit_cash_revenue_for_month, sale_limit_delta
        from Komponenty.dnr.storage import list_costs, list_sales
    except ImportError:
        return 0.0, 0.0, 0.0

    limit_rev = 0.0
    pit_cash = 0.0
    costs = 0.0
    for m in months:
        pit_cash += pit_cash_revenue_for_month(year, m)
        for s in list_sales():
            if not str(s.event_date).startswith(f"{year:04d}-{m:02d}"):
                continue
            limit_rev += sale_limit_delta(s)
        for c in list_costs():
            if str(c.event_date).startswith(f"{year:04d}-{m:02d}"):
                costs += float(c.amount_pln or 0)
    return round(limit_rev, 2), round(pit_cash, 2), round(costs, 2)


def build_transition_year_report(year: int, settings: KpirSettings) -> TransitionYearReport:
    reg = _parse_iso(settings.jdg_registered_at)
    report = TransitionYearReport(year=year, jdg_registered_at=settings.jdg_registered_at or "")

    if reg and reg.year == year:
        report.split_month = reg.month
        report.is_transition_year = True
        report.dnr_months = list(range(1, reg.month))
        report.kpir_months = list(range(reg.month, 13))
        report.notes.append(
            f"Rok przejściowy: DNR do {reg.month - 1:02d}.{year}, JDG (KPiR) od {reg.month:02d}.{year}."
        )
    elif reg and reg.year < year:
        report.split_month = 13
        report.kpir_months = list(range(1, 13))
        report.notes.append(f"Pełny rok JDG (rejestracja JDG: {reg.isoformat()}).")
    elif reg and reg.year > year:
        report.split_month = 0
        report.dnr_months = list(range(1, 13))
        report.notes.append(f"Pełny rok DNR (JDG od {reg.isoformat()}).")
    else:
        report.dnr_months = list(range(1, 13))
        if is_jdg_mode(settings):
            report.kpir_months = list(range(1, 13))
            report.notes.append("Brak daty rejestracji JDG — ustaw w Ustawieniach księgowości.")
        else:
            report.notes.append("Tryb DNR — sekcja KPiR pusta do czasu migracji na JDG.")

    if report.dnr_months:
        lim, pit, cos = _dnr_month_totals(year, report.dnr_months)
        report.dnr_limit_revenue = lim
        report.dnr_pit_cash = pit
        report.dnr_costs = cos

    if report.kpir_months:
        summary = yearly_summary(year)
        rev = cos = inc = 0.0
        for m in report.kpir_months:
            d = summary["by_month"][m]
            rev += d["revenue"]
            cos += d["costs"]
            inc += d["income"]
        report.kpir_revenue = round(rev, 2)
        report.kpir_costs = round(cos, 2)
        report.kpir_income = round(inc, 2)

    months_label = (
        f"{report.dnr_months[0]:02d}–{report.dnr_months[-1]:02d}" if report.dnr_months else "—"
    )
    kpir_label = (
        f"{report.kpir_months[0]:02d}–{report.kpir_months[-1]:02d}" if report.kpir_months else "—"
    )

    report.lines = [
        f"Rok {year}",
        "",
        f"=== Okres DNR (mies. {months_label}) ===",
        f"  Przychód należny (limit): {report.dnr_limit_revenue:.2f} PLN",
        f"  Wpływy kasowe PIT (inne źródła): {report.dnr_pit_cash:.2f} PLN",
        f"  Koszty DNR: {report.dnr_costs:.2f} PLN",
        "",
        f"=== Okres JDG / KPiR (mies. {kpir_label}) ===",
        f"  Przychody KPiR: {report.kpir_revenue:.2f} PLN",
        f"  Koszty KPiR: {report.kpir_costs:.2f} PLN",
        f"  Dochód KPiR: {report.kpir_income:.2f} PLN",
    ]

    if report.is_transition_year and report.kpir_months:
        report.lines.extend([
            "",
            "Miesięcznie KPiR (okres JDG):",
        ])
        summary = yearly_summary(year)
        for m in report.kpir_months:
            d = summary["by_month"][m]
            report.lines.append(
                f"  {m:02d}: przychód {d['revenue']:.2f} / koszt {d['costs']:.2f} / dochód {d['income']:.2f}"
            )

    if report.notes:
        report.lines.extend(["", "Uwagi:"])
        report.lines.extend(f"  • {n}" for n in report.notes)

    return report
