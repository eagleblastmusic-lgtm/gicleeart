"""Import prowizji z CSV — Stripe, PayPal, Shopify Payments."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from .cost_service import book_cost_to_kpir, create_cost
from .storage import list_costs
from .validation import ValidationError

FeeProvider = Literal["stripe", "paypal", "shopify", "auto"]

_PROVIDER_CATEGORIES = {
    "stripe": "prowizje Stripe",
    "paypal": "prowizje PayPal",
    "shopify": "prowizje Shopify",
}

_PROVIDER_SELLERS = {
    "stripe": "Stripe",
    "paypal": "PayPal",
    "shopify": "Shopify Payments",
}


@dataclass
class FeeImportRow:
    event_date: str
    document_number: str
    description: str
    amount: float
    currency: str
    provider: str
    external_id: str = ""
    order_ref: str = ""

    def fingerprint(self) -> str:
        return f"{self.provider}:{self.external_id or self.document_number}"


@dataclass
class FeeImportResult:
    provider: str
    parsed: int = 0
    created_costs: int = 0
    booked: int = 0
    skipped_duplicates: int = 0
    errors: list[str] = field(default_factory=list)
    cost_ids: list[str] = field(default_factory=list)
    bulk_entry_id: str = ""


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", " ", (h or "").strip().lower())


def _parse_float(val: Any) -> float:
    if val is None:
        return 0.0
    s = str(val).strip().replace("\xa0", "").replace(" ", "")
    if not s:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -abs(v) if neg else v


def _parse_date(val: str) -> str:
    raw = (val or "").strip()
    if not raw:
        return datetime.now().date().isoformat()
    raw = raw.replace("Z", "").replace(" UTC", "")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(raw[:19], fmt).date().isoformat()
        except ValueError:
            continue
    if "T" in raw:
        try:
            return datetime.fromisoformat(raw[:19]).date().isoformat()
        except ValueError:
            pass
    return raw[:10] if len(raw) >= 10 else datetime.now().date().isoformat()


def _find_col(headers: list[str], *candidates: str) -> int | None:
    norm = [_norm_header(h) for h in headers]
    for cand in candidates:
        c = cand.lower()
        for i, h in enumerate(norm):
            if c == h or c in h:
                return i
    return None


def detect_provider(path: Path) -> FeeProvider:
    name = path.name.lower()
    if "stripe" in name:
        return "stripe"
    if "paypal" in name:
        return "paypal"
    if "shopify" in name or "payout" in name:
        return "shopify"
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            row = next(csv.reader(f), [])
        joined = " ".join(_norm_header(x) for x in row)
        if "fee" in joined and "net" in joined and "captured" in joined:
            return "stripe"
        if "opłata" in joined or "opłata" in joined or "paypal" in joined:
            return "paypal"
        if "shopify" in joined or "payout" in joined:
            return "shopify"
    except OSError:
        pass
    return "auto"


def _read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    for enc in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                return [], []
            return rows[0], rows[1:]
        except (OSError, UnicodeDecodeError):
            continue
    raise ValidationError(f"Nie można odczytać pliku CSV: {path}")


def parse_fee_csv(path: Path | str, provider: FeeProvider = "auto") -> list[FeeImportRow]:
    p = Path(path)
    if not p.is_file():
        raise ValidationError(f"Brak pliku: {p}")

    if provider == "auto":
        provider = detect_provider(p)

    headers, data_rows = _read_csv_rows(p)
    if not headers:
        return []

    fee_col = _find_col(headers, "fee", "opłata", "oplata", "prowizja", "charge fee")
    date_col = _find_col(
        headers, "created (utc)", "created", "date", "data", "transaction date", "posting date",
    )
    amount_col = _find_col(headers, "amount", "gross", "brutto", "kwota brutto", "total")
    currency_col = _find_col(headers, "currency", "waluta")
    desc_col = _find_col(headers, "description", "opis", "nazwa", "type")
    id_col = _find_col(headers, "id", "transaction id", "identyfikator transakcji", "reference txn id")
    order_col = _find_col(headers, "order", "order id", "shopify", "metadata order")

    if fee_col is None and amount_col is None:
        raise ValidationError(
            "Nie rozpoznano kolumn CSV. Oczekiwane: Fee/Opłata lub Amount/Kwota.",
        )

    prov = provider if provider != "auto" else "stripe"
    out: list[FeeImportRow] = []

    for row in data_rows:
        if not row or all(not str(c).strip() for c in row):
            continue

        def cell(idx: int | None) -> str:
            if idx is None or idx >= len(row):
                return ""
            return str(row[idx]).strip()

        fee = _parse_float(cell(fee_col)) if fee_col is not None else 0.0
        if fee_col is None and amount_col is not None:
            amt = _parse_float(cell(amount_col))
            if prov == "paypal" and amt < 0:
                fee = abs(amt)
        if fee == 0:
            continue
        fee = abs(fee)

        event_date = _parse_date(cell(date_col))
        currency = (cell(currency_col) or "PLN").upper()[:3]
        desc = cell(desc_col) or f"Prowizja {_PROVIDER_SELLERS.get(prov, prov)}"
        ext_id = cell(id_col)
        order_ref = cell(order_col)
        doc_no = ext_id or f"{prov.upper()}/{event_date}/{len(out) + 1}"

        out.append(FeeImportRow(
            event_date=event_date,
            document_number=doc_no,
            description=desc,
            amount=round(fee, 2),
            currency=currency,
            provider=prov,
            external_id=ext_id,
            order_ref=order_ref,
        ))

    return out


def _existing_fingerprints() -> set[str]:
    fps: set[str] = set()
    for c in list_costs():
        if c.document_number:
            fps.add(c.document_number)
        if c.description and c.category.startswith("prowizje"):
            fps.add(f"{c.seller}:{c.document_number}")
    return fps


def import_fee_rows(
    rows: list[FeeImportRow],
    *,
    book: bool = False,
    aggregate_monthly: bool = False,
) -> FeeImportResult:
    if not rows:
        raise ValidationError("Brak wierszy do importu.")

    provider = rows[0].provider
    result = FeeImportResult(provider=provider, parsed=len(rows))
    existing = _existing_fingerprints()

    if aggregate_monthly:
        buckets: dict[str, list[FeeImportRow]] = {}
        for r in rows:
            key = r.event_date[:7]
            buckets.setdefault(key, []).append(r)

        for month_key, group in sorted(buckets.items()):
            total = round(sum(g.amount for g in group), 2)
            if total <= 0:
                continue
            doc = f"PROW/{provider.upper()}/{month_key}"
            if doc in existing:
                result.skipped_duplicates += len(group)
                continue
            cat = _PROVIDER_CATEGORIES.get(provider, "prowizje Stripe")
            seller = _PROVIDER_SELLERS.get(provider, provider)
            cost = create_cost(
                issue_date=f"{month_key}-01",
                event_date=f"{month_key}-28",
                document_number=doc,
                seller=seller,
                description=f"Prowizje {seller} — {month_key} ({len(group)} transakcji)",
                category=cat,
                amount_gross=total,
                currency=group[0].currency,
                is_internal_doc=True,
                is_paid=True,
            )
            result.created_costs += 1
            result.cost_ids.append(cost.id)
            existing.add(doc)
            if book:
                try:
                    book_cost_to_kpir(cost.id)
                    result.booked += 1
                except ValidationError as exc:
                    result.errors.append(str(exc))

        return result

    for row in rows:
        fp = row.fingerprint()
        if fp in existing or row.document_number in existing:
            result.skipped_duplicates += 1
            continue
        cat = _PROVIDER_CATEGORIES.get(row.provider, "prowizje Stripe")
        seller = _PROVIDER_SELLERS.get(row.provider, row.provider)
        desc = row.description
        if row.order_ref:
            desc += f" ({row.order_ref})"
        try:
            cost = create_cost(
                issue_date=row.event_date,
                event_date=row.event_date,
                document_number=row.document_number,
                seller=seller,
                description=desc,
                category=cat,
                amount_gross=row.amount,
                currency=row.currency,
                is_paid=True,
            )
            result.created_costs += 1
            result.cost_ids.append(cost.id)
            existing.add(fp)
            existing.add(row.document_number)
            if book:
                book_cost_to_kpir(cost.id)
                result.booked += 1
        except ValidationError as exc:
            result.errors.append(f"{row.document_number}: {exc}")

    return result


def import_fee_csv(
    path: Path | str,
    provider: FeeProvider = "auto",
    *,
    book: bool = False,
    aggregate_monthly: bool = False,
) -> FeeImportResult:
    rows = parse_fee_csv(path, provider)
    if not rows:
        raise ValidationError("Nie znaleziono prowizji w pliku CSV.")
    return import_fee_rows(rows, book=book, aggregate_monthly=aggregate_monthly)
