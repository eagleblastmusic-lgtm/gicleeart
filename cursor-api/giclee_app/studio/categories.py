"""Mapowanie komponentów na kategorie sidebaru GicleeApp Studio."""

from __future__ import annotations

import json
from pathlib import Path

from ..component_loader import Component

VALID_CATEGORY_IDS = frozenset({
    "dashboard",
    "asset_lab",
    "theme",
    "products",
    "orders",
    "production",
    "finance",
    "content",
    "review",
    "system",
})

NAV_CATEGORIES: list[tuple[str, str, str]] = [
    ("dashboard", "Dashboard", "◈"),
    ("asset_lab", "Asset Lab", "◇"),
    ("theme", "Strona / Motyw", "◻"),
    ("products", "Produkty", "◆"),
    ("orders", "Zamówienia", "◇"),
    ("production", "Produkcja", "▣"),
    ("finance", "Finanse", "◉"),
    ("content", "Content / AI", "✎"),
    ("review", "Review / GPT", "◎"),
    ("system", "System", "⚙"),
]

_CATEGORIES_PATH = Path(__file__).resolve().parents[1] / "data" / "studio_categories.json"

# Cache mapy kategorii (wczytywany raz z JSON).
_cached_default_category: str | None = None
_cached_folder_to_category: dict[str, str] | None = None
_cached_category_labels: dict[str, str] | None = None


def clear_categories_cache() -> None:
    """Tylko dla testów — wymusza ponowne wczytanie JSON."""
    global _cached_default_category, _cached_folder_to_category, _cached_category_labels
    _cached_default_category = None
    _cached_folder_to_category = None
    _cached_category_labels = None


def _ensure_mapping_loaded() -> tuple[str, dict[str, str]]:
    global _cached_default_category, _cached_folder_to_category, _cached_category_labels
    if _cached_folder_to_category is not None and _cached_default_category is not None:
        return _cached_default_category, _cached_folder_to_category

    default = "system"
    folder_to_cat: dict[str, str] = {}
    labels: dict[str, str] = {}

    if _CATEGORIES_PATH.is_file():
        try:
            data = json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                default = str(data.get("default_category") or "system")
                cats = data.get("categories")
                if isinstance(cats, dict):
                    for cat_id, row in cats.items():
                        if cat_id == "dashboard" or not isinstance(row, dict):
                            continue
                        if row.get("label"):
                            labels[str(cat_id)] = str(row["label"])
                        folders = row.get("folders")
                        if isinstance(folders, list):
                            for folder in folders:
                                folder_to_cat[str(folder)] = str(cat_id)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    _cached_default_category = default
    _cached_folder_to_category = folder_to_cat
    _cached_category_labels = labels
    return default, folder_to_cat


def category_for_folder(folder_name: str) -> str:
    default, mapping = _ensure_mapping_loaded()
    return mapping.get(folder_name, default)


def category_label(category_id: str) -> str:
    for cid, label, _icon in NAV_CATEGORIES:
        if cid == category_id:
            return label
    _ensure_mapping_loaded()
    if _cached_category_labels and category_id in _cached_category_labels:
        return _cached_category_labels[category_id]
    return category_id


def all_folder_mappings() -> dict[str, str]:
    _default, mapping = _ensure_mapping_loaded()
    return dict(mapping)


def components_for_category(
    category_id: str,
    *,
    all_components: list[Component] | None = None,
    include_hidden: bool = True,
) -> list[Component]:
    """Komponenty przypisane do kategorii.

    Gdy podano ``all_components`` (z StudioComponentIndex), bez ponownego discover.
    """
    if category_id in ("dashboard", "asset_lab"):
        return []
    if all_components is not None:
        return [c for c in all_components if category_for_folder(c.folder_name) == category_id]
    from ..component_loader import discover_components, find_components_dir

    root = find_components_dir()
    discovered = discover_components(root, include_hidden=include_hidden)
    return [c for c in discovered if category_for_folder(c.folder_name) == category_id]


def discover_valid_component_folders(components_dir=None) -> set[str]:  # noqa: ANN001
    """Foldery uznawane za komponenty (jak discover_components)."""
    from ..component_loader import discover_components, find_components_dir

    root = components_dir or find_components_dir()
    return {c.folder_name for c in discover_components(root, include_hidden=True)}
