from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAYOUT_PATH = ROOT / "layout" / "theme.liquid"
JS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.js"
NATIVE_V2_PATH = ROOT / "assets" / "giclee-home-native-v2.js"
NATIVE_V2_CULL_JS_PATH = ROOT / "assets" / "giclee-home-native-v2-layer-cull.js"
NATIVE_V2_CULL_CSS_PATH = ROOT / "assets" / "giclee-home-native-v2-layer-cull.css"
CSS_PATH = ROOT / "assets" / "giclee-home-smooth-scroll.css"
CRITICAL_SNIPPET = ROOT / "snippets" / "giclee-home-stack-critical.liquid"
GENERATOR_PATH = ROOT / "cursor-api" / "Komponenty" / "stronaglowna" / "prehero_full_generator.py"


def _css_rule_body(source: str, selector_fragment: str) -> str:
    selector_start = source.index(selector_fragment)
    opening_brace = source.index("{", selector_start)
    closing_brace = source.index("}", opening_brace)
    return source[opening_brace + 1 : closing_brace]


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


def test_native_v2_smooths_real_mouse_wheel_and_uses_cached_active_pair_stack() -> None:
    source = NATIVE_V2_PATH.read_text(encoding="utf-8")
    styles = CSS_PATH.read_text(encoding="utf-8")
    snippet = CRITICAL_SNIPPET.read_text(encoding="utf-8")

    assert "mode !== 'native-v2'" in source
    assert "WHEEL_GAIN = 1.35" in source
    assert "FOLLOW_TAU_MS = 230" in source
    assert "MAX_TARGET_LEAD_PX = 1800" in source
    assert "window.addEventListener('wheel', onWheel, { passive: false })" in source
    assert "event.preventDefault();" in source
    assert "window.scrollTo(0, value);" in source
    assert "normalizeWheelDelta" in source
    assert "shouldBypassWheel" in source
    assert "elementCanConsumeVerticalWheel" in source
    assert "data-giclee-wheel-native" in source
    assert "data-lenis-prevent" in source
    assert "wheel-cinematic-nous-v3-fast-stack" in source
    assert "native-v2-wheel-raf" in source
    assert "GICLEE_NATIVE_V2_STATUS" in source
    assert "new window.Lenis" not in source
    assert "document.body.style.transform" not in source

    assert "prepareFastStackTakeover" in source
    assert "listener.name === 'initHomeStack'" in source
    assert "native-v2-fast-active-pair" in source
    assert "fastStackPairStarts[pairIndex] - scrollY" in source
    assert "scheduleFastStackRender(value);" in source
    assert "cachedGeometry: true" in source
    assert "activePairOnly: true" in source
    assert "independentMotionLoop: false" in source
    assert "legacyListenerIntercepted" in source
    assert "GICLEE_HOME_STACK_PERFORMANCE_STATUS" in source

    assert "changes only the mouse-wheel timeline" in styles
    assert "--giclee-native-v2-slip-y" not in styles
    assert "giclee-prehero-scrub__video" not in styles
    assert "giclee-prehero-reveal__visual" not in styles
    assert "giclee-prehero-hero-rise" not in styles
    assert "giclee-hero-horizontal-curtain__intro-layer" not in styles

    assert "giclee-home-native-v2.js" in snippet
    assert snippet.index("giclee-home-native-v2.js") < snippet.index(
        "giclee-home-prehero-scrub.js"
    )


def test_native_v2_culls_only_fully_covered_stack_layers_without_flow_collapse() -> None:
    source = NATIVE_V2_CULL_JS_PATH.read_text(encoding="utf-8")
    styles = NATIVE_V2_CULL_CSS_PATH.read_text(encoding="utf-8")
    snippet = CRITICAL_SNIPPET.read_text(encoding="utf-8")
    generator = GENERATOR_PATH.read_text(encoding="utf-8")

    assert "resolveLayerState" in source
    assert "transitionStart = pairStarts[i] - vh" in source
    assert "transitionEnd = pairStarts[i] - STACK_PIN_TOP" in source
    assert "cullBefore: resolvedActivePair >= 0 ? resolvedActivePair : resolvedFrontIndex" in source
    assert "index < state.cullBefore" in source
    assert "giclee-native-v2-covered" in source
    assert "GICLEE_NATIVE_V2_LAYER_CULL_STATUS" in source
    assert "geometryPreserved: true" in source
    assert "normalFlowGeometryPreserved: true" in source
    assert "coveredStickyReleased: true" in source
    assert "paintOnlyCulling: false" in source
    assert "video.pause()" in source
    assert "video.play()" in source
    assert "window.addEventListener('scroll', scheduleApply" in source
    assert "ResizeObserver" in source

    cull_rule = _css_rule_body(
        styles,
        ".shopify-section.giclee-native-v2-covered[data-giclee-home-stack]",
    )
    assert "position: relative !important" in cull_rule
    assert "top: auto !important" in cull_rule
    assert "visibility: hidden !important" in cull_rule
    assert "pointer-events: none !important" in cull_rule
    assert "display:" not in cull_rule
    assert "position: sticky" not in cull_rule
    assert "transform:" not in cull_rule

    assert "giclee-home-native-v2-layer-cull.css" in snippet
    assert "giclee-home-native-v2-layer-cull.js" in snippet
    assert snippet.index("giclee-home-native-v2.js") < snippet.index(
        "giclee-home-native-v2-layer-cull.js"
    )
    assert "giclee-home-native-v2-layer-cull.css" in generator
    assert "giclee-home-native-v2-layer-cull.js" in generator


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
    assert "pointerdown" in source
    assert "keydown" in source
    assert "cancelAnimation" in source
    assert "resetPosition" in source
    assert "ResizeObserver" in source
    assert "shopify:section:load" in source


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

    assert "zones:" in native_v2
    assert "upperHalf:" in native_v2
    assert "lowerHalf:" in native_v2
