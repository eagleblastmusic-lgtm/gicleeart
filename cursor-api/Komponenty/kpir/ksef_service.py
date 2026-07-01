"""KSeF — numer e-faktury w fakturze i wpisie KPiR (kol. 3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from Komponenty.dokumentysprzedazy.invoice_helpers import is_bookable_invoice
from Komponenty.dokumentysprzedazy.models import InvoiceRecord
from Komponenty.dokumentysprzedazy.storage import get_invoice, list_invoices, save_invoice

from .entry_service import update_entry
from .storage import posted_entry_for_invoice


_KSEF_RE = re.compile(r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$")


def normalize_ksef_number(value: str) -> str:
    return str(value or "").strip()


def is_valid_ksef_format(value: str) -> bool:
    v = normalize_ksef_number(value)
    if not v:
        return True
    return bool(_KSEF_RE.match(v))


def is_b2b_invoice(invoice: InvoiceRecord) -> bool:
    nip = normalize_ksef_number(invoice.buyer.nip if invoice.buyer else "")
    if nip:
        return True
    return invoice.invoice_customer_type == "company"


@dataclass
class KsefSyncRow:
    invoice_id: str
    invoice_number: str
    sale_date: str
    buyer_name: str
    buyer_nip: str
    ksef_number: str
    kpir_status: str
    entry_number: str
    entry_ksef: str
    needs_ksef: bool
    sync_ok: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice_number,
            "sale_date": self.sale_date,
            "buyer_name": self.buyer_name,
            "buyer_nip": self.buyer_nip,
            "ksef_number": self.ksef_number,
            "kpir_status": self.kpir_status,
            "entry_number": self.entry_number,
            "entry_ksef": self.entry_ksef,
            "needs_ksef": self.needs_ksef,
            "sync_ok": self.sync_ok,
        }


def list_ksef_sync_rows(*, year: int | None = None, month: int | None = None) -> list[KsefSyncRow]:
    from Komponenty._shared.compliance_monitors import ksef_b2b_monthly_status
    from Komponenty.kpir.order_status import get_invoice_kpir_status

    ksef_required_month = False
    if year and month:
        st = ksef_b2b_monthly_status(year, month)
        ksef_required_month = bool(st.get("ksef_required"))

    rows: list[KsefSyncRow] = []
    for inv in list_invoices():
        if not is_bookable_invoice(inv):
            continue
        sale = (inv.sale_date or inv.issue_date or "")[:10]
        if year:
            try:
                iy, im = int(sale[:4]), int(sale[5:7])
            except (ValueError, IndexError):
                continue
            if iy != year:
                continue
            if month and im != month:
                continue
        st = get_invoice_kpir_status(inv.id)
        entry = posted_entry_for_invoice(inv.id)
        entry_ksef = entry.ksef_number if entry else ""
        ksef = normalize_ksef_number(inv.ksef_number)
        b2b = is_b2b_invoice(inv)
        needs = b2b and ksef_required_month and not ksef
        sync_ok = (not ksef) or (ksef == normalize_ksef_number(entry_ksef))
        rows.append(KsefSyncRow(
            invoice_id=inv.id,
            invoice_number=inv.invoice_number,
            sale_date=sale,
            buyer_name=(inv.buyer.name if inv.buyer else "")[:40],
            buyer_nip=normalize_ksef_number(inv.buyer.nip if inv.buyer else ""),
            ksef_number=ksef,
            kpir_status=st.status,
            entry_number=st.entry_number or "",
            entry_ksef=entry_ksef,
            needs_ksef=needs,
            sync_ok=sync_ok,
        ))
    return sorted(rows, key=lambda r: r.sale_date, reverse=True)


def set_invoice_ksef(invoice_id: str, ksef_number: str, *, buyer_nip: str = "") -> InvoiceRecord:
    inv = get_invoice(invoice_id)
    if not inv:
        raise ValueError("Nie znaleziono faktury.")
    ksef = normalize_ksef_number(ksef_number)
    if ksef and not is_valid_ksef_format(ksef):
        raise ValueError("Numer KSeF powinien mieć format UUID (np. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).")
    inv.ksef_number = ksef
    if buyer_nip:
        inv.buyer.nip = normalize_ksef_number(buyer_nip)
    save_invoice(inv)
    sync_ksef_to_kpir(invoice_id)
    return inv


def sync_ksef_to_kpir(invoice_id: str) -> bool:
    """Kopiuje ksef_number i NIP nabywcy z faktury do wpisu KPiR."""
    inv = get_invoice(invoice_id)
    if not inv:
        return False
    entry = posted_entry_for_invoice(invoice_id)
    if not entry:
        return False
    ksef = normalize_ksef_number(inv.ksef_number)
    nip = normalize_ksef_number(inv.buyer.nip if inv.buyer else "")
    changed = False
    if entry.ksef_number != ksef:
        entry.ksef_number = ksef
        changed = True
    if nip and entry.contractor_nip != nip:
        entry.contractor_nip = nip
        changed = True
    if changed:
        update_entry(entry, reason="sync KSeF z faktury")
    return changed


def sync_all_ksef_to_kpir(*, year: int | None = None, month: int | None = None) -> dict[str, int]:
    synced = 0
    skipped = 0
    for row in list_ksef_sync_rows(year=year, month=month):
        if not row.ksef_number:
            skipped += 1
            continue
        if sync_ksef_to_kpir(row.invoice_id):
            synced += 1
        else:
            skipped += 1
    return {"synced": synced, "skipped": skipped}


def apply_ksef_on_booking(invoice: InvoiceRecord) -> tuple[str, str]:
    """Zwraca (ksef_number, contractor_nip) do create_entry."""
    return (
        normalize_ksef_number(invoice.ksef_number),
        normalize_ksef_number(invoice.buyer.nip if invoice.buyer else ""),
    )
