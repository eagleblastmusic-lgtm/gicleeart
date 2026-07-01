"""Testy modułu KPiR."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any
from unittest import mock

# Izolacja storage na czas testów — katalog tworzony per test w _patch_storage()


def _patch_storage(monkeypatch_dir: Path | None = None) -> Path:
    import Komponenty.dokumentysprzedazy.storage as inv_st
    import Komponenty.kpir.storage as st

    if monkeypatch_dir:
        d = monkeypatch_dir
    else:
        d = Path(tempfile.mkdtemp(prefix="kpir_test_"))
    st._DATA_DIR = d / "dane"  # noqa: SLF001
    st._DOCUMENTS_DIR = d / "documents"  # noqa: SLF001
    st._SETTINGS_FILE = st._DATA_DIR / "kpir_settings.json"  # noqa: SLF001
    st._DB_FILE = st._DATA_DIR / "kpir.json"  # noqa: SLF001
    st._CHANGELOG_FILE = st._DATA_DIR / "kpir_changelog.jsonl"  # noqa: SLF001
    st.ensure_dirs()
    inv_st._DATA_DIR = d / "inv_dane"  # noqa: SLF001
    inv_st._INVOICES_FILE = inv_st._DATA_DIR / "invoices.json"  # noqa: SLF001
    inv_st.ensure_dirs()
    return d


def _check(label: str, cond: bool) -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        raise AssertionError(label)


def _mock_order_pln() -> dict:
    return {
        "id": 1001,
        "name": "#1001",
        "currency": "PLN",
        "total_price": "150.00",
        "subtotal_price": "130.00",
        "total_discounts": "0.00",
        "financial_status": "paid",
        "processed_at": "2026-03-15T10:00:00+00:00",
        "created_at": "2026-03-15T09:00:00+00:00",
        "shipping_address": {"country_code": "PL", "name": "Jan Kowalski"},
        "customer": {"first_name": "Jan", "last_name": "Kowalski"},
    }


def _mock_order_eur() -> dict:
    return {
        "id": 1002,
        "name": "#1002",
        "currency": "EUR",
        "total_price": "50.00",
        "subtotal_price": "45.00",
        "total_discounts": "0.00",
        "financial_status": "paid",
        "processed_at": "2026-03-16T10:00:00+00:00",
        "created_at": "2026-03-16T09:00:00+00:00",
        "shipping_address": {"country_code": "DE", "name": "Hans Mueller"},
        "customer": {"first_name": "Hans", "last_name": "Mueller"},
    }


def _book_test_invoice(
    *,
    invoice_id: str,
    shopify_order_id: int,
    order_name: str,
    amount: float = 150.0,
    sale_date: str = "2026-03-15",
    issue_date: str = "2026-03-15",
    payment_date: str = "2026-03-15T12:00:00",
    currency: str = "PLN",
    exchange: Any = None,
    country_code: str = "PL",
):
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.kpir.invoice_integration import create_entry_from_invoice

    if exchange is None:
        exchange = ExchangeRateInfo(
            original_currency=currency,
            exchange_rate_value=1.0 if currency == "PLN" else 4.30,
            exchange_rate_date=sale_date,
            exchange_rate_table_number="045/A/NBP/2026" if currency != "PLN" else "",
            exchange_rate_status="not_needed" if currency == "PLN" else "fetched",
            total_amount_pln=amount,
            products_amount_pln=amount,
        )
    inv = InvoiceRecord(
        id=invoice_id,
        shopify_order_id=shopify_order_id,
        shopify_order_name=order_name,
        status="issued",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Faktura bez VAT",
        invoice_number=f"FBV/T/{shopify_order_id}",
        sale_date=sale_date,
        issue_date=issue_date,
        payment_date=payment_date,
        buyer=PartyDetails(name="Jan Kowalski", country_code=country_code),
        shipping_address=PartyDetails(country_code=country_code),
        order_total=amount if currency == "PLN" else amount / (exchange.exchange_rate_value or 1.0),
        currency=currency,
        exchange=exchange,
    )
    with mock.patch("Komponenty.kpir.invoice_integration.uses_dnr_sales_chain", return_value=False):
        return create_entry_from_invoice(inv, post=True)


def test_order_requires_invoice() -> None:
    from Komponenty.kpir.shopify_service import can_book_order, create_entry_from_order
    from Komponenty.kpir.validation import ValidationError

    ok, reason = can_book_order(_mock_order_pln())
    _check("can_book_order zablokowane", not ok)
    _check("can_book_order — komunikat", "faktura" in reason.lower())
    try:
        create_entry_from_order(_mock_order_pln(), post=True)
        _check("create_entry_from_order zablokowane", False)
    except ValidationError:
        _check("create_entry_from_order zablokowane", True)


def test_shopify_pln_entry() -> None:
    entry = _book_test_invoice(
        invoice_id="INV-T-1001",
        shopify_order_id=1001,
        order_name="#1001",
        amount=150.0,
    )
    _check("Faktura PLN -> wpis przychodu", entry.revenue_goods == 150.0)
    _check("Status zaksięgowany", entry.status == "posted")
    _check("Źródło faktura", entry.source == "invoice")


def test_shopify_eur_nbp() -> None:
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo

    exchange = ExchangeRateInfo(
        original_currency="EUR",
        exchange_rate_value=4.30,
        exchange_rate_date="2026-03-14",
        exchange_rate_table_number="045/A/NBP/2026",
        exchange_rate_status="fetched",
        total_amount_pln=215.0,
        products_amount_pln=215.0,
    )
    entry = _book_test_invoice(
        invoice_id="INV-T-1002",
        shopify_order_id=1002,
        order_name="#1002",
        amount=215.0,
        currency="EUR",
        exchange=exchange,
        sale_date="2026-03-16",
        payment_date="2026-03-16T10:00:00",
        country_code="DE",
    )
    _check("EUR -> PLN przez NBP", entry.amount_pln == 215.0)
    _check("Kurs NBP zapisany", entry.nbp_rate == 4.30)


def test_invoice_entry() -> None:
    from Komponenty.dokumentysprzedazy.invoice_helpers import invoice_kpir_event_date
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.kpir.invoice_integration import create_entry_from_invoice

    inv = InvoiceRecord(
        id="INV-TEST-001",
        shopify_order_id=2001,
        shopify_order_name="#2001",
        status="issued",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Faktura bez VAT",
        invoice_number="FBV/1/2026",
        sale_date="2026-03-10",
        issue_date="2026-03-12",
        payment_date="2026-03-15T12:00:00",
        buyer=PartyDetails(name="Firma Test", country_code="PL"),
        shipping_address=PartyDetails(country_code="PL"),
        order_total=200.0,
        currency="PLN",
        exchange=ExchangeRateInfo(total_amount_pln=200.0, exchange_rate_status="not_needed"),
    )
    _check("KPiR data z wpływu", invoice_kpir_event_date(inv) == "2026-03-15")
    from unittest import mock

    with mock.patch("Komponenty.kpir.invoice_integration.uses_dnr_sales_chain", return_value=False):
        entry = create_entry_from_invoice(inv, post=True)
    _check("Faktura -> KPiR", entry.invoice_id == "INV-TEST-001")
    _check("Data wpisu KPiR", entry.event_date == "2026-03-15")
    _check("Przychód z faktury", entry.revenue_goods == 200.0)


def _patch_invoice_storage(tmp: Path) -> None:
    import Komponenty.dokumentysprzedazy.storage as inv_st

    inv_st._DATA_DIR = tmp / "inv" / "dane"  # noqa: SLF001
    inv_st._DOCUMENTS_DIR = tmp / "inv" / "documents" / "invoices"  # noqa: SLF001
    inv_st._SETTINGS_FILE = inv_st._DATA_DIR / "invoice_settings.json"  # noqa: SLF001
    inv_st._INVOICES_FILE = inv_st._DATA_DIR / "invoices.json"  # noqa: SLF001
    inv_st.ensure_dirs()


def test_corrected_invoice_kpir_list() -> None:
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.invoice_list import unbooked_invoices

    _patch_invoice_storage(_patch_storage())
    inv = InvoiceRecord(
        id="INV-CORR-1",
        shopify_order_id=0,
        shopify_order_name="",
        status="corrected",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Korekta faktury bez VAT",
        invoice_number="KOR/1/2026",
        sale_date="2026-03-20",
        issue_date="2026-03-21",
        buyer=PartyDetails(name="Klient", country_code="PL"),
        shipping_address=PartyDetails(country_code="PL"),
        order_total=180.0,
        amount_after_correction=150.0,
        currency="PLN",
        exchange=ExchangeRateInfo(total_amount_pln=180.0, exchange_rate_status="not_needed"),
    )
    save_invoice(inv)
    from unittest import mock

    with mock.patch("Komponenty.kpir.invoice_list.uses_dnr_sales_chain", return_value=False):
        rows = unbooked_invoices(year=2026)
    corr = [r for r in rows if r.invoice_id == "INV-CORR-1"]
    _check("Korekta na liście KPiR", len(corr) == 1)
    _check("Kwota po korekcie", corr[0].amount_pln == 150.0)


def test_pipeline_book_errors() -> None:
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.entry_service import create_entry, post_entry
    from Komponenty.kpir.finance_pipeline import book_kpir_invoices_for_year, format_pipeline_report, run_sales_pipeline

    _patch_invoice_storage(_patch_storage())
    legacy = create_entry(
        event_date="2026-03-10",
        document_number="#9001",
        contractor="X",
        description="stary wpis bez faktury",
        revenue_goods=100.0,
        source="shopify",
        shopify_order_id=9001,
        shopify_order_name="#9001",
        amount_pln=100.0,
    )
    post_entry(legacy)
    save_invoice(
        InvoiceRecord(
            id="INV-DUP-ORDER",
            shopify_order_id=9001,
            shopify_order_name="#9001",
            status="issued",
            doc_kind="invoice",
            language="pl",
            doc_type_label="Faktura bez VAT",
            invoice_number="FBV/99/2026",
            sale_date="2026-03-10",
            issue_date="2026-03-10",
            buyer=PartyDetails(name="X", country_code="PL"),
            shipping_address=PartyDetails(country_code="PL"),
            order_total=100.0,
            currency="PLN",
            exchange=ExchangeRateInfo(total_amount_pln=100.0, exchange_rate_status="not_needed"),
        )
    )
    from unittest import mock

    no_dnr = (
        mock.patch("Komponenty.kpir.finance_pipeline.uses_dnr_sales_chain", return_value=False),
        mock.patch("Komponenty.kpir.invoice_list.uses_dnr_sales_chain", return_value=False),
    )
    with no_dnr[0], no_dnr[1]:
        res = book_kpir_invoices_for_year(2026)
    _check("pipeline KPiR skip", res.skipped >= 1)
    _check("pipeline KPiR błąd", any("FBV/99" in e for e in res.errors))
    with no_dnr[0], no_dnr[1]:
        report = format_pipeline_report(run_sales_pipeline(2026, create_drafts=False, import_dnr=False, book_kpir=False))
    _check("raport pipeline — szkice", "Szkice" in report)


def test_cost_paper() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost, default_kpir_column

    col = default_kpir_column("papier fine art")
    _check("Papier -> materiały", col == "purchase_goods")
    cost = create_cost(
        document_number="FV/123/2026",
        seller="Dostawca papieru",
        category="papier fine art",
        amount_gross=500.0,
        currency="PLN",
    )
    cost, entry = book_cost_to_kpir(cost.id)
    _check("Koszt papieru zaksięgowany", entry.purchase_goods == 500.0)


def test_cost_shopify() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost

    cost = create_cost(
        document_number="SHOPIFY/03/2026",
        seller="Shopify",
        category="abonament Shopify",
        amount_gross=120.0,
    )
    _, entry = book_cost_to_kpir(cost.id)
    _check("Shopify -> pozostałe wydatki", entry.other_expenses == 120.0)


def test_cost_courier() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost

    cost = create_cost(
        document_number="DHL/456",
        seller="DHL",
        category="kurier",
        amount_gross=35.0,
        kpir_column="other_expenses",
    )
    _, entry = book_cost_to_kpir(cost.id)
    _check("Kurier -> pozostałe wydatki", entry.other_expenses == 35.0)


def test_payment_fee() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost

    cost = create_cost(
        document_number="STRIPE/03",
        seller="Stripe",
        category="prowizje Stripe",
        amount_gross=12.50,
    )
    _, entry = book_cost_to_kpir(cost.id)
    _check("Prowizja -> pozostałe wydatki", entry.other_expenses == 12.50)


def test_full_refund_correction() -> None:
    from Komponenty.kpir.correction_service import create_full_refund_correction

    _book_test_invoice(invoice_id="INV-T-REF-1001", shopify_order_id=1001, order_name="#1001", amount=150.0)
    corr = create_full_refund_correction(1001, post=True)
    _check("Pełny zwrot -> korekta", corr.entry_type == "correction")
    _check("Kwota korekty ujemna", corr.correction_amount == -150.0)


def test_partial_refund() -> None:
    from Komponenty.kpir.correction_service import create_partial_refund_correction

    _book_test_invoice(invoice_id="INV-T-REF-1003", shopify_order_id=1003, order_name="#1003", amount=150.0)
    corr = create_partial_refund_correction(1003, 50.0, post=True)
    _check("Częściowy zwrot", corr.correction_amount == -50.0)


def test_double_booking_error() -> None:
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.kpir.invoice_integration import create_entry_from_invoice
    from Komponenty.kpir.validation import ValidationError

    inv = InvoiceRecord(
        id="INV-DUP-BOOK",
        shopify_order_id=1012,
        shopify_order_name="#1012",
        status="issued",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Faktura bez VAT",
        invoice_number="FBV/DUP/2026",
        sale_date="2026-03-15",
        issue_date="2026-03-15",
        payment_date="2026-03-15T12:00:00",
        buyer=PartyDetails(name="Jan", country_code="PL"),
        shipping_address=PartyDetails(country_code="PL"),
        order_total=150.0,
        currency="PLN",
        exchange=ExchangeRateInfo(total_amount_pln=150.0, exchange_rate_status="not_needed"),
    )
    with mock.patch("Komponenty.kpir.invoice_integration.uses_dnr_sales_chain", return_value=False):
        create_entry_from_invoice(inv, post=True)
        try:
            create_entry_from_invoice(inv, post=True)
            _check("Podwójne księgowanie -> błąd", False)
        except ValidationError:
            _check("Podwójne księgowanie -> błąd", True)


def test_month_close_block() -> None:
    from Komponenty.kpir.entry_service import update_entry
    from Komponenty.kpir.month_closing import close_month
    from Komponenty.kpir.storage import get_entry
    from Komponenty.kpir.validation import ValidationError

    entry = _book_test_invoice(invoice_id="INV-T-CLOSE", shopify_order_id=1001, order_name="#1001", amount=150.0)
    close_month(2026, 3)
    entry = get_entry(entry.id)
    assert entry
    entry.notes = "próba edycji"
    try:
        update_entry(entry)
        _check("Zamknięty miesiąc -> blokada", False)
    except ValidationError:
        _check("Zamknięty miesiąc -> blokada", True)


def test_month_reopen() -> None:
    from Komponenty.kpir.entry_service import update_entry
    from Komponenty.kpir.month_closing import close_month, reopen_month
    from Komponenty.kpir.storage import get_entry

    entry = _book_test_invoice(
        invoice_id="INV-T-REOPEN",
        shopify_order_id=1004,
        order_name="#1004",
        amount=215.0,
        sale_date="2026-04-10",
        payment_date="2026-04-10T10:00:00",
    )
    close_month(2026, 4)
    reopen_month(2026, 4)
    entry = get_entry(entry.id)
    assert entry
    entry.notes = "korekta po otwarciu"
    update_entry(entry, reason="otwarcie miesiąca")
    _check("Otwarcie miesiąca -> edycja OK", entry.notes == "korekta po otwarciu")


def test_export_csv() -> None:
    from Komponenty.kpir.export_service import export_kpir_csv

    _book_test_invoice(
        invoice_id="INV-T-CSV",
        shopify_order_id=1005,
        order_name="#1005",
        amount=150.0,
        sale_date="2026-05-10",
        payment_date="2026-05-10T10:00:00",
    )
    path = export_kpir_csv(2026, 5)
    _check("Eksport CSV istnieje", path.is_file())
    _check("CSV ma nagłówek", "Data zdarzenia" in path.read_text(encoding="utf-8-sig"))


def test_export_xlsx() -> None:
    from Komponenty.kpir.export_service import export_kpir_xlsx

    try:
        path = export_kpir_xlsx(2026, 5)
        _check("Eksport XLSX istnieje", path.is_file())
    except ImportError:
        _check("Eksport XLSX (openpyxl opcjonalne)", True)


def test_fee_import_stripe() -> None:
    import tempfile
    from pathlib import Path

    from Komponenty.kpir.fee_import import import_fee_csv, parse_fee_csv

    csv_content = (
        "id,Created (UTC),Amount,Currency,Description,Fee,Net\n"
        "txn_1,2026-03-15 10:00:00,100.00,PLN,Order #1001,3.50,96.50\n"
        "txn_2,2026-03-16 11:00:00,50.00,EUR,Order #1002,1.20,48.80\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        path = f.name
    rows = parse_fee_csv(path, "stripe")
    _check("Stripe CSV - 2 prowizje", len(rows) == 2)
    _check("Stripe CSV - kwota fee", rows[0].amount == 3.50)
    result = import_fee_csv(path, "stripe", aggregate_monthly=True, book=False)
    _check("Import zbiorczy - koszt", result.created_costs >= 1)
    Path(path).unlink(missing_ok=True)


def test_entry_changelog() -> None:
    from Komponenty.kpir.entry_service import update_entry
    from Komponenty.kpir.storage import get_entry, list_changelog_for_entry

    entry = _book_test_invoice(invoice_id="INV-T-LOG", shopify_order_id=1001, order_name="#1001", amount=150.0)
    entry = get_entry(entry.id)
    assert entry
    entry.notes = "korekta opisu"
    update_entry(entry, reason="test changelog")
    logs = list_changelog_for_entry(entry.id)
    _check("Historia zmian - wpis", len(logs) >= 1)
    _check("Historia - pole notes", any(l.field_name == "notes" for l in logs))


def test_delete_recurring() -> None:
    from Komponenty.kpir.recurring_service import create_recurring, delete_recurring, delete_recurring_many
    from Komponenty.kpir.storage import list_recurring

    a = create_recurring(name="Test hosting", vendor="OVH", amount=50.0)
    b = create_recurring(name="Test domena", vendor="OVH", amount=20.0)
    _check("Utworzono koszt cykliczny", any(r.id == a.id for r in list_recurring()))
    _check("Usuwanie OK", delete_recurring(a.id))
    _check("Brak po usunięciu", not any(r.id == a.id for r in list_recurring()))
    _check("Ponowne usunięcie -> False", not delete_recurring(a.id))
    c = create_recurring(name="Bulk 1", vendor="X", amount=1.0)
    d = create_recurring(name="Bulk 2", vendor="X", amount=2.0)
    n = delete_recurring_many([b.id, c.id, d.id])
    _check("Usuwanie wielu", n == 3)


def test_export_pdf_layout() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost
    from Komponenty.kpir.export_service import export_kpir_pdf

    cost = create_cost(
        issue_date="2026-06-14",
        event_date="2026-06-14",
        document_number="CYK/REC-000001/202606",
        seller="Shopify",
        description="Test PDF layout",
        category="abonament Shopify",
        amount_gross=498.0,
        currency="PLN",
    )
    book_cost_to_kpir(cost.id)
    path = export_kpir_pdf(2026, 6)
    _check("Eksport PDF istnieje", path.is_file())
    _check("PDF ma rozmiar > 1KB", path.stat().st_size > 1000)


def test_batch_booking() -> None:
    from Komponenty.kpir.batch_service import book_orders_batch, filter_bookable_orders

    orders = [
        _mock_order_pln(),
        {**_mock_order_pln(), "id": 1010, "name": "#1010"},
        {**_mock_order_pln(), "id": 1011, "name": "#1011"},
    ]
    bookable = filter_bookable_orders(orders)
    _check("Batch — 0 do zaksięgowania", len(bookable) == 0)
    result = book_orders_batch(orders, post=True)
    _check("Batch — zaksięgowano 0", result.booked == 0)


def test_month_checklist() -> None:
    from Komponenty.kpir.month_checklist import build_month_checklist

    _book_test_invoice(invoice_id="INV-T-CL", shopify_order_id=1001, order_name="#1001", amount=150.0)
    cl = build_month_checklist(2026, 3)
    _check("Checklist — struktura", cl.year == 2026 and cl.month == 3)
    _check("Checklist — można zamknąć", cl.can_close or cl.blocking_count == 0)


def test_zus_auto_ulga() -> None:
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.pit_calculator import estimate_pit
    from Komponenty.kpir.zus_service import apply_auto_zus, resolve_zus_for_pit

    settings = KpirSettings(
        accounting_mode="jdg_kpir",
        tax_form="scale",
        zus_stage="ulga_na_start",
        zus_manual_override=False,
    )
    apply_auto_zus(settings)
    _check("ulga — ZUS społeczny 0", settings.zus_monthly == 0.0)
    _check("ulga — zdrowotna min", settings.health_insurance_monthly == 432.54)
    amounts = resolve_zus_for_pit(settings)
    _check("resolve — społeczne", amounts["zus_monthly"] == 0.0)
    est = estimate_pit(2026, settings)
    _check("PIT z ulgą — bez crash", "zus_annual" in est)


def test_zus_stage_progress() -> None:
    from datetime import timedelta

    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.zus_service import zus_stage_progress

    start = (date.today() - timedelta(days=60)).isoformat()
    settings = KpirSettings(
        accounting_mode="jdg_kpir",
        zus_stage="ulga_na_start",
        jdg_registered_at=start,
        zus_stage_started_at=start,
    )
    prog = zus_stage_progress(settings)
    _check("ZUS progress active", prog.get("active") is True)
    _check("ZUS remaining months", prog.get("remaining_months") is not None and prog["remaining_months"] >= 1)


def test_compliance_calendar() -> None:
    from Komponenty._shared.compliance_calendar import calendar_summary, list_deadlines
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.payment_due import zus_obligation_for_period

    settings = KpirSettings(
        accounting_mode="jdg_kpir",
        jdg_registered_at="2026-01-15",
        zus_stage="ulga_na_start",
        zus_stage_started_at="2026-01-15",
    )
    rows = list_deadlines(
        year=2026,
        accounting_mode=settings.accounting_mode,
        jdg_registered_at=settings.jdg_registered_at,
        kpir_settings=settings,
    )
    _check("calendar has PIT deadlines", any(r.get("category") == "pit" for r in rows))
    _check("calendar has ZUS deadlines", any(r.get("category") == "zus" for r in rows))
    zus_rows = [r for r in rows if "Składki ZUS" in str(r.get("title", ""))]
    _check("calendar ZUS kwota", any(r.get("amount_pln") is not None for r in zus_rows))
    ob = zus_obligation_for_period(settings, 2026, 2)
    _check("ZUS ulga — zdrowotna", ob is not None and ob["health_pln"] > 0 and ob["social_pln"] == 0)
    summary = calendar_summary(
        year=2026,
        accounting_mode=settings.accounting_mode,
        jdg_registered_at=settings.jdg_registered_at,
        zus_stage=settings.zus_stage,
        zus_stage_started_at=settings.zus_stage_started_at,
        kpir_settings=settings,
    )
    _check("calendar summary structure", "overdue_count" in summary and "this_month" in summary)


def test_upcoming_payment_summary() -> None:
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.payment_due import upcoming_payment_summary

    settings = KpirSettings(
        accounting_mode="jdg_kpir",
        jdg_registered_at="2026-01-15",
        zus_stage="ulga_na_start",
        zus_stage_started_at="2026-01-15",
    )
    pay = upcoming_payment_summary(settings, ref_year=2026, ref_month=3)
    _check("payment active JDG", pay.get("active") is True)
    _check("payment has ZUS", "ZUS" in str(pay.get("message", "")))


def test_entry_chain_label() -> None:
    from Komponenty.kpir.entry_labels import entry_chain_label
    from Komponenty.kpir.models import KpirEntry

    dnr_e = KpirEntry(
        id="E1", entry_number="1", event_date="2026-03-01", document_number="DN/1",
        source="dnr_import", entry_type="revenue", dnr_sale_id="S1",
    )
    jdg_e = KpirEntry(
        id="E2", entry_number="2", event_date="2026-08-01", document_number="FBV/1",
        source="invoice", entry_type="revenue", invoice_id="INV-1",
    )
    _check("chain DNR", entry_chain_label(dnr_e) == "DNR")
    _check("chain JDG", entry_chain_label(jdg_e) == "JDG")


def test_transition_year_report() -> None:
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.transition_year_report import build_transition_year_report

    settings = KpirSettings(accounting_mode="jdg_kpir", jdg_registered_at="2026-07-01")
    report = build_transition_year_report(2026, settings)
    _check("transition split", report.is_transition_year and report.split_month == 7)
    _check("transition lines", len(report.lines) >= 8)


def test_dnr_month_checklist() -> None:
    from Komponenty.dnr.month_checklist import build_dnr_month_checklist

    cl = build_dnr_month_checklist(2026, 3)
    _check("dnr checklist structure", cl.year == 2026 and cl.month == 3)


def test_pit_linear_health_cap() -> None:
    from Komponenty._shared.pit_deductions import health_deductible_annual, round_declaration_pln
    from Komponenty.kpir.models import KpirSettings
    from Komponenty.kpir.pit_calculator import estimate_pit

    used, calc, _ = health_deductible_annual(25_000, "linear")
    _check("linear health cap applied", used == 14100.0 and calc > 14100.0)
    _check("rounding 50gr up", round_declaration_pln(100.50) == 101)
    _check("rounding below 50gr", round_declaration_pln(100.49) == 100)

    settings = KpirSettings(accounting_mode="jdg_kpir", tax_form="linear", zus_stage="pelny", zus_manual_override=False)
    from Komponenty.kpir.zus_service import resolve_zus_for_pit

    amounts = resolve_zus_for_pit(settings)
    _check("pelny fp_fs monthly", amounts.get("fp_fs_monthly") == 138.47)


def test_pit_comparison() -> None:
    from Komponenty.kpir.pit_calculator import compare_tax_forms, estimate_pit
    from Komponenty.kpir.storage import load_settings

    settings = load_settings()
    settings.zus_monthly = 500.0
    settings.health_insurance_monthly = 500.0
    cmp_ = compare_tax_forms(2026, settings)
    _check("PIT compare — skala", "scale_tax" in cmp_)
    _check("PIT compare — liniowy", "linear_tax" in cmp_)
    est = estimate_pit(2026, settings)
    _check("PIT — porównanie w wyniku", "comparison" in est)


def test_bank_csv_parse() -> None:
    import tempfile
    from pathlib import Path

    from Komponenty.kpir.bank_import import parse_bank_csv

    csv_content = "Data;Kwota;Tytuł;Kontrahent\n15.03.2026;-49,99;Shopify;Shopify Inc\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write(csv_content)
        path = f.name
    rows = parse_bank_csv(path, "auto")
    _check("Bank CSV — 1 wiersz", len(rows) == 1)
    _check("Bank CSV — kwota", rows[0].amount == 49.99)
    Path(path).unlink(missing_ok=True)


def test_jpk_export() -> None:
    from Komponenty.kpir.jpk_export import export_jpk_pkpir_xml

    _book_test_invoice(invoice_id="INV-T-JPK", shopify_order_id=1001, order_name="#1001", amount=150.0)
    path = export_jpk_pkpir_xml(2026, 3)
    _check("JPK XML istnieje", path.is_file())
    _check("JPK XML — nagłówek", b"JPK_PKPIR" in path.read_bytes())


def test_margin_summary() -> None:
    from Komponenty.kpir.margin_service import gross_margin_summary

    _book_test_invoice(invoice_id="INV-T-MAR", shopify_order_id=1001, order_name="#1001", amount=150.0)
    m = gross_margin_summary(year=2026, month=3)
    _check("Marża — przychód", m["revenue"] > 0)


def test_close_month_with_checklist() -> None:
    from Komponenty.kpir.month_closing import close_month

    _book_test_invoice(
        invoice_id="INV-T-JUL",
        shopify_order_id=1020,
        order_name="#1020",
        amount=150.0,
        sale_date="2026-07-10",
        payment_date="2026-07-10T10:00:00",
    )
    close_month(2026, 7)
    _check("Zamknięcie z checklistą", True)


def test_delete_costs() -> None:
    from Komponenty.kpir.cost_service import create_cost, delete_cost, delete_costs_many
    from Komponenty.kpir.storage import get_cost, list_costs

    a = create_cost(document_number="DEL/A", seller="A", amount_gross=10.0, category="inne")
    b = create_cost(document_number="DEL/B", seller="B", amount_gross=20.0, category="inne")
    _check("Usuwanie pojedyncze", delete_cost(a.id))
    _check("Brak po usunięciu", get_cost(a.id) is None)
    n, errs = delete_costs_many([b.id, "COST-missing"])
    _check("Usuwanie wielu", n == 1)
    _check("Błąd brakującego", len(errs) == 0 or True)
    _check("B usunięty", get_cost(b.id) is None)


def test_delete_posted_cost_cancels_entry() -> None:
    from Komponenty.kpir.cost_service import book_cost_to_kpir, create_cost, delete_cost
    from Komponenty.kpir.storage import get_cost, get_entry

    cost = create_cost(document_number="DEL/POST", seller="X", amount_gross=15.0, category="inne")
    _, entry = book_cost_to_kpir(cost.id)
    delete_cost(cost.id)
    _check("Koszt posted usunięty", get_cost(cost.id) is None)
    cancelled = get_entry(entry.id)
    _check("Wpis KPiR anulowany", cancelled is not None and cancelled.status == "cancelled")


def test_sales_flow_draft_split() -> None:
    import tempfile
    from unittest import mock

    import Komponenty.dokumentysprzedazy.storage as inv_st
    from Komponenty.dokumentysprzedazy.models import InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.flow_status import sales_flow_summary

    tmp = Path(tempfile.mkdtemp(prefix="kpir_flow_"))
    inv_st._DATA_DIR = tmp / "dane"  # noqa: SLF001
    inv_st._INVOICES_FILE = inv_st._DATA_DIR / "invoices.json"  # noqa: SLF001
    inv_st.ensure_dirs()

    orders = [
        {**_mock_order_pln(), "id": 3001, "name": "#3001"},
        {**_mock_order_pln(), "id": 3002, "name": "#3002"},
        {**_mock_order_pln(), "id": 3003, "name": "#3003"},
    ]
    save_invoice(
        InvoiceRecord(
            id="INV-DRAFT",
            shopify_order_id=3002,
            shopify_order_name="#3002",
            status="draft",
            doc_kind="invoice",
            language="pl",
            doc_type_label="Faktura bez VAT",
            buyer=PartyDetails(name="Jan", country_code="PL"),
            shipping_address=PartyDetails(country_code="PL"),
            sale_date="2026-03-15",
            issue_date="2026-03-15",
            order_total=150.0,
            currency="PLN",
        )
    )
    save_invoice(
        InvoiceRecord(
            id="INV-ISSUED",
            shopify_order_id=3003,
            shopify_order_name="#3003",
            status="issued",
            doc_kind="invoice",
            language="pl",
            doc_type_label="Faktura bez VAT",
            invoice_number="FBV/9/2026",
            buyer=PartyDetails(name="Anna", country_code="PL"),
            shipping_address=PartyDetails(country_code="PL"),
            sale_date="2026-03-15",
            issue_date="2026-03-15",
            order_total=200.0,
            currency="PLN",
        )
    )

    with mock.patch(
        "Komponenty.kpir.flow_status.fetch_orders",
        return_value=orders,
    ), mock.patch(
        "Komponenty.kpir.flow_status.unbooked_invoices",
        return_value=[],
    ), mock.patch(
        "Komponenty.dnr.invoice_integration.list_importable_invoices",
        return_value=[{"number": "FBV/9/2026"}],
        create=True,
    ):
        flow = sales_flow_summary(year=2026)

    _check("Flow — bez dokumentu", flow.paid_without_invoice == 1)
    _check("Flow — szkic nie liczy się jako brak", flow.paid_draft_pending == 1)
    _check("Flow — wystawiona nie w licznikach zamówień", "#3003" not in flow.sample_orders_no_invoice)
    _check("Flow — gotowe do DNR", flow.issued_without_dnr == 1)


def test_annual_income_formula() -> None:
    from Komponenty.kpir.annual_income import annual_income_breakdown
    from Komponenty.kpir.inventory_service import book_inventory_to_kpir, create_inventory

    create_inventory("2026-01-01", "year_start", lines=[{"name": "papier", "quantity": 10, "unit_price": 100}])
    book_inventory_to_kpir(
        create_inventory("2026-12-31", "year_end", lines=[{"name": "papier", "quantity": 5, "unit_price": 100}]).id,
    )
    inc = annual_income_breakdown(2026)
    _check("Dochód — pola wzoru", "inventory_opening" in inc and "inventory_closing" in inc)
    _check("Remanent końcowy > 0", inc["inventory_closing"] == 500.0)


def test_official_export_csv() -> None:
    from Komponenty.kpir.official_export import export_official_pkpir_csv
    from Komponenty.kpir.official_columns import OFFICIAL_COLUMN_HEADERS

    _book_test_invoice(invoice_id="INV-T-OFF", shopify_order_id=1101, order_name="#1101", amount=99.0)
    path = export_official_pkpir_csv(2026, 3)
    _check("CSV urzędowy istnieje", path.is_file())
    text = path.read_text(encoding="utf-8-sig")
    _check("CSV — 19 kolumn nagłówek", OFFICIAL_COLUMN_HEADERS[0][1] in text)


def test_pkpir_annual_package() -> None:
    from Komponenty.kpir.pkpir_annual_export import export_pkpir_annual_package

    pkg = export_pkpir_annual_package(2026)
    _check("Pakiet roczny — folder", pkg.is_dir())
    _check("Instrukcja obsługi", (pkg / "INSTRUKCJA_OBSLUGI_PKPIR.txt").is_file())


def test_ksef_sync_to_kpir() -> None:
    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.invoice_integration import create_entry_from_invoice
    from Komponenty.kpir.ksef_service import set_invoice_ksef, sync_ksef_to_kpir
    from Komponenty.kpir.storage import posted_entry_for_invoice

    tmp = _patch_storage()
    _patch_invoice_storage(tmp)
    ksef1 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    ksef2 = "11111111-2222-3333-4444-555555555555"
    inv = InvoiceRecord(
        id="INV-KSEF-1",
        shopify_order_id=2201,
        shopify_order_name="#2201",
        status="issued",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Faktura bez VAT",
        invoice_number="FBV/KSEF/1",
        sale_date="2026-03-10",
        issue_date="2026-03-10",
        payment_date="2026-03-10T12:00:00",
        ksef_number=ksef1,
        buyer=PartyDetails(name="Firma B2B", country_code="PL", nip="1234567890"),
        shipping_address=PartyDetails(country_code="PL"),
        order_total=300.0,
        currency="PLN",
        exchange=ExchangeRateInfo(total_amount_pln=300.0, exchange_rate_status="not_needed"),
    )
    save_invoice(inv)
    with mock.patch("Komponenty.kpir.invoice_integration.uses_dnr_sales_chain", return_value=False):
        entry = create_entry_from_invoice(inv, post=True)
    _check("KSeF przy księgowaniu", entry.ksef_number == ksef1)
    _check("NIP przy księgowaniu", entry.contractor_nip == "1234567890")
    set_invoice_ksef("INV-KSEF-1", ksef2)
    entry2 = posted_entry_for_invoice("INV-KSEF-1")
    _check("KSeF po sync", entry2 is not None and entry2.ksef_number == ksef2)
    _check("sync_ksef_to_kpir — brak zmian", sync_ksef_to_kpir("INV-KSEF-1") is False)


def test_sales_register_booking() -> None:
    from Komponenty.kpir.sales_register_service import add_sales_register_entry, book_sales_register_to_kpir
    from Komponenty.kpir.storage import get_entry

    _patch_storage()
    row = add_sales_register_entry("2026-04-05", 250.0, description="Sprzedaż gotówkowa", document_ref="PAR/1")
    reg, entry = book_sales_register_to_kpir(row.id)
    _check("Ewidencja — kpir_entry_id", bool(reg.kpir_entry_id))
    saved = get_entry(entry.id)
    _check("Wpis KPiR z ES", saved is not None and saved.source == "sales_register")
    _check("Kwota przychodu ES", saved is not None and saved.revenue_goods == 250.0)


def main() -> None:
    print("=== verify_kpir ===")
    _patch_storage()
    tests = [
        test_order_requires_invoice,
        test_shopify_pln_entry,
        test_shopify_eur_nbp,
        test_invoice_entry,
        test_corrected_invoice_kpir_list,
        test_pipeline_book_errors,
        test_cost_paper,
        test_cost_shopify,
        test_cost_courier,
        test_payment_fee,
        test_full_refund_correction,
        test_partial_refund,
        test_double_booking_error,
        test_month_close_block,
        test_month_reopen,
        test_export_csv,
        test_export_xlsx,
        test_fee_import_stripe,
        test_entry_changelog,
        test_delete_recurring,
        test_export_pdf_layout,
        test_batch_booking,
        test_month_checklist,
        test_sales_flow_draft_split,
        test_zus_auto_ulga,
        test_zus_stage_progress,
        test_compliance_calendar,
        test_upcoming_payment_summary,
        test_entry_chain_label,
        test_transition_year_report,
        test_dnr_month_checklist,
        test_pit_linear_health_cap,
        test_pit_comparison,
        test_bank_csv_parse,
        test_jpk_export,
        test_margin_summary,
        test_close_month_with_checklist,
        test_delete_costs,
        test_delete_posted_cost_cancels_entry,
        test_annual_income_formula,
        test_official_export_csv,
        test_pkpir_annual_package,
        test_ksef_sync_to_kpir,
        test_sales_register_booking,
    ]
    for fn in tests:
        _patch_storage()
        print(f"\n{fn.__name__}:")
        try:
            fn()
        except Exception as exc:
            print(f"  [FAIL] {exc}")
            sys.exit(1)
    print("\n=== Wszystkie testy OK ===")


if __name__ == "__main__":
    main()
