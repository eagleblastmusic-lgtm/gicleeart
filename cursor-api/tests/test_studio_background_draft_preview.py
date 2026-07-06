"""Testy koncepcyjnego podglądu draftu — Studio Preview (F5.3)."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_preview import (
    PREVIEW_BADGE,
    PREVIEW_DISCLAIMER,
    PREVIEW_EMPTY_COPY,
    format_preview_body,
    placeholder_label_for_kind,
    preview_enabled_for_folder,
)
from giclee_app.studio.background_draft_state import BackgroundDraftState

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_draft_preview.py"
)
_PANEL_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"


def test_empty_draft_preview_copy() -> None:
    draft = BackgroundDraftState()
    assert format_preview_body(draft) == PREVIEW_EMPTY_COPY


def test_draft_preview_contains_zone_type_and_not_applied() -> None:
    draft = BackgroundDraftState(zone_field_id="ga_background", asset_kind="image")
    body = format_preview_body(draft)
    assert PREVIEW_BADGE in body
    assert "niezastosowany" in body
    assert "ga_background" in body
    assert "obraz" in body
    assert "placeholder obrazu" in body
    assert PREVIEW_DISCLAIMER in body
    assert "shopify://" not in body
    assert "http" not in body.lower()


def test_draft_preview_shows_selected_asset_label() -> None:
    draft = BackgroundDraftState(zone_field_id="ga_background", asset_kind="image")
    draft.set_selected_asset("img:0")
    body = format_preview_body(draft, selected_label="hero.webp")
    assert "hero.webp" in body
    assert "placeholder obrazu" not in body
    assert "shopify://" not in body


def test_placeholder_labels_per_kind() -> None:
    assert placeholder_label_for_kind("image") == "placeholder obrazu"
    assert placeholder_label_for_kind("video") == "placeholder wideo"
    assert placeholder_label_for_kind("video_collage") == "placeholder kolażu"


def test_preview_enabled_only_stronaglowna() -> None:
    assert preview_enabled_for_folder("stronaglowna")
    assert not preview_enabled_for_folder("tldobio")


def test_no_komponenty_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_no_write_or_file_apis_in_preview_module() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "filedialog" not in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "CTkImage" not in text
    assert "shopify" not in text.lower()


def test_panel_no_apply_or_file_preview() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "Zastosuj" not in text
    assert "CTkImage" not in text
    assert "filedialog" not in text
    assert "_render_preview_section" in text
    assert "background_draft_preview" in text
