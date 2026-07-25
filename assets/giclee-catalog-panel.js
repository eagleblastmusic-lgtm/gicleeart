/* Giclée Catalog — panel submenu, konfiguracja, efekty artystów i kolejka podglądów. */
const imageCache = {};
let currentPreviewSrc = null;
let activePreviewHandle = null;

// Konfiguracja panelu Katalog — edytowana w GicleeApp (Komponenty/submenukatalog).
// Źródło: assets/giclee-catalog-submenu-config.json
var DEFAULT_CATALOG_SUBMENU_CONFIG = {
  version: 1,
  list: {
    columns: 3,
    show_header: true,
    hidden_artists_text: [
      'francois-boucher',
      'william-bradford',
      'paul-fisher',
      'jean-auguste-ingres',
      'peder-severin-kryer',
      'edmund-blair-leighton',
      'charles-sillem-lidderdale',
      'giordano-luca',
      'anders-andersen-lundby',
      'johan-thomas-lundbye',
      'anton-melbye',
      'jean-francois-millet',
      'claude-monet',
      'thomas-moran',
      'bartolome-esteban-murillo',
      'harmenszoon-van-rijn-rembrandt',
      'guido-reni',
      'aguste-renoir',
      'willem-roelofs',
      'dante-gabriel-rossetti',
      'rafael-santi',
      'alfred-sisley',
      'tycjan-tiziano-vecellio',
      'claude-joseph-vernet'
    ].join('\n')
  },
  animation: {
    open_reveal_delay_ms: 120,
    max_cascade_ms: 2200,
    min_interval_ms: 20,
    max_interval_ms: 92,
    interval_curve: 1.75,
    link_transition_ms: 220
  },
  appearance: {
    preview_graphics_variant: 'v1',
    preview_width_px: 560,
    panel_max_height_vh: 82
  }
};

var catalogSubmenuConfig = DEFAULT_CATALOG_SUBMENU_CONFIG;
var HIDDEN_CATALOG_ARTISTS = new Set();
var CATALOG_LIST_COLUMNS = 3;
var CATALOG_SHOW_HEADER = true;
var CATALOG_PREVIEW_GRAPHICS_VARIANT = 'v1';
var catalogSubmenuConfigLoaded = false;
var catalogPanelScript = document.currentScript;
var catalogSubmenuConfigUrl = catalogPanelScript && catalogPanelScript.dataset
  ? (catalogPanelScript.dataset.configUrl || '')
  : '';

function _catalogCfgNum(value, fallback) {
  var n = Number(value);
  return isFinite(n) ? n : fallback;
}

