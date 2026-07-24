from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CHROME = ROOT / "assets" / "giclee-home-prehero-chrome.js"
REVEAL = ROOT / "assets" / "giclee-home-prehero-reveal.js"
CURTAIN = ROOT / "assets" / "giclee-home-hero-horizontal-curtain.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"
GATE = ROOT / "assets" / "giclee-home-hero-video-gate.js"


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
    gate = GATE.read_text(encoding="utf-8")

    assert "rootDocumentTop" in chrome
    assert "scrubDocumentTop" in reveal
    assert "runwayDocumentTop" in curtain
    assert "heroDocumentTop" in gate
    assert "scrollY() - scrubDocumentTop" in reveal
    assert "scrollY() - runwayDocumentTop + viewport" in curtain
    assert "heroDocumentTop - scrollY()" in gate


def test_lenis_adaptively_reduces_video_seek_pressure() -> None:
    source = SCRUB.read_text(encoding="utf-8")

    assert "var LENIS_MAX_SEEK_FPS = 12;" in source
    assert "function activeSeekFps()" in source
    assert "Math.min(SEEK_FPS, LENIS_MAX_SEEK_FPS)" in source
    assert "activeSeekIntervalMs()" in source
    assert "activeSeekEpsilon()" in source
    assert "lenisAdaptiveSeeking:" in source


def test_video_gate_uses_lightweight_curtain_runtime_and_no_idle_reset_loop() -> None:
    curtain = CURTAIN.read_text(encoding="utf-8")
    gate = GATE.read_text(encoding="utf-8")

    assert "GICLEE_HERO_HORIZONTAL_CURTAIN_RUNTIME" in curtain
    assert "GICLEE_HERO_HORIZONTAL_CURTAIN_RUNTIME" in gate
    assert "curtainStatusFallbackCount" in gate
    assert "if (playbackAllowed) stopPlayback();" in gate
    assert "else collectVideos().forEach(pauseAndReset);" not in gate
    assert "gateSyncCount:" in gate
    assert "mediaResetCount:" in gate


def test_sound_consent_only_during_hero_hold_window() -> None:
    gate = GATE.read_text(encoding="utf-8")

    assert "function inHeroHoldWindow(runtime)" in gate
    assert "return heroFullyAppeared() && inHeroHoldWindow(runtime);" in gate
    assert "status.localScroll < status.holdTravel" in gate
    assert "setPromptVisible(false);" in gate


def test_sound_consent_waits_for_full_hero_then_fades_with_audio() -> None:
    gate = GATE.read_text(encoding="utf-8")
    consent_css = (ROOT / "assets" / "giclee-home-hero-sound-consent.css").read_text(
        encoding="utf-8"
    )

    assert "var promptSticky" not in gate
    assert "var promptUnlocked = false;" in gate
    assert "function heroFullyAppeared()" in gate
    assert "function syncPrompt(runtime)" in gate
    assert "setPromptGain(gain);" in gate
    assert "sceneAudioGain(runtime)" in gate
    assert "resolveChoice(false, 'auto-muted');" not in gate
    assert "(hero || document.body).appendChild(prompt);" in gate
    assert "position: absolute;" in consent_css
    assert "--giclee-hero-sound-prompt-gain" in consent_css
    assert "var(--giclee-hero-sound-prompt-gain, 1)" in consent_css


def test_sound_consent_excluded_from_splash_body_fade() -> None:
    """Splash opacity:1 !important must not unmask the body-mounted consent bar."""
    theme = (ROOT / "layout" / "theme.liquid").read_text(encoding="utf-8")
    consent_css = (ROOT / "assets" / "giclee-home-hero-sound-consent.css").read_text(
        encoding="utf-8"
    )

    assert ":not(.giclee-hero-sound-consent)" in theme
    assert "splash-reveal.splash-reveal-active body > :not(#page-transition):not(#splash-screen):not(.giclee-hero-sound-consent)" in theme
    assert "opacity: 0 !important;" in consent_css
    assert "html[data-giclee-hero-sound-prompt='visible'] .giclee-hero-sound-consent" in consent_css
