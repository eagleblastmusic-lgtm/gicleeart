from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAYOUT_PATH = ROOT / "layout" / "theme.liquid"
JS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.js"
NATIVE_V2_PATH = ROOT / "assets" / "giclee-home-native-v2.js"
CSS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.css"
CRITICAL_SNIPPET = ROOT / "snippets" / "giclee-home-stack-critical.liquid"


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
    assert "CONFIG.smoothScrollMode || 'native'" in source
    assert "autoRaf: true" in source
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


def test_lenis_performance_profile_uses_cached_active_pair_stack() -> None:
    source = JS_PATH.read_text(encoding="utf-8")

    assert "giclee-lenis-performance" in source
    assert "GICLEE_HOME_SECTION_SCROLL" in source
    assert "api.destroy();" in source
    assert "gicleeHomeSectionScroll = 'lenis-bypass'" in source
    assert "listener.name === 'initHomeStack'" in source
    assert "lenis-fast-active-pair" in source
    assert "activePairOnly: true" in source
    assert "cachedGeometry: true" in source
    assert "independentMotionLoop: false" in source
    assert "fastStackPairStarts[pairIndex] - scrollY" in source
    assert "scheduleFastStackRender(lenis.scroll);" in source
    assert "new CustomEvent('giclee:smooth-scroll'" not in source
    assert "performanceProfile:" in source
    assert "sectionScrollBypassed:" in source
    assert "stackEngine:" in source


def test_native_v2_keeps_native_document_scroll_and_uses_visual_inertia_only() -> None:
    source = NATIVE_V2_PATH.read_text(encoding="utf-8")
    styles = CSS_PATH.read_text(encoding="utf-8")
    snippet = CRITICAL_SNIPPET.read_text(encoding="utf-8")

    assert "mode !== 'native-v2'" in source
    assert "MAX_SLIP_PX = 7" in source
    assert "window.addEventListener('scroll', onScroll" in source
    assert "window.requestAnimationFrame(tick)" in source
    assert "--giclee-native-v2-slip-y" in source
    assert "GICLEE_NATIVE_V2_STATUS" in source
    assert "native-v2-visual-raf" in source
    assert "new window.Lenis" not in source
    assert "preventDefault" not in source
    assert "wheel" not in source.lower()
    assert "document.body.style.transform" not in source
    assert "giclee-prehero-scrub__video" in styles
    assert "giclee-prehero-scrub__canvas" in styles
    assert "giclee-prehero-reveal__visual" in styles
    assert "will-change: translate" in styles
    assert "giclee-home-native-v2.js" in snippet
    assert snippet.index("giclee-home-native-v2.js") < snippet.index(
        "giclee-home-prehero-scrub.js"
    )


def test_native_v2_has_accessibility_and_runtime_safety_guards() -> None:
    source = NATIVE_V2_PATH.read_text(encoding="utf-8")

    assert "prefers-reduced-motion: reduce" in source
    assert "window.Shopify && window.Shopify.designMode" in source
    assert "(hover: none) and (pointer: coarse)" in source
    assert "giclee_native_scroll" in source
    assert "splash-pending" in source
    assert "splash-reveal" in source
    assert "curtain-pending" in source
    assert "document.hidden" in source
    assert "visibilitychange" in source
    assert "scrollend" in source
    assert "stopMotion();" in source


def test_frame_monitor_reports_scroll_rendering_metrics() -> None:
    source = JS_PATH.read_text(encoding="utf-8")
    native_v2 = NATIVE_V2_PATH.read_text(encoding="utf-8")

    for current in (source, native_v2):
        assert "GICLEE_FRAME_MONITOR" in current
        assert "averageFrameMs" in current
        assert "p95FrameMs" in current
        assert "longFramesOver25Ms" in current
        assert "longFramesOver40Ms" in current
        assert "clock:" in current
        assert "stackEngine:" in current
