"""Monitory compliance: WSTO/OSS, KSeF B2B, import usług art. 28b."""

from __future__ import annotations

from datetime import date
from typing import Any

from Komponenty._shared.tax_config import ksef_monthly_gross_exemption, wsto_tbe_threshold_pln

_EU_FOREIGN_SERVICE_KEYWORDS = (
    "shopify", "subscription", "app", "saas", "platform", "stripe", "google", "meta",
    "facebook", "mailchimp", "klaviyo", "cloudflare",
)


def _year_month(iso: str) -> tuple[int, int] | None:
    if not iso or len(iso) < 7:
        return None
    try:
        return int(iso[:4]), int(iso[5:7])
    except ValueError:
        return None


def wsto_oss_status(year: int | None = None) -> dict[str, Any]:
    """Monitor progu WSTO/TBE 42 000 zł — sprzedaż B2C z PL do UE (bez pełnego silnika OSS)."""
    from Komponenty.dokumentysprzedazy.country import is_eu_b2c, is_poland, normalize_country
    from Komponenty.dokumentysprzedazy.invoice_helpers import is_test_invoice
    from Komponenty.dokumentysprzedazy.storage import list_invoices
    from Komponenty.dnr.storage import list_sales

    y = year or date.today().year
    threshold = wsto_tbe_threshold_pln()
    total = 0.0
    rows: list[dict[str, Any]] = []
    local_vat_review = False

    def _add_row(source: str, row_id: str, dt: str, amt: float, dest: str, fulfill: str, note: str) -> None:
        nonlocal total, local_vat_review
        if amt <= 0:
            return
        total += amt
        if fulfill and not is_poland(fulfill):
            local_vat_review = True
        rows.append({
            "source": source,
            "id": row_id,
            "date": dt,
            "amount_pln": round(amt, 2),
            "destination_country": dest,
            "fulfillment_country": fulfill or "PL",
            "note": note,
        })

    for inv in list_invoices():
        if is_test_invoice(inv):
            continue
        if inv.status not in ("issued", "corrected"):
            continue
        dt = inv.sale_date or inv.issue_date or ""
        if dt and int(dt[:4]) != y:
            continue
        dest = normalize_country(inv.shipping_address.country_code or inv.buyer.country_code)
        if not is_eu_b2c(dest):
            continue
        fulfill = normalize_country(getattr(inv, "fulfillment_country", "") or "PL")
        amt = float(inv.exchange.total_amount_pln or inv.order_total or 0)
        _add_row("invoice", inv.id, dt, amt, dest, fulfill, inv.invoice_number)

    for sale in list_sales():
        if sale.migrated_to_kpir_at or sale.merchant_of_record:
            continue
        if (sale.entry_kind or "sale") != "sale":
            continue
        if sale.event_date and int(sale.event_date[:4]) != y:
            continue
        dest = normalize_country(sale.destination_country or "")
        if not is_eu_b2c(dest):
            continue
        fulfill = normalize_country(sale.fulfillment_country or "PL")
        _add_row("dnr", sale.id, sale.event_date, float(sale.amount_pln or 0), dest, fulfill, sale.document_number)

    total = round(total, 2)
    remaining = round(max(0.0, threshold - total), 2)
    pct = round((total / threshold * 100) if threshold > 0 else 0, 1)
    over = total > threshold
    if over:
        level, message = "over", (
            f"Próg WSTO/TBE ({threshold:,.0f} zł) przekroczony o {total - threshold:,.2f} zł — "
            "rozważ OSS / VAT kraju konsumpcji."
        )
    elif pct >= 90:
        level, message = "warn", f"Zbliżasz się do progu WSTO ({remaining:,.2f} zł do {threshold:,.0f} zł)."
    elif pct >= 75:
        level, message = "caution", f"WSTO: wykorzystano {pct}% progu ({total:,.2f} zł)."
    else:
        level, message = "ok", f"WSTO B2C UE: {total:,.2f} / {threshold:,.0f} zł ({pct}%)."
    if local_vat_review:
        message += " Fulfillment spoza PL — sprawdź lokalną rejestrację VAT (OSS może nie wystarczyć)."

    return {
        "year": y,
        "wsto_total_pln": total,
        "threshold_pln": threshold,
        "remaining_pln": remaining,
        "pct": pct,
        "over_threshold": over,
        "oss_recommended": over,
        "local_vat_registration_review": local_vat_review,
        "level": level,
        "message": message,
        "rows": rows,
    }


def ksef_b2b_monthly_status(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    """Monitor uproszczenia KSeF: faktury B2B poza KSeF do 10 000 zł brutto/mies. (do końca 2026)."""
    from Komponenty.dokumentysprzedazy.invoice_helpers import is_test_invoice
    from Komponenty.dokumentysprzedazy.storage import list_invoices

    today = date.today()
    y = year or today.year
    m = month or today.month
    threshold = ksef_monthly_gross_exemption()
    gross = 0.0
    count = 0
    for inv in list_invoices():
        if is_test_invoice(inv):
            continue
        if inv.status not in ("issued", "corrected"):
            continue
        ym = _year_month(inv.issue_date or inv.sale_date or "")
        if not ym or ym != (y, m):
            continue
        if not (inv.invoice_requested and inv.invoice_customer_type == "company"):
            if not (inv.buyer.name and inv.invoice_customer_type):
                continue
        gross += float(inv.order_total or inv.exchange.total_amount_pln or 0)
        count += 1
    gross = round(gross, 2)
    over = gross > threshold
    return {
        "year": y,
        "month": m,
        "b2b_gross_pln": gross,
        "threshold_pln": threshold,
        "invoice_count": count,
        "ksef_required": over,
        "level": "over" if over else "ok",
        "message": (
            f"Faktury B2B w {m:02d}/{y}: {gross:,.2f} zł brutto — próg KSeF {threshold:,.0f} zł przekroczony."
            if over
            else f"Faktury B2B w {m:02d}/{y}: {gross:,.2f} zł / {threshold:,.0f} zł (uproszczenie poza KSeF)."
        ),
    }


def foreign_service_alerts(*, year: int | None = None) -> dict[str, Any]:
    """Alerty importu usług (art. 28b) i VAT-UE dla kosztów platformowych."""
    from Komponenty.dnr.storage import list_costs

    y = year or date.today().year
    alerts: list[dict[str, str]] = []
    for cost in list_costs():
        if cost.event_date and int(cost.event_date[:4]) != y:
            continue
        blob = f"{cost.seller} {cost.description} {cost.category}".lower()
        if not any(k in blob for k in _EU_FOREIGN_SERVICE_KEYWORDS):
            continue
        alerts.append({
            "id": cost.id,
            "date": cost.event_date,
            "seller": cost.seller or "?",
            "amount_pln": f"{cost.amount_pln:.2f}",
            "message": "Potencjalny import usług (art. 28b) — sprawdź VAT-UE i rozliczenie w JPK_VAT.",
        })
    return {
        "year": y,
        "count": len(alerts),
        "alerts": alerts,
        "vat_ue_recommended": len(alerts) > 0,
        "message": (
            f"{len(alerts)} koszt(ów) platformowych do weryfikacji (art. 28b / VAT-UE)."
            if alerts
            else "Brak oznaczonych kosztów platformowych do weryfikacji art. 28b."
        ),
    }
