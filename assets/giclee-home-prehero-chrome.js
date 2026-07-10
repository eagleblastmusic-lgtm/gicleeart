/*
 * Homepage pre-hero viewport curtain controller.
 * The native Shopify .header-section and the lower black rail are driven by one RAF value.
 * The video is never translated.
 */
(function () {
  'use strict';

  var ROOT_ID = 'giclee-prehero-video-scrub';
  var HEADER_CLASS = 'giclee-prehero-chrome-header';
  var ROOT_CLASS = 'giclee-prehero-chrome-enabled';
  var TAU_MS = 88;
  var EPSILON = 0.0005;
  var START_SCROLL_EPS = 2;

  var root = null;
  var header = null;
  var headerComponent = null;
  var headerRow = null;
  var bottomBand = null;
  var headerHeight = 60;
  var targetProgress = 0;
  var currentProgress = 0;
  var rafId = 0;
  var lastFrameTime = 0;
  var reducedMotion = false;
  var startupResetActive = true;
  var startupResetCount = 0;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function smoothstep(value) {
    var t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function expAlpha(deltaMs, tauMs) {
    if (deltaMs <= 0) return 1;
    return 1 - Math.exp(-deltaMs / Math.max(1, tauMs));
  }

  function getScrollY() {
    return window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
  }

  function findHeader() {
    headerComponent = document.getElementById('header-component');
    if (!headerComponent) return null;

    headerRow = headerComponent.querySelector('.header__row--top');
    return headerComponent.closest('.header-section') || headerComponent;
  }

  function ensureBottomBand() {
    var existing = root.querySelector('.giclee-prehero-scrub__bottom-band');
    if (existing) return existing;

    var band = document.createElement('div');
    band.className = 'giclee-prehero-scrub__bottom-band';
    band.setAttribute('aria-hidden', 'true');
    root.appendChild(band);
    return band;
  }

  function readCssHeight() {
    var bodyStyle = getComputedStyle(document.body);
    var value = parseFloat(bodyStyle.getPropertyValue('--header-height'));
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function measureHeader() {
    if (!header) return;

    var rowRect = headerRow ? headerRow.getBoundingClientRect() : null;
    var componentRect = headerComponent ? headerComponent.getBoundingClientRect() : null;
    var headerRect = header.getBoundingClientRect();
    var measured = Math.round(
      readCssHeight() ||
      (rowRect && rowRect.height) ||
      (componentRect && componentRect.height) ||
      headerRect.height ||
      60
    );

    headerHeight = Math.max(1, measured);
    document.documentElement.style.setProperty(
      '--giclee-prehero-header-height',
      headerHeight + 'px'
    );
  }

  function collapseDistance() {
    var viewport = window.innerHeight || document.documentElement.clientHeight || 800;
    return Math.max(headerHeight * 4, Math.min(viewport * 0.58, 560));
  }

  function forceClosedCurtain() {
    targetProgress = 0;
    currentProgress = 0;
    lastFrameTime = 0;
    applyFrame();
  }

  function readTargets() {
    if (!root) return;

    if (startupResetActive || getScrollY() <= START_SCROLL_EPS) {
      targetProgress = 0;
      requestTick();
      return;
    }

    var scrollY = getScrollY();
    var rootRect = root.getBoundingClientRect();
    var rootDocumentTop = scrollY + rootRect.top;
    var raw = (scrollY - rootDocumentTop) / Math.max(1, collapseDistance());

    targetProgress = smoothstep(clamp(raw, 0, 1));
    requestTick();
  }

  function disableLegacyFade() {
    if (!headerComponent) return;
    headerComponent.classList.remove('giclee-header-scroll-fade');
    headerComponent.style.setProperty('--gab-header-fade-opacity', '1', 'important');
    headerComponent.style.setProperty('opacity', '1', 'important');
    headerComponent.style.setProperty('visibility', 'visible', 'important');
    headerComponent.style.setProperty('pointer-events', 'auto', 'important');
  }

  function applyFrame() {
    var eased = clamp(currentProgress, 0, 1);
    var distance = headerHeight * eased;
    var interactive = eased <= 0.96;

    document.documentElement.style.setProperty(
      '--giclee-prehero-header-y',
      (-distance).toFixed(3) + 'px'
    );
    document.documentElement.style.setProperty(
      '--giclee-prehero-band-y',
      distance.toFixed(3) + 'px'
    );

    header.style.setProperty('opacity', '1', 'important');
    header.style.setProperty('visibility', 'visible', 'important');
    header.style.setProperty(
      'pointer-events',
      interactive ? 'auto' : 'none',
      'important'
    );

    disableLegacyFade();
    root.setAttribute('data-chrome-progress', eased.toFixed(4));
  }

  function tick(now) {
    rafId = 0;
    var delta = lastFrameTime ? Math.min(64, now - lastFrameTime) : 16.67;
    lastFrameTime = now;

    if (reducedMotion) {
      currentProgress = targetProgress;
    } else {
      currentProgress +=
        (targetProgress - currentProgress) * expAlpha(delta, TAU_MS);
    }

    if (Math.abs(targetProgress - currentProgress) <= EPSILON) {
      currentProgress = targetProgress;
    }

    applyFrame();

    if (Math.abs(targetProgress - currentProgress) > EPSILON) {
      requestTick();
    } else {
      lastFrameTime = 0;
    }
  }

  function requestTick() {
    if (!rafId) rafId = window.requestAnimationFrame(tick);
  }

  function refreshLayout() {
    measureHeader();
    disableLegacyFade();
    readTargets();
  }

  function rectSnapshot(element) {
    if (!element) return null;
    var rect = element.getBoundingClientRect();
    return {
      top: Math.round(rect.top * 100) / 100,
      right: Math.round(rect.right * 100) / 100,
      bottom: Math.round(rect.bottom * 100) / 100,
      left: Math.round(rect.left * 100) / 100,
      width: Math.round(rect.width * 100) / 100,
      height: Math.round(rect.height * 100) / 100,
    };
  }

  function styleSnapshot(element) {
    if (!element) return null;
    var style = getComputedStyle(element);
    return {
      display: style.display,
      visibility: style.visibility,
      opacity: style.opacity,
      position: style.position,
      transform: style.transform,
      color: style.color,
      backgroundColor: style.backgroundColor,
      zIndex: style.zIndex,
    };
  }

  function shouldResetToTop() {
    return !window.location.hash;
  }

  function resetSequenceToTop() {
    if (!shouldResetToTop()) {
      startupResetActive = false;
      readTargets();
      return;
    }

    startupResetActive = true;
    startupResetCount += 1;
    forceClosedCurtain();

    try {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
    } catch (error) {
      window.scrollTo(0, 0);
    }

    requestAnimationFrame(function () {
      try {
        window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      } catch (error) {
        window.scrollTo(0, 0);
      }

      requestAnimationFrame(function () {
        startupResetActive = false;
        forceClosedCurtain();
      });
    });
  }

  function boot() {
    if (document.documentElement.classList.contains(ROOT_CLASS)) return;

    root = document.getElementById(ROOT_ID);
    header = findHeader();
    if (!root || !header) return;

    reducedMotion = !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );

    if ('scrollRestoration' in history && shouldResetToTop()) {
      history.scrollRestoration = 'manual';
    }

    measureHeader();
    bottomBand = ensureBottomBand();
    header.classList.add(HEADER_CLASS);
    document.documentElement.classList.add(ROOT_CLASS);

    disableLegacyFade();
    forceClosedCurtain();
    resetSequenceToTop();

    window.addEventListener('scroll', readTargets, { passive: true });
    window.addEventListener('resize', refreshLayout, { passive: true });
    window.addEventListener('orientationchange', refreshLayout, { passive: true });
    window.addEventListener('giclee:splash-done', function () {
      disableLegacyFade();
      forceClosedCurtain();
    }, { passive: true });
    window.addEventListener('pageshow', function () {
      resetSequenceToTop();
    }, { passive: true });

    if (window.ResizeObserver) {
      var observer = new ResizeObserver(refreshLayout);
      observer.observe(headerRow || headerComponent || header);
    }

    window.GICLEE_PREHERO_CHROME_STATUS = function () {
      return {
        headerHeight: headerHeight,
        targetProgress: targetProgress,
        smoothedProgress: currentProgress,
        headerY: -headerHeight * currentProgress,
        bandY: headerHeight * currentProgress,
        videoTranslateY: 0,
        scrollY: getScrollY(),
        startupResetActive: startupResetActive,
        startupResetCount: startupResetCount,
        headerTarget: header.className || header.tagName,
        headerRect: rectSnapshot(header),
        headerStyle: styleSnapshot(header),
        rowRect: rectSnapshot(headerRow),
        rowStyle: styleSnapshot(headerRow),
        componentRect: rectSnapshot(headerComponent),
        componentStyle: styleSnapshot(headerComponent),
        bandRect: rectSnapshot(bottomBand),
        bottomBand: !!bottomBand,
        reducedMotion: reducedMotion,
      };
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
