"""Testy GF-M1 — czyste kontrakty widoku GICLÉE FRAME."""

from __future__ import annotations

import ast
import inspect
import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.gicleeframe_page_draft import MergedPageElement
from giclee_app.ui import gicleeframe_view as view
from giclee_app.ui import gicleeframe_view_models as models

_MODELS_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view_models.py"
_VIEW_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "gicleeframe_view.py"

_PAGE_CONTEXT_ROW_SPEC_FIELDS = (
    "kind",
    "label",
    "value",
    "group_title",
    "slot",
    "field",
    "key",
    "setting_id",
    "group_id",
    "group_settings",
)

_SECTION_VISUAL_CACHE_ENTRY_FIELDS = (
    "element_type",
    "status",
    "has_draft_patch",
    "title",
    "text",
    "alt",
    "image_ref",
    "notes",
    "visible",
    "subtitle_text",
    "page_context_summary",
    "fields_title",
    "fields_text",
    "fields_alt",
    "fields_image_ref",
    "fields_notes",
    "fields_visible",
    "fields_children",
    "fields_page_context",
    "media_details_built",
    "preview_key",
    "layer_nav_visible",
    "layer_nav_titles",
    "details_cache_preview",
    "details_cache_page_context",
    "details_cache_layer_nav",
    "details_cache_children",
)

_FORBIDDEN_MODELS_TOKENS = (
    "tkinter",
    "customtkinter",
    "Komponenty",
    "open(",
    "write_text",
    "requests",
    "subprocess",
)


def _merged(element_id: str, element_type: str) -> MergedPageElement:
    return MergedPageElement(
        element_id=element_id,
        section_key="section-a",
        element_type=element_type,
        group="body",
        order=0,
        label="Label",
        title="Title",
        text="",
        image_ref="",
        alt="",
        notes="",
        editable=True,
        source="inventory",
        status="ok",
        has_draft_patch=False,
        visible=True,
    )


def test_models_dataclasses_importable() -> None:
    assert models.PageContextRowSpec is not None
    assert models.SectionVisualCacheEntry is not None


def test_view_reexports_dataclasses() -> None:
    assert view.PageContextRowSpec is not None
    assert view.SectionVisualCacheEntry is not None


def test_view_and_models_share_same_dataclass_objects() -> None:
    assert view.SectionVisualCacheEntry is models.SectionVisualCacheEntry
    assert view.PageContextRowSpec is models.PageContextRowSpec


def test_page_context_row_spec_fields_unchanged() -> None:
    names = tuple(field.name for field in fields(models.PageContextRowSpec))
    assert names == _PAGE_CONTEXT_ROW_SPEC_FIELDS
    assert len(names) == 10


def test_section_visual_cache_entry_fields_unchanged() -> None:
    names = tuple(field.name for field in fields(models.SectionVisualCacheEntry))
    assert names == _SECTION_VISUAL_CACHE_ENTRY_FIELDS
    assert len(names) == 27


def test_ellipsize_default_matches_view_constant() -> None:
    default = inspect.signature(models._ellipsize).parameters["max_chars"].default
    assert default == 42


def test_ellipsize_empty_text() -> None:
    assert models._ellipsize("") == ""


def test_ellipsize_normalizes_whitespace() -> None:
    assert models._ellipsize("  foo   bar  ") == "foo bar"


def test_ellipsize_shorter_than_limit() -> None:
    assert models._ellipsize("short", max_chars=10) == "short"


def test_ellipsize_equal_to_limit() -> None:
    text = "a" * 10
    assert models._ellipsize(text, max_chars=10) == text


def test_ellipsize_longer_than_limit() -> None:
    text = "a" * 12
    assert models._ellipsize(text, max_chars=10) == ("a" * 9) + "…"


def test_ellipsize_uses_unicode_ellipsis() -> None:
    result = models._ellipsize("abcdefghijklmnop", max_chars=10)
    assert result.endswith("…")
    assert not result.endswith("...")


def test_section_kind_copy_divider() -> None:
    items = [_merged("elem-1", "divider")]
    assert models._section_kind_copy("elem-1", items) == "separator"


def test_section_kind_copy_section_legacy() -> None:
    items = [_merged("elem-1", "section_legacy")]
    assert models._section_kind_copy("elem-1", items) == "legacy"


def test_section_kind_copy_media_section() -> None:
    items = [_merged("elem-1", "media_section")]
    assert models._section_kind_copy("elem-1", items) == "sekcja edytorska"


def test_section_kind_copy_other_type() -> None:
    items = [_merged("elem-1", "text")]
    assert models._section_kind_copy("elem-1", items) == "sekcja"


def test_section_kind_copy_missing_element() -> None:
    items = [_merged("elem-1", "divider")]
    assert models._section_kind_copy("missing", items) == ""


def test_models_source_guardrails() -> None:
    text = _MODELS_PATH.read_text(encoding="utf-8")
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
        assert imp not in {"tkinter", "customtkinter", "requests", "subprocess"}
    for token in _FORBIDDEN_MODELS_TOKENS:
        assert token not in text


def test_view_imports_models_and_does_not_redefine_dataclasses() -> None:
    text = _VIEW_PATH.read_text(encoding="utf-8")
    assert "gicleeframe_view_models" in text
    assert "class PageContextRowSpec" not in text
    assert "class SectionVisualCacheEntry" not in text
    assert "@dataclass" not in text
