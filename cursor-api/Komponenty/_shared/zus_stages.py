"""Etapy ZUS JDG 2026 — wspólne dla KPiR i kalkulacji."""



from __future__ import annotations



from datetime import date

from typing import Any, Literal



from Komponenty._shared.tax_config import fp_fs_full, maly_zus_plus, zus as zus_cfg



ZusStage = Literal["ulga_na_start", "preferencyjny", "maly_zus_plus", "pelny"]



_zus = zus_cfg()

_mzp = maly_zus_plus()



MIN_WAGE_2026 = float(_zus.get("min_wage") or 4806.0)

MIN_HEALTH_SKALA_LINIOWY_2026 = float(_zus.get("health_min_scale_linear") or 432.54)

PREFERENTIAL_ZUS_SOCIAL_2026 = float(_zus.get("preferential_social") or 420.86)

PREFERENTIAL_ZUS_SOCIAL_SICK_2026 = float(_zus.get("preferential_social_sick") or 456.18)

FULL_ZUS_SOCIAL_2026 = float(_zus.get("full_social") or 1788.29)

FULL_ZUS_SOCIAL_SICK_2026 = float(_zus.get("full_social_sick") or 1926.76)

FP_FS_FULL_2026 = fp_fs_full()



ZUS_STAGES: tuple[tuple[str, str], ...] = (

    ("ulga_na_start", "Ulga na start (6 mies. — bez ZUS społecznego)"),

    ("preferencyjny", "Preferencyjny ZUS (24 mies. po uldze)"),

    ("maly_zus_plus", "Mały ZUS Plus (36 mies. / 60 — od dochodu)"),

    ("pelny", "Pełny ZUS"),

)



ZUS_STAGE_KEYS = frozenset(k for k, _ in ZUS_STAGES)





def _parse_iso(iso: str) -> date | None:

    try:

        return date.fromisoformat(iso[:10])

    except (TypeError, ValueError):

        return None





def _calendar_months_elapsed(start: date, end: date) -> int:

    return (end.year - start.year) * 12 + (end.month - start.month) + 1





def normalize_zus_stage(stage: str | None) -> ZusStage:

    s = str(stage or "ulga_na_start")

    return s if s in ZUS_STAGE_KEYS else "ulga_na_start"  # type: ignore[return-value]





def _preferential_social_rate(voluntary_sickness: bool) -> float:

    base = float(_mzp.get("base_min") or _zus.get("preferential_base") or 1441.8)

    ref = PREFERENTIAL_ZUS_SOCIAL_SICK_2026 if voluntary_sickness else PREFERENTIAL_ZUS_SOCIAL_2026

    return ref / base if base > 0 else 0.0





def maly_zus_plus_base_monthly(prior_year_income: float) -> float:

    """Podstawa składek Mały ZUS Plus — 30%–60% MW, od dochodu z poprzedniego roku."""

    base_min = float(_mzp.get("base_min") or 1441.8)

    base_max = float(_mzp.get("base_max") or 5652.0)

    if prior_year_income <= 0:

        return base_min

    monthly = prior_year_income / 12

    return round(max(base_min, min(base_max, monthly)), 2)





def maly_zus_plus_eligibility(

    *,

    prior_year_income: float,

    prior_year_activity_days: int = 365,

) -> dict[str, Any]:

    """Warunki ulgi Mały ZUS Plus (uproszczone — weryfikacja w ZUS)."""

    rev_max = float(_mzp.get("prior_year_revenue_max") or 120_000)

    min_days = int(_mzp.get("min_activity_days_prior_year") or 60)

    reasons: list[str] = []

    if prior_year_income > rev_max:

        reasons.append(f"przychód/dochód {prior_year_income:,.0f} zł > limit {rev_max:,.0f} zł")

    if prior_year_activity_days < min_days:

        reasons.append(f"działalność w poprzednim roku < {min_days} dni")

    eligible = not reasons

    return {

        "eligible": eligible,

        "prior_year_income": round(prior_year_income, 2),

        "prior_year_activity_days": prior_year_activity_days,

        "revenue_limit": rev_max,

        "min_activity_days": min_days,

        "reasons": reasons,

        "message": "Spełniasz warunki Małego ZUS Plus." if eligible else "; ".join(reasons),

    }





