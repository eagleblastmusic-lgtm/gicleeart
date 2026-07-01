"""Numeracja dokumentów — FBV/INV, DN/KDN (ten sam styl PREFIX/n/rok) oraz TEST/TST."""

from __future__ import annotations

from datetime import datetime

from .constants import BUSINESS_MODE_DNR, numbering_preset_for_mode
from .invoice_helpers import is_test_invoice
from .models import InvoiceLanguage, InvoiceSettings, NumberingSeries

ALL_SERIES_ATTRS: list[tuple[str, InvoiceLanguage, bool, bool]] = [
    ("numbering_pl", "pl", False, False),
    ("numbering_dnr_pl", "pl", False, False),
    ("numbering_en", "en", False, False),
    ("numbering_dnr_en", "en", False, False),
    ("numbering_correction_pl", "pl", True, False),
    ("numbering_dnr_correction_pl", "pl", True, False),
    ("numbering_correction_en", "en", True, False),
    ("numbering_dnr_correction_en", "en", True, False),
    ("numbering_test_pl", "pl", False, True),
    ("numbering_test_en", "en", False, True),
]


def format_number(series: NumberingSeries) -> str:
    """PREFIX/n/rok (FBV, DN, KDN). Stary format dnr (PREFIX/rok/nnn) tylko dla zapisanych serii."""
    if (series.format or "legacy") == "dnr":
        return f"{series.prefix}/{series.year}/{series.next_number:03d}"
    return f"{series.prefix}/{series.next_number}/{series.year}"


def format_pdf_slug(number: str) -> str:
    return number.replace("/", "-")


def parse_invoice_number(number: str) -> tuple[str, int, int] | None:
    """Zwraca (prefix, kolejny_nr, rok). Obsługuje PREFIX/n/rok i PREFIX/rok/nnn."""
    parts = number.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        prefix = parts[0]
        a, b = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if b >= 2000:
        return prefix, a, b
    if a >= 2000:
        return prefix, b, a
    return None


def _series_attr_for(
    settings: InvoiceSettings,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool = False,
) -> str:
    if is_test:
        return "numbering_test_pl" if language == "pl" else "numbering_test_en"
    mode = settings.seller.business_mode or BUSINESS_MODE_DNR
    if is_correction:
        if language == "pl":
            return "numbering_dnr_correction_pl" if mode == BUSINESS_MODE_DNR else "numbering_correction_pl"
        return "numbering_dnr_correction_en" if mode == BUSINESS_MODE_DNR else "numbering_correction_en"
    if language == "pl":
        return "numbering_dnr_pl" if mode == BUSINESS_MODE_DNR else "numbering_pl"
    return "numbering_dnr_en" if mode == BUSINESS_MODE_DNR else "numbering_en"


def _series_for(
    settings: InvoiceSettings,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool = False,
) -> NumberingSeries:
    return getattr(settings, _series_attr_for(
        settings, language=language, is_correction=is_correction, is_test=is_test,
    ))


def _write_series(
    settings: InvoiceSettings,
    series: NumberingSeries,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool = False,
) -> InvoiceSettings:
    attr = _series_attr_for(
        settings, language=language, is_correction=is_correction, is_test=is_test,
    )
    setattr(settings, attr, series)
    return settings


def resolve_series_attr_by_invoice(settings: InvoiceSettings, invoice) -> str | None:
    """Która seria w settings odpowiada wystawionemu numerowi (niezależnie od bieżącego trybu)."""
    parsed = parse_invoice_number(invoice.invoice_number or "")
    if not parsed:
        return None
    prefix = parsed[0]
    is_test = is_test_invoice(invoice)
    is_corr = invoice.doc_kind == "correction"
    lang = invoice.language
    for attr, series_lang, series_corr, series_test in ALL_SERIES_ATTRS:
        if series_lang != lang or series_corr != is_corr or series_test != is_test:
            continue
        if getattr(settings, attr).prefix == prefix:
            return attr
    return None


