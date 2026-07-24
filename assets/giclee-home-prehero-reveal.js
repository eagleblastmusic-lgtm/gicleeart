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
  var COPY_HOLD_VH = configNumber('copyHoldVh', 200, 0, 800);
  var SOURCE_RETRY_MS = 250;
  var SOURCE_RETRY_LIMIT = 40;
  var DEFAULT_COPY_LINES = [
    'Fotografia i obraz zaczynają żyć w pełni',
    'dopiero wtedy, gdy opuszczają ekran',
    'i stają się częścią świata fizycznego.',
  ];
  var COPY_ENABLED = CONFIG.copyEnabled !== false;
  var COPY_LINES = configuredCopyLines();
  var WORD_DIM_OPACITY = 0.18;
  var WORD_STAGGER = 0.08;
  /* Shorter than GSAP default 1 — each word hits full white sooner, like the Napis reference feel. */
  var WORD_DURATION = 0.4;
  /* Begin word brightening before the portal is fully open (eased progress). */
  var WORD_REVEAL_START = 0.52;
  /* Share of the word wave that plays during late portal open; rest finishes in the hold. */
  var WORD_PORTAL_SHARE = 0.4;
  /* Finish the remaining word wave in the first half of the copy-hold scroll. */
  var WORD_REVEAL_COMPLETE = 0.5;
  var COPY_RISE_VH = 32;
  /* Start already ~3/4 up the path; finish centred as the portal sides fully open. */
  var COPY_RISE_FROM = 0.75;
  var COPY_APPEAR_AT = 0.08;
  var COPY_FADE_END = 0.88;
  /* After word opacity finishes, each word recedes (to ~12%), then slowly fades to 0. */
  var COPY_DEPTH_Z_PX = -360;
  var COPY_DEPTH_SCALE_TO = 0.76;
  var COPY_DEPTH_OPACITY_TO = 0.12;
  var COPY_DEPTH_HERO_SHARE = 0.55;
  var DEPTH_STAGGER = WORD_STAGGER;
  /* Recession + trailing slow fade-out to zero. */
  var DEPTH_DURATION = 0.72;
  /* Share of each word slot for perspective→12%; remainder slowly fades 12%→0. */
  var DEPTH_MOTION_SHARE = 0.58;
  /* Gallery clip fades in only after the portal is fully open (early copy-hold). */
  var PORTAL_VIDEO_FADE_HOLD_FRACTION = 0.28;
  /* Fade out starts at this film time (seconds) during scroll scrub. */
  var PORTAL_VIDEO_FADE_OUT_AT = 5;
  var PORTAL_VIDEO_FADE_OUT_DURATION = 2.2;
  var PORTAL_SEEK_FPS = 30;
  var PORTAL_FRAME_END_EPSILON = 0.04;
  /* Scrub media softens with the portal/curtain open (px at full open). */
  var PREHERO_CURTAIN_BLUR_PX = 52;

  var scrubRoot = null;
  var scrubStage = null;
  var revealRoot = null;
  var nextVisual = null;
  var portalVideo = null;
  var portalDuration = 0;
  var portalVideoOpacity = 0;
  var portalSeekRafId = 0;
  var portalLastSeekAt = 0;
  var portalSeekCount = 0;
  var copy = null;
  var copyLines = [];
  var copyWords = [];
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
  var copyHoldTravel = 0;
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

  /* Milder ease-out: opens a bit faster early, then settles — less aggressive than cubic. */
  function easeOutQuad(value) {
    var t = clamp(value, 0, 1);
    return 1 - (1 - t) * (1 - t);
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

  function fillCopyText(text) {
    copyLines = [];
    copyWords = [];
    if (!text) return;
    text.textContent = '';
    text.setAttribute('aria-label', COPY_LINES.join(' '));
    COPY_LINES.forEach(function (lineText, index) {
      var line = document.createElement('span');
      line.className = 'giclee-prehero-reveal__copy-line';
      line.setAttribute('aria-hidden', 'true');
      line.setAttribute('data-line', String(index + 1));
      var parts = String(lineText || '')
        .trim()
        .split(/\s+/)
        .filter(Boolean);
      parts.forEach(function (part, partIndex) {
        var word = document.createElement('span');
        word.className = 'giclee-prehero-reveal__copy-word';
        word.textContent = part;
        line.appendChild(word);
        copyWords.push(word);
        if (partIndex < parts.length - 1) {
          line.appendChild(document.createTextNode(' '));
        }
      });
      text.appendChild(line);
      copyLines.push(line);
    });
  }

  function createCopy() {
    if (!COPY_ENABLED || !revealRoot) return null;
    copy = document.createElement('div');
    copy.className = 'giclee-prehero-reveal__copy';
    var text = document.createElement('p');
    text.className = 'giclee-prehero-reveal__copy-text';
    fillCopyText(text);
    copy.appendChild(text);
    revealRoot.appendChild(copy);
    return copy;
  }

  function ensureCopyWords() {
    if (!COPY_ENABLED) {
      copy = null;
      copyLines = [];
      copyWords = [];
      return;
    }
    if (!copy && revealRoot) createCopy();
    if (!copy) return;
    var text = copy.querySelector('.giclee-prehero-reveal__copy-text');
    if (!text) {
      text = document.createElement('p');
      text.className = 'giclee-prehero-reveal__copy-text';
      copy.appendChild(text);
    }
    if (!copy.querySelector('.giclee-prehero-reveal__copy-word')) {
      fillCopyText(text);
      return;
    }
    copyLines = Array.prototype.slice.call(
      copy.querySelectorAll('.giclee-prehero-reveal__copy-line')
    );
    copyWords = Array.prototype.slice.call(
      copy.querySelectorAll('.giclee-prehero-reveal__copy-word')
    );
  }

  function portalVideoUrl() {
    return String(window.GICLEE_PREHERO_PORTAL_VIDEO_URL || '').trim();
  }

  function createPortalVideo() {
    if (!nextVisual) return null;
    var existing = nextVisual.querySelector('.giclee-prehero-reveal__portal-video');
    if (existing) {
      portalVideo = existing;
      return portalVideo;
    }
    var url = portalVideoUrl();
    if (!url) return null;
    portalVideo = document.createElement('video');
    portalVideo.className = 'giclee-prehero-reveal__portal-video';
    portalVideo.muted = true;
    portalVideo.defaultMuted = true;
    portalVideo.playsInline = true;
    portalVideo.preload = 'auto';
    portalVideo.autoplay = false;
    portalVideo.loop = false;
    portalVideo.controls = false;
    portalVideo.setAttribute('muted', '');
    portalVideo.setAttribute('playsinline', '');
    portalVideo.setAttribute('webkit-playsinline', '');
    portalVideo.setAttribute('aria-hidden', 'true');
    portalVideo.setAttribute('tabindex', '-1');
    portalVideo.disablePictureInPicture = true;
    portalVideo.addEventListener('loadedmetadata', onPortalVideoMetadata);
    portalVideo.addEventListener('seeked', onPortalVideoSeeked);
    portalVideo.src = url;
    nextVisual.appendChild(portalVideo);
    return portalVideo;
  }

  function onPortalVideoMetadata() {
    if (!portalVideo) return;
    if (!Number.isFinite(portalVideo.duration) || portalVideo.duration <= 0) return;
    portalDuration = portalVideo.duration;
    try {
      portalVideo.pause();
      portalVideo.currentTime = 0;
    } catch (error) {}
    setAttrIfChanged(scrubRoot, 'data-portal-video-ready', 'true');
    requestPortalSeek();
  }

  function portalRevealEndScroll() {
    return revealStart + revealTravel;
  }

  function portalScrubProgress() {
    /* Scrub starts with the post-portal fade — not during the panel opening. */
    var start = portalRevealEndScroll();
    var travel = Math.max(1, heroRiseStart - start);
    return clamp((localScroll - start) / travel, 0, 1);
  }

  function portalTargetTime() {
    if (!portalDuration) return 0;
    var frameCountLocal = Math.max(1, Math.round(portalDuration * PORTAL_SEEK_FPS));
    var maxFrame = Math.max(0, frameCountLocal - 1);
    var frame = clamp(Math.round(portalScrubProgress() * maxFrame), 0, maxFrame);
    var lastFrameTime = Math.max(0, portalDuration - PORTAL_FRAME_END_EPSILON);
    return clamp(frame / PORTAL_SEEK_FPS, 0, lastFrameTime);
  }

  function onPortalVideoSeeked() {
    if (!portalVideo || !portalDuration || reducedMotion) return;
    var desired = portalTargetTime();
    if (Math.abs(portalVideo.currentTime - desired) > 0.04) requestPortalSeek();
  }

  function portalSeekTick(now) {
    portalSeekRafId = 0;
    if (!portalVideo || !portalDuration || reducedMotion) return;
    if (portalVideo.seeking || portalVideo.readyState < 1) return;
    var desired = portalTargetTime();
    if (Math.abs(portalVideo.currentTime - desired) <= 0.03) return;
    if (now - portalLastSeekAt < 1000 / PORTAL_SEEK_FPS) {
      portalSeekRafId = window.requestAnimationFrame(portalSeekTick);
      return;
    }
    portalLastSeekAt = now;
    portalSeekCount += 1;
    try {
      portalVideo.currentTime = desired;
    } catch (error) {
      portalSeekRafId = window.requestAnimationFrame(portalSeekTick);
    }
  }

  function requestPortalSeek() {
    if (!portalVideo || !portalDuration || reducedMotion || portalSeekRafId) return;
    if (portalVideo.seeking) return;
    portalSeekRafId = window.requestAnimationFrame(portalSeekTick);
  }

  function portalVideoTimeFade(timeSeconds) {
    if (!Number.isFinite(timeSeconds)) return 1;
    var fadeOutEnd = PORTAL_VIDEO_FADE_OUT_AT + PORTAL_VIDEO_FADE_OUT_DURATION;
    if (timeSeconds <= PORTAL_VIDEO_FADE_OUT_AT) return 1;
    return 1 - smoothstep(rangeProgress(timeSeconds, PORTAL_VIDEO_FADE_OUT_AT, fadeOutEnd));
  }

  function applyPortalVideo(eased) {
    if (!nextVisual) return;
    var portalOpen = eased >= 0.999;
    var fade = 0;
    if (portalOpen) {
      if (reducedMotion) {
        fade = portalVideoTimeFade(portalTargetTime());
      } else {
        var start = portalRevealEndScroll();
        var holdTravel = Math.max(1, heroRiseStart - start);
        var fadeEnd = start + holdTravel * PORTAL_VIDEO_FADE_HOLD_FRACTION;
        var fadeIn = smoothstep(rangeProgress(localScroll, start, fadeEnd));
        fade = fadeIn * portalVideoTimeFade(portalTargetTime());
      }
    }
    portalVideoOpacity = fade;
    setStyleIfChanged(
      nextVisual,
      '--giclee-prehero-portal-video-opacity',
      fade.toFixed(3),
      '_gicleePortalVideoOpacity'
    );
    if (portalVideo && portalDuration && portalOpen) requestPortalSeek();
  }

  function createIntegratedReveal() {
    if (!scrubRoot || !scrubStage) return false;
    var existing = scrubStage.querySelector('.' + REVEAL_CLASS);
    if (existing) {
      revealRoot = existing;
      nextVisual = existing.querySelector('.giclee-prehero-reveal__visual');
      copy = existing.querySelector('.giclee-prehero-reveal__copy');
      ensureCopyWords();
      createPortalVideo();
      return !!nextVisual;
    }
    revealRoot = document.createElement('div');
    revealRoot.className = REVEAL_CLASS;
    revealRoot.setAttribute('data-reveal-progress', '0');
    nextVisual = document.createElement('div');
    nextVisual.className = 'giclee-prehero-reveal__visual';
    nextVisual.setAttribute('aria-hidden', 'true');
    revealRoot.appendChild(nextVisual);
    createPortalVideo();
    createCopy();
    scrubStage.appendChild(revealRoot);
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
    copyHoldTravel = Math.min(
      Math.max(0, totalTravel - heroRiseTravel),
      viewport * (COPY_HOLD_VH / 100)
    );
    preHeroTravel = Math.max(1, totalTravel - heroRiseTravel);
    heroRiseStart = preHeroTravel;
    var scrubEnd = Math.max(1, heroRiseStart - copyHoldTravel);
    revealTravel = Math.min(scrubEnd, viewport * (REVEAL_OVERLAP_VH / 100));
    revealStart = Math.max(0, scrubEnd - revealTravel);
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
    if (!copy || !copyWords.length) {
      copyOpacity = 0;
      return;
    }

    var revealEndScroll = revealStart + revealTravel;
    var copyOut = 1 - smoothstep(
      rangeProgress(
        localScroll,
        heroRiseStart,
        heroRiseStart + Math.max(1, heroRiseTravel * 0.22)
      )
    );
    var fadeIn = reducedMotion
      ? 1
      : smoothstep(rangeProgress(eased, COPY_APPEAR_AT, COPY_FADE_END));
    var riseIn = reducedMotion
      ? 1
      : clamp((eased - COPY_APPEAR_AT) / Math.max(0.0001, 1 - COPY_APPEAR_AT), 0, 1);
    var holdTravel = Math.max(1, heroRiseStart - revealEndScroll);
    var wordTravelEnd = revealEndScroll + holdTravel * WORD_REVEAL_COMPLETE;
    var depthEnd =
      heroRiseStart + Math.max(1, heroRiseTravel * COPY_DEPTH_HERO_SHARE);
    var depthTimeline = reducedMotion
      ? 0
      : easeOutQuad(rangeProgress(localScroll, wordTravelEnd, depthEnd));
    var timelineProgress;
    if (reducedMotion) {
      timelineProgress = 1;
    } else if (localScroll < revealEndScroll) {
      timelineProgress =
        rangeProgress(eased, WORD_REVEAL_START, 1) * WORD_PORTAL_SHARE;
    } else {
      timelineProgress =
        WORD_PORTAL_SHARE +
        (1 - WORD_PORTAL_SHARE) *
          rangeProgress(localScroll, revealEndScroll, wordTravelEnd);
    }
    var copyY = COPY_RISE_VH * (1 - COPY_RISE_FROM) * (1 - riseIn);
    var wordCount = copyWords.length;
    var total = WORD_DURATION + WORD_STAGGER * Math.max(0, wordCount - 1);
    var depthTotal = DEPTH_DURATION + DEPTH_STAGGER * Math.max(0, wordCount - 1);

    setStyleIfChanged(
      copy,
      '--giclee-prehero-copy-y',
      copyY.toFixed(2) + 'vh',
      '_gicleeRevealCopyY'
    );

    copyOpacity = 0;
    copyWords.forEach(function (word, index) {
      var wordOpacity;
      var wordDepth = 0;
      if (reducedMotion) {
        wordOpacity = copyOut;
      } else {
        var wordStart = (index * WORD_STAGGER) / total;
        var wordEnd = (index * WORD_STAGGER + WORD_DURATION) / total;
        var wordIn = rangeProgress(timelineProgress, wordStart, wordEnd);
        var depthStart = (index * DEPTH_STAGGER) / depthTotal;
        var depthWordEnd = (index * DEPTH_STAGGER + DEPTH_DURATION) / depthTotal;
        var depthSlot = Math.max(0.0001, depthWordEnd - depthStart);
        var depthMotionEnd = depthStart + depthSlot * DEPTH_MOTION_SHARE;
        wordDepth = smoothstep(rangeProgress(depthTimeline, depthStart, depthMotionEnd));
        var depthFade = 1 - (1 - COPY_DEPTH_OPACITY_TO) * wordDepth;
        if (wordDepth >= 0.999) {
          var trail = smoothstep(
            rangeProgress(depthTimeline, depthMotionEnd, depthWordEnd)
          );
          depthFade = COPY_DEPTH_OPACITY_TO * (1 - trail);
        }
        wordOpacity =
          (WORD_DIM_OPACITY + (1 - WORD_DIM_OPACITY) * wordIn) *
          fadeIn *
          copyOut *
          depthFade;
      }
      var wordZ = COPY_DEPTH_Z_PX * wordDepth;
      var wordScale = 1 - (1 - COPY_DEPTH_SCALE_TO) * wordDepth;
      copyOpacity = Math.max(copyOpacity, wordOpacity);
      setStyleIfChanged(
        word,
        '--giclee-prehero-copy-word-opacity',
        wordOpacity.toFixed(3),
        '_gicleeRevealWordOpacity'
      );
      setStyleIfChanged(
        word,
        '--giclee-prehero-copy-word-z',
        wordZ.toFixed(2) + 'px',
        '_gicleeRevealWordZ'
      );
      setStyleIfChanged(
        word,
        '--giclee-prehero-copy-word-scale',
        wordScale.toFixed(4),
        '_gicleeRevealWordScale'
      );
    });
    setStyleIfChanged(copy, '--giclee-prehero-copy-opacity', copyOpacity.toFixed(3), '_gicleeRevealCopyOpacity');
  }

  function applyPreheroCurtainBlur(eased) {
    if (!scrubStage) return;
    var amount = reducedMotion ? 0 : PREHERO_CURTAIN_BLUR_PX * clamp(eased, 0, 1);
    setStyleIfChanged(
      scrubStage,
      '--giclee-prehero-media-blur',
      amount.toFixed(2) + 'px',
      '_gicleePreheroMediaBlur'
    );
  }

  function applyFrame() {
    if (!revealRoot || !scrubRoot) return;
    frameCount += 1;
    var eased = easeOutQuad(currentProgress);
    var inset = 50 * (1 - eased);
    setStyleIfChanged(revealRoot, '--giclee-prehero-reveal-inset', inset.toFixed(2) + '%', '_gicleeRevealInset');
    setStyleIfChanged(revealRoot, '--giclee-prehero-reveal-progress', eased.toFixed(3), '_gicleeRevealProgress');
    applyPreheroCurtainBlur(eased);
    applyPortalVideo(eased);
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
        insetPercent: 50 * (1 - easeOutQuad(currentProgress)),
        copyOpacity: copyOpacity,
        copyLines: copyLines.length,
        copyWords: copyWords.length,
        configuredCopyLines: COPY_LINES.slice(),
        portalVideoUrl: portalVideoUrl(),
        portalVideoReady: scrubRoot.getAttribute('data-portal-video-ready') === 'true',
        portalVideoOpacity: portalVideoOpacity,
        portalScrubProgress: portalScrubProgress(),
        portalDuration: portalDuration,
        portalSeekCount: portalSeekCount,
        totalTravel: totalTravel,
        preHeroTravel: preHeroTravel,
        revealStart: revealStart,
        revealTravel: revealTravel,
        copyHoldTravel: copyHoldTravel,
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
          copyHoldVh: COPY_HOLD_VH,
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
