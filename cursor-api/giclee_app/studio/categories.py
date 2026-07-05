"""Mapowanie komponentów na kategorie sidebaru GicleeApp Studio."""

from __future__ import annotations

import json
from pathlib import Path

from ..component_loader import Component, discover_components, find_components_dir

VALID_CATEGORY_IDS = frozenset({
    "dashboard",
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


def _load_mapping() -> tuple[str, dict[str, str]]:
    """Zwraca (default_category, folder -> category_id)."""
    default = "system"
    folder_to_cat: dict[str, str] = {}
    if not _CATEGORIES_PATH.is_file():
        return default, folder_to_cat
    try:
        data = json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default, folder_to_cat
    if not isinstance(data, dict):
        return default, folder_to_cat
    default = str(data.get("default_category") or "system")
    cats = data.get("categories")
    if not isinstance(cats, dict):
        return default, folder_to_cat
    for cat_id, row in cats.items():
        if cat_id == "dashboard" or not isinstance(row, dict):
            continue
        folders = row.get("folders")
        if not isinstance(folders, list):
            continue
        for folder in folders:
            folder_to_cat[str(folder)] = str(cat_id)
    return default, folder_to_cat


def category_for_folder(folder_name: str) -> str:
    default, mapping = _load_mapping()
    return mapping.get(folder_name, default)


def category_label(category_id: str) -> str:
    for cid, label, _icon in NAV_CATEGORIES:
        if cid == category_id:
            return label
    _, mapping = _load_mapping()
    if _CATEGORIES_PATH.is_file():
        try:
            data = json.loads(_CATEGORIES_PATH.read_text(encoding="utf-8"))
            cats = data.get("categories") if isinstance(data, dict) else None
            if isinstance(cats, dict) and category_id in cats:
                row = cats[category_id]
                if isinstance(row, dict) and row.get("label"):
                    return str(row["label"])
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    return category_id


def all_folder_mappings() -> dict[str, str]:
    """folder_name -> category_id (z pliku JSON)."""
    _default, mapping = _load_mapping()
    return dict(mapping)


def components_for_category(
    category_id: str,
    *,
    components_dir: Path | None = None,
    include_hidden: bool = True,
) -> list[Component]:
    """Komponenty przypisane do kategorii (posortowane jak discover)."""
    if category_id == "dashboard":
        return []
    root = components_dir or find_components_dir()
    all_comps = discover_components(root, include_hidden=include_hidden)
    return [c for c in all_comps if category_for_folder(c.folder_name) == category_id]


def discover_valid_component_folders(components_dir: Path | None = None) -> set[str]:
    """Foldery uznawane za komponenty (jak discover_components)."""
    root = components_dir or find_components_dir()
    return {c.folder_name for c in discover_components(root, include_hidden=True)}