function _catalogHiddenHandlesFromText(text) {
  return String(text || '')
    .split(/[\n,]+/)
    .map(function(handle) { return handle.replace(/#.*/, '').trim().toLowerCase(); })
    .filter(Boolean);
}

function _catalogPreviewGraphicsVariant(value) {
  return String(value || '').trim().toLowerCase() === 'v2' ? 'v2' : 'v1';
}

function applyCatalogPreviewGraphicsVariant() {
  var panel = document.getElementById('giclee-catalog-panel');
  if (panel) {
    panel.setAttribute('data-preview-graphics-variant', CATALOG_PREVIEW_GRAPHICS_VARIANT);
  }
}

function applyCatalogSubmenuConfig(cfg) {
  var merged = DEFAULT_CATALOG_SUBMENU_CONFIG;
  if (cfg && typeof cfg === 'object') {
    merged = {
      version: cfg.version || DEFAULT_CATALOG_SUBMENU_CONFIG.version,
      list: Object.assign({}, DEFAULT_CATALOG_SUBMENU_CONFIG.list, cfg.list || {}),
      animation: Object.assign({}, DEFAULT_CATALOG_SUBMENU_CONFIG.animation, cfg.animation || {}),
      appearance: Object.assign({}, DEFAULT_CATALOG_SUBMENU_CONFIG.appearance, cfg.appearance || {})
    };
  }

  catalogSubmenuConfig = merged;
  CATALOG_LIST_COLUMNS = Math.max(1, Math.min(5, Math.round(_catalogCfgNum(merged.list.columns, 3))));
  CATALOG_SHOW_HEADER = merged.list.show_header !== false;
  HIDDEN_CATALOG_ARTISTS = new Set(_catalogHiddenHandlesFromText(merged.list.hidden_artists_text));
  CATALOG_PREVIEW_GRAPHICS_VARIANT = _catalogPreviewGraphicsVariant(
    merged.appearance.preview_graphics_variant
  );
  applyCatalogPreviewGraphicsVariant();

  var previewWidth = Math.max(320, Math.round(_catalogCfgNum(merged.appearance.preview_width_px, 560)));
  var panelMaxHeight = Math.max(40, Math.min(100, Math.round(_catalogCfgNum(merged.appearance.panel_max_height_vh, 82))));
  document.documentElement.style.setProperty('--giclee-catalog-preview-width', previewWidth + 'px');
  document.documentElement.style.setProperty('--giclee-catalog-panel-max-height', panelMaxHeight + 'vh');
  document.documentElement.style.setProperty('--giclee-catalog-list-columns', String(CATALOG_LIST_COLUMNS));
}

function _parseCatalogSubmenuConfigText(raw) {
  if (!raw) return null;
  var text = String(raw).replace(/^\s+/, '');
  if (text.indexOf('/*') === 0) {
    var end = text.indexOf('*/');
    if (end >= 0) text = text.slice(end + 2).replace(/^\s+/, '');
  }
  try {
    return JSON.parse(text);
  } catch (err) {
    return null;
  }
}

function loadCatalogSubmenuConfig(callback) {
  if (!catalogSubmenuConfigUrl) {
    applyCatalogSubmenuConfig(null);
    catalogSubmenuConfigLoaded = true;
    if (callback) callback();
    return;
  }
  fetch(catalogSubmenuConfigUrl, { credentials: 'same-origin' })
    .then(function(response) { return response.ok ? response.text() : null; })
    .catch(function() { return null; })
    .then(function(raw) {
      applyCatalogSubmenuConfig(_parseCatalogSubmenuConfigText(raw));
      catalogSubmenuConfigLoaded = true;
      if (callback) callback();
    });
}

applyCatalogSubmenuConfig(null);

function shopifyUrlRoot() {
  var root = (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || '/';
  if (root.length && root.charAt(root.length - 1) !== '/') root += '/';
  return root;
}

function getCollectionHandleFromHref(href) {
  if (!href) return null;
  try {
    const path = new URL(href, window.location.origin).pathname;
    const match = path.match(/\/collections\/([^/]+)/i);
    return match ? match[1].toLowerCase() : null;
  } catch (err) {
    const parts = String(href).split('/collections/');
    if (!parts[1]) return null;
    return parts[1].split('?')[0].split('#')[0].split('/')[0].toLowerCase();
  }
}

function collectionProductsJsonUrl(handle) {
  return shopifyUrlRoot() + 'collections/' + encodeURIComponent(handle) + '/products.json?limit=1';
}

function isCatalogArtistHidden(handle) {
  return !!handle && HIDDEN_CATALOG_ARTISTS.has(String(handle).toLowerCase());
}

function applyHiddenCatalogArtistsToNavigation() {
  document.querySelectorAll('.menu-drawer a[href*="/collections/"]').forEach(function(link) {
    const handle = getCollectionHandleFromHref(link.getAttribute('href'));
    if (!isCatalogArtistHidden(handle)) return;
    const item = link.closest('.menu-drawer__list-item');
    if (item) {
      item.style.display = 'none';
      item.setAttribute('aria-hidden', 'true');
    } else {
      link.style.display = 'none';
      link.setAttribute('aria-hidden', 'true');
    }
  });
}

var CATALOG_SURNAME_PARTICLES = {
  van: 1, von: 1, de: 1, da: 1, del: 1, della: 1, di: 1, du: 1,
  ten: 1, ter: 1, den: 1, der: 1, af: 1, av: 1, la: 1, le: 1
};

function titleCaseWords(text) {
  return String(text || '').split(/\s+/).filter(Boolean).map(function(w) {
    return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase();
  }).join(' ');
}

function normalizeCatalogArtistTitle(raw) {
  var title = String(raw || '').trim();
  if (title.indexOf(', ') === -1) return { surname: title, given: '' };
  var comma = title.indexOf(', ');
  var surname = title.slice(0, comma).trim();
  var given = title.slice(comma + 2).trim();
  var givenWords = given.split(/\s+/).filter(Boolean);
  if (givenWords.length > 1) {
    var last = givenWords[givenWords.length - 1].toLowerCase().replace(/\.$/, '');
    if (CATALOG_SURNAME_PARTICLES[last]) {
      var particle = givenWords[givenWords.length - 1];
      given = givenWords.slice(0, -1).join(' ');
      surname = (particle + ' ' + surname).trim();
    }
  }
  return { surname: titleCaseWords(surname), given: titleCaseWords(given) };
}

function formatCatalogArtistName(raw) {
  var parts = normalizeCatalogArtistTitle(raw);
  return parts.given ? parts.surname + ', ' + parts.given : parts.surname;
}

function catalogArtistSortKey(raw) {
  var parts = normalizeCatalogArtistTitle(raw);
  return (parts.surname + '\0' + parts.given).toLowerCase();
}

function resortMegaMenuArtistLists(root) {
  if (!root) return;
  root.querySelectorAll('.mega-menu__flyout-list').forEach(function(list) {
    var items = Array.prototype.slice.call(list.querySelectorAll(':scope > li'));
    if (items.length < 2) return;
    items.sort(function(a, b) {
      var ta = (a.querySelector('a') && a.querySelector('a').textContent || '').trim();
      var tb = (b.querySelector('a') && b.querySelector('a').textContent || '').trim();
      return catalogArtistSortKey(ta).localeCompare(catalogArtistSortKey(tb));
    });
    items.forEach(function(li) {
      var link = li.querySelector('a');
      if (link) link.textContent = formatCatalogArtistName(link.textContent.trim());
      list.appendChild(li);
    });
  });
}

function attachCatalogArtistLink(listCol, linkEl, handle) {
  linkEl.addEventListener('mouseenter', function() {
    listCol.querySelectorAll('a').forEach(function(l) { l.classList.remove('is-active'); });
    linkEl.classList.add('is-active');
    if (handle) {
      activePreviewHandle = handle;
      document.getElementById('giclee-preview-name').textContent = linkEl.textContent;
      document.getElementById('giclee-preview-count').textContent = (window.__gicleeI18n && window.__gicleeI18n.catalog_view_collection) || 'Zobacz kolekcję';
      fetchArtistPreview(handle, function(data) {
        if (activePreviewHandle !== handle) return;
        setPreviewImage(data.img);
      });
    }
  });
}

function populateCatalogArtistList(listCol, artistLinks, showHeader) {
  const visible = [];
  artistLinks.forEach(function(origLink) {
    const handle = getCollectionHandleFromHref(origLink.href);
    if (isCatalogArtistHidden(handle)) return;
    const rawText = origLink.textContent.trim();
    visible.push({
      href: origLink.href,
      text: formatCatalogArtistName(rawText),
      handle: handle
    });
  });

  visible.sort(function(a, b) {
    return catalogArtistSortKey(a.text).localeCompare(catalogArtistSortKey(b.text));
  });

  if (showHeader && CATALOG_SHOW_HEADER) {
    const header = document.createElement('div');
    header.className = 'giclee-artists-list-header';
    header.textContent = (window.__gicleeI18n && window.__gicleeI18n.catalog_artists) || 'Artyści';
    listCol.appendChild(header);
  }

  const grid = document.createElement('div');
  grid.className = 'giclee-artists-columns';
  const totalSlots = artistLinks.length;
  const targetRowsPerCol = Math.max(1, Math.ceil(totalSlots / CATALOG_LIST_COLUMNS));
  const perCol = visible.length
    ? Math.ceil(visible.length / CATALOG_LIST_COLUMNS)
    : 0;

  for (var c = 0; c < CATALOG_LIST_COLUMNS; c++) {
    const colEl = document.createElement('div');
    colEl.className = 'giclee-artists-col';
    const chunk = visible.slice(c * perCol, (c + 1) * perCol);
    chunk.forEach(function(item) {
      const a = document.createElement('a');
      a.href = item.href;
      a.textContent = item.text;
      attachCatalogArtistLink(listCol, a, item.handle);
      colEl.appendChild(a);
    });
    grid.appendChild(colEl);
  }
  listCol.appendChild(grid);

  requestAnimationFrame(function() {
    requestAnimationFrame(function() {
      const sample = listCol.querySelector('a');
      if (!sample) return;
      const linkH = sample.offsetHeight || 23;
      const colMinH = targetRowsPerCol * linkH;
      grid.style.minHeight = colMinH + 'px';
      listCol.querySelectorAll('.giclee-artists-col').forEach(function(col) {
        col.style.minHeight = colMinH + 'px';
        const links = col.querySelectorAll('a');
        const n = links.length;
        if (n <= 1) return;
        const extra = colMinH - n * linkH;
        if (extra > 0) {
          col.style.gap = (extra / (n - 1)) + 'px';
        }
      });
    });
  });
}

function fetchArtistPreview(handle, callback) {
  if (imageCache[handle]) {
    callback(imageCache[handle]);
    return;
  }
  fetch(collectionProductsJsonUrl(handle))
    .then(r => r.json())
    .then(data => {
      const imgs = data.products?.[0]?.images || [];
      const previewImg = imgs.find(function(im) {
        return (im.alt || '').toLowerCase().indexOf('(preview)') !== -1;
      });
      const pick = previewImg || imgs[0];
      let src = pick?.src || null;
      if (src && src.indexOf('width=') === -1) {
        src += (src.indexOf('?') === -1 ? '?' : '&') + 'width=720';
      }
      imageCache[handle] = { img: src };
      callback({ img: src });
    })
    .catch(() => callback({ img: null }));
}

function hideCatalogPreview() {
  activePreviewHandle = null;
  currentPreviewSrc = null;
  const img = document.getElementById('giclee-preview-img');
  const previewCol = document.getElementById('giclee-artist-preview');
  if (img) {
    img.classList.remove('is-visible');
    img.style.transition = 'none';
    img.style.opacity = '0';
    img.style.visibility = 'hidden';
  }
  if (previewCol) {
    previewCol.style.transition = 'none';
    previewCol.style.opacity = '0';
    previewCol.style.visibility = 'hidden';
  }
}

function setPreviewImage(src) {
  const img = document.getElementById('giclee-preview-img');
  const previewCol = document.getElementById('giclee-artist-preview');
  if (document.body.classList.contains('is-navigating')) return;
  const panel = document.getElementById('giclee-catalog-panel');
  if (panel && (panel.classList.contains('is-closing') || panel._navLock)) return;
  if (!src) {
    img.classList.remove('is-visible');
    return;
  }

  if (currentPreviewSrc === src && img.hasAttribute('src') && img.complete && img.naturalWidth > 0) {
    if (previewCol) {
      previewCol.style.opacity = '';
      previewCol.style.visibility = '';
    }
    img.style.opacity = '';
    img.style.visibility = '';
    img.classList.add('is-visible');
    return;
  }

  currentPreviewSrc = src;

  const loader = new Image();
  loader.onload = function() {
    if (currentPreviewSrc !== src) return;
    if (document.body.classList.contains('is-navigating')) return;
    if (panel && (panel.classList.contains('is-closing') || panel._navLock)) return;
    img.src = src;
    if (previewCol) {
      previewCol.style.opacity = '';
      previewCol.style.visibility = '';
    }
    img.style.opacity = '';
    img.style.visibility = '';
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        if (currentPreviewSrc === src && !document.body.classList.contains('is-navigating')) {
          img.classList.add('is-visible');
        }
      });
    });
  };
  loader.onerror = function() {
    if (currentPreviewSrc === src) {
      currentPreviewSrc = img.getAttribute('src');
    }
  };
  loader.src = src;
}

