(function () {
  var sections = document.querySelectorAll('.giclee-process, .giclee-trust');
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
})();
