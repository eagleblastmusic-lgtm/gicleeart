(() => {
  const API_KEY = 'GicleeScrollScrubVideo';
  const ROOT_SELECTOR = '.media-block--scroll-scrub';
  const VIDEO_SELECTOR = '[data-scroll-scrub-media]';
  const controllers = new Map();
  let frameRequested = false;

  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

  class ScrollScrubVideo {
    constructor(root) {
      this.root = root;
      this.video = root.querySelector(VIDEO_SELECTOR);
      this.maxDuration = Number.parseFloat(this.video?.dataset.scrollScrubDuration || '6');
      this.maxDuration = clamp(Number.isFinite(this.maxDuration) ? this.maxDuration : 6, 1, 6);
      this.targetTime = 0;
      this.objectUrl = null;
      this.abortController = new AbortController();
      this.update = this.update.bind(this);
      this.handleVideoReady = this.handleVideoReady.bind(this);

      if (!this.video) return;

      this.video.defaultMuted = true;
      this.video.muted = true;
      this.video.pause();
      this.prepareVideo();
    }

    async prepareVideo() {
      const sourceUrl = this.video.dataset.scrollScrubSrc;
      if (!sourceUrl) return;

      try {
        const response = await fetch(sourceUrl, {
          cache: 'force-cache',
          credentials: 'same-origin',
          signal: this.abortController.signal,
        });
        if (!response.ok) {
          throw new Error(`Nie udało się załadować wideo: ${response.status}`);
        }

        const blob = await response.blob();
        if (!this.root.isConnected) return;

        this.objectUrl = URL.createObjectURL(blob);
        this.video.addEventListener('loadeddata', this.handleVideoReady, { once: true });
        this.video.src = this.objectUrl;
        this.video.load();
      } catch (error) {
        if (error?.name === 'AbortError' || !this.root.isConnected) return;

        this.video.addEventListener('loadeddata', this.handleVideoReady, { once: true });
        this.video.preload = 'auto';
        this.video.src = sourceUrl;
        this.video.load();
      }
    }

    handleVideoReady() {
      this.video.pause();
      this.update();
    }

    update() {
      if (!this.video || this.video.readyState < 1) return;

      const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
      const rect = this.root.getBoundingClientRect();
      const videoHeight = Math.min(this.video.getBoundingClientRect().height || viewportHeight, viewportHeight);
      const pinnedTravel = rect.height - videoHeight;
      const centerLine = viewportHeight / 2;
      const progress = pinnedTravel > 0
        ? clamp((centerLine - rect.top) / pinnedTravel, 0, 1)
        : 0;
      const playableDuration = Math.min(this.video.duration || this.maxDuration, this.maxDuration);
      this.targetTime = progress * playableDuration;

      if (Math.abs(this.video.currentTime - this.targetTime) < 1 / 120) return;

      try {
        this.video.currentTime = this.targetTime;
      } catch (_error) {
        // Metadata may be replaced while Shopify reloads a section.
      }
    }

    destroy() {
      this.abortController.abort();
      this.video?.removeEventListener('loadeddata', this.handleVideoReady);
      if (this.objectUrl) {
        URL.revokeObjectURL(this.objectUrl);
      }
    }
  }

  const updateAll = () => {
    frameRequested = false;
    controllers.forEach((controller, root) => {
      if (!root.isConnected) {
        controller.destroy();
        controllers.delete(root);
        return;
      }
      controller.update();
    });
  };

  const requestUpdate = () => {
    if (frameRequested) return;
    frameRequested = true;
    window.requestAnimationFrame(updateAll);
  };

  const refresh = (scope = document) => {
    scope.querySelectorAll(ROOT_SELECTOR).forEach((root) => {
      if (!controllers.has(root)) {
        controllers.set(root, new ScrollScrubVideo(root));
      }
    });
    requestUpdate();
  };

  if (window[API_KEY]) {
    window[API_KEY].refresh();
    return;
  }

  window[API_KEY] = { refresh };
  window.addEventListener('scroll', requestUpdate, { passive: true });
  window.addEventListener('resize', requestUpdate, { passive: true });
  window.addEventListener('pageshow', requestUpdate);
  document.addEventListener('shopify:section:load', (event) => refresh(event.target));

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => refresh(), { once: true });
  } else {
    refresh();
  }
})();
