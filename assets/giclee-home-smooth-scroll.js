/* Homepage smooth scrolling tuned for the cinematic Giclee Art flow. */
(function () {
  'use strict';

  var root = document.documentElement;
  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var LERP = 0.11;
  var WHEEL_MULTIPLIER = 1;
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
    return String(CONFIG.smoothScrollMode || 'lenis').toLowerCase() === 'native'
      ? 'native'
      : 'lenis';
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

  function publishStatus() {
    window.GICLEE_SMOOTH_SCROLL_STATUS = function () {
      return {
        ready: !!instance,
        active: root.getAttribute('data-giclee-smooth-scroll') === 'active',
        mode: configuredMode(),
        disabledReason: disabledReason,
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