def maly_zus_plus_progress(

    *,

    zus_stage_started_at: str,

    jdg_registered_at: str = "",

    maly_zus_cycle_start: str = "",

) -> dict[str, Any]:

    """Licznik 36 mies. ulgi w cyklu 60 mies. (Mały ZUS Plus)."""

    start = _parse_iso(zus_stage_started_at) or _parse_iso(jdg_registered_at)

    if not start:

        return {

            "active": False,

            "message": "Ustaw datę startu Małego ZUS Plus.",

            "needs_start_date": True,

        }

    today = date.today()

    months_used = _calendar_months_elapsed(start, today)

    limit = int(_mzp.get("months_per_cycle") or 36)

    cycle_len = int(_mzp.get("cycle_months") or 60)

    cycle_anchor = _parse_iso(maly_zus_cycle_start) or start

    cycle_elapsed = _calendar_months_elapsed(cycle_anchor, today)

    remaining = max(0, limit - months_used + 1)

    suggest = "pelny" if remaining <= 1 else None

    msg = (

        f"Mały ZUS Plus: minęło {months_used} mies., zostało ok. {remaining} mies. ulgi "

        f"(limit {limit} w cyklu {cycle_len} mies.)."

    )

    if suggest:

        msg += " Rozważ przejście na pełny ZUS."

    return {

        "active": True,

        "started_at": start.isoformat(),

        "cycle_start": cycle_anchor.isoformat(),

        "elapsed_months": months_used,

        "total_months": limit,

        "remaining_months": remaining,

        "cycle_elapsed_months": cycle_elapsed,

        "cycle_total_months": cycle_len,

        "cycle_remaining_months": max(0, cycle_len - cycle_elapsed),

        "message": msg,

        "suggest_next": suggest,

        "needs_start_date": False,

    }





def social_insurance_monthly(

    *,

    zus_stage: str,

    voluntary_sickness: bool = False,

    prior_year_income: float = 0.0,

) -> float:

    stage = normalize_zus_stage(zus_stage)

    if stage == "ulga_na_start":

        return 0.0

    if stage == "maly_zus_plus":

        base = maly_zus_plus_base_monthly(prior_year_income)

        rate = _preferential_social_rate(voluntary_sickness)

        return round(base * rate, 2)

    if stage == "preferencyjny":

        return PREFERENTIAL_ZUS_SOCIAL_SICK_2026 if voluntary_sickness else PREFERENTIAL_ZUS_SOCIAL_2026

    social = FULL_ZUS_SOCIAL_SICK_2026 if voluntary_sickness else FULL_ZUS_SOCIAL_2026

    return round(social + FP_FS_FULL_2026, 2)





def health_minimum_monthly(tax_form: str) -> float:

    """Minimalna zdrowotna (skala/liniowy) lub pierwszy próg ryczałtu."""

    if tax_form == "lump_sum":

        tiers = _zus.get("ryczalt_health_tiers") or []

        if tiers:

            return float(tiers[0].get("amount") or 498.35)

        return 498.35

    return MIN_HEALTH_SKALA_LINIOWY_2026





def zus_stage_summary(

    *,

    zus_stage: str,

    tax_form: str = "scale",

    voluntary_sickness: bool = False,

    prior_year_income: float = 0.0,

) -> dict[str, Any]:

    social = social_insurance_monthly(

        zus_stage=zus_stage,

        voluntary_sickness=voluntary_sickness,

        prior_year_income=prior_year_income,

    )

    health_min = health_minimum_monthly(tax_form)

    stage = normalize_zus_stage(zus_stage)

    label = next((lbl for k, lbl in ZUS_STAGES if k == stage), zus_stage)

    out: dict[str, Any] = {

        "zus_stage": stage,

        "label": label,

        "social_monthly": round(social, 2),

        "health_minimum_monthly": round(health_min, 2),

        "voluntary_sickness": voluntary_sickness,

    }

    if stage == "pelny":

        out["fp_fs_monthly"] = FP_FS_FULL_2026

        out["social_without_fp_fs"] = round(social - FP_FS_FULL_2026, 2)

    if stage == "maly_zus_plus":

        out["maly_zus_base_monthly"] = maly_zus_plus_base_monthly(prior_year_income)

        out["prior_year_income"] = round(prior_year_income, 2)

    return out


