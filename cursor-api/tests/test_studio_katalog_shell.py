"""Testy Katalog shell view (F1) — import / AST / copy guardrails."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.categories import NAV_CATEGORIES, VALID_CATEGORY_IDS
from giclee_app.studio.katalog_inventory import status_strip, workflow_summary
from giclee_app.ui.katalog_view import KatalogView, _BACK_LABEL, _REFRESH_LABEL

_FORBIDDEN_UI_LABELS = (
    "Zapisz",
    "Zapisz lokalnie",
    "Zastosuj",
    "Sync",
    "Deploy",
    "Upload",
    "Import",
    "Migracja",
    "SAVE_LOCAL_LABEL",
    "shopify",
)


def test_katalog_in_nav_categories() -> None:
    nav_ids = [cid for cid, _label, _icon in NAV_CATEGORIES]
    assert "katalog" in nav_ids
    assert "katalog" in VALID_CATEGORY_IDS


def test_view_source_no_komponenty_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "katalog_view.py"
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


def test_view_source_read_only_no_save_buttons() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "katalog_view.py"
    text = path.read_text(encoding="utf-8")
    assert _REFRESH_LABEL in text
    assert "Parent workflow" in text
    assert "absorbed subflow" in text
    assert "Read-only" in text or "read-only" in text
    for label in _FORBIDDEN_UI_LABELS:
        assert label not in text


def test_view_source_no_write_or_network() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "katalog_view.py"
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "requests" not in text
    assert "filedialog" not in text
    assert "shutil" not in text


def test_launcher_studio_routes_katalog() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "_show_katalog" in text
    assert '_show_katalog_shell' in text
    assert 'comp.folder_name == "katalog"' in text
    assert "KatalogView" in text


def test_launcher_intercept_not_for_tldobio() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert 'comp.folder_name == "tldobio"' not in text


def test_inventory_helpers_read_only_copy() -> None:
    assert "read-only" in workflow_summary().lower() or "parent" in workflow_summary().lower()
    assert "no Save" in status_strip()
    assert "no writer" in status_strip()
    assert "no Shopify" in status_strip()


def test_import_katalog_view_module() -> None:
    assert KatalogView.__name__ == "KatalogView"
    assert _BACK_LABEL == "Wróć do huba"
