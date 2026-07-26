/* FAQ — GSAP: wejście hero (title) + akordeonu + Style 2/3 Galaxy hover. Tło pod hero bez fade-in. */
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

    /* Grafika hero + tło pod hero FAQ — bez fade-in, widoczne od razu. */

    /* Akordeon czeka na otwarcie kurtyny — ukryty od razu, bez FOUC. */
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
   * @param {GsapStatic} tween
   */
  function runHeroEntrance(/** @type {GsapStatic} */ tween) {
    var titleDelay = 0.2;

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

    if (!titleNodes.length) return;

    var trigger =
      (titleNodes[0] && titleNodes[0].closest('.hero')) ||
      titleNodes[0];

    var play = function () {
      titleNodes.forEach(function (node) {
        playFadeIn(/** @type {HTMLElement} */ (node), tween, { delay: titleDelay });
      });
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
   * Start akordeonu wraz z otwieraniem kurtyny (#page-transition.opening).
   * Jeśli kurtyna już się otwiera / otworzyła (skrypt FAQ doładował się później) — od razu.
   * @param {() => void} callback
   */
  function whenCurtainOpening(callback) {
    var done = false;
    var run = function () {
      if (done) return;
      done = true;
      window.removeEventListener('giclee:curtain-opening', run);
      callback();
    };

    var overlay = document.getElementById('page-transition');
    if (
      !overlay ||
      overlay.hidden ||
      overlay.classList.contains('opening') ||
      (!overlay.classList.contains('pt-init') &&
        !overlay.classList.contains('closing') &&
        !overlay.classList.contains('active'))
    ) {
      run();
      return;
    }

    window.addEventListener('giclee:curtain-opening', run);
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
      var hoveredIndex = -1;
      var persistentIndex = -1;
      /** @type {GsapTimeline | null} */
      var leaveTl = null;

      var findOpenIndex = function () {
        var found = -1;
        cards.forEach(function (card, index) {
          var details = card.querySelector('details');
          if (details instanceof HTMLDetailsElement && details.open) {
            found = index;
          }
        });
        return found;
      };

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
              duration: 0.45,
              ease: 'sine.out',
              overwrite: 'auto',
            });
            card.style.zIndex = '2';
            card.style.position = 'relative';
          } else {
            tween.to(card, {
              filter: 'blur(3.5px)',
              opacity: 0.42,
              duration: 0.45,
              ease: 'sine.out',
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

        if (leaveTl) {
          leaveTl.kill();
          leaveTl = null;
        }

        var tl = tween.timeline({
          defaults: {
            ease: 'sine.out',
            overwrite: 'auto',
          },
          onComplete: function () {
            cards.forEach(function (card) {
              tween.set(card, {
                filter: 'blur(0px)',
                opacity: 1,
                clearProps: 'zIndex,position',
              });
            });
            leaveTl = null;
          },
        });
        leaveTl = tl;

        /* Jedna fala od aktywnej karty — dłużej, miękko, bez skoku clearProps na filtrze */
        tl.to(cards, {
          filter: 'blur(0px)',
          opacity: 1,
          duration: 0.95,
          stagger: {
            each: 0.055,
            from: Math.max(0, from),
          },
        });
      };

      cards.forEach(function (card, index) {
        card.addEventListener('mouseenter', function () {
          hoveredIndex = index;
          focusCard(index);
        });

        var details = card.querySelector('details');
        if (!(details instanceof HTMLDetailsElement)) return;
        if (details.open) persistentIndex = index;

        details.addEventListener('toggle', function () {
          if (details.open) {
            persistentIndex = index;
            focusCard(index);
            return;
          }

          if (persistentIndex === index) {
            persistentIndex = findOpenIndex();
          }
          if (hoveredIndex >= 0) {
            focusCard(hoveredIndex);
          } else if (persistentIndex >= 0) {
            focusCard(persistentIndex);
          } else {
            releaseAll();
          }
        });
      });
      accordion.addEventListener('mouseleave', function () {
        hoveredIndex = -1;
        persistentIndex = findOpenIndex();
        if (persistentIndex >= 0) {
          focusCard(persistentIndex);
        } else {
          releaseAll();
        }
      });

      if (persistentIndex >= 0) {
        focusCard(persistentIndex);
      }
    });
  }

  /*
   * Otwarcie dowolnego pytania płynnie przenosi widok na koniec strony.
   * Zamknięcie nie ingeruje w pozycję scrolla.
   */
  var faqPageScrollRaf = 0;
  var restoreFaqScrollBehavior = null;
  var faqScrollEnergyCycle = 0;
  var faqScrollEnergyTimer = 0;

  function startFaqScrollEnergyAnimation() {
    if (window.location.search.indexOf('faq-perf-no-energy=1') !== -1) return;
    var section = document.querySelector('.faq-section');
    if (!(section instanceof HTMLElement)) return;
    faqScrollEnergyCycle = faqScrollEnergyCycle ? 0 : 1;
    var nextClass = faqScrollEnergyCycle
      ? 'faq-scroll-energy-a'
      : 'faq-scroll-energy-b';
    section.classList.remove(
      'faq-scroll-energy-a',
      'faq-scroll-energy-b'
    );
    section.classList.add(nextClass);
    window.clearTimeout(faqScrollEnergyTimer);
    faqScrollEnergyTimer = window.setTimeout(function () {
      section.classList.remove(nextClass);
    }, 1180);
  }

  /**
   * Przewijanie kontrolowane przez rAF zapewnia stały, mierzalny czas ruchu.
   * Natywne behavior:smooth kończyło krótki zakres FAQ już po około 230 ms.
   * @param {number} targetY
   * @param {() => void} [onComplete]
   */
  function animateFaqPageScroll(targetY, onComplete) {
    if (faqPageScrollRaf) {
      window.cancelAnimationFrame(faqPageScrollRaf);
      faqPageScrollRaf = 0;
    }
    if (restoreFaqScrollBehavior) restoreFaqScrollBehavior();

    var startY = window.scrollY;
    var distance = targetY - startY;
    if (reduceMotion || Math.abs(distance) <= 1) {
      window.scrollTo(0, targetY);
      if (onComplete) onComplete();
      return;
    }
    startFaqScrollEnergyAnimation();

    var root = document.documentElement;
    var previousBehavior = root.style.getPropertyValue('scroll-behavior');
    var previousPriority = root.style.getPropertyPriority('scroll-behavior');
    var restored = false;
    restoreFaqScrollBehavior = function () {
      if (restored) return;
      restored = true;
      if (previousBehavior) {
        root.style.setProperty(
          'scroll-behavior',
          previousBehavior,
          previousPriority
        );
      } else {
        root.style.removeProperty('scroll-behavior');
      }
      restoreFaqScrollBehavior = null;
    };
    root.style.setProperty('scroll-behavior', 'auto', 'important');

    var startTime = 0;
    var duration = 760;
    var frameTimes = [];
    var measureFrames =
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === 'localhost' ||
      window.location.search.indexOf('faq-perf=1') !== -1;
    var frame = function (timestamp) {
      if (!startTime) startTime = timestamp;
      if (measureFrames) frameTimes.push(timestamp);
      var progress = Math.min(1, (timestamp - startTime) / duration);
      var eased =
        progress * progress * progress *
        (progress * (progress * 6 - 15) + 10);

      window.scrollTo(0, startY + distance * eased);
      if (progress < 1) {
        faqPageScrollRaf = window.requestAnimationFrame(frame);
        return;
      }

      faqPageScrollRaf = 0;
      window.scrollTo(0, targetY);
      if (restoreFaqScrollBehavior) restoreFaqScrollBehavior();
      if (frameTimes.length > 1) {
        var deltas = frameTimes.slice(1).map(function (time, index) {
          return time - frameTimes[index];
        });
        var average =
          deltas.reduce(function (sum, delta) {
            return sum + delta;
          }, 0) / deltas.length;
        var sorted = deltas.slice().sort(function (a, b) {
          return a - b;
        });
        console.info(
          '[FAQ page-scroll performance] ' +
          JSON.stringify({
            fps: Number((1000 / average).toFixed(1)),
            frames: frameTimes.length,
            durationMs: Number(
              (frameTimes[frameTimes.length - 1] - frameTimes[0]).toFixed(1)
            ),
            averageFrameMs: Number(average.toFixed(2)),
            medianFrameMs: Number(
              sorted[Math.floor(sorted.length * 0.5)].toFixed(2)
            ),
            p95FrameMs: Number(
              sorted[
                Math.min(
                  sorted.length - 1,
                  Math.floor(sorted.length * 0.95)
                )
              ].toFixed(2)
            ),
            framesOver20Ms: deltas.filter(function (delta) {
              return delta > 20;
            }).length,
          })
        );
      }
      if (onComplete) onComplete();
    };

    faqPageScrollRaf = window.requestAnimationFrame(frame);
  }

  function initFaqScrollToBottomOnOpen() {
    document
      .querySelectorAll('.faq-section .accordion details')
      .forEach(function (detailsNode) {
        if (!(detailsNode instanceof HTMLDetailsElement)) return;
        var details = detailsNode;
        if (details.dataset.faqScrollToBottomBound) return;
        details.dataset.faqScrollToBottomBound = '1';

        details.addEventListener('toggle', function () {
          if (!details.open) return;
          window.requestAnimationFrame(function () {
            animateFaqPageScroll(
              Math.max(
                0,
                document.documentElement.scrollHeight - window.innerHeight
              )
            );
          });
        });
      });
  }

  /*
   * Jeden impuls kółka przewija krótką stronę FAQ do odpowiedniej krawędzi:
   * w dół do końca, a w górę do początku. Blokada zapobiega ponownemu
   * uruchamianiu przez kolejne impulsy tej samej bezwładności myszy lub touchpada.
   */
  function initFaqSingleWheelPageSnap() {
    var wheelScrollActive = false;
    var releaseTimer = 0;

    window.addEventListener(
      'wheel',
      function (event) {
        if (event.deltaY === 0) return;
        var pageBottom = Math.max(
          0,
          document.documentElement.scrollHeight - window.innerHeight
        );
        var targetY = event.deltaY > 0 ? pageBottom : 0;
        if (Math.abs(window.scrollY - targetY) <= 1) return;

        event.preventDefault();
        if (wheelScrollActive) return;
        wheelScrollActive = true;

        animateFaqPageScroll(targetY, function () {
          window.clearTimeout(releaseTimer);
          releaseTimer = window.setTimeout(function () {
            wheelScrollActive = false;
          }, 90);
        });

        window.clearTimeout(releaseTimer);
        releaseTimer = window.setTimeout(function () {
          wheelScrollActive = false;
        }, reduceMotion ? 80 : 950);
      },
      { passive: false, capture: true }
    );
  }

  /*
   * Gdy jedno pytanie jest otwarte, pozostałe są całkowicie nieinteraktywne.
   * Najpierw trzeba zamknąć aktywną kartę; dopiero wtedy można otworzyć inną.
   */
  function initFaqSingleOpenLock() {
    document.querySelectorAll('.faq-section .accordion').forEach(function (node) {
      if (!(node instanceof HTMLElement)) return;
      var accordion = node;
      if (accordion.dataset.faqSingleOpenLockBound) return;
      accordion.dataset.faqSingleOpenLockBound = '1';

      var cards = Array.prototype.slice.call(
        accordion.querySelectorAll(':scope > accordion-custom')
      );
      if (!cards.length) return;

      var applyLock = function () {
        var openCard = null;
        cards.some(function (card) {
          var details = card.querySelector('details');
          if (details instanceof HTMLDetailsElement && details.open) {
            openCard = card;
            return true;
          }
          return false;
        });

        cards.forEach(function (card) {
          if (!(card instanceof HTMLElement)) return;
          var locked = openCard instanceof HTMLElement && card !== openCard;
          card.toggleAttribute('inert', locked);
          card.dataset.faqLocked = locked ? '1' : '0';

          var summary = card.querySelector('summary');
          if (!(summary instanceof HTMLElement)) return;
          if (locked) {
            summary.setAttribute('aria-disabled', 'true');
            summary.setAttribute('tabindex', '-1');
          } else {
            summary.removeAttribute('aria-disabled');
            summary.removeAttribute('tabindex');
          }
        });
      };

      cards.forEach(function (card) {
        var details = card.querySelector('details');
        if (!(details instanceof HTMLDetailsElement)) return;
        details.addEventListener('toggle', applyLock);
      });

      applyLock();
    });
  }

  /*
   * Dolna świetlista kreska jest wizualnie przywiązana do ostatniej karty.
   * Kontener akordeonu ma zamrożoną wysokość, więc pozycję przepełnionej
   * karty trzeba śledzić osobno podczas animacji details.
   */
  function ensureFaqAccordionTail(accordion) {
    var existing = accordion.querySelector(':scope > .faq-accordion-tail');
    if (existing instanceof HTMLElement) return existing;
    var tail = document.createElement('span');
    tail.className = 'faq-accordion-tail';
    tail.setAttribute('aria-hidden', 'true');
    tail.faqScrollY = 0;
    tail.faqOpenY = 0;
    accordion.appendChild(tail);
    return tail;
  }

  function setFaqAccordionTailOffset(tail, component, value) {
    if (component === 'scroll') {
      tail.faqScrollY = value;
    } else {
      tail.faqOpenY = value;
    }
    var scrollY = tail.faqScrollY || 0;
    var openY = tail.faqOpenY || 0;
    tail.style.transform =
      'translate3d(0, ' + (scrollY + openY).toFixed(2) + 'px, 0)';
  }

  function initFaqAccordionTailTracking() {
    document.querySelectorAll('.faq-section .accordion').forEach(function (node) {
      if (!(node instanceof HTMLElement)) return;
      var accordion = node;
      if (accordion.dataset.faqTailTrackingBound) return;
      accordion.dataset.faqTailTrackingBound = '1';

      var cards = accordion.querySelectorAll(':scope > accordion-custom');
      if (!cards.length) return;
      var lastCard = cards[cards.length - 1];
      if (!(lastCard instanceof HTMLElement)) return;
      var tail = ensureFaqAccordionTail(accordion);

      var baselineBottom =
        lastCard.getBoundingClientRect().bottom -
        accordion.getBoundingClientRect().top;
      var rafId = 0;
      var stableFrames = 0;
      var previousOffset = NaN;
      var stopAfter = 0;

      var track = function (timestamp) {
        rafId = 0;
        var offset =
          lastCard.getBoundingClientRect().bottom -
          accordion.getBoundingClientRect().top -
          baselineBottom -
          (tail.faqScrollY || 0);
        setFaqAccordionTailOffset(tail, 'open', offset);
        accordion.dispatchEvent(new CustomEvent('faq:tail-move'));

        if (Number.isFinite(previousOffset) &&
            Math.abs(offset - previousOffset) < 0.04) {
          stableFrames += 1;
        } else {
          stableFrames = 0;
        }
        previousOffset = offset;

        if (stableFrames < 8 && timestamp < stopAfter) {
          rafId = window.requestAnimationFrame(track);
        }
      };

      var startTracking = function () {
        stableFrames = 0;
        previousOffset = NaN;
        stopAfter = window.performance.now() + (reduceMotion ? 100 : 2400);
        if (!rafId) rafId = window.requestAnimationFrame(track);
      };

      accordion.querySelectorAll('details').forEach(function (details) {
        details.addEventListener('toggle', startTracking);
      });
    });
  }

  /*
   * Dekoracje leżą pod warstwą treści i nie przechwytują wskaźnika.
   * Hit-test wykonywany na dokumencie pozwala rozświetlać same pierścienie
   * oraz dolną kreskę bez blokowania akordeonów.
   */
  function initFaqDecorationHoverGlow() {
    var section = document.querySelector('.faq-section');
    if (!(section instanceof HTMLElement)) return;
    if (section.dataset.faqDecorationHoverBound) return;
    section.dataset.faqDecorationHoverBound = '1';

    var left = section.querySelector('.faq-artwork-decoration--left');
    var right = section.querySelector('.faq-disc--right');
    var accordion = section.querySelector('.accordion');
    if (!(left instanceof HTMLElement) &&
        !(right instanceof HTMLElement) &&
        !(accordion instanceof HTMLElement)) return;

    var pointerX = -10000;
    var pointerY = -10000;
    var rafId = 0;
    var scrollHoverTimer = 0;
    var tailHoverTimer = 0;

    /**
     * @param {HTMLElement} element
     * @param {boolean} active
     */
    var setHovered = function (element, active) {
      element.classList.toggle('is-faq-decoration-hovered', active);
    };

    /**
     * @param {DOMRect} rect
     * @param {number} x
     * @param {number} y
     */
    var hitsLeftRings = function (rect, x, y) {
      if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
        return false;
      }

      var scale = Math.max(rect.width / 600, rect.height / 900);
      var offsetX = (rect.width - 600 * scale) / 2;
      var offsetY = (rect.height - 900 * scale) / 2;
      var svgX = (x - rect.left - offsetX) / scale;
      var svgY = (y - rect.top - offsetY) / scale;
      var rings = [
        [-35, 450, 405, 350],
        [-40, 450, 320, 278],
        [-48, 450, 262, 228],
      ];

      return rings.some(function (ring) {
        var dx = (svgX - ring[0]) / ring[2];
        var dy = (svgY - ring[1]) / ring[3];
        return Math.abs(Math.sqrt(dx * dx + dy * dy) - 1) <= 0.055;
      });
    };

    /**
     * @param {DOMRect} rect
     * @param {number} x
     * @param {number} y
     */
    var hitsRightRings = function (rect, x, y) {
      if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
        return false;
      }

      var centerX = rect.left + rect.width / 2;
      var centerY = rect.top + rect.height / 2;
      return [0, 0.05, 0.1].some(function (inset) {
        var rx = rect.width * (0.5 - inset);
        var ry = rect.height * (0.5 - inset);
        var dx = (x - centerX) / rx;
        var dy = (y - centerY) / ry;
        return Math.abs(Math.sqrt(dx * dx + dy * dy) - 1) <= 0.035;
      });
    };

    /**
     * @param {HTMLElement} element
     * @param {number} x
     * @param {number} y
     */
    var hitsAccordionTail = function (element, x, y) {
      var tail = element.querySelector(':scope > .faq-accordion-tail');
      if (!(tail instanceof HTMLElement)) return false;
      var rect = tail.getBoundingClientRect();
      var width = Math.min(760, rect.width * 0.84);
      var top = rect.top - 5;
      return (
        x >= rect.left + (rect.width - width) / 2 &&
        x <= rect.right - (rect.width - width) / 2 &&
        y >= top &&
        y <= top + 32
      );
    };

    var renderHover = function () {
      rafId = 0;
      if (left instanceof HTMLElement) {
        setHovered(left, hitsLeftRings(left.getBoundingClientRect(), pointerX, pointerY));
      }
      if (right instanceof HTMLElement) {
        setHovered(right, hitsRightRings(right.getBoundingClientRect(), pointerX, pointerY));
      }
      if (accordion instanceof HTMLElement) {
        setHovered(accordion, hitsAccordionTail(accordion, pointerX, pointerY));
      }
    };

    var scheduleHover = function () {
      if (!rafId) rafId = window.requestAnimationFrame(renderHover);
    };

    document.addEventListener(
      'pointermove',
      function (event) {
        pointerX = event.clientX;
        pointerY = event.clientY;
        scheduleHover();
      },
      { passive: true }
    );
    document.addEventListener('pointerleave', function () {
      pointerX = -10000;
      pointerY = -10000;
      scheduleHover();
    });
    window.addEventListener(
      'scroll',
      function () {
        window.clearTimeout(scrollHoverTimer);
        scrollHoverTimer = window.setTimeout(scheduleHover, 120);
      },
      { passive: true }
    );
    window.addEventListener('resize', scheduleHover, { passive: true });
    if (accordion instanceof HTMLElement) {
      accordion.addEventListener('faq:tail-move', function () {
        window.clearTimeout(tailHoverTimer);
        tailHoverTimer = window.setTimeout(scheduleHover, 60);
      });
    }
  }

  /*
   * Lokalny pomiar częstotliwości rAF bez animowania elementów. Pozwala
   * odróżnić koszt efektów FAQ od limitu odświeżania samego podglądu.
   */
  function initFaqIdlePerformanceProbe() {
    var enabled =
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === 'localhost' ||
      window.location.search.indexOf('faq-perf=1') !== -1;
    if (!enabled || document.documentElement.dataset.faqIdleProbeBound) return;
    document.documentElement.dataset.faqIdleProbeBound = '1';

    window.setTimeout(function () {
      var frames = [];
      var frame = function (timestamp) {
        frames.push(timestamp);
        if (frames.length < 2 || timestamp - frames[0] < 1200) {
          window.requestAnimationFrame(frame);
          return;
        }

        var deltas = frames.slice(1).map(function (time, index) {
          return time - frames[index];
        });
        var sorted = deltas.slice().sort(function (a, b) {
          return a - b;
        });
        var average =
          deltas.reduce(function (sum, delta) {
            return sum + delta;
          }, 0) / deltas.length;
        var p95 =
          sorted[
            Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))
          ];
        console.info(
          '[FAQ idle performance] ' +
          JSON.stringify({
            fps: Number((1000 / average).toFixed(1)),
            frames: frames.length,
            averageFrameMs: Number(average.toFixed(2)),
            medianFrameMs: Number(
              sorted[Math.floor(sorted.length * 0.5)].toFixed(2)
            ),
            p95FrameMs: Number(p95.toFixed(2)),
            framesOver20Ms: deltas.filter(function (delta) {
              return delta > 20;
            }).length,
          })
        );
      };
      window.requestAnimationFrame(frame);
    }, 1800);
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

  /*
   * Podczas scrollowania wysuwa tło FAQ ku górze, bez przesuwania akordeonu.
   * Ujemny margin wrappera i równy padding sekcji wzajemnie się kompensują,
   * więc zmienia się wyłącznie górna krawędź tła.
   */
  function initFaqBackgroundScrollExpansion() {
    var wrapper = document.querySelector(
      '#MainContent > .shopify-section:has(.faq-section)'
    );
    if (!(wrapper instanceof HTMLElement)) return;
    if (wrapper.dataset.faqScrollBgExpansionBound) return;
    wrapper.dataset.faqScrollBgExpansionBound = '1';

    var section = wrapper.querySelector('.faq-section');
    if (!(section instanceof HTMLElement)) return;
    var heroWrapper = document.querySelector(
      '#MainContent > .shopify-section:has(.hero)'
    );

    var scrollRange = Math.max(
      1,
      document.documentElement.scrollHeight - window.innerHeight
    );
    var maxHeroOffset = Math.min(36, scrollRange * 0.18);
    var sectionDocumentTop =
      wrapper.getBoundingClientRect().top + window.scrollY;
    var stickyHeader = document.querySelector(
      'header.header-section, #header-component'
    );
    var stickyHeaderHeight = stickyHeader instanceof HTMLElement
      ? stickyHeader.getBoundingClientRect().height
      : 0;
    var maxBackgroundExtension = Math.max(
      0,
      sectionDocumentTop -
        scrollRange -
        stickyHeaderHeight +
        1
    );
    var accordion = section.querySelector('.accordion');
    var accordionTail = accordion instanceof HTMLElement
      ? ensureFaqAccordionTail(accordion)
      : null;
    var accordionItems = accordion instanceof HTMLElement
      ? Array.prototype.slice.call(
          accordion.querySelectorAll(':scope > accordion-custom')
        )
      : [];
    var maxAccordionOffset = 0;
    if (accordion instanceof HTMLElement) {
      var accordionRect = accordion.getBoundingClientRect();
      /*
       * Zamknięta wysokość pozostaje wysokością przepływu dokumentu.
       * Otwarta odpowiedź przesuwa następne karty wewnątrz tego kadru,
       * ale nie wydłuża sekcji ani nie tworzy nowego zakresu scrollowania.
       */
      accordion.style.setProperty(
        '--faq-accordion-flow-height',
        accordionRect.height.toFixed(2) + 'px'
      );
      accordion.style.setProperty(
        'block-size',
        accordionRect.height.toFixed(2) + 'px',
        'important'
      );
      accordion.style.setProperty(
        'max-block-size',
        accordionRect.height.toFixed(2) + 'px',
        'important'
      );
      accordion.style.setProperty('min-block-size', '0', 'important');
      var accordionDocumentCenter =
        (accordionRect.top + accordionRect.bottom) * 0.5 + window.scrollY;
      /*
       * Pozycja końcowa odnosi się do 50% viewportu, nie do środka sekcji,
       * której górna krawędź i wysokość zmieniają się podczas scrollowania.
       */
      maxAccordionOffset =
        window.innerHeight * 0.5 -
        (accordionDocumentCenter - scrollRange);
    }
    var clampProgress = function (value) {
      return Math.min(1, Math.max(0, value));
    };
    var easeProgress = function (progress) {
      /* Smootherstep: zerowa prędkość i przyspieszenie na obu końcach. */
      return (
        progress * progress * progress *
        (progress * (progress * 6 - 15) + 10)
      );
    };
    var damp = function (current, target, deltaMs, duration) {
      return target + (current - target) * Math.exp(-deltaMs / duration);
    };

    var targetProgress = clampProgress(window.scrollY / scrollRange);
    var heroProgress = targetProgress;
    var accordionProgress = targetProgress;
    var itemProgresses = accordionItems.map(function () {
      return targetProgress;
    });
    var rafId = 0;
    var lastFrameTime = 0;
    var performanceProbe = null;
    var performanceProbeRafId = 0;
    var performanceProbeEnabled =
      window.location.hostname === '127.0.0.1' ||
      window.location.hostname === 'localhost' ||
      window.location.search.indexOf('faq-perf=1') !== -1;
    var performanceDisableHero =
      window.location.search.indexOf('faq-perf-no-hero=1') !== -1;
    var performanceDisableAccordion =
      window.location.search.indexOf('faq-perf-no-accordion=1') !== -1;
    var performanceDisableItems =
      window.location.search.indexOf('faq-perf-no-items=1') !== -1;
    var performanceDisableBackground =
      window.location.search.indexOf('faq-perf-no-background=1') !== -1;

    var reportPerformanceProbe = function (endTime) {
      if (!performanceProbe || performanceProbe.frames.length < 2) {
        performanceProbe = null;
        return;
      }

      var frameDeltas = performanceProbe.frames.slice(1).map(function (time, index) {
        return time - performanceProbe.frames[index];
      });
      var sortedDeltas = frameDeltas.slice().sort(function (a, b) {
        return a - b;
      });
      var percentile = function (ratio) {
        return sortedDeltas[
          Math.min(
            sortedDeltas.length - 1,
            Math.floor(sortedDeltas.length * ratio)
          )
        ];
      };
      var averageDelta =
        frameDeltas.reduce(function (sum, delta) {
          return sum + delta;
        }, 0) / frameDeltas.length;
      var report = {
        fps: Number((1000 / averageDelta).toFixed(1)),
        frames: performanceProbe.frames.length,
        averageFrameMs: Number(averageDelta.toFixed(2)),
        medianFrameMs: Number(percentile(0.5).toFixed(2)),
        p95FrameMs: Number(percentile(0.95).toFixed(2)),
        maximumFrameMs: Number(
          Math.max.apply(Math, frameDeltas).toFixed(2)
        ),
        framesOver20Ms: frameDeltas.filter(function (delta) {
          return delta > 20;
        }).length,
        framesOver33Ms: frameDeltas.filter(function (delta) {
          return delta > 33.4;
        }).length,
        scrollInputMs: Number(
          (performanceProbe.lastScrollTime - performanceProbe.startTime).toFixed(1)
        ),
        visualSettleMs: Number(
          (endTime - performanceProbe.lastScrollTime).toFixed(1)
        ),
        totalMotionMs: Number(
          (endTime - performanceProbe.startTime).toFixed(1)
        ),
      };

      console.info('[FAQ performance] ' + JSON.stringify(report));
      performanceProbe = null;
    };

    var samplePerformanceFrame = function (timestamp) {
      if (!performanceProbe) {
        performanceProbeRafId = 0;
        return;
      }
      performanceProbe.frames.push(timestamp);
      performanceProbeRafId =
        window.requestAnimationFrame(samplePerformanceFrame);
    };

    var paint = function () {
      var easedHero = easeProgress(heroProgress);
      var easedAccordion = easeProgress(accordionProgress);
      var backgroundExtension = performanceDisableBackground
        ? 0
        : maxBackgroundExtension * easedHero;
      var accordionBaseOffset = performanceDisableAccordion
        ? 0
        : maxAccordionOffset * easedAccordion;
      wrapper.style.marginBlockStart =
        (-backgroundExtension).toFixed(2) + 'px';
      section.style.paddingBlockStart =
        backgroundExtension.toFixed(2) + 'px';
      if (
        heroWrapper instanceof HTMLElement &&
        !performanceDisableHero
      ) {
        heroWrapper.style.transform =
          'translate3d(0, ' +
          (maxHeroOffset * easedHero).toFixed(2) +
          'px, 0)';
        heroWrapper.style.opacity = (1 - easedHero).toFixed(3);
      }

      /*
       * Każda karta ma własną bezwładność. Trail wzmacnia różnicę faz tylko
       * podczas ruchu; po zatrzymaniu wszystkie korekty miękko wracają do 0.
       */
      var lastItemScrollOffset = accordionBaseOffset;
      accordionItems.forEach(function (node, index) {
        if (!(node instanceof HTMLElement)) return;
        var itemProgress = itemProgresses[index];
        var itemEased = easeProgress(itemProgress);
        var phaseTrail =
          (itemProgress - accordionProgress) * (70 + index * 9);
        var easingCorrection =
          maxAccordionOffset * (itemEased - easedAccordion);
        var itemOffset =
          accordionBaseOffset + phaseTrail + easingCorrection;
        if (index === accordionItems.length - 1) {
          lastItemScrollOffset = itemOffset;
        }
        if (!performanceDisableItems) {
          node.style.transform =
            'translate3d(0, ' + itemOffset.toFixed(2) + 'px, 0)';
        }
      });
      if (accordionTail instanceof HTMLElement) {
        setFaqAccordionTailOffset(
          accordionTail,
          'scroll',
          lastItemScrollOffset
        );
      }

    };

    var render = function (timestamp) {
      rafId = 0;
      var deltaMs = lastFrameTime
        ? Math.min(48, Math.max(1, timestamp - lastFrameTime))
        : 16;
      lastFrameTime = timestamp;
      targetProgress = clampProgress(window.scrollY / scrollRange);

      heroProgress = damp(heroProgress, targetProgress, deltaMs, 85);
      accordionProgress = damp(
        accordionProgress,
        targetProgress,
        deltaMs,
        105
      );
      for (var itemIndex = 0; itemIndex < itemProgresses.length; itemIndex += 1) {
        itemProgresses[itemIndex] = damp(
          itemProgresses[itemIndex],
          targetProgress,
          deltaMs,
          130 + itemIndex * 20
        );
      }

      paint();

      var stillMoving =
        Math.abs(heroProgress - targetProgress) > 0.012 ||
        Math.abs(accordionProgress - targetProgress) > 0.012 ||
        itemProgresses.some(function (current) {
          return Math.abs(current - targetProgress) > 0.012;
        });
      if (stillMoving) {
        rafId = window.requestAnimationFrame(render);
      } else {
        heroProgress = targetProgress;
        accordionProgress = targetProgress;
        for (
          var settledIndex = 0;
          settledIndex < itemProgresses.length;
          settledIndex += 1
        ) {
          itemProgresses[settledIndex] = targetProgress;
        }
        paint();
        if (performanceProbe) reportPerformanceProbe(timestamp);
      }
    };

    var requestRender = function () {
      targetProgress = clampProgress(window.scrollY / scrollRange);
      if (performanceProbeEnabled) {
        var probeTime = window.performance.now();
        if (!performanceProbe) {
          performanceProbe = {
            startTime: probeTime,
            lastScrollTime: probeTime,
            frames: [],
          };
          if (!performanceProbeRafId) {
            performanceProbeRafId =
              window.requestAnimationFrame(samplePerformanceFrame);
          }
        } else {
          performanceProbe.lastScrollTime = probeTime;
        }
      }
      if (!rafId) {
        lastFrameTime = 0;
        rafId = window.requestAnimationFrame(render);
      }
    };

    window.addEventListener('scroll', requestRender, { passive: true });
    paint();
  }

  /**
   * Subtelny parallax dekoracji — jak przy pierwszym wdrożeniu.
   * Lewa max +18px, prawa −14px, scrub 1.2; CSS top:50% + yPercent:-50.
   * @param {GsapStatic} tween
   */
  function initArtworkDecorationParallax(/** @type {GsapStatic} */ tween) {
    var sections = document.querySelectorAll('.faq-section');
    if (!sections.length) return;

    /*
     * Zamrożenie osi Y dekoracji przed otwarciem akordeonu.
     * CSS top:50% przesuwał oba kształty, gdy sekcja rosła od długiej odpowiedzi.
     */
    sections.forEach(function (sectionNode) {
      if (!(sectionNode instanceof HTMLElement)) return;
      var section = sectionNode;
      if (section.style.getPropertyValue('--faq-decoration-anchor-y')) return;
      section.style.setProperty(
        '--faq-decoration-anchor-y',
        Math.round(section.getBoundingClientRect().height * 0.65) + 'px'
      );
    });

    if (reduceMotion) return;

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
            ease: 'power2.inOut',
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
            ease: 'power3.inOut',
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
    initFaqScrollToBottomOnOpen();
    initFaqSingleWheelPageSnap();
    initFaqSingleOpenLock();
    initFaqAccordionTailTracking();
    initFaqDecorationHoverGlow();
    initFaqIdlePerformanceProbe();
    if (reduceMotion) return;
    if (
      window.location.search.indexOf('faq-perf-scroll-only=1') === -1
    ) {
      initFaqBackgroundScrollExpansion();
    }
    prepareFadeEntrances();
    whenGsapReady(
      /** @param {GsapStatic} tween */ function (tween) {
        var accordionStarted = false;
        var startAccordion = function () {
          if (accordionStarted) return;
          accordionStarted = true;
          runAccordionEntrance(tween);
        };
        runHeroEntrance(tween);
        whenCurtainOpening(startAccordion);
        initAccordionFocusBlur(tween);
        if (
          window.location.search.indexOf('faq-perf-lite=1') === -1 &&
          window.location.search.indexOf('faq-perf-no-parallax=1') === -1
        ) {
          initArtworkDecorationParallax(tween);
        }
        /* Awaryjnie: jeśli kurtyna / event nie dojdzie, pokaż akordeon po chwili. */
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
