/* Filozofia / Wrota — flat parallax Bottom+Middle (Pedzel_Alchemy #7). */
(function () {
  'use strict';

  if (window.GicleeFmWrotaParallax) return;

  var MAX_SHIFT_X = 36;
  var MAX_SHIFT_Y = 24;
  var LAYERS = [
    { key: 'bottom', depth: 1, blend: false, offsetY: '0%' },
    { key: 'middle', depth: 0.4, blend: true, offsetY: '0%' },
  ];

  function readAssets() {
    var el = document.getElementById('giclee-fm-wrota-parallax-assets');
    if (!el) return null;
    try {
      var data = JSON.parse(el.textContent || '{}');
      if (data && data.bottom && data.middle) return data;
    } catch (_error) {}
    return null;
  }

  function resolveMiddleKind(assets) {
    if (!assets || !assets.config) {
      return Promise.resolve('image');
    }
    return fetch(assets.config, { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) return { middleKind: 'image' };
        return response.json();
      })
      .then(function (cfg) {
        return cfg && cfg.middleKind === 'webm' ? 'webm' : 'image';
      })
      .catch(function () {
        return 'image';
      });
  }

  function markLoaded(root, counter) {
    counter.loaded += 1;
    if (counter.loaded >= LAYERS.length) root.classList.add('is-ready');
  }

  function createImageMedia(url, root, counter) {
    var img = document.createElement('img');
    img.alt = '';
    img.draggable = false;
    img.decoding = 'async';
    img.src = url;
    img.addEventListener('load', function () {
      markLoaded(root, counter);
    }, { once: true });
    img.addEventListener('error', function () {
      markLoaded(root, counter);
    }, { once: true });
    return img;
  }

  function createVideoMedia(url, fallbackUrl, root, counter) {
    var video = document.createElement('video');
    video.muted = true;
    video.defaultMuted = true;
    video.loop = true;
    video.autoplay = true;
    video.playsInline = true;
    video.setAttribute('muted', '');
    video.setAttribute('playsinline', '');
    video.setAttribute('webkit-playsinline', '');
    video.preload = 'auto';
    video.src = url;

    var settled = false;
    function settle() {
      if (settled) return;
      settled = true;
      markLoaded(root, counter);
    }

    video.addEventListener(
      'loadeddata',
      function () {
        settle();
        try {
          var playPromise = video.play();
          if (playPromise && typeof playPromise.catch === 'function') {
            playPromise.catch(function () {});
          }
        } catch (_error) {}
      },
      { once: true }
    );
    video.addEventListener(
      'error',
      function () {
        if (fallbackUrl && video.parentNode) {
          var img = document.createElement('img');
          img.alt = '';
          img.draggable = false;
          img.decoding = 'async';
          img.src = fallbackUrl;
          video.parentNode.replaceChild(img, video);
        }
        settle();
      },
      { once: true }
    );
    return video;
  }

  function buildLayers(root, assets, middleKind) {
    var counter = { loaded: 0 };
    var layerEls = [];

    LAYERS.forEach(function (meta) {
      var layer = document.createElement('div');
      layer.className = meta.blend
        ? 'giclee-fm-flat-parallax__layer giclee-fm-flat-parallax__layer--blend'
        : 'giclee-fm-flat-parallax__layer';
      layer.style.transform = 'translate(0, ' + meta.offsetY + ')';

      var media;
      if (
        meta.key === 'middle' &&
        middleKind === 'webm' &&
        assets.middleWebm
      ) {
        media = createVideoMedia(assets.middleWebm, assets.middle, root, counter);
      } else {
        media = createImageMedia(assets[meta.key], root, counter);
      }

      layer.appendChild(media);
      root.appendChild(layer);
      layerEls.push({ el: layer, meta: meta });
    });

    return layerEls;
  }

  function mount(host, options) {
    if (!(host instanceof HTMLElement)) return null;
    var existing = host.querySelector('.giclee-fm-flat-parallax');
    if (existing) return existing.__gicleeFmParallax || null;

    var assets = (options && options.assets) || readAssets();
    if (!assets || !assets.bottom || !assets.middle) return null;

    var reducedMotion = !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
    var ease = reducedMotion ? 1 : 0.08;

    var root = document.createElement('div');
    root.className = 'giclee-fm-flat-parallax';
    root.setAttribute('aria-hidden', 'true');
    host.appendChild(root);

    var layerEls = [];
    var targetX = 0;
    var targetY = 0;
    var currentX = 0;
    var currentY = 0;
    var raf = 0;
    var reveal = 0;
    var listening = false;
    var middleSlide = 0; // 0 = poniżej kadru, 1 = na miejscu

    function applyLayers() {
      for (var i = 0; i < layerEls.length; i++) {
        var item = layerEls[i];
        var x = currentX * item.meta.depth * -MAX_SHIFT_X;
        var y = currentY * item.meta.depth * -MAX_SHIFT_Y;
        var slideExtra = '';
        if (item.meta.key === 'middle') {
          var slidePct = ((1 - middleSlide) * 108).toFixed(2);
          slideExtra = ' translateY(' + slidePct + '%)';
        }
        item.el.style.transform =
          'translate(' +
          x.toFixed(2) +
          'px, calc(' +
          y.toFixed(2) +
          'px + ' +
          item.meta.offsetY +
          '))' +
          slideExtra;
      }
    }

    function frame() {
      raf = 0;
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;
      applyLayers();
      if (
        Math.abs(targetX - currentX) > 0.0008 ||
        Math.abs(targetY - currentY) > 0.0008
      ) {
        raf = window.requestAnimationFrame(frame);
      }
    }

    function requestFrame() {
      if (!raf) raf = window.requestAnimationFrame(frame);
    }

    function onPointerMove(e) {
      if (reveal < 0.02) return;
      var w = window.innerWidth || 1;
      var h = window.innerHeight || 1;
      targetX = (e.clientX / w - 0.5) * 2;
      targetY = (e.clientY / h - 0.5) * 2;
      requestFrame();
    }

    function onPointerLeave() {
      targetX = 0;
      targetY = 0;
      requestFrame();
    }

    function setListening(on) {
      if (on === listening) return;
      listening = on;
      if (on) {
        window.addEventListener('pointermove', onPointerMove, { passive: true });
        window.addEventListener('pointerleave', onPointerLeave);
      } else {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerleave', onPointerLeave);
        targetX = 0;
        targetY = 0;
        requestFrame();
      }
    }

    var api = {
      root: root,
      setReveal: function (value) {
        reveal = Math.max(0, Math.min(1, Number(value) || 0));
        root.style.opacity = reveal.toFixed(4);
        root.classList.toggle('is-active', reveal > 0.02);
        setListening(reveal > 0.02 && !reducedMotion);
        if (reveal > 0.02) {
          var videos = root.querySelectorAll('video');
          for (var i = 0; i < videos.length; i++) {
            try {
              var playPromise = videos[i].play();
              if (playPromise && typeof playPromise.catch === 'function') {
                playPromise.catch(function () {});
              }
            } catch (_error) {}
          }
        }
        return reveal;
      },
      setMiddleSlide: function (value) {
        middleSlide = Math.max(0, Math.min(1, Number(value) || 0));
        root.style.setProperty('--fm-middle-slide', middleSlide.toFixed(4));
        applyLayers();
        return middleSlide;
      },
      destroy: function () {
        setListening(false);
        if (raf) window.cancelAnimationFrame(raf);
        raf = 0;
        if (root.parentNode) root.parentNode.removeChild(root);
        delete root.__gicleeFmParallax;
      },
    };

    root.__gicleeFmParallax = api;
    api.setReveal(0);
    api.setMiddleSlide(0);

    resolveMiddleKind(assets).then(function (middleKind) {
      layerEls = buildLayers(root, assets, middleKind);
      applyLayers();
    });

    return api;
  }

  window.GicleeFmWrotaParallax = {
    mount: mount,
    readAssets: readAssets,
  };
})();
