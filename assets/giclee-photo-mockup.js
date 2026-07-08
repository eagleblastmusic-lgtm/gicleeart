(function () {
    const hero = document.getElementById("pm-hero");
    if (!hero) return;

    function pmI18n(key, fallback) {
      if (typeof window.__gicleeI18nGet === 'function') return window.__gicleeI18nGet(key, fallback);
      var bag = window.__gicleeI18n || {};
      var v = bag[key];
      if (!v || (typeof v === 'string' && /translation missing/i.test(v))) return fallback;
      return v;
    }

    const embedHost = hero.closest(".product-wlasna-fotografia-mockup");
    const isIntroPin = !!hero.closest('[data-pm-intro-pin="1"]');
    const isPdpEmbed = !!embedHost;
    const host = embedHost || hero.closest(".shopify-section");
    const PM_REST_SCALE = 0.9;

    /* ── Pin intro — JS-sterowany kontr-scroll (transform #pm-hero) ──
       Grafika wizualnie stoi przez ~jeden ekran przewijania; strona przewija sie
       (tor .pm-pin-track daje dodatkowa wysokosc), a #pm-hero jest przesuwany
       w dol przez --pm-lift o tyle, ile strona sie przewinela. */
    const pinTrackEl = hero.closest(".pm-pin-track");
    const PM_PIN_MQ =
      window.matchMedia && window.matchMedia("(min-width: 981px)");
    const PM_PIN_REDUCE_MQ =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)");
    /** Dystans DOJAZDU tekstu przed trzymaniem (× wysokosc ekranu):
       tekst animuje sie gdy grafika wjezdza i osiada w centrum ZANIM zacznie sie freeze. */
    const PM_PIN_ANIM_PART = 0.7;
    /** Ulamek wysokosci ekranu = dystans "trzymania" (dodatkowy scroll). */
    const PM_PIN_DISTANCE_RATIO = 0.85;

    function pmPinActive() {
      return (
        isIntroPin &&
        !!pinTrackEl &&
        !!PM_PIN_MQ &&
        PM_PIN_MQ.matches &&
        !(PM_PIN_REDUCE_MQ && PM_PIN_REDUCE_MQ.matches) &&
        !hero.classList.contains("loaded")
      );
    }

    function pmPinDistancePx() {
      var vh = window.innerHeight || 1;
      return Math.round(vh * PM_PIN_DISTANCE_RATIO);
    }

    /* Pauza intro realizowana przez TWARDY scroll-lock (pmScrollLock), nie kontr-scroll.
       Tor pinu pozostaje inertny (display: contents); utrzymujemy --pm-lift = 0. */
    function updatePinLayout() {
      if (!pinTrackEl) return;
      pinTrackEl.classList.remove("pm-pin-track--on");
      pinTrackEl.style.height = "";
      if (!isPdpEmbed) hero.style.setProperty("--pm-lift", "0px");
    }

    function drivePinLift() {}

    /* Postep animacji tekstu 0..1 wg POZYCJI grafiki (#pm-wrapper) wzgledem srodka ekranu:
       - grafika ponizej srodka (distBelow > 0): 0..1 gdy sie zbliza (swobodny scroll);
       - tekst osiada w centrum ramki DOKLADNIE gdy grafika wysrodkowana (distBelow <= 0);
       - nizej/pod lockiem: 1 (tekst zamrozony). Freeze widoku robi pmScrollLock. */
    function getPinProgress() {
      var vh = window.innerHeight || 1;
      var distBelow = getFrameWindowCenterClient().y - vh / 2;
      if (distBelow <= 0) return 1;
      var approachPx = vh * PM_PIN_ANIM_PART;
      if (approachPx <= 0 || distBelow >= approachPx) return 0;
      var p = 1 - distBelow / approachPx;
      return p * p * (3 - 2 * p);
    }

    function getSideScale() {
      if (!mockupShell) return PM_REST_SCALE;
      var v = parseFloat(
        getComputedStyle(mockupShell).getPropertyValue("--pm-side-scale")
      );
      return isFinite(v) && v > 0 ? v : PM_REST_SCALE;
    }
    var mockupUiActive = !isPdpEmbed;
    var accum = 0;
    var displayP = 0;
    var lastTx = 0;
    var lastTy = 0;

    function refreshMockupUiActive() {
      if (!isPdpEmbed) return;
      var r = hero.getBoundingClientRect();
      var vh = window.innerHeight || 1;
      var visible = Math.min(r.bottom, vh) - Math.max(r.top, 0);
      var visibleRatio = Math.max(0, visible) / Math.max(1, r.height);
      var wasActive = mockupUiActive;
      mockupUiActive = visibleRatio >= 0.16 && r.top < vh * 0.76;
      if (!mockupUiActive && wasActive) accum = 0;
    }

    function syncMockupHostLayer() {
      if (!host) return;
      host.style.position = "relative";
      host.style.zIndex =
        window.matchMedia("(max-width: 749px)").matches ? "4" : "60";
      host.style.isolation = "isolate";
    }

    syncMockupHostLayer();
    window.addEventListener("resize", syncMockupHostLayer);

    new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) hero.classList.add("pm-hero--lift");
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    ).observe(hero);

    if (isPdpEmbed) {
      refreshMockupUiActive();
      window.addEventListener("scroll", refreshMockupUiActive, { passive: true });
      window.addEventListener("resize", refreshMockupUiActive);
    }

    (function scrollLift() {
      if (isPdpEmbed) return;
      const section = hero.closest(".shopify-section");
      if (!section) return;
      var maxPx = 72;
      var travel = 0.65;
      var ticking = false;

      function update() {
        // Pin intro (loopUi -> drivePinLift) w pelni steruje --pm-lift na standalone.
        // Gdy pin nieaktywny (np. po uploadzie), trzymamy 0 — bez starego entrance-lift.
        if (pmPinActive()) return;
        hero.style.setProperty("--pm-lift", "0px");
      }

      function onScroll() {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
          ticking = false;
          update();
        });
      }

      window.addEventListener("scroll", onScroll, { passive: true });
      window.addEventListener("resize", onScroll);
      update();
    })();

    const canvas = hero.querySelector("#pm-canvas");
    const wrapper = hero.querySelector("#pm-wrapper");
    const mockupShell = hero.querySelector(".pm-mockup-shell");
    const mockupBox = mockupShell || wrapper;
    const frame = hero.querySelector("#pm-frame");
    const upload = hero.querySelector("#pm-upload");
    if (!canvas || !wrapper || !frame || !upload) return;

    const ctx = canvas.getContext("2d");
    frame.crossOrigin = "anonymous";

    const frames = {
  landscape: {
    src: "https://cdn.shopify.com/s/files/1/1011/0517/2828/files/a4_poziom_v5_-_CZB.png?v=1780499409",
    baseSrc: "https://cdn.shopify.com/s/files/1/1011/0517/2828/files/a4_poziom_v5_-_CZB.png?v=1780499409",
    rendered: { w: 1000, h: 868 },
    source: { w: 1164, h: 1010 },
    /** Zewnętrzny obrys czarnej ramki w px źródłowego PNG. */
    outer: { x: 57, y: 92, w: 1055, h: 824 },
    window: { x: 195, y: 229, w: 775, h: 548 },
  },
  portrait: {
    src: "https://cdn.shopify.com/s/files/1/1011/0517/2828/files/a4_pion_v5_-_CZB.png?v=1780499407",
    baseSrc: "https://cdn.shopify.com/s/files/1/1011/0517/2828/files/a4_pion_v5_-_CZB.png?v=1780499407",
    rendered: { w: 800, h: 921 },
    source: { w: 1010, h: 1164 },
    outer: { x: 50, y: 57, w: 868, h: 1055 },
    window: { x: 232, y: 195, w: 548, h: 775 },
  },
};

    /** Zewnętrzne wymiary ramki (cm) — lib/pm-frame-sizes.json, orientacja pozioma. */
    const PM_FRAME_SIZES_CM = {
      M: { w: 36.1, h: 27.4 },
      L: { w: 58.7, h: 43.3 },
      XL: { w: 72.1, h: 55.1 },
    };
    const PM_SIZE_OVERLAY_KEY = "pm-frame-sizes-visible";

    let sizeOverlayEl = null;
    let sizeToggleInput = null;
    let pmSelectedFrameSize = "M";
    let sizeOverlayEnabled = true;

    try {
      const stored = localStorage.getItem(PM_SIZE_OVERLAY_KEY);
      if (stored !== null) sizeOverlayEnabled = stored === "1";
    } catch (err) {}

    function frameDimsForSize(size, orientation) {
      const raw = String(size || "M").toUpperCase();
      const key = raw === "S" ? "M" : raw;
      const base = PM_FRAME_SIZES_CM[key] || PM_FRAME_SIZES_CM.M;
      if (orientation === "portrait") {
        return { widthCm: base.h, heightCm: base.w };
      }
      return { widthCm: base.w, heightCm: base.h };
    }

    function fmtCmLabel(cm) {
      return cm.toFixed(1).replace(".", ",") + " cm";
    }

    function currentFrameShopifySize() {
      const cfg = window.pmFrameConfig;
      if (cfg && cfg.size) return cfg.size;
      const sel = document.querySelector(
        "#pm-config .pm-opt--size.is-selected"
      );
      if (sel) return sel.getAttribute("data-value") || pmSelectedFrameSize;
      return pmSelectedFrameSize;
    }

    function ensureSizeOverlay() {
      const host = mockupShell || wrapper;
      sizeOverlayEl = hero.querySelector("#pm-size-overlay");
      if (sizeOverlayEl && wrapper.contains(sizeOverlayEl) && host !== wrapper) {
        host.appendChild(sizeOverlayEl);
      }
      if (sizeOverlayEl) return sizeOverlayEl;

      sizeOverlayEl = document.createElement("div");
      sizeOverlayEl.className = "pm-size-overlay";
      sizeOverlayEl.id = "pm-size-overlay";
      sizeOverlayEl.setAttribute("aria-hidden", "true");
      sizeOverlayEl.innerHTML = "";
      host.appendChild(sizeOverlayEl);
      return sizeOverlayEl;
    }

    /** Ramka w px układu renderowanego (canvas / mockup). */
    function frameOuterRendered(f) {
      const src = f.source;
      const outer = f.outer || { x: 0, y: 0, w: src.w, h: src.h };
      const sx = f.rendered.w / src.w;
      const sy = f.rendered.h / src.h;
      const left = outer.x * sx;
      const top = outer.y * sy;
      const right = (outer.x + outer.w) * sx;
      const bottom = (outer.y + outer.h) * sy;
      return { left, top, right, bottom, midX: (left + right) / 2, midY: (top + bottom) / 2 };
    }

    /** Odstęp lewej linii wysokości od ramki (px renderowane). */
    const PM_DIM_GAP_HEIGHT = 6;
    const PM_DIM_GAP_HEIGHT_LANDSCAPE = 22;
    const PM_DIM_GAP_WIDTH = 11;
    /** Lewy koniec dolnej linii szerokości — wcięcie od narożnika ramki (px renderowane). */
    const PM_DIM_WIDTH_TRIM_LEFT = 14;
    const PM_DIM_LABEL = 15;
    const PM_DIM_LABEL_BELOW = 7;

    function buildSizeOverlayMarkup(f, widthLabel, heightLabel) {
      const rw = f.rendered.w;
      const rh = f.rendered.h;
      const fr = frameOuterRendered(f);
      const gapHeight =
        mode === "landscape" ? PM_DIM_GAP_HEIGHT_LANDSCAPE : PM_DIM_GAP_HEIGHT;
      const hX = Math.max(5, fr.left - gapHeight);
      const wY = Math.min(rh - 5, fr.bottom + PM_DIM_GAP_WIDTH);
      const wX1 = Math.min(fr.right - 24, fr.left + PM_DIM_WIDTH_TRIM_LEFT);
      const sideTickLen = fr.left - hX;
      const cornerTickLen =
        mode === "landscape" ? sideTickLen * 0.5 : sideTickLen;
      const hTickX2 = mode === "landscape" ? hX + cornerTickLen : fr.left;
      const pctX = function (px) {
        return ((px / rw) * 100).toFixed(3) + "%";
      };
      const pctY = function (px) {
        return ((px / rh) * 100).toFixed(3) + "%";
      };
      const esc = function (s) {
        return String(s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;");
      };
      const lines =
        '<line x1="' +
        hX +
        '" y1="' +
        fr.top +
        '" x2="' +
        hX +
        '" y2="' +
        fr.bottom +
        '"/>' +
        '<line x1="' +
        hX +
        '" y1="' +
        fr.top +
        '" x2="' +
        hTickX2 +
        '" y2="' +
        fr.top +
        '"/>' +
        '<line x1="' +
        hX +
        '" y1="' +
        fr.bottom +
        '" x2="' +
        hTickX2 +
        '" y2="' +
        fr.bottom +
        '"/>' +
        '<line x1="' +
        wX1 +
        '" y1="' +
        wY +
        '" x2="' +
        fr.right +
        '" y2="' +
        wY +
        '"/>' +
        '<line x1="' +
        wX1 +
        '" y1="' +
        (wY - cornerTickLen) +
        '" x2="' +
        wX1 +
        '" y2="' +
        wY +
        '"/>' +
        '<line x1="' +
        fr.right +
        '" y1="' +
        (wY - cornerTickLen) +
        '" x2="' +
        fr.right +
        '" y2="' +
        wY +
        '"/>';

      const hLabelX = hX - PM_DIM_LABEL;
      const wLabelY = Math.min(wY + PM_DIM_LABEL_BELOW, rh - 14);

      return (
        '<svg class="pm-size-svg" viewBox="0 0 ' +
        rw +
        " " +
        rh +
        '" preserveAspectRatio="none" aria-hidden="true">' +
        '<g class="pm-size-strokes pm-size-strokes--halo" fill="none">' +
        lines +
        "</g>" +
        '<g class="pm-size-strokes" fill="none">' +
        lines +
        "</g></svg>" +
        '<span class="pm-size-label pm-size-label--h" style="left:' +
        pctX(hLabelX) +
        ";top:" +
        pctY(fr.midY) +
        '">' +
        esc(heightLabel) +
        "</span>" +
        '<span class="pm-size-label pm-size-label--w" style="left:' +
        pctX(fr.midX) +
        ";top:" +
        pctY(wLabelY) +
        '">' +
        esc(widthLabel) +
        "</span>"
      );
    }

    function renderFrameSizeOverlay() {
      const overlay = ensureSizeOverlay();
      if (!overlay) return;

      const show = sizeOverlayEnabled && hero.classList.contains("loaded");
      overlay.classList.toggle("is-visible", show);
      overlay.setAttribute("aria-hidden", show ? "false" : "true");

      if (!show) return;

      const f = frames[mode];
      const dims = frameDimsForSize(currentFrameShopifySize(), mode);
      overlay.innerHTML = buildSizeOverlayMarkup(
        f,
        fmtCmLabel(dims.widthCm),
        fmtCmLabel(dims.heightCm)
      );
    }

    function bindFrameSizeOverlayUi() {
      sizeToggleInput = hero.querySelector("#pm-size-toggle");
      if (sizeToggleInput) {
        sizeToggleInput.checked = sizeOverlayEnabled;
        sizeToggleInput.addEventListener("change", function () {
          sizeOverlayEnabled = sizeToggleInput.checked;
          try {
            localStorage.setItem(
              PM_SIZE_OVERLAY_KEY,
              sizeOverlayEnabled ? "1" : "0"
            );
          } catch (err) {}
          renderFrameSizeOverlay();
        });
      }

      hero.addEventListener("pm-config-change", function (e) {
        if (e.detail && e.detail.size) pmSelectedFrameSize = e.detail.size;
        renderFrameSizeOverlay();
      });

      document.addEventListener("click", function (e) {
        const btn = e.target.closest(".pm-opt--size");
        if (!btn || !hero.contains(btn)) return;
        pmSelectedFrameSize = btn.getAttribute("data-value") || "M";
        renderFrameSizeOverlay();
      });

      const loadedObs = new MutationObserver(function () {
        renderFrameSizeOverlay();
      });
      loadedObs.observe(hero, {
        attributes: true,
        attributeFilter: ["class"],
      });
    }



    const MIN_ZOOM = 1;
    const MAX_ZOOM = 4;
    const ZOOM_STEP = 1.045;
    const ZOOM_WHEEL_SENS = 0.00068;
    const ZOOM_SMOOTH_TAU = 0.2;
    const FIT_SMOOTH_TAU = 0.32;

    let img = null;
    let sourceFile = null;
    /** Pełna rozdzielczość zdekodowana z pliku (createImageBitmap), nie tylko podgląd w img. */
    let fullDecode = { w: 0, h: 0 };
    /** Wczesny upload surowego pliku z telefonu (uploadId z workera). */
    let stagedUploadId = null;
    let stagedUploadPromise = null;
    let sourceBitmapRef = null;

    function isCoarseMobile() {
      return !!(
        window.matchMedia &&
        (window.matchMedia("(pointer: coarse)").matches ||
          window.matchMedia("(hover: none)").matches)
      );
    }

    function sourcePixelWidth() {
      if (!img) return 0;
      return img.naturalWidth || img.width || 0;
    }

    function sourcePixelHeight() {
      if (!img) return 0;
      return img.naturalHeight || img.height || 0;
    }

    function isHeicLikeFile(file) {
      if (!file) return false;
      var t = (file.type || "").toLowerCase();
      var n = (file.name || "").toLowerCase();
      return (
        t.indexOf("heic") >= 0 ||
        t.indexOf("heif") >= 0 ||
        /\.heic$/i.test(n) ||
        /\.heif$/i.test(n)
      );
    }

    function readFileAsRawBlob(file) {
      if (!file) return Promise.resolve(null);
      if (typeof file.arrayBuffer === "function") {
        return file.arrayBuffer().then(function (buf) {
          return new Blob([buf], {
            type: file.type || "application/octet-stream",
          });
        });
      }
      return Promise.resolve(file);
    }

    function releasePhotoSource() {
      if (sourceBitmapRef && typeof sourceBitmapRef.close === "function") {
        try {
          sourceBitmapRef.close();
        } catch (err) {}
      }
      sourceBitmapRef = null;
      img = null;
    }

    function updatePhotoQualityUi() {
      dispatchPmImageState();
    }
    let mode = "portrait";
    let baseScale = 1;

    const view = { zoom: 1, x: 0, y: 0 };
    let targetZoom = 1;
    let zoomAnchor = { x: 0, y: 0 };

    let dragging = false;
    let pinching = false;
    let dragStart = { x: 0, y: 0 };
    let viewStart = { x: 0, y: 0 };
    let pinchStartDist = 0;
    let pinchStartZoom = 1;
    const activePointers = new Map();

    const targetPan = { x: 0, y: 0 };

    let raf = 0;
    let zoomAnimTs = 0;
    let fitRaf = 0;
    let fitAnimTs = 0;
    let sliderDragging = false;

    function clampZoom(z) {
      return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z));
    }

    function normalizeWheelDelta(e) {
      var dy = e.deltaY;
      if (e.deltaMode === 1) dy *= 18;
      else if (e.deltaMode === 2) dy *= window.innerHeight * 0.85;
      return dy;
    }

    function wheelZoomFactor(deltaY) {
      return Math.exp(-deltaY * ZOOM_WHEEL_SENS);
    }

    function clientToCanvas(clientX, clientY) {
      const rect = canvas.getBoundingClientRect();
      const sx = canvas.width / rect.width;
      const sy = canvas.height / rect.height;
      return { x: (clientX - rect.left) * sx, y: (clientY - rect.top) * sy };
    }

    function dispatchPmImageState() {
      if (!img) return;
      var w = fullDecode.w || sourcePixelWidth();
      var h = fullDecode.h || sourcePixelHeight();
      hero.dispatchEvent(
        new CustomEvent("pm-image-loaded", {
          bubbles: true,
          detail: {
            widthPx: w,
            heightPx: h,
            decodeWidthPx: w,
            decodeHeightPx: h,
            fileBytes: sourceFile ? sourceFile.size : 0,
            orientation: mode,
          },
        })
      );
    }

    function getVisibleSourcePixels() {
      if (!img) return null;
      const win = getWindow();
      const scale = baseScale * view.zoom;
      const scaledW = img.width * scale;
      const scaledH = img.height * scale;
      const visLeft = Math.max(win.x, view.x);
      const visTop = Math.max(win.y, view.y);
      const visRight = Math.min(win.x + win.w, view.x + scaledW);
      const visBottom = Math.min(win.y + win.h, view.y + scaledH);
      const visibleW = Math.max(0, visRight - visLeft);
      const visibleH = Math.max(0, visBottom - visTop);
      return {
        widthPx: visibleW / scale,
        heightPx: visibleH / scale,
      };
    }

    function dispatchPmViewChange() {
      if (!img) return;
      const visible = getVisibleSourcePixels();
      if (!visible) return;
      hero.dispatchEvent(
        new CustomEvent("pm-view-change", {
          bubbles: true,
          detail: {
            widthPx: img.width,
            heightPx: img.height,
            orientation: mode,
            visibleWidthPx: visible.widthPx,
            visibleHeightPx: visible.heightPx,
            zoom: view.zoom,
          },
        })
      );
    }

    function passepartoutSuffixFromLabel(label) {
      const v = String(label || "").toLowerCase();
      return v.indexOf("czarn") >= 0 ? "CZCZ" : "CZB";
    }

    function frameUrlWithPassepartoutSuffix(baseSrc, suffix) {
      return String(baseSrc || "").replace(/_CZ(B|CZ)(?=\.png)/i, "_" + suffix);
    }

    function applyPassepartoutToFrames(label) {
      const suffix = passepartoutSuffixFromLabel(label);
      Object.keys(frames).forEach(function (key) {
        const f = frames[key];
        const base = f.baseSrc || f.src;
        f.baseSrc = frameUrlWithPassepartoutSuffix(base, "CZB");
        f.src = frameUrlWithPassepartoutSuffix(f.baseSrc, suffix);
      });
    }

    function refreshFrameOverlayOnly() {
      const f = frames[mode];
      if (!f || !frame) return;
      const targetSrc = f.src;
      const fallbackSrc = f.baseSrc || frameUrlWithPassepartoutSuffix(targetSrc, "CZB");
      frame.crossOrigin = "anonymous";
      function markReady() {
        hero.classList.add("pm-frame-ready");
      }
      frame.onload = markReady;
      frame.onerror = function () {
        frame.onerror = null;
        if (frame.src !== fallbackSrc) {
          f.src = fallbackSrc;
          frame.src = fallbackSrc;
        }
        markReady();
      };
      frame.src = targetSrc;
      if (frame.complete && frame.src === targetSrc) markReady();
    }

    function setFrame(nextMode) {
      mode = nextMode;
      const f = frames[mode];
      canvas.width = f.rendered.w;
      canvas.height = f.rendered.h;
      const sizeHost = mockupShell || wrapper;
      sizeHost.style.width = f.rendered.w + "px";
      sizeHost.style.maxWidth = "100%";
      sizeHost.style.height = "auto";
      sizeHost.style.aspectRatio = f.rendered.w + " / " + f.rendered.h;
      if (mockupShell) {
        wrapper.style.width = "100%";
        wrapper.style.maxWidth = "100%";
        wrapper.style.height = "";
        wrapper.style.aspectRatio = "";
        mockupShell.setAttribute("data-pm-orient", mode);
      } else {
        wrapper.setAttribute("data-pm-orient", mode);
      }
      frame.crossOrigin = "anonymous";
      function markFrameReady() {
        hero.classList.add("pm-frame-ready");
      }
      frame.onload = markFrameReady;
      frame.src = f.src;
      if (frame.complete) markFrameReady();
      hero.dispatchEvent(
        new CustomEvent("pm-frame-change", {
          bubbles: true,
          detail: { orientation: mode },
        })
      );
      renderFrameSizeOverlay();
    }

    function getWindow() {
      const f = frames[mode];
      const sx = f.rendered.w / f.source.w;
      const sy = f.rendered.h / f.source.h;
      return {
        x: f.window.x * sx,
        y: f.window.y * sy,
        w: f.window.w * sx,
        h: f.window.h * sy,
      };
    }

    function clampPanXY(x, y) {
      if (!img) return { x: x, y: y };
      const win = getWindow();
      const scale = baseScale * view.zoom;
      const iw = img.width * scale;
      const ih = img.height * scale;
      const minX = win.x + win.w - iw;
      const maxX = win.x;
      const minY = win.y + win.h - ih;
      const maxY = win.y;
      return {
        x: Math.min(maxX, Math.max(minX, x)),
        y: Math.min(maxY, Math.max(minY, y)),
      };
    }

    function clampView() {
      if (!img) return;
      const c = clampPanXY(view.x, view.y);
      view.x = c.x;
      view.y = c.y;
    }

    function syncTargetPanFromView() {
      targetPan.x = view.x;
      targetPan.y = view.y;
    }

    function panAfterZoom(x, y, oldZoom, newZoom, anchor) {
      const sOld = baseScale * oldZoom;
      const sNew = baseScale * newZoom;
      const relX = (anchor.x - x) / sOld;
      const relY = (anchor.y - y) / sOld;
      return { x: anchor.x - relX * sNew, y: anchor.y - relY * sNew };
    }

    function applyZoomAtPoint(newZoom, anchor) {
      const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, newZoom));
      const oldZoom = view.zoom;
      if (Math.abs(z - oldZoom) < 1e-9) return;
      const v = panAfterZoom(view.x, view.y, oldZoom, z, anchor);
      const t = panAfterZoom(targetPan.x, targetPan.y, oldZoom, z, anchor);
      view.zoom = z;
      const cv = clampPanXY(v.x, v.y);
      view.x = cv.x;
      view.y = cv.y;
      const ct = clampPanXY(t.x, t.y);
      targetPan.x = ct.x;
      targetPan.y = ct.y;
      if (dragging) {
        view.x = targetPan.x;
        view.y = targetPan.y;
      }
    }

    function cancelFitAnim() {
      if (fitRaf) cancelAnimationFrame(fitRaf);
      fitRaf = 0;
      fitAnimTs = 0;
    }

    function computeFitTarget() {
      const win = getWindow();
      const bs = Math.max(win.w / img.width, win.h / img.height);
      const scale = bs;
      return clampPanXY(
        win.x + (win.w - img.width * scale) / 2,
        win.y + (win.h - img.height * scale) / 2
      );
    }

    function applyFitTarget() {
      const win = getWindow();
      baseScale = Math.max(win.w / img.width, win.h / img.height);
      const pos = computeFitTarget();
      view.zoom = 1;
      targetZoom = 1;
      view.x = pos.x;
      view.y = pos.y;
      clampView();
      syncTargetPanFromView();
      draw();
      syncZoomSliderUI();
    }

    function tickFit(ts) {
      if (!img) {
        fitRaf = 0;
        return;
      }
      if (!fitAnimTs) fitAnimTs = ts;
      const dt = Math.min(0.05, (ts - fitAnimTs) / 1000);
      fitAnimTs = ts;
      const alpha = 1 - Math.exp(-dt / FIT_SMOOTH_TAU);

      const win = getWindow();
      baseScale = Math.max(win.w / img.width, win.h / img.height);
      const dest = computeFitTarget();

      view.zoom += (1 - view.zoom) * alpha;
      view.x += (dest.x - view.x) * alpha;
      view.y += (dest.y - view.y) * alpha;
      clampView();
      targetZoom = view.zoom;
      targetPan.x = view.x;
      targetPan.y = view.y;
      draw();
      syncZoomSliderUI();

      const done =
        Math.abs(1 - view.zoom) < 0.002 &&
        Math.hypot(dest.x - view.x, dest.y - view.y) < 0.6;

      if (done) {
        applyFitTarget();
        fitRaf = 0;
        fitAnimTs = 0;
        return;
      }
      fitRaf = requestAnimationFrame(tickFit);
    }

    function fitImage(smooth) {
      if (!img) return;
      cancelAnimationFrame(raf);
      raf = 0;
      zoomAnimTs = 0;

      if (smooth) {
        cancelFitAnim();
        fitAnimTs = 0;
        fitRaf = requestAnimationFrame(tickFit);
        return;
      }

      cancelFitAnim();
      applyFitTarget();
    }

    function draw() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!img) return;
      const scale = baseScale * view.zoom;
      ctx.drawImage(img, view.x, view.y, img.width * scale, img.height * scale);
      dispatchPmViewChange();
    }

    function getZoomWindowAnchor() {
      const win = getWindow();
      return { x: win.x + win.w / 2, y: win.y + win.h / 2 };
    }

    function zoomToSliderPercent(z) {
      const lo = Math.log(MIN_ZOOM);
      const hi = Math.log(MAX_ZOOM);
      return ((Math.log(z) - lo) / (hi - lo)) * 100;
    }

    function sliderPercentToZoom(p) {
      const lo = Math.log(MIN_ZOOM);
      const hi = Math.log(MAX_ZOOM);
      const t = Math.max(0, Math.min(100, p)) / 100;
      return Math.exp(lo + t * (hi - lo));
    }

    function syncZoomSliderUI() {
      if (!zoomSlider || !img || sliderDragging) return;
      zoomSlider.value = String(Math.round(zoomToSliderPercent(view.zoom)));
    }

    function applySliderZoomImmediate() {
      if (!img || !zoomSlider) return;
      cancelFitAnim();
      cancelZoomAnim();
      zoomAnchor = getZoomWindowAnchor();
      var z = clampZoom(sliderPercentToZoom(Number(zoomSlider.value)));
      targetZoom = z;
      applyZoomAtPoint(z, zoomAnchor);
      draw();
    }

    function endSliderDrag() {
      if (!sliderDragging) return;
      sliderDragging = false;
      targetZoom = view.zoom;
      syncZoomSliderUI();
    }

    function stepZoom(direction) {
      if (!img) return;
      zoomAnchor = getZoomWindowAnchor();
      const factor = direction > 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
      targetZoom = clampZoom(targetZoom * factor);
      scheduleZoomAnim();
    }

    function exportFilename() {
      var stamp = new Date();
      var pad = function (n) {
        return String(n).padStart(2, "0");
      };
      return (
        "giclee-podglad-" +
        mode +
        "-" +
        stamp.getFullYear() +
        pad(stamp.getMonth() + 1) +
        pad(stamp.getDate()) +
        "-" +
        pad(stamp.getHours()) +
        pad(stamp.getMinutes()) +
        ".jpg"
      );
    }

    function dataUrlToBlob(dataUrl) {
      var parts = dataUrl.split(",");
      var mime = parts[0].match(/:(.*?);/)[1];
      var bin = atob(parts[1]);
      var len = bin.length;
      var arr = new Uint8Array(len);
      for (var i = 0; i < len; i++) arr[i] = bin.charCodeAt(i);
      return new Blob([arr], { type: mime });
    }

    function canvasToJpegBlobPromise(canvas, quality) {
      return new Promise(function (resolve, reject) {
        canvasToJpegBlob(canvas, quality, function (blob) {
          if (blob && blob.size) resolve(blob);
          else reject(new Error("Nie udało się zakodować JPEG"));
        });
      });
    }

    function probeFullDecodeFromFile(file) {
      fullDecode = { w: 0, h: 0 };
      if (!file || typeof createImageBitmap !== "function") return Promise.resolve();
      return createImageBitmap(file, { imageOrientation: "from-image" })
        .then(function (bitmap) {
          fullDecode = { w: bitmap.width, h: bitmap.height };
          bitmap.close();
        })
        .catch(function () {});
    }

    function canvasToJpegBlob(canvas, quality, callback) {
      if (canvas.toBlob) {
        canvas.toBlob(
          function (blob) {
            if (blob && blob.size > 0) {
              callback(blob);
              return;
            }
            try {
              callback(dataUrlToBlob(canvas.toDataURL("image/jpeg", quality)));
            } catch (err) {
              callback(null);
            }
          },
          "image/jpeg",
          quality
        );
        return;
      }
      try {
        callback(dataUrlToBlob(canvas.toDataURL("image/jpeg", quality)));
      } catch (err) {
        callback(null);
      }
    }

    function encodeDrawSourceToJpegPromise(drawSource, quality) {
      if (!drawSource) return Promise.resolve(null);
      var canvas = document.createElement("canvas");
      canvas.width = drawSource.width;
      canvas.height = drawSource.height;
      var ctx2 = canvas.getContext("2d");
      if (!ctx2) return Promise.resolve(null);
      ctx2.drawImage(drawSource, 0, 0);
      return canvasToJpegBlobPromise(canvas, quality);
    }

    function needsOriginalFullUpload() {
      if (!sourceFile || !fullDecode.w) return false;
      var type = (sourceFile.type || "").toLowerCase();
      var isJpegPng =
        type === "image/jpeg" ||
        type === "image/jpg" ||
        type === "image/png";
      var displayW = sourcePixelWidth();
      var displayH = sourcePixelHeight();
      var displaySmaller =
        displayW > 0 &&
        displayH > 0 &&
        (fullDecode.w > displayW + 2 || fullDecode.h > displayH + 2);
      if (isHeicLikeFile(sourceFile) || type === "image/webp") return true;
      if (displaySmaller) return true;
      if (!type || type === "application/octet-stream") return true;
      if (isCoarseMobile() && !isJpegPng) return true;
      return false;
    }

    function buildOriginalFullBlobPromise() {
      if (!needsOriginalFullUpload()) {
        return Promise.resolve(null);
      }
      var quality = isCoarseMobile() ? 0.99 : 0.98;
      if (sourceBitmapRef) {
        return encodeDrawSourceToJpegPromise(sourceBitmapRef, quality);
      }
      if (typeof createImageBitmap !== "function") {
        return Promise.resolve(null);
      }
      return createImageBitmap(sourceFile, { imageOrientation: "from-image" })
        .then(function (bitmap) {
          return encodeDrawSourceToJpegPromise(bitmap, quality).then(function (blob) {
            bitmap.close();
            return blob;
          });
        })
        .catch(function () {
          return null;
        });
    }

    function loadViaImageElement(file) {
      return new Promise(function (resolve, reject) {
        var image = new Image();
        var url = URL.createObjectURL(file);
        image.onload = function () {
          URL.revokeObjectURL(url);
          fullDecode = {
            w: image.naturalWidth || image.width,
            h: image.naturalHeight || image.height,
          };
          resolve(image);
        };
        image.onerror = function () {
          URL.revokeObjectURL(url);
          reject(new Error("Nie udało się wczytać zdjęcia"));
        };
        image.src = url;
      });
    }

    /** Pełna rozdzielczość — createImageBitmap (iOS/Android), nie ograniczony podgląd Image(). */
    function loadPhotoFromFile(file) {
      if (typeof createImageBitmap !== "function") {
        return loadViaImageElement(file);
      }
      return createImageBitmap(file, { imageOrientation: "from-image" })
        .then(function (bitmap) {
          fullDecode = { w: bitmap.width, h: bitmap.height };
          sourceBitmapRef = bitmap;
          return bitmap;
        })
        .catch(function () {
          return loadViaImageElement(file);
        });
    }

    function stageRawUploadOnMobile() {
      if (!isCoarseMobile() || !sourceFile) return Promise.resolve(null);
      var apiUrl = (hero.getAttribute("data-pm-upload-api") || "").trim();
      if (!apiUrl) return Promise.resolve(null);
      if (stagedUploadId) return Promise.resolve(stagedUploadId);
      if (stagedUploadPromise) return stagedUploadPromise;

      stagedUploadPromise = readFileAsRawBlob(sourceFile)
        .then(function (rawBlob) {
          if (!rawBlob || !rawBlob.size) return null;
          var fd = new FormData();
          fd.append("original", rawBlob, sourceFile.name || "photo.jpg");
          fd.append("stage_only", "1");
          fd.append(
            "meta_extra",
            JSON.stringify({
              dimensions: {
                decodeWidth: fullDecode.w,
                decodeHeight: fullDecode.h,
                originalBytes: sourceFile.size,
                originalType: sourceFile.type || null,
                originalName: sourceFile.name || null,
                stagedFromMobile: true,
              },
            })
          );
          return fetch(apiUrl, { method: "POST", body: fd }).then(function (res) {
            return res.json().then(function (data) {
              if (!res.ok || !data || !data.uploadId) {
                return null;
              }
              stagedUploadId = data.uploadId;
              return stagedUploadId;
            });
          });
        })
        .catch(function () {
          return null;
        })
        .finally(function () {
          stagedUploadPromise = null;
        });

      return stagedUploadPromise;
    }

    function loadCorsImage(src) {
      return new Promise(function (resolve) {
        var im = new Image();
        im.crossOrigin = "anonymous";
        im.onload = function () {
          resolve(im);
        };
        im.onerror = function () {
          resolve(null);
        };
        im.src =
          src + (src.indexOf("?") >= 0 ? "&" : "?") + "pm_export=" + Date.now();
      });
    }

    /** Pobranie pliku — bez nawigacji do blob: w tej samej karcie. */
    function anchorDownloadBlob(blob, filename) {
      try {
        var url = URL.createObjectURL(blob);
        var link = document.createElement("a");
        link.style.display = "none";
        link.href = url;
        link.download = filename;
        link.setAttribute("download", filename);
        link.rel = "noopener";
        document.body.appendChild(link);
        link.click();
        window.setTimeout(function () {
          URL.revokeObjectURL(url);
          if (link.parentNode) link.remove();
        }, 60000);
        return true;
      } catch (err) {
        console.warn("pm-export: download failed", err);
        return false;
      }
    }

    function saveBlobToFile(blob, filename) {
      if (!blob || !blob.size) return Promise.resolve(false);

      var nav = window.navigator;
      var coarse =
        window.matchMedia && window.matchMedia("(pointer: coarse)").matches;

      if (coarse && nav && typeof nav.share === "function" && typeof File !== "undefined") {
        try {
          var shareFile = new File([blob], filename, { type: "image/jpeg" });
          if (typeof nav.canShare !== "function" || nav.canShare({ files: [shareFile] })) {
            return nav
              .share({ files: [shareFile], title: filename })
              .then(function () {
                return true;
              })
              .catch(function (err) {
                if (err && err.name === "AbortError") return false;
                return anchorDownloadBlob(blob, filename);
              });
          }
        } catch (shareErr) {}
      }

      if (nav && typeof nav.msSaveOrOpenBlob === "function") {
        return Promise.resolve(nav.msSaveOrOpenBlob(blob, filename));
      }

      var canSavePicker =
        typeof window.showSaveFilePicker === "function" &&
        window.isSecureContext &&
        !coarse;

      if (canSavePicker) {
        return window
          .showSaveFilePicker({
            suggestedName: filename,
            types: [
              {
                description: "Obraz JPEG",
                accept: { "image/jpeg": [".jpg", ".jpeg"] },
              },
            ],
          })
          .then(function (handle) {
            return handle.createWritable();
          })
          .then(function (writable) {
            return writable.write(blob).then(function () {
              return writable.close();
            });
          })
          .then(function () {
            return true;
          })
          .catch(function (err) {
            if (err && err.name === "AbortError") return false;
            return anchorDownloadBlob(blob, filename);
          });
      }

      return Promise.resolve(anchorDownloadBlob(blob, filename));
    }

    function showPmExportToast(message) {
      var toast = document.getElementById("pm-export-toast");
      if (!toast) return;
      if (showPmExportToast._timer) {
        window.clearTimeout(showPmExportToast._timer);
      }
      toast.textContent = message || pmI18n("mockup_file_saved", "Plik zapisany");
      toast.hidden = false;
      toast.classList.add("is-visible");
      showPmExportToast._timer = window.setTimeout(function () {
        toast.classList.remove("is-visible");
        window.setTimeout(function () {
          toast.hidden = true;
        }, 320);
      }, 2600);
    }

    function getCropPayload(frameConfig) {
      if (!img) return null;
      const win = getWindow();
      const scale = baseScale * view.zoom;
      const scaledW = img.width * scale;
      const scaledH = img.height * scale;
      const visLeft = Math.max(win.x, view.x);
      const visTop = Math.max(win.y, view.y);
      const visRight = Math.min(win.x + win.w, view.x + scaledW);
      const visBottom = Math.min(win.y + win.h, view.y + scaledH);
      const cropSrcX = (visLeft - view.x) / scale;
      const cropSrcY = (visTop - view.y) / scale;
      const cropSrcW = Math.max(0, (visRight - visLeft) / scale);
      const cropSrcH = Math.max(0, (visBottom - visTop) / scale);
      const decodeW = fullDecode.w || img.width;
      const decodeH = fullDecode.h || img.height;
      const toFullX = decodeW / (img.width || decodeW);
      const toFullY = decodeH / (img.height || decodeH);
      const toFull = (toFullX + toFullY) / 2;
      return {
        v: 1,
        orientation: mode,
        sourceWidthPx: decodeW,
        sourceHeightPx: decodeH,
        displayWidthPx: img.width,
        displayHeightPx: img.height,
        baseScale: baseScale,
        zoom: view.zoom,
        panCanvas: { x: view.x, y: view.y },
        frameWindow: { x: win.x, y: win.y, w: win.w, h: win.h },
        cropSource: {
          x: cropSrcX * toFull,
          y: cropSrcY * toFull,
          width: cropSrcW * toFull,
          height: cropSrcH * toFull,
        },
        cropSourceDisplay: {
          x: cropSrcX,
          y: cropSrcY,
          width: cropSrcW,
          height: cropSrcH,
        },
        frameConfig: frameConfig || window.pmFrameConfig || null,
      };
    }

    function buildPreviewBlobPromise() {
      return new Promise(function (resolve, reject) {
        if (!img) {
          reject(new Error("Brak zdjęcia w mockupie"));
          return;
        }
        const f = frames[mode];
        const out = document.createElement("canvas");
        out.width = f.rendered.w;
        out.height = f.rendered.h;
        const octx = out.getContext("2d");
        if (!octx) {
          reject(new Error("Canvas niedostępny"));
          return;
        }
        const scale = baseScale * view.zoom;
        octx.drawImage(
          img,
          view.x,
          view.y,
          img.width * scale,
          img.height * scale
        );
        loadCorsImage(f.src).then(function (corsFrame) {
          if (corsFrame) {
            octx.drawImage(corsFrame, 0, 0, out.width, out.height);
          }
          canvasToJpegBlob(out, 0.92, function (blob) {
            if (blob && blob.size) resolve(blob);
            else reject(new Error("Nie udało się wygenerować podglądu"));
          });
        });
      });
    }

    function exportMockupJpeg() {
      if (!img) return;
      var exportBtn = document.getElementById("pm-export-jpg");
      var exportLabel = exportBtn
        ? exportBtn.querySelector(".pm-hint__export-btn__label")
        : null;
      var prevLabel = exportLabel ? exportLabel.textContent : "";
      if (exportBtn) exportBtn.disabled = true;

      function setExportLabel(text) {
        if (exportLabel) exportLabel.textContent = text;
      }

      function releaseBtn() {
        if (exportBtn) exportBtn.disabled = false;
        if (exportLabel) exportLabel.textContent = prevLabel || pmI18n("mockup_export_jpg", "Eksport .jpg");
      }

      setExportLabel(pmI18n("mockup_export_preparing", "Przygotowanie…"));
      buildPreviewBlobPromise()
        .then(function (blob) {
          setExportLabel(pmI18n("mockup_export_saving", "Zapisywanie…"));
          return saveBlobToFile(blob, exportFilename());
        })
        .then(function (ok) {
          releaseBtn();
          if (ok) showPmExportToast(pmI18n("mockup_file_saved", "Plik zapisany"));
        })
        .catch(function () {
          releaseBtn();
        });
    }

    function tickZoom(ts) {
      if (!img) return;
      if (!zoomAnimTs) zoomAnimTs = ts;
      var dt = Math.min(0.05, (ts - zoomAnimTs) / 1000);
      zoomAnimTs = ts;
      var alpha = 1 - Math.exp(-dt / ZOOM_SMOOTH_TAU);
      var next = view.zoom + (targetZoom - view.zoom) * alpha;
      if (Math.abs(targetZoom - view.zoom) < 0.0012) {
        applyZoomAtPoint(targetZoom, zoomAnchor);
        draw();
        syncZoomSliderUI();
        zoomAnimTs = 0;
        raf = 0;
        return;
      }
      applyZoomAtPoint(next, zoomAnchor);
      draw();
      syncZoomSliderUI();
      raf = requestAnimationFrame(tickZoom);
    }

    function scheduleZoomAnim() {
      cancelFitAnim();
      if (!raf) {
        zoomAnimTs = 0;
        raf = requestAnimationFrame(tickZoom);
      }
    }

    function nudgeTargetZoom(factor, anchor) {
      if (!img) return;
      zoomAnchor = anchor;
      targetZoom = clampZoom(targetZoom * factor);
      scheduleZoomAnim();
    }

    canvas.addEventListener(
      "wheel",
      function (e) {
        if (!img) return;
        e.preventDefault();
        nudgeTargetZoom(
          wheelZoomFactor(normalizeWheelDelta(e)),
          clientToCanvas(e.clientX, e.clientY)
        );
      },
      { passive: false }
    );

    function pointerPairDistance(a, b) {
      return Math.hypot(a.x - b.x, a.y - b.y);
    }

    function getActivePointerPair() {
      if (activePointers.size < 2) return null;
      var pts = Array.from(activePointers.values());
      return [pts[0], pts[1]];
    }

    function cancelZoomAnim() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      zoomAnimTs = 0;
    }

    function beginPinchGesture() {
      var pair = getActivePointerPair();
      if (!pair) return;
      pinching = true;
      dragging = false;
      canvas.classList.remove("pm-dragging");
      cancelFitAnim();
      cancelZoomAnim();
      pinchStartDist = Math.max(pointerPairDistance(pair[0], pair[1]), 24);
      pinchStartZoom = view.zoom;
      zoomAnchor = clientToCanvas(
        (pair[0].x + pair[1].x) * 0.5,
        (pair[0].y + pair[1].y) * 0.5
      );
      targetZoom = view.zoom;
      activePointers.forEach(function (_, id) {
        try {
          canvas.releasePointerCapture(id);
        } catch (err) {}
      });
    }

    function beginDragGesture(clientX, clientY, pointerId) {
      pinching = false;
      cancelFitAnim();
      try {
        canvas.setPointerCapture(pointerId);
      } catch (err) {}
      dragging = true;
      canvas.classList.add("pm-dragging");
      var p = clientToCanvas(clientX, clientY);
      dragStart = p;
      viewStart = { x: targetPan.x, y: targetPan.y };
    }

    function applyDragPan(raw) {
      view.x = raw.x;
      view.y = raw.y;
      targetPan.x = raw.x;
      targetPan.y = raw.y;
      draw();
    }

    canvas.addEventListener("pointerdown", function (e) {
      if (!img || e.button !== 0) return;
      activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      e.preventDefault();
      if (activePointers.size >= 2) {
        beginPinchGesture();
        return;
      }
      beginDragGesture(e.clientX, e.clientY, e.pointerId);
    });

    canvas.addEventListener("pointermove", function (e) {
      if (!img || !activePointers.has(e.pointerId)) return;
      activePointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (pinching && activePointers.size >= 2) {
        e.preventDefault();
        var pair = getActivePointerPair();
        if (!pair) return;
        var dist = Math.max(pointerPairDistance(pair[0], pair[1]), 24);
        var ratio = dist / pinchStartDist;
        applyZoomAtPoint(pinchStartZoom * ratio, zoomAnchor);
        draw();
        syncZoomSliderUI();
        targetZoom = view.zoom;
        return;
      }
      if (!dragging || pinching || activePointers.size !== 1) return;
      e.preventDefault();
      var p = clientToCanvas(e.clientX, e.clientY);
      var raw = clampPanXY(
        viewStart.x + (p.x - dragStart.x),
        viewStart.y + (p.y - dragStart.y)
      );
      applyDragPan(raw);
    });

    function releaseCanvasPointer(e) {
      if (!activePointers.has(e.pointerId)) return;
      activePointers.delete(e.pointerId);
      try {
        canvas.releasePointerCapture(e.pointerId);
      } catch (err) {}

      if (pinching && activePointers.size < 2) {
        pinching = false;
        pinchStartDist = 0;
        targetZoom = view.zoom;
        if (activePointers.size === 1) {
          var remaining = Array.from(activePointers.entries())[0];
          beginDragGesture(remaining[1].x, remaining[1].y, remaining[0]);
        }
      }

      if (activePointers.size === 0) {
        dragging = false;
        pinching = false;
        canvas.classList.remove("pm-dragging");
      }
    }

    canvas.addEventListener("pointerup", releaseCanvasPointer);
    canvas.addEventListener("pointercancel", releaseCanvasPointer);
    canvas.addEventListener("lostpointercapture", function (e) {
      if (pinching || !dragging) return;
      releaseCanvasPointer(e);
    });

    canvas.addEventListener("dblclick", function (e) {
      if (!img) return;
      e.preventDefault();
      fitImage(true);
    });

    applyPassepartoutToFrames(
      (window.pmFrameConfig && window.pmFrameConfig.passepartout) || "Białe"
    );
    setFrame("portrait");

    hero.addEventListener("pm-config-change", function (e) {
      const label = e.detail && e.detail.passepartout;
      if (!label) return;
      applyPassepartoutToFrames(label);
      refreshFrameOverlayOnly();
    });
    bindFrameSizeOverlayUi();
    renderFrameSizeOverlay();

    var hintEl = hero.querySelector(".pm-hint");
    var shopEl = hero.querySelector(".pm-side-shop");
    var zoomRailEl = hero.querySelector(".pm-zoom-rail");
    var zoomSlider = document.getElementById("pm-zoom-slider");
    var zoomInBtn = document.getElementById("pm-zoom-in");
    var zoomOutBtn = document.getElementById("pm-zoom-out");

    function syncPmMockupCenterUi() {
      if (!wrapper || !hero.classList.contains("loaded")) return;
      var stage = wrapper.closest(".pm-stage");
      if (!stage) return;
      var heroRect = hero.getBoundingClientRect();
      var stageRect = stage.getBoundingClientRect();
      var wrapRect = mockupBox.getBoundingClientRect();
      var isLaptopBand =
        window.innerWidth >= 1024 && window.innerWidth <= 1400;
      var isDesktopWide = window.innerWidth > 1400;
      var mockupClear = isLaptopBand
        ? Math.round(Math.min(34, Math.max(22, window.innerWidth * 0.022)))
        : isDesktopWide
          ? Math.round(Math.min(84, Math.max(56, window.innerWidth * 0.042)))
          : Math.round(Math.min(52, Math.max(36, window.innerWidth * 0.032)));
      var hintGap = isLaptopBand ? 8 : isDesktopWide ? 20 : 14;
      var shopGap = isLaptopBand ? 14 : 22;
      var rightInset = isLaptopBand
        ? Math.round(Math.min(36, Math.max(20, window.innerWidth * 0.02)))
        : Math.round(Math.min(58, Math.max(38, window.innerWidth * 0.032)));
      var sideBlend = window.innerWidth < 1024 ? 0.48 : 0;
      var sideScale = getSideScale();
      var cx = wrapRect.left + wrapRect.width * 0.5;
      var cy = wrapRect.top + wrapRect.height * 0.5;
      var anchorW = mockupBox.offsetWidth * sideScale;
      var anchorH = mockupBox.offsetHeight * sideScale;
      var visualRight = cx + anchorW * 0.5 - stageRect.left;
      var minZoomLeft = visualRight + mockupClear;
      var hintTop = cy - stageRect.top;
      var hintBelowTop = cy + anchorH * 0.5 - stageRect.top + 14;

      var zoomWidth = 0;
      var zoomLeft = minZoomLeft;
      var hintLeft = minZoomLeft;

      if (hintEl && zoomRailEl) {
        var hintWidth = hintEl.offsetWidth || (isLaptopBand ? 148 : 168);
        zoomWidth = zoomRailEl.offsetWidth || 46;
        var desiredHintLeft = minZoomLeft + zoomWidth + hintGap;
        var packedHintLeft = stageRect.width - hintWidth - rightInset;
        hintLeft = Math.round(
          desiredHintLeft + (packedHintLeft - desiredHintLeft) * sideBlend
        );
        zoomLeft = Math.max(minZoomLeft, hintLeft - zoomWidth - hintGap);
        hintLeft = zoomLeft + zoomWidth + hintGap;
      }

      stage.style.setProperty("--pm-zoom-left", zoomLeft.toFixed(2) + "px");
      stage.style.setProperty("--pm-zoom-top", hintTop.toFixed(2) + "px");
      stage.style.setProperty("--pm-hint-left", hintLeft.toFixed(2) + "px");
      stage.style.setProperty("--pm-hint-top", hintTop.toFixed(2) + "px");
      stage.style.setProperty("--pm-hint-below-top", hintBelowTop.toFixed(2) + "px");

      if (hintEl) {
        var hintWidthCheck = hintEl.offsetWidth || 168;
        var totalSide = zoomWidth + (zoomWidth ? hintGap : 0) + hintWidthCheck;
        var roomRight = stageRect.width - minZoomLeft - 12;
        /* Tablet (<1024) — układ pod mockupem; laptop/desktop — zawsze z boku. */
        var stackLayout = window.innerWidth < 1024;
        if (stackLayout) {
          hintEl.classList.add("pm-hint--below");
        } else {
          hintEl.classList.remove("pm-hint--below");
        }
        if (hintEl.classList.contains("pm-hint--below")) {
          stage.style.setProperty(
            "--pm-hint-left",
            (stageRect.width * 0.5).toFixed(2) + "px"
          );
        }
      }

      if (
        mockupShell &&
        isLaptopBand &&
        hintEl &&
        !hintEl.classList.contains("pm-hint--below")
      ) {
        var shopW =
          shopEl && !shopEl.hidden ? shopEl.offsetWidth || 0 : 0;
        var panelsRight =
          hintLeft +
          Math.max(hintEl.offsetWidth || 168, shopW) +
          rightInset;
        var maxScale = window.innerWidth < 1200 ? 0.9 : 0.98;
        var minScale = 0.62;
        var fitScale = sideScale;
        while (panelsRight > stageRect.width && fitScale > minScale) {
          fitScale = Math.max(minScale, fitScale - 0.035);
          mockupShell.style.setProperty(
            "--pm-side-scale",
            fitScale.toFixed(3)
          );
          anchorW = mockupBox.offsetWidth * fitScale;
          visualRight = cx + anchorW * 0.5 - stageRect.left;
          minZoomLeft = visualRight + mockupClear;
          if (hintEl && zoomRailEl) {
            zoomLeft = minZoomLeft;
            hintLeft = minZoomLeft + zoomWidth + hintGap;
          } else {
            zoomLeft = minZoomLeft;
            hintLeft = minZoomLeft;
          }
          panelsRight =
            hintLeft +
            Math.max(hintEl.offsetWidth || 168, shopW) +
            rightInset;
        }
        if (fitScale > maxScale) {
          fitScale = maxScale;
          mockupShell.style.setProperty(
            "--pm-side-scale",
            fitScale.toFixed(3)
          );
        }

        var layoutH = mockupBox.offsetHeight;
        if (layoutH > 0) {
          var vh = window.innerHeight || 800;
          var vertReserve = Math.round(
            Math.min(168, Math.max(112, vh * 0.16 + 24))
          );
          var vertBudget = Math.max(320, vh - stageRect.top - vertReserve);
          var scaledH = layoutH * fitScale;
          if (scaledH > vertBudget) {
            fitScale = Math.max(minScale, vertBudget / layoutH);
            mockupShell.style.setProperty(
              "--pm-side-scale",
              fitScale.toFixed(3)
            );
          }
        }

        stage.style.setProperty("--pm-zoom-left", zoomLeft.toFixed(2) + "px");
        stage.style.setProperty("--pm-hint-left", hintLeft.toFixed(2) + "px");
      } else if (mockupShell && isLaptopBand) {
        var layoutHOnly = mockupBox.offsetHeight;
        if (layoutHOnly > 0) {
          var vhOnly = window.innerHeight || 800;
          var vertReserveOnly = Math.round(
            Math.min(168, Math.max(112, vhOnly * 0.16 + 24))
          );
          var vertBudgetOnly = Math.max(
            320,
            vhOnly - stageRect.top - vertReserveOnly
          );
          var fitScaleOnly = getSideScale();
          if (layoutHOnly * fitScaleOnly > vertBudgetOnly) {
            mockupShell.style.setProperty(
              "--pm-side-scale",
              Math.max(0.62, vertBudgetOnly / layoutHOnly).toFixed(3)
            );
          }
        }
      }

      var useFlowLayout = window.innerWidth < 980;

      if (useFlowLayout && mockupShell) {
        mockupShell.style.setProperty("--pm-side-scale", "1");
        mockupShell.style.removeProperty("--pm-hover-scale");
      }

      if (
        shopEl &&
        hintEl &&
        hero.classList.contains("loaded") &&
        !useFlowLayout
      ) {
        var shopLift = isLaptopBand ? 24 : 36;
        var hintBelow = hintEl.classList.contains("pm-hint--below");
        shopEl.classList.toggle("pm-side-shop--below", hintBelow);
        var shopHeight = shopEl.offsetHeight || 0;
        var shopLeft = hintLeft;

        if (hintBelow) {
          var belowTop = parseFloat(
            getComputedStyle(stage).getPropertyValue("--pm-hint-below-top")
          );
          if (!isFinite(belowTop)) belowTop = hintBelowTop;
          var shopTopBelow = belowTop - shopGap - shopLift - shopHeight;
          stage.style.setProperty("--pm-shop-left", (stageRect.width * 0.5).toFixed(2) + "px");
          stage.style.setProperty("--pm-shop-top", shopTopBelow.toFixed(2) + "px");
        } else {
          var hintHeightNow = hintEl.offsetHeight || 0;
          var hintTopEdge = hintTop - hintHeightNow * 0.5;
          var shopTop = hintTopEdge - shopGap - shopLift - shopHeight;
          stage.style.setProperty("--pm-shop-left", shopLeft.toFixed(2) + "px");
          stage.style.setProperty("--pm-shop-top", Math.max(12, shopTop).toFixed(2) + "px");
        }

        stage.style.setProperty(
          "--pm-shop-max-width",
          (isLaptopBand ? "min(210px, " : "min(280px, ") +
            "calc(100% - " +
            Math.max(shopLeft, 0).toFixed(2) +
            "px - 16px))"
        );
      }

      if (isPdpEmbed) {
        var centerY = wrapRect.top + wrapRect.height / 2 - heroRect.top;
        hero.style.setProperty("--pm-mockup-center-y", centerY.toFixed(2) + "px");
      }
    }

    function schedulePmMockupCenterUiSync() {
      requestAnimationFrame(function () {
        requestAnimationFrame(syncPmMockupCenterUi);
      });
    }

    window.addEventListener("scroll", schedulePmMockupCenterUiSync, { passive: true });
    window.addEventListener("resize", schedulePmMockupCenterUiSync);
    hero.addEventListener("pm-side-shop-update", schedulePmMockupCenterUiSync);

    upload.addEventListener("change", function (e) {
      const file = e.target.files[0];
      if (!file) return;
      stagedUploadId = null;
      stagedUploadPromise = null;
      releasePhotoSource();
      sourceFile = file;
      loadPhotoFromFile(file)
        .then(function (source) {
          img = source;
          hero.classList.add("loaded");
          updatePinLayout();
          const isLandscape = sourcePixelWidth() >= sourcePixelHeight();
          setFrame(isLandscape ? "landscape" : "portrait");
          fitImage();
          dispatchPmImageState();
          updatePhotoQualityUi();
          upload.value = "";
          scheduleScrollAfterLayout();
          stageRawUploadOnMobile();
        })
        .catch(function () {
          sourceFile = null;
          releasePhotoSource();
          updatePhotoQualityUi();
          upload.value = "";
        });
    });

    const uiWrap = document.getElementById("pm-hero-ui");
    const coarsePointer =
      window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
    const disableMobilePdpScrollCoupling = coarsePointer && isPdpEmbed;

    var WHEEL_NOTCH = 100;
    var WHEEL_STEPS = isPdpEmbed ? 4 : 6;
    var WHEEL_NEED = WHEEL_NOTCH * WHEEL_STEPS;
    var WHEEL_SPAN = WHEEL_NEED * (isPdpEmbed ? 0.7 : 0.8);

    var reduceMotion =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function targetPFromAccum(a) {
      if (a <= WHEEL_NEED) return 0;
      var t = (a - WHEEL_NEED) / WHEEL_SPAN;
      return Math.max(0, Math.min(1, t));
    }

    function getFrameWindowCenterClient() {
      var wr = wrapper.getBoundingClientRect();
      var f = frames[mode];
      var win = getWindow();
      var sx = wr.width / f.rendered.w;
      var sy = wr.height / f.rendered.h;
      return {
        x: wr.left + (win.x + win.w / 2) * sx,
        y: wr.top + (win.y + win.h / 2) * sy,
      };
    }

    function tickUiSmooth() {
      if (disableMobilePdpScrollCoupling) {
        accum = 0;
        displayP = 0;
        if (uiWrap) {
          uiWrap.style.transform = "";
          lastTx = lastTy = 0;
        }
        if (!uiWrap || hero.classList.contains("loaded")) return;
      }

      if (!uiWrap || hero.classList.contains("loaded")) {
        if (uiWrap) {
          uiWrap.style.transform = "";
          lastTx = lastTy = 0;
        }
        return;
      }
      var targetP = pmPinActive()
        ? getPinProgress()
        : isPdpEmbed && !mockupUiActive
          ? 0
          : targetPFromAccum(accum);
      var k = reduceMotion ? 1 : 0.1;
      displayP += (targetP - displayP) * k;
      if (Math.abs(targetP - displayP) < 0.0004) displayP = targetP;
      var rect = uiWrap.getBoundingClientRect();
      var ucx = rect.left + rect.width / 2 - lastTx;
      var ucy = rect.top + rect.height / 2 - lastTy;
      var tc = getFrameWindowCenterClient();
      var fdx = tc.x - ucx;
      var fdy = tc.y - ucy;
      lastTx = fdx * displayP;
      lastTy = fdy * displayP;
      uiWrap.style.transform =
        "translate3d(" + lastTx.toFixed(2) + "px," + lastTy.toFixed(2) + "px,0)";
    }

    function loopUi() {
      drivePinLift();
      tickUiSmooth();
      requestAnimationFrame(loopUi);
    }

    window.addEventListener(
      "wheel",
      function (e) {
        if (disableMobilePdpScrollCoupling) return;
        if (isPdpEmbed) refreshMockupUiActive();
        if (isPdpEmbed && !mockupUiActive) return;
        accum += e.deltaY;
        accum = Math.max(0, accum);
      },
      { passive: true }
    );

    /* ── Magnetyczny snap — używa sekcji (host), NIE hero z transformem ── */
    var snapTimer = null;
    var snapCorrecting = false;
    var SNAP_ZONE = 200;
    var snapSection = host || hero.parentElement || hero;

    function getSnapDist() {
      var rect = snapSection.getBoundingClientRect();
      return rect.bottom - window.innerHeight;
    }

    function trySnap() {
      return;
    }

    var lastScrollY = window.scrollY || 0;

    window.addEventListener(
      "scroll",
      function () {
        var y = window.scrollY || 0;

        if (
          !disableMobilePdpScrollCoupling &&
          coarsePointer &&
          (!isPdpEmbed || mockupUiActive)
        ) {
          accum += (y - lastScrollY) * 1.15;
          accum = Math.max(0, accum);
        }
        lastScrollY = y;

        if (false) {
          clearTimeout(snapTimer);
          snapTimer = setTimeout(trySnap, 100);
        }
      },
      { passive: true }
    );

    window.addEventListener("resize", function () {
      lastTx = lastTy = 0;
      if (uiWrap) uiWrap.style.transform = "";
    });

    window.addEventListener("resize", updatePinLayout);
    if (PM_PIN_MQ && PM_PIN_MQ.addEventListener) {
      PM_PIN_MQ.addEventListener("change", updatePinLayout);
    }
    updatePinLayout();

    loopUi();

        function scrollToLab() {
      var target = document.getElementById("giclee-shell");
      if (!target) return;
      var targetSection = target.closest(".shopify-section");
      if (targetSection) {
        targetSection.classList.add("giclee-section-active");
      }
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          var top =
            target.getBoundingClientRect().top +
            (window.pageYOffset || window.scrollY);
          window.scrollTo({ top: top, behavior: "smooth" });
        });
      });
    }

    function updateMockupHoverScale() {
      if (!hero.classList.contains("loaded")) return;
      var baseW = mockupBox.offsetWidth;
      var baseH = mockupBox.offsetHeight;
      if (!baseW || !baseH) return;

      var rect = mockupBox.getBoundingClientRect();
      var cx = rect.left + rect.width / 2;
      var cy = rect.top + rect.height / 2;
      var pad = 20;
      var vh = window.innerHeight || document.documentElement.clientHeight || 0;
      var vw = window.innerWidth || document.documentElement.clientWidth || 0;
      var halfW = baseW / 2;
      var halfH = baseH / 2;
      var maxSx = Math.min(cx - pad, vw - cx - pad) / halfW;
      var maxSy = Math.min(cy - pad, vh - cy - pad) / halfH;
      var fit = Math.min(1, maxSx, maxSy);
      var restScale = getSideScale();
      if (!isFinite(fit) || fit < restScale) fit = restScale;
      mockupBox.style.setProperty("--pm-hover-scale", fit.toFixed(4));
    }

    var scrollAligning = false;
    var mockupHoverIntent = false;
    var suppressLeaveClearUntil = 0;
    var suppressMockupAutoScrollUntil = 0;
    var scrollLayoutTimers = [];
    var hoverPointer = { x: 0, y: 0 };

    function pauseMockupAutoScroll(ms) {
      suppressMockupAutoScrollUntil = Date.now() + (ms || 5000);
      clearMockupHoverScale();
      scrollLayoutTimers.forEach(function (id) {
        clearTimeout(id);
      });
      scrollLayoutTimers = [];
    }

    window.pmPauseMockupAutoScroll = pauseMockupAutoScroll;

    hero.addEventListener("pm-pause-mockup-scroll", function (e) {
      pauseMockupAutoScroll((e.detail && e.detail.ms) || 5000);
    });
    hero.addEventListener("pm-config-add-to-cart", function () {
      pauseMockupAutoScroll(4000);
    });

    function pointerStillOverMockup() {
      var hit = document.elementFromPoint(hoverPointer.x, hoverPointer.y);
      return !!(hit && mockupBox.contains(hit));
    }

    function refreshMockupHoverScale() {
      mockupBox.classList.add("pm-hover-active");
      updateMockupHoverScale();
    }

    var hoverRefreshTimers = [];

    function cancelPendingHoverRefresh() {
      hoverRefreshTimers.forEach(function (id) {
        clearTimeout(id);
      });
      hoverRefreshTimers = [];
    }

    function armHoverRefresh(fn, ms) {
      var id = setTimeout(fn, ms);
      hoverRefreshTimers.push(id);
      return id;
    }

    function clearMockupHoverScale() {
      cancelPendingHoverRefresh();
      mockupHoverIntent = false;
      suppressLeaveClearUntil = 0;
      scrollAligning = false;
      mockupBox.classList.remove("pm-hover-active");
      mockupBox.style.removeProperty("--pm-hover-scale");
    }

    function applyMockupHoverScaleIfHovering() {
      if (!mockupBox.classList.contains("pm-hover-active")) return;
      refreshMockupHoverScale();
    }

    function extendSuppressLeaveClear(ms) {
      suppressLeaveClearUntil = Math.max(
        suppressLeaveClearUntil,
        Date.now() + (ms || 500)
      );
    }

    function tryLeaveMockupNow() {
      if (!mockupHoverIntent) return false;
      if (pointerStillOverMockup() || mockupBox.matches(":hover")) return false;
      clearMockupHoverScale();
      return true;
    }

    function scheduleLeaveCheck() {
      requestAnimationFrame(function () {
        if (scrollAligning && pointerStillOverMockup()) {
          armHoverRefresh(scheduleLeaveCheck, 40);
          return;
        }
        tryLeaveMockupNow();
      });
    }

    function unlockPageScrollForCart() {
      document.documentElement.removeAttribute("scroll-lock");
      document.documentElement.style.overflow = "";
      document.body.style.overflow = "";
      document.body.style.position = "";
      document.body.style.top = "";
      document.body.style.width = "";
      document.body.style.paddingRight = "";
    }

    function forcePageScrollTop(instant) {
      unlockPageScrollForCart();
      var scrollTargets = [
        document.documentElement,
        document.body,
        document.scrollingElement,
      ];
      scrollTargets.forEach(function (el) {
        if (!el) return;
        el.scrollTop = 0;
        el.scrollLeft = 0;
      });
      window.scrollTo({
        top: 0,
        left: 0,
        behavior: instant ? "instant" : "smooth",
      });
      var header = document.getElementById("header-group");
      if (header && typeof header.scrollIntoView === "function") {
        header.scrollIntoView({
          block: "start",
          behavior: instant ? "instant" : "smooth",
        });
      }
    }

    function pageScrollYNow() {
      return (
        window.pageYOffset ||
        document.documentElement.scrollTop ||
        document.body.scrollTop ||
        0
      );
    }

    function pmScrollPageToTopForCart() {
      pauseMockupAutoScroll(4000);
      clearMockupHoverScale();
      mockupHoverIntent = false;
      window.pmCartScrollLock = true;

      if (!isPdpEmbed) {
        hero.style.setProperty("--pm-lift", "0px");
      }

      return new Promise(function (resolve) {
        var minMs = 520;
        var maxMs = 1500;
        var started = Date.now();

        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            var startY = pageScrollYNow();

            function finish() {
              forcePageScrollTop(true);
              window.pmCartScrollLock = false;
              var elapsed = Date.now() - started;
              var wait = Math.max(0, minMs - elapsed);
              setTimeout(resolve, wait);
            }

            if (startY <= 2) {
              forcePageScrollTop(true);
              setTimeout(function () {
                window.pmCartScrollLock = false;
                resolve();
              }, minMs);
              return;
            }

            forcePageScrollTop(false);

            var done = false;
            function complete() {
              if (done) return;
              done = true;
              document.removeEventListener("scrollend", onScrollEnd, true);
              clearTimeout(maxTimer);
              clearInterval(pollTimer);
              finish();
            }

            function onScrollEnd() {
              if (pageScrollYNow() <= 2 && Date.now() - started >= minMs) {
                complete();
              }
            }

            document.addEventListener("scrollend", onScrollEnd, true);
            var maxTimer = setTimeout(complete, maxMs);
            var pollTimer = setInterval(function () {
              if (pageScrollYNow() <= 2 && Date.now() - started >= minMs) {
                complete();
              }
            }, 40);
          });
        });
      });
    }

    window.pmScrollPageToTopForCart = pmScrollPageToTopForCart;

    function scrollMockupToViewportCenter() {
      if (window.pmCartScrollLock) return;
      if (Date.now() < suppressMockupAutoScrollUntil) return;
      if (!wrapper || !hero.classList.contains("loaded")) return;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          var rect = mockupBox.getBoundingClientRect();
          var vh =
            window.innerHeight || document.documentElement.clientHeight || 1;
          var scrollY = window.pageYOffset || window.scrollY || 0;
          var centerOffset = rect.top + rect.height / 2 - vh / 2;
          var didScroll = false;
          var scrolledDown = false;

          if (Math.abs(centerOffset) <= 24) return;

          scrolledDown = centerOffset > 0;
          var targetTop = scrollY + centerOffset;
          var maxScroll = Math.max(
            0,
            (document.documentElement.scrollHeight || 0) - vh
          );
          targetTop = Math.max(0, Math.min(maxScroll, Math.round(targetTop)));

          if (centerOffset < 0 && targetTop === 0 && rect.top >= 40) return;

          if (Math.abs(targetTop - scrollY) < 10) return;

          scrollAligning = true;
          clearTimeout(snapTimer);
          snapCorrecting = true;
          var se = document.scrollingElement || document.documentElement;
          se.scrollTop = targetTop;
          didScroll = true;
          setTimeout(function () {
            snapCorrecting = false;
          }, 400);

          function finishHoverScale() {
            if (!mockupHoverIntent) return;
            extendSuppressLeaveClear(scrolledDown ? 500 : 200);
            refreshMockupHoverScale();
            requestAnimationFrame(function () {
              if (!mockupHoverIntent) return;
              refreshMockupHoverScale();
              armHoverRefresh(function () {
                if (!mockupHoverIntent) return;
                refreshMockupHoverScale();
                scrollAligning = false;
                if (scrolledDown && mockupHoverIntent) {
                  armHoverRefresh(refreshMockupHoverScale, 60);
                  armHoverRefresh(refreshMockupHoverScale, 160);
                  extendSuppressLeaveClear(300);
                }
              }, 80);
            });
          }

          if (didScroll) {
            scrollAligning = true;
            requestAnimationFrame(function () {
              requestAnimationFrame(finishHoverScale);
            });
          } else {
            finishHoverScale();
          }
          schedulePmMockupCenterUiSync();
        });
      });
    }

    function scheduleScrollAfterLayout() {
      if (window.pmCartScrollLock) return;
      if (Date.now() < suppressMockupAutoScrollUntil) return;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          scrollMockupToViewportCenter();
          schedulePmMockupCenterUiSync();
          scrollLayoutTimers.push(setTimeout(scrollMockupToViewportCenter, 150));
          scrollLayoutTimers.push(setTimeout(schedulePmMockupCenterUiSync, 150));
          scrollLayoutTimers.push(setTimeout(scrollMockupToViewportCenter, 450));
          scrollLayoutTimers.push(setTimeout(schedulePmMockupCenterUiSync, 450));
          scrollLayoutTimers.push(setTimeout(scrollMockupToViewportCenter, 950));
          scrollLayoutTimers.push(setTimeout(schedulePmMockupCenterUiSync, 950));
        });
      });
    }

    function onMockupEnter(e) {
      if (window.pmCartScrollLock) return;
      if (Date.now() < suppressMockupAutoScrollUntil) return;
      hoverPointer.x = e.clientX;
      hoverPointer.y = e.clientY;
      mockupHoverIntent = true;
      extendSuppressLeaveClear(1200);
      scrollMockupToViewportCenter();
      refreshMockupHoverScale();
    }

    function onMockupMove(e) {
      hoverPointer.x = e.clientX;
      hoverPointer.y = e.clientY;
      if (mockupHoverIntent && !pointerStillOverMockup()) tryLeaveMockupNow();
    }

    function onMockupLeave(e) {
      hoverPointer.x = e.clientX;
      hoverPointer.y = e.clientY;
      scheduleLeaveCheck();
    }

    mockupBox.addEventListener("mouseenter", onMockupEnter);
    mockupBox.addEventListener("mousemove", onMockupMove, { passive: true });
    mockupBox.addEventListener("mouseleave", onMockupLeave);

    document.addEventListener(
      "pointermove",
      function (e) {
        hoverPointer.x = e.clientX;
        hoverPointer.y = e.clientY;
        if (!mockupHoverIntent) return;
        if (pointerStillOverMockup() || mockupBox.matches(":hover")) return;
        tryLeaveMockupNow();
      },
      { passive: true }
    );
    window.addEventListener("resize", function () {
      if (mockupBox.classList.contains("pm-hover-active")) {
        scrollMockupToViewportCenter();
      }
    });

    var reuploadBtn = document.getElementById("pm-reupload");
    var exportBtn = document.getElementById("pm-export-jpg");
    if (reuploadBtn && upload) {
      reuploadBtn.addEventListener("click", function () {
        upload.click();
      });
    }
    if (exportBtn) {
      exportBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        exportMockupJpeg();
      });
    }

    if (zoomInBtn) {
      zoomInBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        stepZoom(1);
      });
    }

    if (zoomOutBtn) {
      zoomOutBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        stepZoom(-1);
      });
    }

    if (zoomSlider) {
      zoomSlider.addEventListener("pointerdown", function () {
        sliderDragging = true;
        cancelZoomAnim();
      });
      zoomSlider.addEventListener("pointerup", endSliderDrag);
      zoomSlider.addEventListener("pointercancel", endSliderDrag);
      window.addEventListener("pointerup", endSliderDrag);
      zoomSlider.addEventListener("input", applySliderZoomImmediate);
      zoomSlider.addEventListener("change", function () {
        endSliderDrag();
        applySliderZoomImmediate();
      });
    }

    var ctaBtn = document.getElementById("pm-cta");
    if (ctaBtn) {
      ctaBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        scrollToLab();
      });
    }

    window.pmHasMockupImage = function () {
      return !!(img && sourceFile);
    };

    window.pmPrepareOrderUpload = function (frameConfig) {
      var apiUrl = (hero.getAttribute("data-pm-upload-api") || "").trim();
      if (!apiUrl) {
        return Promise.reject(new Error("Brak URL uploadu w ustawieniach motywu"));
      }
      if (!img || !sourceFile) {
        return Promise.reject(new Error("Najpierw wgraj zdjęcie"));
      }
      if (sourceFile.size > 50 * 1024 * 1024) {
        return Promise.reject(new Error("Plik za duży (max 50 MB)"));
      }

      function finishUploadForm(
        fd,
        previewBlob,
        originalFullBlob,
        crop,
        frameConfig,
        stagedFlag
      ) {
        if (originalFullBlob && originalFullBlob.size) {
          fd.append("original_full", originalFullBlob, "original-full.jpg");
        }
        fd.append("preview", previewBlob, "mockup-preview.jpg");
        if (crop) fd.append("crop", JSON.stringify(crop));
        if (frameConfig) fd.append("config", JSON.stringify(frameConfig));
        fd.append(
          "meta_extra",
          JSON.stringify({
            dimensions: {
              decodeWidth: fullDecode.w || sourcePixelWidth(),
              decodeHeight: fullDecode.h || sourcePixelHeight(),
              displayWidth: sourcePixelWidth(),
              displayHeight: sourcePixelHeight(),
              originalBytes: sourceFile.size,
              originalType: sourceFile.type || null,
              originalName: sourceFile.name || null,
              stagedFromMobile: !!stagedFlag,
              coarseMobile: isCoarseMobile(),
            },
          })
        );

        return fetch(apiUrl, { method: "POST", body: fd }).then(function (res) {
          return res.json().then(function (data) {
            if (!res.ok || !data || !data.uploadId) {
              throw new Error(
                (data && data.error) || "Upload nie powiódł się (" + res.status + ")"
              );
            }
            return data;
          });
        });
      }

      return probeFullDecodeFromFile(sourceFile)
        .then(function () {
          return stageRawUploadOnMobile();
        })
        .then(function (stagedId) {
          var crop = getCropPayload(frameConfig);
          return Promise.all([
            buildPreviewBlobPromise(),
            buildOriginalFullBlobPromise(),
          ]).then(function (parts) {
            var previewBlob = parts[0];
            var originalFullBlob = parts[1];
            var fd = new FormData();
            var useStaged = stagedId || stagedUploadId;
            if (useStaged) {
              fd.append("upload_id", useStaged);
              fd.append("complete_staged", "1");
              return finishUploadForm(
                fd,
                previewBlob,
                originalFullBlob,
                crop,
                frameConfig,
                true
              );
            }
            return readFileAsRawBlob(sourceFile).then(function (rawBlob) {
              fd.append("original", rawBlob, sourceFile.name || "photo.jpg");
              return finishUploadForm(
                fd,
                previewBlob,
                originalFullBlob,
                crop,
                frameConfig,
                false
              );
            });
          });
        });
    };
  })();
