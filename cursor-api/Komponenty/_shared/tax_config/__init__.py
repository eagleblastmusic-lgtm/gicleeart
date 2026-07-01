"""Wersjonowana konfiguracja podatkowa Polska 2026 — jedno źródło stałych."""



from __future__ import annotations



import json

from functools import lru_cache

from pathlib import Path

from typing import Any



_CONFIG_PATH = Path(__file__).resolve().parent / "tax_config_2026.json"





@lru_cache(maxsize=1)

def load_tax_config() -> dict[str, Any]:

    raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):

        raise ValueError(f"Nieprawidłowy format: {_CONFIG_PATH}")

    return raw





def config_id() -> str:

    return str(load_tax_config().get("id") or "")





def dnr() -> dict[str, Any]:

    return dict(load_tax_config().get("dnr") or {})





def pit_scale() -> dict[str, Any]:

    pit = load_tax_config().get("pit") or {}

    return dict(pit.get("scale") or {})





def pit_linear() -> dict[str, Any]:

    pit = load_tax_config().get("pit") or {}

    return dict(pit.get("linear") or {})





def zus() -> dict[str, Any]:

    return dict(load_tax_config().get("zus") or {})





def maly_zus_plus() -> dict[str, Any]:

    return dict(zus().get("maly_zus_plus") or {})





def vat() -> dict[str, Any]:

    return dict(load_tax_config().get("vat") or {})





def compliance() -> dict[str, Any]:

    return dict(load_tax_config().get("compliance") or {})





def small_taxpayer() -> dict[str, Any]:

    return dict(load_tax_config().get("small_taxpayer") or {})





def ulga_na_start_months() -> int:

    return int(zus().get("ulga_na_start_months") or 6)





def preferential_months() -> int:

    return int(zus().get("preferential_months") or 24)





def ceidg_deadline_days() -> int:

    return int(dnr().get("ceidg_days") or 7)





def fp_fs_full() -> float:

    return float(zus().get("fp_fs_full") or 138.47)





def health_linear_annual_deduction_limit() -> float:

    return float(pit_linear().get("health_annual_deduction_limit") or 14100.0)





def mpp_invoice_threshold() -> float:

    return float(compliance().get("mpp_invoice_threshold") or 15000.0)





def vat_prorata_divisor() -> int:

    return int(vat().get("prorata_days_divisor") or 365)





def platform(name: str) -> dict[str, Any]:

    platforms = load_tax_config().get("platforms") or {}

    return dict(platforms.get(name) or {})





def dnr_quarterly_limit() -> float:

    return float(dnr().get("quarterly_limit") or 10813.5)





def dnr_monthly_guardrail() -> float:

    return float(dnr().get("monthly_guardrail") or 3604.5)





def dnr_legacy_annual_limit() -> float:

    return float(dnr().get("legacy_annual_limit") or 11250.0)





def vat_exemption_threshold() -> float:

    return float(vat().get("exemption_threshold_annual") or 240_000.0)





def wsto_tbe_threshold_pln() -> float:

    return float(vat().get("wsto_tbe_threshold_pln") or 42_000.0)





def default_vat_rate_pl() -> float:

    return float(vat().get("default_vat_rate_pl") or 23.0)





def pit_advance_minimum_exempt() -> float:

    return float(compliance().get("pit_advance_minimum_exempt_pln") or 1000.0)





def health_annual_settlement_month() -> int:

    return int(compliance().get("health_annual_settlement_month") or 4)





def ksef_monthly_gross_exemption() -> float:

    return float(small_taxpayer().get("ksef_monthly_gross_exemption_until_2026") or 10_000.0)





def merchant_of_record_default(platform_name: str) -> bool:

    return bool(platform(platform_name).get("merchant_of_record_default"))


