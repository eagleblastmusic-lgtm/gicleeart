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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import shopify_client as sc

# Importujemy tylko wartosc, nie zeby inportowac cale create.py
REFERENCE_PRODUCT_ID = 15524677845340

_DATA_DIR = Path(__file__).resolve().parent / "data"
_TEMPLATES_FILE = _DATA_DIR / "variant_templates.json"

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
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


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
    if not _TEMPLATES_FILE.is_file():
        return []
    try:
        data = json.loads(_TEMPLATES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("templates", []) if isinstance(data, dict) else []
    return [_from_dict(x) for x in raw if isinstance(x, dict)]


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
    _TEMPLATES_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
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
    found = False
    for t in templates:
        if t.id == template_id:
            t.is_default = True
            t.updated_at = _now()
            found = True
        else:
            t.is_default = False
    if found:
        save_templates(templates)
    return found


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
