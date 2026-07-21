/*
 * Losuj Obraz — museum atmosphere controller.
 * Smooth cursor light + sparse canvas dust, scoped to the section viewport.
 */
(() => {
  'use strict';

  if (window.GICLEE_RANDOM_ARTWORK_ATMOSPHERE) return;

  const MAX_DEVICE_PIXEL_RATIO = 1.5;
  const DUST_FRAME_INTERVAL_MS = 1000 / 24;
  const MOBILE_QUERY = '(max-width: 749px), (hover: none), (pointer: coarse)';
  const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
  const controllers = new Set();

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const datasetNumber = (root, key, fallback, min, max) => {
    const raw = Number(root.dataset[key]);
    return clamp(Number.isFinite(raw) ? raw : fallback, min, max);
  };

  class MuseumAtmosphere {
    constructor(root) {
      this.root = root;
      this.scene = root.querySelector('[data-grw-scene]');
      this.layer = root.querySelector('[data-grw-atmosphere]');
      this.glow = root.querySelector('[data-grw-atmosphere-glow]');
      this.canvas = root.querySelector('[data-grw-atmosphere-dust]');
      this.ctx = this.canvas?.getContext('2d', { alpha: true }) || null;

      this.intensity = datasetNumber(root, 'atmosphereIntensity', 35, 0, 70) / 100;
      this.glowSizeScale = datasetNumber(root, 'atmosphereGlowSize', 100, 60, 160) / 100;
      this.glowResponse = datasetNumber(root, 'atmosphereGlowResponse', 50, 10, 100);
      this.hazeLevel = datasetNumber(root, 'atmosphereHaze', 100, 0, 100) / 100;
      this.hazeSpeed = datasetNumber(root, 'atmosphereHazeSpeed', 100, 0, 200) / 100;
      this.dustLevel = datasetNumber(root, 'atmosphereDust', 25, 0, 60) / 100;
      this.dustAmount = datasetNumber(root, 'atmosphereDustAmount', 50, 0, 100) / 100;
      this.dustSpeed = datasetNumber(root, 'atmosphereDustSpeed', 100, 0, 200) / 100;
      this.enabled = root.dataset.atmosphereEnabled !== 'false';
      this.reducedMotion = window.matchMedia?.(REDUCED_MOTION_QUERY).matches ?? false;
      this.mobileMode = window.matchMedia?.(MOBILE_QUERY).matches ?? false;

      this.width = 0;
      this.height = 0;
      this.dpr = 1;
      this.glowSize = 560;
      this.sceneRect = null;
      this.targetX = 0;
      this.targetY = 0;
      this.currentX = 0;
      this.currentY = 0;
      this.targetPresence = 0.42;
      this.currentPresence = 0.42;
      this.visible = true;
      this.pageVisible = !document.hidden;
      this.lastFrameAt = 0;
      this.lastDustAt = 0;
      this.rafId = 0;
      this.particles = [];

      this.onPointerMove = this.onPointerMove.bind(this);
      this.onPointerEnter = this.onPointerEnter.bind(this);
      this.onPointerLeave = this.onPointerLeave.bind(this);
      this.onVisibilityChange = this.onVisibilityChange.bind(this);
      this.resize = this.resize.bind(this);
      this.tick = this.tick.bind(this);

      this.init();
    }

    init() {
      if (!this.enabled || !this.scene || !this.layer) {
        this.layer?.setAttribute('hidden', '');
        return;
      }

      this.applyTuning();
      this.root.dataset.atmosphereReady = 'true';

      if ('ResizeObserver' in window) {
        this.resizeObserver = new ResizeObserver(this.resize);
        this.resizeObserver.observe(this.scene);
      } else {
        window.addEventListener('resize', this.resize, { passive: true });
      }

      if ('IntersectionObserver' in window) {
        this.intersectionObserver = new IntersectionObserver(
          (entries) => {
            const entry = entries[entries.length - 1];
            this.visible = Boolean(entry?.isIntersecting);
            this.updateLoopState();
          },
          { rootMargin: '120px 0px', threshold: 0.01 },
        );
        this.intersectionObserver.observe(this.root);
      }

      document.addEventListener('visibilitychange', this.onVisibilityChange, { passive: true });

      this.resize();

      if (!this.mobileMode && !this.reducedMotion && this.glow) {
        this.root.dataset.atmosphereMode = 'interactive';
        this.scene.addEventListener('pointermove', this.onPointerMove, { passive: true });
        this.scene.addEventListener('pointerenter', this.onPointerEnter, { passive: true });
        this.scene.addEventListener('pointerleave', this.onPointerLeave, { passive: true });
      } else {
        this.root.dataset.atmosphereMode = 'static';
      }

      this.updateLoopState();
    }

    applyTuning() {
      if (!this.layer) return;

      const galleryOpacity = this.intensity * 0.46 * this.hazeLevel;
      const depthOpacity = this.intensity * 0.34 * this.hazeLevel;
      const loadingOpacity = this.intensity * 0.52 * this.hazeLevel;
      const speed = Math.max(0.05, this.hazeSpeed);

      this.layer.style.setProperty('--grw-atmosphere-level', this.intensity.toFixed(3));
      this.layer.style.setProperty('--grw-dust-level', this.dustLevel.toFixed(3));
      this.layer.style.setProperty('--grw-haze-gallery-opacity', galleryOpacity.toFixed(4));
      this.layer.style.setProperty('--grw-haze-depth-opacity', depthOpacity.toFixed(4));
      this.layer.style.setProperty('--grw-haze-loading-opacity', loadingOpacity.toFixed(4));
      this.layer.style.setProperty(
        '--grw-haze-gallery-mobile-opacity',
        (galleryOpacity * 0.52).toFixed(4),
      );
      this.layer.style.setProperty(
        '--grw-haze-depth-mobile-opacity',
        (depthOpacity * 0.47).toFixed(4),
      );
      this.layer.style.setProperty('--grw-haze-gallery-duration', `${(22 / speed).toFixed(2)}s`);
      this.layer.style.setProperty('--grw-haze-depth-duration', `${(30 / speed).toFixed(2)}s`);
      this.root.dataset.atmosphereHazePaused = this.hazeSpeed <= 0.01 ? 'true' : 'false';
    }

    resize() {
      if (!this.scene) return;
      const rect = this.scene.getBoundingClientRect();
      this.sceneRect = rect;
      this.width = Math.max(1, rect.width);
      this.height = Math.max(1, rect.height);
      this.dpr = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO);

      const baseGlowSize = clamp(window.innerWidth * 0.46, 420, 700);
      this.glowSize = clamp(baseGlowSize * this.glowSizeScale, 280, 1120);
      if (this.glow) this.glow.style.width = `${this.glowSize.toFixed(1)}px`;

      if (!this.currentX && !this.currentY) {
        this.targetX = this.currentX = this.width * 0.5;
        this.targetY = this.currentY = this.height * 0.43;
      } else {
        this.targetX = clamp(this.targetX, 0, this.width);
        this.targetY = clamp(this.targetY, 0, this.height);
        this.currentX = clamp(this.currentX, 0, this.width);
        this.currentY = clamp(this.currentY, 0, this.height);
      }

      if (this.canvas && this.ctx && !this.mobileMode && !this.reducedMotion) {
        const pixelWidth = Math.max(1, Math.round(this.width * this.dpr));
        const pixelHeight = Math.max(1, Math.round(this.height * this.dpr));
        if (this.canvas.width !== pixelWidth || this.canvas.height !== pixelHeight) {
          this.canvas.width = pixelWidth;
          this.canvas.height = pixelHeight;
          this.canvas.style.width = `${this.width}px`;
          this.canvas.style.height = `${this.height}px`;
          this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
        }
        this.createParticles();
      }

      this.positionGlow();
    }

    createParticles() {
      if (!this.width || !this.height || this.dustLevel <= 0 || this.dustAmount <= 0) {
        this.particles = [];
        return;
      }

      const areaScale = clamp((this.width * this.height) / (1440 * 900), 0.55, 1.35);
      const baseCount = 10 + this.dustLevel * 26 * areaScale;
      const amountScale = this.dustAmount / 0.5;
      const count = Math.round(clamp(baseCount * amountScale, 0, 48));

      this.particles = Array.from({ length: count }, (_, index) => {
        const layer = index % 3;
        const depth = layer === 0 ? 0.3 : layer === 1 ? 0.58 : 0.88;
        return {
          x: Math.random() * this.width,
          y: Math.random() * this.height,
          depth,
          radius: 0.32 + Math.random() * (0.62 + depth * 0.5),
          speed: 1.2 + Math.random() * (2.6 + depth * 3.2),
          drift: 1.6 + Math.random() * (3 + depth * 4),
          phase: Math.random() * Math.PI * 2,
          alpha: 0.025 + Math.random() * (0.045 + depth * 0.06),
        };
      });
    }

    onPointerMove(event) {
      const rect = this.sceneRect || this.scene.getBoundingClientRect();
      this.targetX = clamp(event.clientX - rect.left, 0, rect.width);
      this.targetY = clamp(event.clientY - rect.top, 0, rect.height);
      this.targetPresence = 1;
      this.updateLoopState();
    }

    onPointerEnter() {
      this.sceneRect = this.scene.getBoundingClientRect();
      this.targetPresence = 0.82;
      this.updateLoopState();
    }

    onPointerLeave() {
      this.targetX = this.width * 0.5;
      this.targetY = this.height * 0.43;
      this.targetPresence = 0.34;
      this.updateLoopState();
    }

    onVisibilityChange() {
      this.pageVisible = !document.hidden;
      this.updateLoopState();
    }

    updateLoopState() {
      const shouldRun =
        this.enabled &&
        this.visible &&
        this.pageVisible &&
        !this.mobileMode &&
        !this.reducedMotion;

      if (shouldRun && !this.rafId) {
        this.lastFrameAt = performance.now();
        this.rafId = window.requestAnimationFrame(this.tick);
      } else if (!shouldRun && this.rafId) {
        window.cancelAnimationFrame(this.rafId);
        this.rafId = 0;
      }
    }

    tick(now) {
      this.rafId = 0;
      const deltaMs = Math.min(50, Math.max(0, now - this.lastFrameAt));
      this.lastFrameAt = now;

      const responseTimeMs = clamp(380 - this.glowResponse * 4.7, 60, 340);
      const smoothing = 1 - Math.exp(-deltaMs / responseTimeMs);
      this.currentX += (this.targetX - this.currentX) * smoothing;
      this.currentY += (this.targetY - this.currentY) * smoothing;
      this.currentPresence += (this.targetPresence - this.currentPresence) * smoothing;
      this.positionGlow();

      if (now - this.lastDustAt >= DUST_FRAME_INTERVAL_MS) {
        this.drawDust(now, Math.max(DUST_FRAME_INTERVAL_MS, now - this.lastDustAt));
        this.lastDustAt = now;
      }

      if (this.visible && this.pageVisible) {
        this.rafId = window.requestAnimationFrame(this.tick);
      }
    }

    positionGlow() {
      if (!this.glow) return;
      const x = this.currentX - this.glowSize / 2;
      const y = this.currentY - this.glowSize / 2;
      this.glow.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`;
      this.glow.style.opacity = String(
        clamp(this.intensity * (0.38 + this.currentPresence * 0.42), 0, 0.42).toFixed(3),
      );
    }

    drawDust(now, deltaMs) {
      if (!this.ctx || !this.canvas) return;
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.width, this.height);
      if (!this.particles.length) return;

      const deltaSeconds = Math.min(0.08, deltaMs / 1000);
      const lightRadius = Math.max(260, Math.min(this.width, this.height) * 0.42);
      ctx.globalCompositeOperation = 'source-over';

      for (const particle of this.particles) {
        particle.y -= particle.speed * this.dustSpeed * deltaSeconds;
        particle.x +=
          Math.sin(now * 0.00018 + particle.phase) *
          particle.drift *
          this.dustSpeed *
          deltaSeconds;

        if (particle.y < -8) {
          particle.y = this.height + 8;
          particle.x = Math.random() * this.width;
        }
        if (particle.x < -8) particle.x = this.width + 8;
        if (particle.x > this.width + 8) particle.x = -8;

        const dx = particle.x - this.currentX;
        const dy = particle.y - this.currentY;
        const lightCatch = clamp(1 - Math.hypot(dx, dy) / lightRadius, 0, 1);
        const depthGain = 0.62 + particle.depth * 0.5;
        const alpha =
          particle.alpha *
          this.dustLevel *
          depthGain *
          (0.5 + lightCatch * 1.2) *
          (0.62 + this.currentPresence * 0.38);

        if (alpha <= 0.002) continue;

        const radius = particle.radius * (0.78 + particle.depth * 0.38);
        if (lightCatch > 0.48 && particle.depth > 0.5) {
          ctx.beginPath();
          ctx.fillStyle = `rgba(230, 205, 134, ${(alpha * 0.22).toFixed(4)})`;
          ctx.arc(particle.x, particle.y, radius * 2.6, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.beginPath();
        ctx.fillStyle = `rgba(255, 248, 229, ${alpha.toFixed(4)})`;
        ctx.arc(particle.x, particle.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    status() {
      return {
        enabled: this.enabled,
        mode: this.mobileMode || this.reducedMotion ? 'static' : 'interactive',
        visible: this.visible,
        intensity: this.intensity,
        glowSize: this.glowSizeScale,
        glowResponse: this.glowResponse,
        hazeLevel: this.hazeLevel,
        hazeSpeed: this.hazeSpeed,
        dustLevel: this.dustLevel,
        dustAmount: this.dustAmount,
        dustSpeed: this.dustSpeed,
        particleCount: this.particles.length,
        dpr: this.dpr,
      };
    }

    destroy() {
      if (this.rafId) window.cancelAnimationFrame(this.rafId);
      this.rafId = 0;
      this.resizeObserver?.disconnect();
      this.intersectionObserver?.disconnect();
      window.removeEventListener('resize', this.resize);
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
      this.scene?.removeEventListener('pointermove', this.onPointerMove);
      this.scene?.removeEventListener('pointerenter', this.onPointerEnter);
      this.scene?.removeEventListener('pointerleave', this.onPointerLeave);
      this.root.removeAttribute('data-atmosphere-ready');
      controllers.delete(this);
    }
  }

  const initWithin = (scope = document) => {
    const roots = scope.matches?.('giclee-random-artwork')
      ? [scope]
      : Array.from(scope.querySelectorAll?.('giclee-random-artwork') || []);

    roots.forEach((root) => {
      if (root.dataset.atmosphereReady === 'true') return;
      const controller = new MuseumAtmosphere(root);
      if (controller.enabled && controller.layer) controllers.add(controller);
    });
  };

  window.GICLEE_RANDOM_ARTWORK_ATMOSPHERE = {
    status: () => Array.from(controllers, (controller) => controller.status()),
    refresh: () => initWithin(document),
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => initWithin(document), { once: true });
  } else {
    initWithin(document);
  }

  document.addEventListener('shopify:section:load', (event) => initWithin(event.target));
  document.addEventListener('shopify:section:unload', (event) => {
    controllers.forEach((controller) => {
      if (event.target?.contains(controller.root)) controller.destroy();
    });
  });
})();
