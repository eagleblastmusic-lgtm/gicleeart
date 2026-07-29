/* Filozofia marki: native, lightweight smoothing, Lenis, or custom wheel tuning. */
(function () {
  'use strict';

  var root = document.documentElement;
  var SCROLL_SMOOTHNESS = 75;
  var WHEEL_GAIN = 1.05;
  var LINE_HEIGHT_PX = 40;
  var PAGE_DELTA_RATIO = 0.9;
  var MAX_WHEEL_DELTA_PX = 420;
  var MAX_TARGET_LEAD_PX = 800;
  var FOLLOW_TAU_MS = 75;
  var STOP_EPSILON_PX = 0.25;
  var MAX_FRAME_DELTA_MS = 48;

  var enabled = false;
  var lenisInstance = null;
  var frameId = 0;
  var animationActive = false;
  var lastFrameTime = 0;
  var targetScrollY = 0;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function filozofiaConfig() {
    return window.GICLEE_FILOZOFIA_CONFIG || {};
  }

  function filozofiaScrollMode() {
    try {
      var override = new URLSearchParams(window.location.search).get(
        'giclee_page_scroll_mode'
      );
      if (
        override === 'standard' ||
        override === 'smooth' ||
        override === 'native-v2' ||
        override === 'lenis' ||
        override === 'custom'
      ) {
        return override;
      }
    } catch (_error) {
      // Keep the saved setting when URLSearchParams is unavailable.
    }
    return String(filozofiaConfig().pageScrollMode || 'standard')
      .trim()
      .toLowerCase();
  }

  function readConfigNumber(key, fallback, min, max) {
    var raw = filozofiaConfig()[key];
    var n = typeof raw === 'number' ? raw : Number.parseFloat(raw);
    if (!Number.isFinite(n)) return fallback;
    return clamp(n, min, max);
  }

  function readConfigBoolean(key, fallback) {
    var raw = filozofiaConfig()[key];
    if (typeof raw === 'boolean') return raw;
    if (raw === 'true' || raw === 1 || raw === '1') return true;
    if (raw === 'false' || raw === 0 || raw === '0') return false;
    return fallback;
  }

  function applyModeTuning() {
    var mode = filozofiaScrollMode();
    SCROLL_SMOOTHNESS = readConfigNumber(
      'scrollSmoothness',
      SCROLL_SMOOTHNESS,
      0,
      100
    );
    WHEEL_GAIN = readConfigNumber('wheelGain', WHEEL_GAIN, 0.1, 5);

    if (mode === 'smooth' || mode === 'native-v2') {
      // 75% = ~74 ms and 800 px. The old 300 ms / 1800 px profile felt
      // resistant because a large target queue stayed alive after wheel input.
      FOLLOW_TAU_MS = clamp(190 - SCROLL_SMOOTHNESS * 1.55, 28, 190);
      MAX_TARGET_LEAD_PX = clamp(
        350 + SCROLL_SMOOTHNESS * 6,
        350,
        950
      );
      return;
    }

    if (mode !== 'custom') return;
    LINE_HEIGHT_PX = readConfigNumber('lineHeightPx', LINE_HEIGHT_PX, 1, 200);
    PAGE_DELTA_RATIO = readConfigNumber(
      'pageDeltaRatio',
      PAGE_DELTA_RATIO,
      0.1,
      2
    );
    MAX_WHEEL_DELTA_PX = readConfigNumber(
      'maxWheelDeltaPx',
      MAX_WHEEL_DELTA_PX,
      50,
      2000
    );
    MAX_TARGET_LEAD_PX = readConfigNumber(
      'maxTargetLeadPx',
      MAX_TARGET_LEAD_PX,
      100,
      5000
    );
    FOLLOW_TAU_MS = readConfigNumber('followTauMs', FOLLOW_TAU_MS, 1, 1200);
    STOP_EPSILON_PX = readConfigNumber(
      'stopEpsilonPx',
      STOP_EPSILON_PX,
      0.01,
      5
    );
    MAX_FRAME_DELTA_MS = readConfigNumber(
      'maxFrameDeltaMs',
      MAX_FRAME_DELTA_MS,
      8,
      100
    );
  }

  function lenisSettings() {
    var preset = String(filozofiaConfig().lenisPreset || '')
      .trim()
      .toLowerCase();
    var settings = {
      preset: preset,
      lerp: 0.245,
      wheelMultiplier: 1.05,
      smoothWheel: true,
      overscroll: true,
      anchors: true,
      stopInertiaOnNavigate: true
    };

    if (!preset || preset === 'legacy') {
      // Backward compatibility for variants saved before the Lenis accordion.
      settings.preset = 'legacy';
      settings.lerp = clamp(
        0.08 + SCROLL_SMOOTHNESS * 0.0022,
        0.08,
        0.3
      );
      settings.wheelMultiplier = WHEEL_GAIN;
    } else if (preset === 'responsive') {
      settings.lerp = 0.32;
      settings.wheelMultiplier = 1;
    } else if (preset === 'cinematic') {
      settings.lerp = 0.14;
      settings.wheelMultiplier = 0.9;
    } else if (preset === 'custom') {
      settings.lerp = readConfigNumber('lenisLerp', 0.245, 0.01, 1);
      settings.wheelMultiplier = readConfigNumber(
        'lenisWheelMultiplier',
        1.05,
        0.1,
        5
      );
      settings.smoothWheel = readConfigBoolean('lenisSmoothWheel', true);
      settings.overscroll = readConfigBoolean('lenisOverscroll', true);
      settings.anchors = readConfigBoolean('lenisAnchors', true);
      settings.stopInertiaOnNavigate = readConfigBoolean(
        'lenisStopInertiaOnNavigate',
        true
      );
    } else {
      settings.preset = 'balanced';
    }
    return settings;
  }

  function followIsDirect() {
    // Bardzo niski tau ≈ natychmiastowe doganianie (bez „filmu”).
    return FOLLOW_TAU_MS <= 16;
  }

  function currentScrollY() {
    return (
      window.scrollY ||
      window.pageYOffset ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0
    );
  }

  function maxScrollY() {
    var doc = document.documentElement;
    var body = document.body;
    var height = Math.max(
      doc ? doc.scrollHeight : 0,
      body ? body.scrollHeight : 0,
      doc ? doc.offsetHeight : 0,
      body ? body.offsetHeight : 0
    );
    return Math.max(0, height - (window.innerHeight || doc.clientHeight || 0));
  }

  function expAlpha(deltaMs, tauMs) {
    if (deltaMs <= 0) return 1;
    return 1 - Math.exp(-deltaMs / Math.max(1, tauMs));
  }

  function queryDisablesProfile() {
    try {
      return new URLSearchParams(window.location.search).get('giclee_native_scroll') === '1';
    } catch (_error) {
      return false;
    }
  }

  function reducedMotionRequested() {
    return !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function designModeActive() {
    return !!(window.Shopify && window.Shopify.designMode);
  }

  function touchLikeDevice() {
    return !!(
      window.matchMedia &&
      window.matchMedia('(hover: none) and (pointer: coarse)').matches
    );
  }

  function determineDisabledReason() {
    if (queryDisablesProfile()) return 'query';
    if (reducedMotionRequested()) return 'reduced-motion';
    if (designModeActive()) return 'shopify-design-mode';
    if (touchLikeDevice()) return 'touch-native';
    if (document.body.classList.contains('template-page-filozofia-marki')) {
      var mode = filozofiaScrollMode();
      if (
        mode !== 'smooth' &&
        mode !== 'native-v2' &&
        mode !== 'lenis' &&
        mode !== 'custom'
      ) {
        return 'configuration';
      }
    }
    return '';
  }

  function normalizeWheelDelta(event) {
    var delta = Number(event.deltaY) || 0;
    if (event.deltaMode === 1) delta *= LINE_HEIGHT_PX;
    if (event.deltaMode === 2) {
      delta *= (window.innerHeight || 800) * PAGE_DELTA_RATIO;
    }
    return clamp(delta, -MAX_WHEEL_DELTA_PX, MAX_WHEEL_DELTA_PX);
  }

  function eventPath(event) {
    if (typeof event.composedPath === 'function') return event.composedPath();
    var path = [];
    var node = event.target;
    while (node) {
      path.push(node);
      node = node.parentNode;
    }
    return path;
  }

  function isExplicitNativeWheelZone(element) {
    if (!element || element.nodeType !== 1) return false;
    if (element.hasAttribute('data-giclee-wheel-native')) return true;
    if (element.hasAttribute('data-lenis-prevent')) return true;
    if (element.tagName === 'IFRAME' || element.tagName === 'SELECT') return true;
    if (element.matches('input[type="number"], textarea, [contenteditable="true"]')) return true;
    if (element.matches('dialog, [role="dialog"], .drawer, .modal, .popover')) return true;
    return false;
  }

  function elementCanConsumeVerticalWheel(element, delta) {
    if (!element || element.nodeType !== 1) return false;
    if (element === document.body || element === document.documentElement) return false;

    var style = window.getComputedStyle(element);
    var overflowY = style.overflowY;
    if (overflowY !== 'auto' && overflowY !== 'scroll' && overflowY !== 'overlay') {
      return false;
    }
    if (element.scrollHeight <= element.clientHeight + 1) return false;

    if (delta < 0) return element.scrollTop > 0;
    if (delta > 0) {
      return element.scrollTop + element.clientHeight < element.scrollHeight - 1;
    }
    return false;
  }

  function shouldBypassWheel(event, delta) {
    if (event.defaultPrevented) return true;
    if (event.ctrlKey || event.metaKey || event.shiftKey) return true;
    if (Math.abs(Number(event.deltaX) || 0) > Math.abs(delta)) return true;

    var path = eventPath(event);
    for (var i = 0; i < path.length; i += 1) {
      var element = path[i];
      if (isExplicitNativeWheelZone(element)) return true;
      if (elementCanConsumeVerticalWheel(element, delta)) return true;
    }
    return false;
  }

  function shouldPreventLenis(node) {
    if (!node || node.nodeType !== 1) return false;
    if (isExplicitNativeWheelZone(node)) return true;
    if (node === document.body || node === document.documentElement) return false;

    var style = window.getComputedStyle(node);
    var overflowY = style.overflowY;
    return (
      (overflowY === 'auto' ||
        overflowY === 'scroll' ||
        overflowY === 'overlay') &&
      node.scrollHeight > node.clientHeight + 1
    );
  }

  function clearAnimationClass() {
    root.classList.remove('giclee-page-smooth-scrolling');
  }

  function cancelAnimation(syncTarget) {
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    animationActive = false;
    lastFrameTime = 0;
    if (syncTarget !== false) targetScrollY = currentScrollY();
    clearAnimationClass();
  }

  function scheduleFrame() {
    if (!frameId) frameId = window.requestAnimationFrame(tick);
  }

  function writeScrollY(value) {
    window.scrollTo(0, value);
  }

  function tick(now) {
    frameId = 0;

    if (!enabled || document.hidden) {
      cancelAnimation(true);
      return;
    }

    var current = currentScrollY();
    targetScrollY = clamp(targetScrollY, 0, maxScrollY());
    var remaining = targetScrollY - current;

    if (Math.abs(remaining) <= STOP_EPSILON_PX) {
      if (Math.abs(remaining) > 0.01) writeScrollY(targetScrollY);
      cancelAnimation(false);
      return;
    }

    if (followIsDirect()) {
      writeScrollY(targetScrollY);
      cancelAnimation(false);
      return;
    }

    var deltaMs = lastFrameTime
      ? Math.min(MAX_FRAME_DELTA_MS, now - lastFrameTime)
      : 16.67;
    lastFrameTime = now;

    var next = current + remaining * expAlpha(deltaMs, FOLLOW_TAU_MS);
    if (Math.abs(targetScrollY - next) <= STOP_EPSILON_PX) next = targetScrollY;
    writeScrollY(next);
    scheduleFrame();
  }

  function onWheel(event) {
    if (!enabled || document.hidden) return;

    var delta = normalizeWheelDelta(event);
    if (!delta) return;
    if (shouldBypassWheel(event, delta)) return;

    event.preventDefault();

    var current = currentScrollY();
    var remaining = targetScrollY - current;
    if (remaining && Math.sign(remaining) !== Math.sign(delta)) {
      targetScrollY = current;
    }

    var proposed = targetScrollY + delta * WHEEL_GAIN;
    proposed = clamp(
      proposed,
      current - MAX_TARGET_LEAD_PX,
      current + MAX_TARGET_LEAD_PX
    );
    targetScrollY = clamp(proposed, 0, maxScrollY());

    if (followIsDirect()) {
      writeScrollY(targetScrollY);
      cancelAnimation(false);
      return;
    }

    animationActive = true;
    root.classList.add('giclee-page-smooth-scrolling');
    scheduleFrame();
  }

  function onNativeScroll() {
    if (!enabled || animationActive) return;
    targetScrollY = currentScrollY();
  }

  function resetPosition() {
    cancelAnimation(true);
  }

  function exposeDiagnostics(mode, extra) {
    window.GICLEE_PAGE_SCROLL = Object.assign(
      {
        mode: mode,
        smoothness: SCROLL_SMOOTHNESS,
        wheelGain: WHEEL_GAIN
      },
      extra || {}
    );
  }

  function bootLenis() {
    if (typeof window.Lenis !== 'function') {
      root.setAttribute('data-giclee-smooth-scroll', 'disabled');
      root.setAttribute(
        'data-giclee-smooth-scroll-reason',
        'lenis-unavailable'
      );
      exposeDiagnostics('disabled', { reason: 'lenis-unavailable' });
      return;
    }

    var settings = lenisSettings();
    lenisInstance = new window.Lenis({
      autoRaf: true,
      smoothWheel: settings.smoothWheel,
      syncTouch: false,
      lerp: settings.lerp,
      wheelMultiplier: settings.wheelMultiplier,
      overscroll: settings.overscroll,
      anchors: settings.anchors,
      stopInertiaOnNavigate: settings.stopInertiaOnNavigate,
      prevent: shouldPreventLenis
    });

    root.classList.add('giclee-page-smooth-scroll');
    root.setAttribute('data-giclee-smooth-scroll', 'lenis');
    root.setAttribute('data-giclee-lenis-preset', settings.preset);
    root.setAttribute(
      'data-giclee-lenis-lerp',
      settings.lerp.toFixed(3)
    );
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    exposeDiagnostics('lenis', {
      preset: settings.preset,
      lerp: settings.lerp,
      wheelMultiplier: settings.wheelMultiplier,
      smoothWheel: settings.smoothWheel,
      overscroll: settings.overscroll,
      anchors: settings.anchors,
      stopInertiaOnNavigate: settings.stopInertiaOnNavigate,
      instance: lenisInstance,
      destroy: function () {
        if (lenisInstance) lenisInstance.destroy();
        lenisInstance = null;
        root.classList.remove('giclee-page-smooth-scroll');
      }
    });
  }

  function boot() {
    var disabledReason = determineDisabledReason();
    if (disabledReason) {
      root.setAttribute('data-giclee-smooth-scroll', 'disabled');
      root.setAttribute('data-giclee-smooth-scroll-reason', disabledReason);
      exposeDiagnostics('disabled', { reason: disabledReason });
      return;
    }

    applyModeTuning();
    if (filozofiaScrollMode() === 'lenis') {
      bootLenis();
      return;
    }

    enabled = true;
    targetScrollY = currentScrollY();
    root.classList.add('giclee-page-smooth-scroll');
    root.setAttribute(
      'data-giclee-smooth-scroll',
      filozofiaScrollMode() === 'custom' ? 'page-custom' : 'page-native-v2'
    );
    root.setAttribute(
      'data-giclee-scroll-smoothness',
      String(SCROLL_SMOOTHNESS)
    );
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    exposeDiagnostics(filozofiaScrollMode(), {
      followTauMs: FOLLOW_TAU_MS,
      maxTargetLeadPx: MAX_TARGET_LEAD_PX
    });

    window.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('scroll', onNativeScroll, { passive: true });
    window.addEventListener('resize', resetPosition, { passive: true });
    window.addEventListener('orientationchange', resetPosition, { passive: true });
    window.addEventListener('pageshow', resetPosition, { passive: true });
    window.addEventListener('pointerdown', function () {
      if (animationActive || frameId) resetPosition();
    }, { passive: true });
    window.addEventListener('keydown', function () {
      if (animationActive || frameId) resetPosition();
    }, { passive: true });
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) cancelAnimation(true);
      else resetPosition();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
