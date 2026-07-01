/*
 * Losuj Obraz — Fine Art Oracle (kontroler).
 * Dane (Liquid + AJAX), losowanie, maszyna stanow, capability gate.
 * Scene WebGL uruchamia giclee-random-artwork-webgl.js (dynamic import).
 * Wynik, tytul, zdjecie i CTA pozostaja w HTML/CSS.
 */
(() => {
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

  const prefersReducedMotion = () =>
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

  const isMobileViewport = () =>
    window.matchMedia?.('(max-width: 749px)').matches ?? window.innerWidth < 750;

  const wait = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms));

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
    if (!raw || !raw.title || !raw.image || !raw.url) return null;
    return {
      title: String(raw.title),
      url: String(raw.url),
      image: String(raw.image),
      imageAlt: raw.imageAlt ? String(raw.imageAlt) : String(raw.title),
      available: raw.available !== false,
    };
  };

  class GicleeRandomArtwork extends HTMLElement {
    connectedCallback() {
      this.rootUrl = this.dataset.rootUrl || '';
      this.endpoint = this.dataset.productsEndpoint || `${this.rootUrl}/collections/all/products.json`;
      this.fetchFull = this.dataset.fetchFull === 'true';
      this.enableWebgl = this.dataset.enableWebgl !== 'false';
      this.webglUrl = this.dataset.webglUrl || '';
      this.threeUrl = this.dataset.threeUrl || '';

      this.fullPoolLoaded = false;
      this.lastWinnerUrl = null;
      this.isDrawing = false;
      this.sceneController = null;
      this.wantTeardown = false;
      this.canvasMount = this.querySelector('[data-grw-canvas-mount]');

      this.phases = [this.dataset.phase1, this.dataset.phase2, this.dataset.phase3]
        .map((text) => (text || '').trim())
        .filter(Boolean);

      this.intro = this.querySelector('[data-grw-intro]');
      this.drawButton = this.querySelector('[data-grw-draw]');
      this.phaseText = this.querySelector('[data-grw-phase]');
      this.resultPanel = this.querySelector('[data-grw-result]');
      this.resultLink = this.querySelector('[data-grw-result-link]');
      this.resultImage = this.querySelector('[data-grw-result-image]');
      this.resultTitle = this.querySelector('[data-grw-result-title]');
      this.viewCta = this.querySelector('[data-grw-view]');
      this.replayButton = this.querySelector('[data-grw-replay]');
      this.errorPanel = this.querySelector('[data-grw-error]');
      this.retryButton = this.querySelector('[data-grw-retry]');

      this.pool = this.parseEmbeddedPool();

      this.drawButton?.addEventListener('click', () => this.draw());
      this.replayButton?.addEventListener('click', () => this.draw());
      this.retryButton?.addEventListener('click', () => this.draw());

      this.setState(STATE.IDLE);
    }

    disconnectedCallback() {
      window.clearTimeout(this.resultTeardownTimer);
      this.teardownScene();
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
      // Wymuszenie reflow, aby przejscie opacity/transform zadzialalo po odkryciu.
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
        if (item && !byUrl.has(item.url)) byUrl.set(item.url, item);
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
            title: product.title,
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

      // Fallback CSS — narracyjne teksty na portalu CSS.
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
              // Jesli teardown poproszono zanim scena sie zainicjalizowala.
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
          /* scena moze byc juz zwolniona */
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
      if (this.resultTitle) this.resultTitle.textContent = winner.title;
      if (this.resultLink) this.resultLink.href = winner.url;
      if (this.viewCta) this.viewCta.href = winner.url;
      this.revealPanel(this.resultPanel, STATE.RESULT);

      // Karta wyniku wjezdza, potem scena WebGL wygasa i zwalnia zasoby.
      if (this.classList.contains('grw--webgl')) {
        this.resultTeardownTimer = window.setTimeout(() => this.teardownScene(), RESULT_TEARDOWN_MS);
      }
    }
  }

  if (!customElements.get('giclee-random-artwork')) {
    customElements.define('giclee-random-artwork', GicleeRandomArtwork);
  }
})();
