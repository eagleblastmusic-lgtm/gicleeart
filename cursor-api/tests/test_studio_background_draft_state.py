"""Testy lokalnego draftu tła — Studio Preview (F5.2)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_state import (
    DRAFT_EMPTY_COPY,
    BackgroundDraftState,
    draft_enabled_for_folder,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "background_draft_state.py"
)
_PANEL_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"


def test_empty_draft_summary() -> None:
    draft = BackgroundDraftState()
    assert draft.is_empty()
    assert draft.format_summary() == DRAFT_EMPTY_COPY


def test_draft_zone_and_kind_summary() -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState()
    draft.set_zone(zone.field_id)
    draft.set_kind("video")
    assert not draft.is_empty()
    summary = draft.format_summary()
    assert "Draft lokalny:" in summary
    assert zone.field_id in summary
    assert zone.label in summary
    assert "wideo" in summary
    assert "niezapisany" in summary
    assert "shopify://" not in summary
    assert "http" not in summary.lower()
    assert "/" not in summary.split("→")[0] or zone.field_id in summary


def test_clear_resets_draft() -> None:
    draft = BackgroundDraftState(zone_field_id="ga_background", asset_kind="image")
    draft.clear()
    assert draft.is_empty()
    assert draft.format_summary() == DRAFT_EMPTY_COPY


def test_unknown_zone_defensive_display() -> None:
    draft = BackgroundDraftState(zone_field_id="unknown_zone", asset_kind="image")
    summary = draft.format_summary()
    assert "nieznana strefa (unknown_zone)" in summary
    assert "obraz" in summary
    assert "niezapisany" in summary


def test_draft_enabled_only_stronaglowna() -> None:
    assert draft_enabled_for_folder("stronaglowna")
    assert not draft_enabled_for_folder("tldobio")
    assert not draft_enabled_for_folder("")


def test_no_komponenty_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_no_write_or_file_apis_in_draft_module() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "filedialog" not in text
    assert "glob(" not in text
    assert "rglob(" not in text


def test_panel_ast_guardrails_no_file_io() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "filedialog" not in text
    assert "askopenfilename" not in text
    assert "asksaveasfilename" not in text
    assert "write_text" not in text
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")
