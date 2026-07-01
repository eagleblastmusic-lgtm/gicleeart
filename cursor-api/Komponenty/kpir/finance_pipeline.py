"""Automatyczny pipeline sprzedaży: szkice faktur → import DNR → ujęcie KPiR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_service import create_draft_for_order
from Komponenty.dokumentysprzedazy.shopify_orders import fetch_orders
from Komponenty.dokumentysprzedazy.storage import invoice_by_order_id

from .flow_status import sales_flow_summary
from .invoice_integration import create_entry_from_invoice_id
from .invoice_list import unbooked_invoices
from .sales_chain import uses_dnr_sales_chain


@dataclass
class PipelineBookResult:
    booked: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class PipelineResult:
    drafts_created: int = 0
    drafts_pending: int = 0
    dnr_imported: int = 0
    dnr_skipped: int = 0
    dnr_errors: list[str] = field(default_factory=list)
    kpir_booked: int = 0
    kpir_skipped: int = 0
    kpir_errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drafts_created": self.drafts_created,
            "drafts_pending": self.drafts_pending,
            "dnr_imported": self.dnr_imported,
            "dnr_skipped": self.dnr_skipped,
            "dnr_errors": self.dnr_errors,
            "kpir_booked": self.kpir_booked,
            "kpir_skipped": self.kpir_skipped,
            "kpir_errors": self.kpir_errors,
            "notes": self.notes,
        }


def format_pipeline_report(result: PipelineResult) -> str:
    lines = [
        f"Szkice utworzone w tym uruchomieniu: {result.drafts_created}",
        f"Szkice czekające na wystawienie (Dokumenty sprzedaży): {result.drafts_pending}",
        f"DNR: zaimportowano {result.dnr_imported}, pominięto {result.dnr_skipped}",
    ]
    if not uses_dnr_sales_chain():
        lines.append(f"KPiR: ujęto {result.kpir_booked}, pominięto {result.kpir_skipped}")
    else:
        lines.append(
            "KPiR: przychody ze sprzedaży księguj w DNR → Import do KPiR (bez faktur → KPiR)."
        )
    if result.dnr_errors:
        lines.append("")
        lines.append("Pominięte faktury DNR:")
        lines.extend(result.dnr_errors[:15])
        if len(result.dnr_errors) > 15:
            lines.append(f"… i {len(result.dnr_errors) - 15} więcej")
    if result.kpir_errors:
        lines.append("")
        lines.append("Pominięte faktury KPiR:")
        lines.extend(result.kpir_errors[:15])
        if len(result.kpir_errors) > 15:
            lines.append(f"… i {len(result.kpir_errors) - 15} więcej")
    if result.notes:
        lines.append("")
        lines.append("Uwagi:")
        lines.extend(result.notes[:10])
    if result.drafts_pending:
        lines.append("")
        tail = "przed importem DNR." if uses_dnr_sales_chain() else "przed importem DNR / KPiR."
        lines.append(
            f"→ {result.drafts_pending} szkic(ów) wymaga wystawienia w Dokumenty sprzedaży "
            f"{tail}"
        )
    return "\n".join(lines)


def create_missing_invoice_drafts(*, days_back: int = 90) -> PipelineResult:
    """Tworzy szkice faktur dla opłaconych zamówień bez dokumentu."""
    result = PipelineResult()
    try:
        orders = fetch_orders(days_back=days_back, financial_status="paid")
    except Exception as exc:
        result.notes.append(f"Shopify: {exc}")
        return result
    for order in orders:
        oid = int(order.get("id") or 0)
        if not oid:
            continue
        existing = invoice_by_order_id(oid)
        if existing:
            continue
        try:
            create_draft_for_order(order)
            result.drafts_created += 1
        except Exception as exc:
            result.notes.append(f"{order.get('name')}: {exc}")
    return result


def import_dnr_for_year(year: int) -> tuple[int, int, list[str]]:
    try:
        from Komponenty.dnr.invoice_integration import import_all_for_year
    except ImportError:
        return 0, 0, []
    return import_all_for_year(year)


def format_dnr_catchup_report(imported: int, skipped: int, errors: list[str]) -> str:
    """Raport importu zaległych faktur do DNR."""
    lines = [
        f"Zaimportowano do DNR: {imported}",
        f"Pominięto: {skipped}",
    ]
    if errors:
        lines.append("")
        lines.append("Pominięte:")
        lines.extend(errors[:15])
        if len(errors) > 15:
            lines.append(f"… i {len(errors) - 15} więcej")
    return "\n".join(lines)


def run_dnr_catchup(year: int) -> tuple[int, int, list[str]]:
    """Zaległe wystawione faktury → DNR (bez szkiców i bez KPiR)."""
    return import_dnr_for_year(year)


def book_kpir_invoices_for_year(year: int) -> PipelineBookResult:
    result = PipelineBookResult()
    if uses_dnr_sales_chain():
        return result
    for row in unbooked_invoices(year=year):
        try:
            create_entry_from_invoice_id(row.invoice_id, post=True)
            result.booked += 1
        except Exception as exc:
            result.skipped += 1
            label = row.invoice_number or row.invoice_id
            result.errors.append(f"{label}: {exc}")
    return result


def run_sales_pipeline(
    year: int,
    *,
    create_drafts: bool = True,
    import_dnr: bool = True,
    book_kpir: bool | None = None,
    days_back: int = 90,
) -> PipelineResult:
    """Uruchamia kroki pipeline (bez auto-wystawiania faktur — tylko szkice)."""
    if book_kpir is None:
        book_kpir = not uses_dnr_sales_chain()
    result = PipelineResult()
    if create_drafts:
        draft_res = create_missing_invoice_drafts(days_back=days_back)
        result.drafts_created = draft_res.drafts_created
        result.notes.extend(draft_res.notes)
    if import_dnr:
        imp, skip, errs = import_dnr_for_year(year)
        result.dnr_imported = imp
        result.dnr_skipped = skip
        result.dnr_errors = errs
    if book_kpir:
        kpir_res = book_kpir_invoices_for_year(year)
        result.kpir_booked = kpir_res.booked
        result.kpir_skipped = kpir_res.skipped
        result.kpir_errors = kpir_res.errors
    try:
        result.drafts_pending = sales_flow_summary(year=year, days_back=days_back).paid_draft_pending
    except Exception:
        result.drafts_pending = 0
    return result
