"""Testy modułu DNR."""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path


def _patch_storage(tmp: Path | None = None) -> Path:
    import Komponenty.dnr.storage as st

    d = tmp or Path(tempfile.mkdtemp(prefix="dnr_test_"))
    st._DATA_DIR = d / "dane"  # noqa: SLF001
    st._DOCUMENTS_DIR = d / "documents"  # noqa: SLF001
    st._SETTINGS_FILE = st._DATA_DIR / "dnr_settings.json"  # noqa: SLF001
    st._DB_FILE = st._DATA_DIR / "dnr.json"  # noqa: SLF001
    st.ensure_dirs()
    return d


def _patch_kpir_storage(tmp: Path) -> None:
    import Komponenty.kpir.storage as kst

    kst._DATA_DIR = tmp / "dane"  # noqa: SLF001
    kst._SETTINGS_FILE = kst._DATA_DIR / "kpir_settings.json"  # noqa: SLF001
    kst._DB_FILE = kst._DATA_DIR / "kpir.json"  # noqa: SLF001
    kst._CHANGELOG_FILE = kst._DATA_DIR / "kpir_changelog.jsonl"  # noqa: SLF001
    kst.ensure_dirs()


def _check(label: str, cond: bool) -> None:
    status = "OK" if cond else "FAIL"
    print(f"  [{status}] {label}")
    if not cond:
        raise AssertionError(label)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    tmp = _patch_storage()
    _patch_kpir_storage(tmp)
    from Komponenty.dnr.constants import DEFAULT_QUARTERLY_LIMIT, LEGACY_ANNUAL_LIMIT
    from Komponenty.dnr.entry_service import (
        create_cost,
        create_sale,
        delete_costs_many,
        delete_sale,
    )
    from Komponenty.dnr.export_service import export_year_csv
    from Komponenty.dnr.models import DnrSettings
    from Komponenty.dnr.storage import load_settings, save_settings
    from Komponenty.dnr.summary_service import (
        dashboard_summary,
        limit_status,
        quarter_limit_revenue,
        quarterly_breakdown,
        sale_limit_delta,
        year_limit_revenue,
    )

    from Komponenty.dnr.summary_service import quarter_from_month

    today = date.today()
    y = today.year
    q = quarter_from_month(today.month)
    mid_month = (q - 1) * 3 + 2
    sale_date = f"{y}-{mid_month:02d}-15"
    refund_date = f"{y}-{mid_month:02d}-20"

    print("DNR verify")
    save_settings(DnrSettings(owner_name="Test", quarterly_limit=1500.0))

    s1 = create_sale(event_date=sale_date, amount_pln=700, description="Sprzedaż A")
    s2 = create_sale(event_date=sale_date, amount_pln=500, description="Sprzedaż B")
    s_disc = create_sale(
        event_date=sale_date, list_price_pln=500, discount_pln=100, description="Obraz A3+",
    )
    _check("rabat — przychód należny 400", s_disc.amount_pln == 400.0)
    _check("rabat — cena i rabat zapisane", s_disc.list_price_pln == 500.0 and s_disc.discount_pln == 100.0)

    r1 = create_sale(event_date=refund_date, amount_pln=100, description="Zwrot", entry_kind="refund")
    _check("create_sale ids", bool(s1.id and s2.id and r1.id))
    _check("refund delta negative", sale_limit_delta(r1) == -100.0)

    qrev = quarter_limit_revenue(y, q)
    _check("quarter revenue net", qrev == 1500.0)

    c1 = create_cost(event_date=sale_date, amount_pln=50, category="materiały", description="Papier")
    _check("costs do not reduce limit", quarter_limit_revenue(y, q) == 1500.0)

    lim = limit_status(y, q)
    _check("quarter at cap", lim["remaining"] == 0.0 and lim["over_limit"] is False)

    create_sale(event_date=sale_date, amount_pln=1, description="Przekroczenie")
    lim_over = limit_status(y, q)
    _check("quarter limit over", lim_over["over_limit"] is True and lim_over["level"] == "over")
    _check("CEIDG warning when over", "CEIDG" in lim_over.get("ceidg_warning", ""))

    from .migration_service import find_limit_exceed_event, migration_overview

    event = find_limit_exceed_event(y)
    _check("migration event found", event is not None and event.get("excess_pln", 0) > 0)
    mig = migration_overview()
    _check("wizard needed after exceed", mig.get("wizard_needed") is True)
    _check("migration status required", mig["migration"]["status"] in ("required", "in_progress"))
    _check("first exceed stored", bool(mig["migration"].get("first_exceed_date")))

    quarters = quarterly_breakdown(y)
    _check("current quarter over in breakdown", quarters[q - 1]["over_limit"] is True)

    create_sale(event_date=refund_date, amount_pln=200, description="Zwrot po przekroczeniu", entry_kind="refund")
    _check("below limit after refund", quarter_limit_revenue(y, q) < 1500.0)
    _check("no current exceed event", find_limit_exceed_event(y) is None)
    mig_after = migration_overview()
    _check("wizard still needed after refund", mig_after.get("wizard_needed") is True)
    _check("manual review required", mig_after.get("manual_review_required") is True)
    _check("manual review alert", mig_after.get("manual_review_alert") is True)
    _check("first exceed preserved", mig_after["migration"]["first_exceed_date"] == mig["migration"]["first_exceed_date"])

    lim_refund = limit_status(y, q)
    _check("obligation after refund", lim_refund.get("obligation_active") is True)
    _check("obligation level", lim_refund.get("level") == "obligation")

    from .migration_service import MigrationCompleteError, acknowledge_manual_review, complete_migration

    try:
        complete_migration()
        _check("complete blocked without steps", False)
    except MigrationCompleteError:
        _check("complete blocked without steps", True)

    acknowledge_manual_review(note="Potwierdzam z księgowym — JDG od dnia przekroczenia")
    mig_ack = migration_overview()
    _check("alert cleared after ack", mig_ack.get("manual_review_alert") is False)
    _check("review flag still set", mig_ack.get("manual_review_required") is True)

    from .migration_service import revert_first_exceed

    revert_first_exceed(note="Zwrot cofnął przekroczenie — błędny wpis testowy")
    mig_rev = migration_overview()
    _check("revert clears first exceed", not mig_rev["migration"].get("first_exceed_date"))
    _check("revert clears wizard", mig_rev.get("wizard_needed") is False)
    _check("revert dismiss flag", bool(mig_rev["migration"].get("first_exceed_dismissed_at")))
    _check("obligation cleared", limit_status(y, q).get("obligation_active") is False)

    dash = dashboard_summary(y)
    _check("dashboard quarters", len(dash.get("quarters") or []) == 4)
    _check("dashboard quarter revenue", dash["quarter_revenue"] == quarter_limit_revenue(y, q))
    _check("dashboard obligation flag", dash.get("obligation_active") is False)

    from .limit_sync import save_canonical_quarterly_limit
    from Komponenty.kpir.storage import load_settings as load_kpir_settings

    save_canonical_quarterly_limit(1600.0)
    _check("canonical limit saved", load_settings().quarterly_limit == 1600.0)
    _check("kpir limit synced", load_kpir_settings().dnr_limit_quarterly == 1600.0)

    from Komponenty.kpir.dnr_tracker import dnr_status

    kpir_dnr = dnr_status(y, q)
    _check("kpir uses dnr ledger", kpir_dnr.get("source") == "dnr_ledger")
    _check("kpir same revenue", kpir_dnr.get("revenue") == quarter_limit_revenue(y, q))

    _check("delete_sale", delete_sale(s1.id) is True)
    _check("revenue after delete", quarter_limit_revenue(y, q) == 601.0)
    _check("year limit revenue", year_limit_revenue(y) == 601.0)

    _check("delete_costs_many", delete_costs_many([c1.id]) == 1)

    path = export_year_csv(y)
    _check("export csv exists", path.is_file())
    text = path.read_text(encoding="utf-8-sig")
    _check("export contains KWARTAŁY", "KWARTAŁY" in text)

    settings = load_settings()
    _check("settings quarterly limit", settings.quarterly_limit == 1600.0)

    migrated = DnrSettings.from_dict({"annual_limit": LEGACY_ANNUAL_LIMIT})
    _check("migration annual->quarterly", migrated.quarterly_limit == DEFAULT_QUARTERLY_LIMIT)

    mor_sale = create_sale(
        event_date=sale_date, amount_pln=999, source="allegro", merchant_of_record=True,
    )
    _check("MoR zero limit delta", sale_limit_delta(mor_sale) == 0.0)

    from .summary_service import monthly_guardrail_status
    gr = monthly_guardrail_status(y)
    _check("guardrail has limit", gr["guardrail"] == 3604.5)

    from Komponenty.kpir.storage import load_settings as load_kpir_settings, save_settings as save_kpir_settings
    from .kpir_import import import_dnr_to_kpir, preview_dnr_kpir_import

    kpir = load_kpir_settings()
    kpir.jdg_registered_at = sale_date
    kpir.accounting_mode = "jdg_kpir"
    save_kpir_settings(kpir)

    from .summary_service import pit_cash_revenue_for_year, sale_pit_cash_delta

    _check("pit cash before import", pit_cash_revenue_for_year(y) > 0)

    unpaid = create_sale(
        event_date=sale_date, amount_pln=500, description="Nieopłacona",
        payment_status="unpaid", amount_received_pln=0.0,
    )
    _check("unpaid zero pit cash", sale_pit_cash_delta(unpaid) == 0.0)
    _check("unpaid counts limit", sale_limit_delta(unpaid) == 500.0)

    pre = preview_dnr_kpir_import()
    _check("import preview actionable", pre.actionable >= 2)
    rev_before = quarter_limit_revenue(y, q)
    imp = import_dnr_to_kpir()
    _check("import ran", imp.imported_sales >= 2)
    _check("migrated excluded from limit", quarter_limit_revenue(y, q) < rev_before)
    _check("no duplicate second import", import_dnr_to_kpir().imported_sales == 0)

    from Komponenty.kpir.storage import list_entries, posted_entry_for_dnr_sale

    kpir_entries = [e for e in list_entries() if e.source == "dnr_import"]
    _check("kpir dnr_import entries", len(kpir_entries) >= 2)
    _check("dnr sale linked", posted_entry_for_dnr_sale(s2.id) is not None)

    from Komponenty.dnr.storage import get_sale
    from Komponenty._shared.vat_exemption import annual_turnover, turnover_from_dnr_sales

    vat = annual_turnover(y)
    dnr_to, dnr_rows = turnover_from_dnr_sales(y)
    _check("migrated sales out of vat dnr", all(not get_sale(r["id"]).migrated_to_kpir_at for r in dnr_rows))
    _check("post-jdg refunds migrated to kpir", dnr_to == 0.0)
    _check("kpir import in vat", vat["kpir_dnr_import_pln"] > 0)

    from .migration_service import set_migration_step

    for key, _ in (
        ("ceidg_submitted", ""),
        ("invoices_switched", ""),
        ("kpir_enabled", ""),
        ("zus_configured", ""),
    ):
        set_migration_step(key)
    _check("dnr_imported auto step", load_settings().migration["steps"]["dnr_imported"] is True)

    from .import_policy import invoices_module_available, is_jdg_active, shopify_dnr_import_blocked
    from Komponenty.kpir.storage import load_settings as load_kpir_settings, save_settings as save_kpir_settings

    blocked, msg = shopify_dnr_import_blocked()
    _check("import policy — moduł faktur blokuje Shopify", invoices_module_available() and blocked)
    _check("import policy — komunikat o fakturach", "Dokumenty sprzedaży" in msg)

    kpir = load_kpir_settings()
    kpir.jdg_registered_at = "2026-06-14"
    kpir.accounting_mode = "jdg_kpir"
    save_kpir_settings(kpir)
    _check("import policy — JDG aktywne", is_jdg_active())
    blocked_jdg, msg_jdg = shopify_dnr_import_blocked()
    _check("import policy — JDG nadal blokuje", blocked_jdg)
    _check("import policy — komunikat JDG", "JDG" in msg_jdg)

    from .shopify_integration import import_all_shopify_for_year, list_importable_shopify_orders

    _check("shopify list pusta przy blokadzie", list_importable_shopify_orders(2026) == [])
    imp, skip = import_all_shopify_for_year(2026)
    _check("shopify import 0 przy blokadzie", imp == 0 and skip == 0)

    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord, PartyDetails
    from Komponenty.dokumentysprzedazy.storage import save_invoice
    from Komponenty.dnr.invoice_integration import import_invoice
    from Komponenty.dnr.storage import get_sale

    inv_st = tmp / "inv" / "dane"
    import Komponenty.dokumentysprzedazy.storage as inv_mod

    inv_mod._DATA_DIR = inv_st  # noqa: SLF001
    inv_mod._INVOICES_FILE = inv_st / "invoices.json"  # noqa: SLF001
    inv_mod.ensure_dirs()
    save_invoice(
        InvoiceRecord(
            id="INV-DNR-DATE",
            shopify_order_id=0,
            shopify_order_name="",
            status="issued",
            doc_kind="invoice",
            language="pl",
            doc_type_label="Faktura bez VAT",
            invoice_number="FBV/DATE/2026",
            sale_date="2026-04-05",
            issue_date="2026-04-10",
            payment_date="2026-04-12T12:00:00",
            buyer=PartyDetails(name="A", country_code="PL"),
            shipping_address=PartyDetails(country_code="PL"),
            order_total=300.0,
            currency="PLN",
            exchange=ExchangeRateInfo(total_amount_pln=300.0, exchange_rate_status="not_needed"),
        )
    )
    ok, _ = import_invoice("INV-DNR-DATE")
    from Komponenty.dnr.storage import list_sales

    imported_sales = [s for s in list_sales() if s.invoice_id == "INV-DNR-DATE"]
    _check("DNR import faktury OK", ok and len(imported_sales) == 1)
    if imported_sales:
        s = imported_sales[0]
        _check("DNR event_date = sale_date", s.event_date == "2026-04-05")
        _check("DNR paid_at z payment_date", s.paid_at.startswith("2026-04-12"))

    print("All DNR tests passed.")


if __name__ == "__main__":
    main()
