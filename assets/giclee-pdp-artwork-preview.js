/**
 * PDP nowy-szblon-produktu: wysuwany podgląd HD (zoom R2) między opisem a SZCZEGÓŁY.
 */
(function () {
  function gicleeUi(key, fallback) {
    var bag = window.__gicleeI18n || {};
    return bag[key] || fallback;
  }

  function boot() {
    // v3 wykluczony: opis stronicowany (giclee-product-story) bez przycisku podgladu.
    var main = document.querySelector(
      'main[data-template="product.nowy-szblon-produktu"], main[data-template="product.szablon-produktu-v2"]'
    );
    if (!main) return;

    var row = main.querySelector(
      '.product-description-below table tbody tr:last-child'
    );
    var zoomRoot = main.querySelector('[data-giclee-zoom]');
    if (!row || !zoomRoot) return;

    var midCell = ensureMidCell(row);
    if (!midCell || midCell.dataset.gicleeArtworkInit === '1') return;
    midCell.dataset.gicleeArtworkInit = '1';
    midCell.classList.add('giclee-pdp-artwork-mid');
    row.classList.add('giclee-pdp-artwork-row');

    var toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'giclee-pdp-artwork-toggle';
    toggleBtn.textContent = gicleeUi('pdp_preview_show', 'Podgląd obrazu');

    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'giclee-pdp-artwork-close';
    closeBtn.textContent = gicleeUi('pdp_preview_hide', 'Schowaj podgląd');
    closeBtn.hidden = true;

    var panel = document.createElement('div');
    panel.className = 'giclee-pdp-artwork-panel';
    panel.setAttribute('aria-hidden', 'true');

    var panelInner = document.createElement('div');
    panelInner.className = 'giclee-pdp-artwork-panel__inner';

    var viewport = document.createElement('div');
    viewport.className = 'giclee-pdp-artwork-panel__viewport';

    var slot = document.createElement('div');
    slot.className = 'giclee-pdp-artwork-slot';

    panelInner.appendChild(closeBtn);
    panelInner.appendChild(viewport);
    panel.appendChild(panelInner);
    slot.appendChild(toggleBtn);
    slot.appendChild(panel);
    midCell.textContent = '';
    midCell.appendChild(slot);

    function moveZoomToPanel() {
      if (zoomRoot.classList.contains('giclee-product-zoom--relocated')) return;
      viewport.appendChild(zoomRoot);
      zoomRoot.classList.add('giclee-product-zoom--relocated');
    }

    function relayoutZoom() {
      zoomRoot.dispatchEvent(
        new CustomEvent('giclee-zoom-relayout', { bubbles: false })
      );
    }

    function setOpen(open) {
      if (open) moveZoomToPanel();
      row.classList.toggle('is-artwork-open', open);
      closeBtn.hidden = !open;
      toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      panel.setAttribute('aria-hidden', open ? 'false' : 'true');
      document.body.classList.toggle('giclee-pdp-artwork-open', open);
      relayoutZoom();
      window.setTimeout(relayoutZoom, 80);
      window.setTimeout(relayoutZoom, 560);
    }

    toggleBtn.addEventListener('click', function () {
      setOpen(true);
    });

    closeBtn.addEventListener('click', function () {
      setOpen(false);
    });

    window.addEventListener('resize', function () {
      if (row.classList.contains('is-artwork-open')) relayoutZoom();
    });
  }

  function ensureMidCell(row) {
    var cells = row.querySelectorAll('td');
    if (cells.length >= 3) return cells[1];
    if (cells.length === 2) {
      var mid = document.createElement('td');
      mid.className = 'giclee-pdp-artwork-mid';
      row.insertBefore(mid, cells[1]);
      return mid;
    }
    return null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
