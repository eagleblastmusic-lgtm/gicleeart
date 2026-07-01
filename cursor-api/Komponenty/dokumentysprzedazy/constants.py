"""Stałe — typy dokumentów, adnotacje, domyślna numeracja."""

from __future__ import annotations

from .i18n import DEFAULT_FOOTNOTES_DNR, DEFAULT_FOOTNOTES_JDG

DOC_TYPE_PL = "Faktura bez VAT"
DOC_TYPE_EN = "Invoice without VAT"
DOC_TYPE_CORRECTION_PL = "Korekta faktury bez VAT"
DOC_TYPE_CORRECTION_EN = "Correction invoice without VAT"

DOC_TYPE_DNR_PL = "Rachunek"
DOC_TYPE_DNR_EN = "Sales receipt"
DOC_TYPE_DNR_CORRECTION_PL = "Korekta rachunku"
DOC_TYPE_DNR_CORRECTION_EN = "Correction receipt"

# Nie używamy „Faktura VAT” / „VAT Invoice”.

BUSINESS_MODE_DNR = "dnr"
BUSINESS_MODE_JDG = "jdg_vat_exempt"

BUSINESS_MODE_LABELS: dict[str, str] = {
    BUSINESS_MODE_DNR: "Działalność nierejestrowana",
    BUSINESS_MODE_JDG: "JDG zwolniona z VAT",
}


def business_mode_display(mode: str) -> str:
    return BUSINESS_MODE_LABELS.get(mode or BUSINESS_MODE_DNR, BUSINESS_MODE_LABELS[BUSINESS_MODE_DNR])

DEFAULT_FOOTNOTES: dict[str, dict[str, str]] = {
    BUSINESS_MODE_DNR: dict(DEFAULT_FOOTNOTES_DNR),
    BUSINESS_MODE_JDG: dict(DEFAULT_FOOTNOTES_JDG),
}

DEFAULT_NUMBERING = {
    "pl": {"prefix": "FBV", "start": 1, "year": 2026, "format": "legacy"},
    "en": {"prefix": "INV", "start": 1, "year": 2026, "format": "legacy"},
    "dnr_en": {"prefix": "DN-INV", "start": 1, "year": 2026, "format": "legacy"},
    "correction_pl": {"prefix": "KOR", "start": 1, "year": 2026, "format": "legacy"},
    "correction_en": {"prefix": "COR", "start": 1, "year": 2026, "format": "legacy"},
    "dnr_correction_en": {"prefix": "KDN-INV", "start": 1, "year": 2026, "format": "legacy"},
    "test_pl": {"prefix": "TEST", "start": 1, "year": 2026, "format": "legacy"},
    "test_en": {"prefix": "TST", "start": 1, "year": 2026, "format": "legacy"},
    "dnr_pl": {"prefix": "DN", "start": 1, "year": 2026, "format": "legacy"},
    "dnr_correction_pl": {"prefix": "KDN", "start": 1, "year": 2026, "format": "legacy"},
}


def numbering_preset_for_mode(mode: str) -> dict[str, dict]:
    """Domyślne serie numeracji dla trybu działalności."""
    if mode == BUSINESS_MODE_DNR:
        return {
            "pl": DEFAULT_NUMBERING["dnr_pl"],
            "en": DEFAULT_NUMBERING["dnr_en"],
            "correction_pl": DEFAULT_NUMBERING["dnr_correction_pl"],
            "correction_en": DEFAULT_NUMBERING["dnr_correction_en"],
            "test_pl": DEFAULT_NUMBERING["test_pl"],
            "test_en": DEFAULT_NUMBERING["test_en"],
        }
    return {
        "pl": DEFAULT_NUMBERING["pl"],
        "en": DEFAULT_NUMBERING["en"],
        "correction_pl": DEFAULT_NUMBERING["correction_pl"],
        "correction_en": DEFAULT_NUMBERING["correction_en"],
        "test_pl": DEFAULT_NUMBERING["test_pl"],
        "test_en": DEFAULT_NUMBERING["test_en"],
    }

SALES_CHANNEL_TEST = "test"

SHOPIFY_INVOICE_TAGS = (
    "invoice_issued",
    "invoice_without_vat",
)

EU_COUNTRY_CODES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})
