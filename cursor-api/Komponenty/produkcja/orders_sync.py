"""Synchronizacja zamowien Shopify -> lokalna baza produkcji.

Algorytm pollingu:
1. Czytamy `data/sync_state.json` z pamiecia ostatniej sync (`last_sync_iso`).
2. Wolamy `sc.iter_orders_since(updated_at_min=last_sync_iso, financial_status='paid')`.
3. Dla kazdego order.line_item tworzymy zamowienie w `zamowienia.json` jesli jeszcze
   nie ma (dedup po `shopify_order_no + shopify_line_item_id`).
4. Zapisujemy nowe `last_sync_iso = now()`.

Wymaga scope `read_orders` (patrz `shopify.app.toml` - scopes).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from Komponenty.dodajobraz import shopify_client as sc

_COMPONENT_DIR = Path(__file__).resolve().parent
_DATA_DIR = _COMPONENT_DIR / "dane"
_ORDERS_FILE = _DATA_DIR / "zamowienia.json"
_SYNC_STATE_FILE = _DATA_DIR / "sync_state.json"

# Heurystyka: rozpoznajemy ze product_type z Shopify to obraz wg
# nazwy/tagow. Mozna rozszerzyc w przyszlosci.
_IS_PAINTING_RE = re.compile(r"(obraz|painting|canvas|reprodukcja)", re.IGNORECASE)

# Rozpoznawanie rozmiaru ramki w variant_title Shopify (np. "Dab / L", "Sosna XL")
_FRAME_PATTERNS = [
    (re.compile(r"\bd[aą]b\b.*\bxl\b", re.IGNORECASE), "Dab XL"),
    (re.compile(r"\bd[aą]b\b.*\bl\b", re.IGNORECASE), "Dab L"),
    (re.compile(r"\bd[aą]b\b.*\bs\b", re.IGNORECASE), "Dab S"),
    (re.compile(r"\bsosn[aę]\b.*\bxl\b", re.IGNORECASE), "Sosna XL"),
    (re.compile(r"\bsosn[aę]\b.*\bl\b", re.IGNORECASE), "Sosna L"),
    (re.compile(r"\bsosn[aę]\b.*\bs\b", re.IGNORECASE), "Sosna S"),
]


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_db() -> dict[str, Any]:
    _ensure_dir()
    if not _ORDERS_FILE.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(_ORDERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_db(db: dict[str, Any]) -> None:
    _ensure_dir()
    _ORDERS_FILE.write_text(
        json.dumps(db, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _load_sync_state() -> dict[str, Any]:
    _ensure_dir()
    if not _SYNC_STATE_FILE.is_file():
        return {}
    try:
        return json.loads(_SYNC_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sync_state(state: dict[str, Any]) -> None:
    _ensure_dir()
    _SYNC_STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _detect_frame_variant(variant_title: str, *, fallback: str = "Dab S") -> str:
    v = (variant_title or "").strip()
    if not v:
        return fallback
    for pattern, label in _FRAME_PATTERNS:
        if pattern.search(v):
            return label
    return fallback


def _format_address(addr: dict | None) -> str:
    if not addr:
        return ""
    parts = [
        " ".join(filter(None, [addr.get("first_name"), addr.get("last_name")])),
        addr.get("address1") or "",
        addr.get("address2") or "",
        " ".join(filter(None, [addr.get("zip"), addr.get("city")])),
        addr.get("province") or "",
        addr.get("country") or "",
        addr.get("phone") or "",
    ]
    return "\n".join(p for p in parts if p).strip()


def _customer_name(order: dict) -> str:
    cust = order.get("customer") or {}
    name = " ".join(filter(None, [cust.get("first_name"), cust.get("last_name")])).strip()
    if name:
        return name
    addr = order.get("shipping_address") or {}
    alt = " ".join(filter(None, [addr.get("first_name"), addr.get("last_name")])).strip()
    return alt or (order.get("email") or "")


def _is_painting_line(item: dict) -> bool:
    """Heurystyka: line_item traktujemy jako obraz jesli title/type sugeruje."""
    title = (item.get("title") or "") + " " + (item.get("name") or "")
    if _IS_PAINTING_RE.search(title):
        return True
    # Fallback: wszystkie line_items sa traktowane jako potencjalne zamowienia produkcji.
    # Lepiej zduplikowac manualnie niz przegapic - user moze sobie usunac te zle.
    return True


def _build_order_from_line(
    order: dict, line: dict, *, next_id: int,
) -> dict[str, Any]:
    order_no = str(order.get("name") or "")  # np. '#1042'
    order_id = f"ORD-{next_id:04d}"
    variant_title = str(line.get("variant_title") or "")
    frame = _detect_frame_variant(variant_title)
    created_iso = str(order.get("created_at") or "")[:10] or date.today().isoformat()

    title = str(line.get("title") or "")
    # Shopify zapisuje 'Artysta - Tytul'; wyciagamy tytul po myslniku jesli wystepuje
    if " - " in title:
        painting_title = title.split(" - ", 1)[1].strip()
    elif " – " in title:
        painting_title = title.split(" – ", 1)[1].strip()
    else:
        painting_title = title

    return {
        "id": order_id,
        "shopify_order_no": order_no,
        "shopify_order_id": int(order.get("id") or 0),
        "shopify_line_item_id": int(line.get("id") or 0),
        "client": _customer_name(order),
        "ramka_wariant": frame,
        "ilosc": int(line.get("quantity") or 1),
        "tytul_obrazu": painting_title,
        "data_zamowienia": created_iso,
        "wydruk_step": 0,
        "ramka_step": 0,
        "data_pomalowania": None,
        "zlozone": False,
        "spakowane": False,
        "wyslane": False,
        "data_wyslania": None,
        "adres_wysylki": _format_address(order.get("shipping_address")),
        "notatka": (order.get("note") or "").strip(),
    }


def _is_duplicate(db_orders: list[dict], order_id: int, line_item_id: int) -> bool:
    for o in db_orders:
        if (
            int(o.get("shopify_order_id") or 0) == int(order_id)
            and int(o.get("shopify_line_item_id") or 0) == int(line_item_id)
        ):
            return True
    return False


def sync_orders(
    *,
    since_days: int = 30,
    financial_status: str = "paid",
    logger: Any = None,
) -> list[dict[str, Any]]:
    """Wykonuje synchronizacje i zwraca liste NOWO dodanych zamowien.

    `since_days` jest uzywane tylko przy pierwszym uruchomieniu (brak sync_state).
    Potem aplikacja pamieta `updated_at_min = last_sync_iso`.
    """
    try:
        shop, token = sc.load_session()
    except FileNotFoundError as e:
        if logger:
            logger(f"[orders_sync] Brak sesji Shopify: {e}")
        return []

    state = _load_sync_state()
    last_sync_iso = state.get("last_sync_iso")
    if not last_sync_iso:
        # Pierwsze uruchomienie - cofamy sie o `since_days`
        from datetime import timedelta
        last_sync_iso = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat()

    if logger:
        logger(f"[orders_sync] Pobieram zamowienia od {last_sync_iso} ({financial_status})...")

    try:
        orders = sc.iter_orders_since(
            shop, token,
            updated_at_min=last_sync_iso,
            financial_status=financial_status,
            status="any",
        )
    except sc.ShopifyError as e:
        if logger:
            logger(f"[orders_sync] BLAD Shopify: {e}")
        return []

    if logger:
        logger(f"[orders_sync] Pobrano {len(orders)} zamowien od ostatniej synchronizacji.")

    db = _load_db()
    db.setdefault("orders", [])
    db.setdefault("next_id", 1)

    added: list[dict[str, Any]] = []
    for order in orders:
        for line in order.get("line_items") or []:
            if not _is_painting_line(line):
                continue
            oid = int(order.get("id") or 0)
            lid = int(line.get("id") or 0)
            if _is_duplicate(db["orders"], oid, lid):
                continue
            next_id = int(db.get("next_id") or 1)
            new_order = _build_order_from_line(order, line, next_id=next_id)
            db["next_id"] = next_id + 1
            db["orders"].append(new_order)
            added.append(new_order)
            if logger:
                logger(
                    f"[orders_sync] + {new_order['id']} "
                    f"(Shopify {new_order['shopify_order_no']}): "
                    f"{new_order['client']} - {new_order['tytul_obrazu']}"
                )

    if added:
        _save_db(db)

    # Zapisz nowy checkpoint (NOW, zeby nastepnym razem pobrac tylko nowsze)
    state["last_sync_iso"] = datetime.now(timezone.utc).isoformat()
    state["last_added_count"] = len(added)
    state["last_run_count"] = len(orders)
    _save_sync_state(state)

    return added


def reset_sync_state() -> None:
    """Kasuje state - przy nastepnej sync pobierzemy cala historie (since_days)."""
    if _SYNC_STATE_FILE.is_file():
        _SYNC_STATE_FILE.unlink()


def get_sync_state() -> dict[str, Any]:
    """Zwraca aktualny stan sync (dla UI)."""
    return _load_sync_state()
