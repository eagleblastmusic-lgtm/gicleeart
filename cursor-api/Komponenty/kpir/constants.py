"""Stałe KPiR — kategorie, kolumny, domyślne ustawienia."""

from __future__ import annotations

from typing import Literal

AccountingMode = Literal["dnr", "jdg_kpir", "jdg_ryczalt"]
TaxForm = Literal["scale", "linear", "lump_sum"]
SalesGrouping = Literal["single", "daily", "monthly"]
KpirColumn = Literal[
    "revenue_goods",
    "revenue_other",
    "purchase_goods",
    "purchase_side",
    "wages",
    "other_expenses",
]
KpirEntryStatus = Literal["draft", "posted", "cancelled", "corrected"]
KpirEntrySource = Literal[
    "shopify",
    "invoice",
    "manual_cost",
    "import",
    "dnr_import",
    "correction",
    "recurring",
    "system",
    "inventory",
    "fixed_asset",
    "intangible_asset",
    "internal_doc",
    "sales_register",
]
CostMethod = Literal["accrual", "cash"]
InventoryKind = Literal[
    "year_start",
    "year_end",
    "business_start",
    "monthly",
    "liquidation",
    "form_change",
    "other",
]
EntryType = Literal["revenue", "cost", "correction"]
CostStatus = Literal["draft", "posted", "rejected", "corrected"]
OrderKpirStatus = Literal["not_booked", "booked", "needs_correction", "skipped"]
InvoiceKpirStatus = Literal["not_booked", "booked", "correction_issued"]

KPIR_COLUMN_LABELS: dict[str, str] = {
    "revenue_goods": "Przychód ze sprzedaży towarów i usług",
    "revenue_other": "Pozostałe przychody",
    "purchase_goods": "Zakup towarów handlowych i materiałów podstawowych",
    "purchase_side": "Koszty uboczne zakupu",
    "wages": "Wynagrodzenia",
    "other_expenses": "Pozostałe wydatki",
}

KPIR_COLUMN_BY_LABEL: dict[str, str] = {v: k for k, v in KPIR_COLUMN_LABELS.items()}

# Kolumny typowe przy dodawaniu kosztów (bez przychodów)
KPIR_COST_COLUMN_KEYS: list[str] = [
    "purchase_goods",
    "purchase_side",
    "wages",
    "other_expenses",
]

COST_KPIR_STATUS_LABELS: dict[str, str] = {
    "draft": "niezaksięgowany",
    "posted": "zaksięgowany",
    "rejected": "odrzucony",
    "corrected": "skorygowany",
}

ENTRY_STATUS_LABELS: dict[str, str] = {
    "draft": "roboczy",
    "posted": "zaksięgowany",
    "cancelled": "anulowany",
    "corrected": "skorygowany",
}

ENTRY_SOURCE_LABELS: dict[str, str] = {
    "shopify": "Shopify",
    "invoice": "faktura",
    "manual_cost": "koszt ręczny",
    "import": "import",
    "dnr_import": "import DNR",
    "correction": "korekta",
    "recurring": "cykliczny",
    "system": "system",
    "inventory": "remanent",
    "fixed_asset": "środek trwały",
    "intangible_asset": "WNiP",
    "internal_doc": "dowód wewnętrzny",
    "sales_register": "ewidencja sprzedaży",
}

DEFAULT_COST_CATEGORIES: list[str] = [
    "papier fine art",
    "tusze",
    "drewno",
    "ramy",
    "passe-partout",
    "płyty",
    "szkło / plexi",
    "zawieszki i akcesoria montażowe",
    "opakowania",
    "kartony",
    "tuby",
    "taśmy",
    "wypełniacze",
    "etykiety",
    "wysyłka",
    "kurier",
    "prowizje Shopify",
    "prowizje Stripe",
    "prowizje PayPal",
    "abonament Shopify",
    "aplikacje Shopify",
    "domena",
    "hosting",
    "reklamy",
    "narzędzia",
    "materiały eksploatacyjne",
    "usługi księgowe",
    "inne",
]

