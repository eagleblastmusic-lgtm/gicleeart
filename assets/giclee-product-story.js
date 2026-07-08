/**
 * PDP szablon-produktu-v3: stronicowany opis produktu ("mini strony").
 *
 * Czyta ukryty .product-description-below (naglowek, akapity, SZCZEGOLY),
 * dzieli akapity na strony wg metafielda custom.story_pages (JSON w
 * data-giclee-story-config) lub — bez konfiguracji — zachlannie wg dlugosci
 * tekstu. Ostatnia strona = panel SZCZEGOLY. Lewa kolumna: tekst + nawigacja,
 * prawa: grafika strony (kropki-wskazniki pod grafika).
 */
(function () {
  var AUTO_PAGE_CHAR_LIMIT = 850;

  /* Ustawienia efektow PDP v3 (metafield shop custom.pdp_v3_effects,
     wstrzykiwane inline w sections/product-information.liquid) */
  function pdpFx() {
    return window.__PDP_V3_EFFECTS__ || {};
  }

  function gicleeUi(key, fallback) {
    if (typeof window.__gicleeI18nGet === 'function') return window.__gicleeI18nGet(key, fallback);
    var bag = window.__gicleeI18n || {};
    var v = bag[key];
    if (!v || (typeof v === 'string' && /translation missing/i.test(v))) return fallback;
    return v;
  }

  function textOf(el) {
    return (el && el.textContent ? el.textContent : '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  var HIDDEN_DETAIL_LABELS = {
    forma: true,
    form: true,
    forme: true,
    vorm: true,
  };

  function isHiddenDetailLabel(label) {
    var key = (label || '').toLowerCase().replace(/\s*:\s*$/, '').trim();
    return !!HIDDEN_DETAIL_LABELS[key];
  }

  /* ------------------------------------------------------------------ */
  /* Parsowanie ukrytego opisu                                           */
  /* ------------------------------------------------------------------ */

  function splitParagraphs(cell) {
    var html = cell.innerHTML || '';
    var parts = html.split(/<br\s*\/?>\s*<br\s*\/?>/i);
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      var tmp = document.createElement('div');
      tmp.innerHTML = parts[i];
      var text = textOf(tmp);
      if (text) out.push(text);
    }
    return out;
  }

  function parseDetails(cell) {
    var out = { heading: '', rows: [], fallbackHtml: cell.innerHTML || '' };
    var lines = (cell.innerHTML || '').split(/<br\s*\/?>/i);
    for (var i = 0; i < lines.length; i++) {
      var tmp = document.createElement('div');
      tmp.innerHTML = lines[i];
      var strong = tmp.querySelector('strong');
      if (!strong) continue;
      var label = textOf(strong).replace(/\s*:\s*$/, '');
      strong.parentNode.removeChild(strong);
      var value = textOf(tmp);
      if (!label) continue;
      if (!value) {
        if (!out.heading) out.heading = label;
      } else {
        out.rows.push({ label: label, value: value });
      }
    }
    return out;
  }

  function parseDescription(descRoot) {
    var table = descRoot.querySelector('table');
    if (!table) return null;
    var rows = table.querySelectorAll('tbody > tr');
    if (!rows.length) return null;

    var header = { title: '', artist: '', dates: '' };
    var headerCell = rows[0].querySelector('td');
    if (headerCell) {
      var divs = headerCell.querySelectorAll('div');
      if (divs[0]) header.title = textOf(divs[0]);
      if (divs[1]) header.artist = textOf(divs[1]);
      if (divs[2]) header.dates = textOf(divs[2]);
    }

    var lastRow = rows[rows.length - 1];
    var cells = lastRow.querySelectorAll('td');
    if (!cells.length) return null;
    var descCell = cells[0];
    var detailsCell = cells.length > 1 ? cells[cells.length - 1] : null;

    return {
      header: header,
      paragraphs: splitParagraphs(descCell),
      details: detailsCell ? parseDetails(detailsCell) : null,
    };
  }

  /* ------------------------------------------------------------------ */
  /* Budowanie stron                                                     */
  /* ------------------------------------------------------------------ */

  function readConfig(root) {
    var raw = root.getAttribute('data-giclee-story-config');
    if (!raw) return null;
    try {
      var parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (e) {
      console.warn('[giclee-story] invalid config', e);
      return null;
    }
  }

  function buildPages(data, config, fallbackImage) {
    var paras = data.paragraphs.slice();
    var pages = [];
    var cfgPages =
      config && Object.prototype.toString.call(config.pages) === '[object Array]'
        ? config.pages
        : null;

    if (cfgPages && cfgPages.length) {
      var idx = 0;
      for (var i = 0; i < cfgPages.length && idx < paras.length; i++) {
        var n = Math.max(1, parseInt(cfgPages[i] && cfgPages[i].paragraphs, 10) || 1);
        var chunk = paras.slice(idx, idx + n);
        idx += n;
        if (chunk.length) {
          pages.push({
            type: 'text',
            paragraphs: chunk,
            image: (cfgPages[i] && cfgPages[i].image) || '',
          });
        }
      }
      if (idx < paras.length) {
        pages.push({ type: 'text', paragraphs: paras.slice(idx), image: '' });
      }
    } else {
      var current = [];
      var len = 0;
      for (var j = 0; j < paras.length; j++) {
        if (current.length && len + paras[j].length > AUTO_PAGE_CHAR_LIMIT) {
          pages.push({ type: 'text', paragraphs: current, image: '' });
          current = [];
          len = 0;
        }
        current.push(paras[j]);
        len += paras[j].length;
      }
      if (current.length) pages.push({ type: 'text', paragraphs: current, image: '' });
    }

    if (data.details && (data.details.rows.length || data.details.fallbackHtml)) {
      pages.push({
        type: 'details',
        details: data.details,
        image: (config && config.details_image) || '',
      });
    }

    for (var k = 0; k < pages.length; k++) {
      if (!pages[k].image) pages[k].image = fallbackImage || '';
    }
    return pages;
  }

  /* ------------------------------------------------------------------ */
  /* Render                                                              */
  /* ------------------------------------------------------------------ */

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function chevronSvg(direction) {
    // Smukly szewron (sam grot) — bez linii, elegancki.
    var path = direction === 'prev'
      ? '<polyline points="15 5 8 12 15 19"/>'
      : '<polyline points="9 5 16 12 9 19"/>';
    return (
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.25" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      path +
      '</svg>'
    );
  }

  function buildTextPage(page, isFirst) {
    var node = el('div', 'giclee-story__page giclee-story__page--text');
    if (isFirst) node.classList.add('giclee-story__page--first');
    for (var i = 0; i < page.paragraphs.length; i++) {
      node.appendChild(el('p', 'giclee-story__paragraph', page.paragraphs[i]));
    }
    return node;
  }

  function buildDetailsPage(page) {
    var node = el('div', 'giclee-story__page giclee-story__page--details');
    var details = page.details;
    if (details.heading) {
      node.appendChild(el('div', 'giclee-story__details-heading', details.heading));
    }
    if (details.rows.length) {
      var list = el('dl', 'giclee-story__details-list');
      for (var i = 0; i < details.rows.length; i++) {
        if (isHiddenDetailLabel(details.rows[i].label)) continue;
        var row = el('div', 'giclee-story__details-row');
        row.appendChild(el('dt', 'giclee-story__details-label', details.rows[i].label));
        row.appendChild(el('dd', 'giclee-story__details-value', details.rows[i].value));
        list.appendChild(row);
      }
      if (list.childNodes.length) node.appendChild(list);
    } else {
      var raw = el('div', 'giclee-story__details-raw');
      raw.innerHTML = details.fallbackHtml;
      node.appendChild(raw);
    }
    return node;
  }

  function render(root, data, pages) {
    var inner = el('div', 'giclee-story__inner');
    var textCol = el('div', 'giclee-story__text');
    var mediaCol = el('div', 'giclee-story__media');

    // --- lewa kolumna -------------------------------------------------
    var counter = el('div', 'giclee-story__counter');
    counter.setAttribute('aria-live', 'polite');
    textCol.appendChild(counter);

    var header = el('header', 'giclee-story__header');
    var titleEl = null;
    if (data.header.title) {
      titleEl = el('h2', 'giclee-story__title', data.header.title);
      header.appendChild(titleEl);
    }
    if (data.header.artist) header.appendChild(el('div', 'giclee-story__artist', data.header.artist));
    if (data.header.dates) header.appendChild(el('div', 'giclee-story__dates', data.header.dates));
    textCol.appendChild(header);

    var pagesWrap = el('div', 'giclee-story__pages');
    var pageNodes = [];
    for (var i = 0; i < pages.length; i++) {
      var pageNode =
        pages[i].type === 'details' ? buildDetailsPage(pages[i]) : buildTextPage(pages[i], i === 0);
      pagesWrap.appendChild(pageNode);
      pageNodes.push(pageNode);
    }
    textCol.appendChild(pagesWrap);

    // --- szewrony po bokach sekcji ------------------------------------
    var prevBtn = el('button', 'giclee-story__chevron giclee-story__chevron--prev');
    prevBtn.type = 'button';
    prevBtn.innerHTML = chevronSvg('prev');
    prevBtn.setAttribute('aria-label', gicleeUi('story_prev', 'Poprzednia strona'));
    var nextBtn = el('button', 'giclee-story__chevron giclee-story__chevron--next');
    nextBtn.type = 'button';
    nextBtn.innerHTML = chevronSvg('next');
    nextBtn.setAttribute('aria-label', gicleeUi('story_next', 'Następna strona'));

    // --- prawa kolumna ------------------------------------------------
    var frame = el('div', 'giclee-story__frame');
    var imageNodes = [];
    for (var m = 0; m < pages.length; m++) {
      var img = document.createElement('img');
      img.className = 'giclee-story__image';
      img.src = pages[m].image;
      img.alt = data.header.title || '';
      img.loading = m === 0 ? 'eager' : 'lazy';
      img.decoding = 'async';
      frame.appendChild(img);
      imageNodes.push(img);
    }
    mediaCol.appendChild(frame);

    var dots = el('div', 'giclee-story__dots');
    var dotNodes = [];
    for (var d = 0; d < pages.length; d++) {
      var dot = el('button', 'giclee-story__dot');
      dot.type = 'button';
      dot.setAttribute(
        'aria-label',
        gicleeUi('story_page', 'Strona') + ' ' + (d + 1)
      );
      dots.appendChild(dot);
      dotNodes.push(dot);
    }
    mediaCol.appendChild(dots);

    inner.appendChild(textCol);
    inner.appendChild(mediaCol);
    inner.appendChild(prevBtn);
    inner.appendChild(nextBtn);
    root.appendChild(inner);

    // --- stan / nawigacja ---------------------------------------------
    var index = 0;

    function syncHeaderHeight() {
      var wasHidden = header.classList.contains('giclee-story__header--hidden');
      header.classList.add('giclee-story__header--instant');
      header.classList.remove('giclee-story__header--hidden');
      void header.offsetHeight;
      var measured = Math.max(header.offsetHeight, header.scrollHeight);
      if (measured > 0) {
        header.style.setProperty('--giclee-story-header-height', measured + 'px');
      }
      header.classList.remove('giclee-story__header--instant');
      if (wasHidden) header.classList.add('giclee-story__header--hidden');
    }

    function setHeaderHidden(hidden, instant) {
      instant =
        instant || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      header.classList.toggle('giclee-story__header--instant', !!instant);
      header.classList.toggle('giclee-story__header--hidden', hidden);
      if (hidden) {
        header.setAttribute('aria-hidden', 'true');
      } else {
        header.removeAttribute('aria-hidden');
      }
      if (instant) {
        window.requestAnimationFrame(function () {
          header.classList.remove('giclee-story__header--instant');
        });
      }
    }

    function findDetailsIndex() {
      for (var i = pages.length - 1; i >= 0; i--) {
        if (pages[i].type === 'details') return i;
      }
      return -1;
    }

    function syncChevronY() {
      var frameRect = frame.getBoundingClientRect();
      var innerRect = inner.getBoundingClientRect();
      if (!frameRect.height) return;
      var centerY = frameRect.top - innerRect.top + frameRect.height / 2;
      inner.style.setProperty('--giclee-story-chevron-top', centerY + 'px');
    }

    function setIndex(next, instant) {
      var max = pages.length - 1;
      index = Math.min(Math.max(next, 0), max);
      counter.textContent = index + 1 + ' / ' + pages.length;
      prevBtn.classList.toggle('is-hidden', index === 0);
      nextBtn.classList.toggle('is-hidden', index === max);
      var onDetails = pages[index].type === 'details';
      setHeaderHidden(onDetails, instant);
      for (var i = 0; i < pageNodes.length; i++) {
        pageNodes[i].classList.toggle('is-active', i === index);
        imageNodes[i].classList.toggle('is-active', i === index);
        dotNodes[i].classList.toggle('is-active', i === index);
        dotNodes[i].setAttribute('aria-current', i === index ? 'true' : 'false');
      }
      window.requestAnimationFrame(syncChevronY);
    }

    var lockStoryFrame = null;

    function lockStoryHeight() {
      if (lockStoryFrame) {
        window.cancelAnimationFrame(lockStoryFrame);
      }
      lockStoryFrame = window.requestAnimationFrame(function () {
        lockStoryFrame = null;
        var detailsIdx = findDetailsIndex();
        if (detailsIdx < 0) {
          setIndex(0);
          return;
        }

        var savedIndex = index;
        inner.style.height = 'auto';
        inner.style.removeProperty('--giclee-story-locked-height');
        setIndex(detailsIdx, true);

        var lockedHeight = inner.offsetHeight;
        inner.style.setProperty('--giclee-story-locked-height', lockedHeight + 'px');

        setIndex(savedIndex, true);
        syncChevronY();
      });
    }

    prevBtn.addEventListener('click', function () {
      setIndex(index - 1);
    });
    nextBtn.addEventListener('click', function () {
      setIndex(index + 1);
    });
    dotNodes.forEach(function (dot, i) {
      dot.addEventListener('click', function () {
        setIndex(i);
      });
    });

    syncHeaderHeight();
    lockStoryHeight();

    window.addEventListener('resize', function () {
      syncHeaderHeight();
      lockStoryHeight();
    }, { passive: true });
    if (typeof ResizeObserver !== 'undefined') {
      var chevronObserver = new ResizeObserver(syncChevronY);
      chevronObserver.observe(frame);
      chevronObserver.observe(textCol);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Scroll reveal (wlasny — sekcja budowana dynamicznie)                */
  /* ------------------------------------------------------------------ */

  function setupReveal(root) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      root.classList.add('is-revealed');
      return;
    }
    var rect = root.getBoundingClientRect();
    var vh = window.innerHeight || document.documentElement.clientHeight || 0;
    if (rect.bottom > 0 && rect.top < vh * 0.92) {
      window.requestAnimationFrame(function () {
        root.classList.add('is-revealed');
      });
      return;
    }
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
    );
    observer.observe(root);
  }

  /* ------------------------------------------------------------------ */
  /* Efekt: tlo konfiguratora jak w karuzeli (obraz + subtelny mouse     */
  /* parallax). Ustawienia: config_bg {enabled, image, parallax, blur,   */
  /* brightness} z window.__PDP_V3_EFFECTS__.                            */
  /* ------------------------------------------------------------------ */

  function isTouchLikeDevice() {
    return window.matchMedia('(hover: none), (pointer: coarse)').matches;
  }

  function initConfigBg(grid) {
    var cfg = pdpFx().config_bg || {};
    if (cfg.enabled === false) return;
    var src = cfg.image || '';
    if (!src || grid.querySelector('.pdp-v3-config-bg')) return;

    var bg = document.createElement('div');
    bg.className = 'pdp-v3-config-bg';
    bg.setAttribute('aria-hidden', 'true');
    bg.innerHTML =
      '<div class="pdp-v3-config-bg__layers">' +
      '<img class="pdp-v3-config-bg__image" alt="" decoding="async" loading="lazy">' +
      '</div>' +
      '<div class="pdp-v3-config-bg__overlay"></div>' +
      '<div class="pdp-v3-config-bg__gradient"></div>';
    bg.querySelector('.pdp-v3-config-bg__image').src = src;

    if (cfg.blur === false) bg.style.setProperty('--pdp-v3-cbg-blur', '0px');
    var brightness = parseInt(cfg.brightness, 10);
    if (brightness && brightness !== 100) {
      bg.style.setProperty('--pdp-v3-cbg-brightness', (brightness / 100).toFixed(2));
    }

    grid.insertBefore(bg, grid.firstChild);

    /* Subtelny parallax od myszy — jak w karuzeli (te same stale) */
    if (
      cfg.parallax === false ||
      isTouchLikeDevice() ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    var MAX_X = 22;
    var MAX_Y = 14;
    var EASE = 0.075;
    var layers = bg.querySelector('.pdp-v3-config-bg__layers');
    var targetX = 0;
    var targetY = 0;
    var curX = 0;
    var curY = 0;
    var rafId = 0;

    function tick() {
      rafId = 0;
      curX += (targetX - curX) * EASE;
      curY += (targetY - curY) * EASE;
      layers.style.setProperty('--pdp-v3-cbg-px', (-curX * MAX_X).toFixed(2) + 'px');
      layers.style.setProperty('--pdp-v3-cbg-py', (-curY * MAX_Y).toFixed(2) + 'px');
      if (Math.abs(targetX - curX) > 0.0008 || Math.abs(targetY - curY) > 0.0008) {
        rafId = window.requestAnimationFrame(tick);
      }
    }

    function startLoop() {
      if (!rafId) rafId = window.requestAnimationFrame(tick);
    }

    window.addEventListener(
      'pointermove',
      function (e) {
        var vw = window.innerWidth || 1;
        var vh = window.innerHeight || 1;
        targetX = Math.min(Math.max((e.clientX / vw) * 2 - 1, -1), 1);
        targetY = Math.min(Math.max((e.clientY / vh) * 2 - 1, -1), 1);
        startLoop();
      },
      { passive: true }
    );
    document.addEventListener(
      'pointerleave',
      function () {
        targetX = 0;
        targetY = 0;
        startLoop();
      },
      { passive: true }
    );
  }

  /* ------------------------------------------------------------------ */

  function initGridSlide() {
    var main = document.querySelector('main[data-template="product.szablon-produktu-v3"]');
    if (!main) return;
    var grid = main.querySelector('.product-information__grid');
    var story = main.querySelector('.giclee-product-story');
    var shell = main.querySelector('.product-information');
    if (!grid || !story || grid.dataset.gicleeGridSlideInit === '1') return;
    grid.dataset.gicleeGridSlideInit = '1';

    initConfigBg(grid);

    var pinWrap = document.createElement('div');
    pinWrap.className = 'giclee-grid-slide-pin';
    grid.parentNode.insertBefore(pinWrap, grid);

    var slotSpacer = document.createElement('div');
    slotSpacer.className = 'giclee-grid-slot-spacer';
    slotSpacer.setAttribute('aria-hidden', 'true');
    pinWrap.appendChild(slotSpacer);
    pinWrap.appendChild(grid);

    var holdTail = document.createElement('div');
    holdTail.className = 'giclee-grid-hold-tail';
    holdTail.setAttribute('aria-hidden', 'true');
    pinWrap.appendChild(holdTail);

    /* Pusty scroll pod sticky gridem — proces ma czas wjechac i zakryc
       konfigurator zanim pinWrap sie konczy (bez ujemnego marginu na wrapie). */
    var followerOverlap = document.createElement('div');
    followerOverlap.className = 'giclee-grid-follower-overlap';
    followerOverlap.setAttribute('aria-hidden', 'true');
    pinWrap.appendChild(followerOverlap);

    function applyFollowerOverlapHeight() {
      var vh = window.innerHeight || document.documentElement.clientHeight || 0;
      followerOverlap.style.height = Math.max(vh, 0) + 'px';
    }

    /* Opis przypina sie dolna krawedzia do dolu ekranu (bottom-anchored sticky).
       top = max(0, viewportH - storyH). Gdy opis wyzszy niz viewport -> 0 (jak
       klasyczny top:0). --pdp-v3-curtain-h = wysokosc kurtyny tla doczepionej
       do opisu (story::after): od gornej krawedzi opisu do konca shellu —
       wartosci z layoutu (stabilne miedzy klatkami), nie z pozycji scrolla. */
    function applyStoryStickyTop() {
      var vh = window.innerHeight || document.documentElement.clientHeight || 0;
      var storyH = story.offsetHeight || 0;
      var top = Math.max(0, vh - storyH);
      var target = shell || story;
      var curtainH = shell ? shell.offsetHeight - story.offsetTop : 0;
      target.style.setProperty('--pdp-v3-story-top', top + 'px');
      target.style.setProperty('--pdp-v3-curtain-h', Math.max(curtainH, vh) + 'px');
      return top;
    }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      grid.style.setProperty('--pdp-v3-grid-slide-x', '0px');
      applyStoryStickyTop();
      applyFollowerOverlapHeight();
      window.addEventListener('resize', applyStoryStickyTop, { passive: true });
      window.addEventListener('resize', applyFollowerOverlapHeight, { passive: true });
      return;
    }

    var ticking = false;
    var isFixed = false;
    var slideDistance = window.innerWidth || 1;
    var HOLD_PX = 240;

    /* Efekt: rozmycie R2 wraz z wjazdem opisu. Start dopiero gdy gorna
       krawedz opisu minie dol R2 (na starcie opis stoi tuz pod zoomem —
       wtedy blur = 0). Koniec przy pozycji przypiecia (stickyTop). */
    var zoomEl = main.querySelector('.giclee-product-zoom');
    var R2_BLUR_MAX = 10;
    var r2BlurOn = pdpFx().r2_blur !== false && !!zoomEl;
    var lastR2Blur = -1;

    function applyR2Blur(storyTop, stickyTop) {
      if (!r2BlurOn) return;
      var r2Bottom = zoomEl.getBoundingClientRect().bottom;

      /* Opis jeszcze nie wjechal w strefe R2 */
      if (storyTop >= r2Bottom - 0.5) {
        if (lastR2Blur === 0) return;
        lastR2Blur = 0;
        zoomEl.style.setProperty('--pdp-v3-r2-blur', '0px');
        return;
      }

      var blurEnd = Math.min(stickyTop, r2Bottom - 1);
      var range = Math.max(r2Bottom - blurEnd, 1);
      var p = Math.min(Math.max((r2Bottom - storyTop) / range, 0), 1);
      var blur = Math.round(p * R2_BLUR_MAX * 10) / 10;
      if (blur === lastR2Blur) return;
      lastR2Blur = blur;
      zoomEl.style.setProperty('--pdp-v3-r2-blur', blur + 'px');
    }

    /* Staly hold — nigdy nie zmieniany w update(): zwiniecie ogona przy
       odpieciu powodowalo nagly 240px skok tresci pod gridem. */
    holdTail.style.height = HOLD_PX + 'px';
    applyFollowerOverlapHeight();

    function smoothstep(t) {
      return t * t * (3 - 2 * t);
    }

    /* clientWidth (bez paska przewijania) — 100vw/50vw powodowaly ~8px
       poziomy skok przy przejsciu fixed -> sticky. */
    function applyMargins() {
      var rect = story.getBoundingClientRect();
      var cw = document.documentElement.clientWidth || window.innerWidth || 0;
      var padLeft = Math.max(rect.left, 0);
      grid.style.setProperty('--pdp-v3-grid-pad-left', padLeft + 'px');
      grid.style.setProperty('--pdp-v3-grid-pad-right', Math.max(cw - rect.right, 0) + 'px');
      grid.style.setProperty('--pdp-v3-grid-w', cw + 'px');
      grid.style.setProperty('--pdp-v3-grid-ml', -padLeft + 'px');
      slideDistance = cw || grid.offsetWidth || 1;
    }

    function setFixed(on) {
      if (on === isFixed) return;
      isFixed = on;
      if (on) {
        slotSpacer.style.height = grid.offsetHeight + 'px';
        grid.classList.add('is-grid-slide-fixed');
      } else {
        slotSpacer.style.height = '0px';
        grid.classList.remove('is-grid-slide-fixed');
      }
    }

    function setDocked(on) {
      if (!shell) return;
      shell.classList.toggle('is-grid-docked', on);
    }

    /* Histereza odpiecia fixed -> sticky: w strefie (0 .. -REFIX_PX) grid
       zostaje fixed top:0 (wizualnie identyczne ze sticky top:0). Flip przy
       dokladnie pinTop=0 psul scroll W GORE: kompozytor przewija o klatke
       przed rAF-em i sticky grid zjezdzal z pinWrap w dol (odbicie +
       przeswit opisu). Przy -REFIX_PX oba stany renderuja sie tak samo,
       wiec spozniona klasa niczego nie przesuwa. Musi byc < HOLD_PX, zeby
       sticky przejal zanim koniec pinWrap zacznie wypychac grid. */
    var REFIX_PX = Math.min(HOLD_PX - 40, 200);

    /*
     * Hybrid:
     *  1. Wjazd (pinTop > 0): fixed top:0 — TYLKO poziomo z prawej (bez skosu).
     *  2. Strefa histerezy (0 >= pinTop > -REFIX_PX): nadal fixed top:0.
     *  3. Glebiej: sticky + staly holdTail (240px pustego scrolla), potem
     *     grid wypychany w gore koncem pinWrap; followerOverlap (1×vh) daje
     *     scroll na overlay procesu nad gridem; trust (sticky, margin -100dvh)
     *     zakrywa proces. Opis zwalnia sticky od zadokowania — nie przeswituje.
     */
    function update() {
      ticking = false;

      var stickyTop = applyStoryStickyTop();
      var storyRect = story.getBoundingClientRect();
      var storyHeight = story.offsetHeight || window.innerHeight || 1;
      var pinRect = pinWrap.getBoundingClientRect();
      var pinTop = pinRect.top;
      var pinBottom = pinRect.bottom;

      applyR2Blur(storyRect.top, stickyTop);

      /* Bramka: opis nie doszedl jeszcze do pozycji przypiecia (bottom-anchored
         => pinuje przy storyRect.top === stickyTop, nie 0) */
      if (storyRect.top > stickyTop + 1) {
        if (shell) shell.classList.remove('is-scroll-normal');
        setDocked(false);
        setFixed(false);
        grid.classList.add('is-grid-slide-hidden');
        grid.classList.remove('is-grid-slide-active', 'is-grid-slide-done');
        grid.style.setProperty('--pdp-v3-grid-slide-x', slideDistance + 'px');
        return;
      }

      grid.classList.remove('is-grid-slide-hidden');
      applyMargins();

      if (pinBottom <= 0) {
        if (shell) shell.classList.add('is-scroll-normal');
        setDocked(true);
        setFixed(false);
        grid.classList.remove('is-grid-slide-active');
        grid.classList.add('is-grid-slide-done');
        grid.style.setProperty('--pdp-v3-grid-slide-x', '0px');
        return;
      }

      if (shell) shell.classList.remove('is-scroll-normal');

      /* Wjazd — fixed u gory, ruch tylko poziomy */
      if (pinTop > 0) {
        var t = smoothstep(1 - Math.min(Math.max(pinTop / storyHeight, 0), 1));
        setDocked(false);
        setFixed(true);
        grid.classList.add('is-grid-slide-active');
        grid.classList.remove('is-grid-slide-done');
        grid.style.setProperty('--pdp-v3-grid-slide-x', (1 - t) * slideDistance + 'px');
        return;
      }

      /* Strefa histerezy — zadokowany, ale wciaz fixed top:0 (== sticky) */
      if (pinTop > -REFIX_PX) {
        setDocked(true);
        setFixed(true);
        grid.classList.add('is-grid-slide-active', 'is-grid-slide-done');
        grid.style.setProperty('--pdp-v3-grid-slide-x', '0px');
        return;
      }

      /* Wjazd zakonczony — sticky przejmuje glebiej w holdzie (bez skoku) */
      setFixed(false);
      setDocked(true);
      grid.classList.add('is-grid-slide-active', 'is-grid-slide-done');
      grid.style.setProperty('--pdp-v3-grid-slide-x', '0px');
    }

    function scheduleUpdate() {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(update);
    }

    window.addEventListener('scroll', scheduleUpdate, { passive: true });
    window.addEventListener('resize', scheduleUpdate, { passive: true });
    window.addEventListener('resize', applyFollowerOverlapHeight, { passive: true });
    if (typeof ResizeObserver !== 'undefined') {
      var slideObserver = new ResizeObserver(scheduleUpdate);
      slideObserver.observe(story);
      slideObserver.observe(pinWrap);
    }
    scheduleUpdate();
  }

  function boot() {
    initGridSlide();

    var main = document.querySelector('main[data-template="product.szablon-produktu-v3"]');
    if (!main) return;
    var root = main.querySelector('[data-giclee-story]');
    var descRoot = main.querySelector('.product-description-below');
    if (!root || root.dataset.gicleeStoryInit === '1') return;
    root.dataset.gicleeStoryInit = '1';

    var data = descRoot ? parseDescription(descRoot) : null;
    if (!data || !data.paragraphs.length) {
      // Nierozpoznany format opisu — przywroc klasyczny opis, schowaj pusta sekcje.
      if (descRoot) descRoot.classList.remove('product-description-below--story-source');
      root.remove();
      return;
    }

    var config = readConfig(root);
    var fallbackImage = root.getAttribute('data-giclee-story-fallback-image') || '';
    var pages = buildPages(data, config, fallbackImage);
    if (!pages.length) {
      if (descRoot) descRoot.classList.remove('product-description-below--story-source');
      root.remove();
      return;
    }

    render(root, data, pages);
    setupReveal(root);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
