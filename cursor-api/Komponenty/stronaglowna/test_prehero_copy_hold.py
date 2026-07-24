from __future__ import annotations

from pathlib import Path


ASSET_PATH = (
    Path(__file__).resolve().parents[3] / "assets" / "giclee-home-prehero-reveal.js"
)


def test_prehero_copy_holds_until_late_reveal_progress() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")

    assert "heroRiseStart + Math.max(1, heroRiseTravel * 0.22)" in source
    assert "rangeProgress(eased, WORD_REVEAL_START, 1)" in source
    assert "rangeProgress(eased, 0.76, 0.95)" not in source


def test_prehero_portal_uses_ease_out_opening() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")

    assert "function easeOutQuad(value)" in source
    assert "var eased = easeOutQuad(currentProgress);" in source
    assert "var eased = smoothstep(currentProgress);" not in source
    assert "var eased = easeOutCubic(currentProgress);" not in source


def test_prehero_blurs_with_portal_curtain_scroll() -> None:
    root = Path(__file__).resolve().parents[3]
    source = ASSET_PATH.read_text(encoding="utf-8")
    styles = (root / "assets" / "giclee-home-prehero-scrub.css").read_text(encoding="utf-8")

    assert "function applyPreheroCurtainBlur(eased)" in source
    assert "PREHERO_CURTAIN_BLUR_PX" in source
    assert "applyPreheroCurtainBlur(eased);" in source
    assert "--giclee-prehero-media-blur" in source
    assert "--giclee-prehero-media-blur" in styles
    assert "filter: blur(var(--giclee-prehero-media-blur, 0px));" in styles


def test_prehero_copy_reveals_words_on_scroll() -> None:
    source = ASSET_PATH.read_text(encoding="utf-8")

    assert "giclee-prehero-reveal__copy-word" in source
    assert "WORD_STAGGER = 0.08" in source
    assert "WORD_DURATION = 0.4" in source
    assert "WORD_REVEAL_START = 0.52" in source
    assert "WORD_PORTAL_SHARE = 0.4" in source
    assert "WORD_REVEAL_COMPLETE = 0.5" in source
    assert "WORD_DIM_OPACITY = 0.18" in source
    assert "--giclee-prehero-copy-word-opacity" in source
    assert "COPY_RISE_FROM = 0.75" in source
    assert "COPY_APPEAR_AT = 0.08" in source
    assert "COPY_FADE_END = 0.88" in source
    assert "COPY_DEPTH_Z_PX" in source
    assert "COPY_DEPTH_SCALE_TO" in source
    assert "DEPTH_STAGGER = WORD_STAGGER" in source
    assert "DEPTH_MOTION_SHARE" in source
    assert "COPY_DEPTH_OPACITY_TO = 0.12" in source
    assert "COPY_DEPTH_OPACITY_TO * (1 - trail)" in source
    assert "--giclee-prehero-copy-word-z" in source
    assert "--giclee-prehero-copy-word-scale" in source
    assert "wordTravelEnd" in source
    assert "depthTimeline" in source
    assert "copyHoldVh', 200" in source
    assert "--giclee-prehero-copy-y" in source
    assert "(eased - COPY_APPEAR_AT) / Math.max(0.0001, 1 - COPY_APPEAR_AT)" in source


def test_prehero_portal_gallery_video_fades_in_behind_copy() -> None:
    root = Path(__file__).resolve().parents[3]
    source = ASSET_PATH.read_text(encoding="utf-8")
    styles = (root / "assets" / "giclee-home-prehero-reveal.css").read_text(encoding="utf-8")
    snippet = (root / "snippets" / "giclee-home-stack-critical.liquid").read_text(
        encoding="utf-8"
    )
    portal_mp4 = root / "assets" / "giclee-home-prehero-portal.mp4"

    assert portal_mp4.is_file()
    assert portal_mp4.stat().st_size > 100_000
    assert "GICLEE_PREHERO_PORTAL_VIDEO_URL" in snippet
    assert "giclee-home-prehero-portal.mp4" in snippet
    assert "giclee-prehero-reveal__portal-video" in source
    assert "function applyPortalVideo(eased)" in source
    assert "PORTAL_VIDEO_FADE_HOLD_FRACTION" in source
    assert "PORTAL_VIDEO_FADE_OUT_AT = 5" in source
    assert "function portalVideoTimeFade(timeSeconds)" in source
    assert "var portalOpen = eased >= 0.999;" in source
    assert "applyPortalVideo(eased);" in source
    assert "portalRevealEndScroll()" in source
    assert "--giclee-prehero-portal-video-opacity" in styles
    assert ".giclee-prehero-reveal__portal-video" in styles
