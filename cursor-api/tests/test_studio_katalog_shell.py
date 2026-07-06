"""Testy Katalog shell view (F1+F2) — import / AST / copy guardrails."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.categories import NAV_CATEGORIES, VALID_CATEGORY_IDS
from giclee_app.studio.katalog_data_map import f2_status_strip, f3_status_strip
from giclee_app.studio.katalog_inventory import status_strip, workflow_summary
from giclee_app.ui.katalog_view import KatalogView, _BACK_LABEL, _REFRESH_LABEL

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"
_NEW_PLANNING_MODULES = (
    "katalog_draft_state.py",
    "katalog_dry_run.py",
    "katalog_readiness.py",
)

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
    assert "absorbed" in text.lower()
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


def test_view_source_f2_data_map_section() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "katalog_view.py"
    text = path.read_text(encoding="utf-8")
    assert "Mapa danych (F2)" in text
    assert "Katalog F2 data map" in text
    assert "build_katalog_data_map" in text
    assert "data_map_display_rows" in text
    assert "f2_status_strip" in text
    assert "service.py" not in text


def test_inventory_helpers_read_only_copy() -> None:
    assert "read-only" in workflow_summary().lower() or "parent" in workflow_summary().lower()
    assert "F1+F2" in status_strip()
    assert "no Save" in status_strip()
    assert "no writer" in status_strip()
    assert "no Shopify" in status_strip()


def test_f2_status_strip_policies() -> None:
    strip = f2_status_strip()
    assert "out-of-scope" in strip.lower() or "out_of_scope" in strip
    assert "no writer" in strip.lower() or "not_started" in strip
    assert "no Save" in strip or "read-only" in strip.lower()


def test_import_katalog_view_module() -> None:
    assert KatalogView.__name__ == "KatalogView"
    assert _BACK_LABEL == "Wróć do huba"


def test_view_source_f3_plan_section() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "katalog_view.py"
    text = path.read_text(encoding="utf-8")
    assert "PLAN_SECTION_TITLE" in text
    assert "CHECK_PLAN_LABEL" in text
    assert "CLEAR_PLAN_LABEL" in text
    assert "local planning only" in text
    assert "DRY_RUN_BADGE" in text
    assert "DRAFT_DISCLAIMER" in text
    assert "F3_READINESS_DISCLAIMER" in text
    assert "f3_status_strip" in text
    assert "build_katalog_plan_dry_run" in text
    assert "evaluate_katalog_plan_readiness" in text


def test_f3_status_strip_copy() -> None:
    strip = f3_status_strip()
    assert "local planning only" in strip
    assert "dry-run" in strip
    assert "not started" in strip


def _assert_no_writes_in_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "shutil" not in text
    assert "requests" not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_planning_modules_source_guardrails() -> None:
    for name in _NEW_PLANNING_MODULES:
        _assert_no_writes_in_source(_STUDIO_ROOT / name)
