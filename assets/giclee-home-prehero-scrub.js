/*
 * Homepage pre-hero video scrub.
 * Critical performance rule: never issue a new seek while the previous seek is active.
 */
(function () {
  'use strict';

  var ROOT_ID = 'giclee-prehero-video-scrub';
  var LERP = 0.08;
  var SEEK_EPSILON = 0.01;
  var SOURCE_RETRY_MS = 250;
  var SOURCE_RETRY_LIMIT = 80;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
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
    var currentTime = 0;
    var progress = 0;
    var rafId = 0;
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function measureProgress() {
      if (!duration || reducedMotion) return;
      var rect = root.getBoundingClientRect();
      var travel = Math.max(1, root.offsetHeight - window.innerHeight);
      progress = clamp(-rect.top / travel, 0, 1);
      targetTime = progress * Math.max(0, duration - 0.033);
      requestTick();
    }

    function tick() {
      rafId = 0;
      if (!duration || reducedMotion) return;

      currentTime += (targetTime - currentTime) * LERP;

      /*
       * CRITICAL VIDEO SCRUBBING TECHNIQUE
       * Update the frame only after the browser has finished the previous seek.
       */
      if (
        !video.seeking &&
        video.readyState >= 1 &&
        Math.abs(video.currentTime - currentTime) > SEEK_EPSILON
      ) {
        try {
          video.currentTime = currentTime;
        } catch (error) {
          /* The media timeline may not be seekable for the first few frames. */
        }
      }

      if (
        Math.abs(targetTime - currentTime) > 0.001 ||
        video.seeking ||
        Math.abs(video.currentTime - currentTime) > SEEK_EPSILON
      ) {
        requestTick();
      }
    }

    function requestTick() {
      if (!rafId) rafId = window.requestAnimationFrame(tick);
    }

    function onMetadata() {
      if (!Number.isFinite(video.duration) || video.duration <= 0) return;
      duration = video.duration;
      currentTime = 0;
      targetTime = 0;
      root.setAttribute('data-video-ready', 'true');

      try {
        video.pause();
        video.currentTime = Math.min(0.001, Math.max(0, duration - 0.033));
      } catch (error) {
        /* Ignore the initial seek until the media timeline is ready. */
      }

      if (!reducedMotion) measureProgress();
    }

    video.addEventListener('loadedmetadata', onMetadata);
    video.addEventListener('durationchange', onMetadata);
    video.addEventListener('seeked', requestTick);

    if (!reducedMotion) {
      window.addEventListener('scroll', measureProgress, { passive: true });
      window.addEventListener('resize', measureProgress, { passive: true });
      window.addEventListener('orientationchange', measureProgress, { passive: true });
    }

    window.GICLEE_PREHERO_SCRUB_STATUS = function () {
      return {
        ready: root.getAttribute('data-video-ready') === 'true',
        duration: duration,
        progress: progress,
        targetTime: targetTime,
        smoothedTime: currentTime,
        renderedTime: video.currentTime,
        seeking: video.seeking,
        source: video.currentSrc || video.src || '',
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
        parts.poster.style.backgroundImage = 'url("' + String(poster).replace(/"/g, '%22') + '")';
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
    if (document.getElementById(ROOT_ID)) return;
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
