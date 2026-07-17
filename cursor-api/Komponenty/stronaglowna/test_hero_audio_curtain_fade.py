from __future__ import annotations

from pathlib import Path


ASSET_PATH = (
    Path(__file__).resolve().parents[3] / "assets" / "giclee-home-hero-video-gate.js"
)


def _source() -> str:
    return ASSET_PATH.read_text(encoding="utf-8")


def test_audio_gain_follows_smoothed_horizontal_curtain_progress() -> None:
    source = _source()

    assert "function curtainAudioGain()" in source
    assert "status.easedProgress" in source
    assert "status.smoothedProgress" in source
    assert "return 1 - Math.min(1, Math.max(0, progress));" in source
    assert "ambientAudio.volume = SOUND_VOLUME * gain;" in source
    assert "audioMaster.volume = gain;" in source


def test_audio_gain_tracking_is_bound_to_playback_lifecycle() -> None:
    source = _source()

    assert "function startVolumeTracking()" in source
    assert "function stopVolumeTracking()" in source
    assert "window.requestAnimationFrame(trackPlaybackVolume)" in source
    assert "startVolumeTracking();" in source
    assert "stopVolumeTracking();" in source
    assert "effectiveAmbientVolume" in source
    assert "audioGain" in source