def migrate_numbering_series(settings: InvoiceSettings) -> InvoiceSettings:
    """Oddziela serię DNR od JDG, jeśli wcześniej współdzielono numbering_pl."""
    pl = settings.numbering_pl
    if pl.format == "dnr" or pl.prefix == "DN":
        presets_dnr = numbering_preset_for_mode(BUSINESS_MODE_DNR)
        settings.numbering_dnr_pl = NumberingSeries(
            prefix=presets_dnr["pl"]["prefix"],
            next_number=pl.next_number,
            year=pl.year,
            used_numbers=list(pl.used_numbers),
            format="legacy",
        )
        presets_jdg = numbering_preset_for_mode("jdg_vat_exempt")
        settings.numbering_pl = NumberingSeries(
            prefix=presets_jdg["pl"]["prefix"],
            next_number=presets_jdg["pl"]["start"],
            year=pl.year,
            format="legacy",
        )
    corr = settings.numbering_correction_pl
    if corr.format == "dnr" or corr.prefix == "KDN":
        presets_dnr = numbering_preset_for_mode(BUSINESS_MODE_DNR)
        settings.numbering_dnr_correction_pl = NumberingSeries(
            prefix=presets_dnr["correction_pl"]["prefix"],
            next_number=corr.next_number,
            year=corr.year,
            used_numbers=list(corr.used_numbers),
            format="legacy",
        )
        presets_jdg = numbering_preset_for_mode("jdg_vat_exempt")
        settings.numbering_correction_pl = NumberingSeries(
            prefix=presets_jdg["correction_pl"]["prefix"],
            next_number=presets_jdg["correction_pl"]["start"],
            year=corr.year,
            format="legacy",
        )
    for attr in ("numbering_dnr_pl", "numbering_dnr_correction_pl"):
        series: NumberingSeries = getattr(settings, attr)
        if (series.format or "legacy") == "dnr":
            series.format = "legacy"
            setattr(settings, attr, series)
    return settings


def _issued_numbers_for_series(
    series: NumberingSeries,
    invoices: list,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool,
) -> set[str]:
    out: set[str] = set()
    for inv in invoices:
        if inv.status not in ("issued", "corrected"):
            continue
        if is_test_invoice(inv) != is_test:
            continue
        if (inv.doc_kind == "correction") != is_correction:
            continue
        if inv.language != language:
            continue
        parsed = parse_invoice_number(inv.invoice_number or "")
        if not parsed or parsed[0] != series.prefix or parsed[2] != series.year:
            continue
        out.add(inv.invoice_number)
    return out


def allocate_number(
    settings: InvoiceSettings,
    *,
    language: InvoiceLanguage,
    is_correction: bool = False,
    is_test: bool = False,
    invoices: list | None = None,
) -> tuple[str, InvoiceSettings]:
    if invoices is None:
        from .storage import list_invoices

        invoices = list_invoices()
    series = _series_for(settings, language=language, is_correction=is_correction, is_test=is_test)
    year_now = datetime.now().year
    if series.year != year_now:
        series.year = year_now
        series.next_number = 1
        series.used_numbers = []

    issued = _issued_numbers_for_series(
        series, invoices, language=language, is_correction=is_correction, is_test=is_test,
    )

    while True:
        candidate = format_number(series)
        if candidate not in series.used_numbers and candidate not in issued:
            break
        series.next_number += 1

    number = candidate
    series.used_numbers.append(number)
    series.next_number += 1

    return number, _write_series(
        settings, series, language=language, is_correction=is_correction, is_test=is_test,
    )


def reset_series_year(settings: InvoiceSettings, year: int) -> InvoiceSettings:
    for attr, *_ in ALL_SERIES_ATTRS:
        s: NumberingSeries = getattr(settings, attr)
        s.year = year
        s.next_number = 1
        s.used_numbers = []
        setattr(settings, attr, s)
    return settings


