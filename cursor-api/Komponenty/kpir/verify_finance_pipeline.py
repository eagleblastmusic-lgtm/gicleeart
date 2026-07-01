"""Testy finance_pipeline (raport błędów KPiR)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def _patch_kpir_storage(tmp: Path) -> None:
    import Komponenty.kpir.storage as st

    st._DATA_DIR = tmp / "kpir" / "dane"  # noqa: SLF001
    st._SETTINGS_FILE = st._DATA_DIR / "kpir_settings.json"  # noqa: SLF001
    st._DB_FILE = st._DATA_DIR / "kpir.json"  # noqa: SLF001
    st._CHANGELOG_FILE = st._DATA_DIR / "kpir_changelog.jsonl"  # noqa: SLF001
    st.ensure_dirs()


def _patch_invoice_storage(tmp: Path) -> None:
    import Komponenty.dokumentysprzedazy.storage as inv_st

    inv_st._DATA_DIR = tmp / "inv" / "dane"  # noqa: SLF001
    inv_st._INVOICES_FILE = inv_st._DATA_DIR / "invoices.json"  # noqa: SLF001
    inv_st.ensure_dirs()


def _check(label: str, cond: bool) -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        raise AssertionError(label)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    tmp = Path(tempfile.mkdtemp(prefix="pipe_test_"))
    _patch_kpir_storage(tmp)
    _patch_invoice_storage(tmp)

    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.entry_service import create_entry, post_entry
    from Komponenty.kpir.finance_pipeline import book_kpir_invoices_for_year, format_pipeline_report, run_sales_pipeline

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
            id="INV-DUP",
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
    _check("skip z błędem", res.skipped >= 1 and res.errors)
    with no_dnr[0], no_dnr[1]:
        report = format_pipeline_report(
            run_sales_pipeline(2026, create_drafts=False, import_dnr=False, book_kpir=False)
        )
    _check("raport zawiera szkice", "Szkice" in report)
    with mock.patch("Komponenty.kpir.finance_pipeline.uses_dnr_sales_chain", return_value=True):
        res_dnr = book_kpir_invoices_for_year(2026)
    _check("DNR: bez ujęcia faktur", res_dnr.booked == 0 and res_dnr.skipped == 0)
    print("verify_finance_pipeline OK")


if __name__ == "__main__":
    main()
