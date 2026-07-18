/* Native cinematic scroll profile: native document scroll + visible visual inertia. */
(function () {
  'use strict';

  var root = document.documentElement;
  var config = window.GICLEE_PREHERO_CONFIG || {};
  var mode = String(config.smoothScrollMode || 'native').trim().toLowerCase();
  var MAX_SLIP_PX = 18;
  var VELOCITY_GAIN = 2.85;
  var TARGET_MEMORY = 0.18;
  var FOLLOW_TAU_MS = 72;
  var RETURN_TAU_MS = 260;
  var INPUT_HOLD_MS = 78;
  var SOFT_RATIO = 0.58;
  var FAR_RATIO = 0.28;
  var BASE_MEDIA_SCALE = 1.018;
  var ACTIVE_MEDIA_SCALE = 0.012;
  var BASE_HERO_SCALE = 1.006;
  var ACTIVE_HERO_SCALE = 0.006;
  var STOP_EPSILON_PX = 0.05;

  var enabled = false;
  var disabledReason = '';
  var frameId = 0;
  var lastFrameTime = 0;
  var lastInputTime = 0;
  var lastScrollY = currentScrollY();
  var targetSlip = 0;
  var currentSlip = 0;
  var appliedVisualKey = '';
  var frameCount = 0;
  var styleWriteCount = 0;
  var peakSlip = 0;
  var inputCount = 0;
  var directionChanges = 0;
  var lastDirection = 0;
  var lastVelocity = 0;

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

  function applyVisualState(value) {
    var rounded = Math.abs(value) <= STOP_EPSILON_PX
      ? 0
      : Math.round(value * 10) / 10;
    var energy = clamp(Math.abs(rounded) / MAX_SLIP_PX, 0, 1);
    var mediaScale = BASE_MEDIA_SCALE + energy * ACTIVE_MEDIA_SCALE;
    var heroScale = BASE_HERO_SCALE + energy * ACTIVE_HERO_SCALE;
    var key = [
      rounded.toFixed(1),
      energy.toFixed(3),
      mediaScale.toFixed(4),
      heroScale.toFixed(4),
    ].join('|');
    if (key === appliedVisualKey) return;
    appliedVisualKey = key;

    root.style.setProperty('--giclee-native-v2-slip-y', rounded.toFixed(1) + 'px');
    root.style.setProperty(
      '--giclee-native-v2-slip-soft-y',
      (rounded * SOFT_RATIO).toFixed(1) + 'px'
    );
    root.style.setProperty(
      '--giclee-native-v2-slip-far-y',
      (rounded * FAR_RATIO).toFixed(1) + 'px'
    );
    root.style.setProperty('--giclee-native-v2-energy', energy.toFixed(3));
    root.style.setProperty('--giclee-native-v2-media-scale', mediaScale.toFixed(4));
    root.style.setProperty('--giclee-native-v2-hero-scale', heroScale.toFixed(4));
    styleWriteCount += 6;
  }

  function stopMotion() {
    targetSlip = 0;
    currentSlip = 0;
    lastFrameTime = 0;
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    applyVisualState(0);
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
    applyVisualState(currentSlip);

    var recentlyActive = now - lastInputTime <= INPUT_HOLD_MS + 36;
    if (
      recentlyActive ||
      Math.abs(targetSlip) > STOP_EPSILON_PX ||
      Math.abs(currentSlip) > STOP_EPSILON_PX
    ) {
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

    var now = performance.now();
    var elapsed = lastInputTime ? clamp(now - lastInputTime, 8, 48) : 16.67;
    var velocity = delta / elapsed;
    var direction = delta > 0 ? 1 : -1;
    if (lastDirection && direction !== lastDirection) directionChanges += 1;
    lastDirection = direction;
    lastVelocity = velocity;

    inputCount += 1;
    lastInputTime = now;
    targetSlip = clamp(
      targetSlip * TARGET_MEMORY + velocity * VELOCITY_GAIN,
      -MAX_SLIP_PX,
      MAX_SLIP_PX
    );
    root.classList.add('giclee-native-v2-scrolling');
    root.setAttribute('data-giclee-native-v2-direction', direction > 0 ? 'down' : 'up');
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
        profile: 'cinematic-visible-v2',
        maxSlipPx: MAX_SLIP_PX,
        followTauMs: FOLLOW_TAU_MS,
        returnTauMs: RETURN_TAU_MS,
        inputHoldMs: INPUT_HOLD_MS,
        targetSlipPx: Math.round(targetSlip * 100) / 100,
        currentSlipPx: Math.round(currentSlip * 100) / 100,
        peakSlipPx: Math.round(peakSlip * 100) / 100,
        lastVelocityPxMs: Math.round(lastVelocity * 1000) / 1000,
        directionChanges: directionChanges,
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
        maxSlipPx: MAX_SLIP_PX,
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
    applyVisualState(0);

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
          profile: 'cinematic-visible-v2',
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
