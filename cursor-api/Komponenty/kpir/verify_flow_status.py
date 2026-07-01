"""Testy sales_flow_summary (rozdzielenie szkiców vs brak faktury)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest import mock


def _patch_invoice_storage(tmp: Path) -> None:
    import Komponenty.dokumentysprzedazy.storage as inv_st

    inv_st._DATA_DIR = tmp / "dane"  # noqa: SLF001
    inv_st._INVOICES_FILE = inv_st._DATA_DIR / "invoices.json"  # noqa: SLF001
    inv_st.ensure_dirs()


def _check(label: str, cond: bool) -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        raise AssertionError(label)


def _mock_order(oid: int, name: str) -> dict:
    return {
        "id": oid,
        "name": name,
        "currency": "PLN",
        "total_price": "150.00",
        "subtotal_price": "130.00",
        "total_discounts": "0.00",
        "financial_status": "paid",
        "processed_at": "2026-03-15T10:00:00+00:00",
        "created_at": "2026-03-15T09:00:00+00:00",
        "shipping_address": {"country_code": "PL", "name": "Jan"},
        "customer": {"first_name": "Jan", "last_name": "Kowalski"},
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from Komponenty.dokumentysprzedazy.models import InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.kpir.flow_status import sales_flow_summary

    tmp = Path(tempfile.mkdtemp(prefix="flow_test_"))
    _patch_invoice_storage(tmp)

    orders = [_mock_order(3001, "#3001"), _mock_order(3002, "#3002"), _mock_order(3003, "#3003")]
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

    with mock.patch("Komponenty.kpir.flow_status.fetch_orders", return_value=orders), mock.patch(
        "Komponenty.kpir.flow_status.unbooked_invoices",
        return_value=[],
    ), mock.patch(
        "Komponenty.dnr.invoice_integration.list_importable_invoices",
        return_value=[{"number": "FBV/9/2026"}],
        create=True,
    ):
        flow = sales_flow_summary(year=2026)

    _check("bez dokumentu", flow.paid_without_invoice == 1)
    _check("szkice osobno", flow.paid_draft_pending == 1)
    _check("gotowe do DNR", flow.issued_without_dnr == 1)
    print("verify_flow_status OK")


if __name__ == "__main__":
    main()
