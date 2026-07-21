(function () {
  var sections = document.querySelectorAll('.giclee-process, .giclee-trust');
  if (!sections.length) return;

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  sections.forEach(function (section) {
    var isTrust = section.classList.contains('giclee-trust');

    if (reducedMotion) {
      section.classList.add('is-revealed');
    }

    if (isTrust) {
      var trustObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            var covering = entry.isIntersecting && entry.intersectionRatio >= 0.18;
            section.classList.toggle('is-covering-process', covering);

            if (covering) {
              section.classList.add('is-revealed');
            }
          });
        },
        { threshold: [0, 0.18], rootMargin: '0px 0px -16% 0px' }
      );

      trustObserver.observe(section);
      return;
    }

    if (reducedMotion) return;

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
