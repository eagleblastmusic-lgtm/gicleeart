/* Scroll-driven Hero → Giclée Art horizontal curtain using the live intro section. */
(function () {
  'use strict';

  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var ROOT_CLASS = 'giclee-hero-horizontal-curtain-enabled';
  var HERO_CLASS = 'giclee-hero-horizontal-curtain-source';
  var INTRO_CLASS = 'giclee-hero-horizontal-curtain-intro-target';
  var DIVIDER_CLASS = 'giclee-hero-horizontal-curtain-divider-target';
  var RUNWAY_ID = 'giclee-hero-horizontal-curtain-runway';
  var LEGACY_LAYER_CLASS = 'giclee-hero-horizontal-curtain__intro-layer';
  var SEAMS_CLASS = 'giclee-hero-horizontal-curtain__seams';
  var HOLD_VH = configNumber('heroHoldVh', 100, 0, 500);
  var CURTAIN_VH = configNumber('heroCurtainVh', 100, 50, 500);
  var INTRO_HOLD_VH = configNumber('introHoldVh', 100, 0, 500);
  var TAU_MS = 86;
  var EPSILON = 0.0005;

  var root = document.documentElement;
  var main = null;
  var hero = null;
  var intro = null;
  var divider = null;
  var runway = null;
  var seams = null;
  var targetProgress = 0;
  var currentProgress = 0;
  var introHoldProgress = 0;
  var localScroll = 0;
  var rawLocalScroll = 0;
  var holdTravel = 0;
  var curtainTravel = 0;
  var introHoldTravel = 0;
  var totalTravel = 0;
  var rafId = 0;
  var lastFrameTime = 0;

  function configNumber(key, fallback, min, max) {
    var value = Number(CONFIG[key]);
    if (!Number.isFinite(value)) value = fallback;
    return Math.min(max, Math.max(min, value));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function smoothstep(value) {
    var t = clamp(value, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function rangeProgress(value, start, end) {
    return clamp((value - start) / Math.max(0.0001, end - start), 0, 1);
  }

  function expAlpha(deltaMs, tauMs) {
    if (deltaMs <= 0) return 1;
    return 1 - Math.exp(-deltaMs / Math.max(1, tauMs));
  }

  function viewportHeight() {
    return window.innerHeight || document.documentElement.clientHeight || 800;
  }

  function findSection(hook, fallback) {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var sectionId = map[hook] || fallback || '';
    if (!sectionId) return null;
    return (
      document.getElementById('shopify-section-' + sectionId) ||
      document.querySelector('.shopify-section[id*="' + sectionId + '"]')
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

  function findDividerBetween(start, end) {
    var node = start ? start.nextElementSibling : null;
    while (node && node !== end) {
      if (isDividerSection(node)) return node;
      node = node.nextElementSibling;
    }
    return null;
  }

  function removeLegacyIntroLayers() {
    document.querySelectorAll('.' + LEGACY_LAYER_CLASS).forEach(function (node) {
      node.remove();
    });
  }

  function configureRunway(node) {
    if (!node) return null;
    var totalVh = HOLD_VH + CURTAIN_VH + INTRO_HOLD_VH;
    node.style.setProperty('--giclee-hero-hold-height', HOLD_VH + 'vh');
    node.style.setProperty('--giclee-hero-curtain-height', CURTAIN_VH + 'vh');
    node.style.setProperty('--giclee-hero-intro-hold-height', INTRO_HOLD_VH + 'vh');
    node.style.height = totalVh + 'vh';
    node.style.minHeight = totalVh + 'vh';
    return node;
  }

  function createRunway() {
    if (!hero || !hero.parentNode) return null;
    var existing = document.getElementById(RUNWAY_ID);
    if (existing) return configureRunway(existing);

    var node = document.createElement('div');
    node.id = RUNWAY_ID;
    node.setAttribute('aria-hidden', 'true');
    configureRunway(node);
    hero.parentNode.insertBefore(node, hero.nextElementSibling);
    return node;
  }

  function createSeams() {
    if (!main) return null;
    var existing = main.querySelector(':scope > .' + SEAMS_CLASS);
    if (existing) return existing;

    var node = document.createElement('div');
    node.className = SEAMS_CLASS;
    node.setAttribute('aria-hidden', 'true');
    main.appendChild(node);
    return node;
  }

  function setRootFlag(name, value) {
    root.setAttribute(name, value ? 'true' : 'false');
  }

  function measureProgress() {
    if (!runway) return;

    var viewport = viewportHeight();
    var rect = runway.getBoundingClientRect();
    holdTravel = viewport * (HOLD_VH / 100);
    curtainTravel = Math.max(1, viewport * (CURTAIN_VH / 100));
    introHoldTravel = viewport * (INTRO_HOLD_VH / 100);
    totalTravel = holdTravel + curtainTravel + introHoldTravel;

    /* At Hero centre the runway starts exactly at the viewport bottom. */
    rawLocalScroll = viewport - rect.top;
    localScroll = clamp(rawLocalScroll, 0, totalTravel);
    targetProgress = clamp((localScroll - holdTravel) / curtainTravel, 0, 1);

    var introHoldStart = holdTravel + curtainTravel;
    introHoldProgress = INTRO_HOLD_VH <= 0
      ? (localScroll >= introHoldStart - 0.5 ? 1 : 0)
      : clamp((localScroll - introHoldStart) / Math.max(1, introHoldTravel), 0, 1);

    setRootFlag(
      'data-giclee-hero-horizontal-curtain-active',
      rawLocalScroll >= -0.5
    );
    requestTick();
  }

  function applyFrame() {
    if (!hero || !seams) return;

    var eased = smoothstep(currentProgress);
    var gap = 50 * eased;
    var opening = eased > 0.0005 && eased < 0.9995;
    var lineIn = smoothstep(rangeProgress(eased, 0, 0.08));
    var lineOut = 1 - smoothstep(rangeProgress(eased, 0.86, 1));
    var lineOpacity = 0.72 * lineIn * lineOut;
    var curtainComplete = currentProgress >= 0.999 && targetProgress >= 0.999;
    var introHoldComplete = curtainComplete && (
      INTRO_HOLD_VH <= 0 || localScroll >= totalTravel - 0.5
    );
    var introHoldActive = curtainComplete && !introHoldComplete;

    hero.style.setProperty('--giclee-hero-curtain-gap', gap.toFixed(4) + '%');
    seams.style.setProperty('--giclee-hero-curtain-gap', gap.toFixed(4) + '%');
    seams.style.setProperty(
      '--giclee-hero-curtain-line-opacity',
      lineOpacity.toFixed(4)
    );
    root.style.setProperty('--giclee-hero-curtain-gap', gap.toFixed(4) + '%');
    root.style.setProperty(
      '--giclee-hero-curtain-line-opacity',
      lineOpacity.toFixed(4)
    );

    setRootFlag('data-giclee-hero-horizontal-curtain-opening', opening);
    setRootFlag('data-giclee-hero-horizontal-curtain-complete', curtainComplete);
    setRootFlag('data-giclee-hero-intro-hold-active', introHoldActive);
    setRootFlag('data-giclee-hero-intro-hold-complete', introHoldComplete);
    setRootFlag('data-giclee-hero-horizontal-curtain-handoff-complete', introHoldComplete);

    if (runway) {
      runway.setAttribute('data-curtain-progress', eased.toFixed(4));
      runway.setAttribute('data-intro-hold-progress', introHoldProgress.toFixed(4));
    }
  }

  function tick(now) {
    rafId = 0;
    var delta = lastFrameTime ? Math.min(64, now - lastFrameTime) : 16.67;
    lastFrameTime = now;
    currentProgress +=
      (targetProgress - currentProgress) * expAlpha(delta, TAU_MS);

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

  function boot() {
    if (CONFIG.enabled === false || CONFIG.horizontalCurtainEnabled === false) return;
    if (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    main = document.getElementById('MainContent');
    hero = findSection('hero', 'slideshow_4LMfx7');
    intro = findSection('intro', 'section_ThWw4Q');
    if (!main || !hero || !intro || hero.parentNode !== intro.parentNode) return;

    removeLegacyIntroLayers();
    divider = findDividerBetween(hero, intro);
    hero.classList.add(HERO_CLASS);
    intro.classList.add(INTRO_CLASS);
    intro.setAttribute('data-giclee-curtain-live-intro', 'true');
    if (divider) divider.classList.add(DIVIDER_CLASS);

    runway = createRunway();
    seams = createSeams();
    if (!runway || !seams) return;

    root.classList.add(ROOT_CLASS);
    root.style.setProperty('--giclee-hero-hold-height', HOLD_VH + 'vh');
    root.style.setProperty('--giclee-hero-curtain-height', CURTAIN_VH + 'vh');
    root.style.setProperty('--giclee-hero-intro-hold-height', INTRO_HOLD_VH + 'vh');
    setRootFlag('data-giclee-hero-horizontal-curtain-active', false);
    setRootFlag('data-giclee-hero-horizontal-curtain-opening', false);
    setRootFlag('data-giclee-hero-horizontal-curtain-complete', false);
    setRootFlag('data-giclee-hero-intro-hold-active', false);
    setRootFlag('data-giclee-hero-intro-hold-complete', false);
    setRootFlag('data-giclee-hero-horizontal-curtain-handoff-complete', false);

    measureProgress();
    currentProgress = targetProgress;
    applyFrame();

    window.addEventListener('scroll', measureProgress, { passive: true });
    window.addEventListener('resize', measureProgress, { passive: true });
    window.addEventListener('orientationchange', measureProgress, { passive: true });
    window.addEventListener('pageshow', measureProgress, { passive: true });

    window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS = function () {
      var introStyle = window.getComputedStyle(intro);
      return {
        ready: true,
        transitionMode: 'live-intro-hold',
        targetProgress: targetProgress,
        smoothedProgress: currentProgress,
        easedProgress: smoothstep(currentProgress),
        gapPercent: 50 * smoothstep(currentProgress),
        rawLocalScroll: rawLocalScroll,
        localScroll: localScroll,
        holdTravel: holdTravel,
        curtainTravel: curtainTravel,
        introHoldTravel: introHoldTravel,
        introHoldProgress: introHoldProgress,
        totalTravel: totalTravel,
        active:
          root.getAttribute('data-giclee-hero-horizontal-curtain-active') ===
          'true',
        opening:
          root.getAttribute('data-giclee-hero-horizontal-curtain-opening') ===
          'true',
        complete:
          root.getAttribute('data-giclee-hero-horizontal-curtain-complete') ===
          'true',
        introHoldActive:
          root.getAttribute('data-giclee-hero-intro-hold-active') === 'true',
        introHoldComplete:
          root.getAttribute('data-giclee-hero-intro-hold-complete') === 'true',
        handoffComplete:
          root.getAttribute(
            'data-giclee-hero-horizontal-curtain-handoff-complete'
          ) === 'true',
        heroRect: rectSnapshot(hero),
        runwayRect: rectSnapshot(runway),
        introRect: rectSnapshot(intro),
        introCloneRect: null,
        introPosition: introStyle.position,
        introOpacity: introStyle.opacity,
        introVisibility: introStyle.visibility,
        dividerHidden: !!divider,
        config: {
          heroHoldVh: HOLD_VH,
          heroCurtainVh: CURTAIN_VH,
          introHoldVh: INTRO_HOLD_VH,
        },
      };
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();