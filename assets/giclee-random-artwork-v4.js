/* Losuj Obraz V4 — staged ceremonial result reveal. */
(() => {
  'use strict';

  if (window.GICLEE_RANDOM_ARTWORK_V4) return;

  const FRAME_TO_IDENTITY_MS = 310;
  const IDENTITY_TO_ACTIONS_MS = 390;

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
  window.GICLEE_RANDOM_ARTWORK_V4 = {
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
})();
