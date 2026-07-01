"""Persystencja DNR — JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CostEntry, DnrSettings, SaleEntry

_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "dane"
_DOCUMENTS_DIR = _COMPONENT_DIR / "documents"
_SETTINGS_FILE = _DATA_DIR / "dnr_settings.json"
_DB_FILE = _DATA_DIR / "dnr.json"


def ensure_dirs() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    (_DOCUMENTS_DIR / "exports").mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data: Any) -> None:
    ensure_dirs()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> DnrSettings:
    raw = _read_json(_SETTINGS_FILE, {})
    return DnrSettings.from_dict(raw if isinstance(raw, dict) else {})


def save_settings(settings: DnrSettings) -> None:
    _write_json(_SETTINGS_FILE, settings.to_dict())


def load_db() -> dict[str, Any]:
    raw = _read_json(_DB_FILE, {"next_sale_id": 1, "next_cost_id": 1, "sales": [], "costs": []})
    if not isinstance(raw, dict):
        return {"next_sale_id": 1, "next_cost_id": 1, "sales": [], "costs": []}
    return raw


def save_db(db: dict[str, Any]) -> None:
    _write_json(_DB_FILE, db)


def new_sale_id() -> str:
    db = load_db()
    n = int(db.get("next_sale_id") or 1)
    db["next_sale_id"] = n + 1
    save_db(db)
    return f"DNR-S-{n:06d}"


def new_cost_id() -> str:
    db = load_db()
    n = int(db.get("next_cost_id") or 1)
    db["next_cost_id"] = n + 1
    save_db(db)
    return f"DNR-C-{n:06d}"


def list_sales() -> list[SaleEntry]:
    return [SaleEntry.from_dict(x) for x in (load_db().get("sales") or [])]


def get_sale(sale_id: str) -> SaleEntry | None:
    for s in list_sales():
        if s.id == sale_id:
            return s
    return None


def save_sale(entry: SaleEntry) -> None:
    db = load_db()
    rows = db.setdefault("sales", [])
    replaced = False
    for idx, row in enumerate(rows):
        if row.get("id") == entry.id:
            rows[idx] = entry.to_dict()
            replaced = True
            break
    if not replaced:
        rows.append(entry.to_dict())
    save_db(db)


def delete_sale_record(sale_id: str) -> bool:
    db = load_db()
    rows = db.get("sales") or []
    filtered = [r for r in rows if r.get("id") != sale_id]
    if len(filtered) == len(rows):
        return False
    db["sales"] = filtered
    save_db(db)
    return True


def sale_for_invoice(invoice_id: str) -> SaleEntry | None:
    for s in list_sales():
        if s.invoice_id == invoice_id:
            return s
    return None


def sale_for_shopify_order(shopify_order_id: int) -> SaleEntry | None:
    if not shopify_order_id:
        return None
    for s in list_sales():
        if s.shopify_order_id == shopify_order_id:
            return s
    return None


def list_costs() -> list[CostEntry]:
    return [CostEntry.from_dict(x) for x in (load_db().get("costs") or [])]


def get_cost(cost_id: str) -> CostEntry | None:
    for c in list_costs():
        if c.id == cost_id:
            return c
    return None


def save_cost(entry: CostEntry) -> None:
    db = load_db()
    rows = db.setdefault("costs", [])
    replaced = False
    for idx, row in enumerate(rows):
        if row.get("id") == entry.id:
            rows[idx] = entry.to_dict()
            replaced = True
            break
    if not replaced:
        rows.append(entry.to_dict())
    save_db(db)


def delete_cost_record(cost_id: str) -> bool:
    db = load_db()
    rows = db.get("costs") or []
    filtered = [r for r in rows if r.get("id") != cost_id]
    if len(filtered) == len(rows):
        return False
    db["costs"] = filtered
    save_db(db)
    return True


def exports_dir(year: int) -> Path:
    ensure_dirs()
    path = _DOCUMENTS_DIR / "exports" / f"{year:04d}"
    path.mkdir(parents=True, exist_ok=True)
    return path
