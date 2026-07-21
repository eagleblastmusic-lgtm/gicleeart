/*
 * Losuj Obraz V3 — Living Museum Light.
 * One scoped pointer model drives spotlight, optional background parallax and dust.
 */
(() => {
  'use strict';

  if (window.GICLEE_LIVING_MUSEUM_LIGHT) return;

  const DPR_CAP = 1.35;
  const DUST_FRAME_MS = 1000 / 24;
  const MOBILE_QUERY = '(max-width: 749px), (hover: none), (pointer: coarse)';
  const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  const readNumber = (root, key, fallback, min, max) => {
    const value = Number(root.dataset[key]);
    return clamp(Number.isFinite(value) ? value : fallback, min, max);
  };

  class LivingMuseumLightController {
    constructor(root) {
      this.root = root;
      this.scene = root.querySelector('[data-grw-scene]');
      this.layer = root.querySelector('[data-grw-living-museum]');
      this.spotlight = root.querySelector('[data-grw-living-spotlight]');
      this.dustCanvas = root.querySelector('[data-grw-living-dust]');
      this.dustContext = this.dustCanvas?.getContext('2d', { alpha: true }) || null;
      this.drawButton = root.querySelector('[data-grw-draw]');
      this.portal = root.querySelector('[data-grw-portal]');
      this.backgroundLayers = root.querySelector('.grw--custom-bg-parallax .giclee-random-artwork__custom-bg-layers');

      this.lightEnabled = root.dataset.livingLightEnabled !== 'false';
      this.dustEnabled = root.dataset.livingDustEnabled !== 'false';
      this.intensity = readNumber(root, 'livingLightIntensity', 45, 0, 100) / 100;
      this.reducedMotion = window.matchMedia?.(REDUCED_QUERY).matches ?? false;
      this.coarsePointer = window.matchMedia?.(MOBILE_QUERY).matches ?? false;
      this.lowMemory = Boolean(globalThis.navigator?.deviceMemory && globalThis.navigator.deviceMemory < 4);
      this.allowTracking = this.lightEnabled && !this.reducedMotion && !this.coarsePointer;
      this.allowDust = this.dustEnabled && !this.reducedMotion && !this.coarsePointer && !this.lowMemory;

      this.state = 'idle';
      this.visible = true;
      this.pageVisible = document.visibilityState !== 'hidden';
      this.pointerInside = false;
      this.buttonHover = false;
      this.sceneRect = null;
      this.buttonRect = null;
      this.resultRect = null;
      this.width = 1;
      this.height = 1;
      this.spotlightWidth = 760;
      this.spotlightHeight = 420;
      this.dpr = 1;
      this.targetX = 0;
      this.targetY = 0;
      this.currentX = 0;
      this.currentY = 0;
      this.targetOpacity = 0.34;
      this.currentOpacity = 0.34;
      this.targetScale = 1;
      this.currentScale = 1;
      this.rafId = 0;
      this.lastFrameAt = 0;
      this.lastDustAt = 0;
      this.dustReady = false;
      this.particles = [];
      this.idleHandle = 0;
      this.destroyed = false;

      this.onPointerMove = this.onPointerMove.bind(this);
      this.onPointerEnter = this.onPointerEnter.bind(this);
      this.onPointerLeave = this.onPointerLeave.bind(this);
      this.onButtonEnter = this.onButtonEnter.bind(this);
      this.onButtonLeave = this.onButtonLeave.bind(this);
      this.onVisibilityChange = this.onVisibilityChange.bind(this);
      this.onResize = this.onResize.bind(this);
      this.tick = this.tick.bind(this);

      this.init();
    }

    init() {
      if (!this.scene || !this.layer || !this.spotlight) return;
      this.layer.style.setProperty('--grw-lml-intensity', this.intensity.toFixed(3));
      this.root.dataset.livingMuseumReady = 'true';
      this.root.dataset.livingLightMode = this.reducedMotion || this.coarsePointer ? 'static' : 'interactive';

      if ('ResizeObserver' in window) {
        this.resizeObserver = new ResizeObserver(this.onResize);
        this.resizeObserver.observe(this.scene);
      } else {
        window.addEventListener('resize', this.onResize, { passive: true });
      }

      if ('IntersectionObserver' in window) {
        this.intersectionObserver = new IntersectionObserver(
          (entries) => {
            const entry = entries[entries.length - 1];
            this.visible = Boolean(entry?.isIntersecting);
            this.updateLoop();
          },
          { rootMargin: '120px 0px', threshold: 0.01 },
        );
        this.intersectionObserver.observe(this.root);
      }

      document.addEventListener('visibilitychange', this.onVisibilityChange, { passive: true });
      this.onResize();

      if (this.allowTracking) {
        this.scene.addEventListener('pointermove', this.onPointerMove, { passive: true });
        this.scene.addEventListener('pointerenter', this.onPointerEnter, { passive: true });
        this.scene.addEventListener('pointerleave', this.onPointerLeave, { passive: true });
        this.drawButton?.addEventListener('pointerenter', this.onButtonEnter, { passive: true });
        this.drawButton?.addEventListener('pointerleave', this.onButtonLeave, { passive: true });
      }

      if (this.allowDust) {
        const startDust = () => {
          this.idleHandle = 0;
          if (this.destroyed) return;
          this.dustReady = true;
          this.resizeDust();
          this.updateLoop();
        };
        if ('requestIdleCallback' in window) {
          this.idleHandle = window.requestIdleCallback(startDust, { timeout: 450 });
        } else {
          this.idleHandle = window.setTimeout(startDust, 80);
        }
      }

      this.setState('idle');
      if (this.reducedMotion || this.coarsePointer || !this.lightEnabled) {
        this.currentOpacity = this.targetOpacity;
        this.currentScale = this.targetScale;
        this.renderLight();
      }
    }

    onResize() {
      if (!this.scene) return;
      this.sceneRect = this.scene.getBoundingClientRect();
      this.width = Math.max(1, this.sceneRect.width);
      this.height = Math.max(1, this.sceneRect.height);
      this.dpr = Math.min(window.devicePixelRatio || 1, DPR_CAP);
      this.spotlightWidth = this.spotlight?.offsetWidth || 760;
      this.spotlightHeight = this.spotlight?.offsetHeight || 420;
      if (!this.currentX && !this.currentY) {
        this.targetX = this.currentX = this.width * 0.5;
        this.targetY = this.currentY = this.height * 0.42;
      }
      this.buttonRect = null;
      this.resultRect = null;
      if (this.dustReady) this.resizeDust();
      this.renderLight();
    }

    resizeDust() {
      if (!this.dustCanvas || !this.dustContext || !this.dustReady) return;
      const pixelWidth = Math.max(1, Math.round(this.width * this.dpr));
      const pixelHeight = Math.max(1, Math.round(this.height * this.dpr));
      if (this.dustCanvas.width !== pixelWidth || this.dustCanvas.height !== pixelHeight) {
        this.dustCanvas.width = pixelWidth;
        this.dustCanvas.height = pixelHeight;
        this.dustCanvas.style.width = `${this.width}px`;
        this.dustCanvas.style.height = `${this.height}px`;
        this.dustContext.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
        this.createParticles();
      }
    }

    createParticles() {
      const area = clamp((this.width * this.height) / (1440 * 900), 0.6, 1.25);
      const count = Math.round(clamp(48 * area, 40, 70));
      this.particles = Array.from({ length: count }, (_, index) => {
        const depth = 0.24 + ((index % 3) / 2) * 0.66;
        return {
          x: Math.random() * this.width,
          y: Math.random() * this.height,
          depth,
          radius: 0.38 + Math.random() * 1.05,
          rise: 1 + Math.random() * 3.1,
          drift: 1.2 + Math.random() * 3.2,
          phase: Math.random() * Math.PI * 2,
          alpha: 0.018 + Math.random() * 0.05,
        };
      });
    }

    onPointerMove(event) {
      if (!this.sceneRect) return;
      this.pointerInside = true;
      this.targetX = clamp(event.clientX - this.sceneRect.left, 0, this.width);
      this.targetY = clamp(event.clientY - this.sceneRect.top, 0, this.height);
      this.updateLoop();
    }

    onPointerEnter() {
      this.pointerInside = true;
      this.sceneRect = this.scene.getBoundingClientRect();
      this.updateLoop();
    }

    onPointerLeave() {
      this.pointerInside = false;
      this.buttonHover = false;
      this.targetX = this.width * 0.5;
      this.targetY = this.height * 0.42;
      this.updateLoop();
    }

    onButtonEnter() {
      this.buttonHover = true;
      this.buttonRect = this.drawButton?.getBoundingClientRect() || null;
      this.updateLoop();
    }

    onButtonLeave() {
      this.buttonHover = false;
      this.updateLoop();
    }

    onVisibilityChange() {
      this.pageVisible = document.visibilityState !== 'hidden';
      this.updateLoop();
    }

    setState(state) {
      this.state = state || 'idle';
      this.root.dataset.livingLightState = this.state;
      this.resultRect = null;

      if (this.state === 'loading' || this.state === 'drawing') {
        this.targetX = this.width * 0.5;
        this.targetY = this.height * 0.5;
      } else if (this.state === 'error') {
        this.targetX = this.width * 0.5;
        this.targetY = this.height * 0.43;
      }

      if (this.state === 'result') {
        window.requestAnimationFrame(() => this.cacheResultTarget());
      }

      this.updateTargets();
      this.updateLoop();
    }

    focusResult(element) {
      this.resultElement = element || this.root.querySelector('[data-grw-result-link]');
      window.requestAnimationFrame(() => this.cacheResultTarget());
    }

    cacheResultTarget() {
      if (this.destroyed || this.state !== 'result') return;
      const element = this.resultElement || this.root.querySelector('[data-grw-result-link]');
      const rect = element?.getBoundingClientRect();
      if (!rect || !this.sceneRect) return;
      this.resultRect = rect;
      this.targetX = clamp(rect.left - this.sceneRect.left + rect.width * 0.5, 0, this.width);
      this.targetY = clamp(rect.top - this.sceneRect.top + rect.height * 0.28, 0, this.height);
      this.updateLoop();
    }

    updateTargets() {
      const base = this.intensity;
      if (!this.lightEnabled) {
        this.targetOpacity = 0;
        this.targetScale = 1;
        return;
      }

      switch (this.state) {
        case 'loading':
          this.targetOpacity = base * 0.58;
          this.targetScale = 0.88;
          break;
        case 'drawing':
          this.targetOpacity = 0;
          this.targetScale = 0.78;
          break;
        case 'result':
          this.targetOpacity = base * 0.82;
          this.targetScale = 0.72;
          break;
        case 'error':
          this.targetOpacity = base * 0.22;
          this.targetScale = 0.92;
          break;
        default:
          this.targetOpacity = base * (this.buttonHover ? 0.62 : 0.54);
          this.targetScale = this.buttonHover ? 1.02 : 1;
      }
    }

    effectiveTarget() {
      let x = this.targetX;
      let y = this.targetY;
      if (this.state === 'idle' && this.buttonHover && this.buttonRect && this.sceneRect) {
        const buttonX = this.buttonRect.left - this.sceneRect.left + this.buttonRect.width * 0.5;
        const buttonY = this.buttonRect.top - this.sceneRect.top + this.buttonRect.height * 0.5;
        x += (buttonX - x) * 0.11;
        y += (buttonY - y) * 0.11;
      }
      return { x, y };
    }

    shouldAnimateDust() {
      return (
        this.allowDust &&
        this.dustReady &&
        this.visible &&
        this.pageVisible &&
        this.state !== 'drawing'
      );
    }

    updateLoop() {
      const shouldRun = this.visible && this.pageVisible && !this.reducedMotion;
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
      if (this.destroyed || !this.visible || !this.pageVisible) return;

      const deltaMs = clamp(now - this.lastFrameAt, 0, 50);
      this.lastFrameAt = now;
      this.updateTargets();
      const target = this.effectiveTarget();
      const motionEase = 1 - Math.pow(0.002, deltaMs / 1000);
      const opacityEase = 1 - Math.pow(0.01, deltaMs / 1000);

      this.currentX += (target.x - this.currentX) * motionEase;
      this.currentY += (target.y - this.currentY) * motionEase;
      this.currentOpacity += (this.targetOpacity - this.currentOpacity) * opacityEase;
      this.currentScale += (this.targetScale - this.currentScale) * opacityEase;
      this.renderLight();
      this.renderParallax();

      if (this.shouldAnimateDust() && now - this.lastDustAt >= DUST_FRAME_MS) {
        this.drawDust(now, Math.max(DUST_FRAME_MS, now - this.lastDustAt));
        this.lastDustAt = now;
      } else if (!this.shouldAnimateDust() && this.dustContext) {
        this.dustContext.clearRect(0, 0, this.width, this.height);
      }

      const motionPending =
        Math.abs(target.x - this.currentX) > 0.2 ||
        Math.abs(target.y - this.currentY) > 0.2 ||
        Math.abs(this.targetOpacity - this.currentOpacity) > 0.002 ||
        Math.abs(this.targetScale - this.currentScale) > 0.002;

      if (motionPending || this.shouldAnimateDust()) {
        this.rafId = window.requestAnimationFrame(this.tick);
      }
    }

    renderLight() {
      if (!this.spotlight) return;
      const x = this.currentX - this.spotlightWidth * 0.5;
      const y = this.currentY - this.spotlightHeight * 0.48;
      this.spotlight.style.transform =
        `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) rotate(-7deg) scale(${this.currentScale.toFixed(4)})`;
      this.spotlight.style.opacity = clamp(this.currentOpacity, 0, 0.55).toFixed(4);
      this.layer?.style.setProperty('--grw-lml-x', `${this.currentX.toFixed(2)}px`);
      this.layer?.style.setProperty('--grw-lml-y', `${this.currentY.toFixed(2)}px`);
    }

    renderParallax() {
      if (!this.backgroundLayers || !this.sceneRect || this.state === 'drawing') return;
      const nx = clamp((this.currentX / this.width) * 2 - 1, -1, 1);
      const ny = clamp((this.currentY / this.height) * 2 - 1, -1, 1);
      this.backgroundLayers.style.setProperty('--grw-cbg-px', `${(-nx * 18).toFixed(2)}px`);
      this.backgroundLayers.style.setProperty('--grw-cbg-py', `${(-ny * 11).toFixed(2)}px`);
    }

    dustStateGain() {
      if (this.state === 'loading') return 1.16;
      if (this.state === 'result') return 0.22;
      if (this.state === 'error') return 0.15;
      return 1;
    }

    drawDust(now, deltaMs) {
      if (!this.dustContext || !this.particles.length) return;
      const ctx = this.dustContext;
      const deltaSeconds = Math.min(0.08, deltaMs / 1000);
      const radiusX = Math.max(280, this.width * 0.34);
      const radiusY = Math.max(180, this.height * 0.28);
      const stateGain = this.dustStateGain();

      ctx.clearRect(0, 0, this.width, this.height);
      for (const particle of this.particles) {
        const speedGain = 0.55 + particle.depth * 0.65;
        particle.y -= particle.rise * speedGain * deltaSeconds;
        particle.x += Math.sin(now * 0.00016 + particle.phase) * particle.drift * deltaSeconds;

        if (particle.y < -8) {
          particle.y = this.height + 8;
          particle.x = Math.random() * this.width;
        }
        if (particle.x < -8) particle.x = this.width + 8;
        if (particle.x > this.width + 8) particle.x = -8;

        const dx = (particle.x - this.currentX) / radiusX;
        const dy = (particle.y - this.currentY) / radiusY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        const lightCatch = clamp(1 - distance, 0, 1);
        const alpha = particle.alpha * stateGain * (0.06 + Math.pow(lightCatch, 2.2) * 1.12) * (0.65 + particle.depth * 0.45);
        if (alpha < 0.002) continue;

        ctx.beginPath();
        ctx.fillStyle = `rgba(255, 247, 225, ${alpha.toFixed(4)})`;
        ctx.arc(particle.x, particle.y, particle.radius * (0.74 + particle.depth * 0.42), 0, Math.PI * 2);
        ctx.fill();
      }
    }

    status() {
      return {
        state: this.state,
        lightEnabled: this.lightEnabled,
        dustEnabled: this.dustEnabled,
        allowTracking: this.allowTracking,
        allowDust: this.allowDust,
        particleCount: this.particles.length,
        visible: this.visible,
        dpr: this.dpr,
      };
    }

    destroy() {
      if (this.destroyed) return;
      this.destroyed = true;
      if (this.rafId) window.cancelAnimationFrame(this.rafId);
      if (this.idleHandle) {
        if ('cancelIdleCallback' in window) window.cancelIdleCallback(this.idleHandle);
        else window.clearTimeout(this.idleHandle);
      }
      this.resizeObserver?.disconnect();
      this.intersectionObserver?.disconnect();
      window.removeEventListener('resize', this.onResize);
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
      this.scene?.removeEventListener('pointermove', this.onPointerMove);
      this.scene?.removeEventListener('pointerenter', this.onPointerEnter);
      this.scene?.removeEventListener('pointerleave', this.onPointerLeave);
      this.drawButton?.removeEventListener('pointerenter', this.onButtonEnter);
      this.drawButton?.removeEventListener('pointerleave', this.onButtonLeave);
      if (this.dustContext) this.dustContext.clearRect(0, 0, this.width, this.height);
      if (this.dustCanvas) {
        this.dustCanvas.width = 0;
        this.dustCanvas.height = 0;
      }
      this.particles = [];
      this.dustContext = null;
      this.dustCanvas = null;
      this.resultElement = null;
      this.root.removeAttribute('data-living-museum-ready');
    }
  }

  const controllers = new Set();
  window.GICLEE_LIVING_MUSEUM_LIGHT = {
    create(root) {
      const controller = new LivingMuseumLightController(root);
      controllers.add(controller);
      const destroy = controller.destroy.bind(controller);
      controller.destroy = () => {
        destroy();
        controllers.delete(controller);
      };
      return controller;
    },
    status() {
      return Array.from(controllers, (controller) => controller.status());
    },
  };
})();
