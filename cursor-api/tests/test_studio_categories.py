"""Testy mapy kategorii GicleeApp Studio."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import discover_components, find_components_dir
from giclee_app.studio.categories import (
    VALID_CATEGORY_IDS,
    all_folder_mappings,
    category_for_folder,
    discover_valid_component_folders,
)


def test_valid_category_ids_exclude_dashboard_from_json_keys() -> None:
    mapping = all_folder_mappings()
    for cat_id in set(mapping.values()):
        assert cat_id in VALID_CATEGORY_IDS
        assert cat_id != "dashboard"


def test_no_duplicate_folders_in_json() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "data" / "studio_categories.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    cats = data.get("categories", {})
    assert isinstance(cats, dict)
    for _cat_id, row in cats.items():
        folders = row.get("folders", [])
        assert isinstance(folders, list)
        for folder in folders:
            assert folder not in seen, f"duplicate folder: {folder}"
            seen.add(folder)


def test_every_discovered_component_has_resolvable_category() -> None:
    root = find_components_dir()
    folders = discover_valid_component_folders(root)
    assert folders, "expected at least one component"
    for folder in folders:
        cat = category_for_folder(folder)
        assert cat in VALID_CATEGORY_IDS - {"dashboard"}


def test_known_product_in_products_category() -> None:
    assert category_for_folder("dodajobraz") == "products"
    assert category_for_folder("stronaglowna") == "theme"
    assert category_for_folder("produkcja") == "production"
    assert category_for_folder("integracjagpt") == "review"
    assert category_for_folder("pushe") == "system"


def test_unmapped_falls_back_to_system() -> None:
    assert category_for_folder("__nonexistent_xyz__") == "system"


def test_components_for_category_filters() -> None:
    root = find_components_dir()
    theme_comps = [
        c.folder_name
        for c in discover_components(root, include_hidden=True)
        if category_for_folder(c.folder_name) == "theme"
    ]
    assert "stronaglowna" in theme_comps
