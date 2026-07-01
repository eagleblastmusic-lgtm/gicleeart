"""Licznik progu zwolnienia z VAT (obrót roczny) — osobny od limitu DNR."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.vat_prorata import vat_prorata_threshold

_ISSUED_STATUSES = frozenset({"issued", "corrected"})


def _year_from_iso(iso: str) -> int:
    try:
        return int(iso[:4])
    except (TypeError, ValueError):
        return date.today().year


def _invoice_net_pln(inv: Any) -> float:
    if getattr(inv, "merchant_of_record", False):
        return 0.0
    if inv.status == "corrected" and inv.amount_after_correction:
        return round(float(inv.amount_after_correction), 2)
    if inv.exchange.total_amount_pln > 0:
        return round(float(inv.exchange.total_amount_pln), 2)
    return round(float(inv.order_total or 0), 2)


def _invoice_turnover_delta(inv: Any) -> float:
    """Wpływ dokumentu na obrót VAT (PLN)."""
    if getattr(inv, "is_test", False) or getattr(inv, "sales_channel", "") == "test":
        return 0.0
    if getattr(inv, "merchant_of_record", False):
        return 0.0
    if inv.status == "cancelled":
        return 0.0
    if inv.doc_kind == "correction":
        if inv.status != "issued":
            return 0.0
        return round(float(inv.correction_amount or 0), 2)
    if inv.doc_kind == "invoice" and inv.status in _ISSUED_STATUSES:
        return _invoice_net_pln(inv)
    return 0.0


def _invoice_year(inv: Any) -> int:
    for field in (inv.sale_date, inv.issue_date, inv.payment_date):
        if field:
            return _year_from_iso(str(field))
    return date.today().year


def _dnr_turnover_delta(entry: Any) -> float:
    if getattr(entry, "merchant_of_record", False):
        return 0.0
    if getattr(entry, "migrated_to_kpir_at", ""):
        return 0.0
    if entry.invoice_id:
        return 0.0
    kind = entry.entry_kind or "sale"
    amt = round(float(entry.amount_pln or 0), 2)
    if kind in ("refund", "correction", "bonification"):
        return -amt
    if kind == "sale":
        return amt
    return 0.0


def turnover_from_invoices(year: int) -> tuple[float, list[dict[str, Any]]]:
    try:
        from Komponenty.dokumentysprzedazy.storage import list_invoices
    except ImportError:
        return 0.0, []

    total = 0.0
    rows: list[dict[str, Any]] = []
    for inv in list_invoices():
        if _invoice_year(inv) != year:
            continue
        delta = _invoice_turnover_delta(inv)
        if delta == 0.0:
            continue
        total += delta
        rows.append({
            "source": "invoice",
            "id": inv.id,
            "date": inv.sale_date or inv.issue_date,
            "number": inv.invoice_number,
            "amount_pln": round(delta, 2),
            "merchant_of_record": bool(getattr(inv, "merchant_of_record", False)),
        })
    return round(total, 2), rows


def turnover_from_dnr_sales(year: int) -> tuple[float, list[dict[str, Any]]]:
    try:
        from Komponenty.dnr.storage import list_sales
    except ImportError:
        return 0.0, []

    total = 0.0
    rows: list[dict[str, Any]] = []
    for entry in list_sales():
        if _year_from_iso(entry.event_date) != year:
            continue
        delta = _dnr_turnover_delta(entry)
        if delta == 0.0:
            continue
        total += delta
        rows.append({
            "source": "dnr",
            "id": entry.id,
            "date": entry.event_date,
            "number": entry.document_number,
            "amount_pln": round(delta, 2),
            "merchant_of_record": bool(getattr(entry, "merchant_of_record", False)),
        })
    return round(total, 2), rows


def turnover_from_kpir_dnr_import(year: int) -> tuple[float, list[dict[str, Any]]]:
    """Przychód z importu DNR → KPiR (bez faktury — uzupełnia licznik VAT po migracji)."""
    try:
        from Komponenty.kpir.storage import list_entries
    except ImportError:
        return 0.0, []

    total = 0.0
    rows: list[dict[str, Any]] = []
    for entry in list_entries():
        if entry.status not in ("posted", "corrected"):
            continue
        if entry.entry_type != "revenue":
            continue
        if entry.source != "dnr_import":
            continue
        if entry.invoice_id:
            continue
        if _year_from_iso(entry.event_date) != year:
            continue
        amt = round(float(entry.amount_pln or entry.revenue_goods or 0), 2)
        if amt == 0.0:
            continue
        total += amt
        rows.append({
            "source": "kpir_dnr_import",
            "id": entry.id,
            "date": entry.event_date,
            "number": entry.document_number,
            "amount_pln": amt,
            "merchant_of_record": False,
        })
    return round(total, 2), rows


def annual_turnover(year: int | None = None, *, jdg_registered_at: str = "") -> dict[str, Any]:
    y = year or date.today().year
    inv_total, inv_rows = turnover_from_invoices(y)
    dnr_total, dnr_rows = turnover_from_dnr_sales(y)
    kpir_total, kpir_rows = turnover_from_kpir_dnr_import(y)
    turnover = round(inv_total + dnr_total + kpir_total, 2)
    prorata = vat_prorata_threshold(jdg_registered_at, y)
    threshold = float(prorata["threshold_pln"])
    remaining = round(max(0.0, threshold - turnover), 2)
    pct = round((turnover / threshold * 100) if threshold > 0 else 0, 1)
    over = turnover > threshold
    if over:
        level = "over"
        message = (
            f"Przekroczono próg zwolnienia z VAT ({threshold:,.2f} zł) "
            f"o {turnover - threshold:,.2f} zł — rozważ rejestrację VAT."
        )
    elif pct >= 90:
        level = "warn"
        message = f"Zbliżasz się do progu VAT — zostało {remaining:,.2f} zł obrotu."
    elif pct >= 75:
        level = "caution"
        message = f"Wykorzystano {pct}% progu zwolnienia z VAT — zostało {remaining:,.2f} zł."
    else:
        level = "ok"
        message = f"Obrót VAT {y}: {turnover:,.2f} zł / {threshold:,.2f} zł ({pct}%)."
    if prorata.get("prorata_applied"):
        message += f" [{prorata['message']}]"
    return {
        "year": y,
        "turnover_pln": turnover,
        "invoice_turnover_pln": inv_total,
        "dnr_turnover_pln": dnr_total,
        "kpir_dnr_import_pln": kpir_total,
        "threshold_pln": threshold,
        "full_threshold_pln": prorata.get("full_threshold_pln"),
        "prorata": prorata,
        "remaining_pln": remaining,
        "pct": pct,
        "over_threshold": over,
        "level": level,
        "message": message,
        "rows": inv_rows + dnr_rows + kpir_rows,
    }


def vat_exemption_status(year: int | None = None, *, jdg_registered_at: str = "") -> dict[str, Any]:
    from Komponenty._shared.tax_config import config_id

    if not jdg_registered_at:
        try:
            from Komponenty.kpir.storage import load_settings as load_kpir_settings

            kpir = load_kpir_settings()
            jdg_registered_at = str(kpir.jdg_registered_at or "")
        except ImportError:
            pass

    status = annual_turnover(year, jdg_registered_at=jdg_registered_at)
    status["config_id"] = config_id()
    return status
