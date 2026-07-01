"""Import wyciągu bankowego → propozycje kosztów."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from .cost_service import create_cost

BankProvider = Literal["auto", "mbank", "pko", "ing", "generic"]


@dataclass
class BankTransaction:
    date: str
    description: str
    amount: float
    counterparty: str = ""


@dataclass
class BankImportResult:
    parsed: int = 0
    created_costs: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_amount(raw: str) -> float:
    s = str(raw or "").strip().replace(" ", "").replace("\xa0", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    return abs(float(s or 0))


def _parse_date(raw: str) -> str:
    raw = str(raw or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return raw


def _detect_columns(headers: list[str]) -> dict[str, int]:
    lower = [h.lower().strip() for h in headers]
    mapping: dict[str, int] = {}

    date_keys = ("data", "date", "data operacji", "data księgowania", "booking date")
    desc_keys = ("tytuł", "tytul", "opis", "description", "nazwa transakcji", "szczegóły")
    amt_keys = ("kwota", "amount", "wartość", "wartosc", "obciążenia", "obciazenia", "debit")
    party_keys = ("kontrahent", "nadawca", "odbiorca", "counterparty", "nazwa")

    for i, h in enumerate(lower):
        if any(k in h for k in date_keys) and "date" not in mapping:
            mapping["date"] = i
        if any(k in h for k in desc_keys) and "desc" not in mapping:
            mapping["desc"] = i
        if any(k in h for k in amt_keys) and "amount" not in mapping:
            mapping["amount"] = i
        if any(k in h for k in party_keys) and "party" not in mapping:
            mapping["party"] = i
    return mapping


def parse_bank_csv(path: str | Path, provider: BankProvider = "auto") -> list[BankTransaction]:
    path = Path(path)
    rows: list[BankTransaction] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.reader(f, delimiter=delimiter)
        all_rows = list(reader)
    if not all_rows:
        return rows

    header_idx = 0
    for i, row in enumerate(all_rows[:15]):
        joined = " ".join(row).lower()
        if any(k in joined for k in ("data", "kwota", "opis", "amount", "date")):
            header_idx = i
            break

    headers = all_rows[header_idx]
    cols = _detect_columns(headers)
    if "amount" not in cols:
        raise ValueError("Nie rozpoznano kolumny kwoty w pliku bankowym.")

    for row in all_rows[header_idx + 1:]:
        if len(row) <= max(cols.values()):
            continue
        amount = _parse_amount(row[cols["amount"]])
        if amount <= 0:
            continue
        desc = row[cols.get("desc", cols["amount"])].strip() if cols.get("desc") is not None else ""
        date_raw = row[cols.get("date", 0)] if cols.get("date") is not None else ""
        party = row[cols["party"]].strip() if cols.get("party") is not None else ""
        if not desc and not party:
            continue
        rows.append(BankTransaction(
            date=_parse_date(date_raw),
            description=desc or party,
            amount=amount,
            counterparty=party,
        ))
    _ = provider
    return rows


def _guess_category(description: str, counterparty: str) -> str:
    text = f"{description} {counterparty}".lower()
    rules = [
        (("shopify",), "abonament Shopify"),
        (("stripe",), "prowizje Stripe"),
        (("paypal",), "prowizje PayPal"),
        (("ovh", "cloudflare"), "hosting"),
        (("dhl", "dpd", "inpost", "kurier", "gls"), "kurier"),
        (("google ads", "facebook", "meta ads"), "reklamy"),
        (("hahnem", "papier", "fine art"), "papier fine art"),
        (("księgow", "ksiegow"), "usługi księgowe"),
    ]
    for keys, cat in rules:
        if any(k in text for k in keys):
            return cat
    return "inne"


def import_bank_csv(
    path: str | Path,
    provider: BankProvider = "auto",
    *,
    book: bool = False,
    skip_duplicates: bool = True,
) -> BankImportResult:
    from .cost_service import book_cost_to_kpir
    from .storage import list_costs

    result = BankImportResult()
    try:
        transactions = parse_bank_csv(path, provider)
    except Exception as exc:
        result.errors.append(str(exc))
        return result

    existing_docs = {c.document_number for c in list_costs() if c.document_number}
    result.parsed = len(transactions)

    for tx in transactions:
        doc_no = f"BANK/{tx.date}/{tx.amount:.2f}"
        if skip_duplicates and doc_no in existing_docs:
            result.skipped += 1
            continue
        cat = _guess_category(tx.description, tx.counterparty)
        try:
            cost = create_cost(
                issue_date=tx.date,
                event_date=tx.date,
                document_number=doc_no,
                seller=tx.counterparty or "Bank",
                description=tx.description[:200],
                category=cat,
                amount_gross=tx.amount,
                currency="PLN",
            )
            existing_docs.add(doc_no)
            result.created_costs += 1
            if book:
                book_cost_to_kpir(cost.id)
        except Exception as exc:
            result.errors.append(f"{tx.date}: {exc}")
    return result
