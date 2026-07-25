/* FAQ — GSAP: wejście akordeonu. */
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

  function run() {
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