def reconcile_one_series(
    settings: InvoiceSettings,
    series_attr: str,
    invoices: list,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool = False,
    prefer_number: int | None = None,
) -> InvoiceSettings:
    """Synchronizuje jedną serię z faktycznymi fakturami w bazie."""
    series: NumberingSeries = getattr(settings, series_attr)
    active_numbers: list[str] = []
    active_nums: list[int] = []
    for inv in invoices:
        if inv.status not in ("issued", "corrected"):
            continue
        if is_test_invoice(inv) != is_test:
            continue
        if (inv.doc_kind == "correction") != is_correction:
            continue
        if inv.language != language:
            continue
        parsed = parse_invoice_number(inv.invoice_number or "")
        if not parsed or parsed[0] != series.prefix or parsed[2] != series.year:
            continue
        active_numbers.append(inv.invoice_number)
        active_nums.append(parsed[1])
    series.used_numbers = active_numbers
    next_from_max = (max(active_nums) + 1) if active_nums else 1
    if prefer_number is not None and (not active_nums or prefer_number > max(active_nums)):
        series.next_number = prefer_number
    else:
        series.next_number = next_from_max
    setattr(settings, series_attr, series)
    return settings


def reconcile_series(
    settings: InvoiceSettings,
    invoices: list,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool = False,
    prefer_number: int | None = None,
) -> InvoiceSettings:
    """Synchronizuje aktywną serię (wg bieżącego trybu) z faktycznymi fakturami."""
    attr = _series_attr_for(
        settings, language=language, is_correction=is_correction, is_test=is_test,
    )
    return reconcile_one_series(
        settings,
        attr,
        invoices,
        language=language,
        is_correction=is_correction,
        is_test=is_test,
        prefer_number=prefer_number,
    )


def reconcile_all_series(
    settings: InvoiceSettings,
    invoices: list | None = None,
    *,
    prefer_release: tuple[str, int] | None = None,
) -> InvoiceSettings:
    if invoices is None:
        from .storage import list_invoices

        invoices = list_invoices()
    for attr, language, is_correction, is_test in ALL_SERIES_ATTRS:
        prefer: int | None = None
        if prefer_release and prefer_release[0] == attr:
            prefer = prefer_release[1]
        settings = reconcile_one_series(
            settings,
            attr,
            invoices,
            language=language,
            is_correction=is_correction,
            is_test=is_test,
            prefer_number=prefer,
        )
    return settings


def can_release_number(
    invoice_number: str,
    *,
    language: InvoiceLanguage,
    is_correction: bool,
    is_test: bool,
    exclude_invoice_id: str,
    other_invoices: list,
) -> bool:
    """Czy po usunięciu można bezpiecznie zwolnić ten numer (brak wyższych w serii)."""
    parsed = parse_invoice_number(invoice_number)
    if not parsed:
        return False
    prefix, num, year = parsed
    for other in other_invoices:
        if other.id == exclude_invoice_id or other.status not in ("issued", "corrected"):
            continue
        if is_test_invoice(other) != is_test:
            continue
        if (other.doc_kind == "correction") != is_correction:
            continue
        if other.language != language:
            continue
        op = parse_invoice_number(other.invoice_number or "")
        if op and op[0] == prefix and op[2] == year and op[1] > num:
            return False
    return True


def release_number_after_delete(
    settings: InvoiceSettings,
    invoice,
    *,
    other_invoices: list | None = None,
) -> tuple[bool, InvoiceSettings]:
    """Zwalnia numer po usunięciu niezaksięgowanej faktury."""
    number = invoice.invoice_number or ""
    if not number or invoice.status not in ("issued", "corrected"):
        return False, settings
    parsed = parse_invoice_number(number)
    if not parsed:
        return False, settings
    attr = resolve_series_attr_by_invoice(settings, invoice)
    if not attr:
        return False, settings
    series = getattr(settings, attr)
    if series.prefix != parsed[0] or series.year != parsed[2]:
        return False, settings
    if other_invoices is None:
        from .storage import list_invoices

        other_invoices = list_invoices()
    remaining = [i for i in other_invoices if i.id != invoice.id]
    is_correction = invoice.doc_kind == "correction"
    is_test = is_test_invoice(invoice)
    num = parsed[1]
    if not can_release_number(
        number,
        language=invoice.language,
        is_correction=is_correction,
        is_test=is_test,
        exclude_invoice_id=invoice.id,
        other_invoices=other_invoices,
    ):
        settings = reconcile_all_series(settings, remaining)
        return False, settings
    settings = reconcile_all_series(
        settings,
        remaining,
        prefer_release=(attr, num),
    )
    return True, settings
