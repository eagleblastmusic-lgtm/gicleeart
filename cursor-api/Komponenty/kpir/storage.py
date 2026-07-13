"""Persystencja KPiR poza repozytorium.

AppData jest lokalizacją nadrzędną. Stare pliki pozostają tymczasowym
fallbackiem tylko do odczytu, a wszystkie nowe zapisy i eksporty trafiają
poza checkout źródłowy.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from giclee_app.app_paths import AppPath, atomic_write_text, config_path, data_path

from .models import (
    ChangeLogEntry,
    CompanyVehicle,
    CostRecord,
    FixedAsset,
    FxSettlement,
    GoodsReceiptPending,
    IntangibleAsset,
    InventoryRecord,
    KpirEntry,
    KpirSettings,
    MileageLogEntry,
    MonthClosure,
    RecurringCost,
    SalesRegisterEntry,
    YearClosure,
)

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_LEGACY_DOCUMENTS_DIR = _COMPONENT_DIR / "documents"
_DEFAULT_SETTINGS_FILE = _LEGACY_DATA_DIR / "kpir_settings.json"
_DEFAULT_DB_FILE = _LEGACY_DATA_DIR / "kpir.json"
_DEFAULT_CHANGELOG_FILE = _LEGACY_DATA_DIR / "kpir_changelog.jsonl"

# Compatibility aliases retained for existing verification helpers that
# intentionally redirect storage to a temporary directory.
_DATA_DIR = _LEGACY_DATA_DIR
_DOCUMENTS_DIR = _LEGACY_DOCUMENTS_DIR
_SETTINGS_FILE = _DEFAULT_SETTINGS_FILE
_DB_FILE = _DEFAULT_DB_FILE
_CHANGELOG_FILE = _DEFAULT_CHANGELOG_FILE

_SETTINGS = config_path(
    "Komponenty/kpir/dane/kpir_settings.json",
    legacy=_DEFAULT_SETTINGS_FILE,
)
_DB = data_path(
    "Komponenty/kpir/dane/kpir.json",
    legacy=_DEFAULT_DB_FILE,
)
_CHANGELOG = data_path(
    "Komponenty/kpir/dane/kpir_changelog.jsonl",
    legacy=_DEFAULT_CHANGELOG_FILE,
)
_DOCUMENTS_MARKER = data_path(
    "Komponenty/kpir/documents/.path",
    legacy=_LEGACY_DOCUMENTS_DIR / ".path",
)

_StoreName = Literal["settings", "db", "changelog"]
_STORE_SPECS: dict[_StoreName, tuple[str, str, AppPath, str]] = {
    "settings": (
        "_SETTINGS_FILE",
        "_DEFAULT_SETTINGS_FILE",
        _SETTINGS,
        "kpir_settings.json",
    ),
    "db": (
        "_DB_FILE",
        "_DEFAULT_DB_FILE",
        _DB,
        "kpir.json",
    ),
    "changelog": (
        "_CHANGELOG_FILE",
        "_DEFAULT_CHANGELOG_FILE",
        _CHANGELOG,
        "kpir_changelog.jsonl",
    ),
}


def _store_spec(name: _StoreName) -> tuple[str, str, AppPath, str]:
    try:
        return _STORE_SPECS[name]
    except KeyError as exc:  # pragma: no cover - Literal + explicit tests
        raise ValueError(f"Nieznany magazyn KPiR: {name!r}") from exc


def _compat_store_override(name: _StoreName) -> Path | None:
    """Zwróć jawny override testowy/narzędziowy, jeśli jest aktywny."""

    current_name, default_name, _spec, filename = _store_spec(name)
    current = Path(globals()[current_name])
    default = Path(globals()[default_name])
    if current != default:
        return current
    if Path(_DATA_DIR) != _LEGACY_DATA_DIR:
        return Path(_DATA_DIR) / filename
    return None


def _read_store_path(name: _StoreName) -> Path:
    """AppData-first read z read-only fallbackiem do legacy."""

    _current_name, _default_name, spec, _filename = _store_spec(name)
    override = _compat_store_override(name)
    return override if override is not None else spec.read_path()


def _write_store_path(name: _StoreName) -> Path:
    """Jedyna granica zapisu dla plikowych magazynów KPiR."""

    _current_name, _default_name, spec, _filename = _store_spec(name)
    override = _compat_store_override(name)
    return override if override is not None else spec.write_path


def _documents_base() -> Path:
    if Path(_DOCUMENTS_DIR) != _LEGACY_DOCUMENTS_DIR:
        return Path(_DOCUMENTS_DIR)
    return _DOCUMENTS_MARKER.write_path.parent


def ensure_dirs() -> None:
    _write_store_path("db").parent.mkdir(parents=True, exist_ok=True)
    _write_store_path("settings").parent.mkdir(parents=True, exist_ok=True)
    for sub in (
        "sales",
        "costs",
        "invoices",
        "corrections",
        "kpir",
        "exports",
        "inventory",
        "fixed_assets",
    ):
        (_documents_base() / sub).mkdir(parents=True, exist_ok=True)


def documents_dir_for(sub: str, year: int, month: int) -> Path:
    """Zwraca zewnętrzny katalog `documents/<sub>/YYYY/MM/`."""

    path = _documents_base() / sub / f"{year:04d}" / f"{month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(store_name: Literal["settings", "db"], default: Any) -> Any:
    path = _read_store_path(store_name)
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(store_name: Literal["settings", "db"], data: Any) -> None:
    atomic_write_text(
        _write_store_path(store_name),
        json.dumps(data, ensure_ascii=False, indent=2),
    )


def load_settings() -> KpirSettings:
    raw = _read_json("settings", {})
    return KpirSettings.from_dict(raw if isinstance(raw, dict) else {})


def save_settings(settings: KpirSettings) -> None:
    _write_json("settings", settings.to_dict())


def _empty_db() -> dict[str, Any]:
    return {
        "next_entry_id": 1,
        "next_cost_id": 1,
        "next_recurring_id": 1,
        "entries": [],
        "costs": [],
        "recurring": [],
        "month_closures": [],
        "skipped_orders": [],
        "inventories": [],
        "fixed_assets": [],
        "sales_register": [],
        "goods_receipts_pending": [],
        "year_closures": [],
        "intangible_assets": [],
        "vehicles": [],
        "mileage_log": [],
        "fx_settlements": [],
    }


def load_db() -> dict[str, Any]:
    raw = _read_json("db", _empty_db())
    return raw if isinstance(raw, dict) else _empty_db()


def save_db(db: dict[str, Any]) -> None:
    _write_json("db", db)


def _list_collection(key: str, model_cls):
    db = load_db()
    return [model_cls.from_dict(x) for x in (db.get(key) or [])]


def _save_collection_item(key: str, item, id_field: str = "id") -> None:
    db = load_db()
    rows = db.setdefault(key, [])
    data = item.to_dict()
    item_id = data.get(id_field)
    for idx, row in enumerate(rows):
        if row.get(id_field) == item_id:
            rows[idx] = data
            save_db(db)
            return
    rows.append(data)
    save_db(db)


def _next_seq(key: str, prefix: str) -> str:
    db = load_db()
    n = int(db.get(key) or 1)
    db[key] = n + 1
    save_db(db)
    return f"{prefix}-{n:06d}"


def list_entries() -> list[KpirEntry]:
    return _list_collection("entries", KpirEntry)


def get_entry(entry_id: str) -> KpirEntry | None:
    for entry in list_entries():
        if entry.id == entry_id:
            return entry
    return None


def save_entry(entry: KpirEntry) -> None:
    _save_collection_item("entries", entry)


def new_entry_id() -> str:
    return _next_seq("next_entry_id", "KPIR")


def new_entry_number(year: int | None = None) -> str:
    selected_year = year or datetime.now().year
    db = load_db()
    key = f"entry_seq_{selected_year}"
    number = int(db.get(key) or 1)
    db[key] = number + 1
    save_db(db)
    return f"K/{selected_year}/{number:04d}"


def list_costs() -> list[CostRecord]:
    return _list_collection("costs", CostRecord)


def get_cost(cost_id: str) -> CostRecord | None:
    for cost in list_costs():
        if cost.id == cost_id:
            return cost
    return None


def save_cost(cost: CostRecord) -> None:
    _save_collection_item("costs", cost)


def delete_cost_record(cost_id: str) -> bool:
    """Usuwa koszt z bazy. Zwraca False, gdy nie znaleziono."""

    db = load_db()
    rows = db.get("costs") or []
    filtered = [row for row in rows if row.get("id") != cost_id]
    if len(filtered) == len(rows):
        return False
    db["costs"] = filtered
    save_db(db)
    return True


def delete_entry_record(entry_id: str) -> bool:
    """Usuwa wpis KPiR z bazy (np. po usunięciu faktury testowej)."""

    db = load_db()
    rows = db.get("entries") or []
    filtered = [row for row in rows if row.get("id") != entry_id]
    if len(filtered) == len(rows):
        return False
    db["entries"] = filtered
    save_db(db)
    return True


def new_cost_id() -> str:
    return _next_seq("next_cost_id", "COST")


def list_recurring() -> list[RecurringCost]:
    return _list_collection("recurring", RecurringCost)


def save_recurring(item: RecurringCost) -> None:
    _save_collection_item("recurring", item)


def delete_recurring(item_id: str) -> None:
    db = load_db()
    db["recurring"] = [
        row for row in (db.get("recurring") or []) if row.get("id") != item_id
    ]
    save_db(db)


def new_recurring_id() -> str:
    return _next_seq("next_recurring_id", "REC")


def list_month_closures() -> list[MonthClosure]:
    return _list_collection("month_closures", MonthClosure)


def get_month_closure(year: int, month: int) -> MonthClosure | None:
    for closure in list_month_closures():
        if closure.year == year and closure.month == month:
            return closure
    return None


def save_month_closure(closure: MonthClosure) -> None:
    db = load_db()
    rows = db.setdefault("month_closures", [])
    for idx, row in enumerate(rows):
        if row.get("year") == closure.year and row.get("month") == closure.month:
            rows[idx] = closure.to_dict()
            save_db(db)
            return
    rows.append(closure.to_dict())
    save_db(db)


def is_month_closed(year: int, month: int) -> bool:
    closure = get_month_closure(year, month)
    return bool(closure and closure.is_closed)


def entries_for_order(shopify_order_id: int) -> list[KpirEntry]:
    return [
        entry
        for entry in list_entries()
        if entry.shopify_order_id == shopify_order_id
        and entry.status in ("posted", "corrected", "draft")
    ]


def posted_entry_for_order(shopify_order_id: int) -> KpirEntry | None:
    for entry in list_entries():
        if (
            entry.shopify_order_id == shopify_order_id
            and entry.entry_type == "revenue"
            and entry.status in ("posted", "corrected")
            and entry.source in ("shopify", "invoice")
        ):
            return entry
    return None


def posted_entry_for_invoice(invoice_id: str) -> KpirEntry | None:
    for entry in list_entries():
        if entry.invoice_id == invoice_id and entry.status in ("posted", "corrected"):
            return entry
    return None


def posted_entry_for_dnr_sale(dnr_sale_id: str) -> KpirEntry | None:
    for entry in list_entries():
        if entry.dnr_sale_id == dnr_sale_id and entry.status in ("posted", "corrected"):
            return entry
    return None


def posted_entry_for_dnr_cost(dnr_cost_id: str) -> KpirEntry | None:
    for entry in list_entries():
        if entry.dnr_cost_id == dnr_cost_id and entry.status in ("posted", "corrected"):
            return entry
    return None


def skip_order(shopify_order_id: int) -> None:
    db = load_db()
    skipped = set(db.get("skipped_orders") or [])
    skipped.add(shopify_order_id)
    db["skipped_orders"] = sorted(skipped)
    save_db(db)


def is_order_skipped(shopify_order_id: int) -> bool:
    return shopify_order_id in (load_db().get("skipped_orders") or [])


def append_changelog(entry: ChangeLogEntry) -> None:
    override = _compat_store_override("changelog")
    if override is None:
        path = _CHANGELOG.seed_from_legacy()
    else:
        path = override
        path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")


def new_changelog_id() -> str:
    return str(uuid.uuid4())[:12]


def list_changelog_for_entry(entry_id: str) -> list[ChangeLogEntry]:
    path = _read_store_path("changelog")
    if not path.is_file():
        return []
    output: list[ChangeLogEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if data.get("entry_id") == entry_id:
            output.append(ChangeLogEntry.from_dict(data))
    return output


def list_inventories() -> list[InventoryRecord]:
    return _list_collection("inventories", InventoryRecord)


def get_inventory(inventory_id: str) -> InventoryRecord | None:
    for item in list_inventories():
        if item.id == inventory_id:
            return item
    return None


def save_inventory(record: InventoryRecord) -> None:
    _save_collection_item("inventories", record)


def new_inventory_id() -> str:
    return _next_seq("next_inventory_id", "INV")


def list_fixed_assets() -> list[FixedAsset]:
    return _list_collection("fixed_assets", FixedAsset)


def get_fixed_asset(asset_id: str) -> FixedAsset | None:
    for item in list_fixed_assets():
        if item.id == asset_id:
            return item
    return None


def save_fixed_asset(asset: FixedAsset) -> None:
    _save_collection_item("fixed_assets", asset)


def new_fixed_asset_id() -> str:
    return _next_seq("next_fixed_asset_id", "ST")


def list_sales_register() -> list[SalesRegisterEntry]:
    return _list_collection("sales_register", SalesRegisterEntry)


def save_sales_register(entry: SalesRegisterEntry) -> None:
    _save_collection_item("sales_register", entry)


def new_sales_register_id() -> str:
    return _next_seq("next_sales_register_id", "ES")


def list_goods_receipts_pending() -> list[GoodsReceiptPending]:
    return _list_collection("goods_receipts_pending", GoodsReceiptPending)


def save_goods_receipt_pending(item: GoodsReceiptPending) -> None:
    _save_collection_item("goods_receipts_pending", item)


def new_goods_receipt_id() -> str:
    return _next_seq("next_goods_receipt_id", "GR")


def list_intangible_assets() -> list[IntangibleAsset]:
    return _list_collection("intangible_assets", IntangibleAsset)


def save_intangible_asset(asset: IntangibleAsset) -> None:
    _save_collection_item("intangible_assets", asset)


def new_intangible_asset_id() -> str:
    return _next_seq("next_intangible_asset_id", "WN")


def list_vehicles() -> list[CompanyVehicle]:
    return _list_collection("vehicles", CompanyVehicle)


def save_vehicle(vehicle: CompanyVehicle) -> None:
    _save_collection_item("vehicles", vehicle)


def new_vehicle_id() -> str:
    return _next_seq("next_vehicle_id", "POJ")


def list_mileage_log() -> list[MileageLogEntry]:
    return _list_collection("mileage_log", MileageLogEntry)


def save_mileage_entry(entry: MileageLogEntry) -> None:
    _save_collection_item("mileage_log", entry)


def new_mileage_log_id() -> str:
    return _next_seq("next_mileage_log_id", "KM")


def list_fx_settlements() -> list[FxSettlement]:
    return _list_collection("fx_settlements", FxSettlement)


def save_fx_settlement(item: FxSettlement) -> None:
    _save_collection_item("fx_settlements", item)


def get_fx_settlement_for_entry(entry_id: str) -> FxSettlement | None:
    for item in list_fx_settlements():
        if item.entry_id == entry_id:
            return item
    return None


def new_fx_settlement_id() -> str:
    return _next_seq("next_fx_settlement_id", "FX")


def list_year_closures() -> list[YearClosure]:
    return _list_collection("year_closures", YearClosure)


def get_year_closure(year: int) -> YearClosure | None:
    for closure in list_year_closures():
        if closure.year == year:
            return closure
    return None


def save_year_closure(closure: YearClosure) -> None:
    db = load_db()
    rows = db.setdefault("year_closures", [])
    data = closure.to_dict()
    for idx, row in enumerate(rows):
        if row.get("year") == closure.year:
            rows[idx] = data
            save_db(db)
            return
    rows.append(data)
    save_db(db)


def is_year_closed(year: int) -> bool:
    closure = get_year_closure(year)
    return bool(closure and closure.is_closed)
