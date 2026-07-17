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
  var clockFrameId = 0;
  var lastVelocityCss = '';

  var lenisStackOriginalFlag = false;
  var lenisStackTakeoverPrepared = false;
  var lenisStackReady = false;
  var lenisStackInitAttempts = 0;
  var lenisStackEls = [];
  var lenisStackPairStarts = [];
  var lenisStackDividers = [];
  var lenisStackHeader = null;
  var lenisStackHero = null;
  var lenisStackHeroFadeAnchor = 120;
  var lenisStackScrollTimer = 0;
  var lenisStackResizeFrame = 0;
  var lenisStackResizeObserver = null;
  var LENIS_STACK_HOOKS = [
    'hero',
    'intro',
    'restoration',
    'color-correction',
    'potential',
    'see-difference',
  ];
  var LENIS_STACK_EPSILON = 0.001;
  var LENIS_STACK_TOP_EPSILON = 16;
  var LENIS_STACK_SCROLL_REST = 4;

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

  function documentTop(element) {
    var top = 0;
    var node = element;
    while (node) {
      top += Number(node.offsetTop) || 0;
      node = node.offsetParent;
    }
    return top;
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

  function setStyleIfChanged(element, property, value, cacheKey) {
    if (!element) return;
    if (element[cacheKey] === value) return;
    element[cacheKey] = value;
    element.style.setProperty(property, value);
  }

  function clearStyleIfPresent(element, property, cacheKey) {
    if (!element || element[cacheKey] === '') return;
    element[cacheKey] = '';
    element.style.removeProperty(property);
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

  function readHeaderGroupHeightPx() {
    var raw = getComputedStyle(document.body).getPropertyValue('--header-group-height');
    var px = parseFloat(raw);
    return Number.isFinite(px) && px > 0 ? px : 0;
  }

  function measureHeaderHeightPx() {
    var header = document.getElementById('header-component');
    if (header) return Math.max(0, header.getBoundingClientRect().height);
    var fallback = readHeaderGroupHeightPx();
    return fallback > 0 ? fallback : 60;
  }

  function applyLenisHeroLayoutMetrics() {
    if (!lenisStackHero) return;
    var headerHeight = measureHeaderHeightPx();
    var heroTopPx = currentScrollY() <= LENIS_STACK_SCROLL_REST
      ? Math.max(0, lenisStackHero.getBoundingClientRect().top)
      : document.querySelector('#header-component[transparent]')
        ? 0
        : readHeaderGroupHeightPx();
    var minHeight = heroTopPx <= LENIS_STACK_TOP_EPSILON
      ? '100svh'
      : 'calc(100svh - ' + heroTopPx.toFixed(2) + 'px)';
    var headerHeightPx = headerHeight.toFixed(2) + 'px';
    var mediaOffsetTopPx = heroTopPx <= LENIS_STACK_TOP_EPSILON
      ? headerHeightPx
      : '0px';
    var key = minHeight + '|' + headerHeightPx + '|' + mediaOffsetTopPx;
    if (lenisStackHero._gicleeLenisHeroLayoutKey === key) return;
    lenisStackHero._gicleeLenisHeroLayoutKey = key;
    lenisStackHero.style.setProperty('--home-stack-hero-min-height', minHeight);
    lenisStackHero.style.setProperty('--home-stack-hero-header-height', headerHeightPx);
    lenisStackHero.style.setProperty('--home-stack-hero-footer-height', headerHeightPx);
    lenisStackHero.style.setProperty('--home-stack-hero-media-offset-top', mediaOffsetTopPx);
  }

  function tagLenisStackDividers() {
    lenisStackDividers = [];
    for (var i = 0; i < lenisStackEls.length; i += 1) {
      var isLast = i === lenisStackEls.length - 1;
      var layer = isLast ? i + 1 : i + 2;
      var stopAt = isLast ? null : lenisStackEls[i + 1];
      var dividers = [];
      var node = lenisStackEls[i].nextElementSibling;
      while (node && node !== stopAt) {
        if (isDividerSection(node)) dividers.push(node);
        node = node.nextElementSibling;
      }

      dividers.forEach(function (divider, dividerIndex) {
        divider.setAttribute('data-giclee-home-stack', String(layer));
        divider.classList.add('giclee-home-stack-divider');
        divider.classList.remove('giclee-home-stack-divider--scroll');
        divider._gicleeLenisPairIndex = -1;
        var isScrollDivider = !isLast && dividerIndex === dividers.length - 1;
        if (!isScrollDivider) return;
        divider.classList.add('giclee-home-stack-divider--scroll');
        divider._gicleeLenisPairIndex = i;
        divider.style.setProperty('--home-stack-slip-y', '0px');
        var line = divider.querySelector('.divider__line');
        if (line) {
          line.style.flexBasis = '';
          line.style.animation = 'none';
          line._gicleeLenisScale = '';
        }
        lenisStackDividers.push(divider);
      });
    }
  }

  function pairProgressFromTop(boardTop, scrollY) {
    var vh = viewportHeight();
    if (boardTop >= vh || scrollY <= LENIS_STACK_SCROLL_REST) return 0;
    if (boardTop <= LENIS_STACK_TOP_EPSILON) return 1;
    return smoothstep(
      (vh - boardTop) / Math.max(vh - LENIS_STACK_TOP_EPSILON, 1)
    );
  }

  function applyLenisPair(index, progress) {
    var previous = lenisStackEls[index];
    var next = lenisStackEls[index + 1];
    if (!previous || !next) return;

    var eased = easeInOutCubic(progress);
    var value = eased.toFixed(4);

    if (eased > LENIS_STACK_EPSILON) {
      setStyleIfChanged(previous, '--home-stack-under-dim', value, '_gicleeLenisUnderDim');
      previous.classList.add('is-stack-under-dim');
      setStyleIfChanged(next, '--home-stack-over-depth', value, '_gicleeLenisOverDepth');
      setStyleIfChanged(next, '--home-stack-overlap-eased', value, '_gicleeLenisOverlap');
    } else {
      previous.classList.remove('is-stack-under-dim');
      clearStyleIfPresent(previous, '--home-stack-under-dim', '_gicleeLenisUnderDim');
      clearStyleIfPresent(next, '--home-stack-over-depth', '_gicleeLenisOverDepth');
      clearStyleIfPresent(next, '--home-stack-overlap-eased', '_gicleeLenisOverlap');
    }

    setStyleIfChanged(next, '--home-stack-slip-y', '0px', '_gicleeLenisSlip');

    lenisStackDividers.forEach(function (divider) {
      if (divider._gicleeLenisPairIndex !== index) return;
      setStyleIfChanged(divider, '--home-stack-slip-y', '0px', '_gicleeLenisSlip');
      var line = divider.querySelector('.divider__line');
      if (!line) return;
      var scale = index === 0 ? '1.000' : eased.toFixed(3);
      setStyleIfChanged(line, '--home-stack-divider-scale', scale, '_gicleeLenisScale');
    });
  }

  function updateLenisHeader(scrollY) {
    if (!lenisStackHeader) return;
    var dimmed = 0.1;
    var opacity = 1;
    if (scrollY > 0) {
      var anchor = Math.max(lenisStackHeroFadeAnchor, 80);
      var t = Math.min(1, scrollY / anchor);
      t = Math.pow(t, 0.35);
      if (scrollY <= anchor) {
        opacity = 1 - (1 - dimmed) * t;
      } else {
        var tailRange = Math.max(anchor * 0.32, 28);
        opacity = Math.max(
          0,
          dimmed * (1 - Math.min(1, (scrollY - anchor) / tailRange))
        );
      }
    }
    lenisStackHeader.classList.add('giclee-header-scroll-fade');
    setStyleIfChanged(
      lenisStackHeader,
      '--gab-header-fade-opacity',
      opacity.toFixed(3),
      '_gicleeLenisHeaderOpacity'
    );
    lenisStackHeader.style.pointerEvents = opacity < 0.12 ? 'none' : '';
  }

  function markLenisStackScrolling() {
    root.classList.add('giclee-home-stack-scrolling');
    window.clearTimeout(lenisStackScrollTimer);
    lenisStackScrollTimer = window.setTimeout(function () {
      root.classList.remove('giclee-home-stack-scrolling');
    }, 150);
  }

  function updateLenisStack(scrollValue) {
    if (!lenisStackReady || lenisStackEls.length < 2) return;
    var scrollY = Number.isFinite(Number(scrollValue))
      ? Number(scrollValue)
      : currentScrollY();
    markLenisStackScrolling();
    updateLenisHeader(scrollY);
    for (var i = 0; i < lenisStackEls.length - 1; i += 1) {
      var boardTop = lenisStackPairStarts[i] - scrollY;
      applyLenisPair(i, pairProgressFromTop(boardTop, scrollY));
    }
  }

  function measureLenisStackLayout() {
    if (!lenisStackReady) return;
    applyLenisHeroLayoutMetrics();
    lenisStackPairStarts = [];
    for (var i = 0; i < lenisStackEls.length - 1; i += 1) {
      lenisStackPairStarts[i] = documentTop(lenisStackEls[i + 1]);
    }
    var heroBottom = documentTop(lenisStackHero) + lenisStackHero.offsetHeight;
    lenisStackHeroFadeAnchor = Math.max(heroBottom * 0.22, 80);
    updateLenisStack(instance ? instance.scroll : currentScrollY());
  }

  function scheduleLenisStackMeasure() {
    if (!lenisStackReady || lenisStackResizeFrame) return;
    lenisStackResizeFrame = window.requestAnimationFrame(function () {
      lenisStackResizeFrame = 0;
      measureLenisStackLayout();
    });
  }

  function restoreStackFeatureFlag() {
    window.setTimeout(function () {
      if (lenisStackOriginalFlag) window.GICLEE_HOME_STACK = true;
    }, 0);
  }

  function initLenisStack() {
    if (lenisStackReady || !lenisStackOriginalFlag) {
      restoreStackFeatureFlag();
      return;
    }

    var map = window.GICLEE_HOME_SECTIONS;
    if (!map || typeof map !== 'object') {
      lenisStackInitAttempts += 1;
      if (lenisStackInitAttempts < 20) {
        window.setTimeout(initLenisStack, 50);
      } else {
        restoreStackFeatureFlag();
      }
      return;
    }

    lenisStackEls = [];
    LENIS_STACK_HOOKS.forEach(function (hook, index) {
      var element = findStackSection(map[hook]);
      if (!element) return;
      element.setAttribute('data-giclee-home-stack', String(index + 1));
      element.style.setProperty('--home-stack-slip-y', '0px');
      lenisStackEls.push(element);
    });

    if (lenisStackEls.length < 2) {
      restoreStackFeatureFlag();
      return;
    }

    lenisStackHero = lenisStackEls[0];
    lenisStackHeader = document.getElementById('header-component');
    ensureHeroScrollCue(lenisStackHero);
    root.classList.add('giclee-home-stack');
    root.dataset.gicleeHomeStackEngine = 'lenis-single-clock';
    tagLenisStackDividers();
    lenisStackReady = true;
    measureLenisStackLayout();

    window.addEventListener('resize', scheduleLenisStackMeasure, { passive: true });
    window.addEventListener('orientationchange', scheduleLenisStackMeasure, { passive: true });
    window.addEventListener('pageshow', scheduleLenisStackMeasure, { passive: true });
    window.addEventListener('giclee:splash-done', scheduleLenisStackMeasure, { passive: true });
    document.addEventListener('shopify:section:load', scheduleLenisStackMeasure);

    var main = document.getElementById('MainContent');
    if (main && typeof ResizeObserver === 'function') {
      lenisStackResizeObserver = new ResizeObserver(scheduleLenisStackMeasure);
      lenisStackResizeObserver.observe(main);
    }

    root.classList.add('giclee-home-stack-ready');
    window.dispatchEvent(new CustomEvent('giclee:home-stack-ready'));
    restoreStackFeatureFlag();

    window.GICLEE_HOME_STACK_PERFORMANCE_STATUS = function () {
      return {
        ready: lenisStackReady,
        engine: root.dataset.gicleeHomeStackEngine || '',
        sectionCount: lenisStackEls.length,
        pairCount: lenisStackPairStarts.length,
        dividerCount: lenisStackDividers.length,
        heroFadeAnchor: lenisStackHeroFadeAnchor,
        independentMotionLoop: false,
        cachedGeometry: true,
      };
    };
  }

  function prepareLenisStackTakeover() {
    if (lenisStackTakeoverPrepared) return;
    lenisStackTakeoverPrepared = true;
    lenisStackOriginalFlag = !!window.GICLEE_HOME_STACK;
    if (!lenisStackOriginalFlag) return;

    /* The legacy stack deferred script executes later in document order. Keeping this
     * flag false until it has executed prevents its independent RAF/lerp engine from
     * registering. The optimized stack is initialized after all deferred scripts. */
    window.GICLEE_HOME_STACK = false;
    root.dataset.gicleeHomeStackEngine = 'lenis-single-clock-pending';

    if (document.readyState === 'complete') {
      initLenisStack();
    } else {
      document.addEventListener('DOMContentLoaded', initLenisStack, { once: true });
    }
  }

  function installPerformanceStyles() {
    if (document.getElementById(PERFORMANCE_STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = PERFORMANCE_STYLE_ID;
    style.textContent = [
      'html.giclee-lenis-performance.giclee-home-stack .shopify-section[data-giclee-home-stack] { --home-stack-slip-y: 0px !important; }',
      'html.giclee-lenis-performance.giclee-home-stack #header-component.giclee-header-scroll-fade { transition: none !important; }',
      'html.giclee-lenis-performance .giclee-prehero-reveal__copy { filter: none !important; will-change: transform !important; }',
      'html.giclee-lenis-performance .giclee-prehero-reveal__copy-line { will-change: transform, opacity; }',
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
            clock: instance ? 'manual-single-raf' : 'native',
            stackEngine: root.dataset.gicleeHomeStackEngine || 'legacy-native',
          };
          console.log('[giclee frame monitor]', result);
          resolve(result);
        }

        function frame(now) {
          samples.push(now - lastAt);
          lastAt = now;
          if (now - startedAt < duration) {
            window.requestAnimationFrame(frame);
          } else {
            finish(now);
          }
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
        clock: instance ? 'manual-single-raf' : 'native',
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

  function startSingleAnimationClock() {
    if (!instance || clockFrameId) return;
    function frame(time) {
      if (!instance) {
        clockFrameId = 0;
        return;
      }
      instance.raf(time);
      clockFrameId = window.requestAnimationFrame(frame);
    }
    clockFrameId = window.requestAnimationFrame(frame);
  }

  function boot() {
    disabledReason = determineDisabledReason();
    if (disabledReason) {
      markDisabled(disabledReason);
      return;
    }

    prepareLenisStackTakeover();

    instance = new window.Lenis({
      autoRaf: false,
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

    instance.on('scroll', function (lenis) {
      var velocity = Number(lenis.velocity) || 0;
      var velocityCss = velocity.toFixed(4);
      if (velocityCss !== lastVelocityCss) {
        lastVelocityCss = velocityCss;
        root.style.setProperty('--giclee-scroll-velocity', velocityCss);
      }
      updateLenisStack(lenis.scroll);
      window.dispatchEvent(
        new CustomEvent('giclee:smooth-scroll', {
          detail: {
            scroll: lenis.scroll,
            progress: lenis.progress,
            velocity: velocity,
            direction: lenis.direction,
            timestamp: performance.now(),
          },
        })
      );
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
      scheduleLenisStackMeasure();
    });

    startSingleAnimationClock();
    publishStatus();
    window.dispatchEvent(
      new CustomEvent('giclee:smooth-scroll-ready', {
        detail: {
          lerp: LERP,
          wheelMultiplier: WHEEL_MULTIPLIER,
          clock: 'manual-single-raf',
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
