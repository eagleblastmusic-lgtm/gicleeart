"""Bezpieczny import ewidencji DNR → KPiR (bez podwójnego liczenia)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from .models import CostEntry, SaleEntry
from .storage import get_cost, get_sale, list_costs, list_sales, load_settings, save_cost, save_sale

_SUBTRACT_KINDS = frozenset({"refund", "correction", "bonification"})

_DNR_COST_COLUMN: dict[str, str] = {
    "materiały": "purchase_goods",
    "wysyłka": "other_expenses",
    "opakowania": "other_expenses",
    "prowizje": "other_expenses",
    "narzędzia": "other_expenses",
    "reklamy": "other_expenses",
    "inne": "other_expenses",
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_date(iso: str) -> date | None:
    raw = (iso or "").strip()[:10]
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def resolve_import_until_date(until_date: str = "") -> str:
    """Domyślna data końca okresu DNR = data rejestracji JDG."""
    if until_date:
        return until_date.strip()[:10]
    try:
        from Komponenty.kpir.storage import load_settings as load_kpir_settings

        reg = str(load_kpir_settings().jdg_registered_at or "")
        if reg:
            return reg[:10]
    except ImportError:
        pass
    mig = load_settings().migration or {}
    eff = str(mig.get("effective_date") or mig.get("first_exceed_date") or "")
    if eff:
        return eff[:10]
    return date.today().isoformat()


def _sale_revenue_pln(sale: SaleEntry) -> float:
    amt = round(float(sale.amount_pln or 0), 2)
    if (sale.entry_kind or "sale") in _SUBTRACT_KINDS:
        return -amt
    return amt


@dataclass
class ImportPreviewRow:
    kind: str
    dnr_id: str
    event_date: str
    amount_pln: float
    description: str
    action: str  # import | link_existing | skip_migrated | skip_mor | skip_date


@dataclass
class ImportPreview:
    until_date: str
    rows: list[ImportPreviewRow] = field(default_factory=list)
    to_import: int = 0
    to_link: int = 0
    skipped: int = 0

    @property
    def actionable(self) -> int:
        return self.to_import + self.to_link


@dataclass
class ImportResult:
    until_date: str
    imported_sales: int = 0
    imported_costs: int = 0
    linked_sales: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    kpir_entry_ids: list[str] = field(default_factory=list)


def _classify_sale(sale: SaleEntry, until: date) -> tuple[str, str]:
    """Zwraca (action, reason)."""
    if sale.migrated_to_kpir_at:
        return "skip_migrated", "już przeniesione"
    if sale.merchant_of_record:
        return "skip_mor", "merchant of record"
    ev = _parse_date(sale.event_date)
    if ev and ev > until:
        if (sale.entry_kind or "sale") in _SUBTRACT_KINDS:
            return "post_jdg_adjustment", "zwrot/korekta po dacie JDG"
        return "skip_date", "po dacie JDG"
    if sale.invoice_id:
        from Komponenty.kpir.storage import posted_entry_for_invoice

        existing = posted_entry_for_invoice(sale.invoice_id)
        if existing:
            return "link_existing", existing.id
    from Komponenty.kpir.storage import posted_entry_for_dnr_sale

    if posted_entry_for_dnr_sale(sale.id):
        return "skip_migrated", "wpis KPiR już istnieje"
    return "import", ""


def preview_dnr_kpir_import(
    *,
    until_date: str = "",
    include_costs: bool = True,
) -> ImportPreview:
    until_s = resolve_import_until_date(until_date)
    until = _parse_date(until_s) or date.today()
    preview = ImportPreview(until_date=until_s)
    for sale in sorted(list_sales(), key=lambda s: s.event_date):
        action, extra = _classify_sale(sale, until)
        row = ImportPreviewRow(
            kind="sale",
            dnr_id=sale.id,
            event_date=sale.event_date,
            amount_pln=_sale_revenue_pln(sale),
            description=(sale.description or sale.document_number or sale.id)[:120],
            action=action,
        )
        preview.rows.append(row)
        if action == "import" or action == "post_jdg_adjustment":
            preview.to_import += 1
        elif action == "link_existing":
            preview.to_link += 1
        else:
            preview.skipped += 1

    if include_costs:
        for cost in sorted(list_costs(), key=lambda c: c.event_date):
            if cost.migrated_to_kpir_at:
                preview.rows.append(ImportPreviewRow(
                    kind="cost", dnr_id=cost.id, event_date=cost.event_date,
                    amount_pln=-round(float(cost.amount_pln or 0), 2),
                    description=(cost.description or cost.category or cost.id)[:120],
                    action="skip_migrated",
                ))
                preview.skipped += 1
                continue
            ev = _parse_date(cost.event_date)
            if ev and ev > until:
                preview.rows.append(ImportPreviewRow(
                    kind="cost", dnr_id=cost.id, event_date=cost.event_date,
                    amount_pln=-round(float(cost.amount_pln or 0), 2),
                    description=(cost.description or cost.category or cost.id)[:120],
                    action="skip_date",
                ))
                preview.skipped += 1
                continue
            from Komponenty.kpir.storage import posted_entry_for_dnr_cost

            if posted_entry_for_dnr_cost(cost.id):
                preview.skipped += 1
                continue
            preview.rows.append(ImportPreviewRow(
                kind="cost", dnr_id=cost.id, event_date=cost.event_date,
                amount_pln=-round(float(cost.amount_pln or 0), 2),
                description=(cost.description or cost.category or cost.id)[:120],
                action="import",
            ))
            preview.to_import += 1
    return preview


def _mark_sale_migrated(sale: SaleEntry, kpir_entry_id: str) -> None:
    sale.migrated_to_kpir_at = _now_iso()
    sale.kpir_entry_id = kpir_entry_id
    sale.updated_at = _now_iso()
    save_sale(sale)


def _mark_cost_migrated(cost: CostEntry, kpir_entry_id: str) -> None:
    cost.migrated_to_kpir_at = _now_iso()
    cost.kpir_entry_id = kpir_entry_id
    cost.updated_at = _now_iso()
    save_cost(cost)


def _import_sale_to_kpir(sale: SaleEntry) -> str:
    from Komponenty.kpir.entry_service import create_entry, post_entry

    rev = _sale_revenue_pln(sale)
    kind = sale.entry_kind or "sale"
    desc = sale.description or f"DNR {kind}"
    if sale.list_price_pln and sale.discount_pln:
        desc = f"{desc} (DNR: {sale.list_price_pln:.2f} − {sale.discount_pln:.2f})"
    notes = f"Import z ewidencji DNR ({sale.id})"
    if sale.invoice_id:
        notes += f"; faktura {sale.invoice_id}"

    entry = create_entry(
        event_date=sale.event_date,
        document_number=sale.document_number or sale.id,
        contractor="Klient DNR",
        description=desc[:200],
        revenue_goods=rev,
        source="dnr_import",
        entry_type="revenue",
        original_currency=sale.currency or "PLN",
        original_amount=sale.amount_original or abs(rev),
        amount_pln=abs(rev),
        nbp_status="not_needed",
        invoice_id=sale.invoice_id or "",
        dnr_sale_id=sale.id,
        notes=notes,
    )
    entry = post_entry(entry)
    return entry.id


def _import_cost_to_kpir(cost: CostEntry) -> str:
    from Komponenty.kpir.entry_service import create_entry, post_entry

    col = _DNR_COST_COLUMN.get(cost.category or "inne", "other_expenses")
    amt = round(float(cost.amount_pln or 0), 2)
    kwargs: dict[str, Any] = {
        "event_date": cost.event_date,
        "document_number": cost.document_number or cost.id,
        "contractor": cost.seller or "Dostawca",
        "description": (cost.description or f"Koszt DNR: {cost.category}")[:200],
        "source": "dnr_import",
        "entry_type": "cost",
        "amount_pln": amt,
        "nbp_status": "not_needed",
        "dnr_cost_id": cost.id,
        "category": cost.category,
        "notes": f"Import kosztu DNR ({cost.id})",
    }
    kwargs[col] = amt
    entry = create_entry(**kwargs)
    entry = post_entry(entry)
    return entry.id


def import_dnr_to_kpir(
    *,
    until_date: str = "",
    include_costs: bool = True,
) -> ImportResult:
    """Przenosi wpisy DNR do KPiR i oznacza je jako zamknięte w DNR (nie wliczane do limitu/VAT)."""
    preview = preview_dnr_kpir_import(until_date=until_date, include_costs=include_costs)
    result = ImportResult(until_date=preview.until_date)

    for row in preview.rows:
        try:
            if row.action in ("import", "post_jdg_adjustment") and row.kind == "sale":
                sale = get_sale(row.dnr_id)
                if not sale:
                    result.errors.append(f"Brak sprzedaży {row.dnr_id}")
                    continue
                kid = _import_sale_to_kpir(sale)
                _mark_sale_migrated(sale, kid)
                result.imported_sales += 1
                result.kpir_entry_ids.append(kid)
            elif row.action == "link_existing" and row.kind == "sale":
                sale = get_sale(row.dnr_id)
                if not sale:
                    continue
                from Komponenty.kpir.storage import posted_entry_for_invoice

                existing = posted_entry_for_invoice(sale.invoice_id)
                if existing:
                    _mark_sale_migrated(sale, existing.id)
                    result.linked_sales += 1
            elif row.action == "import" and row.kind == "cost":
                cost = get_cost(row.dnr_id)
                if not cost:
                    result.errors.append(f"Brak kosztu {row.dnr_id}")
                    continue
                kid = _import_cost_to_kpir(cost)
                _mark_cost_migrated(cost, kid)
                result.imported_costs += 1
                result.kpir_entry_ids.append(kid)
            else:
                result.skipped += 1
        except Exception as exc:
            result.errors.append(f"{row.dnr_id}: {exc}")

    if result.imported_sales or result.imported_costs or result.linked_sales:
        from .migration_service import set_migration_step

        set_migration_step("dnr_imported")
    else:
        follow = preview_dnr_kpir_import(until_date=preview.until_date, include_costs=include_costs)
        if follow.actionable == 0:
            from .migration_service import set_migration_step

            set_migration_step("dnr_imported")
    return result
