"""Automatyczne księgowanie po wystawieniu dokumentu — DNR lub KPiR."""

from __future__ import annotations

from Komponenty._shared.accounting_mode_sync import effective_invoice_business_mode
from Komponenty.dokumentysprzedazy.constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG
from Komponenty.dokumentysprzedazy.invoice_helpers import is_test_invoice
from Komponenty.dokumentysprzedazy.models import InvoiceRecord
from Komponenty.dokumentysprzedazy.storage import load_settings


def dnr_threshold_exceeded() -> bool:
    """True gdy działalność nierejestrowana przekroczyła limit kwartalny (obowiązek JDG)."""
    try:
        from datetime import date

        from Komponenty.dnr.migration_service import find_limit_exceed_event, migration_overview

        y = date.today().year
        ov = migration_overview(y)
        mig = ov.get("migration") or {}
        if mig.get("first_exceed_date"):
            return True
        if find_limit_exceed_event(y):
            return True
    except ImportError:
        pass
    return False


def should_book_to_dnr(invoice: InvoiceRecord) -> bool:
    """DNR tylko w trybie nierejestrowanym i pod limitem kwartalnym."""
    if is_test_invoice(invoice):
        return True
    settings = load_settings()
    mode = effective_invoice_business_mode(settings)
    if mode == BUSINESS_MODE_JDG:
        return False
    if dnr_threshold_exceeded():
        return False
    return mode == BUSINESS_MODE_DNR


def book_invoice_after_issue(invoice: InvoiceRecord) -> tuple[str, str]:
    """Księguje wystawiony dokument. Zwraca (kanał, komunikat)."""
    if is_test_invoice(invoice):
        channel = "dnr" if should_book_to_dnr(invoice) else "kpir"
        try:
            if channel == "dnr":
                from Komponenty.dnr.invoice_integration import import_invoice

                ok, msg = import_invoice(invoice.id)
                return ("dnr" if ok else "skip", msg)
            from Komponenty.kpir.invoice_integration import create_entry_from_invoice

            create_entry_from_invoice(invoice, post=True)
            return "kpir", "Zaksięgowano w KPiR (test)."
        except Exception as exc:
            return "error", str(exc)

    if should_book_to_dnr(invoice):
        try:
            from Komponenty.dnr.invoice_integration import import_invoice

            ok, msg = import_invoice(invoice.id)
            if ok:
                return "dnr", msg
            return "skip", msg
        except Exception as exc:
            return "error", f"DNR: {exc}"

    try:
        from Komponenty.kpir.invoice_integration import create_entry_from_invoice

        create_entry_from_invoice(invoice, post=True, bypass_dnr_chain=True)
        return "kpir", "Zaksięgowano w KPiR."
    except Exception as exc:
        return "error", f"KPiR: {exc}"
