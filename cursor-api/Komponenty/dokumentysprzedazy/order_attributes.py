"""Atrybuty zamówienia z koszyka (note_attributes) — prośba o fakturę."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .i18n import TAX_ID_LABELS, normalize_language

ATTR_INVOICE_REQUESTED = "_Invoice requested"
ATTR_INVOICE_TYPE = "_Invoice type"
ATTR_COMPANY_NAME = "_Company name"
ATTR_TAX_ID = "_Tax ID"

INVOICE_TYPE_PRIVATE = "private"
INVOICE_TYPE_COMPANY = "company"


@dataclass
class InvoiceRequestInfo:
    requested: bool = False
    customer_type: str = ""  # private | company
    company_name: str = ""
    tax_id: str = ""

    @property
    def type_label_pl(self) -> str:
        if self.customer_type == INVOICE_TYPE_COMPANY:
            return "Firma"
        if self.customer_type == INVOICE_TYPE_PRIVATE:
            return "Osoba prywatna"
        return ""

    @property
    def type_label_en(self) -> str:
        if self.customer_type == INVOICE_TYPE_COMPANY:
            return "Company"
        if self.customer_type == INVOICE_TYPE_PRIVATE:
            return "Private individual"
        return ""


def note_attributes_map(order: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in order.get("note_attributes") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            out[name] = str(item.get("value") or "").strip()
    return out


def parse_invoice_request(order: dict[str, Any]) -> InvoiceRequestInfo:
    attrs = note_attributes_map(order)
    requested = attrs.get(ATTR_INVOICE_REQUESTED, "").lower() in ("yes", "true", "1", "tak")
    ctype = attrs.get(ATTR_INVOICE_TYPE, "").lower()
    if ctype not in (INVOICE_TYPE_PRIVATE, INVOICE_TYPE_COMPANY):
        ctype = INVOICE_TYPE_PRIVATE if requested else ""
    return InvoiceRequestInfo(
        requested=requested,
        customer_type=ctype,
        company_name=attrs.get(ATTR_COMPANY_NAME, ""),
        tax_id=attrs.get(ATTR_TAX_ID, ""),
    )


_EU_COUNTRIES = frozenset({
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU",
    "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
})


def tax_id_label_for_country(country_code: str, *, language: str = "pl") -> str:
    cc = (country_code or "").upper()
    lang = normalize_language(language)
    if cc == "PL":
        return TAX_ID_LABELS["PL"][lang]
    if cc in _EU_COUNTRIES:
        return TAX_ID_LABELS["EU"][lang]
    return TAX_ID_LABELS["OTHER"][lang]
