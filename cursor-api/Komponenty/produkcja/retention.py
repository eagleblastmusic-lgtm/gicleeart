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

_DATA_DIR = Path(__file__).resolve().parent / "dane"
_ORDERS_FILE = _DATA_DIR / "zamowienia.json"


def _load_orders() -> dict:
    if not _ORDERS_FILE.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_orders(db: dict) -> None:
    _ORDERS_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _archive_file_for_year(year: int) -> Path:
    return _DATA_DIR / f"archive_{year}.json"


def _load_archive(year: int) -> dict:
    p = _archive_file_for_year(year)
    if not p.is_file():
        return {"year": year, "orders": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"year": year, "orders": []}


def _save_archive(year: int, data: dict) -> None:
    p = _archive_file_for_year(year)
    p.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
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
    if not _DATA_DIR.is_dir():
        return out
    for p in sorted(_DATA_DIR.glob("archive_*.json")):
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
