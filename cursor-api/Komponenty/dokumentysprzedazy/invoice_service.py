"""Logika wystawiania, korekt i walidacji faktur."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .constants import BUSINESS_MODE_DNR
from .invoice_builder import (
    build_draft_from_order,
    build_manual_draft,
    build_test_draft,
    doc_type_label_for,
)
from .invoice_helpers import is_test_invoice
from .models import InvoiceRecord, InvoiceSettings, seller_display_name
from .numbering import allocate_number, format_pdf_slug, reconcile_all_series, release_number_after_delete
from .nbp_service import convert_amounts_to_pln, fetch_rate_for_income_date, income_date_from_order, parse_iso_date
from .pdf_generator import generate_invoice_pdf, pdf_filename
from .shopify_orders import mark_invoice_issued_on_shopify
from .storage import (
    append_event,
    delete_invoice_record,
    documents_dir_for_date,
    get_invoice,
    invoice_by_order_id,
    invoices_correcting,
    load_settings,
    list_invoices,
    save_invoice,
    save_settings,
)


class InvoiceValidationError(Exception):
    pass


def validate_before_issue(invoice: InvoiceRecord, settings: InvoiceSettings) -> list[str]:
    warnings: list[str] = []
    errors: list[str] = []
    if not seller_display_name(settings.seller).strip():
        errors.append("Uzupełnij dane sprzedawcy (nazwa).")
    if not settings.seller.address.strip():
        errors.append("Uzupełnij adres sprzedawcy.")
    if not invoice.buyer.name.strip() and not invoice.buyer.email.strip():
        errors.append("Brak danych nabywcy.")
    if invoice.financial_status and invoice.financial_status not in ("paid", "partially_paid", "partially_refunded"):
        warnings.append(
            f"Zamówienie ma status płatności „{invoice.financial_status}” — rozważ wystawienie po opłaceniu."
        )
    if invoice.doc_kind == "invoice" and invoice.shopify_order_id:
        existing = invoice_by_order_id(invoice.shopify_order_id)
        if existing and existing.id != invoice.id and existing.status == "issued":
            errors.append(
                f"Dla tego zamówienia wystawiono już fakturę {existing.invoice_number}. "
                "Wystaw korektę lub anuluj dokument."
            )
    if errors:
        raise InvoiceValidationError("\n".join(errors))
    return warnings


def refresh_exchange(invoice: InvoiceRecord, *, manual_rate: float | None = None) -> InvoiceRecord:
    income_d = parse_iso_date(invoice.payment_date) or parse_iso_date(invoice.sale_date) or datetime.now().date()
    info = fetch_rate_for_income_date(invoice.currency, income_d, manual_rate=manual_rate)
    pln = convert_amounts_to_pln(
        products=invoice.products_total,
        shipping=invoice.shipping_total,
        discounts=invoice.discounts_total,
        total=invoice.order_total,
        rate=float(info.get("exchange_rate_value") or 1.0),
    )
    invoice.exchange.original_currency = invoice.currency
    invoice.exchange.exchange_rate_source = str(info.get("exchange_rate_source") or "")
    invoice.exchange.exchange_rate_table_number = str(info.get("exchange_rate_table_number") or "")
    invoice.exchange.exchange_rate_date = str(info.get("exchange_rate_date") or "")
    invoice.exchange.exchange_rate_value = float(info.get("exchange_rate_value") or 1.0)
    invoice.exchange.exchange_rate_status = info.get("exchange_rate_status") or "missing"
    invoice.exchange.products_amount_pln = pln["products_amount_pln"]
    invoice.exchange.shipping_amount_pln = pln["shipping_amount_pln"]
    invoice.exchange.discounts_amount_pln = pln["discounts_amount_pln"]
    invoice.exchange.total_amount_pln = pln["total_amount_pln"]
    return invoice


def issue_invoice(invoice: InvoiceRecord, *, actor: str = "user") -> InvoiceRecord:
    settings = load_settings()
    settings = reconcile_all_series(settings)
    validate_before_issue(invoice, settings)

    is_corr = invoice.doc_kind == "correction"
    number, settings = allocate_number(
        settings,
        language=invoice.language,
        is_correction=is_corr,
        is_test=is_test_invoice(invoice),
    )
    save_settings(settings)

    invoice.invoice_number = number
    invoice.status = "issued"
    invoice.locked = True
    invoice.business_mode = settings.seller.business_mode or BUSINESS_MODE_DNR
    invoice.doc_type_label = doc_type_label_for(
        settings,
        invoice.language,
        is_correction=is_corr,
    )
    if not (invoice.payment_date or "").strip():
        invoice.payment_date = ""
    invoice.updated_at = datetime.now().isoformat(timespec="seconds")

    folder = documents_dir_for_date(invoice.issue_date)
    fname = pdf_filename(invoice)
    pdf_path = folder / fname
    generate_invoice_pdf(invoice, settings.seller, pdf_path)
    invoice.pdf_path = str(pdf_path)

    save_invoice(invoice)
    append_event("issued", invoice.id, details=invoice.invoice_number, actor=actor)

    try:
        if invoice.shopify_order_id:
            mark_invoice_issued_on_shopify(invoice.shopify_order_id, invoice.language)
    except Exception as exc:
        append_event("shopify_tag_error", invoice.id, details=str(exc), actor=actor)

    if invoice.corrected_from_invoice_id:
        orig = get_invoice(invoice.corrected_from_invoice_id)
        if orig:
            orig.status = "corrected"
            orig.updated_at = datetime.now().isoformat(timespec="seconds")
            save_invoice(orig)

    try:
        from .accounting_booking import book_invoice_after_issue
        from .orders_sync import mark_order_handled

        channel, book_msg = book_invoice_after_issue(invoice)
        append_event("booked", invoice.id, details=f"{channel}: {book_msg}", actor=actor)
        if invoice.shopify_order_id:
            mark_order_handled(invoice.shopify_order_id)
    except Exception as exc:
        append_event("book_error", invoice.id, details=str(exc), actor=actor)

    return invoice


def create_draft_for_order(order: dict[str, Any], *, language: str | None = None) -> InvoiceRecord:
    settings = load_settings()
    draft = build_draft_from_order(order, settings, language=language)
    save_invoice(draft)
    append_event("draft_created", draft.id, details=draft.shopify_order_name)
    return draft


def create_manual_draft(*, language: str | None = None) -> InvoiceRecord:
    """Nowa faktura bez zamówienia Shopify (sprzedaż poza sklepem)."""
    settings = load_settings()
    draft = build_manual_draft(settings, language=language)
    save_invoice(draft)
    append_event("draft_created", draft.id, details="poza Shopify")
    return draft


def create_test_draft(*, language: str | None = None) -> InvoiceRecord:
    """Faktura testowa — numeracja TEST/TST, w pełni usuwalna, bez ewidencji."""
    settings = load_settings()
    draft = build_test_draft(settings, language=language)
    save_invoice(draft)
    append_event("draft_created", draft.id, details="test")
    return draft


def create_correction_draft(order: dict[str, Any], original: InvoiceRecord) -> InvoiceRecord:
    settings = load_settings()
    draft = build_draft_from_order(
        order, settings, language=original.language, is_correction=True, original=original,
    )
    save_invoice(draft)
    append_event("correction_draft", draft.id, details=original.invoice_number)
    return draft


def cancel_invoice(invoice_id: str) -> InvoiceRecord:
    inv = get_invoice(invoice_id)
    if not inv:
        raise InvoiceValidationError("Nie znaleziono dokumentu.")
    if inv.sent_to_customer and not is_test_invoice(inv):
        raise InvoiceValidationError("Dokument wysłany do klienta — wystaw korektę zamiast anulowania.")
    inv.status = "cancelled"
    inv.locked = True
    inv.updated_at = datetime.now().isoformat(timespec="seconds")
    save_invoice(inv)
    append_event("cancelled", inv.id)
    return inv


def mark_pdf_downloaded(invoice_id: str) -> None:
    append_event("pdf_downloaded", invoice_id)


def mark_pdf_sent(invoice_id: str) -> None:
    inv = get_invoice(invoice_id)
    if inv and not is_test_invoice(inv):
        inv.sent_to_customer = True
        inv.updated_at = datetime.now().isoformat(timespec="seconds")
        save_invoice(inv)
    append_event("pdf_sent", invoice_id)


def _dnr_linked(invoice_id: str) -> bool:
    try:
        from Komponenty.dnr.storage import sale_for_invoice
    except ImportError:
        return False
    return sale_for_invoice(invoice_id) is not None


def _kpir_linked(invoice_id: str) -> object | None:
    """Wpis KPiR powiązany z fakturą (bezpośrednio lub przez sprzedaż DNR)."""
    try:
        from Komponenty.kpir.storage import posted_entry_for_dnr_sale, posted_entry_for_invoice
    except ImportError:
        return None
    direct = posted_entry_for_invoice(invoice_id)
    if direct:
        return direct
    try:
        from Komponenty.dnr.storage import sale_for_invoice

        sale = sale_for_invoice(invoice_id)
        if sale:
            return posted_entry_for_dnr_sale(sale.id)
    except ImportError:
        pass
    return None


def _will_release_number(inv: InvoiceRecord) -> bool:
    if is_test_invoice(inv):
        return bool(inv.invoice_number) and inv.status in ("issued", "corrected")
    if not inv.invoice_number or inv.status not in ("issued", "corrected"):
        return False
    if _dnr_linked(inv.id) or _kpir_linked(inv.id):
        return False
    from .numbering import can_release_number

    return can_release_number(
        inv.invoice_number,
        language=inv.language,
        is_correction=inv.doc_kind == "correction",
        is_test=False,
        exclude_invoice_id=inv.id,
        other_invoices=list_invoices(),
    )


def _cleanup_test_invoice_bookings(invoice_id: str) -> tuple[int, int]:
    """Usuwa wpisy DNR/KPiR powiązane z fakturą testową. Zwraca (dnr, kpir)."""
    dnr_removed = 0
    kpir_removed = 0
    sale_id = ""
    try:
        from Komponenty.dnr.storage import sale_for_invoice

        sale = sale_for_invoice(invoice_id)
        if sale:
            sale_id = sale.id
    except ImportError:
        pass

    try:
        from Komponenty.kpir.storage import delete_entry_record, list_entries

        for entry in list_entries():
            if entry.invoice_id == invoice_id or (sale_id and entry.dnr_sale_id == sale_id):
                if delete_entry_record(entry.id):
                    kpir_removed += 1
    except ImportError:
        pass

    if sale_id:
        try:
            from Komponenty.dnr.entry_service import delete_sale

            if delete_sale(sale_id):
                dnr_removed = 1
        except ImportError:
            pass

    return dnr_removed, kpir_removed


def delete_invoice_confirm_message(inv: InvoiceRecord) -> str:
    """Tekst potwierdzenia usunięcia (do messagebox)."""
    label = inv.invoice_number or "szkic"
    if is_test_invoice(inv):
        if inv.status in ("draft", "not_issued"):
            return f"Usunąć szkic faktury testowej ({label})?"
        in_dnr = _dnr_linked(inv.id)
        kpir_entry = _kpir_linked(inv.id)
        lines = [
            f"Usunąć fakturę testową {label}?",
            "",
            "Dokument testowy nie trafia do eksportu ani licznika VAT.",
            f"Numer {label} zostanie zwolniony do ponownego użycia.",
        ]
        if in_dnr or kpir_entry:
            lines.extend([
                "",
                "Powiązane wpisy DNR i KPiR zostaną usunięte razem z fakturą.",
            ])
        return "\n".join(lines)
    if inv.status in ("draft", "not_issued"):
        return f"Usunąć szkic faktury ({label})?"
    lines = [f"Usunąć fakturę {label}?"]
    in_dnr = _dnr_linked(inv.id)
    kpir_entry = _kpir_linked(inv.id)
    release = _will_release_number(inv)
    if release:
        lines.extend([
            "",
            f"Numer {label} zostanie zwolniony i będzie można go użyć ponownie.",
            "Faktura nie jest w DNR ani KPiR — usunięcie dotyczy tylko dokumentu.",
        ])
    else:
        if in_dnr or kpir_entry:
            lines.extend(["", "Numer w serii nie zostanie zwrócony."])
        elif inv.invoice_number:
            lines.extend([
                "",
                "Numer w serii nie zostanie zwrócony — istnieją wyższe numery w tej serii "
                "lub faktura jest już powiązana z ewidencją.",
            ])
        if in_dnr or kpir_entry:
            lines.append("")
            if in_dnr:
                lines.append("Faktura jest w DNR — po usunięciu usuń też wpis sprzedaży w module DNR.")
            if kpir_entry:
                num = getattr(kpir_entry, "entry_number", "") or "?"
                lines.append(f"Wpis w KPiR ({num}) pozostanie — usuń lub skoryguj w module KPiR.")
        elif not (in_dnr or kpir_entry):
            lines.extend([
                "",
                "Faktura nie jest w DNR ani KPiR — usunięcie dotyczy tylko dokumentu "
                "(wystawienie nie jest tym samym co zaksięgowanie).",
            ])
    if inv.sent_to_customer and inv.status in ("issued", "corrected"):
        lines.append("Dokument wysłany do klienta — rozważ korektę zamiast usuwania.")
    return "\n".join(lines)


def delete_invoices_bulk_confirm_extra(invoices: list[InvoiceRecord]) -> str:
    """Dopisek do potwierdzenia zbiorczego usuwania (tylko gdy są wystawione)."""
    issued = [i for i in invoices if i.status in ("issued", "corrected")]
    if not issued:
        return ""
    test_count = sum(1 for i in issued if is_test_invoice(i))
    if test_count == len(issued):
        return (
            f"\n\nWszystkie {len(issued)} wystawione to faktury testowe — "
            "numery TEST/TST zostaną zwolnione; wpisy DNR/KPiR (jeśli są) też zostaną usunięte."
        )
    releasable = sum(1 for i in issued if _will_release_number(i))
    lines = [""]
    if releasable == len(issued):
        lines.append(f"Wszystkie {len(issued)} wystawione — numery zostaną zwolnione do ponownego użycia.")
    elif releasable:
        lines.append(
            f"W tym {releasable} z {len(issued)} wystawionych — numery zostaną zwolnione; "
            f"pozostałe zachowają lukę w serii."
        )
    else:
        lines.append(f"W tym {len(issued)} wystawionych — numery w serii nie zostaną zwrócone.")
    dnr_count = sum(1 for i in issued if _dnr_linked(i.id))
    kpir_count = sum(1 for i in issued if _kpir_linked(i.id))
    if dnr_count:
        lines.append(f"{dnr_count} jest w DNR — usuń wpisy ręcznie w module DNR.")
    if kpir_count:
        lines.append(f"{kpir_count} ma wpis w KPiR — usuń lub skoryguj w module KPiR.")
    if not dnr_count and not kpir_count and releasable < len(issued):
        lines.append(
            "Część faktur nie jest w DNR ani KPiR — usuwasz tylko dokumenty "
            "(wystawienie ≠ zaksięgowanie)."
        )
    return "\n".join(lines)


def delete_invoice(invoice_id: str) -> None:
    """Usuwa fakturę z ewidencji (głównie sprzedaż poza Shopify)."""
    inv = get_invoice(invoice_id)
    if not inv:
        raise InvoiceValidationError("Nie znaleziono dokumentu.")
    if inv.shopify_order_id:
        raise InvoiceValidationError(
            "Faktury powiązane z zamówieniem Shopify nie są usuwane tutaj — "
            "użyj anulowania lub korekty w edytorze."
        )
    children = invoices_correcting(invoice_id)
    if children:
        nums = ", ".join(c.invoice_number or c.id for c in children[:3])
        raise InvoiceValidationError(f"Dokument ma powiązane korekty ({nums}) — usuń je najpierw.")
    if inv.sent_to_customer and inv.status in ("issued", "corrected") and not is_test_invoice(inv):
        raise InvoiceValidationError(
            "Dokument wysłany do klienta — nie usuwaj; wystaw korektę lub anuluj w edytorze."
        )

    all_invoices = list_invoices()
    settings = load_settings()
    remaining = [i for i in all_invoices if i.id != invoice_id]
    if is_test_invoice(inv):
        _cleanup_test_invoice_bookings(invoice_id)
        _, settings = release_number_after_delete(
            settings, inv, other_invoices=all_invoices
        )
        save_settings(settings)
    elif not _dnr_linked(invoice_id) and not _kpir_linked(invoice_id):
        _, settings = release_number_after_delete(
            settings, inv, other_invoices=all_invoices
        )
        save_settings(settings)
    else:
        settings = reconcile_all_series(settings, remaining)
        save_settings(settings)

    details = inv.invoice_number or inv.id
    pdf_path = inv.pdf_path
    if pdf_path:
        try:
            from pathlib import Path
            Path(pdf_path).unlink(missing_ok=True)
        except OSError:
            pass
    if not delete_invoice_record(invoice_id):
        raise InvoiceValidationError("Nie udało się usunąć dokumentu z bazy.")
    append_event("deleted", invoice_id, details=details)


def delete_invoices_many(invoice_ids: list[str]) -> tuple[int, list[str]]:
    """Zwraca (usunięte, komunikaty błędów)."""
    removed = 0
    errors: list[str] = []
    for iid in invoice_ids:
        try:
            delete_invoice(iid)
            removed += 1
        except InvoiceValidationError as exc:
            errors.append(str(exc))
    return removed, errors
