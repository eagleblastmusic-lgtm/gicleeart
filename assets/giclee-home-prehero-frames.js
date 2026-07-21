/* Predictive WebP frame-sequence renderer for the pre-Hero scroll scene. */
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
    var maxCache = clamp(Number(config.cacheSize) || 36, 12, 72);
    var maxBlobCache = clamp(Number(config.blobCacheSize) || maxCache * 2, maxCache, 160);
    var preloadRadius = clamp(Number(config.preloadRadius) || 12, 4, 32);
    var maxConcurrentLoads = clamp(Number(config.maxConcurrentLoads) || 3, 2, 6);
    var maxDpr = clamp(Number(config.maxDpr) || 1.5, 1, 2);
    var sourceWidthHint = Math.max(1, Number(config.sourceWidth) || 1920);
    var sourceHeightHint = Math.max(1, Number(config.sourceHeight) || 1080);
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

    context.imageSmoothingEnabled = true;
    if ('imageSmoothingQuality' in context) context.imageSmoothingQuality = 'high';

    var bitmapCache = new Map();
    var blobCache = new Map();
    var tasks = new Map();
    var highQueue = [];
    var lowQueue = [];
    var desiredFrames = new Map();
    var activeTasks = new Map();
    var targetFrame = -1;
    var renderedFrame = -1;
    var previousTarget = 0;
    var direction = 1;
    var generation = 0;
    var pumpScheduled = false;
    var drawHandle = 0;
    var activeLoads = 0;
    var lastUsedCounter = 0;
    var currentDpr = 0;
    var drawCount = 0;
    var exactDrawCount = 0;
    var fallbackDrawCount = 0;
    var loadCount = 0;
    var decodeCount = 0;
    var errorCount = 0;
    var abortedLoadCount = 0;
    var staleCompletionCount = 0;
    var bitmapEvictionCount = 0;
    var blobEvictionCount = 0;
    var coalescedSetCount = 0;
    var redundantSetCount = 0;
    var resizeCount = 0;
    var maxFrameLag = 0;

    parts.root.setAttribute('data-render-mode', 'webp-frames');
    parts.root.setAttribute('data-frame-sequence-ready', 'false');
    parts.root.setAttribute('data-frame-count', String(frameCount));

    function now() {
      return window.performance && typeof window.performance.now === 'function'
        ? window.performance.now()
        : Date.now();
    }

    function nextUse() {
      lastUsedCounter += 1;
      return lastUsedCounter;
    }

    function sourceWidth(source) {
      return source.naturalWidth || source.videoWidth || source.width || sourceWidthHint || 1;
    }

    function sourceHeight(source) {
      return source.naturalHeight || source.videoHeight || source.height || sourceHeightHint || 1;
    }

    function releaseSource(source) {
      if (source && typeof source.close === 'function') {
        try { source.close(); } catch (error) {}
      }
    }

    function touchBitmap(index) {
      var entry = bitmapCache.get(index);
      if (entry) entry.lastUsed = nextUse();
    }

    function touchBlob(index) {
      var entry = blobCache.get(index);
      if (entry) entry.lastUsed = nextUse();
    }

    function usefulDpr(width, height) {
      var deviceDpr = Math.max(1, Number(window.devicePixelRatio) || 1);
      var sourceLimit = Math.max(
        1,
        Math.min(sourceWidthHint / Math.max(1, width), sourceHeightHint / Math.max(1, height))
      );
      return Math.min(deviceDpr, maxDpr, sourceLimit);
    }

    function closeBitmapCache() {
      bitmapCache.forEach(function (entry) { releaseSource(entry.source); });
      bitmapCache.clear();
    }

    function resize() {
      var width = Math.max(1, parts.stage.clientWidth || window.innerWidth || 1);
      var height = Math.max(1, parts.stage.clientHeight || window.innerHeight || 1);
      var dpr = usefulDpr(width, height);
      var nextWidth = Math.max(1, Math.round(width * dpr));
      var nextHeight = Math.max(1, Math.round(height * dpr));
      if (canvas.width === nextWidth && canvas.height === nextHeight) {
        currentDpr = dpr;
        return false;
      }

      canvas.width = nextWidth;
      canvas.height = nextHeight;
      currentDpr = dpr;
      resizeCount += 1;
      closeBitmapCache();
      renderedFrame = -1;
      generation += 1;
      rebuildDesiredFrames();
      schedulePump();
      scheduleDraw();
      return true;
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

    function publishRenderedFrame(index, source, exact) {
      if (!source) return;
      if (renderedFrame === index) {
        touchBitmap(index);
        return;
      }
      drawCover(source);
      renderedFrame = index;
      drawCount += 1;
      if (exact) exactDrawCount += 1;
      else fallbackDrawCount += 1;
      parts.root.setAttribute('data-frame-sequence-ready', 'true');
      parts.root.setAttribute('data-video-ready', 'true');
      parts.root.setAttribute('data-rendered-frame', String(index));
    }

    function monotonicFallback(index) {
      if (!bitmapCache.size) return -1;
      var candidate = -1;

      if (renderedFrame < 0) {
        var initialDistance = Infinity;
        bitmapCache.forEach(function (_entry, cachedIndex) {
          var distance = Math.abs(index - cachedIndex);
          if (distance < initialDistance) {
            initialDistance = distance;
            candidate = cachedIndex;
          }
        });
        return candidate;
      }

      if (index > renderedFrame) {
        bitmapCache.forEach(function (_entry, cachedIndex) {
          if (cachedIndex > renderedFrame && cachedIndex <= index) {
            if (candidate < 0 || cachedIndex > candidate) candidate = cachedIndex;
          }
        });
      } else if (index < renderedFrame) {
        bitmapCache.forEach(function (_entry, cachedIndex) {
          if (cachedIndex < renderedFrame && cachedIndex >= index) {
            if (candidate < 0 || cachedIndex < candidate) candidate = cachedIndex;
          }
        });
      }

      if (candidate >= 0) return candidate;

      var currentDistance = Math.abs(index - renderedFrame);
      var bestDistance = currentDistance;
      bitmapCache.forEach(function (_entry, cachedIndex) {
        var distance = Math.abs(index - cachedIndex);
        if (distance < bestDistance) {
          bestDistance = distance;
          candidate = cachedIndex;
        }
      });
      return candidate;
    }

    function drawTarget() {
      drawHandle = 0;
      if (targetFrame < 0) return;
      if (renderedFrame >= 0) {
        maxFrameLag = Math.max(maxFrameLag, Math.abs(targetFrame - renderedFrame));
      }

      var exact = bitmapCache.get(targetFrame);
      if (exact) {
        touchBitmap(targetFrame);
        publishRenderedFrame(targetFrame, exact.source, true);
        return;
      }

      var fallback = monotonicFallback(targetFrame);
      if (fallback >= 0 && fallback !== renderedFrame) {
        var fallbackEntry = bitmapCache.get(fallback);
        if (fallbackEntry) {
          touchBitmap(fallback);
          publishRenderedFrame(fallback, fallbackEntry.source, false);
        }
      }
      requestFrame(targetFrame, 'target');
    }

    function scheduleDraw() {
      if (drawHandle) {
        coalescedSetCount += 1;
        return;
      }
      drawHandle = window.requestAnimationFrame(drawTarget);
    }

    function cropForCanvas(width, height) {
      var targetAspect = canvas.width / Math.max(1, canvas.height);
      var sourceAspect = width / Math.max(1, height);
      if (sourceAspect > targetAspect) {
        var cropWidth = height * targetAspect;
        return { x: (width - cropWidth) * 0.5, y: 0, width: cropWidth, height: height };
      }
      var cropHeight = width / targetAspect;
      return { x: 0, y: (height - cropHeight) * 0.5, width: width, height: cropHeight };
    }

    function loadImageFallback(url) {
      return new Promise(function (resolve, reject) {
        var image = new Image();
        image.decoding = 'async';
        image.loading = 'eager';
        image.onload = function () { resolve(image); };
        image.onerror = function () { reject(new Error('Unable to decode pre-Hero frame')); };
        image.src = url;
      });
    }

    function decodeBlob(blob, url) {
      if (typeof window.createImageBitmap !== 'function') return loadImageFallback(url);

      return window.createImageBitmap(blob).then(function (full) {
        decodeCount += 1;
        var fullWidth = sourceWidth(full);
        var fullHeight = sourceHeight(full);
        if (fullWidth > 1 && fullHeight > 1) {
          sourceWidthHint = fullWidth;
          sourceHeightHint = fullHeight;
        }
        var crop = cropForCanvas(fullWidth, fullHeight);
        return window.createImageBitmap(
          full,
          crop.x,
          crop.y,
          crop.width,
          crop.height,
          {
            resizeWidth: canvas.width,
            resizeHeight: canvas.height,
            resizeQuality: 'high',
          }
        ).then(function (resized) {
          releaseSource(full);
          return resized;
        }).catch(function () {
          return full;
        });
      }).catch(function () {
        return loadImageFallback(url);
      });
    }

    function fetchBlob(index, signal) {
      var cached = blobCache.get(index);
      if (cached) {
        touchBlob(index);
        return Promise.resolve(cached.blob);
      }
      if (typeof window.fetch !== 'function') return Promise.resolve(null);
      return window.fetch(urls[index], {
        signal: signal,
        cache: 'force-cache',
        credentials: 'same-origin',
      }).then(function (response) {
        if (!response || !response.ok) throw new Error('Unable to fetch pre-Hero frame ' + index);
        return response.blob();
      }).then(function (blob) {
        blobCache.set(index, { blob: blob, lastUsed: nextUse() });
        evictBlobs();
        return blob;
      });
    }

    function decodeFrame(index, signal) {
      return fetchBlob(index, signal).then(function (blob) {
        if (signal && signal.aborted) throw new Error('aborted');
        if (!blob) return loadImageFallback(urls[index]);
        return decodeBlob(blob, urls[index]);
      });
    }

    function protectedIndex(index) {
      return index === targetFrame || index === renderedFrame || desiredFrames.has(index);
    }

    function evictBitmaps() {
      if (bitmapCache.size <= maxCache) return;
      var candidates = [];
      bitmapCache.forEach(function (entry, index) {
        if (!protectedIndex(index)) candidates.push({ index: index, lastUsed: entry.lastUsed });
      });
      candidates.sort(function (a, b) { return a.lastUsed - b.lastUsed; });
      while (bitmapCache.size > maxCache && candidates.length) {
        var candidate = candidates.shift();
        var entry = bitmapCache.get(candidate.index);
        bitmapCache.delete(candidate.index);
        if (entry) releaseSource(entry.source);
        bitmapEvictionCount += 1;
      }
    }

    function evictBlobs() {
      if (blobCache.size <= maxBlobCache) return;
      var candidates = [];
      blobCache.forEach(function (entry, index) {
        if (!protectedIndex(index) && !activeTasks.has(index)) {
          candidates.push({ index: index, lastUsed: entry.lastUsed });
        }
      });
      candidates.sort(function (a, b) { return a.lastUsed - b.lastUsed; });
      while (blobCache.size > maxBlobCache && candidates.length) {
        blobCache.delete(candidates.shift().index);
        blobEvictionCount += 1;
      }
    }

    function removeQueuedTask(task) {
      if (tasks.get(task.index) === task) tasks.delete(task.index);
      task.cancelled = true;
    }

    function takeTask(queue) {
      while (queue.length) {
        var task = queue.shift();
        if (!task.cancelled && tasks.get(task.index) === task && !task.active) return task;
      }
      return null;
    }

    function nextTask() {
      var high = takeTask(highQueue);
      if (high) return high;
      if (lowQueue.length > 1) {
        lowQueue.sort(function (a, b) {
          return Math.abs(a.index - targetFrame) - Math.abs(b.index - targetFrame);
        });
      }
      return takeTask(lowQueue);
    }

    function schedulePump() {
      if (pumpScheduled) return;
      pumpScheduled = true;
      Promise.resolve().then(function () {
        pumpScheduled = false;
        pump();
      });
    }

    function finishTask(task) {
      if (task.finished) return;
      task.finished = true;
      activeTasks.delete(task.index);
      if (tasks.get(task.index) === task) tasks.delete(task.index);
      activeLoads = Math.max(0, activeLoads - 1);
      schedulePump();
    }

    function startTask(task) {
      task.active = true;
      task.startedAt = now();
      task.controller = typeof window.AbortController === 'function'
        ? new window.AbortController()
        : null;
      activeLoads += 1;
      activeTasks.set(task.index, task);
      var signal = task.controller ? task.controller.signal : null;

      decodeFrame(task.index, signal).then(function (source) {
        if (task.cancelled || (signal && signal.aborted)) {
          releaseSource(source);
          staleCompletionCount += 1;
          return;
        }
        loadCount += 1;
        bitmapCache.set(task.index, { source: source, lastUsed: nextUse() });
        evictBitmaps();
        if (task.index === targetFrame) scheduleDraw();
      }).catch(function (error) {
        if (signal && signal.aborted) return;
        errorCount += 1;
        if (task.index === 0) parts.root.setAttribute('data-frame-sequence-error', 'true');
      }).then(function () {
        finishTask(task);
      });
    }

    function abortTask(task) {
      if (!task || task.finished || task.cancelled) return;
      task.cancelled = true;
      if (task.controller && typeof task.controller.abort === 'function') {
        abortedLoadCount += 1;
        task.controller.abort();
      }
      if (!task.active) removeQueuedTask(task);
    }

    function cancelStaleWork() {
      tasks.forEach(function (task, index) {
        if (index === targetFrame || desiredFrames.has(index)) return;
        abortTask(task);
      });
    }

    function freeTargetSlot() {
      if (bitmapCache.has(targetFrame) || tasks.has(targetFrame) || activeLoads < maxConcurrentLoads) return;
      var candidate = null;
      activeTasks.forEach(function (task, index) {
        if (index === targetFrame) return;
        if (!candidate || Math.abs(index - targetFrame) > Math.abs(candidate.index - targetFrame)) {
          candidate = task;
        }
      });
      if (candidate) abortTask(candidate);
    }

    function pump() {
      freeTargetSlot();
      while (activeLoads < maxConcurrentLoads) {
        var task = nextTask();
        if (!task) break;
        if (task.priority === 'low' && activeLoads >= maxConcurrentLoads - 1) {
          lowQueue.unshift(task);
          break;
        }
        startTask(task);
      }
    }

    function requestFrame(index, priority) {
      index = clamp(Math.round(index), 0, frameCount - 1);
      if (bitmapCache.has(index)) {
        touchBitmap(index);
        return;
      }

      var existing = tasks.get(index);
      if (existing) {
        if (priority !== 'low' && existing.priority === 'low') {
          existing.priority = priority;
          highQueue.push(existing);
        }
        return;
      }

      var task = {
        index: index,
        priority: priority === 'low' ? 'low' : priority,
        generation: generation,
        active: false,
        finished: false,
        cancelled: false,
        controller: null,
      };
      tasks.set(index, task);
      if (task.priority === 'low') lowQueue.push(task);
      else highQueue.push(task);
      schedulePump();
    }

    function addDesired(index, priority) {
      if (index < 0 || index >= frameCount) return;
      var current = desiredFrames.get(index);
      if (!current || (priority !== 'low' && current === 'low')) {
        desiredFrames.set(index, priority);
      }
    }

    function rebuildDesiredFrames() {
      desiredFrames.clear();
      if (targetFrame < 0) return;

      addDesired(targetFrame, 'target');

      if (renderedFrame >= 0 && renderedFrame !== targetFrame) {
        var gap = targetFrame - renderedFrame;
        var bridgeCount = Math.min(4, Math.abs(gap));
        for (var bridge = 1; bridge <= bridgeCount; bridge += 1) {
          addDesired(
            renderedFrame + Math.round((gap * bridge) / bridgeCount),
            bridge === bridgeCount ? 'target' : 'bridge'
          );
        }
      }

      var jump = Math.abs(targetFrame - previousTarget);
      var ahead = preloadRadius + Math.min(preloadRadius, jump * 2);
      var behind = Math.max(3, Math.ceil(preloadRadius * 0.55));
      var step;
      for (step = 1; step <= ahead; step += 1) {
        addDesired(targetFrame + step * direction, 'low');
      }
      for (step = 1; step <= behind; step += 1) {
        addDesired(targetFrame - step * direction, 'low');
      }

      desiredFrames.forEach(function (priority, index) {
        requestFrame(index, priority);
      });
      cancelStaleWork();
      evictBitmaps();
      evictBlobs();
    }

    function setProgress(progress) {
      var next = Math.round(clamp(Number(progress) || 0, 0, 1) * (frameCount - 1));
      if (next === targetFrame) {
        redundantSetCount += 1;
        return;
      }

      direction = next >= targetFrame ? 1 : -1;
      previousTarget = targetFrame < 0 ? next : targetFrame;
      targetFrame = next;
      generation += 1;
      parts.root.setAttribute('data-target-frame', String(targetFrame));
      rebuildDesiredFrames();
      scheduleDraw();
    }

    function status() {
      return {
        ready: renderedFrame >= 0,
        mode: 'webp-canvas-predictive',
        frameCount: frameCount,
        targetFrame: targetFrame,
        renderedFrame: renderedFrame,
        frameLag: targetFrame >= 0 && renderedFrame >= 0
          ? Math.abs(targetFrame - renderedFrame)
          : 0,
        maxFrameLag: maxFrameLag,
        bitmapCacheSize: bitmapCache.size,
        blobCacheSize: blobCache.size,
        queuedCount: Math.max(0, tasks.size - activeTasks.size),
        pendingCount: tasks.size,
        activeLoads: activeLoads,
        maxConcurrentLoads: maxConcurrentLoads,
        maxCache: maxCache,
        maxBlobCache: maxBlobCache,
        preloadRadius: preloadRadius,
        currentDpr: currentDpr,
        sourceWidth: sourceWidthHint,
        sourceHeight: sourceHeightHint,
        drawCount: drawCount,
        exactDrawCount: exactDrawCount,
        fallbackDrawCount: fallbackDrawCount,
        loadCount: loadCount,
        decodeCount: decodeCount,
        errorCount: errorCount,
        abortedLoadCount: abortedLoadCount,
        staleCompletionCount: staleCompletionCount,
        bitmapEvictionCount: bitmapEvictionCount,
        blobEvictionCount: blobEvictionCount,
        coalescedSetCount: coalescedSetCount,
        redundantSetCount: redundantSetCount,
        resizeCount: resizeCount,
        generation: generation,
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
