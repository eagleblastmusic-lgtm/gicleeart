"""Testy licznika progu zwolnienia z VAT i tax_config 2026."""



from __future__ import annotations



import sys

import tempfile

from datetime import date

from pathlib import Path





def _patch_stores(tmp: Path) -> None:

    import Komponenty.dnr.storage as dnr_st

    import Komponenty.dokumentysprzedazy.storage as inv_st



    dnr_st._DATA_DIR = tmp / "dnr" / "dane"  # noqa: SLF001

    dnr_st._DOCUMENTS_DIR = tmp / "dnr" / "documents"  # noqa: SLF001

    dnr_st._SETTINGS_FILE = dnr_st._DATA_DIR / "dnr_settings.json"  # noqa: SLF001

    dnr_st._DB_FILE = dnr_st._DATA_DIR / "dnr.json"  # noqa: SLF001

    dnr_st.ensure_dirs()



    inv_st._DATA_DIR = tmp / "inv" / "dane"  # noqa: SLF001

    inv_st._DOCUMENTS_DIR = tmp / "inv" / "documents" / "invoices"  # noqa: SLF001

    inv_st._SETTINGS_FILE = inv_st._DATA_DIR / "invoice_settings.json"  # noqa: SLF001

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



    from Komponenty._shared.tax_config import (

        config_id,

        dnr_quarterly_limit,

        fp_fs_full,

        health_linear_annual_deduction_limit,

        maly_zus_plus,

        mpp_invoice_threshold,

        small_taxpayer,

        vat_exemption_threshold,

    )

    from Komponenty._shared.vat_prorata import activity_days_in_year, vat_prorata_threshold

    from Komponenty._shared.zus_stages import (

        maly_zus_plus_base_monthly,

        maly_zus_plus_eligibility,

        social_insurance_monthly,

        zus_stage_summary,

    )



    _check("tax_config id", config_id() == "PL-JDG-2026-06-14")

    _check("dnr quarterly limit", dnr_quarterly_limit() == 10813.5)

    _check("vat threshold", vat_exemption_threshold() == 240_000.0)

    _check("fp_fs_full", fp_fs_full() == 138.47)

    _check("health linear cap", health_linear_annual_deduction_limit() == 14100.0)

    _check("mpp threshold", mpp_invoice_threshold() == 15000.0)

    _check("maly zus plus config", maly_zus_plus().get("months_per_cycle") == 36)

    _check("small taxpayer ksef", small_taxpayer().get("ksef_monthly_gross_exemption_until_2026") == 10000.0)



    start = date(2026, 7, 10)

    days = activity_days_in_year(start, 2026)

    _check("prorata days jul10", days == 175)

    pr = vat_prorata_threshold("2026-07-10", 2026)

    _check("prorata applied", pr["prorata_applied"] is True)

    _check("prorata threshold ~115068", abs(pr["threshold_pln"] - 115068.49) < 1.0)



    elig = maly_zus_plus_eligibility(prior_year_income=80_000, prior_year_activity_days=365)

    _check("maly zus eligible", elig["eligible"] is True)

    base = maly_zus_plus_base_monthly(80_000)

    _check("maly zus base capped at max", base == 5652.0)

    social = social_insurance_monthly(zus_stage="maly_zus_plus", prior_year_income=80_000)

    _check("maly zus social > 0", social > 420.0)

    pelny = zus_stage_summary(zus_stage="pelny", tax_form="scale")

    _check("pelny includes fp_fs", pelny.get("fp_fs_monthly") == 138.47)



    tmp = Path(tempfile.mkdtemp(prefix="vat_test_"))

    _patch_stores(tmp)



    from Komponenty.dnr.entry_service import create_sale

    from Komponenty.dokumentysprzedazy.models import ExchangeRateInfo, InvoiceRecord

    from Komponenty.dokumentysprzedazy.storage import save_invoices_db as save_inv_db

    from Komponenty._shared.vat_exemption import vat_exemption_status



    inv = InvoiceRecord(

        id="INV-000001",

        shopify_order_id=0,

        shopify_order_name="",

        status="issued",

        doc_kind="invoice",

        language="pl",

        doc_type_label="Faktura bez VAT",

        invoice_number="FBV/1/2026",

        sale_date="2026-03-15",

        issue_date="2026-03-15",

        order_total=1000.0,

        exchange=ExchangeRateInfo(total_amount_pln=1000.0),

    )

    save_inv_db({"next_id": 2, "invoices": [inv.to_dict()]})



    st = vat_exemption_status(2026)

    _check("invoice turnover", st["invoice_turnover_pln"] == 1000.0)

    _check("total turnover", st["turnover_pln"] == 1000.0)



    create_sale(event_date="2026-04-01", amount_pln=200, description="Ręczna bez faktury")

    st2 = vat_exemption_status(2026)

    _check("dnr adds turnover", st2["turnover_pln"] == 1200.0)



    create_sale(

        event_date="2026-04-02",

        amount_pln=500,

        description="Allegro MoR",

        source="allegro",

        merchant_of_record=True,

    )

    st3 = vat_exemption_status(2026)

    _check("MoR excluded", st3["turnover_pln"] == 1200.0)



    st4 = vat_exemption_status(2026, jdg_registered_at="2026-07-10")

    _check("prorata in status", st4.get("prorata", {}).get("prorata_applied") is True)



    print("verify_vat_exemption: wszystkie testy OK")





if __name__ == "__main__":

    main()