# Domyślne mapowanie kategorii → kolumna KPiR
CATEGORY_TO_KPIR_COLUMN: dict[str, KpirColumn] = {
    "papier fine art": "purchase_goods",
    "tusze": "purchase_goods",
    "drewno": "purchase_goods",
    "ramy": "purchase_goods",
    "passe-partout": "purchase_goods",
    "płyty": "purchase_goods",
    "szkło / plexi": "purchase_goods",
    "zawieszki i akcesoria montażowe": "purchase_goods",
    "opakowania": "other_expenses",
    "kartony": "other_expenses",
    "tuby": "other_expenses",
    "taśmy": "other_expenses",
    "wypełniacze": "other_expenses",
    "etykiety": "other_expenses",
    "wysyłka": "other_expenses",
    "kurier": "other_expenses",
    "prowizje Shopify": "other_expenses",
    "prowizje Stripe": "other_expenses",
    "prowizje PayPal": "other_expenses",
    "abonament Shopify": "other_expenses",
    "aplikacje Shopify": "other_expenses",
    "domena": "other_expenses",
    "hosting": "other_expenses",
    "reklamy": "other_expenses",
    "narzędzia": "other_expenses",
    "materiały eksploatacyjne": "other_expenses",
    "usługi księgowe": "other_expenses",
    "inne": "other_expenses",
}

ACCOUNTING_MODE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("dnr", "Działalność nierejestrowana"),
    ("jdg_kpir", "JDG — KPiR"),
    ("jdg_ryczalt", "JDG — ryczałt"),
)

TAX_FORM_OPTIONS: tuple[tuple[str, str], ...] = (
    ("scale", "Skala podatkowa"),
    ("linear", "Podatek liniowy"),
    ("lump_sum", "Ryczałt"),
)

SALES_GROUPING_OPTIONS: tuple[tuple[str, str], ...] = (
    ("single", "Pojedynczo (każde zamówienie)"),
    ("daily", "Zbiorczo dziennie"),
    ("monthly", "Zbiorczo miesięcznie"),
)

VAT_STATUS_OPTIONS: tuple[tuple[str, str], ...] = (
    ("exempt", "Zwolnienie z VAT (przychód brutto)"),
    ("active", "Czynny podatnik VAT (przychód netto)"),
)


def option_label(options: tuple[tuple[str, str], ...], key: str) -> str:
    for k, label in options:
        if k == key:
            return label
    return key


def option_key(options: tuple[tuple[str, str], ...], value: str) -> str:
    for k, label in options:
        if value == label or value == k:
            return k
    return value


def resolved_accounting_mode(settings) -> str:
    """Tryb do wyświetlenia w UI — zgodny z fakturami / rejestracją JDG."""
    mode = settings.accounting_mode
    if settings.jdg_registered_at and mode == "dnr":
        return "jdg_kpir"
    try:
        from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_JDG
        from Komponenty.dokumentysprzedazy.storage import load_settings as load_inv_settings

        if load_inv_settings().seller.business_mode == BUSINESS_MODE_JDG and mode == "dnr":
            return "jdg_kpir"
    except ImportError:
        pass
    return mode


from Komponenty._shared.tax_config import (
    dnr_legacy_annual_limit,
    dnr_quarterly_limit,
    pit_scale,
    vat_exemption_threshold,
)

_scale = pit_scale()

# Oficjalne kolumny PKPiR (Dz.U. 2025 poz. 1299, załącznik)
OFFICIAL_COLUMN_HEADERS: list[tuple[str, str]] = [
    ("lp", "Lp."),
    ("event_date", "Data zdarzenia"),
    ("ksef_number", "Nr e-faktury KSeF"),
    ("document_number", "Nr dowodu księgowego"),
    ("contractor_nip", "Identyfikator podatkowy kontrahenta"),
    ("contractor", "Imię i nazwisko (nazwa firmy)"),
    ("contractor_address", "Adres"),
    ("description", "Opis zdarzenia gospodarczego"),
    ("revenue_goods", "Przychód ze sprzedaży towarów i usług"),
    ("revenue_other", "Pozostałe przychody"),
    ("total_revenue", "Razem przychód (9+10)"),
    ("purchase_goods", "Zakup towarów i materiałów"),
    ("purchase_side", "Koszty uboczne zakupu"),
    ("wages", "Wynagrodzenia"),
    ("other_expenses", "Pozostałe wydatki"),
    ("total_expenses", "Razem wydatki (14+15)"),
    ("other_events", "Kolumna wolna (17)"),
    ("rd_expenses", "Koszty B+R (18)"),
    ("notes", "Uwagi (19)"),
]

COST_METHOD_OPTIONS: tuple[tuple[str, str], ...] = (
    ("accrual", "Memoriałowa (data faktury / otrzymania)"),
    ("cash", "Kasowa (data zapłaty)"),
)

