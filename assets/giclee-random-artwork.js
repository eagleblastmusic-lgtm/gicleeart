/*
 * Losuj Obraz — Fine Art Oracle controller.
 * Product data, identity parsing, draw state machine, WebGL capability gate,
 * optional V3 Living Museum Light hand-off, and complete lifecycle cleanup.
 */
(() => {
  'use strict';

  const STATE = {
    IDLE: 'idle',
    LOADING: 'loading',
    DRAWING: 'drawing',
    RESULT: 'result',
    ERROR: 'error',
  };

  const MIN_LOADING_MS_DEFAULT = 700;
  const PHASE_HOLD_MS_DEFAULT = 1100;
  const HEADING_LETTER_FADE_MS = 2200;
  const HEADING_LETTER_MIN_MS = 600;
  const HEADING_LETTER_EASE = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'; /* ~power2.out */
  const SUBTITLE_LETTER_TOTAL_MS = 2000;
  const SUBTITLE_LETTER_FADE_MS = 160;
  const SUBTITLE_START_AFTER_MS = 1000;
  /**
   * Start tytułu zanim artysta domknie fade (CSS `0.75s ease`) — inaczej jest
   * martwa przerwa po wizualnym pojawieniu się artysty.
   */
  const RESULT_TITLE_AFTER_ARTIST_MS = 380;
  /** Wynik — ujawnienie tytułu maską L→P (jedna linia). */
  const RESULT_TITLE_GRADIENT_MS = 1500;
  /** Wynik — czas jednej linii przy tytule wieloliniowym (kolejno: 1., potem 2.). */
  const RESULT_TITLE_LINE_MS = 900;
  const RESULT_TITLE_LINE_TOLERANCE_PX = 4;
  /** Portal CSS: fade-out + pomniejszenie po fazie „Przeszukuję kolekcję…”. */
  const PORTAL_FADE_MS = 700;
  const PORTAL_FADE_SCALE = 0.62;
  /** Proximity lift: letters near the cursor rise; falloff by mask radius. */
  const LETTER_WAVE_RISE_PX = 3;
  const LETTER_WAVE_RADIUS_PX = 100;
  /** Letters within this Y delta share a row for the hover wave. */
  const LETTER_WAVE_ROW_TOLERANCE_PX = 10;
  /**
   * Loading phase letter illuminate (CSS-driven).
   * Keep in sync with `--grw-phase-char-stagger` / animation duration in CSS.
   */
  const PHASE_LETTER_STAGGER_MS = 55;
  const PHASE_LETTER_PULSE_MS = 1100;
  /** Minimum time the loading copy stays visible so the sweep can read. */
  const PHASE_LETTER_MIN_VISIBLE_MS = 1600;
  /** Start wirowania kółka względem startu podtytułu. */
  const PORTAL_START_AFTER_SUBTITLE_MS = 1000;
  /** Musi być zsynchronizowane z `grw-portal-spin` w CSS. */
  const PORTAL_REVEAL_MS = 2800;
  /** Musi być zsynchronizowane z `grw-eyebrow-line` w CSS. */
  const EYEBROW_LINE_REVEAL_MS = 900;
  const FETCH_PAGE_SIZE = 250;
  const FETCH_MAX_PAGES = 20;
  const IMAGE_PRELOAD_TIMEOUT_MS = 6000;
  const SAMPLE_DESKTOP = 16;
  const SAMPLE_MOBILE = 8;
  const SCENE_SAFETY_MS = 9000;
  /** Legacy fade delay when falling back to a non-WebGL result. */
  const RESULT_TEARDOWN_MS = 200;
  /** Crossfade film→obraz — domyślne (nadpisywane z data-* / GicleeApp). */
  const BG_VIDEO_CROSSFADE_LEAD_MS_DEFAULT = 1400;
  const BG_VIDEO_CROSSFADE_HOLD_MS_DEFAULT = 1400;
  const BG_SPOTLIGHT_R_DEFAULT = 340;
  const BG_SPOTLIGHT_EASE_DEFAULT = 0.1;
  /** 6-stop radial mask: center opaque → soft falloff → transparent edge */
  const BG_SPOTLIGHT_STOPS = [
    [0, 1],
    [0.2, 0.95],
    [0.4, 0.6],
    [0.6, 0.25],
    [0.8, 0.08],
    [1, 0],
  ];

  const clampNumber = (value, min, max, fallback) => {
    const n = Number(value);
    if (!Number.isFinite(n)) return fallback;
    return Math.min(max, Math.max(min, n));
  };

  const readSpotlightRadius = (host) =>
    clampNumber(host?.dataset?.bgHoverSpotlightRadius, 120, 600, BG_SPOTLIGHT_R_DEFAULT);

  /** Section stores ease as 5–50 (×0.01). */
  const readSpotlightEase = (host) => {
    const raw = Number(host?.dataset?.bgHoverSpotlightEase);
    if (!Number.isFinite(raw)) return BG_SPOTLIGHT_EASE_DEFAULT;
    if (raw > 1) return clampNumber(raw / 100, 0.05, 0.5, BG_SPOTLIGHT_EASE_DEFAULT);
    return clampNumber(raw, 0.05, 0.5, BG_SPOTLIGHT_EASE_DEFAULT);
  };
  const ARTIST_SEPARATOR_RE = /\s[-–—]\s/;
  const YEAR_TOKEN_RE = /(?:\b(?:ok\.?|około|circa|ca\.?)\s*)?(?:1\d{3}|20[0-2]\d)(?:\s*[\-–—]\s*(?:1\d{3}|20[0-2]\d))?/iu;
  const ARTIST_PARTICLES = new Set([
    'af', 'al', 'av', 'da', 'de', 'del', 'dell', 'della', 'den', 'der', 'di',
    'do', 'dos', 'du', 'el', 'la', 'le', 'les', 'lo', 'ten', 'ter', 'van', 'von',
  ]);

  const prefersReducedMotion = () =>
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

  const isTouchLikeDevice = () =>
    window.matchMedia?.('(hover: none), (pointer: coarse)').matches ?? false;

  const isMobileViewport = () =>
    window.matchMedia?.('(max-width: 749px)').matches ?? window.innerWidth < 750;

  const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

  const cleanText = (value) => String(value || '').replace(/\s+/g, ' ').trim();

  const createLetterVisual = (
    source,
    { visualClass = '', wordClass, charClass, prepareChar = null }
  ) => {
    const visual = document.createElement('span');
    if (visualClass) visual.className = visualClass;
    visual.setAttribute('aria-hidden', 'true');

    const chars = [];
    for (const token of source.split(/(\s+)/)) {
      if (!token) continue;
      if (/^\s+$/.test(token)) {
        visual.appendChild(document.createTextNode(token));
        continue;
      }

      const word = document.createElement('span');
      word.className = wordClass;
      for (const glyph of token) {
        const char = document.createElement('span');
        char.className = charClass;
        char.textContent = glyph;
        if (typeof prepareChar === 'function') prepareChar(char, chars.length);
        chars.push(char);
        word.appendChild(char);
      }
      visual.appendChild(word);
    }

    return { visual, chars };
  };

  const cleanupTitleTail = (value) =>
    cleanText(value)
      .replace(/[\s,;:|/\\\-–—]+$/u, '')
      .trim();

  const extractYear = (rawTitle) => {
    const match = cleanText(rawTitle).match(YEAR_TOKEN_RE);
    return match ? cleanText(match[0]).replace(/\s*([\-–—])\s*/u, '$1') : '';
  };

  const parseArtworkIdentity = (rawTitle) => {
    const raw = cleanText(rawTitle);
    const year = extractYear(raw);
    let title = raw.split('(', 1)[0] || raw;

    if (year) {
      const escapedYear = year.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      title = title.replace(new RegExp(escapedYear.replace(/[\-–—]/g, '[\\-–—]'), 'iu'), '');
    }

    title = cleanupTitleTail(title);
    return { rawTitle: raw, title, year: year || null };
  };

  const formatArtistDisplayName = (value) => {
    const raw = cleanText(value);
    if (!raw || !raw.includes(',')) return raw;

    const parts = raw.split(',').map((item) => item.trim()).filter(Boolean);
    if (parts.length < 2) return raw;

    let surname = parts.shift();
    let given = parts.shift();
    const suffix = parts.length ? `, ${parts.join(', ')}` : '';
    const givenWords = given.split(/\s+/u).filter(Boolean);
    const lastGiven = (givenWords.at(-1) || '').toLocaleLowerCase('pl-PL').replace(/\.$/u, '');

    if (givenWords.length > 1 && ARTIST_PARTICLES.has(lastGiven)) {
      const particle = givenWords.pop();
      surname = `${particle} ${surname}`;
      given = givenWords.join(' ');
    }

    return cleanText(`${given} ${surname}${suffix}`);
  };

  const splitProductIdentity = (rawProductTitle, explicitArtist = '') => {
    const full = cleanText(rawProductTitle);
    let artist = cleanText(explicitArtist);
    let rawArtworkTitle = full;
    const match = full.match(ARTIST_SEPARATOR_RE);

    if (match?.index >= 0) {
      const prefix = full.slice(0, match.index).trim();
      const remainder = full.slice(match.index + match[0].length).trim();
      if (!artist) artist = prefix;
      if (!artist || prefix.toLocaleLowerCase('pl-PL') === artist.toLocaleLowerCase('pl-PL')) {
        rawArtworkTitle = remainder || full;
      }
    }

    return {
      artist: formatArtistDisplayName(artist),
      rawArtworkTitle,
    };
  };

  const hasWebGL = () => {
    try {
      const canvas = document.createElement('canvas');
      return !!(
        window.WebGLRenderingContext &&
        (canvas.getContext('webgl2') || canvas.getContext('webgl'))
      );
    } catch {
      return false;
    }
  };

  const shuffle = (list) => {
    const out = list.slice();
    for (let i = out.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
  };

  const sizedImageUrl = (src, width) => {
    if (!src) return src;
    try {
      const url = new URL(src, window.location.origin);
      url.searchParams.set('width', String(width));
      return url.toString();
    } catch {
      return src;
    }
  };

  const normalizeProduct = (raw) => {
    if (!raw || !raw.image || !raw.url) return null;
    const sourceTitle = cleanText(raw.rawTitle || raw.title);
    if (!sourceTitle) return null;

    const split = splitProductIdentity(sourceTitle, raw.artist);
    const identity = parseArtworkIdentity(split.rawArtworkTitle);
    if (!identity.title) return null;

    return {
      rawTitle: identity.rawTitle,
      title: identity.title,
      year: identity.year,
      artist: split.artist,
      url: String(raw.url),
      image: String(raw.image),
      imageAlt: cleanText(raw.imageAlt) || cleanText(`${split.artist} — ${identity.title}`),
      available: raw.available !== false,
    };
  };

  const mergeProductRecords = (preferred, candidate) => {
    if (!preferred) return candidate;
    if (!candidate) return preferred;
    return {
      rawTitle: preferred.rawTitle || candidate.rawTitle,
      title: preferred.title || candidate.title,
      year: preferred.year || candidate.year || null,
      artist: preferred.artist || candidate.artist,
      url: preferred.url || candidate.url,
      image: preferred.image || candidate.image,
      imageAlt: preferred.imageAlt || candidate.imageAlt,
      available:
        typeof preferred.available === 'boolean'
          ? preferred.available
          : candidate.available !== false,
    };
  };

  window.GICLEE_RANDOM_ARTWORK_TEST_API = Object.freeze({
    parseArtworkIdentity,
    splitProductIdentity,
    formatArtistDisplayName,
    normalizeProduct,
    mergeProductRecords,
  });

  class GicleeRandomArtwork extends HTMLElement {
    connectedCallback() {
      this.rootUrl = this.dataset.rootUrl || '';
      this.endpoint = this.dataset.productsEndpoint || `${this.rootUrl}/collections/all/products.json`;
      this.fetchFull = this.dataset.fetchFull === 'true';
      this.enableWebgl = this.dataset.enableWebgl !== 'false';
      this.designVariant = this.dataset.designVariant || 'v1';
      this.webglUrl = this.dataset.webglUrl || '';
      this.threeUrl = this.dataset.threeUrl || '';
      this.minLoadingMs = clampNumber(
        this.dataset.drawLoadingMs,
        300,
        3000,
        MIN_LOADING_MS_DEFAULT
      );
      this.phaseHoldMs = clampNumber(
        this.dataset.drawPhaseHoldMs,
        400,
        3000,
        PHASE_HOLD_MS_DEFAULT
      );
      this.bgVideoCrossfadeLeadMs = clampNumber(
        this.dataset.bgVideoCrossfadeLeadMs,
        0,
        4000,
        BG_VIDEO_CROSSFADE_LEAD_MS_DEFAULT
      );
      this.bgVideoCrossfadeHoldMs = clampNumber(
        this.dataset.bgVideoCrossfadeHoldMs,
        0,
        4000,
        BG_VIDEO_CROSSFADE_HOLD_MS_DEFAULT
      );
      this.bgVideoFadeMs = this.bgVideoCrossfadeLeadMs + this.bgVideoCrossfadeHoldMs;

      this.fullPoolLoaded = false;
      this.lastWinnerUrl = null;
      this.isDrawing = false;
      this.sceneController = null;
      this.wantTeardown = false;
      this.canvasMount = this.querySelector('[data-grw-canvas-mount]');

      this.phases = [this.dataset.phase1, this.dataset.phase2, this.dataset.phase3]
        .map((text) => cleanText(text))
        .filter(Boolean);

      this.intro = this.querySelector('[data-grw-intro]');
      this.drawButton = this.querySelector('[data-grw-draw]');
      this.phaseWrap = this.querySelector('[data-grw-phase-wrap]');
      this.phaseText = this.querySelector('[data-grw-phase]');
      this.phaseSwapTimer = 0;
      this.resultPanel = this.querySelector('[data-grw-result]');
      this.resultLink = this.querySelector('[data-grw-result-link]');
      this.resultImage = this.querySelector('[data-grw-result-image]');
      this.resultArtist = this.querySelector('[data-grw-result-artist]');
      this.resultTitle = this.querySelector('[data-grw-result-title]');
      this.resultTitleHost = this.querySelector('[data-grw-result-title-fade]');
      this.resultYear = this.querySelector('[data-grw-result-year]');
      this.viewCta = this.querySelector('[data-grw-view]');
      this.replayButton = this.querySelector('[data-grw-replay]');
      this.errorPanel = this.querySelector('[data-grw-error]');
      this.retryButton = this.querySelector('[data-grw-retry]');

      this.pool = this.parseEmbeddedPool();

      this._onDrawClick = () => this.draw();
      this.drawButton?.addEventListener('click', this._onDrawClick);
      this.replayButton?.addEventListener('click', this._onDrawClick);
      this.retryButton?.addEventListener('click', this._onDrawClick);

      if (this.designVariant === 'v3' && window.GICLEE_LIVING_MUSEUM_LIGHT?.create) {
        this.livingMuseumLight = window.GICLEE_LIVING_MUSEUM_LIGHT.create(this);
      }

      this.setState(STATE.IDLE);
      this.initHeadingLetterFade();
      this.initSubtitleLetterFade();
      this.initIntroCircleReveal();
      this.initGalaxyButton();
      this.initBackgroundVideoHandoff();
      this.initBackgroundHoverReveal();
      if (!this.livingMuseumLight) this.initCustomBgParallax();
    }

    disconnectedCallback() {
      this.drawButton?.removeEventListener('click', this._onDrawClick);
      this.replayButton?.removeEventListener('click', this._onDrawClick);
      this.retryButton?.removeEventListener('click', this._onDrawClick);
      this.cleanupHeadingLetterFade();
      this.cleanupSubtitleLetterFade();
      this.cleanupResultIdentityMotion();
      this.unbindFinaleExhibitHover();
      this.cleanupLetterHoverWaves();
      this.cleanupIntroCircleReveal();
      this.cleanupGalaxyButton();
      this.cleanupBackgroundVideoHandoff({ release: true });
      this.cleanupBackgroundHoverReveal();
      this.cleanupCustomBgParallax();
      this.livingMuseumLight?.destroy?.();
      this.livingMuseumLight = null;
      window.clearTimeout(this.resultTeardownTimer);
      window.clearTimeout(this.phaseSwapTimer);
      this.teardownScene();
    }

    mountOneGalaxyButton(btn, { reduce, touch, lottieUrl }) {
      const glows = [...btn.querySelectorAll('.giclee-galaxy-btn__glow')];
      const star = btn.querySelector('[data-grw-galaxy-star]');

      let op = 0;
      let scale = 0.2;
      let btnScale = 1;
      let tx = 0;
      let ty = 0;
      let targetOp = 0;
      let targetScale = 0.2;
      let targetBtnScale = 1;
      let targetTx = 0;
      let targetTy = 0;
      let rafId = 0;
      let starRaf = 0;
      let starRafStart = 0;
      const lottieInstances = [];

      const apply = () => {
        const glowTransform = `translate3d(${tx.toFixed(3)}%, ${ty.toFixed(3)}%, 0) scale3d(${scale.toFixed(4)}, ${scale.toFixed(4)}, 1)`;
        for (const glow of glows) {
          glow.style.opacity = String(op);
          glow.style.transform = glowTransform;
        }
        btn.style.transform = `scale(${btnScale.toFixed(4)})`;
      };

      const tick = () => {
        rafId = 0;
        const glowK = 0.22;
        const btnK = 0.35;
        op += (targetOp - op) * glowK;
        scale += (targetScale - scale) * glowK;
        btnScale += (targetBtnScale - btnScale) * btnK;
        tx += (targetTx - tx) * glowK;
        ty += (targetTy - ty) * glowK;
        apply();
        if (
          Math.abs(targetOp - op) > 0.004 ||
          Math.abs(targetScale - scale) > 0.004 ||
          Math.abs(targetBtnScale - btnScale) > 0.0004 ||
          Math.abs(targetTx - tx) > 0.15 ||
          Math.abs(targetTy - ty) > 0.15
        ) {
          rafId = window.requestAnimationFrame(tick);
        } else {
          op = targetOp;
          scale = targetScale;
          btnScale = targetBtnScale;
          tx = targetTx;
          ty = targetTy;
          apply();
        }
      };

      const kick = () => {
        if (!rafId) rafId = window.requestAnimationFrame(tick);
      };

      const setMouse = (event) => {
        const rect = btn.getBoundingClientRect();
        const mx = Math.min(1, Math.max(0, (event.clientX - rect.left) / Math.max(rect.width, 1)));
        const my = Math.min(1, Math.max(0, (event.clientY - rect.top) / Math.max(rect.height, 1)));
        targetTx = (mx - 0.5) * 200;
        targetTy = (my - 0.5) * 40;
        kick();
      };

      const onEnter = (event) => {
        targetOp = 1;
        targetScale = 1;
        targetBtnScale = 1.03;
        setMouse(event);
        kick();
      };

      const onLeave = () => {
        targetOp = 0;
        targetScale = 0.2;
        targetBtnScale = 1;
        targetTx = 0;
        targetTy = 0;
        kick();
      };

      apply();

      if (!reduce && !touch) {
        btn.addEventListener('mouseenter', onEnter);
        btn.addEventListener('mouseleave', onLeave);
        btn.addEventListener('mousemove', setMouse);
      }

      const spinStar = (ts) => {
        if (!star) return;
        if (!starRafStart) starRafStart = ts;
        const t = (ts - starRafStart) / 5000;
        star.style.transform = `rotate(${(t % 1) * 360}deg)`;
        starRaf = window.requestAnimationFrame(spinStar);
      };

      if (star && !reduce) starRaf = window.requestAnimationFrame(spinStar);

      const mountLotties = () => {
        if (!window.lottie || reduce || !lottieUrl) return;
        btn.querySelectorAll('[data-grw-galaxy-lottie]').forEach((el) => {
          if (el.dataset.lottieMounted) return;
          el.dataset.lottieMounted = '1';
          try {
            lottieInstances.push(
              window.lottie.loadAnimation({
                container: el,
                renderer: 'svg',
                loop: true,
                autoplay: true,
                path: lottieUrl,
              })
            );
          } catch (_) {
            /* ignore */
          }
        });
      };

      let lottieRetry = 0;
      if (window.lottie) {
        mountLotties();
      } else {
        window.addEventListener('load', mountLotties, { once: true });
        lottieRetry = window.setTimeout(mountLotties, 400);
      }

      return () => {
        btn.removeEventListener('mouseenter', onEnter);
        btn.removeEventListener('mouseleave', onLeave);
        btn.removeEventListener('mousemove', setMouse);
        window.removeEventListener('load', mountLotties);
        window.clearTimeout(lottieRetry);
        if (rafId) window.cancelAnimationFrame(rafId);
        if (starRaf) window.cancelAnimationFrame(starRaf);
        btn.style.transform = '';
        lottieInstances.forEach((instance) => {
          try {
            instance.destroy();
          } catch (_) {
            /* ignore */
          }
        });
      };
    }

    initGalaxyButton() {
      this.cleanupGalaxyButton();

      const buttons = [...this.querySelectorAll('[data-grw-galaxy-btn]')];
      if (!buttons.length) return;

      const reduce = prefersReducedMotion();
      const touch = isTouchLikeDevice();
      const lottieUrl = this.dataset.galaxyLottieUrl || '';
      const cleanups = buttons.map((btn) =>
        this.mountOneGalaxyButton(btn, { reduce, touch, lottieUrl })
      );

      this._cleanupGalaxyButton = () => {
        cleanups.forEach((fn) => {
          try {
            fn();
          } catch (_) {
            /* ignore */
          }
        });
        this._cleanupGalaxyButton = null;
      };
    }

    cleanupGalaxyButton() {
      if (typeof this._cleanupGalaxyButton === 'function') {
        this._cleanupGalaxyButton();
      }
    }

    revealEyebrowFade() {
      const eyebrow = this.querySelector('[data-grw-eyebrow-fade]');
      if (!eyebrow) return;
      eyebrow.classList.add('is-eyebrow-fade-ready');
    }

    initHeadingLetterFade() {
      this.cleanupHeadingLetterFade();

      const heading = this.querySelector('[data-grw-letter-fade]');
      if (!heading) {
        this.revealEyebrowFade();
        return;
      }

      const source = cleanText(heading.textContent);
      if (!source) {
        this.revealEyebrowFade();
        return;
      }

      heading.setAttribute('aria-label', source);

      if (prefersReducedMotion() || typeof heading.animate !== 'function') {
        heading.classList.add('is-letter-fade-prepared');
        this.revealEyebrowFade();
        return;
      }

      heading.textContent = '';
      const { visual, chars } = createLetterVisual(source, {
        wordClass: 'giclee-random-artwork__heading-word',
        charClass: 'giclee-random-artwork__heading-char',
        prepareChar: (char) => {
          char.style.opacity = '0';
        },
      });

      heading.appendChild(visual);
      heading.classList.add('is-letter-fade-prepared');
      heading.style.transform = 'scale(1.2)';

      const animations = [];
      const totalSec = HEADING_LETTER_FADE_MS / 1000;
      const minSec = HEADING_LETTER_MIN_MS / 1000;
      const mid = Math.max((chars.length - 1) / 2, 0.5);
      const maxOffsetPx = 28;

      // Jak w demo Potter: fade liter z losowym duration/delay + scale bloku.
      // Lekki translateX proporcjonalny do odległości od centrum (lewe ←, prawe →).
      chars.forEach((char, index) => {
        const randomDuration = minSec + Math.random() * (totalSec - minSec);
        const randomDelay = Math.random() * (totalSec - randomDuration);
        const offsetX = ((index - mid) / mid) * maxOffsetPx;

        char.style.opacity = '0';
        char.style.transform = `translateX(${offsetX.toFixed(2)}px)`;

        animations.push(
          char.animate(
            [
              { opacity: 0, transform: `translateX(${offsetX.toFixed(2)}px)` },
              { opacity: 1, transform: 'translateX(0px)' },
            ],
            {
              duration: randomDuration * 1000,
              delay: randomDelay * 1000,
              easing: HEADING_LETTER_EASE,
              fill: 'forwards',
            }
          )
        );
      });

      animations.push(
        heading.animate([{ transform: 'scale(1.2)' }, { transform: 'scale(1)' }], {
          duration: HEADING_LETTER_FADE_MS,
          easing: HEADING_LETTER_EASE,
          fill: 'forwards',
        })
      );

      this._headingLetterAnimations = animations;
      this._headingLetterEl = heading;
      this._headingLetterGen = (this._headingLetterGen || 0) + 1;
      const gen = this._headingLetterGen;

      // Hover-wave + eyebrow fade dopiero po zakończeniu letter-fade + scale.
      Promise.all(animations.map((animation) => animation.finished.catch(() => {}))).then(() => {
        if (gen !== this._headingLetterGen || this._headingLetterEl !== heading) return;
        this.settleLetterIntro(animations, chars, heading);
        this._headingLetterAnimations = null;
        this.revealEyebrowFade();
        this.attachLetterHoverWave(heading, chars, 'heading');
      });
    }

    cleanupHeadingLetterFade() {
      this._headingLetterGen = (this._headingLetterGen || 0) + 1;
      this.querySelector('[data-grw-eyebrow-fade]')?.classList.remove('is-eyebrow-fade-ready');
      if (Array.isArray(this._headingLetterAnimations)) {
        this._headingLetterAnimations.forEach((animation) => {
          try {
            animation.cancel();
          } catch (_) {
            /* ignore */
          }
        });
      }
      this._headingLetterAnimations = null;
      this.detachLetterHoverWave('heading');
      if (this._headingLetterEl) {
        this._headingLetterEl.style.transform = '';
        this._headingLetterEl = null;
      }
    }

    initSubtitleLetterFade() {
      this.cleanupSubtitleLetterFade();

      const subtitle = this.querySelector('[data-grw-subtitle-fade]');
      if (!subtitle) return;

      const source = cleanText(subtitle.textContent);
      if (!source) return;

      subtitle.setAttribute('aria-label', source);

      if (prefersReducedMotion() || typeof subtitle.animate !== 'function') {
        subtitle.classList.add('is-letter-fade-prepared');
        return;
      }

      subtitle.textContent = '';
      const { visual, chars } = createLetterVisual(source, {
        wordClass: 'giclee-random-artwork__subtitle-word',
        charClass: 'giclee-random-artwork__subtitle-char',
        prepareChar: (char) => {
          char.style.opacity = '0';
        },
      });

      subtitle.appendChild(visual);
      subtitle.classList.add('is-letter-fade-prepared');

      if (!chars.length) return;

      const fadeMs = SUBTITLE_LETTER_FADE_MS;
      const maxDelay = Math.max(0, SUBTITLE_LETTER_TOTAL_MS - fadeMs);
      const lastIndex = Math.max(chars.length - 1, 1);
      // Start po rozpoczęciu letter-fade nagłówka.
      const startAfterMs = SUBTITLE_START_AFTER_MS;
      this._subtitleLetterEl = subtitle;
      this._subtitleLetterGen = (this._subtitleLetterGen || 0) + 1;
      const gen = this._subtitleLetterGen;

      const start = () => {
        if (!this._subtitleLetterPending || gen !== this._subtitleLetterGen) return;
        this._subtitleLetterPending = false;
        const animations = chars.map((char, index) => {
          const delay = (index / lastIndex) * maxDelay;
          return char.animate([{ opacity: 0 }, { opacity: 1 }], {
            duration: fadeMs,
            delay,
            easing: 'ease-out',
            fill: 'forwards',
          });
        });
        this._subtitleLetterAnimations = animations;

        Promise.all(animations.map((animation) => animation.finished.catch(() => {}))).then(() => {
          if (gen !== this._subtitleLetterGen || this._subtitleLetterEl !== subtitle) return;
          this.settleLetterIntro(animations, chars, null);
          this._subtitleLetterAnimations = null;
        });
      };

      this._subtitleLetterPending = true;
      this._subtitleLetterTimer = window.setTimeout(start, startAfterMs);
    }

    cleanupSubtitleLetterFade() {
      this._subtitleLetterGen = (this._subtitleLetterGen || 0) + 1;
      window.clearTimeout(this._subtitleLetterTimer);
      this._subtitleLetterTimer = 0;
      this._subtitleLetterPending = false;
      if (Array.isArray(this._subtitleLetterAnimations)) {
        this._subtitleLetterAnimations.forEach((animation) => {
          try {
            animation.cancel();
          } catch (_) {
            /* ignore */
          }
        });
      }
      this._subtitleLetterAnimations = null;
      this._subtitleLetterEl = null;
    }

    /** Wynik: fade artysty, tytuł nachodzi na jego domknięcie (bez martwej przerwy). */
    playResultIdentityMotion() {
      this.cleanupResultIdentityMotion();
      const artistVisible = this.revealResultArtistFade();
      const delay =
        artistVisible && !prefersReducedMotion() ? RESULT_TITLE_AFTER_ARTIST_MS : 0;

      this._resultTitleStartGen = (this._resultTitleStartGen || 0) + 1;
      const gen = this._resultTitleStartGen;
      window.clearTimeout(this._resultTitleStartTimer);
      this._resultTitleStartTimer = window.setTimeout(() => {
        if (gen !== this._resultTitleStartGen) return;
        this.initResultTitleGradientReveal();
      }, delay);
    }

    cleanupResultIdentityMotion() {
      this._resultTitleStartGen = (this._resultTitleStartGen || 0) + 1;
      window.clearTimeout(this._resultTitleStartTimer);
      this._resultTitleStartTimer = 0;
      this.cleanupResultArtistFade();
      this.cleanupResultTitleGradientReveal();
    }

    /** @returns {boolean} true gdy artysta jest widoczny i animowany */
    revealResultArtistFade() {
      const artist = this.resultArtist?.hasAttribute?.('data-grw-result-artist-fade')
        ? this.resultArtist
        : this.querySelector('[data-grw-result-artist-fade]');
      if (!artist || artist.hidden || !cleanText(artist.textContent)) return false;
      artist.classList.remove('is-artist-fade-ready');
      void artist.offsetWidth;
      artist.classList.add('is-artist-fade-ready');
      return true;
    }

    cleanupResultArtistFade() {
      const artist = this.resultArtist?.hasAttribute?.('data-grw-result-artist-fade')
        ? this.resultArtist
        : this.querySelector('[data-grw-result-artist-fade]');
      artist?.classList.remove('is-artist-fade-ready');
    }

    restoreResultTitleDom() {
      const snap = this._resultTitleSnapshot;
      const host = this.resultTitleHost || this.querySelector('[data-grw-result-title-fade]');
      if (!snap || !host) {
        this._resultTitleSnapshot = null;
        return;
      }

      const title = document.createElement('span');
      title.setAttribute('data-grw-result-title', '');
      title.textContent = snap.title;

      const year = document.createElement('span');
      year.className = 'giclee-random-artwork__result-year';
      year.setAttribute('data-grw-result-year', '');
      year.textContent = snap.year;
      year.hidden = snap.yearHidden;

      host.replaceChildren(title, year);
      this.resultTitle = title;
      this.resultYear = year;
      this._resultTitleSnapshot = null;
    }

    /**
     * Freeze wrapped title into block lines so reveal can run line 1, then line 2.
     * @returns {HTMLElement[]}
     */
    buildResultTitleLines(host) {
      const titleEl = this.resultTitle;
      if (!titleEl || !host) return [];

      const titleText = cleanText(titleEl.textContent);
      if (!titleText) return [];

      const yearEl = this.resultYear;
      const yearHidden = !yearEl || yearEl.hidden || !cleanText(yearEl.textContent);
      this._resultTitleSnapshot = {
        title: titleText,
        year: yearEl ? yearEl.textContent || '' : '',
        yearHidden,
      };

      titleEl.textContent = '';
      const measureNodes = [];
      const words = titleText.split(/\s+/).filter(Boolean);
      words.forEach((word, index) => {
        const span = document.createElement('span');
        span.className = 'giclee-random-artwork__result-title-word';
        span.textContent = word;
        titleEl.appendChild(span);
        measureNodes.push({ el: span, isGlue: false });
        if (index < words.length - 1) {
          titleEl.appendChild(document.createTextNode(' '));
        }
      });

      // Keep ", year" glued to the last word — never orphan it on its own line.
      if (yearEl && !yearHidden && measureNodes.length) {
        const last = measureNodes[measureNodes.length - 1];
        const glue = document.createElement('span');
        glue.className = 'giclee-random-artwork__result-title-glue';
        last.el.replaceWith(glue);
        glue.appendChild(last.el);
        glue.appendChild(yearEl);
        measureNodes[measureNodes.length - 1] = { el: glue, isGlue: true };
      }

      void host.offsetWidth;

      const groups = [];
      let currentTop = null;
      for (const node of measureNodes) {
        const top = Math.round(node.el.offsetTop);
        if (
          currentTop === null ||
          Math.abs(top - currentTop) > RESULT_TITLE_LINE_TOLERANCE_PX
        ) {
          groups.push([node]);
          currentTop = top;
        } else {
          groups[groups.length - 1].push(node);
        }
      }

      titleEl.replaceChildren();
      const lineEls = [];
      for (const group of groups) {
        const line = document.createElement('span');
        line.className = 'giclee-random-artwork__result-title-line';
        line.setAttribute('data-grw-title-line', '');
        const parts = [];
        for (const node of group) {
          if (node.isGlue) {
            if (parts.length) {
              line.appendChild(document.createTextNode(parts.join(' ')));
              parts.length = 0;
            }
            if (line.childNodes.length) {
              line.appendChild(document.createTextNode(' '));
            }
            line.appendChild(node.el);
          } else {
            parts.push(node.el.textContent || '');
          }
        }
        if (parts.length) {
          if (line.childNodes.length) {
            line.appendChild(document.createTextNode(` ${parts.join(' ')}`));
          } else {
            line.appendChild(document.createTextNode(parts.join(' ')));
          }
        }
        titleEl.appendChild(line);
        lineEls.push(line);
      }

      if (!lineEls.length) {
        this.restoreResultTitleDom();
        return [];
      }

      return lineEls;
    }

    initResultTitleGradientReveal() {
      this.cleanupResultTitleGradientReveal();

      const host = this.resultTitleHost || this.querySelector('[data-grw-result-title-fade]');
      if (!host) return;

      const source = cleanText(this.resultTitle?.textContent);
      if (!source) {
        host.classList.add('is-title-gradient-ready');
        host.classList.add('is-title-gradient-done');
        return;
      }

      if (prefersReducedMotion()) {
        host.classList.add('is-title-gradient-ready');
        host.classList.add('is-title-gradient-done');
        return;
      }

      const lines = this.buildResultTitleLines(host);
      const lineCount = Math.max(1, lines.length);
      const lineMs = lineCount > 1 ? RESULT_TITLE_LINE_MS : RESULT_TITLE_GRADIENT_MS;
      const totalMs = lineMs * lineCount;

      host.style.setProperty('--grw-title-line-ms', `${lineMs}ms`);
      host.classList.remove('is-title-gradient-ready', 'is-title-gradient-done');
      void host.offsetWidth;
      host.classList.add('is-title-gradient-ready');

      this._resultTitleGradientHost = host;
      this._resultTitleGradientGen = (this._resultTitleGradientGen || 0) + 1;
      const gen = this._resultTitleGradientGen;
      this._resultTitleLineTimers = [];

      if (!lines.length) {
        // Fallback: host-level sweep when line split is unavailable.
        host.style.setProperty('--grw-title-gradient-ms', `${RESULT_TITLE_GRADIENT_MS}ms`);
        host.classList.add('is-title-host-reveal');
        window.clearTimeout(this._resultTitleGradientTimer);
        this._resultTitleGradientTimer = window.setTimeout(() => {
          if (gen !== this._resultTitleGradientGen || this._resultTitleGradientHost !== host) return;
          host.classList.add('is-title-gradient-done');
        }, RESULT_TITLE_GRADIENT_MS + 40);
        return;
      }

      lines.forEach((line, index) => {
        const timer = window.setTimeout(() => {
          if (gen !== this._resultTitleGradientGen || this._resultTitleGradientHost !== host) return;
          line.classList.add('is-title-line-reveal');
        }, index * lineMs);
        this._resultTitleLineTimers.push(timer);
      });

      window.clearTimeout(this._resultTitleGradientTimer);
      this._resultTitleGradientTimer = window.setTimeout(() => {
        if (gen !== this._resultTitleGradientGen || this._resultTitleGradientHost !== host) return;
        host.classList.add('is-title-gradient-done');
      }, totalMs + 40);
    }

    cleanupResultTitleGradientReveal() {
      this._resultTitleGradientGen = (this._resultTitleGradientGen || 0) + 1;
      window.clearTimeout(this._resultTitleGradientTimer);
      this._resultTitleGradientTimer = 0;
      if (Array.isArray(this._resultTitleLineTimers)) {
        this._resultTitleLineTimers.forEach((timer) => window.clearTimeout(timer));
      }
      this._resultTitleLineTimers = [];

      const host = this._resultTitleGradientHost || this.resultTitleHost;
      host?.classList.remove(
        'is-title-gradient-ready',
        'is-title-gradient-done',
        'is-title-host-reveal'
      );
      host?.style.removeProperty('--grw-title-gradient-ms');
      host?.style.removeProperty('--grw-title-line-ms');
      host
        ?.querySelectorAll?.('[data-grw-title-line].is-title-line-reveal')
        ?.forEach((line) => line.classList.remove('is-title-line-reveal'));

      if (this._resultTitleSnapshot) this.restoreResultTitleDom();
      this._resultTitleGradientHost = null;
    }

    settleLetterIntro(animations, chars, host) {
      if (Array.isArray(animations)) {
        animations.forEach((animation) => {
          try {
            animation.commitStyles?.();
          } catch (_) {
            /* ignore */
          }
          try {
            animation.cancel();
          } catch (_) {
            /* ignore */
          }
        });
      }
      chars.forEach((char) => {
        char.style.opacity = '1';
        char.style.transform = 'translate3d(0, 0, 0)';
      });
      if (host) host.style.transform = '';
    }

    attachLetterHoverWave(host, chars, key) {
      this.detachLetterHoverWave(key);
      if (!host || !chars?.length || prefersReducedMotion()) return;

      let armed = true;
      let active = false;
      let raf = 0;
      let pointerX = 0;
      let pointerY = 0;
      let centers = null;
      const supportsHover =
        window.matchMedia?.('(hover: hover) and (pointer: fine)').matches ?? true;

      const restChar = (char) => {
        char.style.transform = 'translate3d(0, 0, 0)';
      };

      const restAll = () => {
        chars.forEach(restChar);
      };

      // Cache resting centers (before lift) so transforms don't skew distance.
      // Also assign a row index so only one line reacts at a time.
      const measureCenters = () => {
        const points = chars.map((char) => {
          const rect = char.getBoundingClientRect();
          return {
            x: rect.left + rect.width * 0.5,
            y: rect.top + rect.height * 0.5,
            row: -1,
          };
        });

        const rowYs = [];
        for (const point of points) {
          let row = rowYs.findIndex((y) => Math.abs(y - point.y) <= LETTER_WAVE_ROW_TOLERANCE_PX);
          if (row < 0) {
            row = rowYs.length;
            rowYs.push(point.y);
          }
          point.row = row;
        }
        centers = points;
      };

      const applyLift = () => {
        raf = 0;
        if (!armed || !active || !centers) return;

        const radius = LETTER_WAVE_RADIUS_PX;
        const maxRise = LETTER_WAVE_RISE_PX;

        // Active row = closest line to the pointer (only that row may lift).
        let activeRow = centers[0].row;
        let bestRowDist = Infinity;
        const seenRows = new Set();
        for (const center of centers) {
          if (seenRows.has(center.row)) continue;
          seenRows.add(center.row);
          const rowDist = Math.abs(pointerY - center.y);
          if (rowDist < bestRowDist) {
            bestRowDist = rowDist;
            activeRow = center.row;
          }
        }

        for (let i = 0; i < chars.length; i += 1) {
          const center = centers[i];
          if (center.row !== activeRow) {
            restChar(chars[i]);
            continue;
          }
          // Horizontal proximity within the active row only.
          const dist = Math.abs(pointerX - center.x);
          let t = 1 - dist / radius;
          if (t <= 0) {
            restChar(chars[i]);
            continue;
          }
          // Smoothstep — miękka maska wokół kursora.
          t = t * t * (3 - 2 * t);
          const y = -(maxRise * t);
          chars[i].style.transform = `translate3d(0, ${y.toFixed(2)}px, 0)`;
        }
      };

      const schedule = () => {
        if (raf || !armed) return;
        raf = window.requestAnimationFrame(applyLift);
      };

      const onMove = (event) => {
        if (!active) return;
        pointerX = event.clientX;
        pointerY = event.clientY;
        schedule();
      };

      const onEnter = (event) => {
        if (!armed || prefersReducedMotion()) return;
        active = true;
        restAll();
        measureCenters();
        pointerX = event.clientX;
        pointerY = event.clientY;
        schedule();
      };

      const onLeave = () => {
        active = false;
        if (raf) {
          window.cancelAnimationFrame(raf);
          raf = 0;
        }
        // CSS transition wygładza powrót — bez snapa.
        restAll();
      };

      const onFocusIn = () => {
        if (!armed || prefersReducedMotion() || active) return;
        active = true;
        restAll();
        measureCenters();
        const rect = host.getBoundingClientRect();
        pointerX = rect.left + rect.width * 0.5;
        pointerY = rect.top + rect.height * 0.5;
        schedule();
      };

      const onResize = () => {
        if (!active) return;
        restAll();
        measureCenters();
        schedule();
      };

      host.classList.add('is-letter-wave-ready');
      if (!host.hasAttribute('tabindex')) host.setAttribute('tabindex', '0');

      if (supportsHover) {
        host.addEventListener('pointerenter', onEnter);
        host.addEventListener('pointermove', onMove);
        host.addEventListener('pointerleave', onLeave);
      }
      host.addEventListener('focusin', onFocusIn);
      host.addEventListener('focusout', onLeave);
      window.addEventListener('resize', onResize);

      if (!this._letterWaveCleanups) this._letterWaveCleanups = {};
      this._letterWaveCleanups[key] = () => {
        armed = false;
        active = false;
        if (raf) {
          window.cancelAnimationFrame(raf);
          raf = 0;
        }
        if (supportsHover) {
          host.removeEventListener('pointerenter', onEnter);
          host.removeEventListener('pointermove', onMove);
          host.removeEventListener('pointerleave', onLeave);
        }
        host.removeEventListener('focusin', onFocusIn);
        host.removeEventListener('focusout', onLeave);
        window.removeEventListener('resize', onResize);
        restAll();
        host.classList.remove('is-letter-wave-ready');
        if (host.getAttribute('tabindex') === '0') host.removeAttribute('tabindex');
      };
    }

    detachLetterHoverWave(key) {
      const cleanup = this._letterWaveCleanups?.[key];
      if (typeof cleanup === 'function') {
        cleanup();
        delete this._letterWaveCleanups[key];
      }
    }

    cleanupLetterHoverWaves() {
      this.detachLetterHoverWave('heading');
    }

    /**
     * Marks end of intro circle spin.
     * Fluid smoke + living dust wait on `data-intro-circle-done`.
     */
    markIntroCircleDone() {
      this.dataset.introCircleDone = 'true';
      // Back-compat for older fluid builds.
      this.dataset.cursorSmokeArmed = 'true';
    }

    initIntroCircleReveal() {
      this.cleanupIntroCircleReveal();

      const portal = this.querySelector('[data-grw-portal-reveal]');
      const draw = this.querySelector('[data-grw-draw-reveal]');
      const line = this.querySelector('[data-grw-eyebrow-line]');
      if (!portal && !draw && !line) {
        this.markIntroCircleDone();
        return;
      }

      const revealPortal = () => portal?.classList.add('is-portal-reveal-ready');
      const revealLine = () => line?.classList.add('is-line-reveal-ready');
      const revealDraw = () => draw?.classList.add('is-draw-reveal-ready');

      if (prefersReducedMotion()) {
        revealPortal();
        if (line) {
          line.style.transform = 'scaleX(1)';
          line.classList.add('is-line-reveal-ready');
        }
        revealDraw();
        this.markIntroCircleDone();
        return;
      }

      // Okrąg → po spinie kreska → po kresce przycisk.
      // Pył / dym startują razem z końcem spinu okręgu (lineStartMs).
      const portalStartMs = SUBTITLE_START_AFTER_MS + PORTAL_START_AFTER_SUBTITLE_MS;
      const lineStartMs = portalStartMs + PORTAL_REVEAL_MS;
      const drawStartMs = lineStartMs + EYEBROW_LINE_REVEAL_MS;
      this._introCircleTimer = window.setTimeout(revealPortal, portalStartMs);
      this._introLineTimer = window.setTimeout(revealLine, lineStartMs);
      this._introDrawTimer = window.setTimeout(revealDraw, drawStartMs);
      this._introCircleDoneTimer = window.setTimeout(() => this.markIntroCircleDone(), lineStartMs);
    }

    cleanupIntroCircleReveal() {
      window.clearTimeout(this._introCircleTimer);
      window.clearTimeout(this._introLineTimer);
      window.clearTimeout(this._introDrawTimer);
      window.clearTimeout(this._introCircleDoneTimer);
      this._introCircleTimer = 0;
      this._introLineTimer = 0;
      this._introDrawTimer = 0;
      this._introCircleDoneTimer = 0;
    }

    releaseBackgroundVideo(video) {
      if (!video) return;
      const host =
        video.closest('video-background-component') ||
        video.closest('.video-background') ||
        video;
      try {
        video.pause();
        video.removeAttribute('src');
        video.querySelectorAll('source').forEach((source) => {
          source.removeAttribute('src');
          source.removeAttribute('data-video-source');
        });
        // Pusty load() zamyka dekoder i zwalnia bufory GPU/CPU.
        video.load();
      } catch (_) {
        /* ignore */
      }
      try {
        host.remove();
      } catch (_) {
        /* ignore */
      }
    }

    initBackgroundVideoHandoff() {
      this.cleanupBackgroundVideoHandoff({ release: true });
      this._bgVideoActive = false;

      const bg = this.querySelector('[data-grw-custom-bg][data-grw-bg-handoff="video-once"]');
      if (!bg) return;

      const video = bg.querySelector('video');
      if (!video) {
        bg.classList.add('is-bg-image');
        bg.classList.add('is-bg-video-disposed');
        this.armBackgroundHoverReveal();
        return;
      }

      const leadMs = this.bgVideoCrossfadeLeadMs ?? BG_VIDEO_CROSSFADE_LEAD_MS_DEFAULT;
      const fadeMs =
        this.bgVideoFadeMs ??
        leadMs + (this.bgVideoCrossfadeHoldMs ?? BG_VIDEO_CROSSFADE_HOLD_MS_DEFAULT);

      try {
        this.style.setProperty('--grw-bg-video-fade-ms', `${Math.max(0, fadeMs)}ms`);
      } catch (_) {
        /* ignore */
      }

      const finishHandoff = () => {
        this.releaseBackgroundVideo(video);
        bg.classList.add('is-bg-video-disposed');
        this._bgVideoActive = false;
        this.cleanupBackgroundVideoHandoff();
      };

      const beginCrossfade = () => {
        if (bg.classList.contains('is-bg-image')) return;
        bg.classList.add('is-bg-image');
        this.armBackgroundHoverReveal();
        // Film gra jeszcze ~LEAD; po ended pauza trzyma ostatnią klatkę do końca fade.

        window.clearTimeout(this._bgVideoDisposeTimer);
        const delay = prefersReducedMotion() ? 0 : fadeMs;
        this._bgVideoDisposeTimer = window.setTimeout(finishHandoff, delay);
      };

      const holdLastFrame = () => {
        try {
          if (!video.paused) video.pause();
        } catch (_) {
          /* ignore */
        }
        // Fallback gdy lead nie zdążył odpalić (krótki film / late init).
        beginCrossfade();
      };

      const maybeStartCrossfade = () => {
        if (bg.classList.contains('is-bg-image')) return;
        const duration = video.duration;
        if (!Number.isFinite(duration) || duration <= 0) return;
        const remaining = duration - video.currentTime;
        if (remaining <= leadMs / 1000 + 0.02) {
          beginCrossfade();
        }
      };

      if (prefersReducedMotion()) {
        beginCrossfade();
        return;
      }

      this._bgVideoActive = true;
      this._bgVideo = video;
      this._onBgVideoEnded = holdLastFrame;
      this._onBgVideoError = beginCrossfade;
      this._onBgVideoTimeUpdate = maybeStartCrossfade;
      video.addEventListener('ended', this._onBgVideoEnded);
      video.addEventListener('error', this._onBgVideoError);
      video.addEventListener('timeupdate', this._onBgVideoTimeUpdate);

      // Już domknięty / w oknie lead (np. cache / late init) — od razu grafika
      if (
        video.ended ||
        (video.readyState >= 2 &&
          Number.isFinite(video.duration) &&
          video.duration > 0 &&
          video.currentTime >= Math.max(0, video.duration - leadMs / 1000 - 0.05))
      ) {
        beginCrossfade();
      } else {
        maybeStartCrossfade();
      }
    }

    cleanupBackgroundVideoHandoff({ release = false } = {}) {
      window.clearTimeout(this._bgVideoDisposeTimer);
      this._bgVideoDisposeTimer = 0;
      if (this._bgVideo && this._onBgVideoEnded) {
        this._bgVideo.removeEventListener('ended', this._onBgVideoEnded);
      }
      if (this._bgVideo && this._onBgVideoError) {
        this._bgVideo.removeEventListener('error', this._onBgVideoError);
      }
      if (this._bgVideo && this._onBgVideoTimeUpdate) {
        this._bgVideo.removeEventListener('timeupdate', this._onBgVideoTimeUpdate);
      }
      if (release && this._bgVideo) {
        this.releaseBackgroundVideo(this._bgVideo);
        this._bgVideoActive = false;
      }
      this._bgVideo = null;
      this._onBgVideoEnded = null;
      this._onBgVideoError = null;
      this._onBgVideoTimeUpdate = null;
    }

    initBackgroundHoverReveal() {
      this.cleanupBackgroundHoverReveal();

      const bg = this.querySelector('[data-grw-custom-bg][data-grw-bg-hover-reveal]');
      const layer = bg?.querySelector('[data-grw-bg-hover-layer]');
      if (!bg || !layer) return;
      if (isTouchLikeDevice() || prefersReducedMotion()) return;

      const scene = this.querySelector('[data-grw-scene]') || this;
      const needsHandoff = bg.dataset.grwBgHandoff === 'video-once';
      const spotlightR = readSpotlightRadius(this);
      const spotlightEase = readSpotlightEase(this);

      // Spotlight: raw mouse → eased → 6-stop radial maskImage na BG2.
      // Parametry z GicleeApp / Theme Editor (Edytowanie Odkrycia maski).
      const mouse = { x: 0, y: 0, active: false, sampled: false };
      const smooth = { x: 0, y: 0, r: 0 };
      let rafId = 0;
      let running = false;
      let ready = false;
      let viewW = window.innerWidth || 1;
      let viewH = window.innerHeight || 1;

      const clearMask = () => {
        layer.style.webkitMaskImage = 'linear-gradient(#0000, #0000)';
        layer.style.maskImage = 'linear-gradient(#0000, #0000)';
        layer.style.webkitMaskSize = '100% 100%';
        layer.style.maskSize = '100% 100%';
      };

      const buildMask = (cx, cy, radius) => {
        const rect = layer.getBoundingClientRect();
        const lw = rect.width || viewW || 1;
        const lh = rect.height || viewH || 1;
        const xPct = (((cx - rect.left) / lw) * 100).toFixed(3);
        const yPct = (((cy - rect.top) / lh) * 100).toFixed(3);
        const stops = BG_SPOTLIGHT_STOPS.map(
          ([stop, alpha]) => `rgba(255,255,255,${alpha}) ${(stop * 100).toFixed(0)}%`
        ).join(', ');
        return `radial-gradient(circle ${radius.toFixed(2)}px at ${xPct}% ${yPct}%, ${stops})`;
      };

      const paint = () => {
        const targetR = mouse.active && ready ? spotlightR : 0;

        smooth.x += (mouse.x - smooth.x) * spotlightEase;
        smooth.y += (mouse.y - smooth.y) * spotlightEase;
        smooth.r += (targetR - smooth.r) * spotlightEase;

        if (smooth.r > 0.5) {
          const mask = buildMask(smooth.x, smooth.y, smooth.r);
          layer.style.webkitMaskImage = mask;
          layer.style.maskImage = mask;
          layer.style.webkitMaskSize = '100% 100%';
          layer.style.maskSize = '100% 100%';
        } else {
          clearMask();
        }

        return (
          Math.abs(mouse.x - smooth.x) > 0.15 ||
          Math.abs(mouse.y - smooth.y) > 0.15 ||
          Math.abs(targetR - smooth.r) > 0.15 ||
          (mouse.active && ready)
        );
      };

      const tick = () => {
        rafId = 0;
        if (paint()) {
          rafId = window.requestAnimationFrame(tick);
          running = true;
        } else {
          running = false;
        }
      };

      const startLoop = () => {
        if (!running) {
          running = true;
          rafId = window.requestAnimationFrame(tick);
        }
      };

      const onPointerMove = (event) => {
        mouse.x = event.clientX;
        mouse.y = event.clientY;
        mouse.sampled = true;
        if (!mouse.active) {
          mouse.active = true;
          if (smooth.r < 1) {
            smooth.x = mouse.x;
            smooth.y = mouse.y;
          }
        }
        if (ready) startLoop();
      };

      const onPointerLeave = () => {
        mouse.active = false;
        if (ready) startLoop();
      };

      const onResize = () => {
        viewW = window.innerWidth || 1;
        viewH = window.innerHeight || 1;
        if (ready) startLoop();
      };

      clearMask();

      this._bgHoverBg = bg;
      this._armBackgroundHoverReveal = () => {
        if (ready) return;
        ready = true;
        bg.classList.add('is-bg-hover-ready');
        this.classList.add('is-bg-hover-ready');
        if (scene.matches?.(':hover') && mouse.sampled) {
          mouse.active = true;
          smooth.x = mouse.x;
          smooth.y = mouse.y;
          startLoop();
        }
      };

      scene.addEventListener('pointermove', onPointerMove, { passive: true });
      scene.addEventListener('pointerleave', onPointerLeave, { passive: true });
      window.addEventListener('resize', onResize, { passive: true });

      this._cleanupBackgroundHoverReveal = () => {
        scene.removeEventListener('pointermove', onPointerMove);
        scene.removeEventListener('pointerleave', onPointerLeave);
        window.removeEventListener('resize', onResize);
        if (rafId) window.cancelAnimationFrame(rafId);
        rafId = 0;
        running = false;
        ready = false;
        clearMask();
        bg.classList.remove('is-bg-hover-ready');
        this.classList.remove('is-bg-hover-ready');
        this._cleanupBackgroundHoverReveal = null;
        this._armBackgroundHoverReveal = null;
        this._bgHoverBg = null;
      };

      if (!needsHandoff || bg.classList.contains('is-bg-image')) {
        this.armBackgroundHoverReveal();
      }
    }

    armBackgroundHoverReveal() {
      if (typeof this._armBackgroundHoverReveal === 'function') {
        this._armBackgroundHoverReveal();
      }
    }

    cleanupBackgroundHoverReveal() {
      if (typeof this._cleanupBackgroundHoverReveal === 'function') {
        this._cleanupBackgroundHoverReveal();
      }
      this.classList.remove('is-bg-hover-ready');
    }

    initCustomBgParallax() {
      this.cleanupCustomBgParallax();

      const bg = this.querySelector('[data-grw-custom-bg]');
      if (!bg?.classList.contains('grw--custom-bg-parallax')) return;
      if (isTouchLikeDevice() || prefersReducedMotion()) return;

      const layers = bg.querySelector('.giclee-random-artwork__custom-bg-layers');
      if (!layers) return;

      const MAX_X = 22;
      const MAX_Y = 14;
      const EASE = 0.075;
      let targetX = 0;
      let targetY = 0;
      let curX = 0;
      let curY = 0;
      let rafId = 0;

      const tick = () => {
        rafId = 0;
        curX += (targetX - curX) * EASE;
        curY += (targetY - curY) * EASE;
        layers.style.setProperty('--grw-cbg-px', `${(-curX * MAX_X).toFixed(2)}px`);
        layers.style.setProperty('--grw-cbg-py', `${(-curY * MAX_Y).toFixed(2)}px`);
        if (Math.abs(targetX - curX) > 0.0008 || Math.abs(targetY - curY) > 0.0008) {
          rafId = window.requestAnimationFrame(tick);
        }
      };

      const startLoop = () => {
        if (!rafId) rafId = window.requestAnimationFrame(tick);
      };

      const onPointerMove = (event) => {
        const vw = window.innerWidth || 1;
        const vh = window.innerHeight || 1;
        targetX = Math.min(Math.max((event.clientX / vw) * 2 - 1, -1), 1);
        targetY = Math.min(Math.max((event.clientY / vh) * 2 - 1, -1), 1);
        startLoop();
      };

      const onPointerLeave = () => {
        targetX = 0;
        targetY = 0;
        startLoop();
      };

      window.addEventListener('pointermove', onPointerMove, { passive: true });
      document.addEventListener('pointerleave', onPointerLeave, { passive: true });

      this._cleanupCustomBgParallax = () => {
        window.removeEventListener('pointermove', onPointerMove);
        document.removeEventListener('pointerleave', onPointerLeave);
        if (rafId) window.cancelAnimationFrame(rafId);
        this._cleanupCustomBgParallax = null;
      };
    }

    cleanupCustomBgParallax() {
      if (typeof this._cleanupCustomBgParallax === 'function') {
        this._cleanupCustomBgParallax();
      }
    }

    parseEmbeddedPool() {
      const node = this.querySelector('[data-grw-pool]');
      if (!node) return [];
      try {
        const data = JSON.parse(node.textContent || '[]');
        return Array.isArray(data) ? data.map(normalizeProduct).filter(Boolean) : [];
      } catch {
        return [];
      }
    }

    setState(state) {
      this.dataset.state = state;
      if (this.drawButton) {
        this.drawButton.disabled = state === STATE.LOADING || state === STATE.DRAWING;
      }
      this.livingMuseumLight?.setState?.(state);
    }

    setPhase(text, { illuminate = false } = {}) {
      if (!this.phaseText) return;
      if (!text) {
        this.clearPhase();
        return;
      }
      window.clearTimeout(this.phaseSwapTimer);
      this.phaseWrap?.classList.remove('is-hidden');

      if (illuminate) {
        this.phaseText.classList.remove('is-swapping');
        this.renderPhaseLetterIlluminate(text);
        return;
      }

      this.phaseText.classList.add('is-swapping');
      this.phaseSwapTimer = window.setTimeout(() => {
        this.phaseText.classList.remove('is-letter-sweep');
        this.phaseText.removeAttribute('aria-label');
        this.phaseText.textContent = text;
        this.phaseText.classList.remove('is-swapping');
      }, 260);
    }

    /** Fade-out tekstu fazy (np. „Przeszukuję kolekcję…” gdy startuje wirowanie). */
    clearPhase() {
      if (!this.phaseText) return;
      window.clearTimeout(this.phaseSwapTimer);
      // Keep letter-sweep markup during fade so letters don't hard-cut mid-pulse.
      this.phaseWrap?.classList.add('is-hidden');
      this.phaseSwapTimer = window.setTimeout(() => {
        this.phaseText.classList.remove('is-letter-sweep');
        this.phaseText.removeAttribute('aria-label');
        this.phaseText.textContent = '';
        this.phaseText.classList.remove('is-swapping');
      }, 700);
    }

    /**
     * Fade out + shrink the gold CSS portal ring after search copy
     * (when the carousel / WebGL sequence begins).
     * Keep centering via top/left + translate; never bake translate into the
     * same transform that we scale — that pulls the ring toward the corner.
     */
    fadeOutPortalRing() {
      const portal = this.querySelector('[data-grw-portal]');
      if (!portal || portal.classList.contains('is-portal-faded')) return;
      const style = getComputedStyle(portal);
      const opacity = style.opacity || '0.8';
      const rawScale = style.scale && style.scale !== 'none' ? Number.parseFloat(style.scale) : 1;
      const fromScale = Number.isFinite(rawScale) ? rawScale : 1;
      const ease = 'cubic-bezier(0.22, 1, 0.36, 1)';
      const duration = `${PORTAL_FADE_MS / 1000}s`;

      portal.style.animation = 'none';
      portal.style.top = '50%';
      portal.style.left = '50%';
      portal.style.translate = '-50% -50%';
      portal.style.transform = 'none';
      portal.style.transformOrigin = '50% 50%';
      portal.style.scale = String(fromScale);
      portal.style.transition = `opacity ${duration} ${ease}, scale ${duration} ${ease}`;
      portal.style.opacity = opacity;
      portal.classList.add('is-portal-faded');
      void portal.offsetWidth;
      portal.style.opacity = '0';
      portal.style.scale = String(PORTAL_FADE_SCALE);
    }

    restorePortalRing() {
      const portal = this.querySelector('[data-grw-portal]');
      if (!portal) return;
      portal.classList.remove('is-portal-faded');
      portal.style.animation = '';
      portal.style.transition = '';
      portal.style.opacity = '';
      portal.style.transform = '';
      portal.style.transformOrigin = '';
      portal.style.translate = '';
      portal.style.top = '';
      portal.style.left = '';
      portal.style.scale = '';
    }

    /** Split loading copy into letters; CSS staggered pulse does the illuminate. */
    renderPhaseLetterIlluminate(source) {
      if (!this.phaseText) return;
      const text =
        cleanText(source) ||
        cleanText(this.dataset.phase1) ||
        cleanText(this.phaseText.textContent) ||
        'Przeszukuję kolekcję…';
      if (!text) return;

      this.phaseText.setAttribute('aria-label', text);
      this.phaseText.textContent = '';
      this.phaseText.classList.add('is-letter-sweep');

      if (prefersReducedMotion()) {
        this.phaseText.textContent = text;
        this.phaseText.classList.remove('is-letter-sweep');
        return;
      }

      const { visual, chars } = createLetterVisual(text, {
        visualClass: 'giclee-random-artwork__phase-visual',
        wordClass: 'giclee-random-artwork__phase-word',
        charClass: 'giclee-random-artwork__phase-char',
        prepareChar: (char, index) => {
          char.style.setProperty('--grw-char-i', String(index));
        },
      });

      this.phaseText.style.setProperty('--grw-phase-char-count', String(chars.length));
      this.phaseText.style.setProperty('--grw-phase-stagger', `${PHASE_LETTER_STAGGER_MS}ms`);
      this.phaseText.style.setProperty('--grw-phase-pulse', `${PHASE_LETTER_PULSE_MS}ms`);
      this.phaseText.appendChild(visual);
    }

    revealPanel(panel, state) {
      if (!panel) {
        this.setState(state);
        return;
      }
      panel.hidden = false;
      void panel.offsetWidth;
      this.setState(state);
    }

    async ensureFullPool() {
      if (!this.fetchFull || this.fullPoolLoaded) return;
      this.fullPoolLoaded = true;

      const fetched = await this.fetchAllProducts();
      if (!fetched.length) return;

      const byUrl = new Map();
      for (const item of [...this.pool, ...fetched]) {
        if (!item) continue;
        byUrl.set(item.url, mergeProductRecords(byUrl.get(item.url), item));
      }
      this.pool = Array.from(byUrl.values());
    }

    async fetchAllProducts() {
      const products = [];
      for (let page = 1; page <= FETCH_MAX_PAGES; page += 1) {
        let batch;
        try {
          const url = `${this.endpoint}?limit=${FETCH_PAGE_SIZE}&page=${page}`;
          const response = await fetch(url, { headers: { Accept: 'application/json' } });
          if (!response.ok) break;
          const data = await response.json();
          batch = Array.isArray(data?.products) ? data.products : [];
        } catch {
          break;
        }
        if (!batch.length) break;

        for (const product of batch) {
          const image = product?.images?.[0]?.src;
          if (!product?.handle || !image) continue;
          const available = Array.isArray(product.variants)
            ? product.variants.some((variant) => variant?.available)
            : true;
          products.push({
            rawTitle: product.title,
            artist: '',
            url: `${this.rootUrl}/products/${product.handle}`,
            image: sizedImageUrl(image, 1280),
            imageAlt: product.title,
            available,
          });
        }
        if (batch.length < FETCH_PAGE_SIZE) break;
      }
      return products.map(normalizeProduct).filter(Boolean);
    }

    pickWinner() {
      if (!this.pool.length) return null;
      const available = this.pool.filter((item) => item.available);
      let candidates = available.length ? available : this.pool;
      if (candidates.length > 1 && this.lastWinnerUrl) {
        const filtered = candidates.filter((item) => item.url !== this.lastWinnerUrl);
        if (filtered.length) candidates = filtered;
      }
      return candidates[Math.floor(Math.random() * candidates.length)];
    }

    preloadImage(src) {
      return new Promise((resolve) => {
        const img = new Image();
        let settled = false;
        const done = () => {
          if (settled) return;
          settled = true;
          resolve();
        };
        img.onload = done;
        img.onerror = done;
        img.src = src;
        if (img.complete) done();
        window.setTimeout(done, IMAGE_PRELOAD_TIMEOUT_MS);
      });
    }

    async draw() {
      if (this.isDrawing) return;
      this.isDrawing = true;
      window.clearTimeout(this.resultTeardownTimer);
      this.teardownScene();
      this.cleanupResultIdentityMotion();

      if (this.resultPanel) this.resultPanel.hidden = true;
      if (this.errorPanel) this.errorPanel.hidden = true;
      this.restorePortalRing();
      this.setState(STATE.LOADING);
      const loadingCopy =
        this.phases[0] ||
        cleanText(this.dataset.phase1) ||
        cleanText(this.phaseText?.textContent) ||
        'Przeszukuję kolekcję…';
      this.setPhase(loadingCopy, { illuminate: true });

      const startedAt = performance.now();
      try {
        await this.ensureFullPool();

        const winner = this.pickWinner();
        if (!winner) {
          this.revealPanel(this.errorPanel, STATE.ERROR);
          return;
        }

        await this.preloadImage(winner.image);

        const elapsed = performance.now() - startedAt;
        const minVisible = Math.max(this.minLoadingMs, PHASE_LETTER_MIN_VISIBLE_MS);
        if (elapsed < minVisible) {
          await wait(minVisible - elapsed);
        }

        await this.runDrawingSequence(winner);
        this.showResult(winner);
      } catch {
        this.teardownScene();
        this.revealPanel(this.errorPanel, STATE.ERROR);
      } finally {
        this.isDrawing = false;
      }
    }

    async runDrawingSequence(winner) {
      // Loading copy (phase 0) leaves as soon as the carousel spin begins.
      this.clearPhase();
      this.fadeOutPortalRing();
      this.setState(STATE.DRAWING);

      if (this.shouldUseWebGL()) {
        const ran = await this.runWebGLScene(winner);
        if (ran) return;
      }

      if (prefersReducedMotion()) {
        await wait(300);
        return;
      }
      const beats = this.phases.slice(1);
      for (const phrase of beats) {
        this.setPhase(phrase);
        await wait(this.phaseHoldMs);
      }
    }

    shouldUseWebGL() {
      if (!this.enableWebgl) return false;
      if (prefersReducedMotion()) return false;
      if (!this.webglUrl || !this.threeUrl || !this.canvasMount) return false;
      if (navigator.deviceMemory && navigator.deviceMemory < 2) return false;
      return hasWebGL();
    }

    buildSceneSample(winner) {
      const mobile = isMobileViewport();
      const size = mobile ? SAMPLE_MOBILE : SAMPLE_DESKTOP;
      const others = shuffle(this.pool.filter((item) => item.url !== winner.url));
      const picked = others.slice(0, Math.max(0, size - 1));
      const sample = shuffle([winner, ...picked]);
      const cardWidth = mobile ? 640 : 512;
      return sample.map((item) => ({
        url: item.url,
        title: item.title,
        image: sizedImageUrl(item.image, item === winner ? 900 : cardWidth),
      }));
    }

    populateResultContent(winner, imageUrl) {
      this.lastWinnerUrl = winner.url;
      if (this.resultImage) {
        this.resultImage.src = imageUrl || winner.image;
        this.resultImage.alt = winner.imageAlt;
      }

      const showMuseumIdentity =
        this.designVariant === 'v3' || this.designVariant === 'v4';
      if (this.resultArtist) {
        this.resultArtist.textContent = winner.artist || '';
        this.resultArtist.hidden = !showMuseumIdentity || !winner.artist;
      }
      if (this.resultTitle) this.resultTitle.textContent = winner.title;
      if (this.resultYear) {
        this.resultYear.textContent = winner.year ? `, ${winner.year}` : '';
        this.resultYear.hidden = !showMuseumIdentity || !winner.year;
      }
      if (this.resultLink) this.resultLink.href = winner.url;
      if (this.viewCta) this.viewCta.href = winner.url;
    }

    prepareHandoffTarget(winner, imageUrl) {
      this.populateResultContent(winner, imageUrl);
      this.classList.add('grw--handoff-prepare');
      if (this.resultPanel) this.resultPanel.hidden = false;
      void this.resultPanel?.offsetWidth;
      const decode = this.resultImage?.decode?.();
      if (decode) {
        decode.catch(() => {
          /* image may already be cached / broken */
        });
      }
    }

    getHandoffTargetRect() {
      const frame = this.resultLink;
      if (!frame || this.resultPanel?.hidden) return null;
      const rect = frame.getBoundingClientRect();
      if (rect.width < 8 || rect.height < 8) return null;
      return {
        left: rect.left,
        top: rect.top,
        width: rect.width,
        height: rect.height,
      };
    }

    async runWebGLScene(winner) {
      let safety = 0;
      try {
        const module = await import(this.webglUrl);
        const cards = this.buildSceneSample(winner);
        const winnerIndex = cards.findIndex((card) => card.url === winner.url);
        const winnerCard = cards[winnerIndex < 0 ? 0 : winnerIndex];
        const handoffImage = winnerCard?.image || winner.image;
        this._handoffImageUrl = handoffImage;
        this.wantTeardown = false;
        this.classList.add('grw--webgl');
        this.prepareHandoffTarget(winner, handoffImage);

        await new Promise((resolve) => {
          let settled = false;
          const finish = () => {
            if (settled) return;
            settled = true;
            resolve();
          };
          safety = window.setTimeout(finish, SCENE_SAFETY_MS);
          module
            .createOracleScene({
              mount: this.canvasMount,
              threeUrl: this.threeUrl,
              cards,
              winnerIndex: winnerIndex < 0 ? 0 : winnerIndex,
              reducedMotion: prefersReducedMotion(),
              isMobile: isMobileViewport(),
              onPhase: (index) => {
                // Never fall back to phase 0 — that loading line must stay gone during spin.
                const text = this.phases[index];
                if (text) this.setPhase(text);
              },
              onHandoffPrepare: () => {
                this.prepareHandoffTarget(winner, handoffImage);
              },
              getHandoffTarget: () => this.getHandoffTargetRect(),
              onComplete: finish,
            })
            .then((controller) => {
              this.sceneController = controller;
              if (this.wantTeardown) this.teardownScene();
            })
            .catch(finish);
        });
        return true;
      } catch {
        this.teardownScene();
        return false;
      } finally {
        window.clearTimeout(safety);
      }
    }

    bindFinaleExhibitHover() {
      this.unbindFinaleExhibitHover();
      if (!this.classList.contains('grw--webgl-finale')) return;
      if (!this.resultLink || typeof this.sceneController?.setExhibitHover !== 'function') return;

      this._onFinaleExhibitEnter = () => this.sceneController?.setExhibitHover?.(true);
      this._onFinaleExhibitLeave = () => this.sceneController?.setExhibitHover?.(false);
      this.resultLink.addEventListener('pointerenter', this._onFinaleExhibitEnter);
      this.resultLink.addEventListener('pointerleave', this._onFinaleExhibitLeave);
      this.resultLink.addEventListener('focus', this._onFinaleExhibitEnter);
      this.resultLink.addEventListener('blur', this._onFinaleExhibitLeave);
    }

    unbindFinaleExhibitHover() {
      if (this.resultLink && this._onFinaleExhibitEnter) {
        this.resultLink.removeEventListener('pointerenter', this._onFinaleExhibitEnter);
        this.resultLink.removeEventListener('pointerleave', this._onFinaleExhibitLeave);
        this.resultLink.removeEventListener('focus', this._onFinaleExhibitEnter);
        this.resultLink.removeEventListener('blur', this._onFinaleExhibitLeave);
      }
      this._onFinaleExhibitEnter = null;
      this._onFinaleExhibitLeave = null;
      try {
        this.sceneController?.setExhibitHover?.(false);
      } catch {
        /* scene may already be gone */
      }
    }

    teardownScene() {
      this.wantTeardown = true;
      this.unbindFinaleExhibitHover();
      if (this.sceneController) {
        try {
          this.sceneController.destroy({ instant: true });
        } catch {
          /* Scene can already be disposed. */
        }
        this.sceneController = null;
      }
      if (this.canvasMount) {
        this.canvasMount.replaceChildren();
        this.canvasMount.style.opacity = '';
      }
      this.classList.remove('grw--webgl');
      this.classList.remove('grw--webgl-finale');
      this.classList.remove('grw--handoff-prepare');
      this.classList.remove('grw--seamless-handoff');
      this._handoffImageUrl = '';
    }

    showResult(winner) {
      const webglFinale = this.classList.contains('grw--webgl') && this.sceneController;
      const handoffSrc =
        this._handoffImageUrl ||
        this.resultImage?.getAttribute('src') ||
        winner.image;
      this.classList.remove('grw--handoff-prepare');
      this.populateResultContent(winner, handoffSrc);
      if (this.resultPanel) {
        this.resultPanel.hidden = false;
        this.resultPanel.style.visibility = '';
        this.resultPanel.style.opacity = '';
      }

      if (webglFinale) {
        // Keep the last WebGL frame as the artwork; HTML only supplies captions + CTA.
        this.classList.add('grw--webgl-finale');
        this.classList.add('grw--seamless-handoff');
        try {
          this.sceneController.freeze?.();
        } catch {
          /* ignore */
        }
        this.bindFinaleExhibitHover();
      } else {
        this.unbindFinaleExhibitHover();
      }

      this.revealPanel(this.resultPanel, STATE.RESULT);
      if (webglFinale && this.dataset.designVariant === 'v4') {
        this.dataset.resultStage = 'actions';
        this.dataset.resultCeremony = 'complete';
      }
      this.playResultIdentityMotion();
      this.livingMuseumLight?.focusResult?.(this.resultLink);
      // Intentionally no teardown on WebGL finale — the frozen card IS the exhibit.
    }
  }

  if (!customElements.get('giclee-random-artwork')) {
    customElements.define('giclee-random-artwork', GicleeRandomArtwork);
  }
})();
