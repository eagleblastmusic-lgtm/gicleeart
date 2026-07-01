"""Kiedy importować sprzedaż do DNR z faktur vs bezpośrednio z Shopify."""

from __future__ import annotations


def invoices_module_available() -> bool:
    try:
        import Komponenty.dokumentysprzedazy.storage  # noqa: F401
    except ImportError:
        return False
    return True


def is_jdg_active() -> bool:
    try:
        from Komponenty.kpir.storage import load_settings

        settings = load_settings()
    except ImportError:
        return False
    return bool(settings.jdg_registered_at) and settings.accounting_mode in ("jdg_kpir", "jdg_ryczalt")


def shopify_dnr_import_blocked() -> tuple[bool, str]:
    """Gdy True — bezpośredni import zamówień Shopify do DNR jest wyłączony."""
    if not invoices_module_available():
        return False, ""

    if is_jdg_active():
        return True, (
            "Przy aktywnym JDG obowiązuje przepływ: opłacone zamówienie → faktura w GicleeApp → import faktury do DNR. "
            "Shopify nie wystawia faktur — wystawiasz je w „Dokumenty sprzedaży”. "
            "Bezpośredni import zamówień grozi podwójnym wpisem lub DNR bez faktury."
        )
    return True, (
        "Shopify nie wystawia faktur — w GicleeApp wystawiasz je w „Dokumenty sprzedaży”, "
        "a do DNR importujesz wystawione faktury (sekcja powyżej). "
        "Bezpośredni import zamówień grozi podwójnym wpisem lub DNR bez faktury."
    )