INVENTORY_KIND_LABELS: dict[str, str] = {
    "year_start": "Spis na 1 stycznia",
    "year_end": "Spis na 31 grudnia",
    "business_start": "Spis na dzień rozpoczęcia działalności",
    "monthly": "Spis miesięczny",
    "liquidation": "Spis przy likwidacji",
    "form_change": "Spis przy zmianie formy opodatkowania",
    "other": "Spis dodatkowy",
}

INVENTORY_VALUATION_LABELS: dict[str, str] = {
    "purchase_price": "Cena zakupu / nabycia",
    "production_cost": "Koszt wytworzenia (półwyroby, wyroby)",
    "market_price": "Cena rynkowa (jeśli niższa)",
    "scrap_estimate": "Odpady — oszacowanie",
}

# Limity formy księgowości (orientacyjne, PLN netto)
KPIR_ANNUAL_REVENUE_LIMIT_PLN = 10_646_500.0
FIXED_ASSET_VALUE_THRESHOLD_PLN = 10_000.0
EQUIPMENT_VALUE_THRESHOLD_PLN = 1_500.0
KPIR_BOOKING_DEADLINE_DAY = 20
KPIR_RETENTION_YEARS = 5

DEFAULT_SETTINGS: dict = {
    "accounting_mode": "jdg_kpir",
    "tax_form": "scale",
    "cost_method": "accrual",
    "activity_description": "",
    "book_opened_at": "",
    "cumulative_monthly_sums": True,
    "sales_grouping": "single",
    "group_by_currency": False,
    "group_by_region": False,
    "group_regions": ["PL", "EU", "NON_EU"],
    "zus_monthly": 0.0,
    "health_insurance_monthly": 0.0,
    "zus_stage": "ulga_na_start",
    "voluntary_sickness": False,
    "zus_manual_override": False,
    "jdg_registered_at": "",
    "zus_stage_started_at": "",
    "maly_zus_prior_year_income": 0.0,
    "maly_zus_prior_year_activity_days": 365,
    "maly_zus_cycle_start": "",
    "tax_free_amount": float(_scale.get("tax_free_annual") or 30000.0),
    "tax_threshold_1": float(_scale.get("threshold_1") or 120000.0),
    "tax_rate_scale_low": float(_scale.get("rate_low") or 0.12),
    "tax_rate_scale_high": float(_scale.get("rate_high") or 0.32),
    "tax_rate_linear": 0.19,
    "dnr_limit_quarterly": dnr_quarterly_limit(),
    "vat_exemption_threshold": vat_exemption_threshold(),
    "vat_status": "exempt",
    "seller_name": "",
    "seller_nip": "",
    "seller_address": "",
}

DNR_LEGACY_ANNUAL_LIMIT = dnr_legacy_annual_limit()

DISCLAIMER_PIT = (
    "Wyliczenie ma charakter pomocniczy i wymaga weryfikacji przed zapłatą podatku."
)

JPK_PKPIR_PLACEHOLDER = "Eksport JPK_PKPIR XML — 19 kolumn (miesięczny); pakiet roczny w Eksport urzędowy"

FX_DIFF_PLACEHOLDER = "Różnice kursowe — ekran „Waluty obce” w module KPiR"

FEE_IMPORT_TIPS: dict[str, str] = {
    "auto": (
        "Stripe: Dashboard → Payments → Export → Balance Transactions.\n"
        "PayPal: Aktywność → Pobierz historię → CSV.\n"
        "Shopify: Ustawienia → Płatności → wypłaty / raport payout."
    ),
    "stripe": (
        "Eksport Stripe: Dashboard → Payments → Export → Balance Transactions.\n"
        "Plik CSV musi zawierać kolumny Fee i Created (UTC)."
    ),
    "paypal": (
        "Eksport PayPal: Aktywność → Pobierz → CSV (polski lub angielski).\n"
        "Szukamy kolumn Opłata / Fee oraz Data / Date."
    ),
    "shopify": (
        "Eksport Shopify Payments: raport wypłat (Payouts) z panelu Shopify.\n"
        "Eksport CSV z podsumowaniem opłat za wybrany okres."
    ),
}

FEE_IMPORT_MONTHLY_HINT = (
    "Zalecane: włączone „Zbiorczo per miesiąc” — jeden koszt prowizji na miesiąc "
    "(np. PROW/STRIPE/2026-03) zamiast setek pojedynczych wpisów. "
    "Odznacz tylko, gdy potrzebujesz każdej transakcji osobno."
)
