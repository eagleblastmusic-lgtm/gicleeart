"""Budowanie szkicu faktury z zamówienia Shopify."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from Komponenty._shared.shopify_tax_lines import line_amounts, order_line_totals

from .constants import (
    BUSINESS_MODE_DNR,
    DEFAULT_FOOTNOTES,
    SALES_CHANNEL_TEST,
)
from .country import is_eu_b2c, is_foreign_order, is_poland, suggest_language
from .i18n import (
    MARKET_DEFAULT_COUNTRY,
    PAYMENT_MANUAL,
    PRODUCT_PLACEHOLDER,
    SAMPLE_DATA,
    SHIPPING_LABEL,
    TEST_BUYER_NAME,
    TEST_LINE_ITEM,
    TEST_NOTE,
    all_default_footnotes_for_lang,
    default_footnote_text,
    doc_type_for_mode,
    is_polish_language,
    normalize_language,
    thank_you_footer,
)
from .order_attributes import (
    INVOICE_TYPE_COMPANY,
    parse_invoice_request,
    tax_id_label_for_country,
)
from .models import ExchangeRateInfo, InvoiceItem, InvoiceRecord, InvoiceSettings, PartyDetails, seller_display_name
from .nbp_service import convert_amounts_to_pln, fetch_rate_for_income_date, income_date_from_order, parse_iso_date
from .storage import new_invoice_id


def _party_from_address(addr: dict[str, Any] | None, email: str = "") -> PartyDetails:
    if not addr:
        return PartyDetails(email=email)
    lines = [
        str(addr.get("address1") or ""),
        str(addr.get("address2") or ""),
        " ".join(
            x for x in [
                str(addr.get("zip") or ""),
                str(addr.get("city") or ""),
                str(addr.get("province") or ""),
            ] if x
        ),
        str(addr.get("country") or ""),
    ]
    return PartyDetails(
        name=str(addr.get("name") or ""),
        email=email,
        address_lines="\n".join(x for x in lines if x.strip()),
        country_code=str(addr.get("country_code") or ""),
    )


def _float(val: Any) -> float:
    try:
        return float(val or 0)
    except (TypeError, ValueError):
        return 0.0


def _seller_thank_you(settings: InvoiceSettings, lang: str) -> str:
    code = normalize_language(lang)
    if code == "pl":
        saved = (settings.seller.thank_you_footer_pl or "").strip()
        return saved or thank_you_footer(code)
    saved = (settings.seller.thank_you_footer_en or "").strip()
    return saved or thank_you_footer(code)


def resolve_footnote(mode: str, saved: str, language: str) -> str:
    """Zwraca adnotację dla trybu — nadpisuje zapisaną, jeśli to nadal domyślny tekst innego trybu."""
    code = normalize_language(language)
    saved = (saved or "").strip()
    if saved and saved not in all_default_footnotes_for_lang(code):
        return saved
    key = mode if mode in DEFAULT_FOOTNOTES else BUSINESS_MODE_DNR
    return DEFAULT_FOOTNOTES[key].get(code) or default_footnote_text(key, code)


def default_footnote(settings: InvoiceSettings, language: str) -> str:
    seller = settings.seller
    mode = seller.business_mode or BUSINESS_MODE_DNR
    code = normalize_language(language)
    if code == "pl":
        return resolve_footnote(mode, seller.footnotes_pl, "pl")
    if code == "en":
        return resolve_footnote(mode, seller.footnotes_en, "en")
    return default_footnote_text(mode, code)


def doc_type_label_for(
    settings: InvoiceSettings,
    language: str,
    *,
    is_correction: bool = False,
) -> str:
    """Tytuł dokumentu — rachunek (DNR) lub faktura bez VAT (JDG)."""
    mode = settings.seller.business_mode or BUSINESS_MODE_DNR
    return doc_type_for_mode(mode, language, is_correction=is_correction)


def is_dnr_business_mode(mode: str) -> bool:
    return (mode or BUSINESS_MODE_DNR) == BUSINESS_MODE_DNR


def _enrich_buyer_from_invoice_request(
    buyer: PartyDetails,
    order: dict[str, Any],
    *,
    language: str,
) -> tuple[PartyDetails, bool, str]:
    """Nadpisuje nabywcę danymi z koszyka (firma / NIP). Zwraca (buyer, requested, type)."""
    info = parse_invoice_request(order)
    if not info.requested:
        return buyer, False, ""
    if info.customer_type == INVOICE_TYPE_COMPANY and info.company_name.strip():
        lines = [line for line in (buyer.address_lines or "").split("\n") if line.strip()]
        if info.tax_id.strip():
            label = tax_id_label_for_country(buyer.country_code, language=language)
            lines.append(f"{label}: {info.tax_id.strip()}")
        enriched = PartyDetails(
            name=info.company_name.strip(),
            email=buyer.email,
            address_lines="\n".join(lines),
            country_code=buyer.country_code,
        )
        return enriched, True, info.customer_type
    return buyer, True, info.customer_type or "private"


def build_draft_from_order(
    order: dict[str, Any],
    settings: InvoiceSettings,
    *,
    language: str | None = None,
    is_correction: bool = False,
    original: InvoiceRecord | None = None,
) -> InvoiceRecord:
    country = str((order.get("shipping_address") or {}).get("country_code") or "")
    lang = normalize_language(language or suggest_language(country))
    doc_type = doc_type_label_for(settings, lang, is_correction=is_correction)

    items: list[InvoiceItem] = []
    pos = 1
    taxes_included = bool(order.get("taxes_included"))
    line_totals = order_line_totals(order)
    for idx, li in enumerate(order.get("line_items") or []):
        lines = line_totals.get("lines") or []
        row = lines[idx] if idx < len(lines) else line_amounts(li, taxes_included=taxes_included)
        qty = _float(li.get("quantity"))
        amount = row["net"] if taxes_included else row["gross"]
        items.append(InvoiceItem(
            position=pos,
            name=str(li.get("name") or li.get("title") or "Produkt"),
            quantity=qty,
            unit_price=round(amount / qty, 2) if qty else _float(li.get("price")),
            discount=row["discount"],
            amount=round(amount, 2),
        ))
        pos += 1

    ship_amt = _float((order.get("total_shipping_price_set") or {}).get("shop_money", {}).get("amount"))
    if ship_amt > 0:
        items.append(InvoiceItem(
            position=pos,
            name=SHIPPING_LABEL[lang],
            quantity=1,
            unit_price=ship_amt,
            discount=0,
            amount=ship_amt,
            is_shipping=True,
        ))

    products_total = round(sum(i.amount for i in items if not i.is_shipping), 2)
    shipping_total = round(sum(i.amount for i in items if i.is_shipping), 2)
    discounts_total = round(_float(order.get("total_discounts")), 2)
    order_total = round(_float(order.get("total_price")), 2)
    currency = str(order.get("currency") or "PLN")

    payment_date = str(order.get("processed_at") or order.get("created_at") or "")
    sale_date = payment_date[:10] or date.today().isoformat()
    issue_date = date.today().isoformat()

    seller_party = PartyDetails(
        name=seller_display_name(settings.seller),
        email=settings.seller.email,
        address_lines=settings.seller.address,
        country_code="PL",
    )
    email = str(order.get("email") or "")
    buyer = _party_from_address(order.get("billing_address") or order.get("shipping_address"), email)
    buyer, inv_requested, inv_type = _enrich_buyer_from_invoice_request(buyer, order, language=lang)
    shipping = _party_from_address(order.get("shipping_address"), email)

    gateways = order.get("payment_gateway_names") or []
    payment_method = ", ".join(str(g) for g in gateways if g)

    income_d = income_date_from_order(payment_date, str(order.get("created_at") or ""))
    rate_info = fetch_rate_for_income_date(currency, income_d)
    pln = convert_amounts_to_pln(
        products=products_total,
        shipping=shipping_total,
        discounts=discounts_total,
        total=order_total,
        rate=float(rate_info.get("exchange_rate_value") or 1.0),
    )
    exchange = ExchangeRateInfo(
        original_currency=currency,
        exchange_rate_source=str(rate_info.get("exchange_rate_source") or ""),
        exchange_rate_table_number=str(rate_info.get("exchange_rate_table_number") or ""),
        exchange_rate_date=str(rate_info.get("exchange_rate_date") or ""),
        exchange_rate_value=float(rate_info.get("exchange_rate_value") or 1.0),
        exchange_rate_status=rate_info.get("exchange_rate_status") or "not_needed",
        **pln,
    )

    now = datetime.now().isoformat(timespec="seconds")
    fulfill_cc = "PL"
    for fl in order.get("fulfillments") or []:
        loc = fl.get("location") or {}
        cc = str(loc.get("country_code") or "").strip().upper()[:2]
        if cc:
            fulfill_cc = cc
            break
    record = InvoiceRecord(
        id=new_invoice_id(),
        shopify_order_id=int(order.get("id") or 0),
        shopify_order_name=str(order.get("name") or ""),
        status="draft",
        doc_kind="correction" if is_correction else "invoice",
        language=lang,
        doc_type_label=doc_type,
        issue_date=issue_date,
        sale_date=sale_date,
        payment_date="",
        seller=seller_party,
        buyer=buyer,
        shipping_address=shipping,
        items=items,
        products_total=products_total,
        shipping_total=shipping_total,
        discounts_total=discounts_total,
        order_total=order_total,
        currency=currency,
        payment_method=payment_method,
        footnote=default_footnote(settings, lang),
        thank_you_footer=_seller_thank_you(settings, lang),
        financial_status=str(order.get("financial_status") or ""),
        fulfillment_status=str(order.get("fulfillment_status") or "") or "unfulfilled",
        is_foreign=is_foreign_order(country),
        is_eu_b2c=is_eu_b2c(country),
        exchange=exchange,
        invoice_requested=inv_requested,
        invoice_customer_type=inv_type,
        taxes_included=taxes_included,
        total_tax=round(line_totals.get("tax_total") or _float(order.get("total_tax")), 2),
        fulfillment_country=fulfill_cc,
        products_total_net=round(line_totals.get("net_total") or products_total, 2),
        created_at=now,
        updated_at=now,
    )
    if is_correction and original:
        record.corrected_from_invoice_id = original.id
        record.correction_of_number = original.invoice_number
        record.amount_before_correction = original.order_total
        record.amount_after_correction = order_total
        record.correction_amount = round(order_total - original.order_total, 2)
    return record


def build_manual_draft(settings: InvoiceSettings, *, language: str | None = None) -> InvoiceRecord:
    """Szkic faktury bez powiązania z zamówieniem Shopify."""
    lang = normalize_language(language)
    today = date.today().isoformat()
    now = datetime.now().isoformat(timespec="seconds")
    doc_type = doc_type_label_for(settings, lang)
    currency = "PLN" if is_polish_language(lang) else "EUR"
    buyer_country = MARKET_DEFAULT_COUNTRY[lang]
    seller = PartyDetails(
        name=seller_display_name(settings.seller),
        email=settings.seller.email,
        address_lines=settings.seller.address,
        country_code="PL",
    )
    buyer = PartyDetails(country_code=buyer_country)
    rate_info = fetch_rate_for_income_date(currency, parse_iso_date(today) or date.today())
    pln = convert_amounts_to_pln(products=0, shipping=0, discounts=0, total=0, rate=float(rate_info.get("exchange_rate_value") or 1.0))
    exchange = ExchangeRateInfo(
        original_currency=currency,
        exchange_rate_source=str(rate_info.get("exchange_rate_source") or ""),
        exchange_rate_table_number=str(rate_info.get("exchange_rate_table_number") or ""),
        exchange_rate_date=str(rate_info.get("exchange_rate_date") or ""),
        exchange_rate_value=float(rate_info.get("exchange_rate_value") or 1.0),
        exchange_rate_status=rate_info.get("exchange_rate_status") or "not_needed",
        **pln,
    )
    return InvoiceRecord(
        id=new_invoice_id(),
        shopify_order_id=0,
        shopify_order_name="",
        status="draft",
        doc_kind="invoice",
        language=lang,
        doc_type_label=doc_type,
        issue_date=today,
        sale_date=today,
        payment_date=now,
        seller=seller,
        buyer=buyer,
        shipping_address=buyer,
        items=[InvoiceItem(1, PRODUCT_PLACEHOLDER[lang], 1, 0, 0, 0)],
        products_total=0,
        shipping_total=0,
        discounts_total=0,
        order_total=0,
        currency=currency,
        payment_method=PAYMENT_MANUAL[lang],
        footnote=default_footnote(settings, lang),
        thank_you_footer=_seller_thank_you(settings, lang),
        financial_status="paid",
        fulfillment_status="fulfilled",
        is_foreign=not is_poland(buyer_country),
        is_eu_b2c=is_eu_b2c(buyer_country),
        exchange=exchange,
        created_at=now,
        updated_at=now,
    )


def build_test_draft(settings: InvoiceSettings, *, language: str | None = None) -> InvoiceRecord:
    """Szkic faktury testowej — osobna numeracja TEST/TST, bez wpływu na ewidencję."""
    draft = build_manual_draft(settings, language=language)
    lang = draft.language
    amount = 123.00
    buyer_country = MARKET_DEFAULT_COUNTRY[lang]
    buyer_addr_samples = {
        "pl": "ul. Testowa 1\n00-001 Warszawa\nPL",
        "de": "Teststraße 1\n10115 Berlin\nDE",
        "fr": "1 rue Test\n75001 Paris\nFR",
        "es": "Calle Test 1\n28001 Madrid\nES",
        "nl": "Teststraat 1\n1012 AB Amsterdam\nNL",
        "it": "Via Test 1\n20121 Milano\nIT",
        "en": "Test Street 1\nSW1A 1AA London\nGB",
    }
    draft.buyer = PartyDetails(
        name=TEST_BUYER_NAME[lang],
        email="test@example.com",
        address_lines=buyer_addr_samples.get(lang, buyer_addr_samples["en"]),
        country_code=buyer_country,
    )
    draft.shipping_address = draft.buyer
    draft.items = [InvoiceItem(1, TEST_LINE_ITEM[lang], 1, amount, 0, amount)]
    draft.products_total = amount
    draft.order_total = amount
    draft.currency = "PLN" if is_polish_language(lang) else "EUR"
    draft.is_foreign = not is_poland(buyer_country)
    draft.is_eu_b2c = is_eu_b2c(buyer_country)
    draft.is_test = True
    draft.sales_channel = SALES_CHANNEL_TEST
    draft.payment_method = "Test"
    draft.footnote = f"{draft.footnote}\n{TEST_NOTE[lang]}".strip()
    draft = refresh_exchange_for_draft(draft)
    return draft


def refresh_exchange_for_draft(draft: InvoiceRecord) -> InvoiceRecord:
    rate_info = fetch_rate_for_income_date(
        draft.currency,
        parse_iso_date(draft.sale_date) or date.today(),
    )
    pln = convert_amounts_to_pln(
        products=draft.products_total,
        shipping=draft.shipping_total,
        discounts=draft.discounts_total,
        total=draft.order_total,
        rate=float(rate_info.get("exchange_rate_value") or 1.0),
    )
    draft.exchange = ExchangeRateInfo(
        original_currency=draft.currency,
        exchange_rate_source=str(rate_info.get("exchange_rate_source") or ""),
        exchange_rate_table_number=str(rate_info.get("exchange_rate_table_number") or ""),
        exchange_rate_date=str(rate_info.get("exchange_rate_date") or ""),
        exchange_rate_value=float(rate_info.get("exchange_rate_value") or 1.0),
        exchange_rate_status=rate_info.get("exchange_rate_status") or "not_needed",
        **pln,
    )
    return draft


def build_sample_invoice(settings: InvoiceSettings, *, language: str = "pl") -> InvoiceRecord:
    """Przykładowa faktura do podglądu PDF (ustawienia sprzedawcy)."""
    lang = normalize_language(language)
    today = date.today().isoformat()
    doc_type = doc_type_label_for(settings, lang)
    now = datetime.now().isoformat(timespec="seconds")
    seller = PartyDetails(
        name=seller_display_name(settings.seller),
        email=settings.seller.email,
        address_lines=settings.seller.address,
        country_code="PL",
    )
    sample = SAMPLE_DATA[lang]
    buyer = PartyDetails(
        name=str(sample["buyer_name"]),
        email=str(sample["buyer_email"]),
        address_lines=str(sample["buyer_addr"]),
        country_code=str(sample["country"]),
    )
    currency = str(sample["currency"])
    product_name = str(sample["product"])
    ship_name = SHIPPING_LABEL[lang]
    payment = str(sample["payment"])
    buyer_cc = str(sample["country"])

    items = [
        InvoiceItem(1, product_name, 1, 189.00, 10.00, 179.00),
        InvoiceItem(2, ship_name, 1, 14.99, 0, 14.99, is_shipping=True),
    ]
    products_total = 179.00
    shipping_total = 14.99
    order_total = 193.99

    return InvoiceRecord(
        id="preview-sample",
        shopify_order_id=0,
        shopify_order_name="#PODGLAD",
        status="draft",
        doc_kind="invoice",
        language=lang,
        doc_type_label=doc_type,
        invoice_number="PODGLĄD",
        issue_date=today,
        sale_date=today,
        payment_date=now,
        seller=seller,
        buyer=buyer,
        shipping_address=buyer,
        items=items,
        products_total=products_total,
        shipping_total=shipping_total,
        discounts_total=10.00,
        order_total=order_total,
        currency=currency,
        payment_method=payment,
        footnote=default_footnote(settings, lang),
        thank_you_footer=_seller_thank_you(settings, lang),
        financial_status="paid",
        fulfillment_status="fulfilled",
        is_foreign=not is_poland(buyer_cc),
        is_eu_b2c=is_eu_b2c(buyer_cc),
        business_mode=settings.seller.business_mode or BUSINESS_MODE_DNR,
        created_at=now,
        updated_at=now,
    )
