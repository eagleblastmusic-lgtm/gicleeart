"""Szacunkowy kalkulator PIT — rozszerzony."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.pit_deductions import health_deductible_annual, round_declaration_pln
from Komponenty._shared.tax_config import health_linear_annual_deduction_limit

from .annual_income import annual_income_breakdown
from .constants import DISCLAIMER_PIT
from .models import KpirSettings
from .summary_service import yearly_summary
from .zus_service import resolve_zus_for_pit


def _calc_tax_scale(taxable: float, settings: KpirSettings) -> tuple[int, str, float]:
    free = settings.tax_free_amount
    if taxable <= free:
        return 0, f"Skala — poniżej kwoty wolnej ({free:.0f} PLN)", 0.0
    if taxable <= settings.tax_threshold_1:
        raw = (taxable - free) * settings.tax_rate_scale_low
        return round_declaration_pln(raw), f"Skala — próg I ({settings.tax_rate_scale_low * 100:.0f}%)", raw
    part1 = (settings.tax_threshold_1 - free) * settings.tax_rate_scale_low
    part2 = (taxable - settings.tax_threshold_1) * settings.tax_rate_scale_high
    raw = part1 + part2
    return round_declaration_pln(raw), "Skala — progi I+II", raw


def _calc_tax_linear(taxable: float, settings: KpirSettings) -> tuple[int, str, float]:
    raw = taxable * settings.tax_rate_linear
    return round_declaration_pln(raw), f"Podatek liniowy {settings.tax_rate_linear * 100:.0f}%", raw


def pit_deadlines(year: int) -> list[dict[str, Any]]:
    """Terminy zaliczek PIT (uproszczone — 20. dnia miesiąca)."""
    today = date.today()
    out = []
    for m in range(1, 13):
        due = date(year, m, 20)
        if due < today and year == today.year:
            status = "minął"
        elif due == today or (due > today and len(out) == 0 and year >= today.year):
            status = "najbliższy"
        else:
            status = "planowany"
        out.append({"month": m, "due_date": due.isoformat(), "status": status})
    return out


def compare_tax_forms(year: int, settings: KpirSettings) -> dict[str, Any]:
    breakdown = annual_income_breakdown(year, settings)
    income = max(0.0, breakdown["income"])
    zus_amounts = resolve_zus_for_pit(settings, monthly_income=income / 12 if income > 0 else 0.0)
    zus = zus_amounts["zus_monthly"] * 12
    health_used_scale, _, _ = health_deductible_annual(
        income / 12, "scale", health_floor_monthly=zus_amounts["health_floor_monthly"],
    )

    base_scale = max(0.0, income - zus - health_used_scale)
    health_used_linear, _, _ = health_deductible_annual(income / 12, "linear")
    base_linear = max(0.0, income - zus - health_used_linear)

    tax_scale, det_scale, raw_scale = _calc_tax_scale(base_scale, settings)
    tax_linear, det_linear, raw_linear = _calc_tax_linear(base_linear, settings)

    better = "scale" if tax_scale <= tax_linear else "linear"
    return {
        "scale_tax": tax_scale,
        "scale_tax_raw": round(raw_scale, 2),
        "scale_details": det_scale,
        "linear_tax": tax_linear,
        "linear_tax_raw": round(raw_linear, 2),
        "linear_details": det_linear,
        "linear_health_deductible": round(health_used_linear, 2),
        "better_form": better,
        "savings": round(abs(tax_scale - tax_linear), 2),
    }


def estimate_pit(year: int, settings: KpirSettings) -> dict[str, Any]:
    breakdown = annual_income_breakdown(year, settings)
    revenue = breakdown["revenue"]
    costs = breakdown["total_costs"]
    income = max(0.0, breakdown["income"])
    monthly_income = income / 12 if income > 0 else 0.0
    zus_amounts = resolve_zus_for_pit(settings, monthly_income=monthly_income)
    zus = zus_amounts["zus_monthly"] * 12

    health_flat = zus_amounts["health_floor_monthly"] * 12
    health_used, health_calc, health_source = health_deductible_annual(
        monthly_income,
        settings.tax_form,
        health_floor_monthly=zus_amounts["health_floor_monthly"],
    )
    if settings.tax_form == "scale":
        health_used = max(health_flat, health_calc)
        health_source = "minimum ustawowe" if health_flat >= health_calc else health_source
    elif settings.tax_form == "lump_sum":
        health_used = health_flat
        health_source = "stała kwota (ryczałt)"

    taxable_base = max(0.0, income - zus - health_used)

    tax_raw = 0.0
    if settings.tax_form == "linear":
        tax, details, tax_raw = _calc_tax_linear(taxable_base, settings)
    elif settings.tax_form == "lump_sum":
        tax = 0
        details = "Ryczałt — użyj ewidencji przychodów, nie KPiR"
    else:
        tax, details, tax_raw = _calc_tax_scale(taxable_base, settings)

    advance_raw = tax_raw / 12 if tax_raw > 0 else 0.0
    from Komponenty._shared.tax_config import pit_advance_minimum_exempt

    advance_min = pit_advance_minimum_exempt()
    advance_required = advance_raw >= advance_min
    advance = round_declaration_pln(advance_raw) if advance_raw > 0 and advance_required else 0
    comparison = compare_tax_forms(year, settings)
    deadlines = pit_deadlines(year)
    next_due = next((d for d in deadlines if d["status"] in ("najbliższy", "planowany")), None)

    warnings: list[str] = []
    if zus_amounts["zus_monthly"] <= 0 and settings.zus_stage != "ulga_na_start":
        warnings.append("ZUS społeczny = 0 przy etapie innym niż ulga na start — sprawdź ustawienia.")
    if health_flat <= 0 and health_calc <= 0:
        warnings.append("Uzupełnij składkę zdrowotną w ustawieniach.")
    if settings.tax_form == "linear" and health_calc > health_used:
        warnings.append(
            f"Zdrowotna wyliczona {health_calc:,.2f} zł/rok — od podstawy odliczono "
            f"{health_used:,.2f} zł (limit {health_linear_annual_deduction_limit():,.0f} zł)."
        )

    return {
        "year": year,
        "revenue": revenue,
        "costs": costs,
        "income": round(income, 2),
        "zus_annual": zus,
        "zus_social_annual": round(zus_amounts.get("zus_social_monthly", zus_amounts["zus_monthly"]) * 12, 2),
        "zus_fp_fs_annual": round(zus_amounts.get("fp_fs_monthly", 0) * 12, 2),
        "health_annual": round(health_used, 2),
        "health_calculated": round(health_calc, 2),
        "health_flat": health_flat,
        "health_source": health_source,
        "taxable_base": round(taxable_base, 2),
        "estimated_tax": tax,
        "estimated_tax_raw": round(tax_raw, 2),
        "estimated_monthly_advance": advance,
        "estimated_monthly_advance_raw": round(advance_raw, 2),
        "advance_payment_required": advance_required,
        "advance_minimum_exempt_pln": advance_min,
        "details": details,
        "comparison": comparison,
        "next_advance_deadline": next_due,
        "warnings": warnings,
        "disclaimer": DISCLAIMER_PIT,
    }
