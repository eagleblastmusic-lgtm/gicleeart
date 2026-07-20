/* WebP frame-sequence renderer for the pre-Hero scroll scene. */
(function () {
  'use strict';

  function sequenceConfig() {
    return window.GICLEE_PREHERO_FRAME_SEQUENCE || {};
  }

  function available() {
    var config = sequenceConfig();
    return !!(
      config.enabled === true &&
      Array.isArray(config.urls) &&
      config.urls.length > 1
    );
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function create(parts) {
    if (!available() || !parts || !parts.root || !parts.stage) return null;

    var config = sequenceConfig();
    var urls = config.urls.slice();
    var frameCount = urls.length;
    var maxCache = clamp(Number(config.cacheSize) || 18, 8, 36);
    var preloadRadius = clamp(Number(config.preloadRadius) || 4, 2, 10);
    var maxDpr = clamp(Number(config.maxDpr) || 1.5, 1, 2);
    var canvas = parts.stage.querySelector('.giclee-prehero-scrub__canvas');
    if (!canvas) {
      canvas = document.createElement('canvas');
      canvas.className = 'giclee-prehero-scrub__canvas';
      canvas.setAttribute('aria-hidden', 'true');
      parts.stage.insertBefore(canvas, parts.video || null);
    }

    var context = canvas.getContext('2d', {
      alpha: false,
      desynchronized: true,
    }) || canvas.getContext('2d');
    if (!context) return null;

    var cache = new Map();
    var pending = new Map();
    var targetFrame = 0;
    var renderedFrame = -1;
    var previousTarget = 0;
    var direction = 1;
    var drawCount = 0;
    var loadCount = 0;
    var errorCount = 0;
    var evictionCount = 0;
    var idleHandle = 0;
    var resizeCount = 0;
    var lastUsedCounter = 0;

    parts.root.setAttribute('data-render-mode', 'webp-frames');
    parts.root.setAttribute('data-frame-sequence-ready', 'false');
    parts.root.setAttribute('data-frame-count', String(frameCount));

    function sourceWidth(source) {
      return source.naturalWidth || source.videoWidth || source.width || 1;
    }

    function sourceHeight(source) {
      return source.naturalHeight || source.videoHeight || source.height || 1;
    }

    function drawCover(source) {
      if (!source || !canvas.width || !canvas.height) return;
      var sw = sourceWidth(source);
      var sh = sourceHeight(source);
      var scale = Math.max(canvas.width / sw, canvas.height / sh);
      var dw = sw * scale;
      var dh = sh * scale;
      var dx = (canvas.width - dw) * 0.5;
      var dy = (canvas.height - dh) * 0.5;
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(source, dx, dy, dw, dh);
    }

    function touch(index) {
      var entry = cache.get(index);
      if (!entry) return;
      lastUsedCounter += 1;
      entry.lastUsed = lastUsedCounter;
    }

    function evict() {
      if (cache.size <= maxCache) return;
      var protectedMin = Math.max(0, targetFrame - 2);
      var protectedMax = Math.min(frameCount - 1, targetFrame + 2);
      var candidates = [];
      cache.forEach(function (entry, index) {
        if (index < protectedMin || index > protectedMax) {
          candidates.push({ index: index, lastUsed: entry.lastUsed || 0 });
        }
      });
      candidates.sort(function (a, b) { return a.lastUsed - b.lastUsed; });
      while (cache.size > maxCache && candidates.length) {
        var candidate = candidates.shift();
        cache.delete(candidate.index);
        evictionCount += 1;
      }
    }

    function loadFrame(index, priority) {
      index = clamp(Math.round(index), 0, frameCount - 1);
      if (cache.has(index)) {
        touch(index);
        return Promise.resolve(cache.get(index).source);
      }
      if (pending.has(index)) return pending.get(index);

      var promise = new Promise(function (resolve, reject) {
        var image = new Image();
        image.decoding = 'async';
        image.loading = 'eager';
        if ('fetchPriority' in image) image.fetchPriority = priority === 'high' ? 'high' : 'low';
        image.onload = function () {
          loadCount += 1;
          lastUsedCounter += 1;
          cache.set(index, { source: image, lastUsed: lastUsedCounter });
          pending.delete(index);
          evict();
          resolve(image);
        };
        image.onerror = function () {
          errorCount += 1;
          pending.delete(index);
          if (index === 0) parts.root.setAttribute('data-frame-sequence-error', 'true');
          reject(new Error('Unable to load pre-Hero frame ' + index));
        };
        image.src = urls[index];
      });
      pending.set(index, promise);
      return promise;
    }

    function drawFrame(index) {
      index = clamp(Math.round(index), 0, frameCount - 1);
      var cached = cache.get(index);
      if (cached) {
        touch(index);
        drawCover(cached.source);
        renderedFrame = index;
        drawCount += 1;
        parts.root.setAttribute('data-frame-sequence-ready', 'true');
        parts.root.setAttribute('data-video-ready', 'true');
        parts.root.setAttribute('data-rendered-frame', String(index));
        return;
      }

      loadFrame(index, 'high').then(function (source) {
        if (targetFrame !== index && renderedFrame >= 0) return;
        drawCover(source);
        renderedFrame = index;
        drawCount += 1;
        parts.root.setAttribute('data-frame-sequence-ready', 'true');
        parts.root.setAttribute('data-video-ready', 'true');
        parts.root.setAttribute('data-rendered-frame', String(index));
      }).catch(function () {});
    }

    function idleCallback(callback) {
      if (typeof window.requestIdleCallback === 'function') {
        return window.requestIdleCallback(callback, { timeout: 180 });
      }
      return window.setTimeout(callback, 16);
    }

    function cancelIdle(handle) {
      if (!handle) return;
      if (typeof window.cancelIdleCallback === 'function') window.cancelIdleCallback(handle);
      else window.clearTimeout(handle);
    }

    function prefetch() {
      cancelIdle(idleHandle);
      idleHandle = idleCallback(function () {
        idleHandle = 0;
        var order = [];
        for (var step = 1; step <= preloadRadius; step += 1) {
          order.push(targetFrame + step * direction);
          order.push(targetFrame - step * direction);
        }
        order.forEach(function (index) {
          if (index < 0 || index >= frameCount || cache.has(index) || pending.has(index)) return;
          loadFrame(index, 'low').catch(function () {});
        });
      });
    }

    function resize() {
      var width = Math.max(1, parts.stage.clientWidth || window.innerWidth || 1);
      var height = Math.max(1, parts.stage.clientHeight || window.innerHeight || 1);
      var dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
      var nextWidth = Math.round(width * dpr);
      var nextHeight = Math.round(height * dpr);
      if (canvas.width === nextWidth && canvas.height === nextHeight) return;
      canvas.width = nextWidth;
      canvas.height = nextHeight;
      resizeCount += 1;
      if (renderedFrame >= 0 && cache.has(renderedFrame)) {
        drawCover(cache.get(renderedFrame).source);
      }
    }

    function setProgress(progress) {
      var next = Math.round(clamp(Number(progress) || 0, 0, 1) * (frameCount - 1));
      direction = next >= previousTarget ? 1 : -1;
      previousTarget = next;
      targetFrame = next;
      parts.root.setAttribute('data-target-frame', String(targetFrame));
      drawFrame(targetFrame);
      prefetch();
    }

    function status() {
      return {
        ready: renderedFrame >= 0,
        mode: 'webp-canvas',
        frameCount: frameCount,
        targetFrame: targetFrame,
        renderedFrame: renderedFrame,
        cacheSize: cache.size,
        pendingCount: pending.size,
        maxCache: maxCache,
        preloadRadius: preloadRadius,
        drawCount: drawCount,
        loadCount: loadCount,
        errorCount: errorCount,
        evictionCount: evictionCount,
        resizeCount: resizeCount,
        canvasWidth: canvas.width,
        canvasHeight: canvas.height,
      };
    }

    resize();
    setProgress(0);
    window.GICLEE_PREHERO_FRAME_STATUS = status;

    return {
      setProgress: setProgress,
      resize: resize,
      status: status,
      frameCount: frameCount,
      duration: Number(config.duration) || 5,
    };
  }

  window.GICLEE_PREHERO_FRAME_RENDERER = {
    available: available,
    create: create,
  };
})();
