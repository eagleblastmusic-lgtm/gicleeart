/**
 * PDP (nowy-szblon-produktu): scroll reveal — nagłówek, opis, SZCZEGÓŁY, galeria, konfigurator.
 */
(function () {
  var REDUCED_MQ = window.matchMedia('(prefers-reduced-motion: reduce)');
  var BOOT_STAGGER_MS = 110;

  var TARGETS = [
    {
      selector: '.product-description-below table tbody tr:first-child',
      modifier: 'giclee-pdp-reveal--header',
    },
    {
      selector:
        '.product-description-below table tbody tr:last-child > td:first-child',
      modifier: 'giclee-pdp-reveal--description',
    },
    {
      selector:
        '.product-description-below table tbody tr:last-child > td:last-child',
      modifier: 'giclee-pdp-reveal--details',
    },
    {
      selector: '.giclee-gallery',
      modifier: 'giclee-pdp-reveal--gallery',
    },
    {
      selector: '.product-details',
      modifier: 'giclee-pdp-reveal--configurator',
    },
  ];

  function isInViewport(el) {
    var rect = el.getBoundingClientRect();
    var vh = window.innerHeight || document.documentElement.clientHeight || 0;
    return rect.bottom > 0 && rect.top < vh * 0.92;
  }

  function boot() {
    var main = document.querySelector(
      'main[data-template="product.nowy-szblon-produktu"], main[data-template="product.szablon-produktu-v2"], main[data-template="product.szablon-produktu-v3"]'
    );
    if (!main) return;

    // v3: klasyczny opis ukryty (giclee-product-story ma wlasny reveal) —
    // pomijamy targety wewnatrz .product-description-below.
    var isStoryTemplate =
      main.getAttribute('data-template') === 'product.szablon-produktu-v3';

    var elements = [];
    TARGETS.forEach(function (target) {
      if (
        isStoryTemplate &&
        target.selector.indexOf('.product-description-below') === 0
      ) {
        return;
      }
      // v3: galeria+konfigurator — wjazd z prawej (giclee-product-story.js), bez fade-up
      if (
        isStoryTemplate &&
        (target.modifier === 'giclee-pdp-reveal--gallery' ||
          target.modifier === 'giclee-pdp-reveal--configurator')
      ) {
        return;
      }
      var el = main.querySelector(target.selector);
      if (!el) return;
      el.classList.add('giclee-pdp-reveal', target.modifier);
      elements.push(el);
    });

    if (!elements.length) return;

    if (REDUCED_MQ.matches) {
      elements.forEach(function (el) {
        el.classList.add('is-revealed');
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
      { threshold: 0.14, rootMargin: '0px 0px -10% 0px' }
    );

    var bootIndex = 0;
    elements.forEach(function (el) {
      if (isInViewport(el)) {
        var delay = bootIndex * BOOT_STAGGER_MS;
        bootIndex += 1;
        window.setTimeout(function () {
          el.classList.add('is-revealed');
        }, delay);
        return;
      }
      observer.observe(el);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
