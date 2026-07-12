"""Przypisania produkt -> szablon wariantow (lokalnie, poza Shopify).

Persystencja: `Komponenty/dodajobraz/data/product_template_assignments.json`:
{
  "assignments": {
    "15524677845340": "abc123def456"
  }
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from giclee_app.app_paths import atomic_write_text, data_path

from . import templates as variant_templates

_LEGACY_DATA_DIR = Path(__file__).resolve().parent / "data"
_LEGACY_ASSIGNMENTS_FILE = _LEGACY_DATA_DIR / "product_template_assignments.json"
_DATA_DIR = _LEGACY_DATA_DIR
_ASSIGNMENTS_FILE = _LEGACY_ASSIGNMENTS_FILE


def _assignments_path(*, for_write: bool = False) -> Path:
    data_dir = Path(_DATA_DIR)
    current = Path(_ASSIGNMENTS_FILE)
    if data_dir != _LEGACY_DATA_DIR and current == _LEGACY_ASSIGNMENTS_FILE:
        current = data_dir / "product_template_assignments.json"
    if current != _LEGACY_ASSIGNMENTS_FILE:
        return current
    app_path = data_path(
        "Komponenty/dodajobraz/data/product_template_assignments.json",
        legacy=_LEGACY_ASSIGNMENTS_FILE,
    )
    return app_path.write_path if for_write else app_path.read_path()


def _variant_key(v: dict[str, Any]) -> tuple[str, ...]:
    parts: list[str] = []
    for i in (1, 2, 3):
        val = v.get(f"option{i}")
        if val is not None and str(val).strip():
            parts.append(str(val).strip())
    return tuple(parts)


def _ensure_dir() -> None:
    _assignments_path(for_write=True).parent.mkdir(parents=True, exist_ok=True)


def load_assignments() -> dict[int, str]:
    _ensure_dir()
    path = _assignments_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    raw = data.get("assignments") if isinstance(data, dict) else {}
    if not isinstance(raw, dict):
        return {}
    out: dict[int, str] = {}
    for key, tid in raw.items():
        try:
            pid = int(key)
        except (TypeError, ValueError):
            continue
        tid_s = str(tid or "").strip()
        if pid > 0 and tid_s:
            out[pid] = tid_s
    return out


def save_assignments(assignments: dict[int, str]) -> None:
    _ensure_dir()
    payload = {
        "assignments": {str(pid): tid for pid, tid in sorted(assignments.items())},
    }
    atomic_write_text(
        _assignments_path(for_write=True),
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
    )


def get_assigned_template_id(product_id: int) -> str | None:
    return load_assignments().get(int(product_id))


def set_product_template_assignment(product_id: int, template_id: str) -> None:
    pid = int(product_id)
    tid = str(template_id or "").strip()
    if pid <= 0 or not tid:
        return
    assignments = load_assignments()
    assignments[pid] = tid
    save_assignments(assignments)


def set_product_template_assignments_batch(
    product_ids: list[int],
    template_id: str,
) -> int:
    tid = str(template_id or "").strip()
    if not tid:
        return 0
    assignments = load_assignments()
    n = 0
    for raw in product_ids:
        pid = int(raw)
        if pid <= 0:
            continue
        assignments[pid] = tid
        n += 1
    if n:
        save_assignments(assignments)
    return n


def clear_product_template_assignment(product_id: int) -> None:
    pid = int(product_id)
    assignments = load_assignments()
    if pid in assignments:
        del assignments[pid]
        save_assignments(assignments)


def infer_template_id_from_variants(variants: list[dict[str, Any]]) -> str | None:
    """Dopasowuje szablon po zestawie kluczy wariantow (option1/2/3)."""
    product_keys = {_variant_key(v) for v in variants if _variant_key(v)}
    if not product_keys:
        return None
    best_id: str | None = None
    best_score = -1
    for template in variant_templates.load_templates():
        template_keys = {_variant_key(v) for v in template.variants if _variant_key(v)}
        if not template_keys:
            continue
        if product_keys == template_keys:
            return template.id
        overlap = len(product_keys & template_keys)
        if overlap > best_score:
            best_score = overlap
            best_id = template.id
    if best_score > 0 and best_id:
        return best_id
    return None


def resolve_template_for_product(
    product_id: int,
    *,
    variants: list[dict[str, Any]] | None = None,
) -> variant_templates.VariantTemplate | None:
    """Przypisanie reczne > inferencja z wariantow > szablon domyslny."""
    assigned = get_assigned_template_id(product_id)
    if assigned:
        t = variant_templates.get_by_id(assigned)
        if t:
            return t
    if variants:
        inferred = infer_template_id_from_variants(variants)
        if inferred:
            t = variant_templates.get_by_id(inferred)
            if t:
                return t
    return variant_templates.get_default()


def template_label_for_product(
    product_id: int,
    *,
    variants: list[dict[str, Any]] | None = None,
) -> tuple[str, str, bool]:
    """Zwraca (nazwa_szablonu, template_id, czy_jawne_przypisanie)."""
    assigned = get_assigned_template_id(product_id)
    if assigned:
        t = variant_templates.get_by_id(assigned)
        if t:
            return t.name, t.id, True
        return f"(brak: {assigned[:8]}…)", assigned, True
    if variants:
        inferred = infer_template_id_from_variants(variants)
        if inferred:
            t = variant_templates.get_by_id(inferred)
            if t:
                return f"{t.name} (dopas.)", t.id, False
    default = variant_templates.get_default()
    if default:
        return f"{default.name} (dom.)", default.id, False
    return "(brak szablonu)", "", False
