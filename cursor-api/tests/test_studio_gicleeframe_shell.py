"""Testy GICLÉE FRAME™ shell view — import / AST / copy guardrails."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_brief import status_strip, WORKFLOW_SUMMARY
from giclee_app.ui.gicleeframe_view import GicleeFrameView, _BACK_LABEL

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"
_NEW_PLANNING_MODULES = (
    "gicleeframe_brief.py",
    "gicleeframe_draft_state.py",
    "gicleeframe_dry_run.py",
    "gicleeframe_readiness.py",
    "gicleeframe_page_inventory.py",
    "gicleeframe_page_draft.py",
    "gicleeframe_page_dry_run.py",
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
    "Legacy editor",
    "shopify",
)


def test_view_source_no_komponenty_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"
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
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    assert _BACK_LABEL in text
    assert "PLANNING_BADGE" in text
    assert "DRY_RUN_BADGE" in text
    for label in _FORBIDDEN_UI_LABELS:
        assert label not in text


def test_view_source_no_write_or_network() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "requests" not in text
    assert "filedialog" not in text
    assert "shutil" not in text


def test_launcher_studio_routes_gicleeframe() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    assert "_show_gicleeframe_shell" in text
    assert 'comp.folder_name == "gicleeframe"' in text
    assert "GicleeFrameView" in text
    assert "_return_from_gicleeframe" in text


def test_brief_helpers_copy() -> None:
    assert "GICLÉE FRAME" in WORKFLOW_SUMMARY
    strip = status_strip()
    assert "planowanie lokalne" in strip
    assert "zablokowane" in strip


def test_import_gicleeframe_view_module() -> None:
    assert GicleeFrameView.__name__ == "GicleeFrameView"
    assert _BACK_LABEL == "Wróć do huba"


def test_view_source_plan_section() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    assert "PLAN_SECTION_TITLE" in text
    assert "CHECK_PLAN_LABEL" in text
    assert "CLEAR_PLAN_LABEL" in text
    assert "build_gicleeframe_plan_dry_run" in text
    assert "evaluate_gicleeframe_readiness" in text
    assert "READINESS_SECTION_LABEL" in text
    assert "Struktura strony GICLÉE FRAME" in text
    assert "REFRESH_INVENTORY_LABEL" in text
    assert "CHECK_STRUCTURE_LABEL" in text
    assert "DRAFT_RAM_DISCLAIMER" in text


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
