/* Scroll-driven Hero → Giclée Art horizontal curtain. */
(function () {
  'use strict';

  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var ROOT_CLASS = 'giclee-hero-horizontal-curtain-enabled';
  var HERO_CLASS = 'giclee-hero-horizontal-curtain-source';
  var INTRO_CLASS = 'giclee-hero-horizontal-curtain-intro-target';
  var DIVIDER_CLASS = 'giclee-hero-horizontal-curtain-divider-target';
  var RUNWAY_ID = 'giclee-hero-horizontal-curtain-runway';
  var LAYER_CLASS = 'giclee-hero-horizontal-curtain__intro-layer';
  var CLONE_CLASS = 'giclee-hero-horizontal-curtain__intro-clone';
  var SEAMS_CLASS = 'giclee-hero-horizontal-curtain__seams';
  var HOLD_VH = configNumber('heroHoldVh', 100, 0, 500);
  var CURTAIN_VH = configNumber('heroCurtainVh', 100, 50, 500);
  var TAU_MS = 86;
  var EPSILON = 0.0005;

  var root = document.documentElement;
  var main = null;
  var hero = null;
  var intro = null;
  var divider = null;
  var runway = null;
  var introLayer = null;
  var introClone = null;
  var seams = null;
  var targetProgress = 0;
  var currentProgress = 0;
  var localScroll = 0;
  var rawLocalScroll = 0;
  var holdTravel = 0;
  var curtainTravel = 0;
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

  function safeId(value) {
    return String(value || 'node').replace(/[^a-zA-Z0-9_-]+/g, '-');
  }

  function rewriteCloneIds(clone) {
    var nodes = [clone].concat(Array.prototype.slice.call(clone.querySelectorAll('[id]')));
    var replacements = [];

    nodes.forEach(function (node, index) {
      var oldId = node.id;
      if (!oldId) return;
      var newId = 'giclee-curtain-clone-' + safeId(oldId) + '-' + index;
      replacements.push({ oldId: oldId, newId: newId });
      node.id = newId;
    });

    clone.querySelectorAll('style').forEach(function (style) {
      var css = style.textContent || '';
      replacements.forEach(function (item) {
        css = css.split('#' + item.oldId).join('#' + item.newId);
      });
      style.textContent = css;
    });

    clone.querySelectorAll('[for], [aria-labelledby], [aria-describedby], [href^="#"]').forEach(
      function (node) {
        replacements.forEach(function (item) {
          ['for', 'aria-labelledby', 'aria-describedby', 'href'].forEach(function (attr) {
            var value = node.getAttribute(attr);
            if (!value) return;
            node.setAttribute(attr, value.split(item.oldId).join(item.newId));
          });
        });
      }
    );
  }

  function prepareCloneMedia(clone) {
    clone.querySelectorAll('video').forEach(function (video) {
      video.muted = true;
      video.defaultMuted = true;
      video.playsInline = true;
      video.loop = true;
      video.autoplay = true;
      video.controls = false;
      video.setAttribute('muted', '');
      video.setAttribute('playsinline', '');
      var playPromise = video.play();
      if (playPromise && typeof playPromise.catch === 'function') {
        playPromise.catch(function () {});
      }
    });
  }

  function createIntroClone() {
    if (!intro || !main) return null;

    introLayer = document.createElement('div');
    introLayer.className = LAYER_CLASS;
    introLayer.setAttribute('aria-hidden', 'true');
    introLayer.setAttribute('inert', '');

    introClone = intro.cloneNode(true);
    introClone.classList.add(CLONE_CLASS);
    introClone.classList.remove('giclee-home-stack-divider');
    introClone.classList.remove('giclee-home-stack-divider--scroll');
    introClone.removeAttribute('data-giclee-home-stack');
    introClone.removeAttribute('data-giclee-home-stack-hook');
    introClone.setAttribute('aria-hidden', 'true');
    introClone.setAttribute('inert', '');

    introClone.querySelectorAll('script, noscript').forEach(function (node) {
      node.remove();
    });
    introClone.querySelectorAll('a, button, input, select, textarea, [tabindex]').forEach(
      function (node) {
        node.setAttribute('tabindex', '-1');
        node.setAttribute('aria-hidden', 'true');
        if ('disabled' in node) node.disabled = true;
      }
    );

    rewriteCloneIds(introClone);
    introLayer.appendChild(introClone);
    main.appendChild(introLayer);
    prepareCloneMedia(introClone);
    return introLayer;
  }

  function createRunway() {
    if (!hero || !hero.parentNode) return null;
    var existing = document.getElementById(RUNWAY_ID);
    if (existing) return existing;

    var node = document.createElement('div');
    node.id = RUNWAY_ID;
    node.setAttribute('aria-hidden', 'true');
    node.style.setProperty('--giclee-hero-hold-height', HOLD_VH + 'vh');
    node.style.setProperty('--giclee-hero-curtain-height', CURTAIN_VH + 'vh');
    hero.parentNode.insertBefore(node, hero.nextElementSibling);
    return node;
  }

  function createSeams() {
    if (!main) return null;
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
    totalTravel = holdTravel + curtainTravel;

    /* At Hero centre the runway starts exactly at the viewport bottom. */
    rawLocalScroll = viewport - rect.top;
    localScroll = clamp(rawLocalScroll, 0, totalTravel);
    targetProgress = clamp((localScroll - holdTravel) / curtainTravel, 0, 1);

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
    var complete = currentProgress >= 0.999 && targetProgress >= 0.999;

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
    setRootFlag('data-giclee-hero-horizontal-curtain-complete', complete);
    if (runway) runway.setAttribute('data-curtain-progress', eased.toFixed(4));
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

    divider = findDividerBetween(hero, intro);
    hero.classList.add(HERO_CLASS);
    intro.classList.add(INTRO_CLASS);
    if (divider) divider.classList.add(DIVIDER_CLASS);

    runway = createRunway();
    introLayer = createIntroClone();
    seams = createSeams();
    if (!runway || !introLayer || !seams) return;

    root.classList.add(ROOT_CLASS);
    root.style.setProperty('--giclee-hero-hold-height', HOLD_VH + 'vh');
    root.style.setProperty('--giclee-hero-curtain-height', CURTAIN_VH + 'vh');
    setRootFlag('data-giclee-hero-horizontal-curtain-active', false);
    setRootFlag('data-giclee-hero-horizontal-curtain-opening', false);
    setRootFlag('data-giclee-hero-horizontal-curtain-complete', false);

    measureProgress();
    currentProgress = targetProgress;
    applyFrame();

    window.addEventListener('scroll', measureProgress, { passive: true });
    window.addEventListener('resize', measureProgress, { passive: true });
    window.addEventListener('orientationchange', measureProgress, { passive: true });
    window.addEventListener('pageshow', measureProgress, { passive: true });

    window.GICLEE_HERO_HORIZONTAL_CURTAIN_STATUS = function () {
      return {
        ready: true,
        targetProgress: targetProgress,
        smoothedProgress: currentProgress,
        easedProgress: smoothstep(currentProgress),
        gapPercent: 50 * smoothstep(currentProgress),
        rawLocalScroll: rawLocalScroll,
        localScroll: localScroll,
        holdTravel: holdTravel,
        curtainTravel: curtainTravel,
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
        heroRect: rectSnapshot(hero),
        runwayRect: rectSnapshot(runway),
        introRect: rectSnapshot(intro),
        introCloneRect: rectSnapshot(introClone),
        dividerHidden: !!divider,
        config: {
          heroHoldVh: HOLD_VH,
          heroCurtainVh: CURTAIN_VH,
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
