"""Archiwizacja starych zamowien.

Zrealizowane zamowienia (wyslane=True) starsze niz N miesiecy trafiaja do
osobnego pliku `archive_YYYY.json` (per rok zakonczenia). Plik glowny
`zamowienia.json` zostaje mniejszy -> lista szybciej sie laduje.

Wywolanie recznego:
    from Komponenty.produkcja.retention import archive_old_orders
    archive_old_orders(months=6)

Archiwa mozna przegladac - sa po prostu plikami JSON w tym samym formacie
co zamowienia.json (`{"orders": [...]}`).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from giclee_app.app_paths import atomic_write_text

from Komponenty.produkcja import production_store

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE


def _data_dir_override() -> Path | None:
    current = Path(_DATA_DIR)
    return current if current != _LEGACY_DATA_DIR else None


def _orders_path(*, for_write: bool) -> Path:
    explicit = Path(_ORDERS_FILE)
    if explicit != _LEGACY_ORDERS_FILE:
        return explicit
    override = _data_dir_override()
    if override is not None:
        return override / "zamowienia.json"
    return production_store.orders_write_path() if for_write else production_store.orders_read_path()


def _load_orders() -> dict:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_orders(db: dict) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\n",
    )


def _archive_file_for_year(year: int, *, for_write: bool = False) -> Path:
    override = _data_dir_override()
    if override is not None:
        return override / f"archive_{int(year)}.json"
    return (
        production_store.archive_write_path(year)
        if for_write
        else production_store.archive_read_path(year)
    )


def _load_archive(year: int) -> dict:
    path = _archive_file_for_year(year)
    if not path.is_file():
        return {"year": year, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"year": year, "orders": []}


def _save_archive(year: int, data: dict) -> None:
    atomic_write_text(
        _archive_file_for_year(year, for_write=True),
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    )


def archive_old_orders(
    *, months: int = 6, logger: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Przenosi wyslane zamowienia starsze niz `months` miesiecy do archive_YYYY.json.

    Zwraca {'archived': N, 'kept': M, 'errors': E}.
    """
    db = _load_orders()
    orders: list[dict] = db.get("orders") or []
    cutoff = date.today().replace(day=1)
    # Cofamy sie o `months` miesiecy
    y, m = cutoff.year, cutoff.month - months
    while m < 1:
        m += 12
        y -= 1
    cutoff = date(y, m, 1)

    archived_by_year: dict[int, list[dict]] = {}
    keep: list[dict] = []
    errors = 0

    for o in orders:
        if not o.get("wyslane"):
            keep.append(o)
            continue
        raw = o.get("data_wyslania") or o.get("data_zamowienia") or ""
        try:
            d = date.fromisoformat(str(raw))
        except ValueError:
            keep.append(o)
            errors += 1
            continue
        if d < cutoff:
            archived_by_year.setdefault(d.year, []).append(o)
        else:
            keep.append(o)

    # Zapis do archiwow
    archived_total = 0
    for year, items in archived_by_year.items():
        arch = _load_archive(year)
        existing_ids = {o.get("id") for o in arch.get("orders") or []}
        for item in items:
            if item.get("id") in existing_ids:
                continue
            arch.setdefault("orders", []).append(item)
            existing_ids.add(item.get("id"))
            archived_total += 1
        arch["last_archived_at"] = datetime.now().isoformat(timespec="seconds")
        _save_archive(year, arch)
        if logger:
            logger(f"[retention] Zapisano {len(items)} zamowien do archive_{year}.json")

    # Zapis zmniejszonego zamowienia.json
    if archived_total > 0:
        db["orders"] = keep
        _save_orders(db)

    if logger:
        logger(
            f"[retention] Zarchiwizowano: {archived_total}, "
            f"pozostalo aktywnych: {len(keep)}, bledow dat: {errors}"
        )
    return {
        "archived": archived_total,
        "kept": len(keep),
        "errors": errors,
    }


def list_archives() -> list[dict[str, Any]]:
    """Zwraca metadane wszystkich plikow archive_YYYY.json."""
    out: list[dict[str, Any]] = []
    override = _data_dir_override()
    if override is not None:
        paths = sorted(override.glob("archive_*.json")) if override.is_dir() else []
    else:
        paths = production_store.archive_read_paths()
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            orders = data.get("orders") or []
        except (OSError, json.JSONDecodeError):
            orders = []
        out.append({
            "year": p.stem.replace("archive_", ""),
            "path": str(p),
            "count": len(orders),
        })
    return out
