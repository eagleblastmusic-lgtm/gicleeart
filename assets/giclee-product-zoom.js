/**
 * OpenSeadragon viewer dla custom.zoom_manifest (kafelki na R2).
 * Wlasny, nowoczesny pasek kontrolek (szklany pill + liniowe ikony) zamiast
 * domyslnego, skeuomorficznego UI OpenSeadragon.
 */
(function () {
  const ZOOM_STEP = 1.45;

  const ICONS = {
    zoomIn:
      '<circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>' +
      '<line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>',
    zoomOut:
      '<circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>' +
      '<line x1="8" y1="11" x2="14" y2="11"/>',
    reset:
      '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    enterFullscreen:
      '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/>' +
      '<path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
    exitFullscreen:
      '<path d="M8 3v3a2 2 0 0 1-2 2H3"/><path d="M21 8h-3a2 2 0 0 1-2-2V3"/>' +
      '<path d="M3 16h3a2 2 0 0 1 2 2v3"/><path d="M16 21v-3a2 2 0 0 1 2-2h3"/>',
    fill:
      '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
    contain:
      '<path d="M4 14h6v6"/><path d="M20 10h-6V4"/><path d="M14 10l7-7"/><path d="M3 21l7-7"/>',
  };

  function iconSvg(name) {
    return (
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" ' +
      'aria-hidden="true" focusable="false">' +
      ICONS[name] +
      '</svg>'
    );
  }

  function initZoom(el) {
    const raw = el.getAttribute('data-giclee-zoom-manifest');
    if (!raw || typeof OpenSeadragon === 'undefined') return;

    let manifest;
    try {
      manifest = JSON.parse(raw);
    } catch (e) {
      console.warn('[giclee-zoom] invalid manifest', e);
      return;
    }

    const viewerEl = el.querySelector('.giclee-zoom-viewer');
    if (!viewerEl) return;

    const base = (manifest.baseUrl || '').replace(/\/$/, '');
    const tileSize = manifest.tileSize || 1024;
    const width = manifest.width;
    const height = manifest.height;
    const imageAspectRatio = width / height;

    const viewer = OpenSeadragon({
      element: viewerEl,
      showNavigationControl: false,
      showNavigator: false,
      maxZoomPixelRatio: 1,
      visibilityRatio: 1,
      constrainDuringPan: true,
      gestureSettingsMouse: {
        dblClickToZoom: false,
        scrollToZoom: false,
      },
      tileSources: {
        width: width,
        height: height,
        tileSize: tileSize,
        minLevel: 0,
        maxLevel: 0,
        getTileUrl: function (level, x, y) {
          return base + '/tiles/' + x + '_' + y + '.webp';
        },
      },
    });

    let fullscreenFill = false;
    let isApplyingLayout = false;

    function getProductTemplate() {
      const main = document.querySelector('main[data-template]');
      return main ? main.getAttribute('data-template') : '';
    }

    function isNowySzblonMobile() {
      const template = getProductTemplate();
      return (
        window.matchMedia('(max-width: 749px)').matches &&
        (template === 'product.nowy-szblon-produktu' ||
          template === 'product.szablon-produktu-v2' ||
          template === 'product.szablon-produktu-v3')
      );
    }

    function usesArtworkCoverDefault() {
      const template = getProductTemplate();
      if (template === 'product.szablon-wlasna-fotografia') return true;
      return isNowySzblonMobile();
    }

    function resetToArtworkWidth(immediate) {
      // Start with the full artwork width visible, even for tall vertical works.
      viewer.viewport.fitHorizontally(immediate);
      if (immediate) {
        viewer.viewport.minZoomLevel = viewer.viewport.getZoom(true);
      }
    }

    function resetToDefaultView(immediate) {
      if (isApplyingLayout) return;

      if (usesArtworkCoverDefault()) {
        isApplyingLayout = true;
        try {
          // Stala wysokosc z CSS (nie kurczymy kontenera dla obrazow poziomych).
          viewerEl.style.height = '';
          fitArtworkCover(immediate);
        } finally {
          isApplyingLayout = false;
        }
      } else {
        viewerEl.style.height = '';
        resetToArtworkWidth(immediate);
      }

      if (immediate) {
        viewer.viewport.minZoomLevel = viewer.viewport.getZoom(true);
      }
    }

    function scheduleMobileDefaultView() {
      if (!usesArtworkCoverDefault()) return;
      window.requestAnimationFrame(function () {
        resetToDefaultView(true);
        pinToolbar();
        window.setTimeout(function () {
          resetToDefaultView(true);
          pinToolbar();
        }, 150);
      });
    }

    function fitArtworkContain(immediate) {
      const tiledImage = viewer.world && viewer.world.getItemAt(0);

      viewer.viewport.minZoomLevel = 0;
      if (tiledImage && typeof tiledImage.getBounds === 'function') {
        viewer.viewport.fitBounds(tiledImage.getBounds(), immediate);
      } else {
        viewer.viewport.goHome(immediate);
      }
      if (immediate) {
        viewer.viewport.minZoomLevel = viewer.viewport.getZoom(true);
      }
    }

    function fitArtworkCover(immediate) {
      const viewerHeight = viewerEl.clientHeight;
      const viewerWidth = viewerEl.clientWidth;
      if (!viewerWidth || !viewerHeight) return;

      const viewportAspectRatio = viewerWidth / viewerHeight;
      if (imageAspectRatio > viewportAspectRatio) {
        viewer.viewport.fitVertically(immediate);
      } else {
        viewer.viewport.fitHorizontally(immediate);
      }
    }

    function fullscreenElement() {
      return (
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.msFullscreenElement ||
        null
      );
    }

    function isFullscreenMode() {
      return fullscreenElement() === viewerEl;
    }

    function toggleFullscreen() {
      if (isFullscreenMode()) {
        const exit =
          document.exitFullscreen ||
          document.webkitExitFullscreen ||
          document.msExitFullscreen;
        if (exit) exit.call(document);
        return;
      }
      const request =
        viewerEl.requestFullscreen ||
        viewerEl.webkitRequestFullscreen ||
        viewerEl.msRequestFullscreen;
      if (request) {
        request.call(viewerEl);
      }
    }

    function fitCurrentMode(immediate) {
      if (isFullscreenMode()) {
        if (fullscreenFill) {
          fitArtworkCover(immediate);
        } else {
          fitArtworkContain(immediate);
        }
      } else {
        fullscreenFill = false;
        resetToDefaultView(immediate);
      }
      updateChrome();
    }

    function scheduleFitCurrentMode() {
      window.requestAnimationFrame(function () {
        fitCurrentMode(true);
        window.setTimeout(function () {
          fitCurrentMode(true);
        }, 120);
      });
    }

    // --- Custom toolbar -----------------------------------------------------
    const toolbar = document.createElement('div');
    toolbar.className = 'gz-toolbar';
    toolbar.setAttribute('role', 'toolbar');
    toolbar.setAttribute('aria-label', 'Sterowanie powiekszeniem');

    ['pointerdown', 'mousedown', 'touchstart', 'wheel', 'dblclick'].forEach(
      function (evName) {
        toolbar.addEventListener(
          evName,
          function (event) {
            event.stopPropagation();
          },
          { passive: true }
        );
      }
    );

    const buttons = {};

    function makeButton(action, iconName, label, extraClass) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'gz-btn' + (extraClass ? ' ' + extraClass : '');
      button.dataset.action = action;
      button.title = label;
      button.setAttribute('aria-label', label);
      button.innerHTML = iconSvg(iconName);
      button.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        bumpToolbarActivity();
        handleAction(action);
      });
      buttons[action] = button;
      return button;
    }

    function handleAction(action) {
      switch (action) {
        case 'zoom-in':
          viewer.viewport.zoomBy(ZOOM_STEP);
          viewer.viewport.applyConstraints();
          break;
        case 'zoom-out':
          viewer.viewport.zoomBy(1 / ZOOM_STEP);
          viewer.viewport.applyConstraints();
          break;
        case 'reset':
          fitCurrentMode(false);
          break;
        case 'fill':
          if (!isFullscreenMode()) return;
          fullscreenFill = !fullscreenFill;
          fitCurrentMode(false);
          break;
        case 'fullscreen':
          toggleFullscreen();
          break;
        default:
          break;
      }
    }

    toolbar.appendChild(makeButton('zoom-in', 'zoomIn', 'Powieksz'));
    toolbar.appendChild(makeButton('zoom-out', 'zoomOut', 'Pomniejsz'));
    toolbar.appendChild(makeButton('reset', 'reset', 'Widok poczatkowy'));
    toolbar.appendChild(
      makeButton('fill', 'fill', 'Wypelnij ekran', 'gz-btn--fill')
    );
    toolbar.appendChild(
      makeButton('fullscreen', 'enterFullscreen', 'Pelny ekran')
    );

    viewerEl.appendChild(toolbar);

    const TOOLBAR_IDLE_MS = 2000;
    let toolbarIdleTimer = null;

    function clearToolbarIdleTimer() {
      if (toolbarIdleTimer !== null) {
        window.clearTimeout(toolbarIdleTimer);
        toolbarIdleTimer = null;
      }
    }

    function setToolbarIdle(idle) {
      toolbar.classList.toggle('gz-toolbar--idle', idle);
    }

    function bumpToolbarActivity() {
      if (!isNowySzblonMobile()) {
        clearToolbarIdleTimer();
        setToolbarIdle(false);
        return;
      }

      setToolbarIdle(false);
      clearToolbarIdleTimer();
      toolbarIdleTimer = window.setTimeout(function () {
        toolbarIdleTimer = null;
        if (!toolbar.classList.contains('gz-toolbar--clip-hidden')) {
          setToolbarIdle(true);
        }
      }, TOOLBAR_IDLE_MS);
    }

    function bindToolbarIdle() {
      if (!isNowySzblonMobile()) return;

      ['touchstart', 'pointerdown'].forEach(function (evName) {
        viewerEl.addEventListener(evName, bumpToolbarActivity, {
          passive: true,
          capture: true,
        });
        toolbar.addEventListener(evName, bumpToolbarActivity, { passive: true });
      });
    }

    function getHeaderBottom() {
      const header = document.querySelector('#header-component');
      if (header) {
        return Math.max(0, header.getBoundingClientRect().bottom);
      }

      const headerSection = document.querySelector('.header-section');
      if (headerSection) {
        return Math.max(0, headerSection.getBoundingClientRect().bottom);
      }

      const cssHeader = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue(
          '--header-height'
        )
      );
      return isFinite(cssHeader) && cssHeader > 0 ? cssHeader : 0;
    }

    // Panel w widocznej czesci viewera; na mobile z-index ponizej sticky headera.
    function pinToolbar() {
      if (isFullscreenMode()) {
        toolbar.classList.remove('gz-toolbar--clip-hidden');
        toolbar.style.top = '50%';
        toolbar.style.transform = 'translateY(-50%)';
        if (
          isNowySzblonMobile() &&
          toolbarIdleTimer === null &&
          !toolbar.classList.contains('gz-toolbar--idle')
        ) {
          bumpToolbarActivity();
        }
        return;
      }

      const rect = viewerEl.getBoundingClientRect();
      const vh =
        window.innerHeight || document.documentElement.clientHeight || 0;
      const mobile = isNowySzblonMobile();
      const headerBottom = mobile ? getHeaderBottom() : 0;
      const clipTop = mobile
        ? Math.max(rect.top, headerBottom)
        : Math.max(rect.top, 0);
      const clipBottom = Math.min(rect.bottom, vh);

      if (clipBottom <= clipTop) {
        toolbar.classList.add('gz-toolbar--clip-hidden');
        setToolbarIdle(false);
        clearToolbarIdleTimer();
        return;
      }

      toolbar.classList.remove('gz-toolbar--clip-hidden');
      if (mobile && toolbarIdleTimer === null && !toolbar.classList.contains('gz-toolbar--idle')) {
        bumpToolbarActivity();
      }

      const visibleTop = clipTop - rect.top;
      const visibleBottom = clipBottom - rect.top;
      const half = toolbar.offsetHeight / 2 + 16;
      let center = (visibleTop + visibleBottom) / 2;
      center = Math.max(half, Math.min(rect.height - half, center));
      toolbar.style.top = center + 'px';
      toolbar.style.transform = 'translateY(-50%)';
    }

    window.addEventListener('scroll', pinToolbar, { passive: true });
    window.addEventListener('resize', pinToolbar);

    function setButtonIcon(action, iconName) {
      if (buttons[action]) {
        buttons[action].innerHTML = iconSvg(iconName);
      }
    }

    function updateChrome() {
      const fullscreen = isFullscreenMode();
      const wasFullscreen = viewerEl.classList.contains('is-fullscreen');
      viewerEl.classList.toggle('is-fullscreen', fullscreen);
      syncWheelZoomMode();
      pinToolbar();
      if (isNowySzblonMobile() && fullscreen !== wasFullscreen) {
        bumpToolbarActivity();
      }

      setButtonIcon(
        'fullscreen',
        fullscreen ? 'exitFullscreen' : 'enterFullscreen'
      );
      if (buttons.fullscreen) {
        const fsLabel = fullscreen ? 'Zamknij pelny ekran' : 'Pelny ekran';
        buttons.fullscreen.title = fsLabel;
        buttons.fullscreen.setAttribute('aria-label', fsLabel);
      }

      if (buttons.fill) {
        const fillLabel = fullscreenFill ? 'Pokaz caly obraz' : 'Wypelnij ekran';
        buttons.fill.title = fillLabel;
        buttons.fill.setAttribute('aria-label', fillLabel);
        buttons.fill.setAttribute(
          'aria-pressed',
          fullscreenFill ? 'true' : 'false'
        );
        setButtonIcon('fill', fullscreenFill ? 'contain' : 'fill');
      }
    }

    function isAtMinZoom() {
      const zoom = viewer.viewport.getZoom(true);
      const minZoom = viewer.viewport.getMinZoom(true);
      return zoom <= minZoom * 1.001 + 0.0001;
    }

    function isPageAtTop() {
      return (window.scrollY || window.pageYOffset || 0) <= 1;
    }

    function syncWheelZoomMode() {
      viewer.gestureSettingsMouse.scrollToZoom = isFullscreenMode();
    }

    /* ---- Immersive zoom (PDP v3): przyblizenie chowa menu i powieksza R2 --- */

    function pdpV3Effects() {
      return (typeof window !== 'undefined' && window.__PDP_V3_EFFECTS__) || {};
    }

    function immersiveEnabled() {
      return (
        getProductTemplate() === 'product.szablon-produktu-v3' &&
        pdpV3Effects().zoom_immersive !== false &&
        !window.matchMedia('(prefers-reduced-motion: reduce)').matches
      );
    }

    function syncImmersive() {
      if (!immersiveEnabled()) return;
      var docEl = document.documentElement;
      var on = !isFullscreenMode() && isPageAtTop() && !isAtMinZoom();
      if (on === docEl.classList.contains('pdp-v3-zoom-immersive')) return;
      if (on) {
        /* Wysokosc headera mierzona przy wejsciu (gdy jeszcze widoczny) —
           ujemny margines zwija jego miejsce, strona podjezdza w gore. */
        var headerGroup = document.getElementById('header-group');
        if (headerGroup) {
          docEl.style.setProperty('--pdp-v3-header-h', headerGroup.offsetHeight + 'px');
        }
      }
      docEl.classList.toggle('pdp-v3-zoom-immersive', on);
    }

    viewer.addHandler('zoom', syncImmersive);
    window.addEventListener('scroll', syncImmersive, { passive: true });

    function isWheelOverViewer(event) {
      const rect = viewerEl.getBoundingClientRect();
      return (
        event.clientX >= rect.left &&
        event.clientX <= rect.right &&
        event.clientY >= rect.top &&
        event.clientY <= rect.bottom
      );
    }

    function wantsPageScrollPassthrough(event) {
      if (!isPageAtTop()) return true;
      return isAtMinZoom() && event.deltaY > 0;
    }

    /*
     * OSD przechwytuje wheel nawet przy scrollToZoom:false — poza fullscreen
     * obslugujemy wheel na document (capture). Passthrough: canvas-scroll z
     * preventDefault:false → natywny scroll. Zoom: reczny zoomBy. Pan zostaje
     * wlaczony (nie wylaczamy setMouseNavEnabled).
     */
    viewer.addHandler('canvas-scroll', function (event) {
      if (isFullscreenMode()) return;
      var original = event.originalEvent;
      if (!original || typeof original.deltaY !== 'number') return;

      if (wantsPageScrollPassthrough(original)) {
        event.preventDefaultAction = true;
        event.preventDefault = false;
      }
    });

    document.addEventListener(
      'wheel',
      function (event) {
        if (!viewer.isOpen() || isFullscreenMode() || !isWheelOverViewer(event)) {
          return;
        }

        if (wantsPageScrollPassthrough(event)) {
          return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();
        var factor = Math.exp(-event.deltaY * 0.0018);
        if (Math.abs(factor - 1) < 0.0001) return;
        viewer.viewport.zoomBy(factor);
        viewer.viewport.applyConstraints();
      },
      { capture: true, passive: false }
    );

    viewer.addOnceHandler('open', function () {
      resetToDefaultView(true);
      scheduleMobileDefaultView();
      updateChrome();
      pinToolbar();
      bindToolbarIdle();
      bumpToolbarActivity();
    });
    ['fullscreenchange', 'webkitfullscreenchange', 'MSFullscreenChange'].forEach(
      function (evName) {
        document.addEventListener(evName, scheduleFitCurrentMode);
      }
    );
    viewer.addHandler('resize', function () {
      if (isApplyingLayout) return;
      if (isFullscreenMode()) {
        fitCurrentMode(true);
      } else if (usesArtworkCoverDefault()) {
        resetToDefaultView(true);
        pinToolbar();
      }
    });
    viewer.addHandler('canvas-double-click', function (event) {
      event.preventDefaultAction = true;
      fitCurrentMode(false);
    });
  }

  function boot() {
    document.querySelectorAll('[data-giclee-zoom]').forEach(initZoom);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
