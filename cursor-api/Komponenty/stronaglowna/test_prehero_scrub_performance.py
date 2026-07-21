from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRUB_PATH = ROOT / "assets" / "giclee-home-prehero-scrub.js"


def test_prehero_scrub_rate_limits_media_seeks() -> None:
    source = SCRUB_PATH.read_text(encoding="utf-8")

    assert "var SEEK_FPS = configNumber('scrubSeekFps', 60, 12, 60);" in source
    assert "var SEEK_EPSILON = 0.004;" in source
    assert "var FRAME_END_EPSILON = 0.0005;" in source
    assert "var SEEK_INTERVAL_MS = 1000 / SEEK_FPS;" in source
    assert "video.addEventListener('seeked', onSeeked);" in source
    assert "if (!duration || reducedMotion || video.seeking || rafId || retryTimer) return;" in source


def test_prehero_scrub_does_not_busy_loop_while_seeking() -> None:
    source = SCRUB_PATH.read_text(encoding="utf-8")

    assert "currentTime += (targetTime - currentTime)" not in source
    assert "video.seeking ||\n        Math.abs(video.currentTime" not in source
    assert source.count("root.getBoundingClientRect()") == 1
    assert "window.addEventListener('scroll', updateProgressFromScroll" in source

def test_prehero_mp4_maps_the_complete_290_frame_timeline() -> None:
    source = SCRUB_PATH.read_text(encoding="utf-8")

    assert "Math.round(duration * SEEK_FPS)" in source
    assert "Math.round(progress * maxMp4Frame())" in source
    assert "frameIndex / SEEK_FPS" in source
    assert "duration - FRAME_END_EPSILON" in source
    assert "sourceFrameCount:" in source
    assert "uniqueRenderedFrameCount:" in source
    assert "allFramesRendered:" in source
    assert "duration - 0.033" not in source
