"""Persystencja dokumentów sprzedaży poza repozytorium.

AppData jest lokalizacją nadrzędną. Stare pliki pozostają tymczasowym fallbackiem
wyłącznie do odczytu; wszystkie nowe JSON-y, zdarzenia i PDF-y trafiają do
Local AppData.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from giclee_app.app_paths import AppPath, atomic_write_text, cache_path, data_path

from .models import InvoiceRecord, InvoiceSettings

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_LEGACY_DOCUMENTS_DIR = _COMPONENT_DIR / "documents" / "invoices"
_SETTINGS = data_path(
    "Komponenty/dokumentysprzedazy/dane/invoice_settings.json",
    legacy=_LEGACY_DATA_DIR / "invoice_settings.json",
)
_INVOICES = data_path(
    "Komponenty/dokumentysprzedazy/dane/invoices.json",
    legacy=_LEGACY_DATA_DIR / "invoices.json",
)
_EXCHANGE_RATES = cache_path(
    "Komponenty/dokumentysprzedazy/dane/exchange_rates.json",
    legacy=_LEGACY_DATA_DIR / "exchange_rates.json",
)
_EVENTS = data_path(
    "Komponenty/dokumentysprzedazy/dane/invoice_events.jsonl",
    legacy=_LEGACY_DATA_DIR / "invoice_events.jsonl",
)
_DOCUMENTS_MARKER = data_path(
    "Komponenty/dokumentysprzedazy/documents/invoices/.path",
    legacy=_LEGACY_DOCUMENTS_DIR / ".path",
)


def _documents_dir() -> Path:
    return _DOCUMENTS_MARKER.write_path.parent


def ensure_dirs() -> None:
    _SETTINGS.write_path.parent.mkdir(parents=True, exist_ok=True)
    _DOCUMENTS_MARKER.write_path.parent.mkdir(parents=True, exist_ok=True)


def documents_dir_for_date(iso_date: str) -> Path:
    """Zwraca zewnętrzny katalog `documents/invoices/YYYY/MM/`."""

    try:
        dt = datetime.fromisoformat(iso_date[:10])
    except ValueError:
        dt = datetime.now()
    path = _documents_dir() / f"{dt.year:04d}" / f"{dt.month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(spec: AppPath, default: Any) -> Any:
    path = spec.read_path()
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(spec: AppPath, data: Any) -> None:
    atomic_write_text(
        spec.write_path,
        json.dumps(data, ensure_ascii=False, indent=2),
    )


def load_settings() -> InvoiceSettings:
    from Komponenty._shared.accounting_mode_sync import sync_invoice_settings_from_kpir
    from .numbering import migrate_numbering_series, reconcile_all_series

    raw = _read_json(_SETTINGS, {})
    settings = InvoiceSettings.from_dict(raw if isinstance(raw, dict) else {})
    settings = migrate_numbering_series(settings)
    settings = reconcile_all_series(settings)
    before = settings.seller.business_mode
    settings = sync_invoice_settings_from_kpir(settings)
    if settings.seller.business_mode != before:
        save_settings(settings)
    return settings


def save_settings(settings: InvoiceSettings) -> None:
    from .numbering import reconcile_all_series

    settings = reconcile_all_series(settings)
    _write_json(_SETTINGS, settings.to_dict())


def load_invoices_db() -> dict[str, Any]:
    raw = _read_json(_INVOICES, {"next_id": 1, "invoices": []})
    if not isinstance(raw, dict):
        return {"next_id": 1, "invoices": []}
    return raw


def save_invoices_db(db: dict[str, Any]) -> None:
    _write_json(_INVOICES, db)


def list_invoices() -> list[InvoiceRecord]:
    db = load_invoices_db()
    return [InvoiceRecord.from_dict(x) for x in (db.get("invoices") or [])]


def invoice_by_order_id(shopify_order_id: int) -> InvoiceRecord | None:
    for invoice in list_invoices():
        if invoice.shopify_order_id == shopify_order_id and invoice.doc_kind == "invoice" and invoice.status in (
            "issued",
            "corrected",
        ):
            return invoice
    return None


def invoices_for_order(shopify_order_id: int) -> list[InvoiceRecord]:
    return [invoice for invoice in list_invoices() if invoice.shopify_order_id == shopify_order_id]


def list_manual_invoices() -> list[InvoiceRecord]:
    return [invoice for invoice in list_invoices() if not invoice.shopify_order_id]


def get_invoice(invoice_id: str) -> InvoiceRecord | None:
    for invoice in list_invoices():
        if invoice.id == invoice_id:
            return invoice
    return None


def save_invoice(record: InvoiceRecord) -> None:
    db = load_invoices_db()
    rows = db.setdefault("invoices", [])
    replaced = False
    for idx, row in enumerate(rows):
        if row.get("id") == record.id:
            rows[idx] = record.to_dict()
            replaced = True
            break
    if not replaced:
        rows.append(record.to_dict())
    save_invoices_db(db)


def delete_invoice_record(invoice_id: str) -> bool:
    db = load_invoices_db()
    rows = db.get("invoices") or []
    filtered = [row for row in rows if row.get("id") != invoice_id]
    if len(filtered) == len(rows):
        return False
    db["invoices"] = filtered
    save_invoices_db(db)
    return True


def invoices_correcting(invoice_id: str) -> list[InvoiceRecord]:
    return [
        invoice
        for invoice in list_invoices()
        if invoice.corrected_from_invoice_id == invoice_id and invoice.status != "cancelled"
    ]


def new_invoice_id() -> str:
    db = load_invoices_db()
    n = int(db.get("next_id") or 1)
    db["next_id"] = n + 1
    save_invoices_db(db)
    return f"INV-{n:06d}"


def load_exchange_rates_cache() -> list[dict[str, Any]]:
    raw = _read_json(_EXCHANGE_RATES, {"rates": []})
    if isinstance(raw, dict):
        return list(raw.get("rates") or [])
    return []


def save_exchange_rates_cache(rates: list[dict[str, Any]]) -> None:
    _write_json(_EXCHANGE_RATES, {"rates": rates})


def find_cached_rate(currency: str, rate_date: str) -> dict[str, Any] | None:
    cur = currency.upper()
    for row in load_exchange_rates_cache():
        if str(row.get("currency") or "").upper() == cur and str(row.get("rate_date") or "") == rate_date:
            return row
    return None


def store_exchange_rate(row: dict[str, Any]) -> None:
    rates = load_exchange_rates_cache()
    key = (str(row.get("currency") or "").upper(), str(row.get("rate_date") or ""))
    rates = [
        item
        for item in rates
        if (str(item.get("currency") or "").upper(), str(item.get("rate_date") or "")) != key
    ]
    rates.append(row)
    save_exchange_rates_cache(rates)


def append_event(action: str, invoice_id: str, *, details: str = "", actor: str = "user") -> None:
    entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "invoice_id": invoice_id,
        "actor": actor,
        "details": details,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    path = _EVENTS.seed_from_legacy()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_events(invoice_id: str | None = None) -> list[dict[str, Any]]:
    path = _EVENTS.read_path()
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if invoice_id and row.get("invoice_id") != invoice_id:
            continue
        out.append(row)
    return out
