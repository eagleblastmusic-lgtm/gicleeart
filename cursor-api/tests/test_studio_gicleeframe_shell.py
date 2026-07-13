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
_BRAND_PANEL_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_brand.py"
)
_PRIMITIVES_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_primitives.py"
)
_PAGE_READINESS_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_page_readiness.py"
)
_STRUCTURE_DRY_RUN_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_structure_dry_run.py"
)
_SAFETY_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_safety.py"
)
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


def _self_method_calls(source: str, method: str) -> list[ast.Call]:
    """Active `self.<method>(...)` calls — AST ignores commented-out lines."""
    tree = ast.parse(source)
    hits: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == method
            and isinstance(func.value, ast.Name)
            and func.value.id == "self"
        ):
            hits.append(node)
    return hits


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
    assert "_build_control_column" in text
    assert "_CONTROL_COL_MINSIZE" in text
    assert "SECTION_LIST_TITLE" in text
    assert "APPLY_RAM_MICROCOPY" in text
    assert "PANEL_STATUS_UNSAVED" in text
    assert "_make_primary_button" in text
    assert "_build_setting_group_card" in text
    assert "divider_setting_groups" in text
    assert "_make_empty_state" in text
    assert "_build_command_bar" in text
    assert "_build_section_identity_card" in text
    assert "_build_action_dock" in text
    assert "_PREVIEW_SETTINGS_CAPTION" in text
    assert "_pack_field_vertical" in text
    assert "_update_section_preview" in text


def test_view_source_f222_premium_copy() -> None:
    from giclee_app.studio.gicleeframe_page_draft import (
        APPLY_RAM_DRAFT_LABEL,
        APPLY_RAM_MICROCOPY,
    )

    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert "APPLY_RAM_MICROCOPY" in text
    assert "Tylko pamięć" in APPLY_RAM_MICROCOPY
    assert "_PREVIEW_SETTINGS_CAPTION" in text
    assert "Podgląd ustawień" in text
    assert "RAM-only" in text
    assert "Widoczna" in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f223_first_screen_composition() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "_ellipsize" in text
    assert "_SECTION_LIST_WIDTH = 320" in text
    assert "_EDITOR_HERO_PREVIEW_HEIGHT" in text
    assert "_SECTION_ROW_HEIGHT" in text
    assert "RAM preview" in text
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert "_build_section_identity_card" in text
    assert "_build_action_dock" in text
    assert "F2.2.3" in text
    assert _self_method_calls(text, "_build_action_dock") == []


def test_view_source_f224_visual_tokens() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    primitives_text = _PRIMITIVES_PATH.read_text(encoding="utf-8")
    assert "F2.2.4" in text
    assert "_GF_PREVIEW_PAPER" in text
    assert "_make_gf_card" in text
    assert "_section_kind_copy" in text
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert '_GF_PREVIEW_PAPER = "#2e2e32"' in primitives_text
    assert "write_text" not in text
    assert _self_method_calls(text, "_build_action_dock") == []
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f225_section_workbench() -> None:
    from giclee_app.studio.gicleeframe_page_draft import APPLY_RAM_DRAFT_LABEL

    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "F2.2.5" in text
    assert "_section_preview_canvas" in text
    assert "_section_preview_badge" in text
    assert "_build_media_section_preview_structure" in text
    assert "_build_divider_preview_structure" in text
    assert "_build_legacy_preview_structure" in text
    assert "_build_text_preview_structure" in text
    assert "Warstwy sekcji" in text
    assert "Kliknij, aby edytować" in text
    assert "Workbench sekcji" in text
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert '"Komponenty"' not in text
    assert "write_text" not in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f226_child_layer_and_color() -> None:
    from giclee_app.studio.gicleeframe_page_draft import APPLY_RAM_DRAFT_LABEL

    text = _VIEW_PATH.read_text(encoding="utf-8")
    primitives_text = _PRIMITIVES_PATH.read_text(encoding="utf-8")
    assert "F2.2.6" in text
    assert "_LAYER_NAV_TITLE" in text
    assert "_IMAGE_SOURCE_TITLE" in text
    assert "_layer_nav_frame" in text
    assert "_update_layer_nav" in text
    assert "_parent_row_for_element" in text
    assert "_selected_layer_items" in text
    assert "_build_image_preview_structure" in text
    assert "_image_ref_label" in text
    assert '_GF_PANEL = "#1e1e21"' in primitives_text
    assert '_GF_GOLD = "#b8a878"' in primitives_text
    assert '_GF_PANEL = "#1e1e21"' not in text
    assert "panel_deep" in text
    assert "Grafika sekcji" in text
    assert "Źródło grafiki" in text
    assert "Warstwy sekcji" in text
    assert "Workbench sekcji" in text
    assert "APPLY_RAM_DRAFT_LABEL" in text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert "write_text" not in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f221_setting_groups() -> None:
    from giclee_app.studio.gicleeframe_page_settings import divider_setting_groups

    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "divider_setting_groups" in text
    group_titles = [title for title, _keys in divider_setting_groups()]
    for group in ("Linia", "Układ", "Styl"):
        assert group in group_titles


def test_view_source_allows_informational_sync_blocked_text() -> None:
    text = _SAFETY_VIEW_PATH.read_text(encoding="utf-8")
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
    host = _VIEW_PATH.read_text(encoding="utf-8")
    brand = _BRAND_PANEL_PATH.read_text(encoding="utf-8")
    assert "PLAN_SECTION_TITLE" in brand
    assert "CHECK_PLAN_LABEL" in brand
    assert "CLEAR_PLAN_LABEL" in brand
    assert "build_gicleeframe_plan_dry_run" in brand
    assert "evaluate_gicleeframe_readiness" in brand
    assert "READINESS_SECTION_LABEL" in brand
    text = host
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


def test_primitives_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_PRIMITIVES_PATH)


def test_page_readiness_view_source_contract() -> None:
    text = _PAGE_READINESS_VIEW_PATH.read_text(encoding="utf-8")
    assert "_toggle_page_readiness" in text
    assert "_PAGE_READINESS_TITLE" in text
    assert "Readiness (strona)" in text


def test_page_readiness_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_PAGE_READINESS_VIEW_PATH)


def test_structure_dry_run_view_source_contract() -> None:
    text = _STRUCTURE_DRY_RUN_VIEW_PATH.read_text(encoding="utf-8")
    assert "_build_control_structure_card" in text
    assert "_reset_structure_dry_run_display" in text
    assert "_run_structure_dry_run" in text
    assert "STRUCTURE_EMPTY_STATE" in text
    assert "_STRUCTURE_DRY_RUN_WRAPLENGTH = 292" in text
    assert "Podgląd struktury" in text


def test_structure_dry_run_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_STRUCTURE_DRY_RUN_VIEW_PATH)
    text = _STRUCTURE_DRY_RUN_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in text


def test_safety_view_source_contract() -> None:
    text = _SAFETY_VIEW_PATH.read_text(encoding="utf-8")
    assert "_build_safety_card" in text
    assert "_SAFETY_TITLE" in text
    assert "_SAFETY_CHECKLIST" in text
    assert "_SAFETY_ROW_WRAPLENGTH = 276" in text
    assert "_build_safety_row" in text
    assert "Bezpieczeństwo" in text
    assert "RAM-only" in text
    assert "Brak zapisu motywu" in text
    assert "Sync/deploy zablokowane" in text
    assert "F3/F4 osobna decyzja" in text


def test_safety_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_SAFETY_VIEW_PATH)
    text = _SAFETY_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in text
