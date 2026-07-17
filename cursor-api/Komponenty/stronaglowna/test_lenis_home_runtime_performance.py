from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHROME = ROOT / "assets" / "giclee-home-prehero-chrome.js"
REVEAL = ROOT / "assets" / "giclee-home-prehero-reveal.js"
CURTAIN = ROOT / "assets" / "giclee-home-hero-horizontal-curtain.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"


def test_lenis_uses_direct_progress_in_secondary_scroll_animations() -> None:
    chrome = CHROME.read_text(encoding="utf-8")
    reveal = REVEAL.read_text(encoding="utf-8")
    curtain = CURTAIN.read_text(encoding="utf-8")

    assert "function lenisPerformanceActive()" in chrome
    assert "function lenisPerformanceActive()" in reveal
    assert "function lenisActive()" in curtain

    for source in (chrome, reveal, curtain):
        assert "currentProgress = targetProgress;" in source
        assert "directLenisProgress:" in source


def test_scroll_geometry_is_cached_outside_hot_scroll_handlers() -> None:
    chrome = CHROME.read_text(encoding="utf-8")
    reveal = REVEAL.read_text(encoding="utf-8")
    curtain = CURTAIN.read_text(encoding="utf-8")

    assert "rootDocumentTop" in chrome
    assert "scrubDocumentTop" in reveal
    assert "runwayDocumentTop" in curtain
    assert "scrollY() - scrubDocumentTop" in reveal
    assert "scrollY() - runwayDocumentTop + viewport" in curtain


def test_lenis_adaptively_reduces_video_seek_pressure() -> None:
    source = SCRUB.read_text(encoding="utf-8")

    assert "var LENIS_MAX_SEEK_FPS = 12;" in source
    assert "function activeSeekFps()" in source
    assert "Math.min(SEEK_FPS, LENIS_MAX_SEEK_FPS)" in source
    assert "activeSeekIntervalMs()" in source
    assert "activeSeekEpsilon()" in source
    assert "lenisAdaptiveSeeking:" in source
