"""Modele DNR — sprzedaż, koszty, ustawienia."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .constants import DEFAULT_QUARTERLY_LIMIT, ELIGIBILITY_ITEMS, LEGACY_ANNUAL_LIMIT

SaleSource = Literal["manual", "invoice", "shopify", "allegro"]
SaleKind = Literal["sale", "refund", "correction", "bonification"]
PaymentStatus = Literal["unpaid", "paid", "partial"]


def _parse_payment_status(raw: Any) -> PaymentStatus:
    s = str(raw or "paid")
    if s in ("unpaid", "paid", "partial"):
        return s  # type: ignore[return-value]
    return "paid"


@dataclass
class DnrSettings:
    owner_name: str = ""
    quarterly_limit: float = DEFAULT_QUARTERLY_LIMIT
    notes: str = ""
    eligibility: dict[str, bool] = field(default_factory=dict)
    eligibility_confirmed_at: str = ""
    migration: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def eligibility_complete(self) -> bool:
        return all(self.eligibility.get(key) for key, _ in ELIGIBILITY_ITEMS)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DnrSettings:
        if "quarterly_limit" in data:
            quarterly = float(data.get("quarterly_limit") or DEFAULT_QUARTERLY_LIMIT)
        elif "annual_limit" in data:
            annual = float(data.get("annual_limit") or 0)
            quarterly = DEFAULT_QUARTERLY_LIMIT if annual == LEGACY_ANNUAL_LIMIT else round(annual / 4, 2)
        else:
            quarterly = DEFAULT_QUARTERLY_LIMIT
        raw_elig = data.get("eligibility") or {}
        eligibility = {
            key: bool(raw_elig.get(key))
            for key, _ in ELIGIBILITY_ITEMS
        }
        from .migration_service import normalize_migration

        return cls(
            owner_name=str(data.get("owner_name") or ""),
            quarterly_limit=quarterly,
            notes=str(data.get("notes") or ""),
            eligibility=eligibility,
            eligibility_confirmed_at=str(data.get("eligibility_confirmed_at") or ""),
            migration=normalize_migration(data.get("migration")),
        )


@dataclass
class SaleEntry:
    id: str = ""
    event_date: str = ""
    amount_pln: float = 0.0
    description: str = ""
    document_number: str = ""
    source: SaleSource = "manual"
    entry_kind: SaleKind = "sale"
    list_price_pln: float = 0.0
    discount_pln: float = 0.0
    invoice_id: str = ""
    currency: str = "PLN"
    amount_original: float = 0.0
    merchant_of_record: bool = False
    payment_status: PaymentStatus = "paid"
    paid_at: str = ""
    amount_received_pln: float = 0.0
    shopify_order_id: int = 0
    destination_country: str = ""
    fulfillment_country: str = "PL"
    migrated_to_kpir_at: str = ""
    kpir_entry_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SaleEntry:
        src = str(data.get("source") or "manual")
        if src not in ("manual", "invoice", "shopify", "allegro"):
            src = "manual"
        kind = str(data.get("entry_kind") or "sale")
        if kind not in ("sale", "refund", "correction", "bonification"):
            kind = "sale"
        return cls(
            id=str(data.get("id") or ""),
            event_date=str(data.get("event_date") or ""),
            amount_pln=float(data.get("amount_pln") or 0),
            description=str(data.get("description") or ""),
            document_number=str(data.get("document_number") or ""),
            source=src,  # type: ignore[arg-type]
            entry_kind=kind,  # type: ignore[arg-type]
            list_price_pln=float(data.get("list_price_pln") or 0),
            discount_pln=float(data.get("discount_pln") or 0),
            invoice_id=str(data.get("invoice_id") or ""),
            currency=str(data.get("currency") or "PLN"),
            amount_original=float(data.get("amount_original") or 0),
            merchant_of_record=bool(data.get("merchant_of_record")),
            payment_status=_parse_payment_status(data.get("payment_status")),
            paid_at=str(data.get("paid_at") or ""),
            amount_received_pln=float(data.get("amount_received_pln") or 0),
            shopify_order_id=int(data.get("shopify_order_id") or 0),
            destination_country=str(data.get("destination_country") or ""),
            fulfillment_country=str(data.get("fulfillment_country") or "PL") or "PL",
            migrated_to_kpir_at=str(data.get("migrated_to_kpir_at") or ""),
            kpir_entry_id=str(data.get("kpir_entry_id") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class CostEntry:
    id: str = ""
    event_date: str = ""
    amount_pln: float = 0.0
    category: str = "inne"
    description: str = ""
    seller: str = ""
    document_number: str = ""
    art28b_service: bool = False
    migrated_to_kpir_at: str = ""
    kpir_entry_id: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostEntry:
        return cls(
            id=str(data.get("id") or ""),
            event_date=str(data.get("event_date") or ""),
            amount_pln=float(data.get("amount_pln") or 0),
            category=str(data.get("category") or "inne"),
            description=str(data.get("description") or ""),
            seller=str(data.get("seller") or ""),
            document_number=str(data.get("document_number") or ""),
            art28b_service=bool(data.get("art28b_service")),
            migrated_to_kpir_at=str(data.get("migrated_to_kpir_at") or ""),
            kpir_entry_id=str(data.get("kpir_entry_id") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )
