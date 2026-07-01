"""Modele danych KPiR."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .constants import (
    AccountingMode,
    CostMethod,
    CostStatus,
    DEFAULT_SETTINGS,
    DNR_LEGACY_ANNUAL_LIMIT,
    EntryType,
    InventoryKind,
    InvoiceKpirStatus,
    KpirColumn,
    KpirEntrySource,
    KpirEntryStatus,
    OrderKpirStatus,
    SalesGrouping,
    TaxForm,
)


@dataclass
class KpirSettings:
    accounting_mode: AccountingMode = "jdg_kpir"
    tax_form: TaxForm = "scale"
    cost_method: CostMethod = "accrual"
    activity_description: str = DEFAULT_SETTINGS["activity_description"]
    book_opened_at: str = DEFAULT_SETTINGS["book_opened_at"]
    cumulative_monthly_sums: bool = DEFAULT_SETTINGS["cumulative_monthly_sums"]
    sales_grouping: SalesGrouping = "single"
    group_by_currency: bool = False
    group_by_region: bool = False
    group_regions: list[str] = field(default_factory=lambda: ["PL", "EU", "NON_EU"])
    zus_monthly: float = 0.0
    health_insurance_monthly: float = 0.0
    zus_stage: str = DEFAULT_SETTINGS["zus_stage"]
    voluntary_sickness: bool = DEFAULT_SETTINGS["voluntary_sickness"]
    zus_manual_override: bool = DEFAULT_SETTINGS["zus_manual_override"]
    jdg_registered_at: str = DEFAULT_SETTINGS["jdg_registered_at"]
    zus_stage_started_at: str = DEFAULT_SETTINGS["zus_stage_started_at"]
    maly_zus_prior_year_income: float = DEFAULT_SETTINGS["maly_zus_prior_year_income"]
    maly_zus_prior_year_activity_days: int = DEFAULT_SETTINGS["maly_zus_prior_year_activity_days"]
    maly_zus_cycle_start: str = DEFAULT_SETTINGS["maly_zus_cycle_start"]
    tax_free_amount: float = DEFAULT_SETTINGS["tax_free_amount"]
    tax_threshold_1: float = DEFAULT_SETTINGS["tax_threshold_1"]
    tax_rate_scale_low: float = DEFAULT_SETTINGS["tax_rate_scale_low"]
    tax_rate_scale_high: float = DEFAULT_SETTINGS["tax_rate_scale_high"]
    tax_rate_linear: float = DEFAULT_SETTINGS["tax_rate_linear"]
    dnr_limit_quarterly: float = DEFAULT_SETTINGS["dnr_limit_quarterly"]
    vat_exemption_threshold: float = DEFAULT_SETTINGS["vat_exemption_threshold"]
    vat_status: str = DEFAULT_SETTINGS["vat_status"]
    seller_name: str = ""
    seller_nip: str = ""
    seller_address: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> KpirSettings:
        if not data:
            return cls()
        regions = data.get("group_regions") or ["PL", "EU", "NON_EU"]
        if "dnr_limit_quarterly" in data:
            dnr_limit = float(data.get("dnr_limit_quarterly") or DEFAULT_SETTINGS["dnr_limit_quarterly"])
        elif "dnr_limit_annual" in data:
            annual = float(data.get("dnr_limit_annual") or 0)
            dnr_limit = (
                DEFAULT_SETTINGS["dnr_limit_quarterly"]
                if annual == DNR_LEGACY_ANNUAL_LIMIT
                else round(annual / 4, 2)
            )
        else:
            dnr_limit = DEFAULT_SETTINGS["dnr_limit_quarterly"]
        return cls(
            accounting_mode=data.get("accounting_mode") or "jdg_kpir",
            tax_form=data.get("tax_form") or "scale",
            cost_method=data.get("cost_method") or DEFAULT_SETTINGS["cost_method"],
            activity_description=str(data.get("activity_description") or ""),
            book_opened_at=str(data.get("book_opened_at") or ""),
            cumulative_monthly_sums=bool(data.get("cumulative_monthly_sums", True)),
            sales_grouping=data.get("sales_grouping") or "single",
            group_by_currency=bool(data.get("group_by_currency")),
            group_by_region=bool(data.get("group_by_region")),
            group_regions=[str(x) for x in regions],
            zus_monthly=float(data.get("zus_monthly") or 0),
            health_insurance_monthly=float(data.get("health_insurance_monthly") or 0),
            zus_stage=str(data.get("zus_stage") or DEFAULT_SETTINGS["zus_stage"]),
            voluntary_sickness=bool(data.get("voluntary_sickness")),
            zus_manual_override=bool(data.get("zus_manual_override")),
            jdg_registered_at=str(data.get("jdg_registered_at") or ""),
            zus_stage_started_at=str(data.get("zus_stage_started_at") or ""),
            maly_zus_prior_year_income=float(data.get("maly_zus_prior_year_income") or 0),
            maly_zus_prior_year_activity_days=int(data.get("maly_zus_prior_year_activity_days") or 365),
            maly_zus_cycle_start=str(data.get("maly_zus_cycle_start") or ""),
            tax_free_amount=float(data.get("tax_free_amount") or DEFAULT_SETTINGS["tax_free_amount"]),
            tax_threshold_1=float(data.get("tax_threshold_1") or DEFAULT_SETTINGS["tax_threshold_1"]),
            tax_rate_scale_low=float(data.get("tax_rate_scale_low") or DEFAULT_SETTINGS["tax_rate_scale_low"]),
            tax_rate_scale_high=float(data.get("tax_rate_scale_high") or DEFAULT_SETTINGS["tax_rate_scale_high"]),
            tax_rate_linear=float(data.get("tax_rate_linear") or DEFAULT_SETTINGS["tax_rate_linear"]),
            dnr_limit_quarterly=dnr_limit,
            vat_exemption_threshold=float(
                data.get("vat_exemption_threshold") or DEFAULT_SETTINGS["vat_exemption_threshold"]
            ),
            vat_status=str(data.get("vat_status") or DEFAULT_SETTINGS["vat_status"]),
            seller_name=str(data.get("seller_name") or ""),
            seller_nip=str(data.get("seller_nip") or ""),
            seller_address=str(data.get("seller_address") or ""),
        )


@dataclass
class KpirEntry:
    id: str
    entry_number: str
    event_date: str
    document_number: str
    ksef_number: str = ""
    contractor_nip: str = ""
    contractor: str = ""
    contractor_address: str = ""
    description: str = ""
    revenue_goods: float = 0.0
    revenue_other: float = 0.0
    purchase_goods: float = 0.0
    purchase_side: float = 0.0
    wages: float = 0.0
    other_expenses: float = 0.0
    other_events: str = ""
    rd_expenses: float = 0.0
    notes: str = ""
    source: KpirEntrySource = "system"
    status: KpirEntryStatus = "draft"
    entry_type: EntryType = "revenue"
    original_currency: str = "PLN"
    original_amount: float = 0.0
    nbp_rate: float = 1.0
    nbp_rate_date: str = ""
    nbp_table_number: str = ""
    amount_pln: float = 0.0
    nbp_status: str = "not_needed"
    country: str = ""
    shopify_order_id: int = 0
    shopify_order_name: str = ""
    invoice_id: str = ""
    dnr_sale_id: str = ""
    dnr_cost_id: str = ""
    cost_id: str = ""
    linked_entry_id: str = ""
    correction_reason: str = ""
    amount_before_correction: float = 0.0
    correction_amount: float = 0.0
    amount_after_correction: float = 0.0
    category: str = ""
    inventory_id: str = ""
    fixed_asset_id: str = ""
    attachments: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @property
    def total_revenue(self) -> float:
        return round(self.revenue_goods + self.revenue_other, 2)

    @property
    def total_costs(self) -> float:
        return round(
            self.purchase_goods + self.purchase_side + self.wages + self.other_expenses, 2,
        )

    @property
    def total_expenses(self) -> float:
        return round(self.wages + self.other_expenses, 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["total_revenue"] = self.total_revenue
        d["total_costs"] = self.total_costs
        d["total_expenses"] = self.total_expenses
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KpirEntry:
        atts = data.get("attachments") or []
        return cls(
            id=str(data.get("id") or ""),
            entry_number=str(data.get("entry_number") or ""),
            event_date=str(data.get("event_date") or ""),
            document_number=str(data.get("document_number") or ""),
            ksef_number=str(data.get("ksef_number") or ""),
            contractor_nip=str(data.get("contractor_nip") or ""),
            contractor=str(data.get("contractor") or ""),
            contractor_address=str(data.get("contractor_address") or ""),
            description=str(data.get("description") or ""),
            revenue_goods=float(data.get("revenue_goods") or 0),
            revenue_other=float(data.get("revenue_other") or 0),
            purchase_goods=float(data.get("purchase_goods") or 0),
            purchase_side=float(data.get("purchase_side") or 0),
            wages=float(data.get("wages") or 0),
            other_expenses=float(data.get("other_expenses") or 0),
            other_events=str(data.get("other_events") or ""),
            rd_expenses=float(data.get("rd_expenses") or 0),
            notes=str(data.get("notes") or ""),
            source=data.get("source") or "system",
            status=data.get("status") or "draft",
            entry_type=data.get("entry_type") or "revenue",
            original_currency=str(data.get("original_currency") or "PLN"),
            original_amount=float(data.get("original_amount") or 0),
            nbp_rate=float(data.get("nbp_rate") or 1),
            nbp_rate_date=str(data.get("nbp_rate_date") or ""),
            nbp_table_number=str(data.get("nbp_table_number") or ""),
            amount_pln=float(data.get("amount_pln") or 0),
            nbp_status=str(data.get("nbp_status") or "not_needed"),
            country=str(data.get("country") or ""),
            shopify_order_id=int(data.get("shopify_order_id") or 0),
            shopify_order_name=str(data.get("shopify_order_name") or ""),
            invoice_id=str(data.get("invoice_id") or ""),
            dnr_sale_id=str(data.get("dnr_sale_id") or ""),
            dnr_cost_id=str(data.get("dnr_cost_id") or ""),
            cost_id=str(data.get("cost_id") or ""),
            linked_entry_id=str(data.get("linked_entry_id") or ""),
            correction_reason=str(data.get("correction_reason") or ""),
            amount_before_correction=float(data.get("amount_before_correction") or 0),
            correction_amount=float(data.get("correction_amount") or 0),
            amount_after_correction=float(data.get("amount_after_correction") or 0),
            category=str(data.get("category") or ""),
            inventory_id=str(data.get("inventory_id") or ""),
            fixed_asset_id=str(data.get("fixed_asset_id") or ""),
            attachments=[str(x) for x in atts],
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class CostRecord:
    id: str
    issue_date: str = ""
    event_date: str = ""
    payment_date: str = ""
    document_number: str = ""
    seller: str = ""
    seller_nip: str = ""
    seller_country: str = ""
    description: str = ""
    category: str = ""
    amount_gross: float = 0.0
    currency: str = "PLN"
    nbp_rate: float = 1.0
    amount_pln: float = 0.0
    nbp_rate_date: str = ""
    nbp_table_number: str = ""
    nbp_status: str = "not_needed"
    payment_method: str = ""
    is_paid: bool = False
    liability_unpaid: bool = False
    kpir_column: KpirColumn = "other_expenses"
    kpir_entry_id: str = ""
    kpir_status: CostStatus = "draft"
    is_internal_doc: bool = False
    attachment_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CostRecord:
        return cls(
            id=str(data.get("id") or ""),
            issue_date=str(data.get("issue_date") or ""),
            event_date=str(data.get("event_date") or ""),
            payment_date=str(data.get("payment_date") or ""),
            document_number=str(data.get("document_number") or ""),
            seller=str(data.get("seller") or ""),
            seller_nip=str(data.get("seller_nip") or ""),
            seller_country=str(data.get("seller_country") or ""),
            description=str(data.get("description") or ""),
            category=str(data.get("category") or ""),
            amount_gross=float(data.get("amount_gross") or 0),
            currency=str(data.get("currency") or "PLN"),
            nbp_rate=float(data.get("nbp_rate") or 1),
            amount_pln=float(data.get("amount_pln") or 0),
            nbp_rate_date=str(data.get("nbp_rate_date") or ""),
            nbp_table_number=str(data.get("nbp_table_number") or ""),
            nbp_status=str(data.get("nbp_status") or "not_needed"),
            payment_method=str(data.get("payment_method") or ""),
            is_paid=bool(data.get("is_paid")),
            liability_unpaid=bool(data.get("liability_unpaid")),
            kpir_column=data.get("kpir_column") or "other_expenses",
            kpir_entry_id=str(data.get("kpir_entry_id") or ""),
            kpir_status=data.get("kpir_status") or "draft",
            is_internal_doc=bool(data.get("is_internal_doc")),
            attachment_path=str(data.get("attachment_path") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class RecurringCost:
    id: str
    name: str
    vendor: str = ""
    amount: float = 0.0
    currency: str = "PLN"
    frequency: str = "monthly"
    day_of_month: int = 1
    category: str = ""
    kpir_column: KpirColumn = "other_expenses"
    active: bool = True
    last_generated: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecurringCost:
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            vendor=str(data.get("vendor") or ""),
            amount=float(data.get("amount") or 0),
            currency=str(data.get("currency") or "PLN"),
            frequency=str(data.get("frequency") or "monthly"),
            day_of_month=int(data.get("day_of_month") or 1),
            category=str(data.get("category") or ""),
            kpir_column=data.get("kpir_column") or "other_expenses",
            active=bool(data.get("active", True)),
            last_generated=str(data.get("last_generated") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class MonthClosure:
    year: int
    month: int
    closed_at: str = ""
    closed_by: str = "user"
    reopened_at: str = ""
    is_closed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MonthClosure:
        return cls(
            year=int(data.get("year") or 0),
            month=int(data.get("month") or 0),
            closed_at=str(data.get("closed_at") or ""),
            closed_by=str(data.get("closed_by") or "user"),
            reopened_at=str(data.get("reopened_at") or ""),
            is_closed=bool(data.get("is_closed")),
        )


@dataclass
class ChangeLogEntry:
    id: str
    entry_id: str
    field_name: str
    old_value: str
    new_value: str
    changed_at: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChangeLogEntry:
        return cls(
            id=str(data.get("id") or ""),
            entry_id=str(data.get("entry_id") or ""),
            field_name=str(data.get("field_name") or ""),
            old_value=str(data.get("old_value") or ""),
            new_value=str(data.get("new_value") or ""),
            changed_at=str(data.get("changed_at") or ""),
            reason=str(data.get("reason") or ""),
        )


@dataclass
class OrderKpirInfo:
    shopify_order_id: int
    status: OrderKpirStatus = "not_booked"
    entry_id: str = ""
    entry_number: str = ""
    amount_pln: float = 0.0
    nbp_rate: float = 1.0
    nbp_rate_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InvoiceKpirInfo:
    invoice_id: str
    status: InvoiceKpirStatus = "not_booked"
    entry_id: str = ""
    entry_number: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InventoryLine:
    line_no: int
    name: str
    unit: str = "szt."
    quantity: float = 0.0
    unit_price: float = 0.0
    value: float = 0.0
    is_foreign_goods: bool = False
    owner_note: str = ""
    valuation_method: str = "purchase_price"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InventoryLine:
        return cls(
            line_no=int(data.get("line_no") or 0),
            name=str(data.get("name") or ""),
            unit=str(data.get("unit") or "szt."),
            quantity=float(data.get("quantity") or 0),
            unit_price=float(data.get("unit_price") or 0),
            value=float(data.get("value") or 0),
            is_foreign_goods=bool(data.get("is_foreign_goods")),
            owner_note=str(data.get("owner_note") or ""),
            valuation_method=str(data.get("valuation_method") or "purchase_price"),
        )


@dataclass
class InventoryRecord:
    id: str
    inventory_date: str
    kind: InventoryKind = "year_end"
    lines: list[InventoryLine] = field(default_factory=list)
    total_value: float = 0.0
    valuation_completed_at: str = ""
    booked_entry_id: str = ""
    status: str = "draft"
    notes: str = ""
    side_cost_markup_pct: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "lines": [ln.to_dict() for ln in self.lines],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InventoryRecord:
        lines = [InventoryLine.from_dict(x) for x in (data.get("lines") or [])]
        return cls(
            id=str(data.get("id") or ""),
            inventory_date=str(data.get("inventory_date") or ""),
            kind=data.get("kind") or "year_end",
            lines=lines,
            total_value=float(data.get("total_value") or 0),
            valuation_completed_at=str(data.get("valuation_completed_at") or ""),
            booked_entry_id=str(data.get("booked_entry_id") or ""),
            status=str(data.get("status") or "draft"),
            notes=str(data.get("notes") or ""),
            side_cost_markup_pct=float(data.get("side_cost_markup_pct") or 0),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class FixedAsset:
    id: str
    name: str
    acquisition_date: str = ""
    document_number: str = ""
    initial_value: float = 0.0
    depreciation_rate: float = 0.20
    accumulated_depreciation: float = 0.0
    is_active: bool = True
    disposal_date: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def net_value(self) -> float:
        return round(max(0.0, self.initial_value - self.accumulated_depreciation), 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["net_value"] = self.net_value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FixedAsset:
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            acquisition_date=str(data.get("acquisition_date") or ""),
            document_number=str(data.get("document_number") or ""),
            initial_value=float(data.get("initial_value") or 0),
            depreciation_rate=float(data.get("depreciation_rate") or 0.20),
            accumulated_depreciation=float(data.get("accumulated_depreciation") or 0),
            is_active=bool(data.get("is_active", True)),
            disposal_date=str(data.get("disposal_date") or ""),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class SalesRegisterEntry:
    id: str
    event_date: str
    amount: float
    description: str = ""
    document_ref: str = ""
    kpir_entry_id: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SalesRegisterEntry:
        return cls(
            id=str(data.get("id") or ""),
            event_date=str(data.get("event_date") or ""),
            amount=float(data.get("amount") or 0),
            description=str(data.get("description") or ""),
            document_ref=str(data.get("document_ref") or ""),
            kpir_entry_id=str(data.get("kpir_entry_id") or ""),
            created_at=str(data.get("created_at") or ""),
        )


@dataclass
class YearClosure:
    year: int
    is_closed: bool = False
    closed_at: str = ""
    inventory_end_id: str = ""
    inventory_start_next_id: str = ""
    annual_income: float = 0.0
    pkpir_export_path: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YearClosure:
        return cls(
            year=int(data.get("year") or 0),
            is_closed=bool(data.get("is_closed")),
            closed_at=str(data.get("closed_at") or ""),
            inventory_end_id=str(data.get("inventory_end_id") or ""),
            inventory_start_next_id=str(data.get("inventory_start_next_id") or ""),
            annual_income=float(data.get("annual_income") or 0),
            pkpir_export_path=str(data.get("pkpir_export_path") or ""),
            notes=str(data.get("notes") or ""),
        )


@dataclass
class GoodsReceiptPending:
    """Opis towaru przed fakturą (§ 9 rozporządzenia)."""
    id: str
    receipt_date: str
    supplier_name: str
    supplier_nip: str = ""
    description: str = ""
    quantity: float = 0.0
    unit: str = "szt."
    unit_price: float = 0.0
    value: float = 0.0
    invoice_document_number: str = ""
    ksef_number: str = ""
    kpir_entry_id: str = ""
    status: str = "pending"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoodsReceiptPending:
        return cls(
            id=str(data.get("id") or ""),
            receipt_date=str(data.get("receipt_date") or ""),
            supplier_name=str(data.get("supplier_name") or ""),
            supplier_nip=str(data.get("supplier_nip") or ""),
            description=str(data.get("description") or ""),
            quantity=float(data.get("quantity") or 0),
            unit=str(data.get("unit") or "szt."),
            unit_price=float(data.get("unit_price") or 0),
            value=float(data.get("value") or 0),
            invoice_document_number=str(data.get("invoice_document_number") or ""),
            ksef_number=str(data.get("ksef_number") or ""),
            kpir_entry_id=str(data.get("kpir_entry_id") or ""),
            status=str(data.get("status") or "pending"),
            created_at=str(data.get("created_at") or ""),
        )


@dataclass
class IntangibleAsset:
    """Wartości niematerialne i prawne — ewidencja łącznie z PKPiR."""
    id: str
    name: str
    acquisition_date: str = ""
    document_number: str = ""
    initial_value: float = 0.0
    depreciation_rate: float = 0.20
    accumulated_depreciation: float = 0.0
    is_active: bool = True
    disposal_date: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def net_value(self) -> float:
        return round(max(0.0, self.initial_value - self.accumulated_depreciation), 2)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["net_value"] = self.net_value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntangibleAsset:
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            acquisition_date=str(data.get("acquisition_date") or ""),
            document_number=str(data.get("document_number") or ""),
            initial_value=float(data.get("initial_value") or 0),
            depreciation_rate=float(data.get("depreciation_rate") or 0.20),
            accumulated_depreciation=float(data.get("accumulated_depreciation") or 0),
            is_active=bool(data.get("is_active", True)),
            disposal_date=str(data.get("disposal_date") or ""),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class CompanyVehicle:
    id: str
    name: str
    registration_number: str = ""
    fixed_asset_id: str = ""
    business_use_pct: float = 100.0
    is_active: bool = True
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompanyVehicle:
        return cls(
            id=str(data.get("id") or ""),
            name=str(data.get("name") or ""),
            registration_number=str(data.get("registration_number") or ""),
            fixed_asset_id=str(data.get("fixed_asset_id") or ""),
            business_use_pct=float(data.get("business_use_pct") or 100),
            is_active=bool(data.get("is_active", True)),
            notes=str(data.get("notes") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


@dataclass
class MileageLogEntry:
    id: str
    vehicle_id: str
    log_date: str
    odometer_km: float = 0.0
    trip_km: float = 0.0
    route_description: str = ""
    purpose: str = "business"
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MileageLogEntry:
        return cls(
            id=str(data.get("id") or ""),
            vehicle_id=str(data.get("vehicle_id") or ""),
            log_date=str(data.get("log_date") or ""),
            odometer_km=float(data.get("odometer_km") or 0),
            trip_km=float(data.get("trip_km") or 0),
            route_description=str(data.get("route_description") or ""),
            purpose=str(data.get("purpose") or "business"),
            created_at=str(data.get("created_at") or ""),
        )


@dataclass
class FxSettlement:
    """Kurs rozliczenia wpłaty/wypłaty — do różnic kursowych."""
    id: str
    entry_id: str
    settlement_date: str
    settlement_rate: float
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FxSettlement:
        return cls(
            id=str(data.get("id") or ""),
            entry_id=str(data.get("entry_id") or ""),
            settlement_date=str(data.get("settlement_date") or ""),
            settlement_rate=float(data.get("settlement_rate") or 0),
            note=str(data.get("note") or ""),
            created_at=str(data.get("created_at") or ""),
        )
