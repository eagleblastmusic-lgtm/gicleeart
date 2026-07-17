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
    if (api && typeof api.destroy === 'function') {
      api.destroy();
    }
    root.dataset.gicleeHomeSectionScroll = 'lenis-bypass';
  }

  function installPerformanceProfile() {
    root.classList.add('giclee-lenis-performance');
    installPerformanceStyles();

    /* Section-scroll registers its DOMContentLoaded listener after this module.
     * A zero-delay task runs after all listeners and removes its wheel/RAF engine. */
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

    instance.on('scroll', function (lenis) {
      var velocity = Number(lenis.velocity) || 0;
      root.style.setProperty('--giclee-scroll-velocity', velocity.toFixed(4));
      window.dispatchEvent(
        new CustomEvent('giclee:smooth-scroll', {
          detail: {
            scroll: lenis.scroll,
            progress: lenis.progress,
            velocity: velocity,
            direction: lenis.direction,
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
    });

    publishStatus();
    window.dispatchEvent(
      new CustomEvent('giclee:smooth-scroll-ready', {
        detail: { lerp: LERP, wheelMultiplier: WHEEL_MULTIPLIER },
      })
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
