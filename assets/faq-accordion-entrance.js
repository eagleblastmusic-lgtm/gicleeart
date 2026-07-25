/* FAQ — GSAP: wejście akordeonu + Style 2/3 Galaxy hover. */
(function () {
  if (window.__GICLEE_FAQ_ACCORDION_ENTRANCE__) return;
  window.__GICLEE_FAQ_ACCORDION_ENTRANCE__ = true;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var coarsePointer = window.matchMedia('(hover: none), (pointer: coarse)').matches;

  function getGsap() {
    return window.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  /**
   * @param {(api: GsapStatic) => void} callback
   */
  function whenGsapReady(callback) {
    var existing = getGsap();
    if (existing) {
      callback(existing);
      return;
    }

    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      var api = getGsap();
      if (api) {
        window.clearInterval(timer);
        callback(api);
        return;
      }
      if (attempts >= 40) window.clearInterval(timer);
    }, 50);
  }

  function runAccordionEntrance(/** @type {GsapStatic} */ tween) {
    var items = document.querySelectorAll('.accordion accordion-custom');
    if (!items.length) return;

    items.forEach(function (el) {
      el.classList.add('list-item');
    });

    /* delay: synchronizacja z kurtyną page-transition (~0.8s po starcie open) */
    tween.from('.accordion .list-item', {
      duration: 0.8,
      y: 30,
      opacity: 0,
      stagger: 0.1,
      ease: 'power3.out',
      delay: 0.8,
    });
  }

  /**
   * Style 2: uproszczony świecący hover — radial CSS podąża za kursorem.
   */
  function initStyle2GalaxyHover() {
    if (reduceMotion || coarsePointer) return;

    var hosts = document.querySelectorAll('.faq-accordion-style2');
    if (!hosts.length) return;

    hosts.forEach(function (host) {
      var cards = host.querySelectorAll('.accordion accordion-custom details');
      cards.forEach(function (node) {
        if (!(node instanceof HTMLElement)) return;
        var card = node;
        if (card.dataset.faqGalaxyHoverBound) return;
        card.dataset.faqGalaxyHoverBound = '1';

        var rafId = 0;
        var targetX = 50;
        var targetY = 50;
        var currentX = 50;
        var currentY = 50;

        var apply = function () {
          card.style.setProperty('--faq-gx', currentX.toFixed(2) + '%');
          card.style.setProperty('--faq-gy', currentY.toFixed(2) + '%');
        };

        var tick = function () {
          rafId = 0;
          currentX += (targetX - currentX) * 0.22;
          currentY += (targetY - currentY) * 0.22;
          apply();
          if (Math.abs(targetX - currentX) > 0.15 || Math.abs(targetY - currentY) > 0.15) {
            rafId = window.requestAnimationFrame(tick);
          } else {
            currentX = targetX;
            currentY = targetY;
            apply();
          }
        };

        var kick = function () {
          if (!rafId) rafId = window.requestAnimationFrame(tick);
        };

        card.addEventListener('mousemove', /** @param {MouseEvent} event */ function (event) {
          var rect = card.getBoundingClientRect();
          var w = Math.max(rect.width, 1);
          var h = Math.max(rect.height, 1);
          targetX = Math.min(100, Math.max(0, ((event.clientX - rect.left) / w) * 100));
          targetY = Math.min(100, Math.max(0, ((event.clientY - rect.top) / h) * 100));
          kick();
        });

        card.addEventListener('mouseleave', function () {
          targetX = 50;
          targetY = 50;
          kick();
        });
      });
    });
  }

  /**
   * @param {string} tag
   * @param {string} className
   * @param {Record<string, string>} [attrs]
   */
  function el(tag, className, attrs) {
    var node = document.createElement(tag);
    node.className = className;
    if (attrs) {
      Object.keys(attrs).forEach(function (key) {
        var value = attrs[key];
        if (typeof value === 'string') node.setAttribute(key, value);
      });
    }
    return node;
  }

  /**
   * Style 3: Galaxy shell/plate + świecący pierścień na krawędzi (bez orbów / Lottie).
   * @param {HTMLElement} card
   */
  function mountStyle3GalaxyCard(card) {
    if (card.dataset.faqGalaxyFullBound) return;
    card.dataset.faqGalaxyFullBound = '1';

    var parent = card.parentNode;
    if (!parent) return;

    var wrap = el('div', 'faq-galaxy-card');
    if (card.classList.contains('details--art')) wrap.classList.add('faq-galaxy-card--art');
    if (card.classList.contains('details--art-shared')) wrap.classList.add('faq-galaxy-card--art-shared');

    var cs = window.getComputedStyle(card);
    var artImage = cs.getPropertyValue('--details-art-image').trim();
    var artPos = cs.getPropertyValue('--details-art-position').trim();
    if (artImage) wrap.style.setProperty('--details-art-image', artImage);
    if (artPos) wrap.style.setProperty('--details-art-position', artPos);

    var shell = el('span', 'faq-galaxy-card__shell', { 'aria-hidden': 'true' });
    shell.appendChild(el('span', 'faq-galaxy-card__plate'));
    var edge = el('span', 'faq-galaxy-card__edge', { 'aria-hidden': 'true' });

    parent.insertBefore(wrap, card);
    wrap.appendChild(shell);
    wrap.appendChild(edge);
    wrap.appendChild(card);

    if (reduceMotion || coarsePointer) return;

    var rafId = 0;
    var targetX = 50;
    var targetY = 50;
    var currentX = 50;
    var currentY = 50;

    var apply = function () {
      wrap.style.setProperty('--faq-gx', currentX.toFixed(2) + '%');
      wrap.style.setProperty('--faq-gy', currentY.toFixed(2) + '%');
    };

    var tick = function () {
      rafId = 0;
      currentX += (targetX - currentX) * 0.22;
      currentY += (targetY - currentY) * 0.22;
      apply();
      if (Math.abs(targetX - currentX) > 0.15 || Math.abs(targetY - currentY) > 0.15) {
        rafId = window.requestAnimationFrame(tick);
      } else {
        currentX = targetX;
        currentY = targetY;
        apply();
      }
    };

    var kick = function () {
      if (!rafId) rafId = window.requestAnimationFrame(tick);
    };

    wrap.addEventListener('mousemove', /** @param {MouseEvent} event */ function (event) {
      var rect = wrap.getBoundingClientRect();
      var w = Math.max(rect.width, 1);
      var h = Math.max(rect.height, 1);
      targetX = Math.min(100, Math.max(0, ((event.clientX - rect.left) / w) * 100));
      targetY = Math.min(100, Math.max(0, ((event.clientY - rect.top) / h) * 100));
      kick();
    });

    wrap.addEventListener('mouseleave', function () {
      targetX = 50;
      targetY = 50;
      kick();
    });
  }

  function initStyle3GalaxyFull() {
    var hosts = document.querySelectorAll('.faq-accordion-style3');
    if (!hosts.length) return;

    hosts.forEach(function (hostNode) {
      if (!(hostNode instanceof HTMLElement)) return;
      var cards = hostNode.querySelectorAll('.accordion accordion-custom details');
      cards.forEach(function (node) {
        if (!(node instanceof HTMLElement)) return;
        mountStyle3GalaxyCard(node);
      });
    });
  }

  function run() {
    initStyle2GalaxyHover();
    initStyle3GalaxyFull();
    if (reduceMotion) return;
    whenGsapReady(/** @param {GsapStatic} tween */ function (tween) {
      runAccordionEntrance(tween);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
