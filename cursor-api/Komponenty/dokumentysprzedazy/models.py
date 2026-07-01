"""Modele danych faktur bez VAT."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .i18n import InvoiceLanguage  # noqa: F401 — re-export
InvoiceStatus = Literal["not_issued", "issued", "corrected", "cancelled", "draft"]
InvoiceDocKind = Literal["invoice", "correction"]
ExchangeRateStatus = Literal["fetched", "manual", "missing", "error", "not_needed"]
BusinessMode = Literal["dnr", "jdg_vat_exempt"]


@dataclass
class SellerSettings:
    name: str = ""
    owner_name: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""
    nip: str = ""
    logo_path: str = ""
    business_mode: BusinessMode = "dnr"
    footnotes_pl: str = ""
    footnotes_en: str = ""
    thank_you_footer_pl: str = "Dziękujemy za zakup."
    thank_you_footer_en: str = "Thank you for your purchase."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> SellerSettings:
        if not data:
            return cls()
        return cls(
            name=str(data.get("name") or ""),
            owner_name=str(data.get("owner_name") or ""),
            address=str(data.get("address") or ""),
            email=str(data.get("email") or ""),
            phone=str(data.get("phone") or ""),
            website=str(data.get("website") or ""),
            nip=str(data.get("nip") or ""),
            logo_path=str(data.get("logo_path") or ""),
            business_mode=data.get("business_mode") or "dnr",
            footnotes_pl=str(data.get("footnotes_pl") or ""),
            footnotes_en=str(data.get("footnotes_en") or ""),
            thank_you_footer_pl=str(data.get("thank_you_footer_pl") or "Dziękujemy za zakup."),
            thank_you_footer_en=str(data.get("thank_you_footer_en") or "Thank you for your purchase."),
        )


def seller_display_name(seller: SellerSettings) -> str:
    """Nazwa firmy + imię i nazwisko właściciela (osobne linie na fakturze)."""
    biz = (seller.name or "").strip()
    owner = (seller.owner_name or "").strip()
    if biz and owner:
        return f"{biz}\n{owner}"
    return biz or owner


@dataclass
class NumberingSeries:
    prefix: str = "FBV"
    next_number: int = 1
    year: int = 2026
    used_numbers: list[str] = field(default_factory=list)
    format: str = "legacy"  # legacy: PREFIX/n/rok (FBV, DN, KDN — ten sam styl)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prefix": self.prefix,
            "next_number": self.next_number,
            "year": self.year,
            "used_numbers": list(self.used_numbers),
            "format": self.format,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> NumberingSeries:
        if not data:
            return cls()
        used = data.get("used_numbers") or []
        return cls(
            prefix=str(data.get("prefix") or "FBV"),
            next_number=int(data.get("next_number") or 1),
            year=int(data.get("year") or 2026),
            used_numbers=[str(x) for x in used],
            format=str(data.get("format") or "legacy"),
        )


@dataclass
class InvoiceSettings:
    seller: SellerSettings = field(default_factory=SellerSettings)
    numbering_pl: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="FBV"))
    numbering_dnr_pl: NumberingSeries = field(
        default_factory=lambda: NumberingSeries(prefix="DN", format="legacy"),
    )
    numbering_en: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="INV"))
    numbering_dnr_en: NumberingSeries = field(
        default_factory=lambda: NumberingSeries(prefix="DN-INV", format="legacy"),
    )
    numbering_correction_pl: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="KOR"))
    numbering_dnr_correction_pl: NumberingSeries = field(
        default_factory=lambda: NumberingSeries(prefix="KDN", format="legacy"),
    )
    numbering_correction_en: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="COR"))
    numbering_dnr_correction_en: NumberingSeries = field(
        default_factory=lambda: NumberingSeries(prefix="KDN-INV", format="legacy"),
    )
    numbering_test_pl: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="TEST"))
    numbering_test_en: NumberingSeries = field(default_factory=lambda: NumberingSeries(prefix="TST"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "seller": self.seller.to_dict(),
            "numbering_pl": self.numbering_pl.to_dict(),
            "numbering_dnr_pl": self.numbering_dnr_pl.to_dict(),
            "numbering_en": self.numbering_en.to_dict(),
            "numbering_dnr_en": self.numbering_dnr_en.to_dict(),
            "numbering_correction_pl": self.numbering_correction_pl.to_dict(),
            "numbering_dnr_correction_pl": self.numbering_dnr_correction_pl.to_dict(),
            "numbering_correction_en": self.numbering_correction_en.to_dict(),
            "numbering_test_pl": self.numbering_test_pl.to_dict(),
            "numbering_test_en": self.numbering_test_en.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> InvoiceSettings:
        if not data:
            return cls()
        return cls(
            seller=SellerSettings.from_dict(data.get("seller")),
            numbering_pl=NumberingSeries.from_dict(data.get("numbering_pl")),
            numbering_dnr_pl=NumberingSeries.from_dict(
                data.get("numbering_dnr_pl") or {"prefix": "DN", "format": "legacy"},
            ),
            numbering_en=NumberingSeries.from_dict(data.get("numbering_en")),
            numbering_dnr_en=NumberingSeries.from_dict(
                data.get("numbering_dnr_en") or {"prefix": "DN-INV", "format": "legacy"},
            ),
            numbering_correction_pl=NumberingSeries.from_dict(data.get("numbering_correction_pl")),
            numbering_dnr_correction_pl=NumberingSeries.from_dict(
                data.get("numbering_dnr_correction_pl") or {"prefix": "KDN", "format": "legacy"},
            ),
            numbering_correction_en=NumberingSeries.from_dict(data.get("numbering_correction_en")),
            numbering_dnr_correction_en=NumberingSeries.from_dict(
                data.get("numbering_dnr_correction_en") or {"prefix": "KDN-INV", "format": "legacy"},
            ),
            numbering_test_pl=NumberingSeries.from_dict(data.get("numbering_test_pl") or {"prefix": "TEST"}),
            numbering_test_en=NumberingSeries.from_dict(data.get("numbering_test_en") or {"prefix": "TST"}),
        )


@dataclass
class InvoiceItem:
    position: int
    name: str
    quantity: float
    unit_price: float
    discount: float
    amount: float
    is_shipping: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvoiceItem:
        return cls(
            position=int(data.get("position") or 0),
            name=str(data.get("name") or ""),
            quantity=float(data.get("quantity") or 0),
            unit_price=float(data.get("unit_price") or 0),
            discount=float(data.get("discount") or 0),
            amount=float(data.get("amount") or 0),
            is_shipping=bool(data.get("is_shipping")),
        )


@dataclass
class PartyDetails:
    name: str = ""
    email: str = ""
    address_lines: str = ""
    country_code: str = ""
    nip: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PartyDetails:
        if not data:
            return cls()
        return cls(
            name=str(data.get("name") or ""),
            email=str(data.get("email") or ""),
            address_lines=str(data.get("address_lines") or ""),
            country_code=str(data.get("country_code") or ""),
            nip=str(data.get("nip") or ""),
        )


@dataclass
class ExchangeRateInfo:
    original_currency: str = "PLN"
    exchange_rate_source: str = "NBP"
    exchange_rate_table_number: str = ""
    exchange_rate_date: str = ""
    exchange_rate_value: float = 1.0
    exchange_rate_status: ExchangeRateStatus = "not_needed"
    products_amount_pln: float = 0.0
    shipping_amount_pln: float = 0.0
    discounts_amount_pln: float = 0.0
    total_amount_pln: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ExchangeRateInfo:
        if not data:
            return cls()
        return cls(
            original_currency=str(data.get("original_currency") or "PLN"),
            exchange_rate_source=str(data.get("exchange_rate_source") or "NBP"),
            exchange_rate_table_number=str(data.get("exchange_rate_table_number") or ""),
            exchange_rate_date=str(data.get("exchange_rate_date") or ""),
            exchange_rate_value=float(data.get("exchange_rate_value") or 1.0),
            exchange_rate_status=data.get("exchange_rate_status") or "not_needed",
            products_amount_pln=float(data.get("products_amount_pln") or 0),
            shipping_amount_pln=float(data.get("shipping_amount_pln") or 0),
            discounts_amount_pln=float(data.get("discounts_amount_pln") or 0),
            total_amount_pln=float(data.get("total_amount_pln") or 0),
        )


@dataclass
class InvoiceRecord:
    id: str
    shopify_order_id: int
    shopify_order_name: str
    status: InvoiceStatus
    doc_kind: InvoiceDocKind
    language: InvoiceLanguage
    doc_type_label: str
    invoice_number: str = ""
    issue_date: str = ""
    sale_date: str = ""
    payment_date: str = ""
    ksef_number: str = ""
    seller: PartyDetails = field(default_factory=PartyDetails)
    buyer: PartyDetails = field(default_factory=PartyDetails)
    shipping_address: PartyDetails = field(default_factory=PartyDetails)
    items: list[InvoiceItem] = field(default_factory=list)
    products_total: float = 0.0
    shipping_total: float = 0.0
    discounts_total: float = 0.0
    order_total: float = 0.0
    currency: str = "PLN"
    payment_method: str = ""
    footnote: str = ""
    thank_you_footer: str = ""
    pdf_path: str = ""
    locked: bool = False
    sent_to_customer: bool = False
    is_foreign: bool = False
    is_eu_b2c: bool = False
    financial_status: str = ""
    fulfillment_status: str = ""
    corrected_from_invoice_id: str = ""
    correction_of_number: str = ""
    amount_before_correction: float = 0.0
    correction_amount: float = 0.0
    amount_after_correction: float = 0.0
    exchange: ExchangeRateInfo = field(default_factory=ExchangeRateInfo)
    invoice_requested: bool = False
    invoice_customer_type: str = ""
    sales_channel: str = ""
    is_test: bool = False
    business_mode: BusinessMode = "dnr"
    merchant_of_record: bool = False
    taxes_included: bool = False
    total_tax: float = 0.0
    fulfillment_country: str = "PL"
    products_total_net: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "shopify_order_id": self.shopify_order_id,
            "shopify_order_name": self.shopify_order_name,
            "status": self.status,
            "doc_kind": self.doc_kind,
            "language": self.language,
            "doc_type_label": self.doc_type_label,
            "invoice_number": self.invoice_number,
            "issue_date": self.issue_date,
            "sale_date": self.sale_date,
            "payment_date": self.payment_date,
            "ksef_number": self.ksef_number,
            "seller": self.seller.to_dict(),
            "buyer": self.buyer.to_dict(),
            "shipping_address": self.shipping_address.to_dict(),
            "items": [i.to_dict() for i in self.items],
            "products_total": self.products_total,
            "shipping_total": self.shipping_total,
            "discounts_total": self.discounts_total,
            "order_total": self.order_total,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "footnote": self.footnote,
            "thank_you_footer": self.thank_you_footer,
            "pdf_path": self.pdf_path,
            "locked": self.locked,
            "sent_to_customer": self.sent_to_customer,
            "is_foreign": self.is_foreign,
            "is_eu_b2c": self.is_eu_b2c,
            "financial_status": self.financial_status,
            "fulfillment_status": self.fulfillment_status,
            "corrected_from_invoice_id": self.corrected_from_invoice_id,
            "correction_of_number": self.correction_of_number,
            "amount_before_correction": self.amount_before_correction,
            "correction_amount": self.correction_amount,
            "amount_after_correction": self.amount_after_correction,
            "exchange": self.exchange.to_dict(),
            "invoice_requested": self.invoice_requested,
            "invoice_customer_type": self.invoice_customer_type,
            "sales_channel": self.sales_channel,
            "is_test": self.is_test,
            "business_mode": self.business_mode,
            "merchant_of_record": self.merchant_of_record,
            "taxes_included": self.taxes_included,
            "total_tax": self.total_tax,
            "fulfillment_country": self.fulfillment_country,
            "products_total_net": self.products_total_net,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvoiceRecord:
        items = [InvoiceItem.from_dict(x) for x in (data.get("items") or [])]
        channel = str(data.get("sales_channel") or "")
        is_test = bool(data.get("is_test"))
        if is_test:
            channel = "test"
        elif not channel:
            channel = "shopify" if int(data.get("shopify_order_id") or 0) else "manual"
        return cls(
            id=str(data.get("id") or ""),
            shopify_order_id=int(data.get("shopify_order_id") or 0),
            shopify_order_name=str(data.get("shopify_order_name") or ""),
            status=data.get("status") or "draft",
            doc_kind=data.get("doc_kind") or "invoice",
            language=data.get("language") or "pl",
            doc_type_label=str(data.get("doc_type_label") or ""),
            invoice_number=str(data.get("invoice_number") or ""),
            issue_date=str(data.get("issue_date") or ""),
            sale_date=str(data.get("sale_date") or ""),
            payment_date=str(data.get("payment_date") or ""),
            ksef_number=str(data.get("ksef_number") or ""),
            seller=PartyDetails.from_dict(data.get("seller")),
            buyer=PartyDetails.from_dict(data.get("buyer")),
            shipping_address=PartyDetails.from_dict(data.get("shipping_address")),
            items=items,
            products_total=float(data.get("products_total") or 0),
            shipping_total=float(data.get("shipping_total") or 0),
            discounts_total=float(data.get("discounts_total") or 0),
            order_total=float(data.get("order_total") or 0),
            currency=str(data.get("currency") or "PLN"),
            payment_method=str(data.get("payment_method") or ""),
            footnote=str(data.get("footnote") or ""),
            thank_you_footer=str(data.get("thank_you_footer") or ""),
            pdf_path=str(data.get("pdf_path") or ""),
            locked=bool(data.get("locked")),
            sent_to_customer=bool(data.get("sent_to_customer")),
            is_foreign=bool(data.get("is_foreign")),
            is_eu_b2c=bool(data.get("is_eu_b2c")),
            financial_status=str(data.get("financial_status") or ""),
            fulfillment_status=str(data.get("fulfillment_status") or ""),
            corrected_from_invoice_id=str(data.get("corrected_from_invoice_id") or ""),
            correction_of_number=str(data.get("correction_of_number") or ""),
            amount_before_correction=float(data.get("amount_before_correction") or 0),
            correction_amount=float(data.get("correction_amount") or 0),
            amount_after_correction=float(data.get("amount_after_correction") or 0),
            exchange=ExchangeRateInfo.from_dict(data.get("exchange")),
            invoice_requested=bool(data.get("invoice_requested")),
            invoice_customer_type=str(data.get("invoice_customer_type") or ""),
            sales_channel=channel,
            is_test=is_test,
            business_mode=data.get("business_mode") or "dnr",
            merchant_of_record=bool(data.get("merchant_of_record")),
            taxes_included=bool(data.get("taxes_included")),
            total_tax=float(data.get("total_tax") or 0),
            fulfillment_country=str(data.get("fulfillment_country") or "PL") or "PL",
            products_total_net=float(data.get("products_total_net") or 0),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class OrderRow:
    """Wiersz listy zamówień w UI."""
    shopify_order_id: int
    shopify_order_name: str
    created_at: str
    payment_date: str
    financial_status: str
    fulfillment_status: str
    customer_name: str
    customer_email: str
    shipping_country: str
    currency: str
    products_total: float
    shipping_total: float
    discounts_total: float
    order_total: float
    doc_status: InvoiceStatus
    invoice_number: str
    invoice_id: str
    is_foreign: bool
    is_eu_b2c: bool
    is_cancelled: bool
    has_refund: bool
    suggested_language: InvoiceLanguage
    invoice_requested: bool = False
    invoice_customer_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
