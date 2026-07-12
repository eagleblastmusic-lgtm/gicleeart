"""Szablony wymiarow paczki — edytowalna mapa `klucz -> (dl, szer, wys, waga)`.

Klucz: wynik `shipping_lookup_key()` w formacie `"{WOOD} {SIZE}"`, np. `"DAB M"`.
Wartosc (wszystkie wymiary w cm, waga w kg):
    {
      "length_cm": 60, "width_cm": 45, "height_cm": 10, "weight_kg": 3.0,
      "updated_at": "2026-04-22T12:34:56"
    }

Dane zyja w `Komponenty/produkcja/dane/package_templates.json`. Gdy plik nie
istnieje, uzywane sa DEFAULTS (te same wartosci, co wczesniej w `shipping.py`).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from giclee_app.app_paths import atomic_write_text, config_path

_COMPONENT_DIR = Path(__file__).resolve().parent
_LEGACY_DATA_DIR = _COMPONENT_DIR / "dane"
_DATA_DIR = _LEGACY_DATA_DIR
_FILE = _LEGACY_DATA_DIR / "package_templates.json"
_TEMPLATES = config_path("Komponenty/produkcja/dane/package_templates.json", legacy=_FILE)


def _templates_path(*, for_write: bool) -> Path:
    if Path(_FILE) != _LEGACY_DATA_DIR / "package_templates.json":
        return Path(_FILE)
    return _TEMPLATES.write_path if for_write else _TEMPLATES.read_path()


DEFAULTS: dict[str, dict[str, float]] = {
    "DAB M":    {"length_cm": 60,  "width_cm": 45, "height_cm": 10, "weight_kg": 3.0},
    "DAB L":    {"length_cm": 85,  "width_cm": 65, "height_cm": 10, "weight_kg": 5.0},
    "DAB XL":   {"length_cm": 105, "width_cm": 85, "height_cm": 12, "weight_kg": 7.0},
    "SOSNA M":  {"length_cm": 60,  "width_cm": 45, "height_cm": 10, "weight_kg": 2.5},
    "SOSNA L":  {"length_cm": 85,  "width_cm": 65, "height_cm": 10, "weight_kg": 4.0},
    "SOSNA XL": {"length_cm": 105, "width_cm": 85, "height_cm": 12, "weight_kg": 6.0},
}

_FIELD_ORDER: tuple[str, ...] = ("length_cm", "width_cm", "height_cm", "weight_kg")


@dataclass
class Template:
    key: str
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0
    weight_kg: float = 0.0
    updated_at: str = ""

    def is_complete(self) -> bool:
        return all(getattr(self, f) > 0 for f in _FIELD_ORDER)

    def format_inline(self) -> str:
        return (
            f"Dlugosc: {self.length_cm:g} cm  |  "
            f"Szerokosc: {self.width_cm:g} cm  |  "
            f"Wysokosc: {self.height_cm:g} cm  |  "
            f"Waga: {self.weight_kg:g} kg"
        )


def _ensure_file() -> None:
    if not _templates_path(for_write=False).is_file():
        now = datetime.now().isoformat(timespec="seconds")
        payload = {
            "templates": [
                {"key": k, **v, "updated_at": now}
                for k, v in DEFAULTS.items()
            ],
        }
        atomic_write_text(_templates_path(for_write=True), json.dumps(payload, indent=2, ensure_ascii=False))


def _raw_templates() -> list[dict]:
    _ensure_file()
    try:
        data = json.loads(_templates_path(for_write=False).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = data.get("templates") if isinstance(data, dict) else None
    return [x for x in raw or [] if isinstance(x, dict)]


def load_templates() -> list[Template]:
    """Zwraca wszystkie szablony posortowane po kluczu."""
    out: list[Template] = []
    for d in _raw_templates():
        key = str(d.get("key") or "").strip()
        if not key:
            continue
        out.append(
            Template(
                key=key,
                length_cm=_safe_float(d.get("length_cm")),
                width_cm=_safe_float(d.get("width_cm")),
                height_cm=_safe_float(d.get("height_cm")),
                weight_kg=_safe_float(d.get("weight_kg")),
                updated_at=str(d.get("updated_at") or ""),
            )
        )
    out.sort(key=lambda t: t.key)
    return out


_LEGACY_TEMPLATE_KEY_ALIASES: dict[str, str] = {
    "DAB S": "DAB M",
    "SOSNA S": "SOSNA M",
}


def get_template(key: str) -> Template | None:
    """Zwraca szablon pasujacy do klucza (np. 'DAB M'). None jesli nie ma."""
    k = (key or "").strip().upper()
    if not k:
        return None
    k = _LEGACY_TEMPLATE_KEY_ALIASES.get(k, k)
    for t in load_templates():
        if t.key.upper() == k:
            return t
    return None


def save_templates(templates: Iterable[Template]) -> None:
    payload = {"templates": [asdict(t) for t in templates]}
    atomic_write_text(_templates_path(for_write=True), json.dumps(payload, indent=2, ensure_ascii=False))


def upsert_template(
    key: str,
    *,
    length_cm: float,
    width_cm: float,
    height_cm: float,
    weight_kg: float,
) -> Template:
    """Dodaje lub aktualizuje szablon pod kluczem (case-insensitive)."""
    k = (key or "").strip().upper()
    if not k:
        raise ValueError("Klucz szablonu nie moze byc pusty.")
    now = datetime.now().isoformat(timespec="seconds")
    items = load_templates()
    found = False
    for t in items:
        if t.key.upper() == k:
            t.key = k
            t.length_cm = float(length_cm)
            t.width_cm = float(width_cm)
            t.height_cm = float(height_cm)
            t.weight_kg = float(weight_kg)
            t.updated_at = now
            found = True
            break
    if not found:
        items.append(
            Template(
                key=k,
                length_cm=float(length_cm),
                width_cm=float(width_cm),
                height_cm=float(height_cm),
                weight_kg=float(weight_kg),
                updated_at=now,
            )
        )
    save_templates(items)
    return next(t for t in items if t.key.upper() == k)


def delete_template(key: str) -> bool:
    k = (key or "").strip().upper()
    items = load_templates()
    filtered = [t for t in items if t.key.upper() != k]
    if len(filtered) == len(items):
        return False
    save_templates(filtered)
    return True


def reset_to_defaults() -> None:
    now = datetime.now().isoformat(timespec="seconds")
    tpls = [
        Template(
            key=k,
            length_cm=float(v["length_cm"]),
            width_cm=float(v["width_cm"]),
            height_cm=float(v["height_cm"]),
            weight_kg=float(v["weight_kg"]),
            updated_at=now,
        )
        for k, v in DEFAULTS.items()
    ]
    save_templates(tpls)


def formatted_for_key(key: str) -> str:
    """Zwraca jedna linijke wymiarow dla klucza lub pusty string."""
    t = get_template(key)
    if t is None or not t.is_complete():
        return ""
    return t.format_inline()


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
