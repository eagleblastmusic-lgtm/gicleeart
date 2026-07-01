"""ZUS w KPiR — auto-wypełnianie z etapu (tax_config 2026)."""

from __future__ import annotations

from datetime import date

from Komponenty._shared.tax_config import preferential_months, ulga_na_start_months
from Komponenty._shared.zus_stages import (
    ZUS_STAGES,
    health_minimum_monthly,
    maly_zus_plus_eligibility,
    maly_zus_plus_progress,
    zus_stage_summary,
)

from .models import KpirSettings

_JDG_MODES = frozenset({"jdg_kpir", "jdg_ryczalt"})


def is_jdg_mode(settings: KpirSettings) -> bool:
    return settings.accounting_mode in _JDG_MODES


def _parse_iso(iso: str) -> date | None:
    try:
        return date.fromisoformat(iso[:10])
    except (TypeError, ValueError):
        return None


def _calendar_months_elapsed(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def resolve_prior_year_income(settings: KpirSettings, year: int | None = None) -> float:
    """Dochód z poprzedniego roku — do Małego ZUS Plus (auto z KPiR lub ręcznie)."""
    manual = float(settings.maly_zus_prior_year_income or 0)
    if manual > 0:
        return manual
    y = (year or date.today().year) - 1
    try:
        from .summary_service import yearly_summary

        summary = yearly_summary(y)
        return max(0.0, float(summary.get("income") or 0))
    except Exception:
        return 0.0


def zus_stage_progress(settings: KpirSettings) -> dict[str, object]:
    """Licznik miesięcy etapu ZUS (ulga 6 → preferencyjny / Mały ZUS Plus → pełny)."""
    if not is_jdg_mode(settings):
        return {"active": False, "message": "Aktywne po przejściu na JDG."}
    stage = settings.zus_stage or "ulga_na_start"
    if stage == "maly_zus_plus":
        prog = maly_zus_plus_progress(
            zus_stage_started_at=settings.zus_stage_started_at,
            jdg_registered_at=settings.jdg_registered_at,
            maly_zus_cycle_start=settings.maly_zus_cycle_start,
        )
        elig = maly_zus_plus_eligibility(
            prior_year_income=resolve_prior_year_income(settings),
            prior_year_activity_days=settings.maly_zus_prior_year_activity_days or 365,
        )
        if not elig["eligible"]:
            prog["message"] = f"{prog.get('message', '')} Uwaga: {elig['message']}"
        prog["eligibility"] = elig
        return prog
    start = _parse_iso(settings.zus_stage_started_at) or _parse_iso(settings.jdg_registered_at)
    if not start:
        return {
            "active": True,
            "message": "Ustaw datę rejestracji JDG w ustawieniach lub kreatorze migracji.",
            "needs_start_date": True,
        }
    today = date.today()
    elapsed = _calendar_months_elapsed(start, today)
    limits: dict[str, int | None] = {
        "ulga_na_start": ulga_na_start_months(),
        "preferencyjny": preferential_months(),
        "pelny": None,
    }
    total = limits.get(stage)
    label = next((lbl for k, lbl in ZUS_STAGES if k == stage), stage)
    if total is None:
        return {
            "active": True,
            "stage": stage,
            "label": label,
            "elapsed_months": elapsed,
            "remaining_months": None,
            "message": f"Etap: {label} (bez limitu czasu w aplikacji).",
            "suggest_next": None,
        }
    remaining = max(0, total - elapsed + 1)
    suggest = None
    if stage == "ulga_na_start" and remaining <= 1:
        suggest = "preferencyjny"
    elif stage == "preferencyjny" and remaining <= 1:
        suggest = "maly_zus_plus"
    msg = f"{label}: minęło {elapsed} mies., zostało ok. {remaining} mies."
    if suggest:
        msg += f" Rozważ przejście na: {suggest}."
    return {
        "active": True,
        "stage": stage,
        "label": label,
        "started_at": start.isoformat(),
        "elapsed_months": elapsed,
        "total_months": total,
        "remaining_months": remaining,
        "message": msg,
        "suggest_next": suggest,
        "needs_start_date": False,
    }


def resolve_zus_for_pit(settings: KpirSettings, *, monthly_income: float = 0.0) -> dict[str, float]:
    """Kwoty ZUS do kalkulatora PIT (auto lub ręczne)."""
    if is_jdg_mode(settings) and not settings.zus_manual_override:
        prior = resolve_prior_year_income(settings)
        summary = zus_stage_summary(
            zus_stage=settings.zus_stage,
            tax_form=settings.tax_form,
            voluntary_sickness=settings.voluntary_sickness,
            prior_year_income=prior,
        )
        social = float(summary["social_monthly"])
        fp_fs = float(summary.get("fp_fs_monthly") or 0)
        if fp_fs > 0:
            social = float(summary.get("social_without_fp_fs") or max(0.0, social - fp_fs))
        health_floor = health_minimum_monthly(settings.tax_form)
    else:
        social = float(settings.zus_monthly or 0)
        fp_fs = 0.0
        health_floor = float(settings.health_insurance_monthly or 0)
    return {
        "zus_monthly": round(social + fp_fs, 2),
        "zus_social_monthly": round(social, 2),
        "fp_fs_monthly": round(fp_fs, 2),
        "health_floor_monthly": round(health_floor, 2),
    }


def apply_auto_zus(settings: KpirSettings) -> KpirSettings:
    """Ustawia zus_monthly i health_insurance_monthly z wybranego etapu."""
    if not is_jdg_mode(settings) or settings.zus_manual_override:
        return settings
    summary = zus_stage_summary(
        zus_stage=settings.zus_stage,
        tax_form=settings.tax_form,
        voluntary_sickness=settings.voluntary_sickness,
        prior_year_income=resolve_prior_year_income(settings),
    )
    settings.zus_monthly = summary["social_monthly"]
    settings.health_insurance_monthly = summary["health_minimum_monthly"]
    return settings
