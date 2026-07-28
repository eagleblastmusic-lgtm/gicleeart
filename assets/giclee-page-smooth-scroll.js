/* Page-agnostic cinematic wheel easing (same profile as homepage native-v2). */
(function () {
  'use strict';

  var root = document.documentElement;
  var WHEEL_GAIN = 1.05;
  var LINE_HEIGHT_PX = 40;
  var PAGE_DELTA_RATIO = 0.9;
  var MAX_WHEEL_DELTA_PX = 420;
  var MAX_TARGET_LEAD_PX = 1800;
  var FOLLOW_TAU_MS = 380;
  var STOP_EPSILON_PX = 0.25;
  var MAX_FRAME_DELTA_MS = 48;

  var enabled = false;
  var frameId = 0;
  var animationActive = false;
  var lastFrameTime = 0;
  var targetScrollY = 0;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
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

  function boot() {
    var disabledReason = determineDisabledReason();
    if (disabledReason) {
      root.setAttribute('data-giclee-smooth-scroll', 'disabled');
      root.setAttribute('data-giclee-smooth-scroll-reason', disabledReason);
      return;
    }

    enabled = true;
    targetScrollY = currentScrollY();
    root.classList.add('giclee-page-smooth-scroll');
    root.setAttribute('data-giclee-smooth-scroll', 'page-native-v2');
    root.removeAttribute('data-giclee-smooth-scroll-reason');

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
