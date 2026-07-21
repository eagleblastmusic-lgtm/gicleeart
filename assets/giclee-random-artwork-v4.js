/* Losuj Obraz V4 — staged ceremonial result reveal and V3 runtime inheritance. */
(() => {
  'use strict';

  if (window.GICLEE_RANDOM_ARTWORK_V4) return;

  const FRAME_TO_IDENTITY_MS = 310;
  const IDENTITY_TO_ACTIONS_MS = 390;
  const ROOT_SELECTOR = 'giclee-random-artwork[data-design-variant="v4"]';

  class CeremonialResultController {
    constructor(root) {
      this.root = root;
      this.result = root.querySelector('[data-grw-result]');
      this.artist = root.querySelector('[data-grw-result-artist]');
      this.year = root.querySelector('[data-grw-result-year]');
      this.reducedMotion =
        window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
      this.timers = new Set();
      this.destroyed = false;
      this.reset();
    }

    schedule(callback, delay) {
      const timer = window.setTimeout(() => {
        this.timers.delete(timer);
        if (!this.destroyed) callback();
      }, delay);
      this.timers.add(timer);
      return timer;
    }

    clearTimers() {
      for (const timer of this.timers) window.clearTimeout(timer);
      this.timers.clear();
    }

    reset() {
      this.clearTimers();
      this.root.dataset.resultStage = 'hidden';
      this.root.removeAttribute('data-result-ceremony');
    }

    reveal() {
      if (!this.result || this.destroyed) return;
      this.clearTimers();

      // Main controller populates identity before setState('result').
      if (this.artist) this.artist.hidden = !this.artist.textContent?.trim();
      if (this.year) this.year.hidden = !this.year.textContent?.trim();

      this.root.dataset.resultCeremony = 'active';
      this.root.dataset.resultStage = 'frame';

      if (this.reducedMotion) {
        this.root.dataset.resultStage = 'actions';
        this.root.dataset.resultCeremony = 'complete';
        return;
      }

      this.schedule(() => {
        this.root.dataset.resultStage = 'identity';
      }, FRAME_TO_IDENTITY_MS);

      this.schedule(() => {
        this.root.dataset.resultStage = 'actions';
        this.root.dataset.resultCeremony = 'complete';
      }, FRAME_TO_IDENTITY_MS + IDENTITY_TO_ACTIONS_MS);
    }

    setState(state) {
      if (state === 'result') {
        this.reveal();
        return;
      }
      this.reset();
    }

    status() {
      return {
        stage: this.root.dataset.resultStage || 'hidden',
        ceremony: this.root.dataset.resultCeremony || 'idle',
        pendingTimers: this.timers.size,
        reducedMotion: this.reducedMotion,
      };
    }

    destroy() {
      if (this.destroyed) return;
      this.destroyed = true;
      this.clearTimers();
      this.root.removeAttribute('data-result-stage');
      this.root.removeAttribute('data-result-ceremony');
    }
  }

  const controllers = new Set();

  const api = {
    create(root) {
      const controller = new CeremonialResultController(root);
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

  window.GICLEE_RANDOM_ARTWORK_V4 = api;

  const enhance = (root) => {
    if (!root || root.dataset.designVariant !== 'v4') return;

    if (!root.livingMuseumLight && window.GICLEE_LIVING_MUSEUM_LIGHT?.create) {
      // V4 inherits the accepted V3 light/dust implementation and removes the
      // fallback global parallax listener created by the base controller.
      root.cleanupCustomBgParallax?.();
      root.livingMuseumLight = window.GICLEE_LIVING_MUSEUM_LIGHT.create(root);
      root.livingMuseumLight.setState?.(root.dataset.state || 'idle');
    }

    if (!root.v4Finale) {
      root.v4Finale = api.create(root);
      root.v4Finale.setState(root.dataset.state || 'idle');
    }
  };

  const ElementClass = window.customElements?.get('giclee-random-artwork');
  const prototype = ElementClass?.prototype;

  if (prototype && !prototype.__grwV4FinalePatched) {
    const connected = prototype.connectedCallback;
    const disconnected = prototype.disconnectedCallback;
    const setState = prototype.setState;

    prototype.connectedCallback = function connectedCallbackV4(...args) {
      const result = connected?.apply(this, args);
      enhance(this);
      return result;
    };

    prototype.setState = function setStateV4(state, ...args) {
      const result = setState?.call(this, state, ...args);
      this.v4Finale?.setState?.(state);
      return result;
    };

    prototype.disconnectedCallback = function disconnectedCallbackV4(...args) {
      this.v4Finale?.destroy?.();
      this.v4Finale = null;
      return disconnected?.apply(this, args);
    };

    Object.defineProperty(prototype, '__grwV4FinalePatched', {
      value: true,
      configurable: false,
      enumerable: false,
      writable: false,
    });
  }

  document.querySelectorAll(ROOT_SELECTOR).forEach(enhance);
})();
