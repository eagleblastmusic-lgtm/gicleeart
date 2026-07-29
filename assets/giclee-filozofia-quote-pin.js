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
    document.documentElement.style.setProperty(
      '--giclee-prehero-header-y',
      (-distance).toFixed(2) + 'px'
    );
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

  // Flat parallax Bottom+Middle — crossfade z końcówką filmu Wrota.
  var PARALLAX_CROSSFADE_DEFAULT = 0.14;
  var parallaxApi = null;

  function ensureParallax() {
    if (parallaxApi) return parallaxApi;
    if (!(stage instanceof HTMLElement)) return null;
    var api = window.GicleeFmWrotaParallax;
    if (!api || typeof api.mount !== 'function') return null;
    parallaxApi = api.mount(stage);
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

  function tresc3dHost() {
    if (!(stage instanceof HTMLElement)) return null;
    return stage.querySelector('[data-fm-tresc3d]');
  }

  function pairOpacityInRange(scrollPx, start, fadeInEnd, fadeOutStart, end) {
    if (scrollPx <= start) return 0;
    if (scrollPx < fadeInEnd) {
      return smoothstep((scrollPx - start) / Math.max(1, fadeInEnd - start));
    }
    if (scrollPx <= fadeOutStart) return 1;
    if (scrollPx < end) {
      return 1 - smoothstep((scrollPx - fadeOutStart) / Math.max(1, end - fadeOutStart));
    }
    return 0;
  }

  /**
   * Po crossfade (afterFilm):
   * 1) wjazd Middle 0.6vh
   * 2) para 1 fade in → hold 0.6vh → fade out
   * 3) para 2 fade in → hold 0.6vh → fade out
   * 4) zjazd Middle w dół 0.6vh
   */
  function applyTresc3d(afterFilmScrollPx, forceSnap) {
    var viewport = window.innerHeight || 1;
    var slideD = readCssNumber(track, '--fm-tresc3d-slide', 0.6) * viewport;
    var fadeD = readCssNumber(track, '--fm-tresc3d-fade', 0.4) * viewport;
    var holdD = readCssNumber(track, '--fm-tresc3d-hold', 0.6) * viewport;
    var scrollPx = Math.max(0, afterFilmScrollPx || 0);

    var p1Start = slideD;
    var p1InEnd = p1Start + fadeD;
    var p1OutStart = p1InEnd + holdD;
    var p1End = p1OutStart + fadeD;

    var p2Start = p1End;
    var p2InEnd = p2Start + fadeD;
    var p2OutStart = p2InEnd + holdD;
    var p2End = p2OutStart + fadeD;

    var middleExitStart = p2End;
    var middleExitEnd = middleExitStart + slideD;

    var middleT = 0;
    if (reducedMotion || forceSnap) {
      middleT =
        scrollPx > 0 && scrollPx < middleExitEnd ? 1 : 0;
    } else if (scrollPx <= 0) {
      middleT = 0;
    } else if (scrollPx < slideD) {
      middleT = smoothstep(scrollPx / Math.max(1, slideD));
    } else if (scrollPx <= middleExitStart) {
      middleT = 1;
    } else if (scrollPx < middleExitEnd) {
      middleT =
        1 -
        smoothstep(
          (scrollPx - middleExitStart) / Math.max(1, slideD)
        );
    } else {
      middleT = 0;
    }

    var api = ensureParallax();
    if (api && typeof api.setMiddleSlide === 'function') {
      api.setMiddleSlide(middleT);
    }

    var o1 = pairOpacityInRange(scrollPx, p1Start, p1InEnd, p1OutStart, p1End);
    var o2 = pairOpacityInRange(scrollPx, p2Start, p2InEnd, p2OutStart, p2End);
    if (reducedMotion) {
      if (scrollPx >= p1Start && scrollPx < p2Start) o1 = 1;
      else o1 = 0;
      if (scrollPx >= p2Start && scrollPx < p2End) o2 = 1;
      else o2 = 0;
    }

    var host = tresc3dHost();
    if (host) {
      var pair1 = host.querySelector('[data-fm-tresc3d-pair="1"]');
      var pair2 = host.querySelector('[data-fm-tresc3d-pair="2"]');
      if (pair1) {
        pair1.style.setProperty('--fm-tresc3d-pair-opacity', o1.toFixed(4));
        pair1.classList.toggle('is-visible', o1 > 0.02);
      }
      if (pair2) {
        pair2.style.setProperty('--fm-tresc3d-pair-opacity', o2.toFixed(4));
        pair2.classList.toggle('is-visible', o2 > 0.02);
      }
      host.classList.toggle('is-active', o1 > 0.02 || o2 > 0.02 || middleT > 0.02);
      host.setAttribute('aria-hidden', o1 > 0.02 || o2 > 0.02 ? 'false' : 'true');
    }

    if (stage instanceof HTMLElement) {
      stage.setAttribute('data-fm-middle-slide', middleT.toFixed(3));
      stage.setAttribute('data-fm-tresc3d-p1', o1.toFixed(3));
      stage.setAttribute('data-fm-tresc3d-p2', o2.toFixed(3));
    }
  }

  function afterFilmScrollPx(phases) {
    var viewport = window.innerHeight || 1;
    var parallaxDuration =
      readCssNumber(track, '--fm-wrota-parallax-duration', 4) * viewport;
    return clamp(phases.afterFilm || 0, 0, 1) * Math.max(1, parallaxDuration);
  }

  /**
   * Fazy na jednym sticky ekranie:
   * 1) pin cytatu
   * 2) portal odsłania Wrota (power2.out + lekki lag)
   * 3) scrub filmu Wrota (bez wjazdu sekcji od dołu)
   * 4) po filmie: crossfade → wjazd Middle → Treść 3D (2 pary)
   */
  function phaseProgress() {
    var viewport = window.innerHeight || 1;
    var pinDuration = readCssNumber(track, '--fm-quote-pin-duration', 0.4) * viewport;
    var portalDuration =
      readCssNumber(track, '--fm-quote-portal-duration', 2) * viewport;
    var filmDuration =
      readCssNumber(track, '--fm-wrota-film-duration', filmDurationVh) * viewport;
    var parallaxDuration =
      readCssNumber(track, '--fm-wrota-parallax-duration', 4) * viewport;

    var trackRect = track.getBoundingClientRect();
    var scrolled = clamp(-trackRect.top, 0, Math.max(1, track.offsetHeight - viewport));

    if (scrolled <= pinDuration) {
      return {
        pin: clamp(scrolled / Math.max(1, pinDuration), 0, 1),
        portal: 0,
        film: 0,
        afterFilm: 0,
      };
    }

    var afterPin = scrolled - pinDuration;
    if (afterPin <= portalDuration) {
      return {
        pin: 1,
        portal: clamp(afterPin / Math.max(1, portalDuration), 0, 1),
        film: 0,
        afterFilm: 0,
      };
    }

    var afterPortal = afterPin - portalDuration;
    if (afterPortal <= filmDuration) {
      return {
        pin: 1,
        portal: 1,
        film: clamp(afterPortal / Math.max(1, filmDuration), 0, 1),
        afterFilm: 0,
      };
    }

    var afterFilmScroll = afterPortal - filmDuration;
    return {
      pin: 1,
      portal: 1,
      film: 1,
      afterFilm: clamp(afterFilmScroll / Math.max(1, parallaxDuration), 0, 1),
    };
  }

  function sceneActive() {
    var viewport = window.innerHeight || 1;
    var trackRect = track.getBoundingClientRect();
    return trackRect.top <= viewport && trackRect.bottom > 0;
  }

  var pendingFilmProgress = null;
  var fallbackSeekAttached = false;
  var lastFilmHeld = 0;

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
    pendingFilmProgress = clamp(progress01, 0, 1);
    flushFallbackSeek();
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
          phases.afterFilm > 0));
    stage.classList.toggle('is-fm-portal-overlay', overlayOn);
    document.body.classList.toggle('giclee-fm-curtain-active', overlayOn);
    document.body.classList.toggle('giclee-fm-curtain-open', local > 0.02);

    var filmShown = 0;
    if (local >= 0.999) {
      filmShown = reducedMotion ? 1 : phases.film;
      if (phases.afterFilm > 0) filmShown = 1;
      lastFilmHeld = filmShown;
      seekFilm(filmShown);
      wakeScrub();
    } else if (local > 0.02) {
      // Nie resetuj do klatki 0 gdy portal jeszcze prawie otwarty —
      // przy scrollu w górę z filmu wyglądało to jak skok na początek
      // i ponowne „odtwarzanie” do przodu.
      if (local < 0.22 && phases.portal < 0.22) {
        lastFilmHeld = 0;
        seekFilm(0);
      } else {
        seekFilm(lastFilmHeld);
      }
      wakeScrub();
      filmShown = lastFilmHeld;
    }

    // Menu chowa się jak w prehero — od klatki 420 scrubu Wrota.
    setChromeFromFilm(filmShown, forceSnap);

    // Paralaksa Bottom+Middle — delikatny crossfade z końcówką filmu.
    applyParallaxCrossfade(filmShown, phases.afterFilm || 0, forceSnap);
    // Po crossfade: wjazd Middle + Treść 3D (tekst + kontenery przed/po).
    applyTresc3d(afterFilmScrollPx(phases), forceSnap);

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
    applyScene({ pin: 1, portal: 1, film: 1, afterFilm: 1 }, true);
    return;
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
})();
