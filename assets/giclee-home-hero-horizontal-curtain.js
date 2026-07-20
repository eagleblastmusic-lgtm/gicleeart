/* Scroll-driven Hero → Giclée Art horizontal curtain using the live intro section. */
(function () {
  'use strict';

  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var ROOT_CLASS = 'giclee-hero-horizontal-curtain-enabled';
  var HERO_CLASS = 'giclee-hero-horizontal-curtain-source';
  var INTRO_CLASS = 'giclee-hero-horizontal-curtain-intro-target';
  var DIVIDER_CLASS = 'giclee-hero-horizontal-curtain-divider-target';
  var RUNWAY_ID = 'giclee-hero-horizontal-curtain-runway';
  var SEAMS_CLASS = 'giclee-hero-horizontal-curtain__seams';
  var HOLD_VH = numberConfig('heroHoldVh', 100, 0, 500);
  var CURTAIN_VH = numberConfig('heroCurtainVh', 100, 50, 500);
  var INTRO_HOLD_VH = numberConfig('introHoldVh', 100, 0, 500);
  var TAU_MS = 86;
  var EPSILON = 0.0005;

  var doc = document.documentElement;
  var main;
  var hero;
  var intro;
  var divider;
  var runway;
  var seams;
  var runwayDocumentTop = 0;
  var targetProgress = 0;
  var currentProgress = 0;
  var rawLocalScroll = 0;
  var localScroll = 0;
  var holdTravel = 0;
  var curtainTravel = 0;
  var introHoldTravel = 0;
  var introHoldProgress = 0;
  var totalTravel = 0;
  var rafId = 0;
  var lastFrameTime = 0;
  var frameCount = 0;
  var layoutReadCount = 0;
  var styleWriteCount = 0;

  function numberConfig(key, fallback, min, max) {
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

  function range(value, start, end) {
    return clamp((value - start) / Math.max(0.0001, end - start), 0, 1);
  }

  function lenisActive() {
    return doc.classList.contains('giclee-lenis-performance');
  }

  function viewportHeight() {
    return window.innerHeight || doc.clientHeight || 800;
  }

  function scrollY() {
    return window.scrollY || window.pageYOffset || doc.scrollTop || 0;
  }

  function setStyle(element, property, value, key) {
    if (!element || element[key] === value) return;
    element[key] = value;
    element.style.setProperty(property, value);
    styleWriteCount += 1;
  }

  function setAttr(element, name, value) {
    if (element && element.getAttribute(name) !== value) element.setAttribute(name, value);
  }

  function setFlag(name, value) {
    setAttr(doc, name, value ? 'true' : 'false');
  }

  function findSection(hook, fallback) {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var id = map[hook] || fallback;
    return document.getElementById('shopify-section-' + id) ||
      document.querySelector('.shopify-section[id*="' + id + '"]');
  }

  function isDivider(element) {
    return !!(element && element.classList &&
      element.classList.contains('shopify-section') &&
      element.querySelector('[data-testid^="divider-"]'));
  }

  function dividerBetween(start, end) {
    var node = start && start.nextElementSibling;
    while (node && node !== end) {
      if (isDivider(node)) return node;
      node = node.nextElementSibling;
    }
    return null;
  }

  function createRunway() {
    var node = document.getElementById(RUNWAY_ID);
    if (!node) {
      node = document.createElement('div');
      node.id = RUNWAY_ID;
      node.setAttribute('aria-hidden', 'true');
      hero.parentNode.insertBefore(node, hero.nextElementSibling);
    }
    var height = HOLD_VH + CURTAIN_VH + INTRO_HOLD_VH;
    node.style.height = height + 'vh';
    node.style.minHeight = height + 'vh';
    setStyle(node, '--giclee-hero-hold-height', HOLD_VH + 'vh', '_gchHold');
    setStyle(node, '--giclee-hero-curtain-height', CURTAIN_VH + 'vh', '_gchCurtain');
    setStyle(node, '--giclee-hero-intro-hold-height', INTRO_HOLD_VH + 'vh', '_gchIntroHold');
    return node;
  }

  function createSeams() {
    var node = main.querySelector(':scope > .' + SEAMS_CLASS);
    if (!node) {
      node = document.createElement('div');
      node.className = SEAMS_CLASS;
      node.setAttribute('aria-hidden', 'true');
      main.appendChild(node);
    }
    return node;
  }

  function measureLayout() {
    var viewport = viewportHeight();
    var rect = runway.getBoundingClientRect();
    layoutReadCount += 1;
    runwayDocumentTop = scrollY() + rect.top;
    holdTravel = viewport * HOLD_VH / 100;
    curtainTravel = Math.max(1, viewport * CURTAIN_VH / 100);
    introHoldTravel = viewport * INTRO_HOLD_VH / 100;
    totalTravel = holdTravel + curtainTravel + introHoldTravel;
    readProgress();
  }

  function readProgress() {
    var viewport = viewportHeight();
    rawLocalScroll = scrollY() - runwayDocumentTop + viewport;
    localScroll = clamp(rawLocalScroll, 0, totalTravel);
    targetProgress = clamp((localScroll - holdTravel) / curtainTravel, 0, 1);
    var introStart = holdTravel + curtainTravel;
    introHoldProgress = INTRO_HOLD_VH <= 0
      ? (localScroll >= introStart - 0.5 ? 1 : 0)
      : clamp((localScroll - introStart) / Math.max(1, introHoldTravel), 0, 1);
    setFlag('data-giclee-hero-horizontal-curtain-active', rawLocalScroll >= -0.5);
    requestFrame();
  }

  function applyFrame() {
    frameCount += 1;
    var eased = smoothstep(currentProgress);
    var gap = (50 * eased).toFixed(3) + '%';
    var lineOpacity = (0.72 * smoothstep(range(eased, 0, 0.08)) *
      (1 - smoothstep(range(eased, 0.86, 1)))).toFixed(3);
    var complete = currentProgress >= 0.999 && targetProgress >= 0.999;
    var introComplete = complete && (INTRO_HOLD_VH <= 0 || localScroll >= totalTravel - 0.5);
    setStyle(hero, '--giclee-hero-curtain-gap', gap, '_gchHeroGap');
    setStyle(seams, '--giclee-hero-curtain-gap', gap, '_gchSeamGap');
    setStyle(seams, '--giclee-hero-curtain-line-opacity', lineOpacity, '_gchSeamLine');
    setStyle(doc, '--giclee-hero-curtain-gap', gap, '_gchRootGap');
    setStyle(doc, '--giclee-hero-curtain-line-opacity', lineOpacity, '_gchRootLine');
    setFlag('data-giclee-hero-horizontal-curtain-opening', eased > 0.0005 && eased < 0.9995);
    setFlag('data-giclee-hero-horizontal-curtain-complete', complete);
    setFlag('data-giclee-hero-intro-hold-active', complete && !introComplete);
    setFlag('data-giclee-hero-intro-hold-complete', introComplete);
    setFlag('data-giclee-hero-horizontal-curtain-handoff-complete', introComplete);
    setAttr(runway, 'data-curtain-progress', eased.toFixed(3));
    setAttr(runway, 'data-intro-hold-progress', introHoldProgress.toFixed(3));
  }

  function tick(now) {
    rafId = 0;
    var direct = lenisActive();
    if (direct) {
      currentProgress = targetProgress;
    } else {
      var delta = lastFrameTime ? Math.min(64, now - lastFrameTime) : 16.67;
      lastFrameTime = now;
      currentProgress += (targetProgress - currentProgress) *
        (1 - Math.exp(-delta / TAU_MS));
    }
    if (Math.abs(targetProgress - currentProgress) <= EPSILON) currentProgress = targetProgress;
    applyFrame();
    if (!direct && Math.abs(targetProgress - currentProgress) > EPSILON) requestFrame();
    else lastFrameTime = 0;
  }

  function requestFrame() {
    if (!rafId) rafId = window.requestAnimationFrame(tick);
  }

  function rectSnapshot(element) {
    if (!element) return null;
    var rect = element.getBoundingClientRect();
    return { top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height };
  }

  function boot() {
    if (CONFIG.enabled === false || CONFIG.horizontalCurtainEnabled === false) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    main = document.getElementById('MainContent');
    hero = findSection('hero', 'slideshow_4LMfx7');
    intro = findSection('intro', 'section_ThWw4Q');
    if (!main || !hero || !intro || hero.parentNode !== intro.parentNode) return;
    document.querySelectorAll('.giclee-hero-horizontal-curtain__intro-layer').forEach(function (node) {
      node.remove();
    });
    divider = dividerBetween(hero, intro);
    hero.classList.add(HERO_CLASS);
    intro.classList.add(INTRO_CLASS);
    intro.setAttribute('data-giclee-curtain-live-intro', 'true');
    if (divider) divider.classList.add(DIVIDER_CLASS);
    runway = createRunway();
    seams = createSeams();
    doc.classList.add(ROOT_CLASS);
    setStyle(doc, '--giclee-hero-hold-height', HOLD_VH + 'vh', '_gchRootHold');
    setStyle(doc, '--giclee-hero-curtain-height', CURTAIN_VH + 'vh', '_gchRootCurtain');
    setStyle(doc, '--giclee-hero-intro-hold-height', INTRO_HOLD_VH + 'vh', '_gchRootIntroHold');
    measureLayout();
    currentProgress = targetProgress;
    applyFrame();
    window.addEventListener('scroll', readProgress, { passive: true });
    window.addEventListener('resize', measureLayout, { passive: true });
    window.addEventListener('orientationchange', measureLayout, { passive: true });
    window.addEventListener('pageshow', measureLayout, { passive: true });

    window.GICLEE_HERO_HORIZONTAL_CURTAIN_RUNTIME = function () {
      return {
        active: doc.getAttribute('data-giclee-hero-horizontal-curtain-active') === 'true',
        opening: doc.getAttribute('data-giclee-hero-horizontal-curtain-opening') === 'true',
        complete: doc.getAttribute('data-giclee-hero-horizontal-curtain-complete') === 'true',
        easedProgress: smoothstep(currentProgress),
        localScroll: localScroll,
        holdTravel: holdTravel,
        curtainTravel: curtainTravel,
        introHoldProgress: introHoldProgress,
      };
    };

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
        runwayDocumentTop: runwayDocumentTop,
        directLenisProgress: lenisActive(),
        frameCount: frameCount,
        layoutReadCount: layoutReadCount,
        styleWriteCount: styleWriteCount,
        active: doc.getAttribute('data-giclee-hero-horizontal-curtain-active') === 'true',
        opening: doc.getAttribute('data-giclee-hero-horizontal-curtain-opening') === 'true',
        complete: doc.getAttribute('data-giclee-hero-horizontal-curtain-complete') === 'true',
        introHoldActive: doc.getAttribute('data-giclee-hero-intro-hold-active') === 'true',
        introHoldComplete: doc.getAttribute('data-giclee-hero-intro-hold-complete') === 'true',
        handoffComplete: doc.getAttribute('data-giclee-hero-horizontal-curtain-handoff-complete') === 'true',
        heroRect: rectSnapshot(hero),
        runwayRect: rectSnapshot(runway),
        introRect: rectSnapshot(intro),
        introCloneRect: null,
        introPosition: introStyle.position,
        introOpacity: introStyle.opacity,
        introVisibility: introStyle.visibility,
        dividerHidden: !!divider,
        config: { heroHoldVh: HOLD_VH, heroCurtainVh: CURTAIN_VH, introHoldVh: INTRO_HOLD_VH },
      };
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
