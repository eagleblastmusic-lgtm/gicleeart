/* Blog — GSAP: wejście hero (tytuł jak FAQ) + letter-fade podtytułu (jak splash) + karty. */
(function () {
  if (window.__GICLEE_BLOG_POSTS_ENTRANCE__) return;
  window.__GICLEE_BLOG_POSTS_ENTRANCE__ = true;

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Parametry letter-fade — jak #splash-screen .splash-sub („Witamy w świecie sztuki”). */
  var LETTER_FADE_MS = 2200;
  var LETTER_MIN_MS = 600;
  var LETTER_EASE = 'cubic-bezier(0.25, 0.46, 0.45, 0.94)';
  var LETTER_START_AFTER_MS = 700;

  function getGsap() {
    return window.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  function getScrollTrigger() {
    return (
      window.ScrollTrigger ||
      (typeof ScrollTrigger !== 'undefined' ? ScrollTrigger : undefined)
    );
  }

  function getBlogHeroTitleNodes() {
    return document.querySelectorAll(
      '.hero__content-wrapper :is(h1, h2, h3, h4, h5, h6)'
    );
  }

  function getBlogHeroSubtitleNodes() {
    return document.querySelectorAll('.hero__content-wrapper p');
  }

  /**
   * @param {HTMLElement} el
   */
  function clearEntranceInline(el) {
    el.style.opacity = '';
    el.style.willChange = '';
  }

  /**
   * @param {(api: { gsap: GsapStatic, ScrollTrigger: object }) => void} callback
   * @param {() => void} [onTimeout]
   */
  function whenReady(callback, onTimeout) {
    var tween = getGsap();
    var st = getScrollTrigger();
    if (tween && st) {
      callback({ gsap: tween, ScrollTrigger: st });
      return;
    }

    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      var nextTween = getGsap();
      var nextSt = getScrollTrigger();
      if (nextTween && nextSt) {
        window.clearInterval(timer);
        callback({ gsap: nextTween, ScrollTrigger: nextSt });
        return;
      }
      if (attempts >= 40) {
        window.clearInterval(timer);
        if (typeof onTimeout === 'function') onTimeout();
      }
    }, 50);
  }

  /**
   * @param {string} value
   */
  function cleanText(value) {
    return String(value || '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * @param {string} source
   */
  function createLetterVisual(source) {
    var visual = document.createElement('span');
    visual.setAttribute('aria-hidden', 'true');
    var chars = [];
    source.split(/(\s+)/).forEach(function (token) {
      if (!token) return;
      if (/^\s+$/.test(token)) {
        visual.appendChild(document.createTextNode(token));
        return;
      }
      var word = document.createElement('span');
      word.className = 'blog-hero-sub-word';
      Array.from(token).forEach(function (glyph) {
        var char = document.createElement('span');
        char.className = 'blog-hero-sub-char';
        char.textContent = glyph;
        char.style.opacity = '0';
        chars.push(char);
        word.appendChild(char);
      });
      visual.appendChild(word);
    });
    return { visual: visual, chars: chars };
  }

  /** Ukrycie przed FOUC — jak prepareFadeEntrances w FAQ. */
  function prepareHeroEntrances() {
    if (reduceMotion) return;

    getBlogHeroTitleNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.blogHeroTitlePrepared) return;
      el.dataset.blogHeroTitlePrepared = '1';
      el.style.opacity = '0';
      el.style.willChange = 'opacity';
    });

    getBlogHeroSubtitleNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      if (el.dataset.blogHeroSubPrepared) return;
      el.dataset.blogHeroSubPrepared = '1';
      el.classList.add('blog-hero-letter-fade');
      el.style.opacity = '0';
    });
  }

  function revealHeroFallback() {
    getBlogHeroTitleNodes().forEach(function (node) {
      clearEntranceInline(/** @type {HTMLElement} */ (node));
    });
    getBlogHeroSubtitleNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      el.style.opacity = '';
      el.classList.add('is-letter-fade-prepared');
    });
  }

  /**
   * Fade-in tytułu — te same parametry co nagłówek FAQ (1.1s, delay 0.2, power3.out).
   * @param {GsapStatic} tween
   */
  function runHeroTitleEntrance(tween) {
    var titleNodes = Array.prototype.slice
      .call(getBlogHeroTitleNodes())
      .filter(function (node) {
        /** @type {HTMLElement} */
        var el = /** @type {HTMLElement} */ (node);
        if (el.dataset.blogHeroTitleEntranceBound) return false;
        el.dataset.blogHeroTitleEntranceBound = '1';
        return true;
      });

    if (!titleNodes.length) return;

    var trigger =
      (titleNodes[0] && titleNodes[0].closest('.hero')) || titleNodes[0];

    var play = function () {
      titleNodes.forEach(function (node) {
        /** @type {HTMLElement} */
        var el = /** @type {HTMLElement} */ (node);
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
            },
          }
        );
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
   * Letter-fade podtytułu — jak splash „Witamy w świecie sztuki”.
   */
  function runHeroSubtitleLetterFade() {
    var nodes = Array.prototype.slice.call(getBlogHeroSubtitleNodes());
    if (!nodes.length) return;

    nodes.forEach(function (node) {
      /** @type {HTMLElement} */
      var sub = /** @type {HTMLElement} */ (node);
      if (sub.dataset.blogHeroSubEntranceBound) return;
      sub.dataset.blogHeroSubEntranceBound = '1';
      sub.classList.add('blog-hero-letter-fade');

      var source = cleanText(sub.textContent);
      if (!source) {
        sub.style.opacity = '';
        sub.classList.add('is-letter-fade-prepared');
        return;
      }
      sub.setAttribute('aria-label', source);

      if (reduceMotion || typeof sub.animate !== 'function') {
        sub.style.opacity = '';
        sub.classList.add('is-letter-fade-prepared');
        return;
      }

      var trigger = sub.closest('.hero') || sub;

      var startPrepared = function () {
        sub.textContent = '';
        var built = createLetterVisual(source);
        sub.appendChild(built.visual);
        sub.style.opacity = '';
        sub.classList.add('is-letter-fade-prepared');
        sub.style.transform = 'scale(1.2)';

        var chars = built.chars;
        if (!chars.length) return;

        var totalSec = LETTER_FADE_MS / 1000;
        var minSec = LETTER_MIN_MS / 1000;
        var mid = Math.max((chars.length - 1) / 2, 0.5);
        var maxOffsetPx = 28;

        var play = function () {
          var animations = [];
          chars.forEach(function (char, index) {
            var randomDuration = minSec + Math.random() * (totalSec - minSec);
            var randomDelay = Math.random() * (totalSec - randomDuration);
            var offsetX = ((index - mid) / mid) * maxOffsetPx;
            char.style.opacity = '0';
            char.style.transform = 'translateX(' + offsetX.toFixed(2) + 'px)';
            animations.push(
              char.animate(
                [
                  {
                    opacity: 0,
                    transform: 'translateX(' + offsetX.toFixed(2) + 'px)',
                  },
                  { opacity: 1, transform: 'translateX(0px)' },
                ],
                {
                  duration: randomDuration * 1000,
                  delay: randomDelay * 1000,
                  easing: LETTER_EASE,
                  fill: 'forwards',
                }
              )
            );
          });
          animations.push(
            sub.animate(
              [{ transform: 'scale(1.2)' }, { transform: 'scale(1)' }],
              {
                duration: LETTER_FADE_MS,
                easing: LETTER_EASE,
                fill: 'forwards',
              }
            )
          );
          Promise.all(
            animations.map(function (animation) {
              return animation.finished.catch(function () {});
            })
          ).then(function () {
            animations.forEach(function (animation) {
              try {
                animation.commitStyles();
                animation.cancel();
              } catch (_) {}
            });
            chars.forEach(function (char) {
              char.style.opacity = '1';
              char.style.transform = '';
            });
            sub.style.transform = '';
          });
        };

        window.setTimeout(play, LETTER_START_AFTER_MS);
      };

      if (typeof IntersectionObserver === 'undefined') {
        startPrepared();
        return;
      }

      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            observer.disconnect();
            startPrepared();
          });
        },
        { threshold: 0 }
      );
      observer.observe(trigger);
    });
  }

  /**
   * @param {{ gsap: GsapStatic, ScrollTrigger: object }} apis
   */
  function runCardsEntrance(apis) {
    var tween = apis.gsap;
    var ScrollTriggerPlugin = apis.ScrollTrigger;

    var container = document.querySelector('.blog-posts-container');
    if (!container) return;

    var items = container.querySelectorAll('.blog-post-item');
    if (!items.length) return;

    container.classList.add('cards');
    items.forEach(function (el) {
      el.classList.add('card');
    });

    tween.registerPlugin(ScrollTriggerPlugin);

    tween.from('.blog-posts .card', {
      scrollTrigger: { trigger: '.blog-posts .cards', start: 'top 80%' },
      y: 50,
      opacity: 0,
      stagger: 0.1,
      duration: 1,
      ease: 'power3.out',
    });
  }

  function run() {
    if (reduceMotion) return;

    prepareHeroEntrances();
    runHeroSubtitleLetterFade();

    whenReady(
      /** @param {{ gsap: GsapStatic, ScrollTrigger: object }} apis */ function (apis) {
        runHeroTitleEntrance(apis.gsap);
        runCardsEntrance(apis);
      },
      revealHeroFallback
    );
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
