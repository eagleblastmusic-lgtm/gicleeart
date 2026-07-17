/* Integrated centred portal reveal + original Hero rise. */
(function () {
  'use strict';

  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var SCRUB_ROOT_ID = 'giclee-prehero-video-scrub';
  var LEGACY_REVEAL_ROOT_ID = 'giclee-prehero-video-reveal';
  var REVEAL_CLASS = 'giclee-prehero-reveal';
  var HERO_CLASS = 'giclee-prehero-hero-rise';
  var HERO_ROOT_CLASS = 'giclee-prehero-hero-rise-enabled';
  var TAU_MS = 82;
  var EPSILON = 0.0005;
  var REVEAL_OVERLAP_VH = configNumber('revealOverlapVh', 200, 100, 1000);
  var HERO_RISE_VH = configNumber('heroRiseVh', 100, 100, 500);
  var SOURCE_RETRY_MS = 250;
  var SOURCE_RETRY_LIMIT = 40;
  var DEFAULT_COPY_LINES = [
    'Fotografia i obraz zaczynają żyć w pełni',
    'dopiero wtedy, gdy opuszczają ekran',
    'i stają się częścią świata fizycznego.',
  ];
  var COPY_ENABLED = CONFIG.copyEnabled !== false;
  var COPY_LINES = configuredCopyLines();

  var scrubRoot = null;
  var scrubStage = null;
  var revealRoot = null;
  var nextVisual = null;
  var copy = null;
  var copyLines = [];
  var spine = null;
  var hero = null;
  var targetProgress = 0;
  var currentProgress = 0;
  var heroRiseProgress = 0;
  var rafId = 0;
  var lastFrameTime = 0;
  var reducedMotion = false;
  var totalTravel = 0;
  var preHeroTravel = 0;
  var revealStart = 0;
  var revealTravel = 0;
  var heroRiseStart = 0;
  var heroRiseTravel = 0;
  var localScroll = 0;
  var scrubDocumentTop = 0;
  var visualRetryTimer = 0;
  var visualRetryCount = 0;
  var copyOpacity = 0;
  var frameCount = 0;
  var layoutReadCount = 0;
  var styleWriteCount = 0;

  function configNumber(key, fallback, min, max) {
    var value = Number(CONFIG[key]);
    if (!Number.isFinite(value)) value = fallback;
    return Math.min(max, Math.max(min, value));
  }

  function configuredCopyLines() {
    if (!Array.isArray(CONFIG.copyLines)) return DEFAULT_COPY_LINES.slice();
    var lines = CONFIG.copyLines
      .map(function (line) { return String(line || '').trim(); })
      .filter(Boolean)
      .slice(0, 5);
    return lines.length ? lines : DEFAULT_COPY_LINES.slice();
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

  function lenisPerformanceActive() {
    return document.documentElement.classList.contains('giclee-lenis-performance');
  }

  function viewportHeight() {
    return window.innerHeight || document.documentElement.clientHeight || 800;
  }

  function scrollY() {
    return window.scrollY || window.pageYOffset || document.documentElement.scrollTop || 0;
  }

  function setStyleIfChanged(element, property, value, cacheKey) {
    if (!element || element[cacheKey] === value) return;
    element[cacheKey] = value;
    element.style.setProperty(property, value);
    styleWriteCount += 1;
  }

  function setAttrIfChanged(element, name, value) {
    if (!element || element.getAttribute(name) === value) return;
    element.setAttribute(name, value);
  }

  function parseCssUrl(value) {
    if (!value || value === 'none') return '';
    var match = String(value).match(/url\(["']?(.*?)["']?\)/i);
    return match ? match[1] : '';
  }

  function largestImageSource(container) {
    if (!container) return '';
    var images = Array.prototype.slice.call(container.querySelectorAll('img'));
    var best = '';
    var bestArea = 0;
    images.forEach(function (img) {
      var source = img.currentSrc || img.src || img.getAttribute('src') || '';
      if (!source) return;
      var rect = img.getBoundingClientRect();
      layoutReadCount += 1;
      var area = Math.max(1, rect.width) * Math.max(1, rect.height);
      if (area > bestArea) {
        best = source;
        bestArea = area;
      }
    });
    return best;
  }

  function resolveBackgroundSource(container) {
    if (!container) return '';
    var nodes = [container].concat(
      Array.prototype.slice.call(container.querySelectorAll('*')).slice(0, 100)
    );
    for (var i = 0; i < nodes.length; i += 1) {
      var source = parseCssUrl(window.getComputedStyle(nodes[i]).backgroundImage);
      if (source) return source;
    }
    return '';
  }

  function findHero() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var heroId = map.hero || 'slideshow_4LMfx7';
    return (
      document.getElementById('shopify-section-' + heroId) ||
      document.querySelector('[id$="__' + heroId + '"]')
    );
  }

  function resolveHeroVisual() {
    var configured = window.GICLEE_PREHERO_REVEAL_IMAGE_URL || '';
    if (configured) return configured;
    var image = largestImageSource(hero);
    if (image) return image;
    var heroVideo = hero ? hero.querySelector('video') : null;
    var poster = heroVideo ? heroVideo.getAttribute('poster') || heroVideo.poster || '' : '';
    return poster || resolveBackgroundSource(hero);
  }

  function removeLegacyRevealSection() {
    var legacy = document.getElementById(LEGACY_REVEAL_ROOT_ID);
    if (legacy && legacy.parentNode) legacy.parentNode.removeChild(legacy);
  }

  function createCopy() {
    if (!COPY_ENABLED || !revealRoot) return null;
    copy = document.createElement('div');
    copy.className = 'giclee-prehero-reveal__copy';
    var text = document.createElement('p');
    text.className = 'giclee-prehero-reveal__copy-text';
    text.setAttribute('aria-label', COPY_LINES.join(' '));
    COPY_LINES.forEach(function (lineText, index) {
      var line = document.createElement('span');
      line.className = 'giclee-prehero-reveal__copy-line';
      line.setAttribute('aria-hidden', 'true');
      line.setAttribute('data-line', String(index + 1));
      line.textContent = lineText;
      text.appendChild(line);
      copyLines.push(line);
    });
    copy.appendChild(text);
    revealRoot.appendChild(copy);
    return copy;
  }

  function createIntegratedReveal() {
    if (!scrubRoot || !scrubStage) return false;
    var existing = scrubStage.querySelector('.' + REVEAL_CLASS);
    if (existing) {
      revealRoot = existing;
      nextVisual = existing.querySelector('.giclee-prehero-reveal__visual');
      spine = scrubStage.querySelector('.giclee-prehero-reveal__spine');
      copy = existing.querySelector('.giclee-prehero-reveal__copy');
      copyLines = copy
        ? Array.prototype.slice.call(copy.querySelectorAll('.giclee-prehero-reveal__copy-line'))
        : [];
      return !!nextVisual;
    }
    revealRoot = document.createElement('div');
    revealRoot.className = REVEAL_CLASS;
    revealRoot.setAttribute('data-reveal-progress', '0');
    nextVisual = document.createElement('div');
    nextVisual.className = 'giclee-prehero-reveal__visual';
    nextVisual.setAttribute('aria-hidden', 'true');
    revealRoot.appendChild(nextVisual);
    createCopy();
    spine = document.createElement('div');
    spine.className = 'giclee-prehero-reveal__spine';
    spine.setAttribute('aria-hidden', 'true');
    scrubStage.appendChild(revealRoot);
    scrubStage.appendChild(spine);
    return true;
  }

  function enableOriginalHeroRise() {
    if (!hero) return;
    hero.classList.add(HERO_CLASS);
    hero.setAttribute('data-giclee-prehero-hero-rise', '1');
    document.documentElement.classList.add(HERO_ROOT_CLASS);
    document.documentElement.style.setProperty(
      '--giclee-prehero-hero-rise-height',
      HERO_RISE_VH + 'vh'
    );
  }

  function stopVisualRetry() {
    if (visualRetryTimer) window.clearInterval(visualRetryTimer);
    visualRetryTimer = 0;
  }

  function applyVisualSource() {
    var source = resolveHeroVisual();
    if (!source || !nextVisual) return false;
    var background = 'url("' + String(source).replace(/"/g, '%22') + '")';
    setStyleIfChanged(nextVisual, 'background-image', background, '_gicleeRevealImage');
    setAttrIfChanged(scrubRoot, 'data-next-visual-ready', 'true');
    stopVisualRetry();
    return true;
  }

  function startVisualRetry() {
    if (applyVisualSource()) return;
    stopVisualRetry();
    visualRetryCount = 0;
    visualRetryTimer = window.setInterval(function () {
      visualRetryCount += 1;
      if (applyVisualSource() || visualRetryCount >= SOURCE_RETRY_LIMIT) stopVisualRetry();
    }, SOURCE_RETRY_MS);
  }

  function measureLayout() {
    if (!scrubRoot) return;
    var viewport = viewportHeight();
    var rect = scrubRoot.getBoundingClientRect();
    layoutReadCount += 1;
    scrubDocumentTop = scrollY() + rect.top;
    totalTravel = Math.max(1, scrubRoot.offsetHeight - viewport);
    heroRiseTravel = Math.min(totalTravel, viewport * (HERO_RISE_VH / 100));
    preHeroTravel = Math.max(1, totalTravel - heroRiseTravel);
    heroRiseStart = preHeroTravel;
    revealTravel = Math.min(preHeroTravel, viewport * (REVEAL_OVERLAP_VH / 100));
    revealStart = Math.max(0, preHeroTravel - revealTravel);
    measureProgress();
  }

  function measureProgress() {
    if (!scrubRoot) return;
    localScroll = clamp(scrollY() - scrubDocumentTop, 0, totalTravel);
    targetProgress = clamp((localScroll - revealStart) / Math.max(1, revealTravel), 0, 1);
    heroRiseProgress = smoothstep(
      clamp((localScroll - heroRiseStart) / Math.max(1, heroRiseTravel), 0, 1)
    );
    setAttrIfChanged(scrubRoot, 'data-reveal-active', localScroll >= revealStart - 0.5 ? 'true' : 'false');
    setAttrIfChanged(scrubRoot, 'data-hero-rise-active', localScroll >= heroRiseStart - 0.5 ? 'true' : 'false');
    setAttrIfChanged(scrubRoot, 'data-hero-rise-progress', heroRiseProgress.toFixed(3));
    requestTick();
  }

  function applyCopyFrame(eased) {
    if (!copy || !copyLines.length) {
      copyOpacity = 0;
      return;
    }
    var copyIn = smoothstep(rangeProgress(eased, 0.08, 0.34));
    var copyOut = 1 - smoothstep(rangeProgress(eased, 0.90, 0.995));
    var copyY = 24 * (1 - copyIn) - 12 * (1 - copyOut);
    setStyleIfChanged(copy, '--giclee-prehero-copy-y', copyY.toFixed(2) + 'px', '_gicleeRevealCopyY');
    if (!lenisPerformanceActive()) {
      var copyBlur = 9 * (1 - copyIn) + 3 * (1 - copyOut);
      setStyleIfChanged(copy, '--giclee-prehero-copy-blur', copyBlur.toFixed(2) + 'px', '_gicleeRevealCopyBlur');
    }
    copyOpacity = 0;
    copyLines.forEach(function (line, index) {
      var lineStart = 0.08 + index * 0.055;
      var lineIn = smoothstep(rangeProgress(eased, lineStart, lineStart + 0.20));
      var lineOpacity = lineIn * copyOut;
      copyOpacity = Math.max(copyOpacity, lineOpacity);
      setStyleIfChanged(line, '--giclee-prehero-copy-line-opacity', lineOpacity.toFixed(3), '_gicleeRevealLineOpacity');
      setStyleIfChanged(line, '--giclee-prehero-copy-line-y', (18 * (1 - lineIn)).toFixed(2) + 'px', '_gicleeRevealLineY');
    });
    setStyleIfChanged(copy, '--giclee-prehero-copy-opacity', copyOpacity.toFixed(3), '_gicleeRevealCopyOpacity');
  }

  function applyFrame() {
    if (!revealRoot || !scrubRoot) return;
    frameCount += 1;
    var eased = smoothstep(currentProgress);
    var inset = 50 * (1 - eased);
    var active = localScroll >= revealStart - 0.5;
    var spineFade = 1 - smoothstep(clamp(eased / 0.16, 0, 1));
    var spineOpacity = active && eased < 1 ? 0.72 * spineFade : 0;
    setStyleIfChanged(revealRoot, '--giclee-prehero-reveal-inset', inset.toFixed(2) + '%', '_gicleeRevealInset');
    setStyleIfChanged(revealRoot, '--giclee-prehero-reveal-progress', eased.toFixed(3), '_gicleeRevealProgress');
    setStyleIfChanged(scrubRoot, '--giclee-prehero-reveal-spine-opacity', spineOpacity.toFixed(3), '_gicleeRevealSpine');
    applyCopyFrame(eased);
    var progressValue = eased.toFixed(3);
    setAttrIfChanged(revealRoot, 'data-reveal-progress', progressValue);
    setAttrIfChanged(scrubRoot, 'data-reveal-progress', progressValue);
    setAttrIfChanged(scrubRoot, 'data-reveal-complete', eased >= 0.999 ? 'true' : 'false');
    setAttrIfChanged(scrubRoot, 'data-hero-rise-complete', heroRiseProgress >= 0.999 ? 'true' : 'false');
  }

  function tick(now) {
    rafId = 0;
    var direct = reducedMotion || lenisPerformanceActive();
    if (direct) {
      currentProgress = targetProgress;
    } else {
      var delta = lastFrameTime ? Math.min(64, now - lastFrameTime) : 16.67;
      lastFrameTime = now;
      currentProgress += (targetProgress - currentProgress) * expAlpha(delta, TAU_MS);
    }
    if (Math.abs(targetProgress - currentProgress) <= EPSILON) currentProgress = targetProgress;
    applyFrame();
    if (!direct && Math.abs(targetProgress - currentProgress) > EPSILON) requestTick();
    else lastFrameTime = 0;
  }

  function requestTick() {
    if (!rafId) rafId = window.requestAnimationFrame(tick);
  }

  function refresh() {
    applyVisualSource();
    measureLayout();
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
    if (CONFIG.enabled === false) return;
    removeLegacyRevealSection();
    scrubRoot = document.getElementById(SCRUB_ROOT_ID);
    hero = findHero();
    scrubStage = scrubRoot ? scrubRoot.querySelector('.giclee-prehero-scrub__stage') : null;
    if (!scrubRoot || !scrubStage || !hero || !createIntegratedReveal()) return;
    reducedMotion = !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
    enableOriginalHeroRise();
    startVisualRetry();
    measureLayout();
    currentProgress = targetProgress;
    applyFrame();

    window.addEventListener('scroll', measureProgress, { passive: true });
    window.addEventListener('resize', refresh, { passive: true });
    window.addEventListener('orientationchange', refresh, { passive: true });
    window.addEventListener('pageshow', refresh, { passive: true });

    window.GICLEE_PREHERO_REVEAL_STATUS = function () {
      return {
        integrated: true,
        targetProgress: targetProgress,
        smoothedProgress: currentProgress,
        insetPercent: 50 * (1 - smoothstep(currentProgress)),
        copyOpacity: copyOpacity,
        copyLines: copyLines.length,
        configuredCopyLines: COPY_LINES.slice(),
        totalTravel: totalTravel,
        preHeroTravel: preHeroTravel,
        revealStart: revealStart,
        revealTravel: revealTravel,
        heroRiseStart: heroRiseStart,
        heroRiseTravel: heroRiseTravel,
        heroRiseProgress: heroRiseProgress,
        localScroll: localScroll,
        scrubDocumentTop: scrubDocumentTop,
        directLenisProgress: lenisPerformanceActive(),
        frameCount: frameCount,
        layoutReadCount: layoutReadCount,
        styleWriteCount: styleWriteCount,
        active: scrubRoot.getAttribute('data-reveal-active') === 'true',
        complete: scrubRoot.getAttribute('data-reveal-complete') === 'true',
        heroRiseActive: scrubRoot.getAttribute('data-hero-rise-active') === 'true',
        heroRiseComplete: scrubRoot.getAttribute('data-hero-rise-complete') === 'true',
        nextVisualReady: scrubRoot.getAttribute('data-next-visual-ready') === 'true',
        scrubRect: rectSnapshot(scrubRoot),
        stageRect: rectSnapshot(scrubStage),
        heroRect: rectSnapshot(hero),
        heroClassApplied: hero.classList.contains(HERO_CLASS),
        heroVideoCount: hero.querySelectorAll('video').length,
        legacySectionPresent: !!document.getElementById(LEGACY_REVEAL_ROOT_ID),
        config: {
          revealOverlapVh: REVEAL_OVERLAP_VH,
          heroRiseVh: HERO_RISE_VH,
          copyEnabled: COPY_ENABLED,
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
