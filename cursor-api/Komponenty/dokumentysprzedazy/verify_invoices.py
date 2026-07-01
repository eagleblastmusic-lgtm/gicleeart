"""Testy modułu faktur bez VAT — python -m Komponenty.dokumentysprzedazy.verify_invoices"""

from __future__ import annotations

import sys
from datetime import date

from .country import is_poland, suggest_language
from .invoice_builder import build_draft_from_order, build_manual_draft, build_test_draft, default_footnote, resolve_footnote
from .constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG, DEFAULT_FOOTNOTES
from .order_attributes import (
    ATTR_COMPANY_NAME,
    ATTR_INVOICE_REQUESTED,
    ATTR_INVOICE_TYPE,
    ATTR_TAX_ID,
    parse_invoice_request,
)
from .models import InvoiceSettings, SellerSettings
from .nbp_service import (
    convert_amounts_to_pln,
    fetch_rate_for_income_date,
    income_date_from_order,
    last_business_day_before,
)
from .invoice_helpers import is_bookable_invoice, is_test_invoice
from .numbering import allocate_number, release_number_after_delete


def _minimal_invoice(**kwargs) -> "InvoiceRecord":
    from .models import InvoiceRecord

    base = dict(
        id="t1",
        shopify_order_id=0,
        shopify_order_name="",
        status="issued",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Faktura bez VAT",
        invoice_number="FBV/1/2026",
    )
    base.update(kwargs)
    return InvoiceRecord(**base)


def _check(label: str, cond: bool) -> None:
    print(f"{'OK' if cond else 'FAIL'} {label}")
    if not cond:
        sys.exit(1)


def test_language_detection() -> None:
    _check("PL -> pl", suggest_language("PL") == "pl")
    _check("DE -> de", suggest_language("DE") == "de")
    _check("FR -> fr", suggest_language("FR") == "fr")
    _check("ES -> es", suggest_language("ES") == "es")
    _check("NL -> nl", suggest_language("NL") == "nl")
    _check("IT -> it", suggest_language("IT") == "it")
    _check("GB -> en", suggest_language("GB") == "en")
    _check("US -> en", suggest_language("US") == "en")
    _check("is_poland", is_poland("PL"))


def test_pln_no_nbp() -> None:
    info = fetch_rate_for_income_date("PLN", date(2026, 3, 10))
    _check("PLN status", info["exchange_rate_status"] == "not_needed")
    _check("PLN rate 1", info["exchange_rate_value"] == 1.0)


def test_manual_rate() -> None:
    info = fetch_rate_for_income_date("EUR", date(2026, 3, 10), manual_rate=4.25)
    _check("manual status", info["exchange_rate_status"] == "manual")
    _check("manual rate", abs(info["exchange_rate_value"] - 4.25) < 1e-6)


def test_business_day_monday() -> None:
    monday = date(2026, 3, 9)
    prev = last_business_day_before(monday)
    _check("Monday -> Friday", prev.weekday() == 4 and prev.day == 6)


def test_income_date() -> None:
    d = income_date_from_order("2026-03-05T12:00:00Z", "2026-03-01T10:00:00Z")
    _check("payment date preferred", d == date(2026, 3, 5))


def test_numbering_unique() -> None:
    from .constants import BUSINESS_MODE_JDG
    from .models import SellerSettings

    s = InvoiceSettings(seller=SellerSettings(business_mode=BUSINESS_MODE_JDG))
    n1, s = allocate_number(s, language="pl", invoices=[])
    n2, s = allocate_number(s, language="pl", invoices=[])
    _check("unique numbers", n1 != n2)
    _check("format FBV", n1.startswith("FBV/"))


def test_dnr_number_format() -> None:
    from .constants import BUSINESS_MODE_DNR
    from .models import SellerSettings

    s = InvoiceSettings(seller=SellerSettings(business_mode=BUSINESS_MODE_DNR))
    s.numbering_dnr_pl.prefix = "DN"
    s.numbering_dnr_pl.format = "legacy"
    s.numbering_dnr_pl.year = 2026
    s.numbering_dnr_pl.next_number = 1
    num, s = allocate_number(s, language="pl", invoices=[])
    _check("DN format", num == "DN/1/2026")
    from .numbering import parse_invoice_number

    parsed = parse_invoice_number(num)
    _check("parse DN", parsed == ("DN", 1, 2026))


def test_separate_dnr_jdg_series() -> None:
    from .constants import BUSINESS_MODE_DNR, BUSINESS_MODE_JDG
    from .models import SellerSettings

    s = InvoiceSettings(seller=SellerSettings(business_mode=BUSINESS_MODE_JDG))
    s.numbering_pl.year = 2026
    s.numbering_pl.next_number = 1
    s.numbering_dnr_pl.year = 2026
    s.numbering_dnr_pl.next_number = 1
    s.numbering_dnr_pl.format = "legacy"
    n1, s = allocate_number(s, language="pl", invoices=[])
    s.seller.business_mode = BUSINESS_MODE_DNR
    n2, s = allocate_number(s, language="pl", invoices=[])
    _check("JDG first", n1 == "FBV/1/2026")
    _check("DNR separate", n2 == "DN/1/2026")
    s.seller.business_mode = BUSINESS_MODE_JDG
    n3, s = allocate_number(s, language="pl", invoices=[])
    _check("JDG continues", n3 == "FBV/2/2026")


