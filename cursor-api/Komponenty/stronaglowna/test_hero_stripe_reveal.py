"""Kontrakt 3-pasowego wjazdu Hero po prehero (stripe-reveal)."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
JS = ROOT / "assets" / "giclee-home-hero-stripe-reveal.js"
CSS = ROOT / "assets" / "giclee-home-hero-stripe-reveal.css"
SNIPPET = ROOT / "snippets" / "giclee-home-stack-critical.liquid"
GENERATOR = (
    ROOT / "cursor-api" / "Komponenty" / "stronaglowna" / "prehero_full_generator.py"
)


def test_hero_stripe_reveal_assets_exist_and_are_wired() -> None:
    assert JS.is_file()
    assert CSS.is_file()
    snippet = SNIPPET.read_text(encoding="utf-8")
    generator = GENERATOR.read_text(encoding="utf-8")

    assert "giclee-home-hero-stripe-reveal.css" in snippet
    assert "giclee-home-hero-stripe-reveal.js" in snippet
    assert snippet.index("giclee-home-prehero-reveal.js") < snippet.index(
        "giclee-home-hero-stripe-reveal.js"
    )
    assert "giclee-home-hero-stripe-reveal.css" in generator
    assert "giclee-home-hero-stripe-reveal.js" in generator


def test_hero_stripe_reveal_masks_live_collage_not_cover_layer() -> None:
    source = JS.read_text(encoding="utf-8")
    styles = CSS.read_text(encoding="utf-8")

    assert "var OFFSETS = [0, 0.13, 0.26];" in source
    assert "var LAG = [0.085, 0.065, 0.048];" in source
    assert "var SECTION_LAG = 0.07;" in source
    assert "function tickSharedMotion()" in source
    assert "updateTargetsFromWipe(complete ? 1 : smoothedProgress)" in source
    assert "is-hero-rise-lagging" in source
    assert "--giclee-hero-rise-lag-y" in source
    assert "data-hero-rise-progress" in source
    assert "is-hero-stripe-masked" in source
    assert "function easeOutCubic(t)" in source
    assert "GICLEE_HERO_STRIPE_REVEAL_STATUS" in source
    assert "giclee-hero-stripe-reveal-host" not in source
    assert "mask-image:" in styles
    assert "--giclee-hero-stripe-h0" in styles
    assert "--giclee-hero-rise-lag-y" in styles
    assert "top: var(--giclee-hero-rise-lag-y, 0px) !important;" in styles
    assert "calc(100% / 3 + 2px)" in styles
    assert "0% 100%, 50% 100%, 100% 100%" in styles
    assert "mask-composite: add" in styles
