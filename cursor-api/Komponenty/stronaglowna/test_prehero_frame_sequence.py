from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "assets" / "giclee-home-prehero-frames.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"
CSS = ROOT / "assets" / "giclee-home-prehero-scrub.css"
MANIFEST = ROOT / "snippets" / "giclee-home-prehero-frame-manifest.liquid"
SPRITES = tuple(sorted((ROOT / "assets").glob("giclee-prehero-sprite-*.jpg")))


def test_frame_renderer_uses_jpg_sprites_with_bounded_cache() -> None:
    source = RENDERER.read_text(encoding="utf-8")

    assert "giclee-prehero-scrub__canvas" in source
    assert "getContext('2d'" in source
    assert "desynchronized: true" in source
    assert "framesPerSprite" in source
    assert "spriteColumns" in source
    assert "function evict()" in source
    assert "requestIdleCallback" in source
    assert "context.drawImage(" in source
    assert "mode: 'jpg-sprite-canvas'" in source
    assert "GICLEE_PREHERO_FRAME_STATUS" in source


def test_frame_mode_is_used_for_every_scroll_engine_without_mp4_seeks() -> None:
    source = SCRUB.read_text(encoding="utf-8")

    assert "frameRendererAvailable()" in source
    assert "renderMode: 'jpg-sprite-canvas'" in source
    assert "if (useFrameSequence) frameController.setProgress(progress);" in source
    assert "if (scrubState && scrubState.usesFrameSequence)" in source
    assert "parts.video.preload = 'none';" in source
    assert "video.currentTime" not in source
    assert "giclee-lenis-performance" not in source


def test_frame_canvas_visibility_keeps_existing_css_contract() -> None:
    styles = CSS.read_text(encoding="utf-8")

    assert ".giclee-prehero-scrub__canvas" in styles
    assert "data-frame-sequence-ready='true'" in styles
    assert "data-render-mode='webp-frames'" in styles
    assert "display: none;" in styles


def test_manifest_and_sprite_assets_are_complete() -> None:
    source = MANIFEST.read_text(encoding="utf-8")

    assert "window.GICLEE_PREHERO_FRAME_SEQUENCE" in source
    assert "format: 'jpg-sprites'" in source
    assert "frameCount: 117" in source
    assert "sourceFps: 24" in source
    assert "framesPerSprite: 8" in source
    assert "spriteColumns: 4" in source
    assert source.count("giclee-prehero-sprite-") == 15
    assert len(SPRITES) == 15
    assert all(path.stat().st_size > 0 for path in SPRITES)
    assert all(path.read_bytes()[:2] == b"\xff\xd8" for path in SPRITES)
    assert not tuple((ROOT / "assets").glob("giclee-prehero-frame-*.webp"))
