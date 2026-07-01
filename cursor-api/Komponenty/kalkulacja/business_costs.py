"""Koszty działalności JDG — stawki 2026, ulga na start i kolejne etapy ZUS."""

from __future__ import annotations

from typing import Any

from .calculator import (
    fmt_money,
    monthly_full_cost_forecast,
    monthly_revenue_forecast,
    resolved_sales_mix,
    work_days_per_month,
)
from .store import load_settings

from Komponenty._shared.pit_deductions import health_deductible_annual, round_declaration_pln
from Komponenty._shared.tax_config import pit_scale, zus as zus_cfg

_scale = pit_scale()
_zus = zus_cfg()

MIN_WAGE_2026 = float(_zus.get("min_wage") or 4806.0)
MIN_HEALTH_SKALA_LINIOWY_2026 = float(_zus.get("health_min_scale_linear") or 432.54)
PREFERENTIAL_ZUS_BASE_2026 = float(_zus.get("preferential_base") or 1441.80)
PREFERENTIAL_ZUS_SOCIAL_2026 = float(_zus.get("preferential_social") or 420.86)
PREFERENTIAL_ZUS_SOCIAL_SICK_2026 = float(_zus.get("preferential_social_sick") or 456.18)
FULL_ZUS_BASE_2026 = float(_zus.get("full_base") or 5652.0)
FULL_ZUS_SOCIAL_2026 = float(_zus.get("full_social") or 1788.29)
FULL_ZUS_SOCIAL_SICK_2026 = float(_zus.get("full_social_sick") or 1926.76)
RYCZALT_HEALTH_TIERS_2026 = tuple(
    (float(t["up_to"]) if t.get("up_to") is not None else float("inf"), float(t["amount"]))
    for t in (_zus.get("ryczalt_health_tiers") or [])
) or (
    (60_000.0, 498.35),
    (300_000.0, 830.58),
    (float("inf"), 1495.04),
)
ANNUAL_TAX_FREE_2026 = float(_scale.get("tax_free_annual") or 30_000.0)
FIRST_BRACKET_LIMIT_2026 = float(_scale.get("threshold_1") or 120_000.0)

TAX_FORMS: tuple[tuple[str, str], ...] = (
    ("skala", "Skala podatkowa (12% / 32%)"),
    ("liniowy", "Podatek liniowy (19%)"),
    ("ryczalt", "Ryczałt od przychodu"),
)

ZUS_STAGES: tuple[tuple[str, str], ...] = (
    ("ulga_na_start", "Ulga na start (6 mies. — bez ZUS społecznego)"),
    ("preferencyjny", "Preferencyjny ZUS (24 mies. po uldze)"),
    ("pelny", "Pełny ZUS"),
)

DEFAULT_BUSINESS_COSTS: dict[str, Any] = {
    "enabled": False,
    "tax_form": "skala",
    "zus_stage": "ulga_na_start",
    "relief_month": 1,
    "voluntary_sickness": False,
    "ryczalt_rate_pct": 8.5,
    "accounting_monthly": 300.0,
    "insurance_oc_monthly": 50.0,
    "bank_fees_monthly": 30.0,
    "other_monthly": 0.0,
    "tax_free_annual": ANNUAL_TAX_FREE_2026,
}


