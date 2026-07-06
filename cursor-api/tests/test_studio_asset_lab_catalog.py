"""Testy katalogu Asset Lab (F6.2) — pure read-only mapping."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.asset_lab_catalog import (
    ASSET_LAB_FOLDERS,
    is_asset_lab_folder,
    tools_in_order,
)
from giclee_app.studio.component_index import StudioComponentIndex

_EXPECTED_FOLDERS = (
    "nazwijobraz",
    "infoplikow",
    "squoosh",
    "print_optimize",
    "przedpo",
    "kolaz",
    "mockup",
    "pobierzobraz",
)


def test_asset_lab_folders_exactly_eight() -> None:
    assert len(ASSET_LAB_FOLDERS) == 8
    assert ASSET_LAB_FOLDERS == _EXPECTED_FOLDERS


def test_tools_in_order_unique_and_sorted() -> None:
    tools = tools_in_order()
    assert len(tools) == 8
    folders = [t.folder for t in tools]
    assert len(folders) == len(set(folders))
    orders = [t.sort_order for t in tools]
    assert orders == sorted(orders)
    assert folders == list(_EXPECTED_FOLDERS)


def test_is_asset_lab_folder_membership() -> None:
    assert is_asset_lab_folder("mockup") is True
    assert is_asset_lab_folder("dodajobraz") is False
    assert is_asset_lab_folder("finanse") is False


def test_all_catalog_folders_in_component_index() -> None:
    index = StudioComponentIndex.build()
    for folder in ASSET_LAB_FOLDERS:
        assert folder in index.by_folder, folder


def test_all_catalog_folders_are_subprocess() -> None:
    index = StudioComponentIndex.build()
    for folder in ASSET_LAB_FOLDERS:
        comp = index.by_folder[folder]
        assert comp.mode == "subprocess", folder


def test_finance_and_product_pipeline_not_in_asset_lab() -> None:
    assert not is_asset_lab_folder("finanse")
    assert not is_asset_lab_folder("dodajobraz")
    assert not is_asset_lab_folder("aktualizujopis")
    assert not is_asset_lab_folder("stronaglowna")


def test_catalog_source_no_forbidden_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "studio"
        / "asset_lab_catalog.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for forbidden in ("Komponenty", "shopify", "requests", "subprocess"):
        for imp in imports:
            assert forbidden not in imp.lower()


def test_catalog_source_no_io_patterns() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "studio"
        / "asset_lab_catalog.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert "open(" not in text
    assert "glob(" not in text
    assert "rglob(" not in text
