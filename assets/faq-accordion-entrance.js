/* FAQ — GSAP: wejście akordeonu + hover nagłówka hero. */
(function () {
  if (window.__GICLEE_FAQ_ACCORDION_ENTRANCE__) return;
  window.__GICLEE_FAQ_ACCORDION_ENTRANCE__ = true;

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

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

  function runHeadingHover(/** @type {GsapStatic} */ tween) {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;

    var headingEl = document.querySelector(
      '.hero__content-wrapper :is(h1, h2, h3, h4, h5, h6)'
    );
    if (!headingEl) return;

    /** @type {HTMLElement} */
    var heading = /** @type {HTMLElement} */ (headingEl);
    /** @type {GsapStatic} */
    var gsapApi = tween;

    heading.classList.add('faq-hero-heading');
    /* Hero content ma pointer-events: none — wymuś hit-target na samym napisie */
    heading.style.pointerEvents = 'auto';
    heading.style.cursor = 'pointer';
    gsapApi.set(heading, { transformOrigin: '50% 50%', display: 'inline-block' });

    heading.addEventListener('mouseenter', function () {
      gsapApi.to(heading, {
        duration: 0.3,
        scale: 1.05,
        ease: 'power2.out',
      });
    });

    heading.addEventListener('mouseleave', function () {
      gsapApi.to(heading, {
        duration: 0.25,
        scale: 1,
        ease: 'power2.out',
      });
    });
  }

  function run() {
    whenGsapReady(/** @param {GsapStatic} tween */ function (tween) {
      runAccordionEntrance(tween);
      runHeadingHover(tween);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
