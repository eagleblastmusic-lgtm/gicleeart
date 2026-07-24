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

  const MIN_LOADING_MS = 700;
  const PHASE_HOLD_MS = 1100;
  const FETCH_PAGE_SIZE = 250;
  const FETCH_MAX_PAGES = 20;
  const IMAGE_PRELOAD_TIMEOUT_MS = 6000;
  const SAMPLE_DESKTOP = 16;
  const SAMPLE_MOBILE = 8;
  const SCENE_SAFETY_MS = 9000;
  const RESULT_TEARDOWN_MS = 700;
  const BG_VIDEO_FADE_MS = 700;
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
      this.phaseText = this.querySelector('[data-grw-phase]');
      this.resultPanel = this.querySelector('[data-grw-result]');
      this.resultLink = this.querySelector('[data-grw-result-link]');
      this.resultImage = this.querySelector('[data-grw-result-image]');
      this.resultArtist = this.querySelector('[data-grw-result-artist]');
      this.resultTitle = this.querySelector('[data-grw-result-title]');
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
      this.initBackgroundVideoHandoff();
      if (!this.livingMuseumLight) this.initCustomBgParallax();
    }

    disconnectedCallback() {
      this.drawButton?.removeEventListener('click', this._onDrawClick);
      this.replayButton?.removeEventListener('click', this._onDrawClick);
      this.retryButton?.removeEventListener('click', this._onDrawClick);
      this.cleanupBackgroundVideoHandoff({ release: true });
      this.cleanupCustomBgParallax();
      this.livingMuseumLight?.destroy?.();
      this.livingMuseumLight = null;
      window.clearTimeout(this.resultTeardownTimer);
      this.teardownScene();
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
        return;
      }

      const finishHandoff = () => {
        this.releaseBackgroundVideo(video);
        bg.classList.add('is-bg-video-disposed');
        this._bgVideoActive = false;
        this.cleanupBackgroundVideoHandoff();
      };

      const revealImage = () => {
        if (bg.classList.contains('is-bg-image')) return;
        bg.classList.add('is-bg-image');
        try {
          if (!video.paused) video.pause();
        } catch (_) {
          /* ignore */
        }

        // Po fade-out zdejmij warstwę video z DOM — samo opacity:0 zostawia dekoder.
        window.clearTimeout(this._bgVideoDisposeTimer);
        const delay = prefersReducedMotion() ? 0 : BG_VIDEO_FADE_MS;
        this._bgVideoDisposeTimer = window.setTimeout(finishHandoff, delay);
      };

      if (prefersReducedMotion()) {
        revealImage();
        return;
      }

      this._bgVideoActive = true;
      this._bgVideo = video;
      this._onBgVideoEnded = revealImage;
      this._onBgVideoError = revealImage;
      video.addEventListener('ended', this._onBgVideoEnded);
      video.addEventListener('error', this._onBgVideoError);

      // Już domknięty / brak duration (np. cache) — od razu grafika
      if (video.ended || (video.readyState >= 2 && Number.isFinite(video.duration) && video.duration > 0 && video.currentTime >= video.duration - 0.05)) {
        revealImage();
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
      if (release && this._bgVideo) {
        this.releaseBackgroundVideo(this._bgVideo);
        this._bgVideoActive = false;
      }
      this._bgVideo = null;
      this._onBgVideoEnded = null;
      this._onBgVideoError = null;
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

    setPhase(text) {
      if (!this.phaseText || !text) return;
      this.phaseText.classList.add('is-swapping');
      window.setTimeout(() => {
        this.phaseText.textContent = text;
        this.phaseText.classList.remove('is-swapping');
      }, 260);
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

      if (this.resultPanel) this.resultPanel.hidden = true;
      if (this.errorPanel) this.errorPanel.hidden = true;
      if (this.phases[0]) this.setPhase(this.phases[0]);
      this.setState(STATE.LOADING);

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
        if (elapsed < MIN_LOADING_MS) {
          await wait(MIN_LOADING_MS - elapsed);
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
        await wait(PHASE_HOLD_MS);
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

    async runWebGLScene(winner) {
      let safety = 0;
      try {
        const module = await import(this.webglUrl);
        const cards = this.buildSceneSample(winner);
        const winnerIndex = cards.findIndex((card) => card.url === winner.url);
        this.wantTeardown = false;
        this.classList.add('grw--webgl');

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
              onPhase: (index) => this.setPhase(this.phases[index] || this.phases.at(-1)),
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

    teardownScene() {
      this.wantTeardown = true;
      if (this.sceneController) {
        try {
          this.sceneController.destroy();
        } catch {
          /* Scene can already be disposed. */
        }
        this.sceneController = null;
      }
      this.classList.remove('grw--webgl');
    }

    showResult(winner) {
      this.lastWinnerUrl = winner.url;
      if (this.resultImage) {
        this.resultImage.src = winner.image;
        this.resultImage.alt = winner.imageAlt;
      }

      const showMuseumIdentity = this.designVariant === 'v3';
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
      this.revealPanel(this.resultPanel, STATE.RESULT);
      this.livingMuseumLight?.focusResult?.(this.resultLink);

      if (this.classList.contains('grw--webgl')) {
        this.resultTeardownTimer = window.setTimeout(() => this.teardownScene(), RESULT_TEARDOWN_MS);
      }
    }
  }

  if (!customElements.get('giclee-random-artwork')) {
    customElements.define('giclee-random-artwork', GicleeRandomArtwork);
  }
})();
