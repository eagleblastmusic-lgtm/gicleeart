/*
 * Homepage pre-hero video scrub.
 *
 * Performance rules:
 * - geometry is measured only on layout changes, never on every scroll event;
 * - at most one media seek is active at a time;
 * - seeks are rate-limited so video decoding cannot monopolise the main thread;
 * - while a seek is active, scroll only updates the newest target (no busy RAF loop).
 */
(function () {
  'use strict';

  var ROOT_ID = 'giclee-prehero-video-scrub';
  var CONFIG = window.GICLEE_PREHERO_CONFIG || {};
  var SEEK_EPSILON = 0.018;
  var SOURCE_RETRY_MS = 250;
  var SOURCE_RETRY_LIMIT = 80;
  var SCROLL_HEIGHT_VH = configNumber('scrollHeightVh', 600, 300, 2000);
  var REVEAL_OVERLAP_VH = configNumber('revealOverlapVh', 200, 100, 1000);
  var HERO_RISE_VH = configNumber('heroRiseVh', 100, 100, 500);
  var SEEK_FPS = configNumber('scrubSeekFps', 24, 12, 60);
  var SEEK_INTERVAL_MS = 1000 / SEEK_FPS;

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
    if (element.getAttribute(name) !== value) {
      element.setAttribute(name, value);
    }
  }

  function firstMediaSource(video) {
    if (!video) return '';
    var source = video.currentSrc || video.getAttribute('src') || video.src || '';
    if (source) return source;
    var sourceEl = video.querySelector('source[src]');
    return sourceEl ? sourceEl.src || sourceEl.getAttribute('src') || '' : '';
  }

  function firstPosterSource(hero, sourceVideo) {
    var configuredPoster = window.GICLEE_PREHERO_SCRUB_POSTER_URL || '';
    if (configuredPoster) return configuredPoster;

    if (sourceVideo) {
      var poster = sourceVideo.getAttribute('poster') || sourceVideo.poster || '';
      if (poster) return poster;
    }

    var image = hero ? hero.querySelector('img') : null;
    return image ? image.currentSrc || image.src || '' : '';
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

  function findSourceVideo(hero) {
    if (!hero) return null;
    var videos = hero.querySelectorAll('video');
    var fallback = null;

    for (var i = 0; i < videos.length; i += 1) {
      var candidate = videos[i];
      if (!fallback) fallback = candidate;
      if (!firstMediaSource(candidate)) continue;

      var style = window.getComputedStyle(candidate);
      if (style.display !== 'none' && style.visibility !== 'hidden') {
        return candidate;
      }
    }

    return fallback && firstMediaSource(fallback) ? fallback : null;
  }

  function createSection(hero) {
    var main = document.getElementById('MainContent');
    if (!main || !hero || document.getElementById(ROOT_ID)) return null;

    var root = document.createElement('section');
    root.id = ROOT_ID;
    root.className = 'giclee-prehero-scrub';
    root.setAttribute('data-giclee-prehero-scrub', '1');
    root.setAttribute('data-video-ready', 'false');
    root.setAttribute('data-scrub-progress', '0');
    root.setAttribute('data-prehero-phase', 'scrub');
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
    video.preload = 'auto';
    video.autoplay = false;
    video.loop = false;
    video.controls = false;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.setAttribute('preload', 'auto');
    video.setAttribute('tabindex', '-1');
    video.setAttribute('focusable', 'false');
    video.setAttribute('inert', '');
    video.disablePictureInPicture = true;
    video.addEventListener('focus', function () {
      video.blur();
    });

    stage.appendChild(poster);
    stage.appendChild(video);
    root.appendChild(stage);
    main.insertBefore(root, hero);

    return {
      root: root,
      stage: stage,
      poster: poster,
      video: video,
      hero: hero,
    };
  }

  function initScrubbing(parts) {
    var root = parts.root;
    var video = parts.video;
    var duration = 0;
    var targetTime = 0;
    var requestedTime = 0;
    var progress = 0;
    var rafId = 0;
    var retryTimer = 0;
    var lastSeekAt = -Infinity;
    var seekCount = 0;
    var totalTravel = 0;
    var preHeroTravel = 0;
    var heroRiseStart = 0;
    var heroRiseTravel = 0;
    var heroRiseProgress = 0;
    var revealStart = 0;
    var revealOverlapTravel = 0;
    var rootStartY = 0;
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function clearRetryTimer() {
      if (retryTimer) window.clearTimeout(retryTimer);
      retryTimer = 0;
    }

    function quantizedTarget() {
      var maxTime = Math.max(0, duration - 0.033);
      var quantized = Math.round(targetTime * SEEK_FPS) / SEEK_FPS;
      return clamp(quantized, 0, maxTime);
    }

    function phaseFor(localScroll) {
      if (localScroll >= heroRiseStart) return 'hero-rise';
      if (localScroll >= revealStart) return 'scrub-reveal';
      return 'scrub';
    }

    function updateProgressFromScroll() {
      if (!duration || reducedMotion) return;

      var localScroll = clamp(scrollY() - rootStartY, 0, totalTravel);
      progress = clamp(localScroll / Math.max(1, preHeroTravel), 0, 1);
      heroRiseProgress = clamp(
        (localScroll - heroRiseStart) / Math.max(1, heroRiseTravel),
        0,
        1
      );
      targetTime = progress * Math.max(0, duration - 0.033);

      setAttrIfChanged(root, 'data-scrub-progress', progress.toFixed(4));
      setAttrIfChanged(root, 'data-hero-rise-progress', heroRiseProgress.toFixed(4));
      setAttrIfChanged(root, 'data-prehero-phase', phaseFor(localScroll));
      requestSeek();
    }

    function measureLayout() {
      if (reducedMotion) return;

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
      updateProgressFromScroll();
    }

    function scheduleAfterSeekBudget(now) {
      clearRetryTimer();
      var wait = Math.max(0, SEEK_INTERVAL_MS - (now - lastSeekAt));
      retryTimer = window.setTimeout(function () {
        retryTimer = 0;
        requestSeek();
      }, Math.ceil(wait));
    }

    function seekTick(now) {
      rafId = 0;
      if (!duration || reducedMotion || video.seeking || video.readyState < 1) return;

      var desired = quantizedTarget();
      requestedTime = desired;

      if (Math.abs(video.currentTime - desired) <= SEEK_EPSILON) return;

      if (now - lastSeekAt < SEEK_INTERVAL_MS) {
        scheduleAfterSeekBudget(now);
        return;
      }

      lastSeekAt = now;
      seekCount += 1;
      try {
        video.currentTime = desired;
      } catch (error) {
        scheduleAfterSeekBudget(now);
      }
    }

    function requestSeek() {
      if (!duration || reducedMotion || video.seeking || rafId || retryTimer) return;
      rafId = window.requestAnimationFrame(seekTick);
    }

    function onSeeked() {
      if (!duration || reducedMotion) return;
      var desired = quantizedTarget();
      if (Math.abs(video.currentTime - desired) > SEEK_EPSILON) {
        scheduleAfterSeekBudget(performance.now());
      }
    }

    function onMetadata() {
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      duration = video.duration;
      targetTime = 0;
      requestedTime = 0;
      root.setAttribute('data-video-ready', 'true');

      try {
        video.pause();
        video.currentTime = Math.min(0.001, Math.max(0, duration - 0.033));
      } catch (error) {
        /* Ignore the initial seek until the media timeline is ready. */
      }

      if (!reducedMotion) measureLayout();
    }

    video.addEventListener('loadedmetadata', onMetadata);
    video.addEventListener('durationchange', onMetadata);
    video.addEventListener('seeked', onSeeked);

    if (!reducedMotion) {
      window.addEventListener('scroll', updateProgressFromScroll, { passive: true });
      window.addEventListener('resize', measureLayout, { passive: true });
      window.addEventListener('orientationchange', measureLayout, { passive: true });
      window.addEventListener('pageshow', measureLayout, { passive: true });
    }

    window.GICLEE_PREHERO_SCRUB_STATUS = function () {
      return {
        ready: root.getAttribute('data-video-ready') === 'true',
        phase: root.getAttribute('data-prehero-phase'),
        duration: duration,
        progress: progress,
        targetTime: targetTime,
        smoothedTime: requestedTime,
        renderedTime: video.currentTime,
        seeking: video.seeking,
        seekFps: SEEK_FPS,
        seekCount: seekCount,
        totalTravel: totalTravel,
        preHeroTravel: preHeroTravel,
        revealStart: revealStart,
        revealOverlapTravel: revealOverlapTravel,
        heroRiseStart: heroRiseStart,
        heroRiseTravel: heroRiseTravel,
        heroRiseProgress: heroRiseProgress,
        rootStartY: rootStartY,
        source: video.currentSrc || video.src || '',
        config: {
          scrollHeightVh: SCROLL_HEIGHT_VH,
          revealOverlapVh: REVEAL_OVERLAP_VH,
          heroRiseVh: HERO_RISE_VH,
          scrubSeekFps: SEEK_FPS,
        },
      };
    };
  }

  function attachSource(parts) {
    var attempts = 0;
    var observer = null;
    var timer = 0;
    var dedicatedSource = window.GICLEE_PREHERO_SCRUB_VIDEO_URL || '';
    var fallbackApplied = false;

    function stopWatching() {
      if (observer) observer.disconnect();
      if (timer) window.clearInterval(timer);
      observer = null;
      timer = 0;
    }

    function applySource(source, poster) {
      if (!source) return false;
      if (poster) {
        parts.poster.style.backgroundImage =
          'url("' + String(poster).replace(/"/g, '%22') + '")';
      }
      stopWatching();
      parts.video.src = source;
      parts.video.load();
      return true;
    }

    function heroFallback() {
      var sourceVideo = findSourceVideo(parts.hero);
      return {
        source: firstMediaSource(sourceVideo),
        poster: firstPosterSource(parts.hero, sourceVideo),
      };
    }

    function tryAttach() {
      attempts += 1;
      var fallback = heroFallback();
      var source = dedicatedSource || fallback.source;
      var poster = firstPosterSource(parts.hero, findSourceVideo(parts.hero));

      if (!source) {
        if (attempts >= SOURCE_RETRY_LIMIT) stopWatching();
        return false;
      }

      return applySource(source, poster);
    }

    parts.video.addEventListener('error', function () {
      if (!dedicatedSource || fallbackApplied) return;
      fallbackApplied = true;
      var fallback = heroFallback();
      if (fallback.source && fallback.source !== dedicatedSource) {
        parts.root.setAttribute('data-video-fallback', 'true');
        applySource(fallback.source, fallback.poster);
      }
    });

    initScrubbing(parts);
    if (tryAttach()) return;

    observer = new MutationObserver(tryAttach);
    observer.observe(parts.hero, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['src'],
    });

    timer = window.setInterval(tryAttach, SOURCE_RETRY_MS);
  }

  function boot() {
    if (CONFIG.enabled === false || document.getElementById(ROOT_ID)) return;
    var hero = findHero();
    if (!hero) return;
    var parts = createSection(hero);
    if (!parts) return;
    attachSource(parts);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
