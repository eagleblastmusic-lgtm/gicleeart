"""Testy GICLÉE FRAME™ shell view — import / AST / copy guardrails."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_brief import status_strip, WORKFLOW_SUMMARY
from giclee_app.ui.gicleeframe_view import GicleeFrameView
from giclee_app.ui.gicleeframe_view_top_bar import _BACK_LABEL

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
_READINESS_ROW_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_readiness_row.py"
)
_TOP_BAR_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_top_bar.py"
)
_RAM_VARIANTS_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_ram_variants.py"
)
_SECTION_LIST_SHELL_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_section_list_shell.py"
)
_SECTION_LIST_INTERACTION_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_section_list_interaction.py"
)
_SECTION_LIST_RENDERING_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_section_list_rendering.py"
)
_EDITOR_SHELL_VIEW_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_editor_shell.py"
)
_VISUAL_RENDERERS_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_visual_detail_renderers.py"
)
_PAGE_CONTEXT_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_page_context.py"
)
_LIFECYCLE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "ui"
    / "gicleeframe_view_lifecycle_inventory.py"
)
_PAGE_DRAFT_PATH = _STUDIO_ROOT / "gicleeframe_page_draft.py"
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
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f21_editor_labels() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    shell_text = _SECTION_LIST_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    interaction_text = _SECTION_LIST_INTERACTION_VIEW_PATH.read_text(encoding="utf-8")
    lifecycle_text = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    top_bar_text = _TOP_BAR_VIEW_PATH.read_text(encoding="utf-8")
    structure_text = _STRUCTURE_DRY_RUN_VIEW_PATH.read_text(encoding="utf-8")
    page_context_text = _PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    draft_text = _PAGE_DRAFT_PATH.read_text(encoding="utf-8")
    combined = shell_text + "\n" + interaction_text + "\n" + editor_text
    assert "PAGE_EDITOR_TITLE" in draft_text
    assert "SECTION_EDITOR_TITLE" in draft_text
    assert "_section_list_trigger" in text
    assert "DEFAULT_VARIANT_NAME" in top_bar_text
    assert "WORKING_VARIANT_LABEL" in draft_text
    assert "+ Dodaj wariant" not in text
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert "editor_field_visibility" in editor_text
    assert "editor_context_rows" in editor_text
    assert "_editor_status_dot" in editor_text
    assert "_section_list_scroll" in text
    assert "_section_dropdown_popup" in text
    assert "_toggle_section_list" in combined
    assert "_SECTION_LIST_WIDTH" in shell_text
    assert "SECTION_LIST_DRAG_HINT" in shell_text
    assert "reorder_page_blocks" in combined
    assert "_structure_dry_run_btn" in text
    assert "_build_control_column" in lifecycle_text
    assert "_CONTROL_COL_MINSIZE" in lifecycle_text
    assert "SECTION_LIST_TITLE" in shell_text
    assert "APPLY_RAM_MICROCOPY" in editor_text
    assert "_make_primary_button" in combined
    assert "_build_setting_group_card" in editor_text
    assert "divider_setting_groups" in page_context_text
    assert "_make_empty_state" in structure_text
    assert "_build_command_bar" in top_bar_text
    assert "_build_section_identity_card" in editor_text
    assert "_build_action_dock" in editor_text
    assert "_PREVIEW_SETTINGS_CAPTION" in editor_text
    assert "_pack_field_vertical" in page_context_text
    visual_text = _VISUAL_RENDERERS_PATH.read_text(encoding="utf-8")
    assert "_update_section_preview" in visual_text


def test_view_source_f222_premium_copy() -> None:
    from giclee_app.studio.gicleeframe_page_draft import (
        APPLY_RAM_DRAFT_LABEL,
        APPLY_RAM_MICROCOPY,
    )

    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    top_bar_text = _TOP_BAR_VIEW_PATH.read_text(encoding="utf-8")
    combined = editor_text
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert "APPLY_RAM_MICROCOPY" in editor_text
    assert "Tylko pamięć" in APPLY_RAM_MICROCOPY
    assert "_PREVIEW_SETTINGS_CAPTION" in combined
    assert "Podgląd ustawień" in combined
    assert "RAM-only" in top_bar_text
    assert "Widoczna" in combined
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f223_first_screen_composition() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    shell_text = _SECTION_LIST_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    rendering_text = _SECTION_LIST_RENDERING_VIEW_PATH.read_text(encoding="utf-8")
    visual_text = _VISUAL_RENDERERS_PATH.read_text(encoding="utf-8")
    combined = shell_text + "\n" + rendering_text + "\n" + editor_text
    assert "_ellipsize" in rendering_text or "_ellipsize" in visual_text
    assert "_SECTION_LIST_WIDTH = 320" in shell_text
    assert "_EDITOR_HERO_PREVIEW_HEIGHT" in combined
    assert "_SECTION_ROW_HEIGHT" in combined
    assert "RAM preview" in combined
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert "_build_section_identity_card" in editor_text
    assert "_build_action_dock" in editor_text
    assert "F2.2.3" in editor_text
    assert _self_method_calls(text, "_build_action_dock") == []


def test_view_source_f224_visual_tokens() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    visual_text = _VISUAL_RENDERERS_PATH.read_text(encoding="utf-8")
    lifecycle_text = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    primitives_text = _PRIMITIVES_PATH.read_text(encoding="utf-8")
    assert "F2.2.4" in text
    assert "_GF_PREVIEW_PAPER" in editor_text or "_GF_PREVIEW_PAPER" in visual_text
    assert "_make_gf_card" in lifecycle_text or "_make_gf_card" in editor_text
    assert "_section_kind_copy" in visual_text
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert '_GF_PREVIEW_PAPER = "#2e2e32"' in primitives_text
    assert "write_text" not in text
    assert _self_method_calls(text, "_build_action_dock") == []
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f225_section_workbench() -> None:
    from giclee_app.studio.gicleeframe_page_draft import APPLY_RAM_DRAFT_LABEL

    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    visual_text = _VISUAL_RENDERERS_PATH.read_text(encoding="utf-8")
    combined = editor_text
    assert "F2.2.5" in text
    assert "_section_preview_canvas" in text
    assert "_section_preview_badge" in text
    assert "_build_media_section_preview_structure" in visual_text
    assert "_build_divider_preview_structure" in visual_text
    assert "_build_legacy_preview_structure" in visual_text
    assert "_build_text_preview_structure" in visual_text
    assert "Warstwy sekcji" in combined
    assert "Kliknij, aby edytować" in visual_text
    assert "Workbench sekcji" in combined
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert '"Komponenty"' not in text
    assert "write_text" not in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f226_child_layer_and_color() -> None:
    from giclee_app.studio.gicleeframe_page_draft import APPLY_RAM_DRAFT_LABEL

    text = _VIEW_PATH.read_text(encoding="utf-8")
    editor_text = _EDITOR_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    visual_text = _VISUAL_RENDERERS_PATH.read_text(encoding="utf-8")
    lifecycle_text = _LIFECYCLE_PATH.read_text(encoding="utf-8")
    combined = editor_text
    primitives_text = _PRIMITIVES_PATH.read_text(encoding="utf-8")
    assert "F2.2.6" in text
    assert "_LAYER_NAV_TITLE" in editor_text
    assert "_IMAGE_SOURCE_TITLE" in editor_text
    assert "_layer_nav_frame" in text
    assert "_update_layer_nav" in visual_text
    assert "_parent_row_for_element" in visual_text
    assert "_selected_layer_items" in visual_text
    assert "_build_image_preview_structure" in visual_text
    assert "_image_ref_label" in visual_text
    assert '_GF_PANEL = "#1e1e21"' in primitives_text
    assert '_GF_GOLD = "#b8a878"' in primitives_text
    assert '_GF_PANEL = "#1e1e21"' not in text
    assert "panel_deep" in lifecycle_text or "panel_deep" in editor_text
    assert "Grafika sekcji" in visual_text
    assert "Źródło grafiki" in combined
    assert "Warstwy sekcji" in combined
    assert "Workbench sekcji" in combined
    assert "APPLY_RAM_DRAFT_LABEL" in editor_text
    assert APPLY_RAM_DRAFT_LABEL == "Uaktualnij wariant RAM"
    assert "write_text" not in text
    for pattern in _FORBIDDEN_BUTTON_PATTERNS:
        assert not re.search(pattern, text), f"Forbidden button pattern found: {pattern}"


def test_view_source_f221_setting_groups() -> None:
    from giclee_app.studio.gicleeframe_page_settings import divider_setting_groups

    page_context_text = _PAGE_CONTEXT_PATH.read_text(encoding="utf-8")
    assert "divider_setting_groups" in page_context_text
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


def test_readiness_row_view_source_contract() -> None:
    text = _READINESS_ROW_VIEW_PATH.read_text(encoding="utf-8")
    assert "_pack_readiness_row" in text
    assert "status_color(ok)" in text
    assert 'text="●"' in text
    assert "width=180" in text
    assert 'theme.get_font(11, "bold")' in text


def test_readiness_row_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_READINESS_ROW_VIEW_PATH)
    text = _READINESS_ROW_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in text


def test_top_bar_view_source_contract() -> None:
    text = _TOP_BAR_VIEW_PATH.read_text(encoding="utf-8")
    assert "_build_context_bar" in text
    assert "_build_command_bar" in text
    assert "_schedule_top_bar_actions_late_build" in text
    assert "_BACK_LABEL" in text
    assert "_SHELL_STATUS_CHIP" in text
    assert "RAM-only · bez zapisu" in text
    assert "Warianty RAM" in text
    assert "Inventory i kontrola" in text
    assert "ADD_VARIANT_RAM_LABEL" in text
    assert "REFRESH_INVENTORY_LABEL" in text
    assert "CHECK_STRUCTURE_LABEL" in text
    assert "PANEL_STATUS_UNSAVED" in text
    assert "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS = 200" in text


def test_top_bar_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_TOP_BAR_VIEW_PATH)


def test_ram_variants_view_source_contract() -> None:
    text = _RAM_VARIANTS_VIEW_PATH.read_text(encoding="utf-8")
    assert "GicleeFrameRamVariantMixin" in text
    assert "working_variant_menu_label" in text
    assert "RENAME_VARIANT_LABEL" in text
    assert "PAGE_SOURCE_FILE" in text
    assert "RAM_ONLY_STATUS" in text
    assert "variant_environment_tag" in text
    assert "merge_inventory_with_draft" in text
    for method in (
        "_sync_working_variant_menu",
        "_on_working_variant_selected",
        "_update_top_bar",
        "_add_ram_variant",
        "_duplicate_ram_variant",
        "_rename_ram_variant",
        "_clear_page_draft",
    ):
        assert method in text


def test_ram_variants_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_RAM_VARIANTS_VIEW_PATH)
    text = _RAM_VARIANTS_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "after(",
        "after_idle(",
        "after_cancel(",
    ):
        assert forbidden_text not in text


def test_section_list_shell_view_source_contract() -> None:
    text = _SECTION_LIST_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    assert "GicleeFrameSectionListShellMixin" in text
    assert "_SECTION_PLACEHOLDER = \"— wybierz sekcję —\"" in text
    assert "_SECTION_LIST_WIDTH = 320" in text
    assert "_SECTION_LIST_HEIGHT = 520" in text
    assert "_SECTION_LIST_LOADING_TEXT = \"Ładowanie struktury sekcji…\"" in text
    assert "_GF_SECTION_FIRST_BATCH_SIZE = 6" in text
    assert "_GF_SECTIONS_COLUMN_EARLY_DEFER_MS = 0" in text
    assert "_GF_SECTION_SCROLL_UPGRADE_AFTER_PERCEIVED_DEFER_MS = 40" in text
    assert "_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS = 800" in text
    for method in (
        "_schedule_sections_column_early_lane",
        "_log_section_list_column_ready",
        "_build_sections_column_shell",
        "_create_section_list_scroll_frame",
        "_populate_section_list_static_lane",
        "_try_refresh_static_lane_before_scroll_upgrade",
        "_cancel_section_list_scroll_upgrade_fallback",
        "_ensure_section_list_scroll_upgrade_fallback",
        "_schedule_section_list_scroll_upgrade_after_perceived",
        "_schedule_section_list_scroll_upgrade",
        "_build_sections_column_extras",
        "_build_sections_column",
    ):
        assert method in text


def test_section_list_shell_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_SECTION_LIST_SHELL_VIEW_PATH)
    text = _SECTION_LIST_SHELL_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "shopify",
        "deploy",
        "subprocess",
        "requests.get",
        "requests.post",
    ):
        assert forbidden_text not in text.lower()


def test_section_list_rendering_view_source_contract() -> None:
    text = _SECTION_LIST_RENDERING_VIEW_PATH.read_text(encoding="utf-8")
    assert "GicleeFrameSectionListRenderingMixin" in text
    assert "_SECTION_ROW_GRIP = \"⋮\"" in text
    assert "_SECTION_ROW_HEIGHT = 64" in text
    assert "_GF_SECTION_BATCH_SIZE = 8" in text
    assert "_GF_SECTION_BATCH_DELAY_MS = 0" in text
    for method in (
        "_render_section_list",
        "_render_full_list_chunk",
        "_render_section_list_incremental",
        "_render_section_list_batch",
        "_schedule_section_list_batch_continuation",
        "_create_section_list_row",
        "_build_section_row",
        "_render_section_menu",
    ):
        assert method in text


def test_section_list_rendering_view_source_no_write_or_network() -> None:
    _assert_no_writes_in_source(_SECTION_LIST_RENDERING_VIEW_PATH)
    text = _SECTION_LIST_RENDERING_VIEW_PATH.read_text(encoding="utf-8")
    for forbidden_text in (
        "shopify",
        "deploy",
        "subprocess",
        "requests.get",
        "requests.post",
    ):
        assert forbidden_text not in text.lower()
