from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PROFILE_CSS = ROOT / "assets" / "giclee-home-native-v2-layer-cull.css"
STACK_CSS = ROOT / "assets" / "giclee-home-stack.css"


def test_native_v2_replaces_full_screen_stack_blur_with_one_compositor_fade() -> None:
    profile = PROFILE_CSS.read_text(encoding="utf-8")
    stack = STACK_CSS.read_text(encoding="utf-8")

    # Preserve evidence of the expensive legacy behavior so the override cannot
    # silently become detached from the actual stack contract.
    assert "filter: blur(calc(var(--home-stack-under-dim, 0) * 14px))" in stack

    assert ".shopify-section.is-stack-under-dim[data-giclee-home-stack]" in profile
    assert "> .section {" in profile
    assert "opacity: calc(1 - var(--home-stack-under-dim, 0) * 0.72)" in profile
    assert "filter: none !important" in profile
    assert "will-change: opacity" in profile


def test_native_v2_bounds_slider_and_decorative_gradient_paint_during_wheel_motion() -> None:
    profile = PROFILE_CSS.read_text(encoding="utf-8")

    assert "comparison-slider-component" in profile
    assert "contain: paint style" in profile
    assert "contain: paint" in profile
    assert "transform: translateZ(0)" in profile
    assert "animation-play-state: paused !important" in profile
    assert "height: 28px !important" in profile
    assert "opacity: var(--home-stack-over-depth, 0)" in profile
    assert "transition-duration: 0s !important" in profile


def test_compositor_profile_does_not_change_stack_geometry() -> None:
    profile = PROFILE_CSS.read_text(encoding="utf-8")

    assert "display: none" not in profile
    assert "position: fixed" not in profile
    assert "position: absolute" not in profile
    assert "margin-top:" not in profile
    assert "min-height:" not in profile
