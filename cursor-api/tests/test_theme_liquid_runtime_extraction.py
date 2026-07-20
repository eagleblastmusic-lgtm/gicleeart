"""Composition contract for the extracted post-layout theme runtime."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEME = ROOT / "layout" / "theme.liquid"
SNIPPETS = ROOT / "snippets"
PARENT = SNIPPETS / "giclee-theme-runtime.liquid"
THEME_RENDER_MARKER = "{% render 'giclee-theme-runtime' %}\n"
EXPECTED_RUNTIME_SHA256 = "52648125da4c7c0ea6dc773032b77acc7fbd821225193c4bdf91fa7c1efe2d69"
CHILDREN = (
    ("general", 58, "bff4c3288415986ecd509f5687f64f4778f3f6e702072f8831409c56fccdcc1c"),
    ("navigation", 485, "2821ea0013807794ae8442aa56d97fae1d2c4470edf548d186ffb7376280d404"),
    ("photo-mockup", 934, "23d3452b47a1a13a2973baff538ba32d6b5d3cbf36682b286eedaab1d765a7b1"),
    ("footer", 49, "8a33ce6ddca2be2cd4f6b721c2e4990f7efa417753b7dc5a5a7b69ec5ff70b7e"),
)


def _compose_runtime() -> str:
    composed = PARENT.read_text(encoding="utf-8")
    for name, _line_count, _digest in CHILDREN:
        marker = "{% render 'giclee-theme-runtime-" + name + "' %}\n"
        block = (SNIPPETS / f"giclee-theme-runtime-{name}.liquid").read_text(encoding="utf-8")
        assert composed.count(marker) == 1
        composed = composed.replace(marker, block, 1)
    return composed


def test_theme_renders_runtime_parent_once_before_body_close() -> None:
    theme = THEME.read_text(encoding="utf-8")
    assert theme.count(THEME_RENDER_MARKER) == 1
    assert theme.index(THEME_RENDER_MARKER) < theme.index("</body>")


def test_runtime_parent_declares_domain_order_only() -> None:
    parent = PARENT.read_text(encoding="utf-8")
    expected = "".join(
        "{% render 'giclee-theme-runtime-" + name + "' %}\n"
        for name, *_ in CHILDREN
    )
    assert parent == expected
    assert len(parent.splitlines()) == 4


def test_runtime_children_preserve_exact_mechanical_blocks() -> None:
    for name, line_count, digest in CHILDREN:
        block = (SNIPPETS / f"giclee-theme-runtime-{name}.liquid").read_text(encoding="utf-8")
        assert len(block.splitlines()) == line_count
        assert sha256(block.encode("utf-8")).hexdigest() == digest


def test_runtime_domains_keep_expected_ownership_boundaries() -> None:
    general = (SNIPPETS / "giclee-theme-runtime-general.liquid").read_text(encoding="utf-8")
    navigation = (SNIPPETS / "giclee-theme-runtime-navigation.liquid").read_text(encoding="utf-8")
    photo = (SNIPPETS / "giclee-theme-runtime-photo-mockup.liquid").read_text(encoding="utf-8")
    footer = (SNIPPETS / "giclee-theme-runtime-footer.liquid").read_text(encoding="utf-8")
    assert "giclee-catalog-panel" in general
    assert "MALE_ORG.webp" in navigation
    assert "pm-cart-product-data" in photo
    assert "assign pm_cart_product = product" in photo
    assert "giclee-site-notice" in footer
    assert "enhanceFaqA11y" in footer


def test_runtime_children_recompose_original_region_and_theme() -> None:
    runtime = _compose_runtime()
    assert len(runtime.splitlines()) == 1526
    assert sha256(runtime.encode("utf-8")).hexdigest() == EXPECTED_RUNTIME_SHA256

    theme = THEME.read_text(encoding="utf-8")
    before, after = theme.split(THEME_RENDER_MARKER, 1)
    reconstructed = theme.replace(THEME_RENDER_MARKER, runtime, 1)

    assert THEME_RENDER_MARKER not in reconstructed
    assert reconstructed == before + runtime + after
    assert len(reconstructed.splitlines()) == (
        len(theme.splitlines()) + len(runtime.splitlines()) - 1
    )
