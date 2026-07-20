from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRUB_PATH = ROOT / "assets" / "giclee-home-prehero-scrub.js"


def test_prehero_scrub_maps_scroll_directly_to_canvas_frames() -> None:
    source = SCRUB_PATH.read_text(encoding="utf-8")

    assert "frameController.setProgress(progress)" in source
    assert "renderMode: 'jpg-sprite-canvas'" in source
    assert "video.currentTime" not in source
    assert "video.addEventListener('seeked'" not in source
    assert "SEEK_INTERVAL_MS" not in source


def test_prehero_scrub_does_not_busy_loop_or_repeat_layout_reads() -> None:
    source = SCRUB_PATH.read_text(encoding="utf-8")

    assert "currentTime += (targetTime - currentTime)" not in source
    assert source.count("root.getBoundingClientRect()") == 1
    assert "window.addEventListener('scroll', updateProgressFromScroll" in source
    assert "requestAnimationFrame(updateProgressFromScroll)" not in source
