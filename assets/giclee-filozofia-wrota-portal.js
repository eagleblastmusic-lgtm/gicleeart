/* Filozofia marki — portal Wrota: fallback gdy kurtyna nie jest na sticky cytatu. */
(function () {
  'use strict';

  if (window.__GICLEE_FILOZOFIA_WROTA_PORTAL__) return;
  window.__GICLEE_FILOZOFIA_WROTA_PORTAL__ = true;

  if (!document.body.classList.contains('template-page-filozofia-marki')) return;

  var PORTAL_END = 0.22;
  var reducedMotion = !!(
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function easeOutQuad(t) {
    return 1 - (1 - t) * (1 - t);
  }

  function applyInset(portal, progress) {
    if (!(portal instanceof HTMLElement)) return;
    // quote-pin.js steruje kurtyną na ekranie cytatu.
    if (portal.classList.contains('giclee-fm-portal-on-quote')) return;
    var local = reducedMotion ? 1 : easeOutQuad(clamp(progress / PORTAL_END, 0, 1));
    var inset = 50 * (1 - local);
    portal.style.setProperty('--giclee-fm-portal-inset', inset.toFixed(2) + '%');
    portal.setAttribute('data-fm-portal-progress', local.toFixed(3));
    portal.setAttribute('data-fm-portal-open', local >= 0.999 ? 'true' : 'false');
  }

  function bindPortal(root) {
    if (!(root instanceof HTMLElement)) return;
    if (root.dataset.fmPortalBound === '1') return;
    var portal = root.querySelector('[data-fm-portal]');
    if (!(portal instanceof HTMLElement)) return;
    if (portal.classList.contains('giclee-fm-portal-on-quote')) {
      root.dataset.fmPortalBound = '1';
      return;
    }
    root.dataset.fmPortalBound = '1';

    function tryRegister() {
      var api = window.GicleeScrollFrameCanvas;
      if (!api || typeof api.registerElement !== 'function') return false;
      try {
        api.registerElement(root, {
          id: 'fm-wrota-portal',
          last: -1,
          render: function (context) {
            var progress = context && typeof context.renderedProgress === 'number'
              ? context.renderedProgress
              : 0;
            if (Math.abs(progress - this.last) < 0.0005) return;
            this.last = progress;
            applyInset(portal, progress);
          },
          destroy: function () {},
        });
        return true;
      } catch (_error) {
        return false;
      }
    }

    if (!tryRegister()) {
      var attempts = 0;
      var timer = window.setInterval(function () {
        attempts += 1;
        if (tryRegister() || attempts >= 100) window.clearInterval(timer);
      }, 50);
    }
  }

  function boot() {
    document.querySelectorAll('[data-fm-portal-root]').forEach(bindPortal);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
