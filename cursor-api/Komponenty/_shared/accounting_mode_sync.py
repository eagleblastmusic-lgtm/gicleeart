"""Synchronizacja trybu DNR/JDG między KPiR (księgowość) a Dokumentami sprzedaży."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Komponenty.dokumentysprzedazy.models import InvoiceSettings
    from Komponenty.kpir.models import KpirSettings

_JDG_KPir_MODES = frozenset({"jdg_kpir", "jdg_ryczalt"})


def load_kpir_accounting_mode() -> str | None:
    try:
        from Komponenty.kpir.storage import load_settings

        return str(load_settings().accounting_mode or "")
    except ImportError:
        return None


def business_mode_from_accounting(accounting_mode: str) -> str:
    """KPiR → tryb faktury (dnr / jdg_vat_exempt)."""
    from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG

    if accounting_mode in _JDG_KPir_MODES:
        return BUSINESS_MODE_JDG
    return BUSINESS_MODE_DNR


def accounting_mode_from_business(
    business_mode: str,
    *,
    current_kpir: str | None = None,
) -> str:
    """Tryb faktury → KPiR (zachowuje ryczałt, jeśli już wybrany)."""
    from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_JDG

    if business_mode == BUSINESS_MODE_JDG:
        if current_kpir == "jdg_ryczalt":
            return "jdg_ryczalt"
        return "jdg_kpir"
    return "dnr"


def effective_invoice_business_mode(settings: InvoiceSettings) -> str:
    """Bieżący tryb faktur — zgodny z ustawieniami księgowości (KPiR), jeśli moduł dostępny."""
    acc = load_kpir_accounting_mode()
    if acc:
        return business_mode_from_accounting(acc)
    return settings.seller.business_mode or "dnr"


def kpir_accounting_label(accounting_mode: str) -> str:
    from Komponenty.kpir.constants import option_label, ACCOUNTING_MODE_OPTIONS

    return option_label(ACCOUNTING_MODE_OPTIONS, accounting_mode)


def sync_invoice_settings_from_kpir(settings: InvoiceSettings) -> InvoiceSettings:
    """Ustawia business_mode w ustawieniach faktur według KPiR."""
    acc = load_kpir_accounting_mode()
    if not acc:
        return settings
    expected = business_mode_from_accounting(acc)
    if settings.seller.business_mode != expected:
        settings.seller.business_mode = expected  # type: ignore[assignment]
    return settings


def sync_kpir_from_invoice_business_mode(kpir: KpirSettings, business_mode: str) -> KpirSettings:
    """Ustawia accounting_mode w KPiR według trybu faktur."""
    new_mode = accounting_mode_from_business(business_mode, current_kpir=kpir.accounting_mode)
    if kpir.accounting_mode != new_mode:
        kpir.accounting_mode = new_mode  # type: ignore[assignment]
    return kpir


def persist_business_mode_both(business_mode: str) -> None:
    """Zapisuje ten sam tryb w invoice_settings.json i kpir_settings.json."""
    from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG
    from Komponenty.dokumentysprzedazy.invoice_builder import resolve_footnote
    from Komponenty.dokumentysprzedazy.storage import load_settings as load_inv, save_settings as save_inv

    mode = business_mode if business_mode in (BUSINESS_MODE_DNR, BUSINESS_MODE_JDG) else BUSINESS_MODE_DNR
    inv = load_inv()
    inv.seller.business_mode = mode  # type: ignore[assignment]
    inv.seller.footnotes_pl = resolve_footnote(mode, inv.seller.footnotes_pl, "pl")
    inv.seller.footnotes_en = resolve_footnote(mode, inv.seller.footnotes_en, "en")
    save_inv(inv)
    try:
        from Komponenty.kpir.storage import load_settings as load_kpir, save_settings as save_kpir

        kpir = load_kpir()
        kpir = sync_kpir_from_invoice_business_mode(kpir, mode)
        save_kpir(kpir)
    except ImportError:
        pass
