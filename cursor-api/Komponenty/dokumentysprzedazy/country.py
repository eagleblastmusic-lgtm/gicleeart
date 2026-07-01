"""Wykrywanie kraju i języka dokumentu."""

from __future__ import annotations

from .constants import EU_COUNTRY_CODES
from .i18n import InvoiceLanguage, language_from_country, normalize_language

PL_CODES = frozenset({"PL", "POL", "POLAND", "POLSKA"})


def normalize_country(code: str | None) -> str:
    if not code:
        return ""
    return str(code).strip().upper()[:2]


def is_poland(country_code: str | None) -> bool:
    c = normalize_country(country_code)
    return c == "PL" or str(country_code or "").strip().upper() in PL_CODES


def suggest_language(country_code: str | None) -> InvoiceLanguage:
    return language_from_country(country_code)


def is_eu_b2c(country_code: str | None) -> bool:
    c = normalize_country(country_code)
    return bool(c and c in EU_COUNTRY_CODES and c != "PL")


def is_foreign_order(country_code: str | None) -> bool:
    return not is_poland(country_code)
