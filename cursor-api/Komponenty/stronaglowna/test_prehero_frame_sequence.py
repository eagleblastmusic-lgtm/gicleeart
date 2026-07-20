from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "assets" / "giclee-home-prehero-frames.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"
CSS = ROOT / "assets" / "giclee-home-prehero-scrub.css"
MANIFEST = ROOT / "snippets" / "giclee-home-prehero-frame-manifest.liquid"
BUILDER = ROOT / "scripts" / "build_prehero_webp_sequence.py"


def test_frame_renderer_uses_canvas_with_bounded_cache() -> None:
    source = RENDERER.read_text(encoding="utf-8")

    assert "giclee-prehero-scrub__canvas" in source
    assert "getContext('2d'" in source
    assert "desynchronized: true" in source
    assert "var maxCache" in source
    assert "var preloadRadius" in source
    assert "function evict()" in source
    assert "requestIdleCallback" in source
    assert "drawImage" in source
    assert "GICLEE_PREHERO_FRAME_STATUS" in source


def test_lenis_frame_mode_bypasses_mp4_source_and_seeks() -> None:
    source = SCRUB.read_text(encoding="utf-8")

    assert "frameRendererAvailable()" in source
    assert "renderMode: useFrameSequence ? 'webp-canvas' : 'mp4-seek'" in source
    assert "if (useFrameSequence) frameController.setProgress(progress);" in source
    assert "if (scrubState && scrubState.usesFrameSequence)" in source
    assert "parts.video.preload = 'none';" in source
    assert "if (useFrameSequence) return;" in source


def test_frame_canvas_visibility_is_scoped_to_frame_mode() -> None:
    styles = CSS.read_text(encoding="utf-8")

    assert ".giclee-prehero-scrub__canvas" in styles
    assert "data-frame-sequence-ready='true'" in styles
    assert "data-render-mode='webp-frames'" in styles
    assert "display: none;" in styles


def test_manifest_has_safe_disabled_fallback() -> None:
    source = MANIFEST.read_text(encoding="utf-8")

    assert "window.GICLEE_PREHERO_FRAME_SEQUENCE" in source
    assert "enabled: false" in source or "enabled: true" in source
    assert "urls:" in source


def test_builder_generates_flat_shopify_assets_and_liquid_manifest() -> None:
    source = BUILDER.read_text(encoding="utf-8")

    assert 'FRAME_PREFIX = "giclee-prehero-frame-"' in source
    assert "libwebp" in source
    assert "asset_url | json" in source
    assert "budget-mb" in source
    assert "TemporaryDirectory" in source
    assert "MANIFEST_PATH.write_text" in source
