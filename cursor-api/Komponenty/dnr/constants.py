"""Stałe modułu DNR — wartości domyślne z tax_config_2026."""

from __future__ import annotations

from Komponenty._shared.tax_config import (
    config_id,
    dnr,
    dnr_legacy_annual_limit,
    dnr_monthly_guardrail,
    dnr_quarterly_limit,
)

_cfg = dnr()
MIN_WAGE_2026 = float(_cfg.get("min_wage") or 4806.0)
LIMIT_MULTIPLIER_2026 = float(_cfg.get("limit_multiplier") or 2.25)
DEFAULT_QUARTERLY_LIMIT = dnr_quarterly_limit()
MONTHLY_GUARDRAIL = dnr_monthly_guardrail()
LEGACY_ANNUAL_LIMIT = dnr_legacy_annual_limit()
CEIDG_DAYS = int(_cfg.get("ceidg_days") or 7)
TAX_CONFIG_ID = config_id()

DEFAULT_COST_CATEGORIES: list[str] = [
    "materiały",
    "wysyłka",
    "opakowania",
    "prowizje",
    "narzędzia",
    "reklamy",
    "inne",
]

SOURCE_LABELS: dict[str, str] = {
    "manual": "ręczny",
    "invoice": "faktura",
    "shopify": "Shopify",
    "allegro": "Allegro",
}

SALE_KIND_LABELS: dict[str, str] = {
    "sale": "sprzedaż",
    "refund": "zwrot",
    "correction": "korekta",
    "bonification": "bonifikata / skonto",
}

QUARTER_LABELS: dict[int, str] = {
    1: "I kwartał (sty–mar)",
    2: "II kwartał (kwi–cze)",
    3: "III kwartał (lip–wrz)",
    4: "IV kwartał (paź–gru)",
}

ELIGIBILITY_ITEMS: tuple[tuple[str, str], ...] = (
    ("no_dg_60m", "Nie prowadziłem/am działalności gospodarczej przez ostatnie 60 miesięcy"),
    ("no_civil_partnership", "Nie jestem wspólnikiem spółki cywilnej w tym samym zakresie"),
    ("aware_of_limits", "Wiem, że limit dotyczy przychodu należnego kwartalnie (nie zysku)"),
)

DISCLAIMER = (
    "Ewidencja pomocnicza — nie zastępuje obowiązków podatkowych ani porady księgowej. "
    "Do limitu kwartalnego liczy się przychód należny po rabatach (kwota faktycznie należna od klienta), "
    "bez kosztów własnych i prowizji. Zwroty, korekty, bonifikaty i skonta zmniejszają przychód w limicie."
)

DISCOUNT_HINT = (
    "Rabat obniża przychód należny: cena 500 zł − rabat 100 zł = 400 zł do limitu. "
    "Przy Shopify wpisuj wartość zamówienia po rabatach (towar + wysyłka w cenie)."
)

CEIDG_WARNING = (
    f"Po przekroczeniu limitu kwartalnego działalność nierejestrowana staje się działalnością "
    f"gospodarczą od dnia przekroczenia. Masz {CEIDG_DAYS} dni na złożenie wniosku do CEIDG."
)

MONTHLY_GUARDRAIL_HINT = (
    f"Orientacyjny guardrail miesięczny {MONTHLY_GUARDRAIL:,.2f} zł "
    f"(¼ limitu kwartalnego) — tylko ostrzeżenie, nie limit prawny."
)

MOR_HINT = (
    "Merchant of record (np. część rozliczeń Allegro): platforma jest sprzedawcą wobec klienta — "
    "wpis może nie wchodzić do limitu DNR ani obrotu VAT."
)

RECOGNITION_HINT = (
    "Limit kwartalny DNR = przychód należny (data sprzedaży / faktury). "
    "PIT z DNR = wpływy kasowe (data zapłaty). "
    "KPiR (JDG) księguje Shopify po opłaceniu zamówienia — to ten sam moment co u Ciebie przy wystawianiu faktury po wpłacie."
)

PIT_CASH_HINT = (
    "Do rocznego PIT-36 (inne źródła) liczą się tylko kwoty oznaczone jako opłacone (wpływy kasowe). "
    "Nieopłacone faktury zużywają limit kwartalny, ale nie zwiększają PIT do czasu wpłaty."
)

PAYMENT_STATUS_LABELS: dict[str, str] = {
    "unpaid": "nieopłacone",
    "paid": "opłacone",
    "partial": "częściowo",
}
