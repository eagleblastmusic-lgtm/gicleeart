"""Theme Page Editor imports its service dependencies directly."""

from __future__ import annotations

import ast
from pathlib import Path

from Komponenty._shared.theme_page_editor import bootstrap, gui_shell
from Komponenty._shared.theme_page_editor.service_base import shopify_ref_label

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "Komponenty" / "_shared" / "theme_page_editor" / "bootstrap.py"
GUI_SHELL = ROOT / "Komponenty" / "_shared" / "theme_page_editor" / "gui_shell.py"


def test_gui_shell_owns_direct_shopify_ref_label_import() -> None:
    assert gui_shell.shopify_ref_label is shopify_ref_label

    tree = ast.parse(GUI_SHELL.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "service_base"
        for alias in node.names
    }
    assert "shopify_ref_label" in imported


def test_bootstrap_contains_no_gui_shell_monkey_patch() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "gui_shell.shopify_ref_label" not in source
    assert "shopify_ref_label =" not in source
    assert bootstrap.gui_shell is gui_shell


def test_bootstrap_stays_a_thin_editor_composition_boundary() -> None:
    tree = ast.parse(BOOTSTRAP.read_text(encoding="utf-8"))
    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
    ]
    assert assignments == []
