/* FAQ — GSAP: wejście hero (title + media) + tła pod hero + akordeonu + Style 2/3 Galaxy hover. */
(function () {
  if (window.__GICLEE_FAQ_ACCORDION_ENTRANCE__) return;
  window.__GICLEE_FAQ_ACCORDION_ENTRANCE__ = true;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var coarsePointer = window.matchMedia('(hover: none), (pointer: coarse)').matches;

  function getGsap() {
    return window.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  function getScrollTrigger() {
    return (
      window.ScrollTrigger ||
      (typeof ScrollTrigger !== 'undefined' ? ScrollTrigger : undefined)
    );
  }

  function getUnderHeroBgNodes() {
    return document.querySelectorAll('.faq-section .custom-section-background');
  }

  function getHeroMediaNodes() {
    return document.querySelectorAll('.hero .hero__media-grid');
  }

  function getAccordionItemNodes() {
    return document.querySelectorAll('.accordion accordion-custom');
  }

  function clearEntranceInline(/** @type {HTMLElement} */ el) {
    el.style.opacity = '';
    el.style.willChange = '';
  }

  function revealEntranceFallback() {
    getHeroTitleNodes().forEach(function (node) {
      clearEntranceInline(/** @type {HTMLElement} */ (node));
    });
    getHeroMediaNodes().forEach(function (node) {
      clearEntranceInline(/** @type {HTMLElement} */ (node));
    });
    getUnderHeroBgNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      clearEntranceInline(el);
      var section = el.closest('.faq-section');
      if (section instanceof HTMLElement) {
        section.style.removeProperty('background');
      }
    });
    getAccordionItemNodes().forEach(function (node) {
      clearEntranceInline(/** @type {HTMLElement} */ (node));
    });
    document.querySelectorAll('.accordion.faq-accordion-entering').forEach(function (node) {
      node.classList.remove('faq-accordion-entering');
    });
  }

  /**
   * @param {(api: GsapStatic) => void} callback
   * @param {() => void} [onTimeout]
   */
  function whenGsapReady(callback, onTimeout) {
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
      if (attempts >= 40) {
        window.clearInterval(timer);
        if (typeof onTimeout === 'function') onTimeout();
      }
    }, 50);
  }

  function getHeroTitleNodes() {
    return document.querySelectorAll(
      '.hero__content-wrapper :is(h1, h2, h3, h4, h5, h6)'
    );
  }

  /**
   * @param {HTMLElement} el
   * @param {Element} trigger
   * @param {GsapStatic} tween
   * @param {() => void} [onStart]
   * @param {() => void} [onComplete]
   */
  function playFadeInWhenVisible(el, trigger, tween, onStart, onComplete) {
    var play = function () {
      if (typeof onStart === 'function') onStart();
      tween.fromTo(
        el,
        { opacity: 0 },
        {
          opacity: 1,
          duration: 1.1,
          delay: 0.2,
          ease: 'power3.out',
          overwrite: 'auto',
          onComplete: function () {
            clearEntranceInline(el);
            if (typeof onComplete === 'function') onComplete();
          },
        }
      );
    };

    if (typeof IntersectionObserver === 'undefined') {
      play();
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          observer.disconnect();
          play();
        });
      },
      { threshold: 0 }
    );
    observer.observe(trigger);
  }

  /** Natychmiastowe ukrycie — bez FOUC zanim GSAP będzie gotowy (bez wpływu na layout). */
  function prepareFadeEntrances() {
    if (reduceMotion) return;

    getHeroTitleNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.faqHeroTitlePrepared) return;
      el.dataset.faqHeroTitlePrepared = '1';
      el.style.opacity = '0';
      el.style.willChange = 'opacity';
    });

    /* Grafika hero FAQ — bez fade-in, widoczna od razu. */

    getUnderHeroBgNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.faqUnderHeroBgPrepared) return;
      el.dataset.faqUnderHeroBgPrepared = '1';
      el.style.opacity = '0';
      el.style.willChange = 'opacity';

      /* Gradient maluje też na .faq-section — wyłączamy, żeby fade dotyczył warstwy tła. */
      var section = el.closest('.faq-section');
      if (
        section instanceof HTMLElement &&
        (section.classList.contains('faq-section--gradient-v1') ||
          section.classList.contains('faq-section--gradient-v2'))
      ) {
        section.style.setProperty('background', 'transparent', 'important');
      }
    });

    /* Akordeon czeka na koniec nagłówka — ukryty od razu, bez FOUC. */
    getAccordionItemNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.faqAccordionPrepared) return;
      el.dataset.faqAccordionPrepared = '1';
      el.style.opacity = '0';
      el.style.willChange = 'opacity';
      var accordion = el.closest('.accordion');
      if (accordion) accordion.classList.add('faq-accordion-entering');
    });
  }

  /**
   * Fade-in elementu (bez IntersectionObserver) — do sekwencji.
   * @param {HTMLElement} el
   * @param {GsapStatic} tween
   * @param {{ delay?: number, onComplete?: () => void }} [opts]
   */
  function playFadeIn(el, tween, opts) {
    var options = opts || {};
    tween.fromTo(
      el,
      { opacity: 0 },
      {
        opacity: 1,
        duration: 1.1,
        delay: typeof options.delay === 'number' ? options.delay : 0,
        ease: 'power3.out',
        overwrite: 'auto',
        onComplete: function () {
          clearEntranceInline(el);
          if (typeof options.onComplete === 'function') options.onComplete();
        },
      }
    );
  }

  /**
   * Wejście hero FAQ: grafika od razu (bez fade), potem fade nagłówka.
   * W połowie animacji nagłówka wywołuje onTitleMidpoint (start akordeonu).
   * @param {GsapStatic} tween
   * @param {() => void} [onTitleMidpoint]
   */
  function runHeroEntrance(/** @type {GsapStatic} */ tween, onTitleMidpoint) {
    var fadeDuration = 1.1;
    var titleDelay = 0.2;
    var titleMidFired = false;

    var notifyTitleMidpoint = function () {
      if (titleMidFired) return;
      titleMidFired = true;
      if (typeof onTitleMidpoint === 'function') onTitleMidpoint();
    };

    /* Media — bez animacji; wyczyść ewentualne inline z poprzednich wersji. */
    Array.prototype.slice.call(getHeroMediaNodes()).forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.faqHeroMediaEntranceBound) return;
      el.dataset.faqHeroMediaEntranceBound = '1';
      clearEntranceInline(el);
    });

    var titleNodes = Array.prototype.slice.call(getHeroTitleNodes()).filter(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.faqHeroTitleEntranceBound) return false;
      el.dataset.faqHeroTitleEntranceBound = '1';
      return true;
    });

    if (!titleNodes.length) {
      notifyTitleMidpoint();
      return;
    }

    var trigger =
      (titleNodes[0] && titleNodes[0].closest('.hero')) ||
      titleNodes[0];

    var play = function () {
      titleNodes.forEach(function (node) {
        playFadeIn(/** @type {HTMLElement} */ (node), tween, { delay: titleDelay });
      });
      /* Akordeon — w połowie animacji nagłówka. */
      tween.delayedCall(titleDelay + fadeDuration * 0.5, notifyTitleMidpoint);
    };

    if (typeof IntersectionObserver === 'undefined') {
      play();
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          observer.disconnect();
          play();
        });
      },
      { threshold: 0 }
    );
    observer.observe(trigger);
  }

  /**
   * Wejście tła pod hero FAQ — sam fade-in (grafika / gradient).
   * @param {GsapStatic} tween
   */
  function runUnderHeroBgEntrance(/** @type {GsapStatic} */ tween) {
    getUnderHeroBgNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var bg = /** @type {HTMLElement} */ (node);
      if (bg.dataset.faqUnderHeroBgEntranceBound) return;
      bg.dataset.faqUnderHeroBgEntranceBound = '1';

      var section = bg.closest('.faq-section') || bg;
      playFadeInWhenVisible(
        bg,
        section,
        tween,
        undefined,
        function () {
          if (section instanceof HTMLElement) {
            section.style.removeProperty('background');
          }
        }
      );
    });
  }

  function runAccordionEntrance(/** @type {GsapStatic} */ tween) {
    var items = getAccordionItemNodes();
    if (!items.length) return;

    items.forEach(function (el) {
      el.classList.add('list-item');
      var accordion = el.closest('.accordion');
      if (accordion) accordion.classList.add('faq-accordion-entering');
    });

    var clearEntering = function () {
      items.forEach(function (node) {
        clearEntranceInline(/** @type {HTMLElement} */ (node));
      });
      document.querySelectorAll('.accordion.faq-accordion-entering').forEach(function (node) {
        node.classList.remove('faq-accordion-entering');
      });
    };

    /* Fala góra→dół — start w połowie animacji nagłówka hero. */
    tween.fromTo(
      items,
      { opacity: 0 },
      {
        opacity: 1,
        duration: 0.8,
        stagger: {
          each: 0.07,
          from: 'start',
          ease: 'sine.inOut',
        },
        ease: 'sine.out',
        delay: 0.08,
        clearProps: 'opacity',
        overwrite: 'auto',
        onComplete: clearEntering,
      }
    );
  }

  /**
   * Hover na karcie: pozostałe się blurowują.
   * Po zejściu: powrót falą od aktywnej karty na zewnątrz (stagger).
   * @param {GsapStatic} tween
   */
  function initAccordionFocusBlur(/** @type {GsapStatic} */ tween) {
    if (reduceMotion || coarsePointer) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    document.querySelectorAll('.accordion').forEach(function (accordionNode) {
      if (!(accordionNode instanceof HTMLElement)) return;
      var accordion = accordionNode;
      if (accordion.dataset.faqFocusBlurBound) return;
      accordion.dataset.faqFocusBlurBound = '1';

      var cards = Array.prototype.slice.call(
        accordion.querySelectorAll('accordion-custom')
      );
      if (cards.length < 2) return;

      var activeIndex = -1;
      /** @type {GsapTimeline | null} */
      var leaveTl = null;

      /**
       * @param {number} index
       */
      var focusCard = function (index) {
        if (accordion.classList.contains('faq-accordion-entering')) return;
        if (leaveTl) {
          leaveTl.kill();
          leaveTl = null;
        }
        activeIndex = index;

        cards.forEach(function (card, i) {
          if (i === index) {
            tween.to(card, {
              filter: 'blur(0px)',
              opacity: 1,
              duration: 0.35,
              ease: 'power2.out',
              overwrite: 'auto',
            });
            card.style.zIndex = '2';
            card.style.position = 'relative';
          } else {
            tween.to(card, {
              filter: 'blur(3.5px)',
              opacity: 0.42,
              duration: 0.35,
              ease: 'power2.out',
              overwrite: 'auto',
            });
            card.style.zIndex = '';
          }
        });
      };

      var releaseAll = function () {
        if (activeIndex < 0) return;
        var from = activeIndex;
        activeIndex = -1;

        var ordered = cards
          .map(function (card, i) {
            return { card: card, i: i, dist: Math.abs(i - from) };
          })
          .sort(function (a, b) {
            return a.dist - b.dist || a.i - b.i;
          });

        var tl = tween.timeline({
          onComplete: function () {
            ordered.forEach(function (item) {
              tween.set(item.card, { clearProps: 'filter,opacity,zIndex,position' });
            });
            leaveTl = null;
          },
        });
        leaveTl = tl;

        ordered.forEach(function (item, rank) {
          tl.to(
            item.card,
            {
              filter: 'blur(0px)',
              opacity: 1,
              duration: 0.65,
              ease: 'power2.out',
              overwrite: 'auto',
            },
            rank * 0.07
          );
        });
      };

      cards.forEach(function (card, index) {
        card.addEventListener('mouseenter', function () {
          focusCard(index);
        });
      });
      accordion.addEventListener('mouseleave', releaseAll);
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
    var artOx = cs.getPropertyValue('--details-art-ox').trim();
    var artOy = cs.getPropertyValue('--details-art-oy').trim();
    var artPos = cs.getPropertyValue('--details-art-position').trim();
    if (artImage) wrap.style.setProperty('--details-art-image', artImage);
    if (artOx) wrap.style.setProperty('--details-art-ox', artOx);
    if (artOy) wrap.style.setProperty('--details-art-oy', artOy);
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

  /**
   * Subtelny parallax dekoracji — jak przy pierwszym wdrożeniu.
   * Lewa max +18px, prawa −14px, scrub 1.2; CSS top:50% + yPercent:-50.
   * @param {GsapStatic} tween
   */
  function initArtworkDecorationParallax(/** @type {GsapStatic} */ tween) {
    if (reduceMotion) return;

    var sections = document.querySelectorAll('.faq-section');
    if (!sections.length) return;

    var bind = function (/** @type {object} */ ScrollTriggerPlugin) {
      tween.registerPlugin(ScrollTriggerPlugin);

      sections.forEach(function (sectionNode) {
        if (!(sectionNode instanceof HTMLElement)) return;
        var section = sectionNode;
        var left = section.querySelector('.faq-artwork-decoration--left');
        var right = section.querySelector('.faq-disc--right');
        if (!left && !right) return;

        if (left instanceof HTMLElement) {
          tween.set(left, { yPercent: -50 });
          tween.to(left, {
            y: 18,
            ease: 'none',
            scrollTrigger: {
              trigger: section,
              start: 'top bottom',
              end: 'bottom top',
              scrub: 1.2,
            },
          });
        }

        if (right instanceof HTMLElement) {
          tween.set(right, { yPercent: -50 });
          tween.to(right, {
            y: -14,
            ease: 'none',
            scrollTrigger: {
              trigger: section,
              start: 'top bottom',
              end: 'bottom top',
              scrub: 1.2,
            },
          });
        }
      });
    };

    var existing = getScrollTrigger();
    if (existing) {
      bind(existing);
      return;
    }

    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      var next = getScrollTrigger();
      if (next) {
        window.clearInterval(timer);
        bind(next);
        return;
      }
      if (attempts >= 40) window.clearInterval(timer);
    }, 50);
  }

  function run() {
    initStyle2GalaxyHover();
    initStyle3GalaxyFull();
    if (reduceMotion) return;
    prepareFadeEntrances();
    whenGsapReady(
      /** @param {GsapStatic} tween */ function (tween) {
        var accordionStarted = false;
        var startAccordion = function () {
          if (accordionStarted) return;
          accordionStarted = true;
          runAccordionEntrance(tween);
        };
        runHeroEntrance(tween, startAccordion);
        runUnderHeroBgEntrance(tween);
        initAccordionFocusBlur(tween);
        initArtworkDecorationParallax(tween);
        /* Awaryjnie: jeśli hero nie wystartuje (IO), pokaż akordeon po chwili. */
        window.setTimeout(startAccordion, 4000);
      },
      revealEntranceFallback
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