function initGalleryCatalog() {
  const katalogItem = Array.from(document.querySelectorAll('.menu-list__list-item')).find(function(li) {
    const a = li.querySelector('a');
    return a && a.dataset.gicleeMenu === 'catalog';
  });

  if (!katalogItem || katalogItem.dataset.galleryInit) return;
  katalogItem.dataset.galleryInit = 'true';

  // Usuń stary panel jeśli istnieje (zabezpieczenie przed duplikatem)
  const existingPanel = document.getElementById('giclee-catalog-panel');
  if (existingPanel) existingPanel.remove();

  const katalogNativeLink = katalogItem.querySelector('a.menu-list__link');
  const katalogNativeTitle = katalogItem.querySelector('.menu-list__link-title');
  function stripKatalogNativeHoverHandlers() {
    katalogItem.removeAttribute('on:pointerenter');
    katalogItem.removeAttribute('on:pointerleave');
    katalogItem.removeAttribute('on:focus');
    katalogItem.removeAttribute('on:blur');
    if (katalogNativeLink) {
      katalogNativeLink.removeAttribute('on:pointerenter');
      katalogNativeLink.removeAttribute('on:pointerleave');
      katalogNativeLink.removeAttribute('on:focus');
      katalogNativeLink.removeAttribute('on:blur');
    }
    if (katalogNativeTitle) {
      katalogNativeTitle.removeAttribute('on:pointerenter');
      katalogNativeTitle.removeAttribute('on:pointerleave');
    }
  }
  stripKatalogNativeHoverHandlers();

  new MutationObserver(stripKatalogNativeHoverHandlers).observe(katalogItem, {
    attributes: true,
    attributeFilter: ['on:pointerenter', 'on:pointerleave', 'on:focus', 'on:blur'],
    subtree: true
  });

  var nativeSub = katalogItem.querySelector('.menu-list__submenu');
  if (nativeSub) {
    nativeSub.style.setProperty('display', 'none', 'important');
    nativeSub.style.setProperty('visibility', 'hidden', 'important');
    nativeSub.style.setProperty('opacity', '0', 'important');
    nativeSub.style.setProperty('pointer-events', 'none', 'important');
    nativeSub.style.setProperty('height', '0', 'important');
    nativeSub.style.setProperty('max-height', '0', 'important');
    nativeSub.style.setProperty('box-shadow', 'none', 'important');
    new MutationObserver(function() {
      nativeSub.style.setProperty('display', 'none', 'important');
      nativeSub.style.setProperty('visibility', 'hidden', 'important');
      nativeSub.style.setProperty('opacity', '0', 'important');
      nativeSub.style.setProperty('height', '0', 'important');
      nativeSub.style.setProperty('max-height', '0', 'important');
      nativeSub.style.setProperty('box-shadow', 'none', 'important');
    }).observe(nativeSub, { attributes: true, attributeFilter: ['style', 'class'] });
  }

  const megaMenuInner = katalogItem.querySelector('.mega-menu__grid');
  if (!megaMenuInner) return;

  const panel = document.createElement('div');
  panel.id = 'giclee-catalog-panel';
  panel._catalogInlineStagger = true;
  panel._linkTimers = [];
  panel.setAttribute('data-preview-graphics-variant', CATALOG_PREVIEW_GRAPHICS_VARIANT);

  const listCol = document.createElement('div');
  listCol.id = 'giclee-artists-list';

  const previewCol = document.createElement('div');
  previewCol.id = 'giclee-artist-preview';
  previewCol.innerHTML = `
    <img id="giclee-preview-img" alt="">
    <div id="giclee-preview-info">
      <div id="giclee-preview-line"></div>
      <div id="giclee-preview-name"></div>
      <div id="giclee-preview-count"></div>
    </div>
  `;

  const artistsLink = megaMenuInner.querySelector('.mega-menu__link--parent');
  resortMegaMenuArtistLists(megaMenuInner);
  const artistLinks = megaMenuInner.querySelectorAll('.mega-menu__link--child, .mega-menu__flyout-panel a');
  populateCatalogArtistList(listCol, artistLinks, !!artistsLink);

  panel.appendChild(listCol);
  panel.appendChild(previewCol);
  document.body.appendChild(panel);

  function positionPanel() {
    const headerEl = document.querySelector('#header-component, .header-section, header');
    const rect = headerEl.getBoundingClientRect();
    // Small overlap removes hover gap between menu item and panel.
    panel.style.top = (rect.bottom - 14) + 'px';
  }

  let hideTimer;
  let hideFinalizeTimer;
  let listCloseTimer;

  function resetPanelLinks() {
    if (panel._linkTimers && panel._linkTimers.length) {
      panel._linkTimers.forEach(function(t) { clearTimeout(t); });
      panel._linkTimers = [];
    }
    listCol.querySelectorAll('a').forEach(function(link) {
      link.classList.remove('is-in');
      link.style.transition = '';
      link.style.opacity = '';
      link.style.transform = '';
      link.style.visibility = '';
      link.style.willChange = '';
    });
  }

  function closePanelLinks() {
    var links = Array.from(listCol.querySelectorAll('a'));
    if (panel._linkTimers && panel._linkTimers.length) {
      panel._linkTimers.forEach(function(t) { clearTimeout(t); });
      panel._linkTimers = [];
    }
    links.forEach(function(link) {
      // Freeze current reveal state; do not force unrevealed links to appear on close.
      var revealed = link.classList.contains('is-in');
      link.style.visibility = revealed ? 'visible' : 'hidden';
      link.style.transition = 'none';
      link.style.opacity = revealed ? '1' : '0';
      link.style.transform = revealed ? 'translateY(0)' : 'translateY(10px)';
    });
  }

  function freezePanelLinksForNavigation() {
    var links = Array.from(listCol.querySelectorAll('a'));
    if (panel._linkTimers && panel._linkTimers.length) {
      panel._linkTimers.forEach(function(t) { clearTimeout(t); });
      panel._linkTimers = [];
    }
    links.forEach(function(link) {
      var cs = window.getComputedStyle(link);
      link.style.transition = 'none';
      link.style.visibility = cs.visibility;
      link.style.opacity = cs.opacity;
      link.style.transform = cs.transform === 'none' ? 'translateY(0)' : cs.transform;
    });
  }

  function freezePanelForNavigation() {
    panel._navLock = true;
    clearTimeout(hideTimer);
    clearTimeout(hideFinalizeTimer);
    clearTimeout(listCloseTimer);
    if (panel._linkTimers && panel._linkTimers.length) {
      panel._linkTimers.forEach(function(t) { clearTimeout(t); });
      panel._linkTimers = [];
    }
    panel.classList.remove('staggering', 'is-closing');
    panel.classList.add('is-open', 'is-nav-lifting');

    panel.style.removeProperty('--giclee-lift-y');
    panel.style.setProperty('clip-path', 'inset(0 0 0 0)', 'important');
    panel.style.setProperty('opacity', '1', 'important');
    panel.style.setProperty('visibility', 'visible', 'important');
    panel.style.setProperty('transition', 'none', 'important');
    panel.style.setProperty('transform', 'translateY(0)', 'important');

    var listCS = window.getComputedStyle(listCol);
    listCol.style.clipPath = listCS.clipPath === 'none' ? 'inset(0 0 0 0)' : listCS.clipPath;
    listCol.style.transition = 'none';
    freezePanelLinksForNavigation();

    /* 3 klatki: zamrożenie → włączenie transition → cel (bez skoku) */
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        if (!panel.classList.contains('is-nav-lifting')) return;
        var rect = panel.getBoundingClientRect();
        var liftTo = -(rect.bottom + 168);
        panel.style.setProperty(
          'transition',
          'transform var(--pt-close-duration, 0.72s) cubic-bezier(0.25, 0.46, 0.45, 0.94)',
          'important'
        );
        panel.style.setProperty('transform', 'translateY(0)', 'important');
        void panel.offsetHeight;
        requestAnimationFrame(function() {
          if (!panel.classList.contains('is-nav-lifting')) return;
          panel.style.setProperty('transform', 'translateY(' + liftTo + 'px)', 'important');
        });
      });
    });
  }

  function staggerPanelLinks() {
    var anim = (catalogSubmenuConfig && catalogSubmenuConfig.animation) || {};
    var openRevealDelay = _catalogCfgNum(anim.open_reveal_delay_ms, 120);
    var maxCascadeMs = _catalogCfgNum(anim.max_cascade_ms, 2200);
    var minIntervalMs = _catalogCfgNum(anim.min_interval_ms, 20);
    var maxIntervalMs = _catalogCfgNum(anim.max_interval_ms, 92);
    var intervalCurve = _catalogCfgNum(anim.interval_curve, 1.75);
    var linkTransitionMs = _catalogCfgNum(anim.link_transition_ms, 220);
    var links = listCol.querySelectorAll('a');
    resetPanelLinks();
    links.forEach(function(link) {
      link.classList.remove('is-in');
      link.style.transition = 'none';
      link.style.opacity = '0';
      link.style.transform = 'translateY(10px)';
      link.style.visibility = 'hidden';
      link.style.willChange = 'opacity, transform';
    });

    requestAnimationFrame(function() {
      var maxCascadeMsClamped = Math.min(4000, Math.max(400, maxCascadeMs));
      var minIntervalMsClamped = Math.max(4, minIntervalMs);
      var maxIntervalMsClamped = Math.max(minIntervalMsClamped, maxIntervalMs);
      var intervalCurveClamped = Math.max(0.5, intervalCurve);
      var totalIntervals = 0;
      var intervals = [];
      for (var k = 0; k < Math.max(0, links.length - 1); k++) {
        var q = (links.length - 2) > 0 ? (k / (links.length - 2)) : 1;
        var rawInterval = minIntervalMsClamped + (maxIntervalMsClamped - minIntervalMsClamped) * Math.pow(q, intervalCurveClamped);
        intervals.push(rawInterval);
        totalIntervals += rawInterval;
      }
      var intervalScale = totalIntervals > 0 ? (maxCascadeMsClamped / totalIntervals) : 1;
      var cumulativeDelay = 0;

      links.forEach(function(link, i) {
        if (i > 0) cumulativeDelay += intervals[i - 1] * intervalScale;
        var timer = setTimeout(function() {
          link.style.visibility = 'visible';
          link.offsetHeight;
          link.style.transition = 'opacity ' + (linkTransitionMs / 1000) + 's cubic-bezier(0.16, 1, 0.3, 1), transform ' + (linkTransitionMs / 1000) + 's cubic-bezier(0.16, 1, 0.3, 1)';
          link.style.opacity = '1';
          link.style.transform = 'translateY(0)';
          link.classList.add('is-in');
        }, openRevealDelay + Math.round(cumulativeDelay));
        panel._linkTimers.push(timer);
      });
    });
  }

  function beginPanelClose(finalize) {
    panel.classList.add('is-closing');
    closePanelLinks();

    listCol.style.transition = 'none';
    listCol.style.clipPath = 'inset(0 0 0 0)';
    listCol.style.opacity = '1';
    listCol.style.transform = 'translateY(0)';
    listCol.style.overflow = 'hidden';
    listCol.style.overflowY = 'hidden';

    requestAnimationFrame(function() {
      listCol.style.transition = 'clip-path 0.5s cubic-bezier(0.22, 0.61, 0.36, 1)';
      listCol.style.clipPath = 'inset(0 0 100% 0)';
    });

    if (!finalize) return;

    listCloseTimer = setTimeout(function() {
      panel.classList.remove('is-open', 'is-closing');
      resetPanelLinks();
      listCol.style.clipPath = '';
      listCol.style.opacity = '';
      listCol.style.transform = '';
      listCol.style.overflow = '';
      listCol.style.overflowY = 'auto';
      listCol.style.transition = '';
      const katalogLink = katalogItem.querySelector('a.menu-list__link');
      if (katalogLink) katalogLink.style.cssText = '';
      hideCatalogPreview();
    }, 500);
  }

  function showPanel() {
    clearTimeout(hideTimer);
    clearTimeout(hideFinalizeTimer);
    clearTimeout(listCloseTimer);
    panel._navLock = false;
    var alreadyOpen = panel.classList.contains('is-open') && !panel.classList.contains('is-closing');
    panel.classList.remove('is-closing', 'is-nav-lifting');
    panel.style.removeProperty('clip-path');
    panel.style.removeProperty('opacity');
    panel.style.removeProperty('visibility');
    panel.style.removeProperty('transform');
    panel.style.removeProperty('transition');
    panel.style.removeProperty('--giclee-lift-y');
    listCol.style.clipPath = 'inset(0 0 0 0)';
    listCol.style.opacity = '';
    listCol.style.transform = '';
    listCol.style.overflow = '';
    listCol.style.overflowY = 'auto';
    listCol.style.transition = '';
    var previewCol = document.getElementById('giclee-artist-preview');
    var previewImg = document.getElementById('giclee-preview-img');
    if (previewCol) {
      previewCol.style.opacity = '';
      previewCol.style.visibility = '';
      previewCol.style.transition = '';
    }
    if (previewImg) {
      previewImg.style.opacity = '';
      previewImg.style.visibility = '';
      previewImg.style.transition = '';
    }
    positionPanel();
    panel.classList.add('is-open');
    if (!alreadyOpen) {
      staggerPanelLinks();
    }
    const katalogLink = katalogItem.querySelector('a.menu-list__link');
    if (katalogLink) katalogLink.style.cssText = 'visibility:visible!important;opacity:1!important;';
    listCol.querySelectorAll('a').forEach(function(link) {
      const h = getCollectionHandleFromHref(link.getAttribute('href'));
      if (h && !imageCache[h]) fetchArtistPreview(h, function() {});
    });
  }

  function hidePanel() {
    if (panel._navLock) return;
    hideTimer = setTimeout(function() {
      if (panel._navLock) return;
      beginPanelClose(true);
    }, 180);
  }

  const katalogLink = katalogItem.querySelector('a.menu-list__link');
  if (katalogLink) {
    katalogLink.setAttribute('href', '#');
    katalogLink.addEventListener('click', function(e) {
      e.preventDefault();
      showPanel();
    });
  }

  // Otwieraj po najechaniu na napis „Katalog”, nie na całe czarne pole pozycji menu.
  const katalogHoverTarget = katalogItem.querySelector('.menu-list__link-title') || katalogLink || katalogItem;
  katalogHoverTarget.addEventListener('mouseenter', showPanel);
  katalogItem.addEventListener('mouseleave', hidePanel);
  panel.addEventListener('mouseenter', function() {
    clearTimeout(hideTimer);
    clearTimeout(hideFinalizeTimer);
    clearTimeout(listCloseTimer);
    panel.classList.remove('is-closing');
    listCol.style.clipPath = 'inset(0 0 0 0)';
    listCol.style.opacity = '';
    listCol.style.transform = '';
    listCol.style.overflow = '';
    listCol.style.overflowY = 'auto';
    listCol.style.transition = '';
    const katalogLink = katalogItem.querySelector('a.menu-list__link');
    if (katalogLink) katalogLink.style.cssText = 'visibility:visible!important;opacity:1!important;';
  });
  panel.addEventListener('mouseleave', hidePanel);

  // Zamroź katalog przy nawigacji (klik autora, kolekcji itd.) — kotara przykrywa panel.
  window.addEventListener('giclee:navigation-start', function() {
    if (!panel.classList.contains('is-open') && !panel.classList.contains('is-closing')) {
      panel._navLock = false;
      return;
    }
    freezePanelForNavigation();
  });

  window.addEventListener('giclee:curtain-closed', hideCatalogPreview);
}

