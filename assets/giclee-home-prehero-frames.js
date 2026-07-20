/* JPG sprite-sequence renderer for the pre-Hero scroll scene. */
(function () {
  'use strict';

  function sequenceConfig() {
    return window.GICLEE_PREHERO_FRAME_SEQUENCE || {};
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function available() {
    var config = sequenceConfig();
    return !!(
      config.enabled === true &&
      Array.isArray(config.urls) &&
      config.urls.length > 0 &&
      Number(config.frameCount) > 1 &&
      Number(config.framesPerSprite) > 0 &&
      Number(config.spriteColumns) > 0 &&
      Number(config.frameWidth) > 0 &&
      Number(config.frameHeight) > 0
    );
  }

  function create(parts) {
    if (!available() || !parts || !parts.root || !parts.stage) return null;

    var config = sequenceConfig();
    var urls = config.urls.slice();
    var frameCount = Math.max(2, Math.floor(Number(config.frameCount) || 2));
    var framesPerSprite = Math.max(1, Math.floor(Number(config.framesPerSprite) || 8));
    var spriteColumns = Math.max(1, Math.floor(Number(config.spriteColumns) || 4));
    var frameWidth = Math.max(1, Math.floor(Number(config.frameWidth) || 1280));
    var frameHeight = Math.max(1, Math.floor(Number(config.frameHeight) || 720));
    var maxCache = clamp(Math.floor(Number(config.cacheSize) || 2), 2, 6);
    var preloadRadius = clamp(Math.floor(Number(config.preloadRadius) || 1), 1, 2);
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
    var renderedSprite = -1;
    var previousTarget = 0;
    var direction = 1;
    var drawCount = 0;
    var loadCount = 0;
    var errorCount = 0;
    var evictionCount = 0;
    var idleHandle = 0;
    var resizeCount = 0;
    var lastUsedCounter = 0;

    /* Keep the legacy attribute value because the existing CSS scopes canvas visibility to it. */
    parts.root.setAttribute('data-render-mode', 'webp-frames');
    parts.root.setAttribute('data-frame-sequence-format', 'jpg-sprites');
    parts.root.setAttribute('data-frame-sequence-ready', 'false');
    parts.root.setAttribute('data-frame-count', String(frameCount));
    parts.root.setAttribute('data-sprite-count', String(urls.length));

    function frameLocation(index) {
      var spriteIndex = Math.floor(index / framesPerSprite);
      var localIndex = index % framesPerSprite;
      return {
        spriteIndex: spriteIndex,
        sourceX: (localIndex % spriteColumns) * frameWidth,
        sourceY: Math.floor(localIndex / spriteColumns) * frameHeight,
      };
    }

    function drawCover(source, sourceX, sourceY) {
      if (!source || !canvas.width || !canvas.height) return;
      var scale = Math.max(canvas.width / frameWidth, canvas.height / frameHeight);
      var drawWidth = frameWidth * scale;
      var drawHeight = frameHeight * scale;
      var drawX = (canvas.width - drawWidth) * 0.5;
      var drawY = (canvas.height - drawHeight) * 0.5;
      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(
        source,
        sourceX,
        sourceY,
        frameWidth,
        frameHeight,
        drawX,
        drawY,
        drawWidth,
        drawHeight
      );
    }

    function touch(spriteIndex) {
      var entry = cache.get(spriteIndex);
      if (!entry) return;
      lastUsedCounter += 1;
      entry.lastUsed = lastUsedCounter;
    }

    function evict() {
      if (cache.size <= maxCache) return;
      var targetSprite = frameLocation(targetFrame).spriteIndex;
      var candidates = [];
      cache.forEach(function (entry, spriteIndex) {
        if (Math.abs(spriteIndex - targetSprite) > 1) {
          candidates.push({ spriteIndex: spriteIndex, lastUsed: entry.lastUsed || 0 });
        }
      });
      candidates.sort(function (a, b) { return a.lastUsed - b.lastUsed; });
      while (cache.size > maxCache && candidates.length) {
        cache.delete(candidates.shift().spriteIndex);
        evictionCount += 1;
      }
    }

    function loadSprite(spriteIndex, priority) {
      spriteIndex = clamp(Math.round(spriteIndex), 0, urls.length - 1);
      if (cache.has(spriteIndex)) {
        touch(spriteIndex);
        return Promise.resolve(cache.get(spriteIndex).source);
      }
      if (pending.has(spriteIndex)) return pending.get(spriteIndex);

      var promise = new Promise(function (resolve, reject) {
        var image = new Image();
        image.decoding = 'async';
        image.loading = 'eager';
        if ('fetchPriority' in image) image.fetchPriority = priority === 'high' ? 'high' : 'low';
        image.onload = function () {
          loadCount += 1;
          lastUsedCounter += 1;
          cache.set(spriteIndex, { source: image, lastUsed: lastUsedCounter });
          pending.delete(spriteIndex);
          evict();
          resolve(image);
        };
        image.onerror = function () {
          errorCount += 1;
          pending.delete(spriteIndex);
          if (spriteIndex === 0) parts.root.setAttribute('data-frame-sequence-error', 'true');
          reject(new Error('Unable to load pre-Hero sprite ' + spriteIndex));
        };
        image.src = urls[spriteIndex];
      });
      pending.set(spriteIndex, promise);
      return promise;
    }

    function commitFrame(index, source, location) {
      drawCover(source, location.sourceX, location.sourceY);
      renderedFrame = index;
      renderedSprite = location.spriteIndex;
      drawCount += 1;
      parts.root.setAttribute('data-frame-sequence-ready', 'true');
      parts.root.setAttribute('data-video-ready', 'true');
      parts.root.setAttribute('data-rendered-frame', String(index));
      parts.root.setAttribute('data-rendered-sprite', String(location.spriteIndex));
    }

    function drawFrame(index) {
      index = clamp(Math.round(index), 0, frameCount - 1);
      var location = frameLocation(index);
      var cached = cache.get(location.spriteIndex);
      if (cached) {
        touch(location.spriteIndex);
        commitFrame(index, cached.source, location);
        return;
      }

      loadSprite(location.spriteIndex, 'high').then(function (source) {
        if (targetFrame !== index && renderedFrame >= 0) return;
        commitFrame(index, source, location);
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
        var targetSprite = frameLocation(targetFrame).spriteIndex;
        var order = [];
        for (var step = 1; step <= preloadRadius; step += 1) {
          order.push(targetSprite + step * direction);
          order.push(targetSprite - step * direction);
        }
        order.forEach(function (spriteIndex) {
          if (
            spriteIndex < 0 ||
            spriteIndex >= urls.length ||
            cache.has(spriteIndex) ||
            pending.has(spriteIndex)
          ) return;
          loadSprite(spriteIndex, 'low').catch(function () {});
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
      if (renderedFrame >= 0 && cache.has(renderedSprite)) {
        var location = frameLocation(renderedFrame);
        drawCover(cache.get(renderedSprite).source, location.sourceX, location.sourceY);
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
        mode: 'jpg-sprite-canvas',
        frameCount: frameCount,
        spriteCount: urls.length,
        framesPerSprite: framesPerSprite,
        targetFrame: targetFrame,
        renderedFrame: renderedFrame,
        renderedSprite: renderedSprite,
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
      duration: Number(config.duration) || 4.875,
    };
  }

  window.GICLEE_PREHERO_FRAME_RENDERER = {
    available: available,
    create: create,
  };
})();