def test_release_number_on_delete() -> None:
    from .constants import BUSINESS_MODE_JDG
    from .models import SellerSettings

    s = InvoiceSettings(seller=SellerSettings(business_mode=BUSINESS_MODE_JDG))
    n1, s = allocate_number(s, language="pl", invoices=[])
    n2, s = allocate_number(s, language="pl", invoices=[])
    _check("allocated two", n1 != n2)
    inv_high = _minimal_invoice(id="high", invoice_number=n2)
    released, s = release_number_after_delete(s, inv_high, other_invoices=[])
    _check("released highest", released)
    n3, s = allocate_number(s, language="pl", invoices=[])
    _check("reuses released number", n3 == n2)

    inv_low = _minimal_invoice(id="low", invoice_number=n1)
    inv_high2 = _minimal_invoice(id="high2", invoice_number=n2)
    released2, s = release_number_after_delete(
        s, inv_low, other_invoices=[inv_high2]
    )
    _check("no release when higher remains", not released2)


def test_draft_from_orders() -> None:
    settings = InvoiceSettings(
        seller=SellerSettings(name="Test Seller", address="ul. Test 1", business_mode=BUSINESS_MODE_JDG),
    )
    pl_order = {
        "id": 1001, "name": "#1001", "created_at": "2026-03-01T10:00:00Z",
        "processed_at": "2026-03-01T11:00:00Z", "financial_status": "paid",
        "fulfillment_status": "fulfilled", "email": "a@b.pl", "currency": "PLN",
        "subtotal_price": "100.00", "total_discounts": "0.00", "total_price": "114.99",
        "total_shipping_price_set": {"shop_money": {"amount": "14.99"}},
        "shipping_address": {"country_code": "PL", "name": "Jan Kowalski", "city": "Warszawa"},
        "line_items": [{"name": "Obraz", "quantity": 1, "price": "100.00", "total_discount": "0"}],
        "payment_gateway_names": ["shopify_payments"],
    }
    de_order = {**pl_order, "id": 1002, "name": "#1002", "currency": "EUR",
                "shipping_address": {"country_code": "DE", "name": "Hans", "city": "Berlin"}}
    fr_order = {**pl_order, "id": 1003, "name": "#1003", "currency": "EUR",
                "shipping_address": {"country_code": "FR", "name": "Marie", "city": "Paris"}}
    pl = build_draft_from_order(pl_order, settings)
    de = build_draft_from_order(de_order, settings)
    fr = build_draft_from_order(fr_order, settings)
    _check("PL doc type", pl.doc_type_label == "Faktura bez VAT")
    _check("DE doc type", de.doc_type_label == "Rechnung ohne USt.")
    _check("FR doc type", fr.doc_type_label == "Facture sans TVA")
    _check("DE language", de.language == "de")
    _check("not VAT invoice", "VAT Invoice" not in de.doc_type_label)
    _check("PLN exchange", pl.exchange.exchange_rate_value == 1.0)


def test_dnr_draft_doc_type() -> None:
    settings = InvoiceSettings(seller=SellerSettings(name="Test", address="Adres", business_mode=BUSINESS_MODE_DNR))
    from .constants import DOC_TYPE_DNR_PL

    draft = build_manual_draft(settings, language="pl")
    _check("DNR PL rachunek", draft.doc_type_label == DOC_TYPE_DNR_PL)


def test_invoice_request_attributes() -> None:
    order = {
        "note_attributes": [
            {"name": ATTR_INVOICE_REQUESTED, "value": "yes"},
            {"name": ATTR_INVOICE_TYPE, "value": "company"},
            {"name": ATTR_COMPANY_NAME, "value": "Acme Sp. z o.o."},
            {"name": ATTR_TAX_ID, "value": "5250000000"},
        ],
        "shipping_address": {"country_code": "PL", "name": "Jan", "city": "Warszawa"},
        "email": "jan@example.com",
    }
    info = parse_invoice_request(order)
    _check("invoice requested", info.requested)
    _check("invoice company", info.customer_type == "company")
    settings = InvoiceSettings()
    draft = build_draft_from_order({**order, **{
        "id": 2001, "name": "#2001", "currency": "PLN", "total_price": "100",
        "subtotal_price": "100", "total_discounts": "0",
        "total_shipping_price_set": {"shop_money": {"amount": "0"}},
        "line_items": [{"name": "X", "quantity": 1, "price": "100", "total_discount": "0"}],
        "payment_gateway_names": [],
    }}, settings)
    _check("buyer company name", draft.buyer.name == "Acme Sp. z o.o.")
    _check("buyer nip line", "5250000000" in draft.buyer.address_lines)
    _check("invoice flagged", draft.invoice_requested)


def test_convert_pln() -> None:
    r = convert_amounts_to_pln(products=100, shipping=10, discounts=5, total=105, rate=4.0)
    _check("products pln", r["products_amount_pln"] == 400.0)
    _check("total pln", r["total_amount_pln"] == 420.0)