let attempts = 0;
let catalogSubmenuBootstrapped = false;

function bootstrapGalleryCatalog() {
  applyHiddenCatalogArtistsToNavigation();
  initGalleryCatalog();
}

loadCatalogSubmenuConfig(function() {
  catalogSubmenuBootstrapped = true;
  bootstrapGalleryCatalog();
});

const interval = setInterval(function() {
  if (!catalogSubmenuBootstrapped) return;
  bootstrapGalleryCatalog();
  attempts++;
  if (attempts > 20) clearInterval(interval);
}, 500);

/* Zgodność z panelem tworzonym dynamicznie przez starsze warianty motywu. */
(function() {
  function initCatalogPanel(panel) {
    if (panel._catalogInit) return;
    if (panel._catalogInlineStagger) return;
    panel._catalogInit = true;
    var wasOpen = panel.classList.contains('is-open');

    function runLinkStagger() {
      var links = panel.querySelectorAll('#giclee-artists-list a');
      panel.classList.add('staggering');
      if (panel._linkTimers && panel._linkTimers.length) {
        panel._linkTimers.forEach(function(t) { clearTimeout(t); });
      }
      panel._linkTimers = [];
      links.forEach(function(link) {
        link.classList.remove('is-in');
        link.style.willChange = 'opacity, transform';
        link.style.transition = 'none';
        link.style.opacity = '0';
        link.style.transform = 'translateY(10px)';
        link.style.visibility = 'hidden';
      });
      requestAnimationFrame(function() {
        var openRevealDelay = 100;
        // Keep cascade readable even for long artist lists.
        var maxCascadeMs = Math.min(2200, Math.max(1300, Math.max(0, links.length - 1) * 24));
        var minIntervalMs = 22;
        var maxIntervalMs = 68;
        var intervalCurve = 1.35; // smaller intervals at start, larger near the end
        var intervals = [];
        var totalIntervals = 0;
        for (var k = 0; k < Math.max(0, links.length - 1); k++) {
          var q = (links.length - 2) > 0 ? (k / (links.length - 2)) : 1;
          var rawInterval = minIntervalMs + (maxIntervalMs - minIntervalMs) * Math.pow(q, intervalCurve);
          intervals.push(rawInterval);
          totalIntervals += rawInterval;
        }
        var intervalScale = totalIntervals > 0 ? (maxCascadeMs / totalIntervals) : 1;
        var cumulativeDelay = 0;
        links.forEach(function(link, i) {
          if (i > 0) {
            cumulativeDelay += intervals[i - 1] * intervalScale;
          }
          var easedDelay = Math.round(cumulativeDelay);
          var timer = setTimeout(function() {
            link.style.visibility = 'visible';
            link.offsetHeight; // force style flush before transition
            link.style.transition = 'opacity 0.22s cubic-bezier(0.16, 1, 0.3, 1), transform 0.22s cubic-bezier(0.16, 1, 0.3, 1)';
            link.style.opacity = '1';
            link.style.transform = 'translateY(0)';
            link.classList.add('is-in');
            if (i === links.length - 1) {
              panel.classList.remove('staggering');
            }
          }, openRevealDelay + easedDelay);
          panel._linkTimers.push(timer);
        });
      });
    }

    function resetLinkStagger() {
      var links = panel.querySelectorAll('#giclee-artists-list a');
      panel.classList.remove('staggering');
      if (panel._linkTimers && panel._linkTimers.length) {
        panel._linkTimers.forEach(function(t) { clearTimeout(t); });
        panel._linkTimers = [];
      }
      links.forEach(function(link) {
        link.classList.remove('is-in');
        link.style.willChange = '';
        link.style.transition = '';
        link.style.opacity = '';
        link.style.transform = '';
        link.style.visibility = '';
      });
    }

    // --- Close on mouseleave ---
    panel.addEventListener('mouseleave', function(e) {
      clearTimeout(panel._closeTimer);
      panel._closeTimer = setTimeout(function() {
        panel.classList.remove('is-open');
      }, 180);
    });
    panel.addEventListener('mouseenter', function() {
      clearTimeout(panel._closeTimer);
    });

    // --- Stagger links on open ---
    panel.addEventListener('giclee:catalog-open', runLinkStagger);
    panel.addEventListener('giclee:catalog-close', resetLinkStagger);
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        if (m.attributeName === 'class') {
          if (panel._skipNextObserver) {
            panel._skipNextObserver = false;
            return;
          }
          var isOpenNow = panel.classList.contains('is-open');
          if (isOpenNow === wasOpen) return;
          wasOpen = isOpenNow;
          if (isOpenNow) {
            runLinkStagger();
          } else {
            resetLinkStagger();
          }
        }
      });
    });
    observer.observe(panel, { attributes: true });
  }

  // Try on DOMContentLoaded, then poll in case it's dynamically created
  function tryInit() {
    var panel = document.getElementById('giclee-catalog-panel');
    if (panel) { initCatalogPanel(panel); return; }
    setTimeout(tryInit, 300);
  }
  document.addEventListener('DOMContentLoaded', tryInit);
})();

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

