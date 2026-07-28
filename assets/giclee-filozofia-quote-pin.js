/* Filozofia marki — pin cytatu 0.6vh, potem portal na tym samym ekranie (bez fade cytatu). */
(function () {
  'use strict';

  if (window.__GICLEE_FILOZOFIA_QUOTE_PIN__) return;
  window.__GICLEE_FILOZOFIA_QUOTE_PIN__ = true;

  if (!document.body.classList.contains('template-page-filozofia-marki')) return;

  var main = document.getElementById('MainContent');
  if (!main) return;

  var topDivider = main.querySelector('.shopify-section[id$="__divider_Utf3HQ"]');
  var quoteSection = main.querySelector('.shopify-section[id$="__section_tAj94h"]');
  var bottomDivider = main.querySelector('.shopify-section[id$="__divider_H4ahef"]');
  var wrotaRoot = main.querySelector('[data-fm-portal-root]');
  var wrotaSection = wrotaRoot
    ? wrotaRoot.closest('.shopify-section')
    : main.querySelector('.shopify-section[id$="__media_with_content_Wrota"]');

  if (!topDivider || !quoteSection || !bottomDivider) return;
  if (topDivider.closest('.giclee-fm-quote-pin-track')) return;

  var track = document.createElement('div');
  track.className = 'giclee-fm-quote-pin-track';

  var sticky = document.createElement('div');
  sticky.className = 'giclee-fm-quote-pin-sticky';

  var quoteLayer = document.createElement('div');
  quoteLayer.className = 'giclee-fm-quote-layer';

  var portalHost = document.createElement('div');
  portalHost.className = 'giclee-fm-portal-host';
  portalHost.setAttribute('aria-hidden', 'true');
  portalHost.style.setProperty('--giclee-fm-portal-inset', '50%');

  var parent = topDivider.parentNode;
  if (!parent) return;

  parent.insertBefore(track, topDivider);

  var node = topDivider;
  while (node) {
    var next = node.nextElementSibling;
    quoteLayer.appendChild(node);
    if (node === bottomDivider) break;
    node = next;
  }

  sticky.appendChild(quoteLayer);
  sticky.appendChild(portalHost);
  track.appendChild(sticky);

  if (wrotaSection instanceof HTMLElement) {
    wrotaSection.classList.add('giclee-fm-wrota-section');
  }

  var stage =
    wrotaRoot instanceof HTMLElement
      ? wrotaRoot.querySelector('.media-block__scroll-stage[data-fm-portal]')
      : null;

  var reducedMotion = !!(
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  var ticking = false;
  var hosted = false;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function easeOutQuad(t) {
    return 1 - (1 - t) * (1 - t);
  }

  function readCssNumber(el, name, fallback) {
    var raw = window.getComputedStyle(el).getPropertyValue(name).trim();
    var n = Number.parseFloat(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  /**
   * Stage musi wyjść z .media-block--scroll-scrub (contain: paint),
   * inaczej position:fixed jest uwięzione poniżej foldu.
   * Czekamy na init Film-scroll, żeby zdążył znaleźć video w root.
   */
  function hostStage() {
    if (hosted || !(stage instanceof HTMLElement)) return false;
    if (stage.parentNode === portalHost) {
      hosted = true;
      return true;
    }

    stage.classList.add('giclee-fm-portal-on-quote');
    portalHost.appendChild(stage);
    hosted = true;
    document.body.classList.add('giclee-fm-quote-curtain-ready');
    return true;
  }

  function waitForScrubThenHost() {
    if (!(stage instanceof HTMLElement)) return;
    var tries = 0;
    var timer = window.setInterval(function () {
      tries += 1;
      var scrubReady =
        wrotaRoot instanceof HTMLElement &&
        (wrotaRoot.classList.contains('is-scroll-frame-ready') ||
          wrotaRoot.querySelector('[data-scroll-native-video], [data-scroll-frame-canvas]'));
      // Po kilku tickach i tak hostujemy — clip-path musi działać nawet bez video ready.
      if ((scrubReady && tries >= 2) || tries >= 60) {
        window.clearInterval(timer);
        hostStage();
        update();
      }
    }, 50);
  }

  function phaseProgress() {
    var viewport = window.innerHeight || 1;
    var pinDuration = readCssNumber(track, '--fm-quote-pin-duration', 0.6) * viewport;
    var portalDuration =
      readCssNumber(track, '--fm-quote-portal-duration', 0.5) * viewport;

    var trackRect = track.getBoundingClientRect();
    var scrolled = clamp(-trackRect.top, 0, Math.max(1, track.offsetHeight - viewport));

    if (scrolled <= pinDuration) {
      return { pin: clamp(scrolled / Math.max(1, pinDuration), 0, 1), portal: 0 };
    }

    var afterPin = scrolled - pinDuration;
    var portal = clamp(afterPin / Math.max(1, portalDuration), 0, 1);

    if (wrotaRoot instanceof HTMLElement && portal < 1) {
      var wrotaRect = wrotaRoot.getBoundingClientRect();
      var wrotaTravel = Math.max(1, wrotaRoot.offsetHeight - viewport);
      var wrotaP = clamp(-wrotaRect.top / wrotaTravel, 0, 1);
      if (wrotaP > 0) portal = 1;
    }

    return { pin: 1, portal: portal };
  }

  function sceneActive() {
    var viewport = window.innerHeight || 1;
    var trackRect = track.getBoundingClientRect();
    if (!(wrotaRoot instanceof HTMLElement)) {
      return trackRect.top < viewport && trackRect.bottom > 0;
    }
    var wrotaRect = wrotaRoot.getBoundingClientRect();
    return trackRect.top <= viewport && wrotaRect.bottom > 0;
  }

  function applyScene(phases) {
    var local = reducedMotion ? 1 : easeOutQuad(clamp(phases.portal, 0, 1));
    var inset = 50 * (1 - local);

    portalHost.style.setProperty('--giclee-fm-portal-inset', inset.toFixed(2) + '%');
    portalHost.setAttribute('data-fm-portal-progress', local.toFixed(3));
    portalHost.setAttribute('data-fm-portal-open', local >= 0.999 ? 'true' : 'false');
    portalHost.setAttribute('data-fm-quote-pin', phases.pin.toFixed(3));

    if (stage instanceof HTMLElement) {
      stage.style.setProperty('--giclee-fm-portal-inset', inset.toFixed(2) + '%');
      stage.setAttribute('data-fm-portal-progress', local.toFixed(3));
      stage.setAttribute('data-fm-portal-open', local >= 0.999 ? 'true' : 'false');
    }

    // Cytat BEZ fade — portal ma wyższy z-index i zasłania go przy otwarciu.
    sticky.style.opacity = '1';
    sticky.style.setProperty('--fm-quote-opacity', '1');
    sticky.classList.remove('is-fm-quote-gone');
    sticky.classList.toggle('is-fm-quote-pinned', phases.pin > 0);

    var active = reducedMotion || sceneActive();
    portalHost.classList.toggle('is-fm-portal-overlay', active);
    document.body.classList.toggle('giclee-fm-curtain-active', active);
    document.body.classList.toggle('giclee-fm-curtain-open', local > 0.02);
  }

  function update() {
    ticking = false;
    applyScene(phaseProgress());
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(update);
  }

  waitForScrubThenHost();

  if (reducedMotion) {
    hostStage();
    applyScene({ pin: 1, portal: 1 });
    return;
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  update();
})();
