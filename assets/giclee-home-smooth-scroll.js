/* Homepage smooth scrolling tuned for the cinematic Giclee Art flow. */
(function () {
  'use strict';

  var root = document.documentElement;
  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var LERP = 0.11;
  var WHEEL_MULTIPLIER = 1;
  var PERFORMANCE_STYLE_ID = 'giclee-lenis-performance-style';
  var instance = null;
  var disabledReason = '';
  var classObserver = null;
  var lastVelocityCss = '';

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
  var stackTakeoverRequested = false;
  var stackFlagValue = !!window.GICLEE_HOME_STACK;
  var stackFlagDescriptorInstalled = false;
  var nativeDocumentAddEventListener = document.addEventListener;
  var legacyStackListenerIntercepted = false;
  var fastStackReady = false;
  var fastStackInitAttempts = 0;
  var fastStackSections = [];
  var fastStackPairStarts = [];
  var fastStackDividers = [];
  var fastStackActivePair = -1;
  var fastStackPendingScroll = 0;
  var fastStackFrameId = 0;
  var fastStackMeasureFrameId = 0;
  var fastStackResizeObserver = null;
  var fastStackRenderCount = 0;
  var fastStackStyleWrites = 0;
  var fastStackLayoutReads = 0;

  var PREVENT_SELECTOR = [
    '[data-lenis-prevent]',
    'dialog',
    '[role="dialog"]',
    '.drawer',
    '.menu-drawer',
    '.search-modal',
    '.quick-add-modal',
    '.cart-drawer',
    '.predictive-search',
    '.facets-drawer',
  ].join(',');

  function configuredMode() {
    return String(CONFIG.smoothScrollMode || 'native').toLowerCase() === 'lenis'
      ? 'lenis'
      : 'native';
  }

  function queryDisablesSmoothScroll() {
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

  function determineDisabledReason() {
    if (queryDisablesSmoothScroll()) return 'query';
    if (configuredMode() === 'native') return 'configuration';
    if (reducedMotionRequested()) return 'reduced-motion';
    if (designModeActive()) return 'shopify-design-mode';
    if (typeof window.Lenis !== 'function') return 'lenis-unavailable';
    return '';
  }

  function preventSmoothing(node) {
    if (!node || !(node instanceof Element)) return false;
    return !!node.closest(PREVENT_SELECTOR);
  }

  function pageInteractionLocked() {
    return (
      root.classList.contains('splash-pending') ||
      root.classList.contains('splash-reveal') ||
      root.classList.contains('curtain-pending')
    );
  }

  function syncPageLock() {
    if (!instance) return;
    if (pageInteractionLocked()) instance.stop();
    else instance.start();
  }

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

  function toggleClassIfChanged(element, className, enabled, cacheKey) {
    if (!element || element[cacheKey] === enabled) return;
    element[cacheKey] = enabled;
    element.classList.toggle(className, enabled);
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
    fastStackDividers = [];
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
        divider._gicleeFastPairIndex = -1;
        var isScrollDivider = !isLast && dividerIndex === dividers.length - 1;
        if (!isScrollDivider) return;
        divider.classList.add('giclee-home-stack-divider--scroll');
        divider._gicleeFastPairIndex = i;
        setStyleIfChanged(divider, '--home-stack-slip-y', '0px', '_gicleeFastSlip');
        var line = divider.querySelector('.divider__line');
        if (line) {
          line.style.flexBasis = '';
          line.style.animation = 'none';
          line._gicleeFastScale = '';
        }
        fastStackDividers.push(divider);
      });
    }
  }

  function setDividerScale(pairIndex, progress) {
    fastStackDividers.forEach(function (divider) {
      if (divider._gicleeFastPairIndex !== pairIndex) return;
      var line = divider.querySelector('.divider__line');
      if (!line) return;
      var value = pairIndex === 0 ? '1.000' : progress.toFixed(3);
      setStyleIfChanged(line, '--home-stack-divider-scale', value, '_gicleeFastScale');
    });
  }

  function clearFastPair(pairIndex) {
    if (pairIndex < 0) return;
    var previous = fastStackSections[pairIndex];
    var next = fastStackSections[pairIndex + 1];
    toggleClassIfChanged(previous, 'is-stack-under-dim', false, '_gicleeFastDimClass');
    removeStyleIfPresent(previous, '--home-stack-under-dim', '_gicleeFastDim');
    removeStyleIfPresent(next, '--home-stack-over-depth', '_gicleeFastDepth');
    removeStyleIfPresent(next, '--home-stack-overlap-eased', '_gicleeFastOverlap');
  }

  function applyFastPair(pairIndex, progress) {
    var previous = fastStackSections[pairIndex];
    var next = fastStackSections[pairIndex + 1];
    if (!previous || !next) return;
    var eased = easeInOutCubic(progress);
    var value = eased.toFixed(3);
    toggleClassIfChanged(previous, 'is-stack-under-dim', eased > 0.001, '_gicleeFastDimClass');
    setStyleIfChanged(previous, '--home-stack-under-dim', value, '_gicleeFastDim');
    setStyleIfChanged(next, '--home-stack-over-depth', value, '_gicleeFastDepth');
    setStyleIfChanged(next, '--home-stack-overlap-eased', value, '_gicleeFastOverlap');
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
    setStyleIfChanged(hero, '--home-stack-hero-min-height', '100svh', '_gicleeFastHeroHeight');
    setStyleIfChanged(hero, '--home-stack-hero-header-height', headerHeightPx, '_gicleeFastHeaderHeight');
    setStyleIfChanged(hero, '--home-stack-hero-footer-height', headerHeightPx, '_gicleeFastFooterHeight');
    setStyleIfChanged(hero, '--home-stack-hero-media-offset-top', '0px', '_gicleeFastMediaOffset');
  }

  function measureFastStack() {
    if (!fastStackReady) return;
    applyFastHeroMetrics();
    fastStackPairStarts = [];
    for (var i = 0; i < fastStackSections.length - 1; i += 1) {
      fastStackPairStarts.push(documentTop(fastStackSections[i + 1]));
    }
    scheduleFastStackRender(instance ? instance.scroll : currentScrollY());
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
    stackTakeoverRequested = true;
    root.dataset.gicleeHomeStackEngine = 'lenis-fast-pending';

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
      /* The named DOMContentLoaded listener interceptor remains as a fallback. */
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
    if (!stackTakeoverRequested || fastStackReady) return;
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
      setStyleIfChanged(section, '--home-stack-slip-y', '0px', '_gicleeFastSlip');
      fastStackSections.push(section);
    });

    if (fastStackSections.length < 2) {
      fastStackInitAttempts += 1;
      if (fastStackInitAttempts < 40) {
        window.setTimeout(initFastStack, 50);
      } else {
        root.classList.add('giclee-home-stack-ready');
      }
      return;
    }

    restoreStackFlagProperty();
    ensureHeroScrollCue(fastStackSections[0]);
    tagFastStackDividers();
    root.classList.add('giclee-home-stack');
    root.dataset.gicleeHomeStackEngine = 'lenis-fast-active-pair';
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

    root.classList.add('giclee-home-stack-ready');
    window.dispatchEvent(new CustomEvent('giclee:home-stack-ready'));

    window.GICLEE_HOME_STACK_PERFORMANCE_STATUS = function () {
      return {
        ready: fastStackReady,
        engine: root.dataset.gicleeHomeStackEngine || '',
        activePair: fastStackActivePair,
        sectionCount: fastStackSections.length,
        pairCount: fastStackPairStarts.length,
        dividerCount: fastStackDividers.length,
        cachedGeometry: true,
        activePairOnly: true,
        independentMotionLoop: false,
        legacyListenerIntercepted: legacyStackListenerIntercepted,
        renderCount: fastStackRenderCount,
        styleWrites: fastStackStyleWrites,
        layoutReads: fastStackLayoutReads,
      };
    };

    window.GICLEE_HOME_STACK_DEBUG = function () {
      var scrollY = instance ? instance.scroll : currentScrollY();
      return {
        engine: root.dataset.gicleeHomeStackEngine || '',
        scrollY: scrollY,
        activePair: fastStackActivePair,
        pairStarts: fastStackPairStarts.slice(),
        pairProgress: fastStackPairStarts.map(function (_start, index) {
          return pairProgress(index, scrollY);
        }),
      };
    };
  }

  function scheduleFastStackInit() {
    var start = function () {
      window.setTimeout(initFastStack, 0);
    };
    if (document.readyState === 'complete') start();
    else nativeDocumentAddEventListener.call(document, 'DOMContentLoaded', start, { once: true });
  }

  function installPerformanceStyles() {
    if (document.getElementById(PERFORMANCE_STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = PERFORMANCE_STYLE_ID;
    style.textContent = [
      'html.giclee-lenis-performance.giclee-home-stack .shopify-section[data-giclee-home-stack] { --home-stack-slip-y: 0px !important; }',
      'html.giclee-lenis-performance.giclee-home-stack #header-component.giclee-header-scroll-fade { transition: none !important; }',
      'html.giclee-lenis-performance .giclee-prehero-reveal__copy { will-change: transform !important; }',
      'html.giclee-lenis-performance .giclee-prehero-reveal__copy-word { will-change: opacity; }',
      'html.giclee-lenis-performance .giclee-home-studio-reveal__heading, html.giclee-lenis-performance .giclee-home-studio-reveal__paragraph { filter: none !important; transition-property: opacity, transform !important; }',
      'html.giclee-lenis-performance .giclee-home-studio-reveal__bg .background-image-container, html.giclee-lenis-performance .giclee-home-studio-reveal__bg .background-image-container img, html.giclee-lenis-performance .giclee-home-studio-reveal__bg video-background-component video { filter: none !important; transition-property: opacity, transform !important; }',
      'html.giclee-lenis-performance .giclee-home-studio-reveal__card { transition-property: opacity, transform !important; }',
    ].join('\n');
    document.head.appendChild(style);
  }

  function disableCompetingSectionScroll() {
    var api = window.GICLEE_HOME_SECTION_SCROLL;
    if (api && typeof api.destroy === 'function') api.destroy();
    root.dataset.gicleeHomeSectionScroll = 'lenis-bypass';
  }

  function installPerformanceProfile() {
    root.classList.add('giclee-lenis-performance');
    installPerformanceStyles();
    window.setTimeout(disableCompetingSectionScroll, 0);
    window.addEventListener('load', disableCompetingSectionScroll, { once: true });
    window.addEventListener('giclee:home-stack-ready', disableCompetingSectionScroll, {
      passive: true,
    });
    document.addEventListener('shopify:section:load', function () {
      window.setTimeout(disableCompetingSectionScroll, 0);
    });
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
            mode: configuredMode(),
            clock: instance ? 'lenis-auto-raf' : 'native',
            stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native',
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
    window.GICLEE_SMOOTH_SCROLL_STATUS = function () {
      return {
        ready: !!instance,
        active: root.getAttribute('data-giclee-smooth-scroll') === 'active',
        mode: configuredMode(),
        disabledReason: disabledReason,
        performanceProfile: root.classList.contains('giclee-lenis-performance'),
        sectionScrollBypassed:
          root.dataset.gicleeHomeSectionScroll === 'lenis-bypass',
        clock: instance ? 'lenis-auto-raf' : 'native',
        stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native',
        lerp: LERP,
        wheelMultiplier: WHEEL_MULTIPLIER,
        scroll: instance ? instance.scroll : window.scrollY,
        actualScroll: instance ? instance.actualScroll : window.scrollY,
        targetScroll: instance ? instance.targetScroll : window.scrollY,
        velocity: instance ? instance.velocity : 0,
        direction: instance ? instance.direction : 0,
        isScrolling: instance ? instance.isScrolling : false,
        stopped: instance ? instance.isStopped : false,
      };
    };
  }

  function markDisabled(reason) {
    disabledReason = reason;
    root.setAttribute('data-giclee-smooth-scroll', 'disabled');
    root.setAttribute('data-giclee-smooth-scroll-reason', reason);
    installFrameMonitor();
    publishStatus();
  }

  function boot() {
    disabledReason = determineDisabledReason();
    if (disabledReason) {
      markDisabled(disabledReason);
      return;
    }

    instance = new window.Lenis({
      autoRaf: true,
      autoResize: true,
      autoToggle: true,
      anchors: true,
      smoothWheel: true,
      syncTouch: false,
      lerp: LERP,
      wheelMultiplier: WHEEL_MULTIPLIER,
      stopInertiaOnNavigate: true,
      overscroll: true,
      prevent: preventSmoothing,
    });

    window.GICLEE_LENIS = instance;
    root.setAttribute('data-giclee-smooth-scroll', 'active');
    root.removeAttribute('data-giclee-smooth-scroll-reason');
    installPerformanceProfile();
    installFrameMonitor();
    scheduleFastStackInit();

    instance.on('scroll', function (lenis) {
      var velocity = Number(lenis.velocity) || 0;
      var velocityCss = velocity.toFixed(2);
      if (velocityCss !== lastVelocityCss) {
        lastVelocityCss = velocityCss;
        root.style.setProperty('--giclee-scroll-velocity', velocityCss);
      }
      scheduleFastStackRender(lenis.scroll);
    });

    classObserver = new MutationObserver(syncPageLock);
    classObserver.observe(root, { attributes: true, attributeFilter: ['class'] });
    syncPageLock();

    document.addEventListener('shopify:section:load', function () {
      if (instance) instance.resize();
    });
    window.addEventListener('pageshow', function () {
      if (!instance) return;
      instance.resize();
      syncPageLock();
      disableCompetingSectionScroll();
      scheduleFastStackMeasure();
    });

    publishStatus();
    window.dispatchEvent(
      new CustomEvent('giclee:smooth-scroll-ready', {
        detail: {
          lerp: LERP,
          wheelMultiplier: WHEEL_MULTIPLIER,
          clock: 'lenis-auto-raf',
          stackEngine: 'lenis-fast-active-pair',
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
