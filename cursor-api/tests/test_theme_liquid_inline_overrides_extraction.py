"""Mechanical extraction contract for the large inline theme CSS block."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / "layout" / "theme.liquid"
SNIPPET = ROOT / "snippets" / "giclee-theme-inline-overrides.liquid"
RENDER_MARKER = "  {% render 'giclee-theme-inline-overrides' %}"
EXPECTED_SNIPPET_SHA256 = "c50a2cc71a70084bec5d062fc954e1b0b47adacd120fbb48b304a6cc7605c69a"


def test_theme_renders_extracted_inline_overrides_once() -> None:
    theme = THEME.read_text(encoding="utf-8")
    assert theme.count(RENDER_MARKER) == 1
    assert theme.index(RENDER_MARKER) < theme.index("{% render 'skip-to-content-link'")


def test_extracted_snippet_preserves_the_mechanical_source_block() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8")
    assert len(snippet.splitlines()) == 1277
    assert sha256(snippet.encode("utf-8")).hexdigest() == EXPECTED_SNIPPET_SHA256
    assert snippet.startswith("  <style>\n    #page-transition {")
    assert snippet.endswith("  </style>")
    assert snippet.count("<style>") == 1
    assert snippet.count("</style>") == 1


def test_liquid_conditions_remain_inside_the_extracted_snippet() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8")
    required = (
        "{% if template.suffix == 'faq' %}",
        "{% if request.page_type == 'page' %}",
        "{% if template.suffix == 'contact' %}",
        "{% if template.suffix == 'fotografia-obraz' or template.suffix == 'szablon-wlasna-fotografia' %}",
        "{% if template.suffix == 'giclee-frame' %}",
    )
    for token in required:
        assert token in snippet


def test_reinserting_snippet_restores_original_layout_line_count() -> None:
    theme = THEME.read_text(encoding="utf-8")
    snippet = SNIPPET.read_text(encoding="utf-8")
    reconstructed = theme.replace(RENDER_MARKER, snippet, 1)
    assert len(theme.splitlines()) == 1878
    assert len(reconstructed.splitlines()) == 3154
