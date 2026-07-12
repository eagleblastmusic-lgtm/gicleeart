"""Mapowanie komponentów na kategorie sidebaru GicleeApp Studio."""

from __future__ import annotations

import json
from pathlib import Path

from ..app_paths import config_path
from ..component_loader import Component

VALID_CATEGORY_IDS = frozenset({
    "dashboard",
    "asset_lab",
    "katalog",
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
    ("katalog", "Katalog", "▤"),
    ("theme", "Strona / Motyw", "◻"),
    ("products", "Produkty", "◆"),
    ("orders", "Zamówienia", "◇"),
    ("production", "Produkcja", "▣"),
    ("finance", "Finanse", "◉"),
    ("content", "Content / AI", "✎"),
    ("review", "Review / GPT", "◎"),
    ("system", "System", "⚙"),
]

DEFAULT_CATEGORIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "resources"
    / "studio_categories.default.json"
)
_LEGACY_CATEGORIES_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "studio_categories.json"
)
_CATEGORIES_PATH = _LEGACY_CATEGORIES_PATH
_CATEGORIES = config_path(
    "giclee_app/data/studio_categories.json",
    legacy=_LEGACY_CATEGORIES_PATH,
)


def _categories_path() -> Path:
    if Path(_CATEGORIES_PATH) != _LEGACY_CATEGORIES_PATH:
        return Path(_CATEGORIES_PATH)
    return _CATEGORIES.read_path()

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


def _load_mapping_from_path(
    path: Path,
) -> tuple[str, dict[str, str], dict[str, str]] | None:
    if not path.is_file():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if not isinstance(data, dict):
        return None

    cats = data.get("categories")

    if not isinstance(cats, dict):
        return None

    default = str(data.get("default_category") or "system")
    folder_to_cat: dict[str, str] = {}
    labels: dict[str, str] = {}

    for cat_id, row in cats.items():
        if cat_id == "dashboard" or not isinstance(row, dict):
            continue

        if row.get("label"):
            labels[str(cat_id)] = str(row["label"])

        folders = row.get("folders")

        if not isinstance(folders, list):
            continue

        for folder in folders:
            folder_to_cat[str(folder)] = str(cat_id)

    return default, folder_to_cat, labels


def _mapping_source_paths() -> tuple[Path, ...]:
    paths: list[Path] = []

    for path in (
        _categories_path(),
        Path(_LEGACY_CATEGORIES_PATH),
        DEFAULT_CATEGORIES_PATH,
    ):
        if path not in paths:
            paths.append(path)

    return tuple(paths)


def _ensure_mapping_loaded() -> tuple[str, dict[str, str]]:
    global _cached_default_category, _cached_folder_to_category, _cached_category_labels
    if _cached_folder_to_category is not None and _cached_default_category is not None:
        return _cached_default_category, _cached_folder_to_category

    loaded: tuple[
        str,
        dict[str, str],
        dict[str, str],
    ] | None = None

    for path in _mapping_source_paths():
        loaded = _load_mapping_from_path(path)

        if loaded is not None:
            break

    if loaded is None:
        default = "system"
        folder_to_cat: dict[str, str] = {}
        labels: dict[str, str] = {}
    else:
        default, folder_to_cat, labels = loaded

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
    if category_id in ("dashboard", "asset_lab", "katalog"):
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
