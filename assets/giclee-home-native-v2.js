/* Native cinematic wheel profile: real wheel smoothing without Lenis or visual layer drift. */
(function () {
  'use strict';

  var root = document.documentElement;
  var config = window.GICLEE_PREHERO_CONFIG || {};
  var mode = String(config.smoothScrollMode || 'native').trim().toLowerCase();

  var WHEEL_GAIN = 1;
  var LINE_HEIGHT_PX = 40;
  var PAGE_DELTA_RATIO = 0.9;
  var MAX_WHEEL_DELTA_PX = 420;
  var MAX_TARGET_LEAD_PX = 1200;
  var FOLLOW_TAU_MS = 105;
  var STOP_EPSILON_PX = 0.35;
  var MAX_FRAME_DELTA_MS = 48;
  var PROGRAMMATIC_SCROLL_TOLERANCE_PX = 2;
  var PROGRAMMATIC_SCROLL_WINDOW_MS = 64;

  var enabled = false;
  var disabledReason = '';
  var frameId = 0;
  var lastFrameTime = 0;
  var targetScrollY = currentScrollY();
  var lastProgrammaticScrollY = targetScrollY;
  var lastProgrammaticWriteAt = 0;
  var interceptedWheelCount = 0;
  var bypassedWheelCount = 0;
  var externalSyncCount = 0;
  var frameCount = 0;
  var lastWheelDelta = 0;
  var peakTargetLead = 0;

  if (mode !== 'native-v2') return;

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
    } catch (error) {
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

  function pageInteractionLocked() {
    return (
      root.classList.contains('splash-pending') ||
      root.classList.contains('splash-reveal') ||
      root.classList.contains('curtain-pending')
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
    root.classList.remove('giclee-native-v2-scrolling');
  }

  function cancelAnimation(syncTarget) {
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    lastFrameTime = 0;
    if (syncTarget !== false) targetScrollY = currentScrollY();
    clearAnimationClass();
  }

  function scheduleFrame() {
    if (!frameId) frameId = window.requestAnimationFrame(tick);
  }

  function writeScrollY(value) {
    lastProgrammaticScrollY = value;
    lastProgrammaticWriteAt = performance.now();
    window.scrollTo(0, value);
  }

  function tick(now) {
    frameId = 0;
    frameCount += 1;

    if (!enabled || pageInteractionLocked() || document.hidden) {
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
    if (!enabled || pageInteractionLocked() || document.hidden) return;

    var delta = normalizeWheelDelta(event);
    if (!delta) return;
    if (shouldBypassWheel(event, delta)) {
      bypassedWheelCount += 1;
      return;
    }

    event.preventDefault();
    interceptedWheelCount += 1;
    lastWheelDelta = delta;

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
    peakTargetLead = Math.max(peakTargetLead, Math.abs(targetScrollY - current));

    root.classList.add('giclee-native-v2-scrolling');
    root.setAttribute('data-giclee-native-v2-direction', delta > 0 ? 'down' : 'up');
    scheduleFrame();
  }

  function onNativeScroll() {
    if (!enabled) return;
    var current = currentScrollY();
    var recentProgrammaticWrite =
      performance.now() - lastProgrammaticWriteAt <= PROGRAMMATIC_SCROLL_WINDOW_MS;
    var matchesProgrammaticWrite =
      Math.abs(current - lastProgrammaticScrollY) <= PROGRAMMATIC_SCROLL_TOLERANCE_PX;

    if (frameId && recentProgrammaticWrite && matchesProgrammaticWrite) return;

    targetScrollY = current;
    if (frameId) {
      externalSyncCount += 1;
      cancelAnimation(false);
    }
  }

  function resetPosition() {
    targetScrollY = currentScrollY();
    lastProgrammaticScrollY = targetScrollY;
    cancelAnimation(false);
  }

  function installFrameMonitor() {
    window.GICLEE_FRAME_MONITOR = function (durationMs) {
      var duration = Math.max(1000, Math.min(30000, Number(durationMs) || 5000));
      return new Promise(function (resolve) {
        var startedAt = performance.now();
        var lastAt = startedAt;
        var samples = [];

        function percentile(values, ratio) {
          if (!values.length) return 0;
          var sorted = values.slice().sort(function (a, b) { return a - b; });
          var index = Math.min(sorted.length - 1, Math.floor(sorted.length * ratio));
          return sorted[index];
        }

        function finish(now) {
          var elapsed = Math.max(1, now - startedAt);
          var average = samples.length
            ? samples.reduce(function (sum, value) { return sum + value; }, 0) / samples.length
            : 0;
          var result = {
            durationMs: Math.round(elapsed),
            sampleCount: samples.length,
            fps: Math.round((samples.length * 1000 / elapsed) * 10) / 10,
            averageFrameMs: Math.round(average * 100) / 100,
            p95FrameMs: Math.round(percentile(samples, 0.95) * 100) / 100,
            longFramesOver25Ms: samples.filter(function (value) { return value > 25; }).length,
            longFramesOver40Ms: samples.filter(function (value) { return value > 40; }).length,
            mode: 'native-v2',
            clock: 'native-v2-wheel-raf',
            stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
          };
          console.log('[giclee frame monitor]', result);
          resolve(result);
        }

        function frame(now) {
          samples.push(now - lastAt);
          lastAt = now;
          if (now - startedAt < duration) window.requestAnimationFrame(frame);
          else finish(now);
        }

        window.requestAnimationFrame(function (now) {
          lastAt = now;
          window.requestAnimationFrame(frame);
        });
      });
    };
  }

  function publishStatus() {
    window.GICLEE_NATIVE_V2_STATUS = function () {
      var current = currentScrollY();
      return {
        ready: enabled,
        active: enabled,
        mode: 'native-v2',
        profile: 'wheel-cinematic-v1',
        disabledReason: disabledReason,
        clock: 'native-v2-wheel-raf',
        wheelSmoothing: true,
        wheelGain: WHEEL_GAIN,
        followTauMs: FOLLOW_TAU_MS,
        maxWheelDeltaPx: MAX_WHEEL_DELTA_PX,
        maxTargetLeadPx: MAX_TARGET_LEAD_PX,
        currentScrollY: Math.round(current * 10) / 10,
        targetScrollY: Math.round(targetScrollY * 10) / 10,
        remainingPx: Math.round((targetScrollY - current) * 10) / 10,
        interceptedWheelCount: interceptedWheelCount,
        bypassedWheelCount: bypassedWheelCount,
        externalSyncCount: externalSyncCount,
        frameCount: frameCount,
        lastWheelDelta: Math.round(lastWheelDelta * 10) / 10,
        peakTargetLeadPx: Math.round(peakTargetLead * 10) / 10,
        running: !!frameId,
      };
    };

    var previousStatus = window.GICLEE_SMOOTH_SCROLL_STATUS;
    window.GICLEE_SMOOTH_SCROLL_STATUS = function () {
      var previous = {};
      if (typeof previousStatus === 'function') {
        try {
          previous = previousStatus() || {};
        } catch (error) {
          previous = {};
        }
      }
      return Object.assign({}, previous, {
        ready: enabled,
        active: enabled,
        mode: 'native-v2',
        disabledReason: disabledReason,
        performanceProfile: false,
        wheelSmoothing: true,
        clock: 'native-v2-wheel-raf',
        stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
      });
    };
  }

  function boot() {
    disabledReason = determineDisabledReason();
    if (disabledReason) {
      publishStatus();
      return;
    }

    enabled = true;
    targetScrollY = currentScrollY();
    lastProgrammaticScrollY = targetScrollY;
    root.classList.add('giclee-native-v2');
    root.setAttribute('data-giclee-smooth-scroll', 'native-v2');
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    root.dataset.gicleeHomeStackEngine = 'legacy-native-v2';

    window.addEventListener('wheel', onWheel, { passive: false });
    window.addEventListener('scroll', onNativeScroll, { passive: true });
    window.addEventListener('resize', resetPosition, { passive: true });
    window.addEventListener('orientationchange', resetPosition, { passive: true });
    window.addEventListener('pageshow', resetPosition, { passive: true });
    window.addEventListener('pointerdown', function () {
      if (frameId) resetPosition();
    }, { passive: true });
    window.addEventListener('keydown', function () {
      if (frameId) resetPosition();
    }, { passive: true });
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) cancelAnimation(true);
      else resetPosition();
    });

    installFrameMonitor();
    publishStatus();
    window.GICLEE_NATIVE_V2_STOP = resetPosition;
    window.dispatchEvent(
      new CustomEvent('giclee:native-v2-ready', {
        detail: {
          profile: 'wheel-cinematic-v1',
          clock: 'native-v2-wheel-raf',
          followTauMs: FOLLOW_TAU_MS,
        },
      })
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
