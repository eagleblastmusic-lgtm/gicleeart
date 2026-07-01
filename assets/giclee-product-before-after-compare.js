(function () {
  function syncCompare(media, slider) {
    if (!media || !slider) return;
    var val =
      (Number(slider.value) - Number(slider.min)) /
      (Number(slider.max) - Number(slider.min));
    var compare = Math.round(val * 100);
    media.style.setProperty('--compare', String(compare));
  }

  function initCompare(root) {
    if (!root || root.dataset.gicleeBeforeAfterReady === 'true') return;

    var media = root.querySelector('[data-giclee-before-after-media]');
    var slider = root.querySelector('[data-giclee-before-after-slider]');
    if (!media || !slider) return;

    root.dataset.gicleeBeforeAfterReady = 'true';

    var sync = function () {
      syncCompare(media, slider);
    };

    slider.addEventListener('input', sync);
    slider.addEventListener('change', sync);

    slider.addEventListener(
      'pointerdown',
      function () {
        media.classList.add('is-dragging');
      },
      { passive: true }
    );

    var endDrag = function () {
      media.classList.remove('is-dragging');
    };

    slider.addEventListener('pointerup', endDrag);
    slider.addEventListener('pointercancel', endDrag);
    slider.addEventListener('blur', endDrag);

    sync();
  }

  function mountFromSource() {
    var target = document.querySelector('[data-giclee-before-after-target]');
    if (!target || target.dataset.gicleeBeforeAfterMounted === 'true') return;

    var source = document.querySelector('.giclee-before-after-source');
    if (!source || !source.firstElementChild) return;

    target.dataset.gicleeBeforeAfterMounted = 'true';
    while (source.firstChild) {
      target.appendChild(source.firstChild);
    }
    source.remove();
  }

  function initAll() {
    mountFromSource();
    document.querySelectorAll('[data-giclee-before-after]').forEach(initCompare);
    initReveal();
  }

  function initReveal() {
    var sections = document.querySelectorAll('.giclee-before-after');
    if (!sections.length) return;

    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    sections.forEach(function (section) {
      if (reducedMotion) {
        section.classList.add('is-revealed');
        return;
      }

      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            section.classList.add('is-revealed');
            observer.unobserve(section);
          });
        },
        { threshold: 0.18, rootMargin: '0px 0px -16% 0px' }
      );

      observer.observe(section);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  document.addEventListener('shopify:section:load', initAll);
})();
