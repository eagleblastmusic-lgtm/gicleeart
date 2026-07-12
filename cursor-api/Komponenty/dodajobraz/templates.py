"""Szablony wariantow/cen produktu.

Cel: zamiast za kazdym razem pytac Shopify o `REFERENCE_PRODUCT_ID`, trzymamy
lokalny snapshot wariantow, ktory mozna swobodnie edytowac i duplikowac.

Persystencja: `Komponenty/dodajobraz/data/variant_templates.json`:
{
  "templates": [
    {
      "id": "uuid12",
      "name": "Podstawowy",
      "is_default": true,
      "source": "shopify:15524677845340",
      "options": [{"name": "Rozmiar", "values": ["50x70", "70x100"], "position": 1}, ...],
      "variants": [{"option1": "50x70", "price": "129.00", "compare_at_price": null,
                    "weight": 1.2, "weight_unit": "kg", "inventory_policy": "deny",
                    ...}, ...],
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}

Przy starcie `bootstrap_default_if_missing()` zaciaga raz dane z Shopify z
REFERENCE_PRODUCT_ID (jesli plik nie istnieje albo nie ma default-a). Potem
apka nigdy nie pyta Shopify - chyba ze user recznie kliknie "Odswiez
z Shopify" w dialogu szablonow.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, config_path

from . import shopify_client as sc

# Importujemy tylko wartosc, nie zeby inportowac cale create.py
REFERENCE_PRODUCT_ID = 15524677845340

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY_TEMPLATES_FILE = _LEGACY_DATA_DIR / "variant_templates.json"
_DATA_DIR = _LEGACY_DATA_DIR
_TEMPLATES_FILE = _LEGACY_TEMPLATES_FILE


def _templates_path(*, for_write: bool = False) -> Path:
    data_dir = Path(_DATA_DIR)
    current = Path(_TEMPLATES_FILE)
    if data_dir != _LEGACY_DATA_DIR and current == _LEGACY_TEMPLATES_FILE:
        current = data_dir / "variant_templates.json"
    if current != _LEGACY_TEMPLATES_FILE:
        return current
    app_path = config_path(
        "Komponenty/dodajobraz/data/variant_templates.json",
        legacy=_LEGACY_TEMPLATES_FILE,
    )
    return app_path.write_path if for_write else app_path.read_path()

# Pola wariantu, ktore kopiujemy z Shopify / trzymamy lokalnie.
_COPY_KEYS: tuple[str, ...] = (
    "option1", "option2", "option3",
    "price", "compare_at_price",
    "weight", "weight_unit",
    "inventory_policy", "fulfillment_service", "inventory_management",
    "requires_shipping", "taxable", "position",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class VariantTemplate:
    id: str
    name: str
    is_default: bool = False
    source: str = "manual"
    options: list[dict[str, Any]] = field(default_factory=list)
    variants: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def new(
        *,
        name: str,
        options: list[dict[str, Any]] | None = None,
        variants: list[dict[str, Any]] | None = None,
        source: str = "manual",
        is_default: bool = False,
    ) -> "VariantTemplate":
        now = _now()
        return VariantTemplate(
            id=uuid.uuid4().hex[:12],
            name=(name or "").strip() or "Nowy szablon",
            is_default=is_default,
            source=source,
            options=list(options or []),
            variants=list(variants or []),
            created_at=now,
            updated_at=now,
        )


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _ensure_dir() -> None:
    _templates_path(for_write=True).parent.mkdir(parents=True, exist_ok=True)


def _from_dict(d: dict[str, Any]) -> VariantTemplate:
    return VariantTemplate(
        id=str(d.get("id") or uuid.uuid4().hex[:12]),
        name=str(d.get("name") or "(bez nazwy)").strip(),
        is_default=bool(d.get("is_default")),
        source=str(d.get("source") or "manual"),
        options=list(d.get("options") or []),
        variants=list(d.get("variants") or []),
        created_at=str(d.get("created_at") or _now()),
        updated_at=str(d.get("updated_at") or _now()),
    )


def load_templates() -> list[VariantTemplate]:
    _ensure_dir()
    path = _templates_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("templates", []) if isinstance(data, dict) else []
    return [_from_dict(x) for x in raw if isinstance(x, dict)]


def apply_default_flag(
    templates: list[VariantTemplate],
    template_id: str,
    *,
    is_default: bool,
) -> None:
    """Ustawia `is_default` dla wskazanego szablonu.

    Gdy `is_default=True`, wszystkie pozostale szablony dostaja `False` (tylko jeden domyslny).
    Gdy `is_default=False`, zmieniany jest tylko wskazany rekord (inne bez zmian).
    """
    for t in templates:
        if t.id == template_id:
            t.is_default = is_default
        elif is_default:
            t.is_default = False


def save_templates(templates: list[VariantTemplate]) -> None:
    _ensure_dir()
    # Dbamy zeby tylko jeden byl is_default
    default_seen = False
    for t in templates:
        if t.is_default and not default_seen:
            default_seen = True
        elif t.is_default:
            t.is_default = False
    if templates and not default_seen:
        templates[0].is_default = True
    payload = {"templates": [asdict(t) for t in templates]}
    atomic_write_text(
        _templates_path(for_write=True),
        json.dumps(payload, indent=2, ensure_ascii=False),
    )


def get_default() -> VariantTemplate | None:
    templates = load_templates()
    for t in templates:
        if t.is_default:
            return t
    return templates[0] if templates else None


def get_by_id(template_id: str) -> VariantTemplate | None:
    for t in load_templates():
        if t.id == template_id:
            return t
    return None


def get_by_name(name: str) -> VariantTemplate | None:
    lower = (name or "").strip().lower()
    for t in load_templates():
        if t.name.lower() == lower:
            return t
    return None


def add_template(template: VariantTemplate) -> None:
    templates = load_templates()
    templates.append(template)
    save_templates(templates)


def update_template(template_id: str, **changes: Any) -> VariantTemplate | None:
    templates = load_templates()
    for i, t in enumerate(templates):
        if t.id == template_id:
            for k, v in changes.items():
                if hasattr(t, k):
                    setattr(t, k, v)
            t.updated_at = _now()
            templates[i] = t
            save_templates(templates)
            return t
    return None


def delete_template(template_id: str) -> bool:
    templates = load_templates()
    filtered = [t for t in templates if t.id != template_id]
    if len(filtered) == len(templates):
        return False
    # Nie pozwalamy usunac wszystkich
    if not filtered:
        return False
    # Jesli usunelismy default, ustaw pierwszy jako default
    if not any(t.is_default for t in filtered):
        filtered[0].is_default = True
    save_templates(filtered)
    return True


def set_default(template_id: str) -> bool:
    templates = load_templates()
    if not any(t.id == template_id for t in templates):
        return False
    apply_default_flag(templates, template_id, is_default=True)
    for t in templates:
        if t.id == template_id:
            t.updated_at = _now()
            break
    save_templates(templates)
    return True


def duplicate_template(template_id: str, *, new_name: str | None = None) -> VariantTemplate | None:
    src = get_by_id(template_id)
    if src is None:
        return None
    copy = VariantTemplate.new(
        name=new_name or f"{src.name} (kopia)",
        options=json.loads(json.dumps(src.options)),
        variants=json.loads(json.dumps(src.variants)),
        source="manual",
        is_default=False,
    )
    add_template(copy)
    return copy


# ---------------------------------------------------------------------------
# Import z Shopify
# ---------------------------------------------------------------------------

def fetch_template_from_shopify(
    product_id: int,
    *,
    name: str | None = None,
) -> VariantTemplate:
    """Laduje warianty z produktu Shopify i zapisuje jako szablon.

    Wymaga scope `read_products`.
    """
    shop, token = sc.load_session()
    prod = sc.get_product(shop, token, product_id)
    if not prod:
        raise sc.ShopifyError(f"Nie znaleziono produktu {product_id}")

    options = []
    for opt in prod.get("options") or []:
        options.append({
            "name": str(opt.get("name") or "").strip(),
            "values": list(opt.get("values") or []),
            "position": int(opt.get("position") or 0),
        })

    variants: list[dict[str, Any]] = []
    for v in prod.get("variants") or []:
        entry: dict[str, Any] = {}
        for k in _COPY_KEYS:
            val = v.get(k)
            if val is not None:
                entry[k] = val
        variants.append(entry)

    template_name = name or f"Szablon z {prod.get('title', product_id)}"
    return VariantTemplate.new(
        name=template_name,
        options=options,
        variants=variants,
        source=f"shopify:{product_id}",
        is_default=False,
    )


def import_from_shopify(product_id: int, *, name: str | None = None) -> VariantTemplate:
    """Pobiera szablon z Shopify i zapisuje go lokalnie."""
    template = fetch_template_from_shopify(product_id, name=name)
    add_template(template)
    return template


# ---------------------------------------------------------------------------
# Bootstrap - jednorazowa migracja
# ---------------------------------------------------------------------------

def bootstrap_default_if_missing(*, logger: Any = None) -> VariantTemplate | None:
    """Pierwsze uruchomienie: jesli nie ma zadnego szablonu LUB zadnego z
    `source = "shopify:{REFERENCE_PRODUCT_ID}"` - probujemy zaciagnac szablon
    z Shopify i zapisac jako "Podstawowy" (is_default=True).

    Jesli Shopify nie odpowiada lub sesji brak, nie crashuje - zwraca None.
    To pozwala uzytkownikowi dalej pracowac (dodaje sobie szablon recznie).
    """
    templates = load_templates()
    if templates and any(t.is_default for t in templates):
        return None  # juz jest jakis default - nie ruszamy

    # Jesli istnieje, ale nie ma default - nadaj pierwszemu.
    if templates:
        templates[0].is_default = True
        save_templates(templates)
        return templates[0]

    # Plik pusty - probujemy zaciagnac z Shopify raz.
    try:
        template = fetch_template_from_shopify(
            REFERENCE_PRODUCT_ID, name="Podstawowy",
        )
        template.is_default = True
        add_template(template)
        if logger:
            try:
                logger(
                    f"[szablony] Zaimportowano 'Podstawowy' z produktu "
                    f"{REFERENCE_PRODUCT_ID}: {len(template.variants)} wariantow."
                )
            except Exception:  # noqa: BLE001
                pass
        return template
    except (sc.ShopifyError, FileNotFoundError, OSError) as e:
        if logger:
            try:
                logger(
                    f"[szablony] Nie udalo sie zaciagnac szablonu Podstawowego z Shopify: {e}. "
                    f"Dodaj szablon recznie w dialogu 'Szablony...'."
                )
            except Exception:  # noqa: BLE001
                pass
        return None


# ---------------------------------------------------------------------------
# Helpers dla create.py / update_all_product_prices
# ---------------------------------------------------------------------------

def template_to_shopify_payload(template: VariantTemplate) -> tuple[list[dict], list[dict]]:
    """Konwersja lokalnego szablonu na payload Shopify (options, variants).

    Struktura jak w [create.py] - idzie bezposrednio do `product_payload`.
    """
    options = []
    for opt in template.options:
        options.append({
            "name": opt.get("name") or "",
            "values": list(opt.get("values") or []),
            "position": opt.get("position", 0),
        })

    variants = []
    for v in template.variants:
        entry: dict[str, Any] = {}
        for k in _COPY_KEYS:
            if k in v and v[k] is not None:
                entry[k] = v[k]
        variants.append(entry)
    return options, variants


# ---------------------------------------------------------------------------
# Masowe zastosowanie szablonu do istniejacych produktow
# ---------------------------------------------------------------------------

_VARIANT_UPDATE_KEYS: tuple[str, ...] = (
    "option1", "option2", "option3",
    "price", "compare_at_price",
    "weight", "weight_unit",
    "inventory_policy", "fulfillment_service", "inventory_management",
    "requires_shipping", "taxable", "position",
)


def _log(logger: Callable[[str], None] | None, msg: str) -> None:
    if logger:
        try:
            logger(msg)
        except Exception:  # noqa: BLE001
            pass


def _variant_key(v: dict[str, Any]) -> tuple[str, ...]:
    parts: list[str] = []
    for i in (1, 2, 3):
        val = v.get(f"option{i}")
        if val is not None and str(val).strip():
            parts.append(str(val).strip())
    return tuple(parts)


def _variant_fields_for_shopify(
    v: dict[str, Any],
    *,
    clear_inventory_tracking: bool = False,
) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in _VARIANT_UPDATE_KEYS:
        if key in v and v[key] is not None:
            fields[key] = v[key]
        elif clear_inventory_tracking and key == "inventory_management":
            fields[key] = None
    if clear_inventory_tracking and "inventory_management" not in fields:
        fields["inventory_management"] = None
    return fields


def _variant_field_changed(current_fields: dict[str, Any], key: str, desired: Any) -> bool:
    current = current_fields.get(key)
    if desired is None:
        return current not in (None, "")
    return str(current if current is not None else "") != str(desired)


def validate_template_for_existing_products(template: VariantTemplate) -> None:
    """Sprawdza limity Shopify przed masowa aktualizacja istniejacych produktow."""
    options, variants = template_to_shopify_payload(template)
    if len(options) > 3:
        raise sc.ShopifyError(
            f"Shopify obsluguje maksymalnie 3 opcje produktu, a szablon ma {len(options)}."
        )
    if len(variants) > 100:
        raise sc.ShopifyError(
            f"Shopify obsluguje maksymalnie 100 wariantow na produkt, a szablon ma {len(variants)}."
        )
    if not variants:
        raise sc.ShopifyError("Szablon nie ma zadnych wariantow.")

    seen: set[tuple[str, ...]] = set()
    for v in variants:
        key = _variant_key(v)
        if not key:
            raise sc.ShopifyError("Szablon zawiera wariant bez wartosci opcji.")
        if key in seen:
            raise sc.ShopifyError(
                f"Szablon zawiera zduplikowany wariant: {' / '.join(key)}"
            )
        seen.add(key)


def apply_template_to_product(
    shop: str,
    token: str,
    product: dict[str, Any],
    template: VariantTemplate,
    *,
    logger: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Dopasowuje warianty jednego produktu do szablonu.

    Strategia jest zachowawcza: najpierw tworzy brakujace warianty, potem aktualizuje
    pasujace i dopiero na koncu usuwa warianty, ktorych nie ma w szablonie.
    """
    options_payload, variants_payload = template_to_shopify_payload(template)
    pid = int(product.get("id") or 0)
    if not pid:
        raise sc.ShopifyError("Produkt bez ID.")

    existing_variants = list(product.get("variants") or [])
    existing_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for v in existing_variants:
        key = _variant_key(v)
        if key and key not in existing_by_key:
            existing_by_key[key] = v

    desired_by_key = {_variant_key(v): v for v in variants_payload}
    desired_keys = set(desired_by_key)
    keep_seen: set[tuple[str, ...]] = set()
    variants_to_delete: list[dict[str, Any]] = []
    for v in existing_variants:
        key = _variant_key(v)
        if key in desired_keys and key not in keep_seen:
            keep_seen.add(key)
            continue
        variants_to_delete.append(v)

    created = 0
    updated = 0
    deleted = 0
    unchanged = 0
    current_count = len(existing_variants)

    def delete_existing_variant(v: dict[str, Any]) -> None:
        nonlocal deleted, current_count
        vid = v.get("id")
        if not vid:
            return
        sc.delete_product_variant(shop, token, pid, int(vid))
        deleted += 1
        current_count = max(0, current_count - 1)

    for key, desired in desired_by_key.items():
        current = existing_by_key.get(key)
        fields = _variant_fields_for_shopify(desired, clear_inventory_tracking=True)
        if current is None:
            while current_count >= 100 and variants_to_delete and current_count > 1:
                delete_existing_variant(variants_to_delete.pop(0))
            sc.create_product_variant(shop, token, pid, fields)
            current_count += 1
            created += 1
            continue

        current_fields = _variant_fields_for_shopify(current)
        needs_update = any(_variant_field_changed(current_fields, k, v) for k, v in fields.items())
        if not needs_update:
            unchanged += 1
            continue
        sc.update_variant(shop, token, int(current["id"]), fields)
        updated += 1

    for v in variants_to_delete:
        try:
            delete_existing_variant(v)
        except sc.ShopifyError as e:
            vid = v.get("id")
            _log(logger, f"[szablony] Nie usunieto wariantu {vid} produktu {pid}: {e}")

    # Nazwy opcji aktualizujemy po operacjach na wariantach, zeby wartosci byly juz obecne.
    sc.update_product(shop, token, pid, {"options": options_payload})

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "unchanged": unchanged,
    }


