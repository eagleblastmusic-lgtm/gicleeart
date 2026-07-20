/* Homepage pre-Hero scroll scrub driven by a JPG canvas frame sequence. */
(function () {
  'use strict';

  var ROOT_ID = 'giclee-prehero-video-scrub';
  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var SCROLL_HEIGHT_VH = configNumber('scrollHeightVh', 600, 300, 2000);
  var REVEAL_OVERLAP_VH = configNumber('revealOverlapVh', 200, 100, 1000);
  var HERO_RISE_VH = configNumber('heroRiseVh', 100, 100, 500);

  function configNumber(key, fallback, min, max) {
    var value = Number(CONFIG[key]);
    if (!Number.isFinite(value)) value = fallback;
    return Math.min(max, Math.max(min, value));
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function viewportHeight() {
    return window.innerHeight || document.documentElement.clientHeight || 800;
  }

  function scrollY() {
    return (
      window.scrollY ||
      window.pageYOffset ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0
    );
  }

  function setAttrIfChanged(element, name, value) {
    if (element.getAttribute(name) !== value) element.setAttribute(name, value);
  }

  function frameRendererAvailable() {
    var renderer = window.GICLEE_PREHERO_FRAME_RENDERER;
    return !!(
      renderer &&
      typeof renderer.available === 'function' &&
      renderer.available()
    );
  }

  function findHero() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var heroId = map.hero || 'slideshow_4LMfx7';
    return (
      document.getElementById('shopify-section-' + heroId) ||
      document.querySelector('[id$="__' + heroId + '"]') ||
      document.querySelector('#MainContent > .shopify-section')
    );
  }

  function firstPosterSource(hero) {
    if (!hero) return '';
    var configuredPoster = window.GICLEE_PREHERO_SCRUB_POSTER_URL || '';
    if (configuredPoster) return configuredPoster;
    var video = hero.querySelector('video');
    var poster = video ? video.getAttribute('poster') || video.poster || '' : '';
    if (poster) return poster;
    var image = hero.querySelector('img');
    return image ? image.currentSrc || image.src || '' : '';
  }

  function createSection(hero) {
    var main = document.getElementById('MainContent');
    if (!main || !hero || document.getElementById(ROOT_ID)) return null;

    var root = document.createElement('section');
    root.id = ROOT_ID;
    root.className = 'giclee-prehero-scrub';
    root.setAttribute('data-giclee-prehero-scrub', '1');
    root.setAttribute('data-video-ready', 'false');
    root.setAttribute('data-frame-sequence-ready', 'false');
    root.setAttribute('data-scrub-progress', '0');
    root.setAttribute('data-hero-rise-progress', '0');
    root.setAttribute('data-prehero-phase', 'scrub');
    root.setAttribute('data-render-mode', 'webp-frames');
    root.style.setProperty('--giclee-prehero-scroll-height', SCROLL_HEIGHT_VH + 'vh');
    root.style.setProperty('--giclee-prehero-reveal-overlap', REVEAL_OVERLAP_VH + 'vh');
    root.style.setProperty('--giclee-prehero-hero-rise-height', HERO_RISE_VH + 'vh');
    document.documentElement.style.setProperty(
      '--giclee-prehero-hero-rise-height',
      HERO_RISE_VH + 'vh'
    );

    var stage = document.createElement('div');
    stage.className = 'giclee-prehero-scrub__stage';
    var poster = document.createElement('div');
    poster.className = 'giclee-prehero-scrub__poster';
    var video = document.createElement('video');
    video.className = 'giclee-prehero-scrub__video';
    video.muted = true;
    video.defaultMuted = true;
    video.playsInline = true;
    video.preload = 'none';
    video.controls = false;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('preload', 'none');
    video.setAttribute('tabindex', '-1');
    video.setAttribute('focusable', 'false');
    video.setAttribute('inert', '');
    video.disablePictureInPicture = true;
    video.addEventListener('focus', function () { video.blur(); });

    stage.appendChild(poster);
    stage.appendChild(video);
    root.appendChild(stage);
    main.insertBefore(root, hero);
    return { root: root, stage: stage, poster: poster, video: video, hero: hero };
  }

  function applyPoster(parts) {
    var poster = firstPosterSource(parts.hero);
    if (!poster) return;
    parts.poster.style.backgroundImage =
      'url("' + String(poster).replace(/"/g, '%22') + '")';
  }

  function initScrubbing(parts) {
    var root = parts.root;
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var frameController = frameRendererAvailable()
      ? window.GICLEE_PREHERO_FRAME_RENDERER.create(parts)
      : null;
    var useFrameSequence = !!frameController;
    var duration = frameController ? Number(frameController.duration) || 4.875 : 0;
    var progress = 0;
    var totalTravel = 0;
    var preHeroTravel = 0;
    var heroRiseStart = 0;
    var heroRiseTravel = 0;
    var heroRiseProgress = 0;
    var revealStart = 0;
    var revealOverlapTravel = 0;
    var rootStartY = 0;

    if (!useFrameSequence) {
      root.setAttribute('data-frame-sequence-error', 'true');
      window.GICLEE_PREHERO_SCRUB_STATUS = function () {
        return {
          ready: false,
          renderMode: 'poster-fallback',
          phase: root.getAttribute('data-prehero-phase'),
          duration: 0,
          progress: 0,
          frameSequence: null,
          source: 'hero-poster-fallback',
        };
      };
      return { usesFrameSequence: false };
    }

    root.setAttribute('data-render-mode', 'webp-frames');

    function phaseFor(localScroll) {
      if (localScroll >= heroRiseStart) return 'hero-rise';
      if (localScroll >= revealStart) return 'scrub-reveal';
      return 'scrub';
    }

    function updateProgressFromScroll() {
      if (reducedMotion) return;
      var localScroll = clamp(scrollY() - rootStartY, 0, totalTravel);
      progress = clamp(localScroll / Math.max(1, preHeroTravel), 0, 1);
      heroRiseProgress = clamp(
        (localScroll - heroRiseStart) / Math.max(1, heroRiseTravel),
        0,
        1
      );
      setAttrIfChanged(root, 'data-scrub-progress', progress.toFixed(4));
      setAttrIfChanged(root, 'data-hero-rise-progress', heroRiseProgress.toFixed(4));
      setAttrIfChanged(root, 'data-prehero-phase', phaseFor(localScroll));
      if (useFrameSequence) frameController.setProgress(progress);
    }

    function measureLayout() {
      var viewport = viewportHeight();
      var rect = root.getBoundingClientRect();
      rootStartY = scrollY() + rect.top;
      totalTravel = Math.max(1, root.offsetHeight - viewport);
      heroRiseTravel = Math.min(totalTravel, viewport * (HERO_RISE_VH / 100));
      preHeroTravel = Math.max(1, totalTravel - heroRiseTravel);
      heroRiseStart = preHeroTravel;
      revealOverlapTravel = Math.min(
        preHeroTravel,
        viewport * (REVEAL_OVERLAP_VH / 100)
      );
      revealStart = Math.max(0, preHeroTravel - revealOverlapTravel);
      frameController.resize();
      if (reducedMotion) frameController.setProgress(0);
      else updateProgressFromScroll();
    }

    if (!reducedMotion) {
      window.addEventListener('scroll', updateProgressFromScroll, { passive: true });
      window.addEventListener('resize', measureLayout, { passive: true });
      window.addEventListener('orientationchange', measureLayout, { passive: true });
      window.addEventListener('pageshow', measureLayout, { passive: true });
    }

    measureLayout();

    window.GICLEE_PREHERO_SCRUB_STATUS = function () {
      var frameStatus = frameController.status();
      var renderedTime = frameStatus.frameCount > 1 && frameStatus.renderedFrame >= 0
        ? (frameStatus.renderedFrame / (frameStatus.frameCount - 1)) * duration
        : 0;
      return {
        ready: !!frameStatus.ready,
        renderMode: 'jpg-sprite-canvas',
        phase: root.getAttribute('data-prehero-phase'),
        duration: duration,
        progress: progress,
        targetTime: progress * duration,
        smoothedTime: progress * duration,
        renderedTime: renderedTime,
        seeking: false,
        seekFps: 0,
        configuredSeekFps: 0,
        seekIntervalMs: 0,
        seekCount: 0,
        skippedSeekCount: 0,
        lenisAdaptiveSeeking: false,
        frameSequence: frameStatus,
        totalTravel: totalTravel,
        preHeroTravel: preHeroTravel,
        revealStart: revealStart,
        revealOverlapTravel: revealOverlapTravel,
        heroRiseStart: heroRiseStart,
        heroRiseTravel: heroRiseTravel,
        heroRiseProgress: heroRiseProgress,
        rootStartY: rootStartY,
        source: 'generated-jpg-sprite-sequence',
        config: {
          scrollHeightVh: SCROLL_HEIGHT_VH,
          revealOverlapVh: REVEAL_OVERLAP_VH,
          heroRiseVh: HERO_RISE_VH,
        },
      };
    };

    return { usesFrameSequence: true };
  }

  function boot() {
    if (CONFIG.enabled === false || document.getElementById(ROOT_ID)) return;
    var hero = findHero();
    if (!hero) return;
    var parts = createSection(hero);
    if (!parts) return;
    applyPoster(parts);
    var scrubState = initScrubbing(parts);
    if (scrubState && scrubState.usesFrameSequence) {
      parts.video.preload = 'none';
      parts.video.setAttribute('preload', 'none');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