def test_manual_draft() -> None:
    settings = InvoiceSettings(
        seller=SellerSettings(name="Test", address="Adres", business_mode=BUSINESS_MODE_JDG),
    )
    draft = build_manual_draft(settings, language="pl")
    _check("manual id", bool(draft.id))
    _check("manual no shopify", draft.shopify_order_id == 0)
    _check("manual PL doc", draft.doc_type_label == "Faktura bez VAT")
    draft_de = build_manual_draft(settings, language="de")
    _check("manual DE doc", draft_de.doc_type_label == "Rechnung ohne USt.")


def test_test_draft() -> None:
    settings = InvoiceSettings(seller=SellerSettings(name="Test", address="Adres"))
    draft = build_test_draft(settings, language="pl")
    _check("test flag", draft.is_test)
    _check("test channel", draft.sales_channel == "test")
    _check("test buyer", "[TEST]" in draft.buyer.name)
    _check("test amount", draft.order_total == 123.0)
    _check("draft not bookable", not is_bookable_invoice(draft))
    issued_test = build_test_draft(settings, language="pl")
    issued_test.status = "issued"
    _check("issued test bookable", is_bookable_invoice(issued_test))
    s = InvoiceSettings()
    num, s = allocate_number(s, language="pl", is_test=True)
    _check("test number prefix", num.startswith("TEST/"))


def test_footnote_follows_business_mode() -> None:
    settings = InvoiceSettings(seller=SellerSettings(
        business_mode=BUSINESS_MODE_JDG,
        footnotes_pl=DEFAULT_FOOTNOTES[BUSINESS_MODE_DNR]["pl"],
        footnotes_en=DEFAULT_FOOTNOTES[BUSINESS_MODE_DNR]["en"],
    ))
    _check("JDG PL", default_footnote(settings, "pl") == DEFAULT_FOOTNOTES[BUSINESS_MODE_JDG]["pl"])
    _check("JDG EN", default_footnote(settings, "en") == DEFAULT_FOOTNOTES[BUSINESS_MODE_JDG]["en"])
    custom = "Własna adnotacja użytkownika."
    _check(
        "custom kept",
        resolve_footnote(BUSINESS_MODE_JDG, custom, "pl") == custom,
    )


def test_order_confirmation_eta() -> None:
    from .email_compose import order_confirmation_body, production_eta_line

    body = order_confirmation_body("#1001", language="pl", production_days=3)
    _check("PL eta body", "do realizacji" in body and "3 dni" in body)
    _check("PL eta line", production_eta_line("pl", 1) == "Szacowany czas produkcji obrazu: 1 dzień.")
    _check("EN eta line", "1 day" in production_eta_line("en", 1))
    body_de = order_confirmation_body("#1001", language="de", production_days=5)
    _check("DE eta body", "5 Tage" in body_de)


def test_dnr_receipt_no_seller_nip() -> None:
    """Rachunek DNR — bez NIP sprzedawcy na PDF (00115)."""
    from .i18n import pdf_header_labels
    from .pdf_fonts import register_invoice_fonts
    from .pdf_generator import _seller_paragraphs, _styles
    from .models import InvoiceRecord, PartyDetails, SellerSettings

    reg, bold = register_invoice_fonts()
    labels = pdf_header_labels("pl", dnr=True)
    st = _styles(reg, bold)
    settings = SellerSettings(
        name="Giclee",
        owner_name="Jan Kowalski",
        address="ul. Test 1",
        nip="1234567890",
        phone="500600700",
        email="a@b.pl",
        business_mode=BUSINESS_MODE_DNR,
    )
    invoice = InvoiceRecord(
        id="t1",
        shopify_order_id=0,
        shopify_order_name="",
        status="draft",
        doc_kind="invoice",
        language="pl",
        doc_type_label="Rachunek",
        seller=PartyDetails(name="Jan Kowalski", address_lines="ul. Test 1", email="a@b.pl"),
        buyer=PartyDetails(name="Klient"),
        business_mode=BUSINESS_MODE_DNR,
    )
    lines = _seller_paragraphs(labels, invoice, settings, st)
    text = " ".join(getattr(p, "text", "") for p in lines)
    _check("brak NIP sprzedawcy", "NIP" not in text and "1234567890" not in text)
    _check("jest imię", "Jan Kowalski" in text)


def main() -> None:
    print("--- Dokumenty sprzedaży: testy ---")
    test_language_detection()
    test_pln_no_nbp()
    test_manual_rate()
    test_business_day_monday()
    test_income_date()
    test_numbering_unique()
    test_dnr_number_format()
    test_separate_dnr_jdg_series()
    test_release_number_on_delete()
    test_draft_from_orders()
    test_dnr_draft_doc_type()
    test_dnr_receipt_no_seller_nip()
    test_invoice_request_attributes()
    test_manual_draft()
    test_test_draft()
    test_footnote_follows_business_mode()
    test_order_confirmation_eta()
    test_convert_pln()
    print("Wszystkie testy OK.")


if __name__ == "__main__":
    main()
