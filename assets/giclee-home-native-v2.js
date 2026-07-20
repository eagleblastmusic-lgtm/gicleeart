/* Native cinematic wheel profile: pronounced real wheel smoothing without Lenis or visual layer drift. */
(function () {
  'use strict';

  var root = document.documentElement;
  var config = window.GICLEE_PREHERO_CONFIG || {};
  var mode = String(config.smoothScrollMode || 'native').trim().toLowerCase();

  /* Tuned to the longer, visibly eased wheel response used by cinematic portals. */
  var WHEEL_GAIN = 1.35;
  var LINE_HEIGHT_PX = 40;
  var PAGE_DELTA_RATIO = 0.9;
  var MAX_WHEEL_DELTA_PX = 420;
  var MAX_TARGET_LEAD_PX = 1800;
  var FOLLOW_TAU_MS = 230;
  var STOP_EPSILON_PX = 0.25;
  var MAX_FRAME_DELTA_MS = 48;

  var STACK_HOOKS = [
    'hero',
    'intro',
    'restoration',
    'color-correction',
    'potential',
    'see-difference',
  ];
  var STACK_PIN_TOP = 16;
  var STACK_SCROLL_REST = 4;

  var enabled = false;
  var disabledReason = '';
  var frameId = 0;
  var animationActive = false;
  var lastFrameTime = 0;
  var targetScrollY = currentScrollY();
  var interceptedWheelCount = 0;
  var bypassedWheelCount = 0;
  var externalSyncCount = 0;
  var frameCount = 0;
  var lastWheelDelta = 0;
  var peakTargetLead = 0;
  var animationCount = 0;

  var stackFlagValue = !!window.GICLEE_HOME_STACK;
  var stackFlagDescriptorInstalled = false;
  var nativeDocumentAddEventListener = document.addEventListener;
  var legacyStackListenerIntercepted = false;
  var fastStackReady = false;
  var fastStackInitAttempts = 0;
  var fastStackSections = [];
  var fastStackPairStarts = [];
  var fastStackDividersByPair = [];
  var fastStackActivePair = -1;
  var fastStackPendingScroll = 0;
  var fastStackFrameId = 0;
  var fastStackMeasureFrameId = 0;
  var fastStackResizeObserver = null;
  var fastStackRenderCount = 0;
  var fastStackStyleWrites = 0;
  var fastStackLayoutReads = 0;

  if (mode !== 'native-v2') return;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function smoothstep(value) {
    var t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function easeInOutCubic(value) {
    var t = clamp(value, 0, 1);
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
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

  function viewportHeight() {
    return window.innerHeight || document.documentElement.clientHeight || 800;
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

  function findStackSection(sectionKey) {
    if (!sectionKey) return null;
    return (
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]')
    );
  }

  function isDividerSection(element) {
    return !!(
      element &&
      element.classList &&
      element.classList.contains('shopify-section') &&
      element.querySelector('[data-testid^="divider-"]')
    );
  }

  function documentTop(element) {
    var top = 0;
    var node = element;
    while (node) {
      top += Number(node.offsetTop) || 0;
      node = node.offsetParent;
    }
    fastStackLayoutReads += 1;
    return top;
  }

  function setStyleIfChanged(element, property, value, cacheKey) {
    if (!element || element[cacheKey] === value) return;
    element[cacheKey] = value;
    element.style.setProperty(property, value);
    fastStackStyleWrites += 1;
  }

  function removeStyleIfPresent(element, property, cacheKey) {
    if (!element || element[cacheKey] === '') return;
    element[cacheKey] = '';
    element.style.removeProperty(property);
    fastStackStyleWrites += 1;
  }

  function toggleClassIfChanged(element, className, active, cacheKey) {
    if (!element || element[cacheKey] === active) return;
    element[cacheKey] = active;
    element.classList.toggle(className, active);
  }

  function ensureHeroFooterBand(heroElement) {
    if (!heroElement) return null;
    var footer = heroElement.querySelector('.giclee-home-hero-footer');
    if (!footer) {
      footer = document.createElement('div');
      footer.className = 'giclee-home-hero-footer';
      footer.setAttribute('aria-hidden', 'true');
      heroElement.appendChild(footer);
    }
    return footer;
  }

  function ensureHeroScrollCue(heroElement) {
    if (!heroElement) return;
    var footer = ensureHeroFooterBand(heroElement);
    var cue = heroElement.querySelector('.giclee-home-scroll-cue');
    if (!cue) {
      cue = document.createElement('div');
      cue.className = 'giclee-home-scroll-cue';
      cue.setAttribute('aria-hidden', 'true');
      var first = document.createElement('span');
      first.className = 'giclee-home-scroll-cue__chevron';
      var second = document.createElement('span');
      second.className = 'giclee-home-scroll-cue__chevron';
      cue.appendChild(first);
      cue.appendChild(second);
    }
    if (footer && cue.parentElement !== footer) footer.appendChild(cue);
  }

  function tagFastStackDividers() {
    fastStackDividersByPair = [];
    for (var pair = 0; pair < fastStackSections.length - 1; pair += 1) {
      fastStackDividersByPair[pair] = [];
    }

    for (var i = 0; i < fastStackSections.length; i += 1) {
      var isLast = i === fastStackSections.length - 1;
      var layer = isLast ? i + 1 : i + 2;
      var stopAt = isLast ? null : fastStackSections[i + 1];
      var dividers = [];
      var node = fastStackSections[i].nextElementSibling;
      while (node && node !== stopAt) {
        if (isDividerSection(node)) dividers.push(node);
        node = node.nextElementSibling;
      }

      dividers.forEach(function (divider, dividerIndex) {
        divider.setAttribute('data-giclee-home-stack', String(layer));
        divider.classList.add('giclee-home-stack-divider');
        divider.classList.remove('giclee-home-stack-divider--scroll');
        divider._gicleeNativeV2PairIndex = -1;
        var isScrollDivider = !isLast && dividerIndex === dividers.length - 1;
        if (!isScrollDivider) return;
        divider.classList.add('giclee-home-stack-divider--scroll');
        divider._gicleeNativeV2PairIndex = i;
        setStyleIfChanged(divider, '--home-stack-slip-y', '0px', '_gicleeNativeV2Slip');
        var line = divider.querySelector('.divider__line');
        if (line) {
          line.style.flexBasis = '';
          line.style.animation = 'none';
          line._gicleeNativeV2Scale = '';
        }
        fastStackDividersByPair[i].push(divider);
      });
    }
  }

  function setDividerScale(pairIndex, progress) {
    var dividers = fastStackDividersByPair[pairIndex] || [];
    for (var i = 0; i < dividers.length; i += 1) {
      var line = dividers[i].querySelector('.divider__line');
      if (!line) continue;
      var value = pairIndex === 0 ? '1.000' : progress.toFixed(3);
      setStyleIfChanged(line, '--home-stack-divider-scale', value, '_gicleeNativeV2Scale');
    }
  }

  function clearFastPair(pairIndex) {
    if (pairIndex < 0) return;
    var previous = fastStackSections[pairIndex];
    var next = fastStackSections[pairIndex + 1];
    toggleClassIfChanged(previous, 'is-stack-under-dim', false, '_gicleeNativeV2DimClass');
    removeStyleIfPresent(previous, '--home-stack-under-dim', '_gicleeNativeV2Dim');
    removeStyleIfPresent(next, '--home-stack-over-depth', '_gicleeNativeV2Depth');
    removeStyleIfPresent(next, '--home-stack-overlap-eased', '_gicleeNativeV2Overlap');
  }

  function applyFastPair(pairIndex, progress) {
    var previous = fastStackSections[pairIndex];
    var next = fastStackSections[pairIndex + 1];
    if (!previous || !next) return;
    var eased = easeInOutCubic(progress);
    var value = eased.toFixed(3);
    toggleClassIfChanged(previous, 'is-stack-under-dim', eased > 0.001, '_gicleeNativeV2DimClass');
    setStyleIfChanged(previous, '--home-stack-under-dim', value, '_gicleeNativeV2Dim');
    setStyleIfChanged(next, '--home-stack-over-depth', value, '_gicleeNativeV2Depth');
    setStyleIfChanged(next, '--home-stack-overlap-eased', value, '_gicleeNativeV2Overlap');
  }

  function pairProgress(pairIndex, scrollY) {
    var boardTop = fastStackPairStarts[pairIndex] - scrollY;
    if (scrollY <= STACK_SCROLL_REST || boardTop >= viewportHeight()) return 0;
    if (boardTop <= STACK_PIN_TOP) return 1;
    return smoothstep(
      (viewportHeight() - boardTop) / Math.max(viewportHeight() - STACK_PIN_TOP, 1)
    );
  }

  function renderFastStack(scrollValue) {
    if (!fastStackReady || fastStackSections.length < 2) return;
    fastStackRenderCount += 1;
    var scrollY = Number.isFinite(Number(scrollValue)) ? Number(scrollValue) : currentScrollY();
    var activePair = -1;
    var activeProgress = 0;

    for (var i = 0; i < fastStackPairStarts.length; i += 1) {
      var progress = pairProgress(i, scrollY);
      setDividerScale(i, progress);
      if (progress > 0.001 && progress < 0.999) {
        activePair = i;
        activeProgress = progress;
      }
    }

    if (fastStackActivePair !== activePair) {
      clearFastPair(fastStackActivePair);
      fastStackActivePair = activePair;
    }
    if (activePair >= 0) applyFastPair(activePair, activeProgress);
  }

  function scheduleFastStackRender(scrollValue) {
    fastStackPendingScroll = Number.isFinite(Number(scrollValue))
      ? Number(scrollValue)
      : currentScrollY();
    if (fastStackFrameId) return;
    fastStackFrameId = window.requestAnimationFrame(function () {
      fastStackFrameId = 0;
      renderFastStack(fastStackPendingScroll);
    });
  }

  function readHeaderHeight() {
    var header = document.getElementById('header-component');
    if (header) {
      fastStackLayoutReads += 1;
      return Math.max(0, header.getBoundingClientRect().height);
    }
    var raw = window.getComputedStyle(document.body).getPropertyValue('--header-group-height');
    var parsed = parseFloat(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 60;
  }

  function applyFastHeroMetrics() {
    var hero = fastStackSections[0];
    if (!hero) return;
    var headerHeight = readHeaderHeight();
    var headerHeightPx = headerHeight.toFixed(2) + 'px';
    setStyleIfChanged(hero, '--home-stack-hero-min-height', '100svh', '_gicleeNativeV2HeroHeight');
    setStyleIfChanged(hero, '--home-stack-hero-header-height', headerHeightPx, '_gicleeNativeV2HeaderHeight');
    setStyleIfChanged(hero, '--home-stack-hero-footer-height', headerHeightPx, '_gicleeNativeV2FooterHeight');
    setStyleIfChanged(hero, '--home-stack-hero-media-offset-top', '0px', '_gicleeNativeV2MediaOffset');
  }

  function measureFastStack() {
    if (!fastStackReady) return;
    applyFastHeroMetrics();
    fastStackPairStarts = [];
    for (var i = 0; i < fastStackSections.length - 1; i += 1) {
      fastStackPairStarts.push(documentTop(fastStackSections[i + 1]));
    }
    scheduleFastStackRender(currentScrollY());
  }

  function scheduleFastStackMeasure() {
    if (!fastStackReady || fastStackMeasureFrameId) return;
    fastStackMeasureFrameId = window.requestAnimationFrame(function () {
      fastStackMeasureFrameId = 0;
      measureFastStack();
    });
  }

  function restoreStackFlagProperty() {
    if (!stackFlagDescriptorInstalled) return;
    try {
      delete window.GICLEE_HOME_STACK;
      window.GICLEE_HOME_STACK = stackFlagValue;
    } catch (error) {
      window.GICLEE_HOME_STACK = stackFlagValue;
    }
    stackFlagDescriptorInstalled = false;
  }

  function prepareFastStackTakeover() {
    if (determineDisabledReason()) return;
    if (!stackFlagValue) return;
    root.dataset.gicleeHomeStackEngine = 'native-v2-fast-pending';

    try {
      Object.defineProperty(window, 'GICLEE_HOME_STACK', {
        configurable: true,
        enumerable: true,
        get: function () {
          var current = document.currentScript;
          if (
            current &&
            current.src &&
            /giclee-home-stack\.js(?:\?|$)/.test(current.src)
          ) {
            return false;
          }
          return stackFlagValue;
        },
        set: function (value) {
          stackFlagValue = !!value;
        },
      });
      stackFlagDescriptorInstalled = true;
    } catch (error) {
      /* Named-listener interception below remains the fallback. */
    }

    document.addEventListener = function (type, listener, options) {
      if (
        type === 'DOMContentLoaded' &&
        typeof listener === 'function' &&
        listener.name === 'initHomeStack'
      ) {
        legacyStackListenerIntercepted = true;
        return;
      }
      return nativeDocumentAddEventListener.call(document, type, listener, options);
    };

    nativeDocumentAddEventListener.call(
      document,
      'DOMContentLoaded',
      function () {
        window.setTimeout(function () {
          document.addEventListener = nativeDocumentAddEventListener;
          restoreStackFlagProperty();
        }, 0);
      },
      { once: true }
    );
  }

  function initFastStack() {
    if (fastStackReady || !stackFlagValue) return;
    var map = window.GICLEE_HOME_SECTIONS;
    if (!map || typeof map !== 'object') {
      fastStackInitAttempts += 1;
      if (fastStackInitAttempts < 40) window.setTimeout(initFastStack, 50);
      return;
    }

    fastStackSections = [];
    STACK_HOOKS.forEach(function (hook, index) {
      var section = findStackSection(map[hook]);
      if (!section) return;
      section.setAttribute('data-giclee-home-stack', String(index + 1));
      setStyleIfChanged(section, '--home-stack-slip-y', '0px', '_gicleeNativeV2Slip');
      fastStackSections.push(section);
    });

    if (fastStackSections.length < 2) {
      fastStackInitAttempts += 1;
      if (fastStackInitAttempts < 40) window.setTimeout(initFastStack, 50);
      else root.classList.add('giclee-home-stack-ready');
      return;
    }

    restoreStackFlagProperty();
    ensureHeroScrollCue(fastStackSections[0]);
    tagFastStackDividers();
    root.classList.add('giclee-home-stack');
    root.dataset.gicleeHomeStackEngine = 'native-v2-fast-active-pair';
    fastStackReady = true;
    measureFastStack();

    window.addEventListener('resize', scheduleFastStackMeasure, { passive: true });
    window.addEventListener('orientationchange', scheduleFastStackMeasure, { passive: true });
    window.addEventListener('pageshow', scheduleFastStackMeasure, { passive: true });
    window.addEventListener('load', scheduleFastStackMeasure, { once: true });
    document.addEventListener('shopify:section:load', scheduleFastStackMeasure);

    var main = document.getElementById('MainContent');
    if (main && typeof ResizeObserver === 'function') {
      fastStackResizeObserver = new ResizeObserver(scheduleFastStackMeasure);
      fastStackResizeObserver.observe(main);
    }

    window.setTimeout(scheduleFastStackMeasure, 0);
    window.setTimeout(scheduleFastStackMeasure, 140);
    window.setTimeout(scheduleFastStackMeasure, 500);

    root.classList.add('giclee-home-stack-ready');
    window.dispatchEvent(new CustomEvent('giclee:home-stack-ready'));

    window.GICLEE_HOME_STACK_PERFORMANCE_STATUS = function () {
      var dividerCount = fastStackDividersByPair.reduce(function (sum, list) {
        return sum + list.length;
      }, 0);
      return {
        ready: fastStackReady,
        engine: root.dataset.gicleeHomeStackEngine || '',
        activePair: fastStackActivePair,
        sectionCount: fastStackSections.length,
        pairCount: fastStackPairStarts.length,
        dividerCount: dividerCount,
        cachedGeometry: true,
        activePairOnly: true,
        independentMotionLoop: false,
        legacyListenerIntercepted: legacyStackListenerIntercepted,
        renderCount: fastStackRenderCount,
        styleWrites: fastStackStyleWrites,
        layoutReads: fastStackLayoutReads,
      };
    };
  }

  function clearAnimationClass() {
    root.classList.remove('giclee-native-v2-scrolling');
    root.classList.remove('giclee-home-stack-scrolling');
  }

  function cancelAnimation(syncTarget) {
    if (frameId) window.cancelAnimationFrame(frameId);
    frameId = 0;
    animationActive = false;
    lastFrameTime = 0;
    if (syncTarget !== false) targetScrollY = currentScrollY();
    clearAnimationClass();
    scheduleFastStackRender(targetScrollY);
  }

  function scheduleFrame() {
    if (!frameId) frameId = window.requestAnimationFrame(tick);
  }

  function writeScrollY(value) {
    window.scrollTo(0, value);
    scheduleFastStackRender(value);
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

    if (!animationActive) animationCount += 1;
    animationActive = true;
    root.classList.add('giclee-native-v2-scrolling');
    root.classList.add('giclee-home-stack-scrolling');
    root.setAttribute('data-giclee-native-v2-direction', delta > 0 ? 'down' : 'up');
    scheduleFrame();
  }

  function onNativeScroll() {
    if (!enabled) return;

    /* Scroll events emitted by our own window.scrollTo() are part of the active easing. */
    if (animationActive) {
      scheduleFastStackRender(currentScrollY());
      return;
    }

    var current = currentScrollY();
    if (Math.abs(targetScrollY - current) > 1) externalSyncCount += 1;
    targetScrollY = current;
    scheduleFastStackRender(current);
  }

  function resetPosition() {
    cancelAnimation(true);
    scheduleFastStackMeasure();
  }

  function summarizeSamples(values) {
    if (!values.length) {
      return {
        sampleCount: 0,
        fps: 0,
        averageFrameMs: 0,
        p95FrameMs: 0,
        longFramesOver25Ms: 0,
        longFramesOver40Ms: 0,
      };
    }
    var sorted = values.slice().sort(function (a, b) { return a - b; });
    var total = values.reduce(function (sum, value) { return sum + value; }, 0);
    var duration = Math.max(1, total);
    var p95Index = Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95));
    return {
      sampleCount: values.length,
      fps: Math.round((values.length * 1000 / duration) * 10) / 10,
      averageFrameMs: Math.round((total / values.length) * 100) / 100,
      p95FrameMs: Math.round(sorted[p95Index] * 100) / 100,
      longFramesOver25Ms: values.filter(function (value) { return value > 25; }).length,
      longFramesOver40Ms: values.filter(function (value) { return value > 40; }).length,
    };
  }

  function installFrameMonitor() {
    window.GICLEE_FRAME_MONITOR = function (durationMs) {
      var duration = Math.max(1000, Math.min(30000, Number(durationMs) || 5000));
      return new Promise(function (resolve) {
        var startedAt = performance.now();
        var lastAt = startedAt;
        var samples = [];
        var upperSamples = [];
        var lowerSamples = [];

        function finish(now) {
          var elapsed = Math.max(1, now - startedAt);
          var summary = summarizeSamples(samples);
          var result = {
            durationMs: Math.round(elapsed),
            sampleCount: summary.sampleCount,
            fps: Math.round((samples.length * 1000 / elapsed) * 10) / 10,
            averageFrameMs: summary.averageFrameMs,
            p95FrameMs: summary.p95FrameMs,
            longFramesOver25Ms: summary.longFramesOver25Ms,
            longFramesOver40Ms: summary.longFramesOver40Ms,
            mode: 'native-v2',
            clock: 'native-v2-wheel-raf',
            stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
            zones: {
              upperHalf: summarizeSamples(upperSamples),
              lowerHalf: summarizeSamples(lowerSamples),
            },
          };
          console.log('[giclee frame monitor]', result);
          resolve(result);
        }

        function frame(now) {
          var frameMs = now - lastAt;
          samples.push(frameMs);
          if (currentScrollY() < maxScrollY() * 0.5) upperSamples.push(frameMs);
          else lowerSamples.push(frameMs);
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
        profile: 'wheel-cinematic-nous-v3-fast-stack',
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
        animationCount: animationCount,
        frameCount: frameCount,
        lastWheelDelta: Math.round(lastWheelDelta * 10) / 10,
        peakTargetLeadPx: Math.round(peakTargetLead * 10) / 10,
        running: animationActive || !!frameId,
        stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
        stackReady: fastStackReady,
        activeStackPair: fastStackActivePair,
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
        performanceProfile: fastStackReady,
        wheelSmoothing: true,
        clock: 'native-v2-wheel-raf',
        stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native-v2',
      });
    };
  }

  function boot() {
    disabledReason = determineDisabledReason();
    if (disabledReason) {
      document.addEventListener = nativeDocumentAddEventListener;
      restoreStackFlagProperty();
      publishStatus();
      return;
    }

    enabled = true;
    targetScrollY = currentScrollY();
    root.classList.add('giclee-native-v2');
    root.setAttribute('data-giclee-smooth-scroll', 'native-v2');
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    root.dataset.gicleeHomeStackEngine = 'native-v2-fast-pending';

    initFastStack();

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

    installFrameMonitor();
    publishStatus();
    window.GICLEE_NATIVE_V2_STOP = resetPosition;
    window.dispatchEvent(
      new CustomEvent('giclee:native-v2-ready', {
        detail: {
          profile: 'wheel-cinematic-nous-v3-fast-stack',
          clock: 'native-v2-wheel-raf',
          followTauMs: FOLLOW_TAU_MS,
          stackEngine: root.dataset.gicleeHomeStackEngine,
        },
      })
    );
  }

  prepareFastStackTakeover();

  if (document.readyState === 'loading') {
    nativeDocumentAddEventListener.call(document, 'DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();