/* Native cinematic scroll profile: native document scroll + subtle visual inertia. */
(function () {
  'use strict';

  var root = document.documentElement;
  var config = window.GICLEE_PREHERO_CONFIG || {};
  var mode = String(config.smoothScrollMode || 'native').trim().toLowerCase();
  var MAX_SLIP_PX = 7;
  var INPUT_GAIN = 0.11;
  var FOLLOW_TAU_MS = 58;
  var RETURN_TAU_MS = 155;
  var INPUT_HOLD_MS = 42;
  var STOP_EPSILON_PX = 0.05;

  var enabled = false;
  var disabledReason = '';
  var frameId = 0;
  var lastFrameTime = 0;
  var lastInputTime = 0;
  var lastScrollY = currentScrollY();
  var targetSlip = 0;
  var currentSlip = 0;
  var appliedSlip = '';
  var frameCount = 0;
  var styleWriteCount = 0;
  var peakSlip = 0;
  var inputCount = 0;

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

  function applySlip(value) {
    var rounded = Math.abs(value) <= STOP_EPSILON_PX
      ? 0
      : Math.round(value * 10) / 10;
    var key = rounded.toFixed(1);
    if (key === appliedSlip) return;
    appliedSlip = key;
    root.style.setProperty('--giclee-native-v2-slip-y', key + 'px');
    root.style.setProperty(
      '--giclee-native-v2-slip-soft-y',
      (rounded * 0.52).toFixed(1) + 'px'
    );
    styleWriteCount += 2;
  }

  function stopMotion() {
    targetSlip = 0;
    currentSlip = 0;
    lastFrameTime = 0;
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    applySlip(0);
    root.classList.remove('giclee-native-v2-scrolling');
  }

  function scheduleFrame() {
    if (!frameId) frameId = window.requestAnimationFrame(tick);
  }

  function tick(now) {
    frameId = 0;
    frameCount += 1;

    if (!enabled || pageInteractionLocked() || document.hidden) {
      stopMotion();
      return;
    }

    var delta = lastFrameTime ? Math.min(48, now - lastFrameTime) : 16.67;
    lastFrameTime = now;

    if (now - lastInputTime > INPUT_HOLD_MS) targetSlip = 0;

    var returning = Math.abs(targetSlip) <= STOP_EPSILON_PX;
    var tau = returning ? RETURN_TAU_MS : FOLLOW_TAU_MS;
    currentSlip += (targetSlip - currentSlip) * expAlpha(delta, tau);

    if (Math.abs(targetSlip - currentSlip) <= STOP_EPSILON_PX && returning) {
      currentSlip = 0;
    }

    peakSlip = Math.max(peakSlip, Math.abs(currentSlip));
    applySlip(currentSlip);

    var recentlyActive = now - lastInputTime <= INPUT_HOLD_MS + 24;
    if (recentlyActive || Math.abs(targetSlip) > STOP_EPSILON_PX || Math.abs(currentSlip) > STOP_EPSILON_PX) {
      scheduleFrame();
      return;
    }

    lastFrameTime = 0;
    root.classList.remove('giclee-native-v2-scrolling');
  }

  function onScroll() {
    if (!enabled || pageInteractionLocked()) return;
    var nextScrollY = currentScrollY();
    var delta = nextScrollY - lastScrollY;
    lastScrollY = nextScrollY;
    if (!delta) return;

    inputCount += 1;
    lastInputTime = performance.now();
    targetSlip = clamp(
      targetSlip * 0.24 + delta * INPUT_GAIN,
      -MAX_SLIP_PX,
      MAX_SLIP_PX
    );
    root.classList.add('giclee-native-v2-scrolling');
    root.setAttribute('data-giclee-native-v2-direction', delta > 0 ? 'down' : 'up');
    scheduleFrame();
  }

  function resetPosition() {
    lastScrollY = currentScrollY();
    stopMotion();
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
            clock: 'native-v2-visual-raf',
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
      return {
        ready: enabled,
        active: enabled,
        mode: 'native-v2',
        disabledReason: disabledReason,
        clock: 'native-v2-visual-raf',
        maxSlipPx: MAX_SLIP_PX,
        targetSlipPx: Math.round(targetSlip * 100) / 100,
        currentSlipPx: Math.round(currentSlip * 100) / 100,
        peakSlipPx: Math.round(peakSlip * 100) / 100,
        inputCount: inputCount,
        frameCount: frameCount,
        styleWriteCount: styleWriteCount,
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
        clock: 'native-v2-visual-raf',
        stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
        slipPx: Math.round(currentSlip * 100) / 100,
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
    root.classList.add('giclee-native-v2');
    root.setAttribute('data-giclee-smooth-scroll', 'native-v2');
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    root.dataset.gicleeHomeStackEngine = 'legacy-native-v2';
    applySlip(0);

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', resetPosition, { passive: true });
    window.addEventListener('orientationchange', resetPosition, { passive: true });
    window.addEventListener('pageshow', resetPosition, { passive: true });
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) stopMotion();
      else resetPosition();
    });
    if ('onscrollend' in window) {
      window.addEventListener('scrollend', function () {
        targetSlip = 0;
        scheduleFrame();
      }, { passive: true });
    }

    installFrameMonitor();
    publishStatus();
    window.dispatchEvent(
      new CustomEvent('giclee:native-v2-ready', {
        detail: {
          maxSlipPx: MAX_SLIP_PX,
          clock: 'native-v2-visual-raf',
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
