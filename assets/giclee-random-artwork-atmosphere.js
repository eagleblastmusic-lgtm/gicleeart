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

  class MuseumAtmosphere {
    constructor(root) {
      this.root = root;
      this.scene = root.querySelector('[data-grw-scene]');
      this.layer = root.querySelector('[data-grw-atmosphere]');
      this.glow = root.querySelector('[data-grw-atmosphere-glow]');
      this.canvas = root.querySelector('[data-grw-atmosphere-dust]');
      this.ctx = this.canvas?.getContext('2d', { alpha: true }) || null;

      this.intensity = clamp(Number(root.dataset.atmosphereIntensity || 38) / 100, 0, 1);
      this.dustLevel = clamp(Number(root.dataset.atmosphereDust || 28) / 100, 0, 1);
      this.enabled = root.dataset.atmosphereEnabled !== 'false';
      this.reducedMotion = window.matchMedia?.(REDUCED_MOTION_QUERY).matches ?? false;
      this.mobileMode = window.matchMedia?.(MOBILE_QUERY).matches ?? false;

      this.width = 0;
      this.height = 0;
      this.dpr = 1;
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
      this.tick = this.tick.bind(this);

      this.init();
    }

    init() {
      if (!this.enabled || !this.scene || !this.layer) {
        this.layer?.setAttribute('hidden', '');
        return;
      }

      this.layer.style.setProperty('--grw-atmosphere-level', this.intensity.toFixed(3));
      this.layer.style.setProperty('--grw-dust-level', this.dustLevel.toFixed(3));
      this.root.dataset.atmosphereReady = 'true';

      this.resizeObserver = new ResizeObserver(() => this.resize());
      this.resizeObserver.observe(this.scene);

      this.intersectionObserver = new IntersectionObserver(
        (entries) => {
          const entry = entries[entries.length - 1];
          this.visible = Boolean(entry?.isIntersecting);
          this.updateLoopState();
        },
        { rootMargin: '120px 0px', threshold: 0.01 },
      );
      this.intersectionObserver.observe(this.root);

      document.addEventListener('visibilitychange', this.onVisibilityChange, { passive: true });

      this.resize();

      if (!this.mobileMode && !this.reducedMotion && this.glow) {
        this.scene.addEventListener('pointermove', this.onPointerMove, { passive: true });
        this.scene.addEventListener('pointerenter', this.onPointerEnter, { passive: true });
        this.scene.addEventListener('pointerleave', this.onPointerLeave, { passive: true });
      } else {
        this.root.dataset.atmosphereMode = 'static';
      }

      this.updateLoopState();
    }

    resize() {
      if (!this.scene) return;
      const rect = this.scene.getBoundingClientRect();
      this.width = Math.max(1, rect.width);
      this.height = Math.max(1, rect.height);
      this.dpr = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO);

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
          this.createParticles();
        }
      }

      this.positionGlow();
    }

    createParticles() {
      if (!this.width || !this.height) return;
      const areaScale = clamp((this.width * this.height) / (1440 * 900), 0.55, 1.35);
      const count = Math.round(clamp(10 + this.dustLevel * 26 * areaScale, 10, 36));
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
      const rect = this.scene.getBoundingClientRect();
      this.targetX = clamp(event.clientX - rect.left, 0, rect.width);
      this.targetY = clamp(event.clientY - rect.top, 0, rect.height);
      this.targetPresence = 1;
      this.updateLoopState();
    }

    onPointerEnter() {
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

      const smoothing = 1 - Math.pow(0.001, deltaMs / 1000);
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
      const size = this.glow.getBoundingClientRect().width || 560;
      const x = this.currentX - size / 2;
      const y = this.currentY - size / 2;
      this.glow.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`;
      this.glow.style.opacity = String(
        clamp(this.intensity * (0.38 + this.currentPresence * 0.42), 0, 0.42).toFixed(3),
      );
    }

    drawDust(now, deltaMs) {
      if (!this.ctx || !this.canvas || !this.particles.length) return;
      const ctx = this.ctx;
      const deltaSeconds = Math.min(0.08, deltaMs / 1000);
      const lightRadius = Math.max(260, Math.min(this.width, this.height) * 0.42);

      ctx.clearRect(0, 0, this.width, this.height);
      ctx.globalCompositeOperation = 'source-over';

      for (const particle of this.particles) {
        particle.y -= particle.speed * deltaSeconds;
        particle.x += Math.sin(now * 0.00018 + particle.phase) * particle.drift * deltaSeconds;

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
        dustLevel: this.dustLevel,
        particleCount: this.particles.length,
        dpr: this.dpr,
      };
    }

    destroy() {
      if (this.rafId) window.cancelAnimationFrame(this.rafId);
      this.rafId = 0;
      this.resizeObserver?.disconnect();
      this.intersectionObserver?.disconnect();
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
