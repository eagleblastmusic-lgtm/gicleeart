"""Testy Asset Lab view (F6.2) — import / AST / tool_card_rows bez Tk mainloop."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.asset_lab_catalog import ASSET_LAB_FOLDERS, tools_in_order
from giclee_app.studio.categories import NAV_CATEGORIES, VALID_CATEGORY_IDS
from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.ui.asset_lab_view import tool_card_rows


def test_asset_lab_in_nav_categories() -> None:
    nav_ids = [cid for cid, _label, _icon in NAV_CATEGORIES]
    assert "asset_lab" in nav_ids
    assert "asset_lab" in VALID_CATEGORY_IDS


def test_tool_card_rows_count_and_order() -> None:
    index = StudioComponentIndex.build()
    rows = tool_card_rows(by_folder=index.by_folder)
    assert len(rows) == 8
    assert [r["folder"] for r in rows] == list(ASSET_LAB_FOLDERS)


def test_tool_card_rows_all_available_in_registry() -> None:
    index = StudioComponentIndex.build()
    rows = tool_card_rows(by_folder=index.by_folder)
    for row in rows:
        assert row["available"] is True
        assert row["mode"] == "subprocess"
        assert row["risk"] in ("N", "M", "H")


def test_tool_card_rows_missing_component_unavailable() -> None:
    rows = tool_card_rows(by_folder={})
    assert len(rows) == 8
    assert all(row["available"] is False for row in rows)


def test_view_source_no_komponenty_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "asset_lab_view.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_view_uses_shared_asset_lab_tool_card() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "asset_lab_view.py"
    text = path.read_text(encoding="utf-8")
    assert "AssetLabToolCard" in text
    widgets = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    assert "class AssetLabToolCard" in widgets.read_text(encoding="utf-8")
    assert "class ComponentCard" in widgets.read_text(encoding="utf-8")


def test_asset_lab_tool_card_click_launch_no_button() -> None:
    widgets = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "widgets.py"
    text = widgets.read_text(encoding="utf-8")
    start = text.index("class AssetLabToolCard")
    end = text.index("class StatCard", start)
    block = text[start:end]
    assert "CTkButton" not in block
    assert "Otwórz narzędzie" not in block
    assert "_handle_click" in block
    assert '"<Button-1>"' in block
    assert "kliknij, aby otworzyć" in block


def test_view_source_no_write_or_glob() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "asset_lab_view.py"
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert "Komponenty." not in text
    assert "glob(" not in text
    assert "rglob(" not in text


def test_import_asset_lab_view_module() -> None:
    __import__("giclee_app.ui.asset_lab_view")


def test_tools_in_order_matches_card_rows() -> None:
    index = StudioComponentIndex.build()
    rows = tool_card_rows(by_folder=index.by_folder)
    for tool, row in zip(tools_in_order(), rows, strict=True):
        assert row["folder"] == tool.folder
        assert row["summary"] == tool.summary
        assert row["risk"] == tool.risk
