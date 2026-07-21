(function () {
  var sections = document.querySelectorAll('.giclee-process, .giclee-trust');
  if (!sections.length) return;

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scene = document.querySelector('.pdp-v3-pt-wrap');

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function rangeProgress(value, start, end) {
    return clamp((value - start) / Math.max(end - start, 0.0001), 0, 1);
  }

  if (scene) {
    var processSection = scene.querySelector('.giclee-process');
    var trustSection = scene.querySelector('.giclee-trust');

    if (processSection && trustSection) {
      var separator = processSection.nextElementSibling;
      if (separator && separator.classList.contains('product-description-trailing-separator')) {
        separator.remove();
      }

      var stage = document.createElement('div');
      stage.className = 'pdp-v3-pt-stage';
      processSection.parentNode.insertBefore(stage, processSection);
      stage.appendChild(processSection);
      stage.appendChild(trustSection);
      scene.setAttribute('data-pdp-v3-pt-scene', '');

      var ticking = false;

      function updateScene() {
        ticking = false;

        var rect = scene.getBoundingClientRect();
        var viewportHeight = Math.max(window.innerHeight || 0, 1);
        var travel = Math.max(scene.offsetHeight - viewportHeight, 1);
        var progress = clamp(-rect.top / travel, 0, 1);

        var processExit = rangeProgress(progress, 0.32, 0.48);
        var trustEnter = rangeProgress(progress, 0.52, 0.68);
        var processOpacity = reducedMotion ? (progress < 0.5 ? 1 : 0) : 1 - processExit;
        var trustOpacity = reducedMotion ? (progress >= 0.5 ? 1 : 0) : trustEnter;
        var processY = reducedMotion ? 0 : -18 * processExit;
        var trustY = reducedMotion ? 0 : 18 * (1 - trustEnter);

        scene.style.setProperty('--pdp-v3-pt-progress', progress.toFixed(4));
        scene.style.setProperty('--pdp-v3-process-opacity', processOpacity.toFixed(4));
        scene.style.setProperty('--pdp-v3-process-y', processY.toFixed(2) + 'px');
        scene.style.setProperty('--pdp-v3-trust-opacity', trustOpacity.toFixed(4));
        scene.style.setProperty('--pdp-v3-trust-y', trustY.toFixed(2) + 'px');
        scene.dataset.pdpV3PtPhase = progress < 0.5 ? 'process' : 'trust';
      }

      function requestSceneUpdate() {
        if (ticking) return;
        ticking = true;
        window.requestAnimationFrame(updateScene);
      }

      window.addEventListener('scroll', requestSceneUpdate, { passive: true });
      window.addEventListener('resize', requestSceneUpdate);
      requestSceneUpdate();
    }
  }

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