def normalize_business_costs(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    src = raw or {}
    out = dict(DEFAULT_BUSINESS_COSTS)
    out.update({k: v for k, v in src.items() if k in DEFAULT_BUSINESS_COSTS})
    out["enabled"] = bool(out.get("enabled"))
    tax = str(out.get("tax_form") or "skala")
    out["tax_form"] = tax if tax in {k for k, _ in TAX_FORMS} else "skala"
    stage = str(out.get("zus_stage") or "ulga_na_start")
    out["zus_stage"] = stage if stage in {k for k, _ in ZUS_STAGES} else "ulga_na_start"
    out["relief_month"] = max(1, min(6, int(out.get("relief_month") or 1)))
    out["voluntary_sickness"] = bool(out.get("voluntary_sickness"))
    out["ryczalt_rate_pct"] = max(0.0, float(out.get("ryczalt_rate_pct") or 8.5))
    for key in ("accounting_monthly", "insurance_oc_monthly", "bank_fees_monthly", "other_monthly"):
        out[key] = max(0.0, float(out.get(key) or 0))
    out["tax_free_annual"] = max(0.0, float(out.get("tax_free_annual") or ANNUAL_TAX_FREE_2026))
    return out


def load_business_costs(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = settings or load_settings()
    return normalize_business_costs(settings.get("business_costs"))


def social_insurance_monthly(config: dict[str, Any]) -> float:
    from Komponenty._shared.zus_stages import social_insurance_monthly as _social

    return _social(
        zus_stage=str(config.get("zus_stage") or "ulga_na_start"),
        voluntary_sickness=bool(config.get("voluntary_sickness")),
    )


def health_insurance_monthly(
    config: dict[str, Any],
    *,
    monthly_income: float,
    monthly_revenue: float,
) -> float:
    tax_form = str(config.get("tax_form") or "skala")
    income = max(0.0, float(monthly_income))
    revenue = max(0.0, float(monthly_revenue))
    annual_revenue = revenue * 12.0
    if tax_form == "skala":
        return max(MIN_HEALTH_SKALA_LINIOWY_2026, income * 0.09)
    if tax_form == "liniowy":
        return max(MIN_HEALTH_SKALA_LINIOWY_2026, income * 0.049)
    for limit, amount in RYCZALT_HEALTH_TIERS_2026:
        if annual_revenue <= limit:
            return amount
    return RYCZALT_HEALTH_TIERS_2026[-1][1]


def pit_annual_skala(annual_income: float, *, tax_free_annual: float = ANNUAL_TAX_FREE_2026) -> int:
    """PIT roczny na skali: 12% do 120 000 zł (minus kwota wolna), 32% od nadwyżki."""
    income = max(0.0, float(annual_income))
    if income <= 0.0:
        return 0
    relief = max(0.0, float(tax_free_annual)) * 0.12
    if income <= FIRST_BRACKET_LIMIT_2026:
        return round_declaration_pln(max(0.0, income * 0.12 - relief))
    bracket_tax = FIRST_BRACKET_LIMIT_2026 * 0.12 - relief
    raw = max(0.0, bracket_tax) + (income - FIRST_BRACKET_LIMIT_2026) * 0.32
    return round_declaration_pln(raw)


def pit_monthly(
    config: dict[str, Any],
    *,
    taxable_income: float,
    monthly_revenue: float,
    social_monthly: float = 0.0,
    health_floor_monthly: float = MIN_HEALTH_SKALA_LINIOWY_2026,
) -> float:
    """PIT miesięczny — skala/liniowy od dochodu (po ZUS i zdrowotnej), ryczałt od przychodu."""
    tax_form = str(config.get("tax_form") or "skala")
    income = max(0.0, float(taxable_income))
    revenue = max(0.0, float(monthly_revenue))
    if tax_form == "skala":
        annual_income = income * 12.0
        annual_zus = float(social_monthly) * 12.0
        health_used, _, _ = health_deductible_annual(
            income, "skala", health_floor_monthly=health_floor_monthly,
        )
        annual_base = max(0.0, annual_income - annual_zus - health_used)
        annual_pit = pit_annual_skala(
            annual_base,
            tax_free_annual=float(config.get("tax_free_annual") or ANNUAL_TAX_FREE_2026),
        )
        return annual_pit / 12.0
    if tax_form == "liniowy":
        annual_income = income * 12.0
        annual_zus = float(social_monthly) * 12.0
        health_used, _, _ = health_deductible_annual(income, "liniowy")
        annual_base = max(0.0, annual_income - annual_zus - health_used)
        annual_pit = round_declaration_pln(annual_base * 0.19)
        return annual_pit / 12.0
    rate = float(config.get("ryczalt_rate_pct") or 8.5) / 100.0
    return revenue * rate


def fixed_costs_monthly(config: dict[str, Any]) -> float:
    return sum(
        float(config.get(key) or 0)
        for key in (
            "accounting_monthly",
            "insurance_oc_monthly",
            "bank_fees_monthly",
            "other_monthly",
        )
    )


def taxable_income_monthly(
    config: dict[str, Any],
    *,
    monthly_revenue: float,
    monthly_production_cost: float,
) -> float:
    """Podstawa PIT i zdrowotnej (skala/liniowy): przychód − koszt prod. z wysyłką (= zysk brutto).

    Pozostałe koszty miesięczne (księgowość itd.) nie wchodzą tutaj — są odejmowane
    osobno w podsumowaniu JDG, żeby nie liczyć ich podwójnie.
    """
    revenue = max(0.0, float(monthly_revenue))
    production = max(0.0, float(monthly_production_cost))
    if str(config.get("tax_form") or "skala") == "ryczalt":
        return revenue
    return max(0.0, revenue - production)


TAX_FORM_LABELS: dict[str, str] = {
    "skala": "skala podatkowa",
    "liniowy": "podatek liniowy",
    "ryczalt": "ryczałt",
}

TAX_FORM_LABELS_LOCATIVE: dict[str, str] = {
    "skala": "skali podatkowej",
    "liniowy": "podatku liniowym",
    "ryczalt": "ryczałcie",
}


def compare_tax_forms(
    config: dict[str, Any] | None = None,
    *,
    monthly_revenue: float,
    monthly_production_cost: float,
) -> dict[str, Any]:
    """Porównuje zysk netto między formami opodatkowania (ta sama baza ZUS i kosztów stałych)."""
    cfg = normalize_business_costs(config)
    if not cfg["enabled"]:
        return {"enabled": False, "message": "", "ryczalt_better": False}

    revenue = max(0.0, float(monthly_revenue))
    production = max(0.0, float(monthly_production_cost))
    current_form = str(cfg["tax_form"])
    by_form: dict[str, float] = {}
    for form in ("skala", "liniowy", "ryczalt"):
        alt = dict(cfg)
        alt["tax_form"] = form
        by_form[form] = compute_business_costs(
            alt,
            monthly_revenue=revenue,
            monthly_production_cost=production,
        )["net_profit"]

    current_net = by_form[current_form]
    ryczalt_net = by_form["ryczalt"]
    best_form = max(by_form, key=by_form.get)
    best_net = by_form[best_form]
    ryczalt_better = current_form != "ryczalt" and ryczalt_net > current_net + 0.005
    gain = round(ryczalt_net - current_net, 2) if ryczalt_better else 0.0

    message = ""
    if ryczalt_better:
        rate = float(cfg.get("ryczalt_rate_pct") or 8.5)
        message = (
            f"Ryczałt ({rate:g}%) byłby korzystniejszy — ok. {fmt_money(gain)} więcej netto / mies.\n"
            f"({fmt_money(ryczalt_net)} vs {fmt_money(current_net)} przy "
            f"{TAX_FORM_LABELS_LOCATIVE.get(current_form, current_form)})."
        )
    elif current_form == "ryczalt" and best_form != "ryczalt" and best_net > ryczalt_net + 0.005:
        gain_alt = round(best_net - ryczalt_net, 2)
        message = (
            f"Przy tym mixie {TAX_FORM_LABELS.get(best_form, best_form)} daje ok. "
            f"{fmt_money(gain_alt)} więcej netto / mies. niż ryczałt."
        )

    return {
        "enabled": True,
        "current_form": current_form,
        "current_net": current_net,
        "ryczalt_net": ryczalt_net,
        "best_form": best_form,
        "best_net": best_net,
        "by_form": by_form,
        "ryczalt_better": ryczalt_better,
        "monthly_gain": gain,
        "message": message,
    }


def compute_business_costs(
    config: dict[str, Any] | None = None,
    *,
    monthly_revenue: float,
    monthly_production_cost: float,
) -> dict[str, Any]:
    """Rozbicie kosztów JDG na miesiąc (orientacyjnie)."""
    cfg = normalize_business_costs(config)
    revenue = max(0.0, float(monthly_revenue))
    production = max(0.0, float(monthly_production_cost))
    fixed = fixed_costs_monthly(cfg)
    gross_profit = revenue - production
    taxable = taxable_income_monthly(
        cfg,
        monthly_revenue=revenue,
        monthly_production_cost=production,
    )
    social = social_insurance_monthly(cfg)
    health = health_insurance_monthly(
        cfg,
        monthly_income=taxable if str(cfg.get("tax_form")) != "ryczalt" else gross_profit,
        monthly_revenue=revenue,
    )
    pit = pit_monthly(
        cfg,
        taxable_income=taxable,
        monthly_revenue=revenue,
        social_monthly=social,
        health_floor_monthly=MIN_HEALTH_SKALA_LINIOWY_2026,
    )
    zus_total = social + health
    total = zus_total + pit + fixed
    return {
        "enabled": cfg["enabled"],
        "config": cfg,
        "monthly_revenue": revenue,
        "production_cost": production,
        "fixed_costs": fixed,
        "operating_costs": production + fixed,
        "gross_profit": gross_profit,
        "taxable_income": taxable,
        "social_insurance": social,
        "health_insurance": health,
        "zus_total": zus_total,
        "pit": pit,
        "total": total,
        "net_profit": gross_profit - fixed - zus_total - pit,
        "daily_total": total / work_days_per_month(),
        "daily_net": (gross_profit - fixed - zus_total - pit) / work_days_per_month(),
    }


def fmt_monthly_net_forecast(
    mix: list[dict[str, Any]] | None = None,
    *,
    settings: dict[str, Any] | None = None,
) -> str:
    settings = settings or load_settings()
    mix = resolved_sales_mix(mix, settings=settings)
    cfg = load_business_costs(settings)
    if not cfg["enabled"]:
        return "—"
    monthly_revenue = monthly_revenue_forecast(mix)
    monthly_production_cost = monthly_full_cost_forecast(mix)
    result = compute_business_costs(
        cfg,
        monthly_revenue=monthly_revenue,
        monthly_production_cost=monthly_production_cost,
    )
    monthly = fmt_money(result["net_profit"])
    daily = fmt_money(result["daily_net"])
    return f"{monthly} / {daily}"
