"""Mechanical extraction contract for post-layout inline theme runtime."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / "layout" / "theme.liquid"
SNIPPET = ROOT / "snippets" / "giclee-theme-runtime.liquid"
RENDER_MARKER = "{% render 'giclee-theme-runtime' %}\n"
EXPECTED_SNIPPET_SHA256 = "52648125da4c7c0ea6dc773032b77acc7fbd821225193c4bdf91fa7c1efe2d69"
EXPECTED_ORIGINAL_THEME_SHA256 = "dc831ecc3eb615144af03b40213e3a2b3700bdd45e9cb058742a22493f9bbaec"


def test_theme_renders_extracted_runtime_once_before_body_close() -> None:
    theme = THEME.read_text(encoding="utf-8")
    assert theme.count(RENDER_MARKER) == 1
    assert theme.index(RENDER_MARKER) < theme.index("</body>")
    assert len(theme.splitlines()) == 353


def test_runtime_snippet_preserves_mechanical_source_region() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8")
    assert len(snippet.splitlines()) == 1526
    assert sha256(snippet.encode("utf-8")).hexdigest() == EXPECTED_SNIPPET_SHA256
    assert snippet.startswith("<script>\n  const observer = new IntersectionObserver")
    assert snippet.endswith("  {% endif %}\n")


def test_runtime_snippet_keeps_liquid_and_execution_boundaries() -> None:
    snippet = SNIPPET.read_text(encoding="utf-8")
    required = (
        "{%- render 'giclee-catalog-panel', part: 'script' -%}",
        "{{ 'MALE_ORG.webp' | asset_url | json }}",
        "{% if template.suffix == 'fotografia-obraz' or template.suffix == 'szablon-wlasna-fotografia' %}",
        "assign pm_cart_product = product",
        "{% render 'giclee-site-notice' %}",
        "{% if template.suffix == 'faq' %}",
    )
    for token in required:
        assert token in snippet
    assert snippet.count("<script") == 12
    assert snippet.count("</script>") == 12


def test_reinserting_runtime_restores_original_theme_byte_for_byte() -> None:
    theme = THEME.read_text(encoding="utf-8")
    snippet = SNIPPET.read_text(encoding="utf-8")
    reconstructed = theme.replace(RENDER_MARKER, snippet, 1)
    assert len(reconstructed.splitlines()) == 1878
    assert sha256(reconstructed.encode("utf-8")).hexdigest() == EXPECTED_ORIGINAL_THEME_SHA256
