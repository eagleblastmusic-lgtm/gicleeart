from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAYOUT_PATH = ROOT / "layout" / "theme.liquid"
JS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.js"
CSS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.css"


def test_homepage_loads_pinned_lenis_before_local_initializer() -> None:
    layout = LAYOUT_PATH.read_text(encoding="utf-8")

    library = "https://cdn.jsdelivr.net/npm/lenis@1.3.25/dist/lenis.min.js"
    initializer = "giclee-home-smooth-scroll.js"

    assert library in layout
    assert "https://cdn.jsdelivr.net/npm/lenis@1.3.25/dist/lenis.css" in layout
    assert initializer in layout
    assert layout.index(library) < layout.index(initializer)


def test_smooth_scroll_uses_accessible_homepage_defaults() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "var LERP = 0.11;" in source
    assert "var WHEEL_MULTIPLIER = 1;" in source
    assert "autoRaf: false" in source
    assert "instance.raf(time);" in source
    assert "manual-single-raf" in source
    assert "autoToggle: true" in source
    assert "anchors: true" in source
    assert "smoothWheel: true" in source
    assert "syncTouch: false" in source
    assert "prefers-reduced-motion: reduce" in source
    assert "window.Shopify && window.Shopify.designMode" in source


def test_smooth_scroll_has_native_fallback_and_nested_scroll_escape_hatches() -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    styles = CSS_PATH.read_text(encoding="utf-8")

    assert "giclee_native_scroll" in source
    assert "CONFIG.smoothScrollMode" in source
    assert "configuredMode() === 'native'" in source
    assert "return 'configuration';" in source
    assert "mode: configuredMode()" in source
    assert "data-lenis-prevent" in source
    assert "data-giclee-smooth-scroll-reason" in source
    assert "GICLEE_SMOOTH_SCROLL_STATUS" in source
    assert "GICLEE_LENIS" in source
    assert ".lenis.lenis-smooth [data-lenis-prevent]" in styles
    assert ".lenis.lenis-stopped" in styles


def test_smooth_scroll_respects_splash_and_page_transition_locks() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "splash-pending" in source
    assert "splash-reveal" in source
    assert "curtain-pending" in source
    assert "instance.stop();" in source
    assert "instance.start();" in source


def test_lenis_performance_profile_uses_single_clock_stack_engine() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "giclee-lenis-performance" in source
    assert "GICLEE_HOME_SECTION_SCROLL" in source
    assert "api.destroy();" in source
    assert "gicleeHomeSectionScroll = 'lenis-bypass'" in source
    assert "--home-stack-slip-y: 0px !important" in source
    assert "filter: none !important" in source
    assert "transition: none !important" in source
    assert "window.GICLEE_HOME_STACK = false" in source
    assert "gicleeHomeStackEngine = 'lenis-single-clock'" in source
    assert "updateLenisStack(lenis.scroll);" in source
    assert "lenisStackPairStarts[i] - scrollY" in source
    assert "independentMotionLoop: false" in source
    assert "cachedGeometry: true" in source
    assert "performanceProfile:" in source
    assert "sectionScrollBypassed:" in source
    assert "stackEngine:" in source


def test_frame_monitor_reports_scroll_rendering_metrics() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "GICLEE_FRAME_MONITOR" in source
    assert "averageFrameMs" in source
    assert "p95FrameMs" in source
    assert "longFramesOver25Ms" in source
    assert "longFramesOver40Ms" in source
    assert "clock:" in source
    assert "stackEngine:" in source
