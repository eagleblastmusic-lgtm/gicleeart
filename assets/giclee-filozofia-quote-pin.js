/* Filozofia marki — pin cytatu, potem portal odsłania Wrota (bez wjazdu sekcji). */
(function () {
  'use strict';

  if (window.__GICLEE_FILOZOFIA_QUOTE_PIN__) return;
  window.__GICLEE_FILOZOFIA_QUOTE_PIN__ = true;

  if (!document.body.classList.contains('template-page-filozofia-marki')) return;

  var main = document.getElementById('MainContent');
  if (!main) return;

  var topDivider = main.querySelector('.shopify-section[id$="__divider_Utf3HQ"]');
  var quoteSection = main.querySelector('.shopify-section[id$="__section_tAj94h"]');
  var bottomDivider = main.querySelector('.shopify-section[id$="__divider_H4ahef"]');
  var wrotaRoot = main.querySelector('[data-fm-portal-root]');
  var wrotaSection = wrotaRoot
    ? wrotaRoot.closest('.shopify-section')
    : main.querySelector('.shopify-section[id$="__media_with_content_Wrota"]');

  if (!topDivider || !quoteSection || !bottomDivider) return;
  if (topDivider.closest('.giclee-fm-quote-pin-track')) return;

  var track = document.createElement('div');
  track.className = 'giclee-fm-quote-pin-track';

  var sticky = document.createElement('div');
  sticky.className = 'giclee-fm-quote-pin-sticky';

  var bgLayer = document.createElement('div');
  bgLayer.className = 'giclee-fm-quote-bg-layer';
  bgLayer.setAttribute('aria-hidden', 'true');
  sticky.appendChild(bgLayer);

  var parent = topDivider.parentNode;
  if (!parent) return;

  parent.insertBefore(track, topDivider);

  var node = topDivider;
  while (node) {
    var next = node.nextElementSibling;
    sticky.appendChild(node);
    if (node === bottomDivider) break;
    node = next;
  }

  var quoteParallaxEnabled = true;
  var quoteParallaxStrength = 100;

  function applyQuoteBackground() {
    var source = document.getElementById('giclee-fm-quote-bg-assets');
    if (!source) return;
    var url = '';
    try {
      var data = JSON.parse(source.textContent || '{}');
      url = data && data.image ? String(data.image) : '';
    } catch (_error) {
      return;
    }
    if (!url) return;
    var probe = new Image();
    probe.onload = function () {
      sticky.classList.add('has-fm-quote-bg');
      sticky.style.setProperty('--fm-quote-bg-image', 'url("' + url + '")');
      sticky.setAttribute('data-fm-quote-bg', 'ready');
      applyQuoteBandOpacities();
    };
    probe.onerror = function () {
      sticky.classList.remove('has-fm-quote-bg');
      sticky.style.removeProperty('--fm-quote-bg-image');
      sticky.setAttribute('data-fm-quote-bg', 'missing');
    };
    probe.decoding = 'async';
    probe.src = url;
  }

  function clampOpacityPct(value, fallback) {
    var n = Number(value);
    if (!Number.isFinite(n)) n = fallback;
    return Math.min(100, Math.max(0, n)) / 100;
  }

  function applyQuoteBandOpacities() {
    var source = document.getElementById('giclee-fm-quote-screen-settings');
    var textPct = 100;
    var topAbovePct = 100;
    var topBelowPct = 100;
    var bottomAbovePct = 100;
    var bottomBelowPct = 100;
    if (source) {
      try {
        var data = JSON.parse(source.textContent || '{}');
        textPct = data.textBgOpacity;
        topAbovePct =
          data.dividerTopAboveOpacity != null
            ? data.dividerTopAboveOpacity
            : data.dividerTopBgOpacity;
        topBelowPct =
          data.dividerTopBelowOpacity != null
            ? data.dividerTopBelowOpacity
            : data.dividerTopBgOpacity;
        bottomAbovePct =
          data.dividerBottomAboveOpacity != null
            ? data.dividerBottomAboveOpacity
            : data.dividerBottomBgOpacity;
        bottomBelowPct =
          data.dividerBottomBelowOpacity != null
            ? data.dividerBottomBelowOpacity
            : data.dividerBottomBgOpacity;
        if (typeof data.parallaxEnabled === 'boolean') {
          quoteParallaxEnabled = data.parallaxEnabled;
        }
        if (Number.isFinite(Number(data.parallaxStrength))) {
          quoteParallaxStrength = Number(data.parallaxStrength);
        }
      } catch (_error) {}
    }
    sticky.style.setProperty(
      '--fm-quote-text-bg-opacity',
      clampOpacityPct(textPct, 100).toFixed(4)
    );
    sticky.style.setProperty(
      '--fm-quote-divider-top-above-opacity',
      clampOpacityPct(topAbovePct, 100).toFixed(4)
    );
    sticky.style.setProperty(
      '--fm-quote-divider-top-below-opacity',
      clampOpacityPct(topBelowPct, 100).toFixed(4)
    );
    sticky.style.setProperty(
      '--fm-quote-divider-bottom-above-opacity',
      clampOpacityPct(bottomAbovePct, 100).toFixed(4)
    );
    sticky.style.setProperty(
      '--fm-quote-divider-bottom-below-opacity',
      clampOpacityPct(bottomBelowPct, 100).toFixed(4)
    );
  }

  applyQuoteBackground();
  applyQuoteBandOpacities();

  var MAX_SHIFT_X = 26;
  var MAX_SHIFT_Y = 16;
  var EASE = 0.075;
  var targetX = 0;
  var targetY = 0;
  var curX = 0;
  var curY = 0;
  var parallaxRafId = 0;

  function applyParallax() {
    var factor = quoteParallaxStrength / 100;
    sticky.style.setProperty('--fm-quote-bg-px', (-curX * MAX_SHIFT_X * factor).toFixed(2) + 'px');
    sticky.style.setProperty('--fm-quote-bg-py', (-curY * MAX_SHIFT_Y * factor).toFixed(2) + 'px');
  }

  function tickParallax() {
    parallaxRafId = 0;
    curX += (targetX - curX) * EASE;
    curY += (targetY - curY) * EASE;
    applyParallax();
    if (Math.abs(targetX - curX) > 0.0008 || Math.abs(targetY - curY) > 0.0008) {
      parallaxRafId = window.requestAnimationFrame(tickParallax);
    }
  }

  function startParallaxLoop() {
    if (!parallaxRafId) parallaxRafId = window.requestAnimationFrame(tickParallax);
  }

  function onPointerMove(event) {
    if (reducedMotion || !quoteParallaxEnabled || !sticky.classList.contains('has-fm-quote-bg')) return;
    var vw = window.innerWidth || 1;
    var vh = window.innerHeight || 1;
    targetX = Math.min(Math.max((event.clientX / vw) * 2 - 1, -1), 1);
    targetY = Math.min(Math.max((event.clientY / vh) * 2 - 1, -1), 1);
    startParallaxLoop();
  }

  function onPointerLeave() {
    targetX = 0;
    targetY = 0;
    startParallaxLoop();
  }

  window.addEventListener('pointermove', onPointerMove, { passive: true });
  document.addEventListener('pointerleave', onPointerLeave, { passive: true });

  track.appendChild(sticky);

  // Host Wrota MUSI być w tracku (nie pod nim) — inaczej film ładuje/renderuje
  // się dopiero gdy dół runwayu dojedzie do viewportu.
  if (wrotaSection instanceof HTMLElement) {
    wrotaSection.classList.add('giclee-fm-wrota-section');
    track.insertBefore(wrotaSection, sticky);
  }

  // Stage zostaje w scrub root (Film-scroll), ale wizualnie jest fixed overlay.
  var stage =
    wrotaRoot instanceof HTMLElement
      ? wrotaRoot.querySelector('.media-block__scroll-stage[data-fm-portal]')
      : null;

  if (stage instanceof HTMLElement) {
    stage.classList.add('giclee-fm-portal-on-quote');
  }

  // Scrub Wrota nie ma osobno wjeżdżać — jego wysokość jedzie w tracku cytatu.
  var filmDurationVh = 6.5;
  if (wrotaRoot instanceof HTMLElement) {
    var scrubRaw = window
      .getComputedStyle(wrotaRoot)
      .getPropertyValue('--scroll-scrub-height')
      .trim();
    // Bierz tylko wartość w vh (nie zresolwowane px).
    var scrubMatch = scrubRaw.match(/([\d.]+)\s*vh/i);
    if (scrubMatch) {
      filmDurationVh = Number.parseFloat(scrubMatch[1]) / 100;
      if (!Number.isFinite(filmDurationVh) || filmDurationVh <= 0) filmDurationVh = 6.5;
    }
    wrotaRoot.classList.add('giclee-fm-wrota-runway-collapsed');
    wrotaRoot.dataset.fmExternalScrub = '1';
  }
  track.style.setProperty('--fm-wrota-film-duration', String(filmDurationVh));


  document.body.classList.add('giclee-fm-quote-curtain-ready');

  var reducedMotion = !!(
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  var ticking = false;
  var portalSmooth = 0;
  var portalRaf = 0;
  var video =
    stage instanceof HTMLElement
      ? stage.querySelector('[data-scroll-native-video]')
      : null;

  // Górne menu: ta sama kurtyna co prehero, start od klatki 420 filmu Wrota.
  var HEADER_HIDE_START_FRAME = 420;
  var HEADER_CHROME_CLASS = 'giclee-prehero-chrome-header';
  var HEADER_ROOT_CLASS = 'giclee-prehero-chrome-enabled';
  var HEADER_TAU_MS = 88;
  var HEADER_EPSILON = 0.0005;
  var chromeHeaderComponent = null;
  var chromeHeaderRow = null;
  var chromeHeader = null;
  var chromeHeaderHeight = 60;
  var visibleMenuEdge = 60;
  var chromeTarget = 0;
  var chromeCurrent = 0;
  var chromeRaf = 0;
  var chromeLastTime = 0;

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

  // GSAP power2.out — 1-(1-t)^2 (prehero / kurtyna)
  function easePower2Out(t) {
    var x = clamp(t, 0, 1);
    return 1 - (1 - x) * (1 - x);
  }

  function readCssNumber(el, name, fallback) {
    var raw = window.getComputedStyle(el).getPropertyValue(name).trim();
    var n = Number.parseFloat(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  function findChromeHeader() {
    chromeHeaderComponent = document.getElementById('header-component');
    if (!chromeHeaderComponent) return null;
    chromeHeaderRow = chromeHeaderComponent.querySelector('.header__row--top');
    return chromeHeaderComponent.closest('.header-section') || chromeHeaderComponent;
  }

  function readCssHeaderHeight() {
    var value = parseFloat(
      getComputedStyle(document.body).getPropertyValue('--header-height')
    );
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function measureChromeHeader() {
    if (!chromeHeader) return;
    var rowRect = chromeHeaderRow ? chromeHeaderRow.getBoundingClientRect() : null;
    var componentRect = chromeHeaderComponent
      ? chromeHeaderComponent.getBoundingClientRect()
      : null;
    var headerRect = chromeHeader.getBoundingClientRect();
    var measured = Math.round(
      readCssHeaderHeight() ||
        (rowRect && rowRect.height) ||
        (componentRect && componentRect.height) ||
        headerRect.height ||
        60
    );
    chromeHeaderHeight = Math.max(1, measured);
    document.documentElement.style.setProperty(
      '--giclee-prehero-header-height',
      chromeHeaderHeight + 'px'
    );
  }

  function collapseDistance() {
    var viewport = window.innerHeight || document.documentElement.clientHeight || 800;
    return Math.max(chromeHeaderHeight * 4, Math.min(viewport * 0.58, 560));
  }

  function readFrameCount() {
    var el =
      (video instanceof HTMLElement && video) ||
      (wrotaRoot instanceof HTMLElement &&
        wrotaRoot.querySelector('[data-frame-count]')) ||
      null;
    var n = el
      ? Number.parseInt(el.getAttribute('data-frame-count') || '', 10)
      : NaN;
    return Number.isFinite(n) && n > 1 ? n : 778;
  }

  function headerHideProgressFromFilm(filmProgress) {
    var lastFrame = Math.max(1, readFrameCount() - 1);
    var startProgress = HEADER_HIDE_START_FRAME / lastFrame;
    var viewport = window.innerHeight || 1;
    var filmPx =
      readCssNumber(track, '--fm-wrota-film-duration', filmDurationVh) * viewport;
    var span = collapseDistance() / Math.max(1, filmPx);
    var raw = (clamp(filmProgress, 0, 1) - startProgress) / Math.max(0.0001, span);
    return smoothstep(clamp(raw, 0, 1));
  }

  function applyChromeFrame() {
    if (!chromeHeader) return;
    var eased = clamp(chromeCurrent, 0, 1);
    var distance = chromeHeaderHeight * eased;
    visibleMenuEdge = Math.max(0, chromeHeaderHeight - distance);
    document.documentElement.style.setProperty(
      '--giclee-prehero-header-y',
      (-distance).toFixed(2) + 'px'
    );
    document.documentElement.style.setProperty(
      '--fm-quote-menu-edge',
      visibleMenuEdge.toFixed(2) + 'px'
    );
    sticky.setAttribute(
      'data-fm-gradient-menu-edge',
      visibleMenuEdge.toFixed(2)
    );
    syncQuoteGradientDock();
    chromeHeader.style.setProperty(
      'pointer-events',
      eased <= 0.96 ? 'auto' : 'none',
      'important'
    );
    if (stage instanceof HTMLElement) {
      stage.setAttribute('data-fm-header-chrome', eased.toFixed(3));
    }
  }

  function chromeTick(now) {
    chromeRaf = 0;
    if (reducedMotion) {
      chromeCurrent = chromeTarget;
    } else {
      var delta = chromeLastTime ? Math.min(64, now - chromeLastTime) : 16.67;
      chromeLastTime = now;
      chromeCurrent += (chromeTarget - chromeCurrent) * expAlpha(delta, HEADER_TAU_MS);
    }
    if (Math.abs(chromeTarget - chromeCurrent) <= HEADER_EPSILON) {
      chromeCurrent = chromeTarget;
    }
    applyChromeFrame();
    if (!reducedMotion && Math.abs(chromeTarget - chromeCurrent) > HEADER_EPSILON) {
      chromeRaf = window.requestAnimationFrame(chromeTick);
    } else {
      chromeLastTime = 0;
    }
  }

  function syncQuoteGradientDock() {
    var stickyTop = sticky.getBoundingClientRect().top;
    var gradientTop = Math.max(0, visibleMenuEdge - stickyTop);
    var gradientEdge = stickyTop + gradientTop;
    var docked =
      stickyTop <= visibleMenuEdge + 0.5 &&
      Math.abs(gradientEdge - visibleMenuEdge) <= 0.5;
    sticky.style.setProperty(
      '--fm-quote-gradient-top',
      gradientTop.toFixed(2) + 'px'
    );
    sticky.setAttribute(
      'data-fm-gradient-top',
      gradientTop.toFixed(2)
    );
    sticky.setAttribute(
      'data-fm-gradient-edge',
      gradientEdge.toFixed(2)
    );
    sticky.setAttribute(
      'data-fm-gradient-docked',
      docked ? 'true' : 'false'
    );
  }

  function requestChromeTick() {
    if (!chromeRaf) chromeRaf = window.requestAnimationFrame(chromeTick);
  }

  function setChromeFromFilm(filmProgress, forceSnap) {
    if (!chromeHeader) return;
    chromeTarget = headerHideProgressFromFilm(filmProgress);
    if (forceSnap || reducedMotion) {
      chromeCurrent = chromeTarget;
      chromeLastTime = 0;
      applyChromeFrame();
      return;
    }
    requestChromeTick();
  }

  function bootChromeHeader() {
    chromeHeader = findChromeHeader();
    if (!chromeHeader) return;
    measureChromeHeader();
    chromeHeader.classList.add(HEADER_CHROME_CLASS);
    document.documentElement.classList.add(HEADER_ROOT_CLASS);
    setChromeFromFilm(0, true);
    if (window.ResizeObserver) {
      var observer = new ResizeObserver(function () {
        measureChromeHeader();
        applyChromeFrame();
      });
      observer.observe(chromeHeaderRow || chromeHeaderComponent || chromeHeader);
    }
  }

  bootChromeHeader();

  // Flat parallax Bottom — crossfade z końcówką filmu Wrota.
  var PARALLAX_CROSSFADE_DEFAULT = 0.14;
  var parallaxApi = null;

  function ensureParallax() {
    if (parallaxApi) return parallaxApi;
    if (!(stage instanceof HTMLElement)) return null;
    var api = window.GicleeFmWrotaParallax;
    if (!api || typeof api.mount !== 'function') return null;
    parallaxApi = api.mount(stage);
    if (
      parallaxApi &&
      typeof parallaxApi.getGalleryDurationVh === 'function'
    ) {
      track.style.setProperty(
        '--fm-wrota-gallery-duration',
        String(Math.max(0, parallaxApi.getGalleryDurationVh() || 0))
      );
    }
    return parallaxApi;
  }

  function parallaxRevealFromFilm(filmProgress, afterFilm) {
    if (afterFilm > 0) return 1;
    var span = readCssNumber(
      track,
      '--fm-wrota-parallax-crossfade',
      PARALLAX_CROSSFADE_DEFAULT
    );
    span = clamp(span, 0.04, 0.45);
    var start = 1 - span;
    var raw = (clamp(filmProgress, 0, 1) - start) / span;
    return smoothstep(clamp(raw, 0, 1));
  }

  function applyParallaxCrossfade(filmProgress, afterFilm, forceSnap) {
    var api = ensureParallax();
    var reveal = reducedMotion && filmProgress >= 1
      ? 1
      : parallaxRevealFromFilm(filmProgress, afterFilm);
    if (forceSnap && reducedMotion && (filmProgress >= 1 || afterFilm > 0)) {
      reveal = 1;
    }
    if (api) api.setReveal(reveal);
    if (!(stage instanceof HTMLElement)) return reveal;
    stage.classList.toggle('is-fm-parallax-crossfade', reveal > 0.001);
    stage.style.setProperty(
      '--giclee-fm-wrota-video-opacity',
      (1 - reveal).toFixed(4)
    );
    stage.setAttribute('data-fm-parallax-reveal', reveal.toFixed(3));
    return reveal;
  }

  function cinematicTextProgress(afterFilm) {
    var progress = clamp(Number(afterFilm) || 0, 0, 1);
    var points = [0, 0.32, 0.68, 1, 1.42, 1.78, 2.14];
    var phase = Math.min(5, Math.floor(progress * 6));
    var local = progress >= 1 ? 1 : progress * 6 - phase;
    var timelineValue =
      points[phase] + (points[phase + 1] - points[phase]) * local;
    return timelineValue / points[points.length - 1];
  }

  function applyParallaxText(afterFilm, forceSnap) {
    var api = ensureParallax();
    if (!api || typeof api.setTextProgress !== 'function') return 0;
    var progress;
    if (reducedMotion || forceSnap) {
      if (afterFilm <= 0) progress = 0;
      else if (afterFilm < 2 / 6) progress = 0.68 / 2.14;
      else if (afterFilm < 3 / 6) progress = 1 / 2.14;
      else if (afterFilm < 5 / 6) progress = 1.78 / 2.14;
      else progress = 1;
    } else {
      progress = cinematicTextProgress(afterFilm);
    }
    api.setTextProgress(progress);
    if (stage instanceof HTMLElement) {
      stage.setAttribute(
        'data-fm-cinematic-text-progress',
        progress.toFixed(3)
      );
    }
    return progress;
  }

  function applyBeforeAfterGallery(galleryProgress, forceSnap) {
    var api = ensureParallax();
    if (!api || typeof api.setGalleryProgress !== 'function') return 0;
    var progress = clamp(Number(galleryProgress) || 0, 0, 1);
    if (reducedMotion && forceSnap && progress > 0) progress = 0.5;
    api.setGalleryProgress(progress);
    if (stage instanceof HTMLElement) {
      stage.classList.toggle(
        'is-fm-before-after-active',
        progress > 0.02 && progress < 0.99
      );
      stage.setAttribute(
        'data-fm-before-after-progress',
        progress.toFixed(3)
      );
    }
    return progress;
  }

  /**
   * Fazy na jednym sticky ekranie:
   * 1) pin cytatu
   * 2) portal odsłania Wrota (power2.out + lekki lag)
   * 3) scrub filmu Wrota (bez wjazdu sekcji od dołu)
   * 4) crossfade do tła Bottom
   * 5) tekst 1: wejście → hold 0.6 viewportu → wyjście
   * 6) tekst 2: świetlny reveal → hold 0.6 viewportu → wyjście
   * 7) galeria Przed i po: crossfade wejścia → po jednym etapie na slajd
   * 8) po ostatnim slajdzie crossfade z powrotem do samej paralaksy Bottom
   */
  function phaseProgress() {
    var viewport = window.innerHeight || 1;
    var pinDuration = readCssNumber(track, '--fm-quote-pin-duration', 0.6) * viewport;
    var portalDuration =
      readCssNumber(track, '--fm-quote-portal-duration', 2) * viewport;
    var filmDuration =
      readCssNumber(track, '--fm-wrota-film-duration', filmDurationVh) * viewport;
    var parallaxDuration =
      readCssNumber(track, '--fm-wrota-parallax-duration', 3.6) * viewport;
    var galleryDuration =
      readCssNumber(track, '--fm-wrota-gallery-duration', 0) * viewport;

    var trackRect = track.getBoundingClientRect();
    sceneInViewport = trackRect.top <= viewport && trackRect.bottom > 0;
    var scrolled = clamp(-trackRect.top, 0, Math.max(1, track.offsetHeight - viewport));
    syncQuoteGradientDock();

    if (scrolled <= pinDuration) {
      return {
        pin: clamp(scrolled / Math.max(1, pinDuration), 0, 1),
        portal: 0,
        film: 0,
        afterFilm: 0,
        gallery: 0,
      };
    }

    var afterPin = scrolled - pinDuration;
    if (afterPin <= portalDuration) {
      return {
        pin: 1,
        portal: clamp(afterPin / Math.max(1, portalDuration), 0, 1),
        film: 0,
        afterFilm: 0,
        gallery: 0,
      };
    }

    var afterPortal = afterPin - portalDuration;
    if (afterPortal <= filmDuration) {
      return {
        pin: 1,
        portal: 1,
        film: clamp(afterPortal / Math.max(1, filmDuration), 0, 1),
        afterFilm: 0,
        gallery: 0,
      };
    }

    var afterFilmScroll = afterPortal - filmDuration;
    return {
      pin: 1,
      portal: 1,
      film: 1,
      afterFilm: clamp(afterFilmScroll / Math.max(1, parallaxDuration), 0, 1),
      gallery: galleryDuration > 0
        ? clamp(
            (afterFilmScroll - parallaxDuration) / Math.max(1, galleryDuration),
            0,
            1
          )
        : 0,
    };
  }

  function sceneActive() {
    return sceneInViewport;
  }

  var pendingFilmProgress = null;
  var fallbackSeekAttached = false;
  var lastFilmHeld = 0;
  var sceneInViewport = false;

  function flushFallbackSeek() {
    if (pendingFilmProgress == null) return;
    var api = window.GicleeScrollFrameCanvas;
    if (
      api &&
      typeof api.setProgress === 'function' &&
      wrotaRoot instanceof HTMLElement
    ) {
      api.setProgress(wrotaRoot, pendingFilmProgress);
      return;
    }
    if (!(video instanceof HTMLVideoElement) || video.seeking) return;
    if (!video.duration || !Number.isFinite(video.duration) || video.duration <= 0) {
      return;
    }
    var next =
      clamp(pendingFilmProgress, 0, 1) *
      Math.max(0, video.duration - 1 / 60);
    if (Math.abs(video.currentTime - next) < 0.001) return;
    try {
      video.currentTime = next;
    } catch (_error) {}
  }

  function ensureVideoReady() {
    if (!(video instanceof HTMLVideoElement)) {
      video =
        stage instanceof HTMLElement
          ? stage.querySelector('[data-scroll-native-video]')
          : null;
    }
    if (!(video instanceof HTMLVideoElement)) return;
    if (video.dataset.fmPortalLoad !== '1') {
      video.dataset.fmPortalLoad = '1';
      try {
        video.preload = 'auto';
        if (typeof video.load === 'function') video.load();
      } catch (_error) {}
      video.addEventListener(
        'loadedmetadata',
        function () {
          if (pendingFilmProgress != null) flushFallbackSeek();
          else onScroll();
        },
        { once: true }
      );
    }
    if (!fallbackSeekAttached) {
      fallbackSeekAttached = true;
      video.addEventListener('seeked', flushFallbackSeek);
    }
    if (wrotaRoot instanceof HTMLElement) {
      wrotaRoot.classList.add('is-scroll-frame-ready');
    }
  }

  function seekFilm(progress01) {
    ensureVideoReady();
    var nextProgress = clamp(progress01, 0, 1);
    if (
      pendingFilmProgress != null &&
      Math.abs(nextProgress - pendingFilmProgress) < 0.0005
    ) {
      return false;
    }
    pendingFilmProgress = nextProgress;
    flushFallbackSeek();
    return true;
  }

  function wakeScrub() {
    ensureVideoReady();
    if (!(wrotaRoot instanceof HTMLElement)) return;
    wrotaRoot.dataset.scrollActive = 'true';
    var api = window.GicleeScrollFrameCanvas;
    if (api && typeof api.update === 'function') {
      try {
        api.update();
      } catch (_error) {}
    }
  }

  function applyScene(phases, forceSnap) {
    if (!(stage instanceof HTMLElement)) return;

    var target = reducedMotion ? 1 : easePower2Out(clamp(phases.portal, 0, 1));
    if (reducedMotion || forceSnap) {
      portalSmooth = target;
    } else {
      // Lekki lag (~power2 feel przy skokach kółka) — dogania target.
      var blend = 0.14;
      portalSmooth += (target - portalSmooth) * blend;
      if (Math.abs(target - portalSmooth) < 0.0004) portalSmooth = target;
    }

    var local = portalSmooth;
    var inset = 50 * (1 - local);
    stage.style.setProperty('--giclee-fm-portal-inset', inset.toFixed(2) + '%');
    stage.setAttribute('data-fm-portal-progress', local.toFixed(3));
    stage.setAttribute('data-fm-portal-open', local >= 0.999 ? 'true' : 'false');
    stage.setAttribute('data-fm-quote-pin', phases.pin.toFixed(3));
    stage.setAttribute('data-fm-film-progress', phases.film.toFixed(3));

    sticky.style.opacity = '1';
    sticky.classList.remove('is-fm-quote-gone');
    sticky.classList.toggle('is-fm-quote-pinned', phases.pin > 0 && local < 1);

    // Overlay dopiero po pinie — wcześniej Wrota nie zajmuje viewportu.
    var overlayOn =
      reducedMotion ||
      (sceneActive() &&
        (phases.pin >= 1 ||
          local > 0 ||
          phases.film > 0 ||
          phases.afterFilm > 0 ||
          phases.gallery > 0));
    stage.classList.toggle('is-fm-portal-overlay', overlayOn);
    document.body.classList.toggle('giclee-fm-curtain-active', overlayOn);
    document.body.classList.toggle('giclee-fm-curtain-open', local > 0.02);

    var filmShown = 0;
    if (local >= 0.999) {
      filmShown = reducedMotion ? 1 : phases.film;
      if (phases.afterFilm > 0 || phases.gallery > 0) filmShown = 1;
      lastFilmHeld = filmShown;
      if (seekFilm(filmShown)) wakeScrub();
    } else if (local > 0.02) {
      // Nie resetuj do klatki 0 gdy portal jeszcze prawie otwarty —
      // przy scrollu w górę z filmu wyglądało to jak skok na początek
      // i ponowne „odtwarzanie” do przodu.
      if (local < 0.22 && phases.portal < 0.22) {
        lastFilmHeld = 0;
        if (seekFilm(0)) wakeScrub();
      } else {
        if (seekFilm(lastFilmHeld)) wakeScrub();
      }
      filmShown = lastFilmHeld;
    }

    // Menu chowa się jak w prehero — od klatki 420 scrubu Wrota.
    setChromeFromFilm(filmShown, forceSnap);

    // Paralaksa Bottom — delikatny crossfade z końcówką filmu.
    applyParallaxCrossfade(
      filmShown,
      phases.afterFilm > 0 || phases.gallery > 0 ? 1 : 0,
      forceSnap
    );
    // Dwa teksty: każdy wejście → hold 0.6 viewportu → animacja wyjścia.
    applyParallaxText(phases.afterFilm || 0, forceSnap);
    applyBeforeAfterGallery(phases.gallery || 0, forceSnap);

    return Math.abs(target - portalSmooth) > 0.0004;
  }

  function update() {
    ticking = false;
    var needsCatchup = applyScene(phaseProgress());
    if (needsCatchup) {
      if (portalRaf) return;
      portalRaf = window.requestAnimationFrame(function catchup() {
        portalRaf = 0;
        if (applyScene(phaseProgress())) {
          portalRaf = window.requestAnimationFrame(catchup);
        }
      });
    }
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(update);
  }

  // Preload od razu — nie czekaj aż sekcja Wrota dojedzie z dołu strony.
  ensureVideoReady();
  ensureParallax();

  if (reducedMotion) {
    applyScene({ pin: 1, portal: 1, film: 1, afterFilm: 1, gallery: 0.5 }, true);
    return;
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
})();
