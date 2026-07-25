/* Hero text — cienie + hover scale (FAQ / Blog). */
(function () {
  if (window.__GICLEE_HERO_TEXT_HOVER__) return;
  window.__GICLEE_HERO_TEXT_HOVER__ = true;

  var currentScript = /** @type {HTMLScriptElement | null} */ (document.currentScript);
  var faqFq3CurtainUrl =
    currentScript && currentScript.src
      ? currentScript.src.replace(
          /giclee-hero-text-hover\.js(?:\?.*)?$/,
          'faq-fq3-hero-curtain.js'
        )
      : '';

  var HERO_TEXT_SHADOW =
    '0 1px 2px rgba(0, 0, 0, 0.55), 0 4px 18px rgba(0, 0, 0, 0.45), 0 0 28px rgba(0, 0, 0, 0.35)';

  function getHeroTextNodes() {
    return document.querySelectorAll(
      '.hero__content-wrapper :is(h1, h2, h3, h4, h5, h6, p)'
    );
  }

  /** Cienie niezależnie od GSAP / reduced-motion / hover. */
  function applyHeroTextShadows() {
    getHeroTextNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);
      el.classList.add('giclee-hero-text-hover');
      el.style.pointerEvents = 'auto';
      el.style.cursor = 'pointer';
      el.style.textShadow = HERO_TEXT_SHADOW;
    });
  }

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

  function runHeroTextHover(/** @type {GsapStatic} */ tween) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    /** @type {GsapStatic} */
    var gsapApi = tween;

    getHeroTextNodes().forEach(function (node) {
      /** @type {HTMLElement} */
      var el = /** @type {HTMLElement} */ (node);

      gsapApi.set(el, { transformOrigin: '50% 50%', display: 'inline-block' });

      el.addEventListener('mouseenter', function () {
        gsapApi.to(el, {
          duration: 0.55,
          scale: 1.025,
          ease: 'power1.out',
        });
      });

      el.addEventListener('mouseleave', function () {
        gsapApi.to(el, {
          duration: 0.5,
          scale: 1,
          ease: 'power1.out',
        });
      });
    });
  }

  function ensureFaqFq3HeroLayer() {
    var runtime = /** @type {any} */ (window);
    var config = runtime.GICLEE_PAGE_SECTION_EFFECTS;

    if (!config || config.page !== 'faq' || config.variant !== 'fq3') return;
    if (document.getElementById('giclee-faq-fq3-hero-layer-fix')) return;

    var style = document.createElement('style');
    style.id = 'giclee-faq-fq3-hero-layer-fix';
    style.textContent = [
      'body.giclee-faq-fq3-curtain-active #MainContent .giclee-faq-curtain-hero {',
      '  position: relative !important;',
      '  z-index: 40 !important;',
      '}',
      'body.giclee-faq-fq3-curtain-active #MainContent .pin-spacer:has(> .giclee-faq-curtain-hero) {',
      '  position: relative !important;',
      '  z-index: 40 !important;',
      '}',
    ].join('\n');
    document.head.appendChild(style);
  }

  function loadFaqFq3HeroCurtain() {
    var runtime = /** @type {any} */ (window);
    var config = runtime.GICLEE_PAGE_SECTION_EFFECTS;

    if (!config || config.page !== 'faq' || config.variant !== 'fq3') return;
    if (!faqFq3CurtainUrl) return;
    if (document.querySelector('script[data-giclee-faq-fq3-curtain="true"]')) return;

    var script = document.createElement('script');
    script.src = faqFq3CurtainUrl;
    script.defer = true;
    script.dataset.gicleeFaqFq3Curtain = 'true';
    document.head.appendChild(script);
  }

  function run() {
    applyHeroTextShadows();
    whenGsapReady(/** @param {GsapStatic} tween */ function (tween) {
      runHeroTextHover(tween);
    });
    ensureFaqFq3HeroLayer();
    loadFaqFq3HeroCurtain();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();