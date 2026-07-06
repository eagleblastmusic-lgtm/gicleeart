"""Testy GICLÉE FRAME™ shell view — import / AST / copy guardrails."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_brief import status_strip, WORKFLOW_SUMMARY
from giclee_app.ui.gicleeframe_view import GicleeFrameView, _BACK_LABEL

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"
_VIEW_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"
_NEW_PLANNING_MODULES = (
    "gicleeframe_brief.py",
    "gicleeframe_draft_state.py",
    "gicleeframe_dry_run.py",
    "gicleeframe_readiness.py",
    "gicleeframe_page_inventory.py",
    "gicleeframe_page_draft.py",
    "gicleeframe_page_dry_run.py",
)

# Zakazane jako tekst przycisków/akcji — nie jako informacyjny status.
_FORBIDDEN_BUTTON_PATTERNS = (
    r'text\s*=\s*["\']Zapisz',
    r'text\s*=\s*["\']Zastosuj',
    r'text\s*=\s*["\']Sync["\']',
    r'text\s*=\s*["\']Deploy',
    r'text\s*=\s*["\']Upload',
    r'text\s*=\s*["\']Publish',
    r'text\s*=\s*["\']Wdróż',
    r'text\s*=\s*["\']Save',
)


def test_view_source_no_komponenty_imports() -> None:
    tree = ast.parse(_VIEW_PATH.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_view_source_no_forbidden_action_buttons() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert _BACK_LABEL in text
    assert "_SHELL_STATUS_CHIP" in text
    assert "RAM-only · bez zapisu" in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f21_editor_labels() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "PAGE_EDITOR_TITLE" in text
    assert "SECTION_EDITOR_TITLE" in text
    assert "_section_list_trigger" in text
    assert "DEFAULT_VARIANT_NAME" in text
    assert "WORKING_VARIANT_LABEL" in text
    assert "working_variant_menu_label" in text
    assert "ADD_VARIANT_RAM_LABEL" in text
    assert "+ Dodaj wariant" not in text
    assert "DUPLICATE_VARIANT_LABEL" in text
    assert "RENAME_VARIANT_LABEL" in text
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert "editor_field_visibility" in text
    assert "editor_context_rows" in text
    assert "_editor_status_dot" in text
    assert "_section_list_scroll" in text
    assert "_section_dropdown_popup" in text
    assert "_toggle_section_list" in text
    assert "_SECTION_LIST_WIDTH" in text
    assert "SECTION_LIST_DRAG_HINT" in text
    assert "reorder_page_blocks" in text
    assert "_structure_dry_run_btn" in text
    assert "_toggle_page_readiness" in text
    assert "_PAGE_READINESS_TITLE" in text


def test_view_source_allows_informational_sync_blocked_text() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "zablokowane" in text.lower() or "Zablokowane" in text


def test_view_source_no_write_or_network() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
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
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "PLAN_SECTION_TITLE" in text
    assert "CHECK_PLAN_LABEL" in text
    assert "CLEAR_PLAN_LABEL" in text
    assert "build_gicleeframe_plan_dry_run" in text
    assert "evaluate_gicleeframe_readiness" in text
    assert "READINESS_SECTION_LABEL" in text
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