/* Giclée Catalog — priorytetowa kolejka podglądów artystów.
 * - maks. 3 requesty łącznie,
 * - maks. 2 requesty tła (1 slot pozostaje dla aktywnego hover/focus),
 * - hover uruchamia request dopiero po krótkim zatrzymaniu,
 * - najnowszy hover ma pierwszeństwo,
 * - wyniki są współdzielone przez istniejący imageCache.
 */
(function () {
  'use strict';

  var MAX_CONCURRENT = 3;
  var MAX_BACKGROUND_CONCURRENT = 2;
  var HOVER_INTENT_DELAY_MS = 75;
  var states = Object.create(null);
  var priorityQueue = [];
  var backgroundQueue = [];
  var activeTotal = 0;
  var activePriority = 0;
  var activeBackground = 0;
  var hoverIntentTimer = 0;
  var hoverIntentToken = 0;
  var installed = false;

  function hasCached(handle) {
    return typeof imageCache === 'object' && imageCache !== null &&
      Object.prototype.hasOwnProperty.call(imageCache, handle);
  }

  function callLater(callback, payload) {
    if (typeof callback !== 'function') return;
    Promise.resolve().then(function () {
      try {
        callback(payload);
      } catch (error) {
        setTimeout(function () { throw error; }, 0);
      }
    });
  }

  function removeQueuedJob(queue, job) {
    var index = queue.indexOf(job);
    if (index >= 0) queue.splice(index, 1);
  }

  function demotePendingPriorities(exceptHandle) {
    priorityQueue.slice().forEach(function (job) {
      if (job.handle === exceptHandle) return;
      removeQueuedJob(priorityQueue, job);
      job.priority = false;
      backgroundQueue.push(job);
    });
  }

  function promoteQueuedJob(job) {
    if (!job || job.status !== 'queued' || job.priority) return;
    removeQueuedJob(backgroundQueue, job);
    demotePendingPriorities(job.handle);
    job.priority = true;
    priorityQueue.unshift(job);
  }

  function extractPreview(data) {
    var products = data && Array.isArray(data.products) ? data.products : [];
    var images = products[0] && Array.isArray(products[0].images)
      ? products[0].images
      : [];
    var previewImage = images.find(function (image) {
      return String((image && image.alt) || '').toLowerCase().indexOf('(preview)') !== -1;
    });
    var pick = previewImage || images[0];
    var src = pick && pick.src ? String(pick.src) : null;
    if (src && src.indexOf('width=') === -1) {
      src += (src.indexOf('?') === -1 ? '?' : '&') + 'width=720';
    }
    return { img: src };
  }

  function finishJob(job, payload, wasBackground) {
    if (typeof imageCache === 'object' && imageCache !== null) {
      imageCache[job.handle] = payload;
    }

    var callbacks = job.callbacks.slice();
    delete states[job.handle];
    activeTotal = Math.max(0, activeTotal - 1);
    if (wasBackground) {
      activeBackground = Math.max(0, activeBackground - 1);
    } else {
      activePriority = Math.max(0, activePriority - 1);
    }

    callbacks.forEach(function (callback) {
      callLater(callback, payload);
    });
    pumpQueue();
  }

  function startJob(job, wasBackground) {
    job.status = 'loading';
    activeTotal += 1;
    if (wasBackground) activeBackground += 1;
    else activePriority += 1;

    fetch(collectionProductsJsonUrl(job.handle), { credentials: 'same-origin' })
      .then(function (response) {
        if (!response.ok) throw new Error('Catalog preview request failed: ' + response.status);
        return response.json();
      })
      .then(extractPreview)
      .catch(function () { return { img: null }; })
      .then(function (payload) {
        finishJob(job, payload, wasBackground);
      });
  }

  function pumpQueue() {
    while (
      activeTotal < MAX_CONCURRENT &&
      activePriority < 1 &&
      priorityQueue.length
    ) {
      startJob(priorityQueue.shift(), false);
    }

    while (
      activeTotal < MAX_CONCURRENT &&
      activeBackground < MAX_BACKGROUND_CONCURRENT &&
      backgroundQueue.length
    ) {
      startJob(backgroundQueue.shift(), true);
    }
  }

  function enqueuePreview(handle, callback, priority) {
    handle = String(handle || '').trim().toLowerCase();
    if (!handle) {
      callLater(callback, { img: null });
      return;
    }

    if (hasCached(handle)) {
      callLater(callback, imageCache[handle]);
      return;
    }

    var existing = states[handle];
    if (existing) {
      if (typeof callback === 'function') existing.callbacks.push(callback);
      if (priority && existing.status === 'queued') promoteQueuedJob(existing);
      pumpQueue();
      return;
    }

    var job = {
      handle: handle,
      callbacks: typeof callback === 'function' ? [callback] : [],
      priority: !!priority,
      status: 'queued'
    };
    states[handle] = job;

    if (priority) {
      demotePendingPriorities(handle);
      priorityQueue.unshift(job);
    } else {
      backgroundQueue.push(job);
    }
    pumpQueue();
  }

  function scheduleHoverPreview(handle, callback) {
    if (hasCached(handle) || (states[handle] && states[handle].status === 'loading')) {
      enqueuePreview(handle, callback, true);
      return;
    }

    hoverIntentToken += 1;
    var token = hoverIntentToken;
    clearTimeout(hoverIntentTimer);
    hoverIntentTimer = setTimeout(function () {
      if (token !== hoverIntentToken) return;
      enqueuePreview(handle, callback, true);
    }, HOVER_INTENT_DELAY_MS);
  }

  function updatePreviewForFocusedLink(link) {
    if (!link || typeof getCollectionHandleFromHref !== 'function') return;
    var handle = getCollectionHandleFromHref(link.getAttribute('href'));
    if (!handle) return;

    var list = link.closest('#giclee-artists-list');
    if (!list) return;
    list.querySelectorAll('a.is-active').forEach(function (other) {
      if (other !== link) other.classList.remove('is-active');
    });
    link.classList.add('is-active');

    activePreviewHandle = handle;
    var name = document.getElementById('giclee-preview-name');
    var count = document.getElementById('giclee-preview-count');
    if (name) name.textContent = link.textContent;
    if (count) {
      count.textContent = (window.__gicleeI18n && window.__gicleeI18n.catalog_view_collection) ||
        'Zobacz kolekcję';
    }

    enqueuePreview(handle, function (data) {
      if (activePreviewHandle !== handle) return;
      if (typeof setPreviewImage === 'function') setPreviewImage(data.img);
    }, true);
  }

  function install() {
    if (installed || typeof fetchArtistPreview !== 'function') return false;
    installed = true;

    fetchArtistPreview = function (handle, callback) {
      var normalized = String(handle || '').trim().toLowerCase();
      var isActiveIntent = !!normalized &&
        typeof activePreviewHandle !== 'undefined' &&
        activePreviewHandle === normalized;

      if (isActiveIntent) {
        scheduleHoverPreview(normalized, callback);
      } else {
        enqueuePreview(normalized, callback, false);
      }
    };

    document.addEventListener('focusin', function (event) {
      var target = event.target;
      var link = target && target.closest
        ? target.closest('#giclee-artists-list a')
        : null;
      if (!link) return;
      clearTimeout(hoverIntentTimer);
      hoverIntentToken += 1;
      updatePreviewForFocusedLink(link);
    }, true);

    document.addEventListener('pointerleave', function (event) {
      var list = event.target && event.target.closest
        ? event.target.closest('#giclee-artists-list')
        : null;
      if (!list) return;
      clearTimeout(hoverIntentTimer);
      hoverIntentToken += 1;
    }, true);

    return true;
  }

  if (!install()) {
    var attempts = 0;
    var timer = setInterval(function () {
      attempts += 1;
      if (install() || attempts >= 40) clearInterval(timer);
    }, 50);
  }
})();