def apply_template_to_all_products(
    template_id: str,
    *,
    product_type: str | None = None,
    logger: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Stosuje wybrany szablon wariantow do wszystkich produktow z katalogu Shopify."""
    template = get_by_id(template_id)
    if template is None:
        raise sc.ShopifyError(f"Szablon wariantow {template_id} nie istnieje.")
    validate_template_for_existing_products(template)

    shop, token = sc.load_session()
    scope_label = product_type or "wszystkie"
    _log(logger, f"[szablony] Sesja: {shop}")
    _log(
        logger,
        f"[szablony] Stosuje szablon '{template.name}' do produktow (typ={scope_label}).",
    )
    if on_progress:
        on_progress("Ladowanie katalogu produktow...")

    def _page_progress(n: int) -> None:
        msg = f"Ladowanie katalogu: {n} produktow..."
        _log(logger, f"[szablony] {msg}")
        if on_progress:
            on_progress(msg)

    products = sc.fetch_all_products(
        shop,
        token,
        product_type=product_type,
        fields="id,title,handle,product_type,variants",
        should_cancel=should_cancel,
        on_page_progress=_page_progress,
    )

    total = len(products)
    _log(logger, f"[szablony] Znaleziono {total} produktow.")
    counters = {
        "products_total": total,
        "products_updated": 0,
        "variants_created": 0,
        "variants_updated": 0,
        "variants_deleted": 0,
        "variants_unchanged": 0,
        "errors": [],
    }

    for idx, product in enumerate(products, start=1):
        if should_cancel and should_cancel():
            raise sc.OperationCancelled("Przerwano stosowanie szablonu wariantow.")
        title = str(product.get("title") or f"id={product.get('id')}")
        msg = f"Produkt {idx}/{total}: {title}"
        if on_progress:
            on_progress(msg)
        try:
            res = apply_template_to_product(shop, token, product, template, logger=logger)
            counters["products_updated"] += 1
            counters["variants_created"] += res["created"]
            counters["variants_updated"] += res["updated"]
            counters["variants_deleted"] += res["deleted"]
            counters["variants_unchanged"] += res["unchanged"]
            _log(
                logger,
                "[szablony] OK "
                f"{title}: +{res['created']} / upd {res['updated']} / "
                f"del {res['deleted']} / bez zmian {res['unchanged']}",
            )
        except sc.ShopifyError as e:
            err = f"{title}: {e}"
            counters["errors"].append(err)
            _log(logger, f"[szablony] BLAD {err}")

    _log(
        logger,
        "[szablony] Gotowe. "
        f"Produkty: {counters['products_updated']}/{total}, "
        f"dodano wariantow: {counters['variants_created']}, "
        f"zmieniono: {counters['variants_updated']}, "
        f"usunieto: {counters['variants_deleted']}, "
        f"bledow: {len(counters['errors'])}.",
    )
    return counters


def apply_template_to_product_id(
    template_id: str,
    product_id: int,
    *,
    logger: Callable[[str], None] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Stosuje wybrany szablon wariantow do jednego produktu Shopify."""
    template = get_by_id(template_id)
    if template is None:
        raise sc.ShopifyError(f"Szablon wariantow {template_id} nie istnieje.")
    validate_template_for_existing_products(template)

    shop, token = sc.load_session()
    pid = int(product_id)
    _log(logger, f"[szablony] Sesja: {shop}")
    _log(logger, f"[szablony] Pobieram produkt {pid}...")
    if on_progress:
        on_progress("Pobieranie produktu z Shopify...")
    product = sc.get_product(shop, token, pid)
    if not product:
        raise sc.ShopifyError(f"Nie znaleziono produktu {pid}.")

    title = str(product.get("title") or f"id={pid}")
    if on_progress:
        on_progress(f"Stosowanie szablonu do: {title}")
    res = apply_template_to_product(shop, token, product, template, logger=logger)
    _log(
        logger,
        "[szablony] OK "
        f"{title}: +{res['created']} / upd {res['updated']} / "
        f"del {res['deleted']} / bez zmian {res['unchanged']}",
    )
    return {
        "product_id": pid,
        "product_title": title,
        "variants_created": res["created"],
        "variants_updated": res["updated"],
        "variants_deleted": res["deleted"],
        "variants_unchanged": res["unchanged"],
    }


def apply_template_to_product_ids(
    template_id: str,
    product_ids: list[int],
    *,
    logger: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Stosuje wybrany szablon wariantow do wskazanych produktow Shopify."""
    ids = [int(x) for x in product_ids if int(x) > 0]
    if not ids:
        raise sc.ShopifyError("Nie wybrano zadnego produktu.")

    template = get_by_id(template_id)
    if template is None:
        raise sc.ShopifyError(f"Szablon wariantow {template_id} nie istnieje.")
    validate_template_for_existing_products(template)

    shop, token = sc.load_session()
    total = len(ids)
    _log(logger, f"[szablony] Sesja: {shop}")
    _log(logger, f"[szablony] Stosuje szablon '{template.name}' do {total} produktow.")

    counters: dict[str, Any] = {
        "products_total": total,
        "products_updated": 0,
        "variants_created": 0,
        "variants_updated": 0,
        "variants_deleted": 0,
        "variants_unchanged": 0,
        "errors": [],
    }
    successful_pids: list[int] = []

    for idx, pid in enumerate(ids, start=1):
        if should_cancel and should_cancel():
            raise sc.OperationCancelled("Przerwano stosowanie szablonu wariantow.")
        if on_progress:
            on_progress(f"Produkt {idx}/{total} (id={pid})...")
        try:
            product = sc.get_product(shop, token, pid)
            if not product:
                raise sc.ShopifyError(f"Nie znaleziono produktu {pid}.")
            title = str(product.get("title") or f"id={pid}")
            res = apply_template_to_product(shop, token, product, template, logger=logger)
            counters["products_updated"] += 1
            successful_pids.append(pid)
            counters["variants_created"] += res["created"]
            counters["variants_updated"] += res["updated"]
            counters["variants_deleted"] += res["deleted"]
            counters["variants_unchanged"] += res["unchanged"]
            _log(
                logger,
                "[szablony] OK "
                f"{title}: +{res['created']} / upd {res['updated']} / "
                f"del {res['deleted']} / bez zmian {res['unchanged']}",
            )
        except sc.ShopifyError as e:
            err = f"id={pid}: {e}"
            counters["errors"].append(err)
            _log(logger, f"[szablony] BLAD {err}")

    _log(
        logger,
        "[szablony] Gotowe. "
        f"Produkty: {counters['products_updated']}/{total}, "
        f"bledow: {len(counters['errors'])}.",
    )
    try:
        from .product_template_assignments import set_product_template_assignments_batch

        if successful_pids:
            set_product_template_assignments_batch(successful_pids, template_id)
    except Exception:  # noqa: BLE001
        pass
    return counters


def variants_as_rows(
    template: VariantTemplate,
    *,
    sort_priority: tuple[str, ...] = ("rodzaj drewna", "rozmiar", "kolor"),
) -> list[dict[str, Any]]:
    """Zwraca warianty jako wiersze [{'key', 'label', 'price'}] - zgodnie z
    formatem [get_reference_variant_rows] w create.py (dla dialogu 'Zmien ceny').

    `key` = krotka wartosci (option1, option2, option3) pomijajac None.
    `label` = sklejone wartosci w kolejnosci wyswietlania.
    """
    option_names = [(o.get("name") or "").strip() for o in template.options]
    while len(option_names) < 3:
        option_names.append("")

    # Kolejnosc wyswietlania
    display_order_idx: list[int] = []
    used: set[int] = set()
    for target in sort_priority:
        tgt = target.lower()
        for i, name in enumerate(option_names):
            n = (name or "").lower()
            if i in used or not n:
                continue
            if n == tgt or tgt in n or n in tgt:
                display_order_idx.append(i)
                used.add(i)
                break
    for i in range(len(option_names)):
        if i not in used and option_names[i]:
            display_order_idx.append(i)
            used.add(i)

    rows: list[dict[str, Any]] = []
    for v in template.variants:
        key_parts: list[str] = []
        for i in (1, 2, 3):
            val = v.get(f"option{i}")
            if val is not None and str(val).strip():
                key_parts.append(str(val).strip())
        values = [v.get(f"option{i + 1}") for i in range(len(option_names))]
        display_parts = [
            str(values[i] or "").strip()
            for i in display_order_idx
            if i < len(values) and values[i] is not None
        ]
        rows.append({
            "key": tuple(key_parts),
            "label": " / ".join(display_parts) if display_parts else "Wariant",
            "price": str(v.get("price") or ""),
        })
    return rows
