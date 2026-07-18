from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
COMPARISON_SLIDER_PATH = ROOT / "assets" / "comparison-slider.js"
NATIVE_V2_PERF_CSS_PATH = ROOT / "assets" / "giclee-home-native-v2-layer-cull.css"


def test_native_v2_keeps_comparison_sliders_interactive_without_auto_hint_animation() -> None:
    source = COMPARISON_SLIDER_PATH.read_text(encoding="utf-8")

    assert "nativeV2AutoHintDisabled" in source
    assert "mode === 'native-v2'" in source
    assert "this.dataset.gicleeNativeV2Hint = 'disabled'" in source
    assert "mediaWrapper.style.setProperty('--transition-duration', '0s')" in source
    assert "this.sync();" in source
    assert "on:input" not in source  # interaction stays in the Liquid block, not duplicated here
    assert "this.setupIntersectionObserver();" in source


def test_native_v2_scroll_time_profile_avoids_heavy_lower_stack_filter_repaints() -> None:
    styles = NATIVE_V2_PERF_CSS_PATH.read_text(encoding="utf-8")

    assert "giclee-native-v2-scrolling" in styles
    assert "giclee-home-studio-reveal__heading" in styles
    assert "giclee-home-studio-reveal__paragraph" in styles
    assert "giclee-home-final-difference" in styles
    assert "comparison-slider-component" in styles
    assert "filter: none !important" in styles
    assert "box-shadow: none !important" in styles
    assert "transition-property: opacity, transform !important" in styles
    assert "transition-duration: 0s !important" in styles
