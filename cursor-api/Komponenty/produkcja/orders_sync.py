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

from giclee_app.app_paths import atomic_write_text

from Komponenty.dodajobraz import shopify_client as sc
from Komponenty.produkcja import production_store
from Komponenty.produkcja.frame_variant import (
    combined_label,
    legacy_compact_label,
    parse_shopify_variant_title,
)
from Komponenty.produkcja.passepartout import parse_passepartout_from_line

# Alias dla testow / kompatybilnosci wstecznej
_detect_frame_variant = legacy_compact_label

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_LEGACY_ORDERS_FILE = _LEGACY_DATA_DIR / "zamowienia.json"
_ORDERS_FILE = _LEGACY_ORDERS_FILE
_LEGACY_SYNC_STATE_FILE = _LEGACY_DATA_DIR / "sync_state.json"
_SYNC_STATE_FILE = _LEGACY_SYNC_STATE_FILE


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


def _sync_state_path(*, for_write: bool) -> Path:
    explicit = Path(_SYNC_STATE_FILE)
    if explicit != _LEGACY_SYNC_STATE_FILE:
        return explicit
    override = _data_dir_override()
    if override is not None:
        return override / "sync_state.json"
    return (
        production_store.sync_state_write_path()
        if for_write
        else production_store.sync_state_read_path()
    )

# Heurystyka: rozpoznajemy ze product_type z Shopify to obraz wg
# nazwy/tagow. Mozna rozszerzyc w przyszlosci.
_IS_PAINTING_RE = re.compile(r"(obraz|painting|canvas|reprodukcja)", re.IGNORECASE)


def _load_db() -> dict[str, Any]:
    path = _orders_path(for_write=False)
    if not path.is_file():
        return {"next_id": 1, "orders": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"next_id": 1, "orders": []}


def _save_db(db: dict[str, Any]) -> None:
    atomic_write_text(
        _orders_path(for_write=True),
        json.dumps(db, indent=2, ensure_ascii=False) + "\n",
    )


def _load_sync_state() -> dict[str, Any]:
    path = _sync_state_path(for_write=False)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_sync_state(state: dict[str, Any]) -> None:
    atomic_write_text(
        _sync_state_path(for_write=True),
        json.dumps(state, indent=2, ensure_ascii=False) + "\n",
    )


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
    order: dict,
    line: dict,
    *,
    next_id: int,
    shop: str = "",
    token: str = "",
) -> dict[str, Any]:
    order_no = str(order.get("name") or "")  # np. '#1042'
    order_id = f"ORD-{next_id:04d}"
    variant_title = str(line.get("variant_title") or "")
    d_opt, r_opt, k_opt = parse_shopify_variant_title(variant_title)
    pp_opt = parse_passepartout_from_line(line)
    rw = combined_label(d_opt, r_opt, k_opt)
    if not rw.strip():
        rw = legacy_compact_label(variant_title)
    created_iso = str(order.get("created_at") or "")[:10] or date.today().isoformat()

    title = str(line.get("title") or "")
    # Shopify zapisuje 'Artysta - Tytul'; wyciagamy tytul po myslniku jesli wystepuje
    if " - " in title:
        painting_title = title.split(" - ", 1)[1].strip()
    elif " – " in title:
        painting_title = title.split(" – ", 1)[1].strip()
    else:
        painting_title = title

    variant_id = int(line.get("variant_id") or 0)
    product_id = int(line.get("product_id") or 0)
    image_url = ""
    if shop and token and variant_id:
        try:
            u = sc.get_variant_featured_image_url(
                shop,
                token,
                variant_id=variant_id,
                product_id=product_id or None,
            )
            image_url = (u or "").strip()
        except sc.ShopifyError:
            image_url = ""

    return {
        "id": order_id,
        "shopify_order_no": order_no,
        "shopify_order_id": int(order.get("id") or 0),
        "shopify_line_item_id": int(line.get("id") or 0),
        "shopify_variant_id": variant_id,
        "shopify_product_id": product_id,
        "shopify_image_url": image_url,
        "client": _customer_name(order),
        "ramka_drewno": d_opt,
        "ramka_rozmiar": r_opt,
        "ramka_kolor": k_opt,
        "passepartout_kolor": pp_opt,
        "ramka_wariant": rw,
        "ilosc": int(line.get("quantity") or 1),
        "tytul_obrazu": painting_title,
        "data_zamowienia": created_iso,
        "wydruk_step": 0,
        "ramka_step": 0,
        "data_pomalowania": None,
        "pomin_schniecie": False,
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
            new_order = _build_order_from_line(
                order, line, next_id=next_id, shop=shop, token=token,
            )
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
    """Resetuje state bez ponownego odslaniania legacy fallbacku."""
    atomic_write_text(_sync_state_path(for_write=True), "{}\n")


def get_sync_state() -> dict[str, Any]:
    """Zwraca aktualny stan sync (dla UI)."""
    return _load_sync_state()
