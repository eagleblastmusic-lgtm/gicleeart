/* Giclée Catalog — konfiguracja efektu aktywnego artysty.
 * Bez zewnętrznych zależności i bez globalnego stanu testowego.
 */
(function () {
  'use strict';

  var ALLOWED_EFFECTS = {
    classic: true,
    curatorial_glow: true,
    depth_of_field: true,
    museum_marker: true,
    preview_focus: true
  };
  var DEFAULT_EFFECT = 'classic';
  var INIT_ATTRIBUTE = 'data-giclee-artist-effects-init';

  function normalizeEffect(value) {
    var effect = String(value || '').trim();
    return ALLOWED_EFFECTS[effect] ? effect : DEFAULT_EFFECT;
  }

  function configuredEffect() {
    var config = window.catalogSubmenuConfig;
    var list = config && config.list;
    return normalizeEffect(list && list.artist_hover_effect);
  }

  function ensureColumnMarkers(panel) {
    panel.querySelectorAll('.giclee-artists-col').forEach(function (column) {
      if (column.querySelector(':scope > .giclee-catalog-margin-marker')) return;
      var marker = document.createElement('span');
      marker.className = 'giclee-catalog-margin-marker';
      marker.setAttribute('aria-hidden', 'true');
      column.prepend(marker);
    });
  }

  function hideMarkers(panel) {
    panel.querySelectorAll('.giclee-catalog-margin-marker.is-visible').forEach(function (marker) {
      marker.classList.remove('is-visible');
    });
  }

  function markerForLink(link) {
    var column = link && link.closest('.giclee-artists-col');
    return column && column.querySelector(':scope > .giclee-catalog-margin-marker');
  }

  function moveMarker(panel, link) {
    if (panel.dataset.artistHoverEffect !== 'museum_marker' || !link) return;
    ensureColumnMarkers(panel);

    var marker = markerForLink(link);
    if (!marker) return;

    hideMarkers(panel);
    var markerHeight = 18;
    var y = link.offsetTop + Math.max(0, (link.offsetHeight - markerHeight) / 2);
    marker.style.setProperty('--giclee-marker-y', y + 'px');
    marker.classList.add('is-visible');
  }

  function setKeyboardActive(list, link) {
    list.querySelectorAll('a.is-active').forEach(function (other) {
      if (other !== link) other.classList.remove('is-active');
    });
    link.classList.add('is-active');
  }

  function currentInteractiveLink(list) {
    var focused = document.activeElement;
    if (focused && focused.matches && focused.matches('#giclee-artists-list a')) {
      return focused;
    }
    return list.querySelector('a:hover, a.is-active');
  }

  function initPanel(panel) {
    if (!panel || panel.getAttribute(INIT_ATTRIBUTE) === '1') return;

    panel.setAttribute(INIT_ATTRIBUTE, '1');
    panel.dataset.artistHoverEffect = configuredEffect();

    var list = panel.querySelector('#giclee-artists-list');
    if (!list) return;

    ensureColumnMarkers(panel);

    list.addEventListener('pointerover', function (event) {
      var link = event.target.closest && event.target.closest('a');
      if (!link || !list.contains(link)) return;
      moveMarker(panel, link);
    });

    list.addEventListener('pointerleave', function () {
      hideMarkers(panel);
    });

    list.addEventListener('focusin', function (event) {
      var link = event.target.closest && event.target.closest('a');
      if (!link || !list.contains(link)) return;
      setKeyboardActive(list, link);
      moveMarker(panel, link);
    });

    list.addEventListener('focusout', function (event) {
      if (event.relatedTarget && list.contains(event.relatedTarget)) return;
      hideMarkers(panel);
    });

    panel.addEventListener('giclee:catalog-effect-refresh', function () {
      panel.dataset.artistHoverEffect = configuredEffect();
      ensureColumnMarkers(panel);
      var active = currentInteractiveLink(list);
      if (active) moveMarker(panel, active);
    });
  }

  function scanForPanels(root) {
    if (root && root.nodeType === 1 && root.id === 'giclee-catalog-panel') {
      initPanel(root);
    }
    document.querySelectorAll('#giclee-catalog-panel').forEach(initPanel);
  }

  var scanQueued = false;
  function queueScan(root) {
    if (scanQueued) return;
    scanQueued = true;
    requestAnimationFrame(function () {
      scanQueued = false;
      scanForPanels(root);
    });
  }

  var observer = new MutationObserver(function (mutations) {
    for (var i = 0; i < mutations.length; i += 1) {
      if (mutations[i].addedNodes && mutations[i].addedNodes.length) {
        queueScan(mutations[i].target);
        return;
      }
    }
  });

  function boot() {
    scanForPanels(document);
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  var resizeQueued = false;
  window.addEventListener('resize', function () {
    if (resizeQueued) return;
    resizeQueued = true;
    requestAnimationFrame(function () {
      resizeQueued = false;
      document.querySelectorAll('#giclee-catalog-panel').forEach(function (panel) {
        var list = panel.querySelector('#giclee-artists-list');
        var active = list && currentInteractiveLink(list);
        if (active) moveMarker(panel, active);
      });
    });
  }, { passive: true });
})();
