/* Page section effects boot — tekst (reveal/hover) + grafika (parallax/hover).
   Config: window.GICLEE_PAGE_SECTION_EFFECTS (GicleeApp → Efekty tekstu/grafiki…). */

(function () {
  var cfg = window.GICLEE_PAGE_SECTION_EFFECTS;
  if (!cfg || !cfg.sections || typeof cfg.sections !== 'object') return;

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var desktop = window.matchMedia('(min-width: 750px)').matches;

  function sectionEl(key) {
    return document.getElementById('shopify-section-' + key);
  }

  function markSection(section, kind) {
    var prev = section.getAttribute('data-giclee-page-fx') || '';
    if (!prev) {
      section.setAttribute('data-giclee-page-fx', kind);
      return;
    }
    if (prev.indexOf(kind) === -1) {
      section.setAttribute('data-giclee-page-fx', prev + ',' + kind);
    }
  }

  function findHeading(content) {
    return (
      content.querySelector('h1, h2, h3, .h1, .h2, .h3, [class*="heading"]') ||
      content.querySelector('.text-block h1, .text-block h2, .text-block h3')
    );
  }

  function findBody(content, heading) {
    var body = content.querySelector('.rte, .text-block__text, .media-with-content__text');
    if (body) return body;
    if (heading && heading.nextElementSibling) return heading.nextElementSibling;
    var group = content.querySelector('.group-block-content');
    return group || content;
  }

  function applyTextEffects(section, textCfg) {
    if (!textCfg || textCfg.enabled === false) return;
    if (textCfg.desktopEnabled === false) return;
    if (prefersReduced) return;

    var content = section.querySelector('.media-with-content__content');
    if (!content) return;

    markSection(section, 'text');
    content.classList.add('giclee-page-fx-text');
    if (textCfg.glowEnabled !== false) {
      content.classList.add('giclee-page-fx-text--glow');
    }

    var duration = Number(textCfg.textDurationMs) || 900;
    var headingDelay = Number(textCfg.headingDelayMs) || 120;
    var stagger = Number(textCfg.paragraphStaggerMs) || 140;
    var hoverMs = Number(textCfg.hoverDurationMs) || 850;
    var copyScale = Number(textCfg.copyHoverScale) || 1.022;
    var copyY = Number(textCfg.copyHoverTranslateY);
    if (isNaN(copyY)) copyY = -4;
    var easing = textCfg.easingBezier || '0.16, 1, 0.3, 1';

    content.style.setProperty('--gpf-text-duration', duration + 'ms');
    content.style.setProperty('--gpf-heading-delay', headingDelay + 'ms');
    content.style.setProperty('--gpf-paragraph-stagger', stagger + 'ms');
    content.style.setProperty('--gpf-hover-duration', hoverMs + 'ms');
    content.style.setProperty('--gpf-copy-scale', String(copyScale));
    content.style.setProperty('--gpf-copy-y', copyY + 'px');
    content.style.setProperty('--gpf-text-ease', 'cubic-bezier(' + easing + ')');

    var heading = findHeading(content);
    if (heading) heading.classList.add('giclee-page-fx-heading');

    var body = findBody(content, heading);
    if (body && body !== heading) {
      body.classList.add('giclee-page-fx-body');
    }

    var threshold = Math.min(1, Math.max(0.05, Number(textCfg.revealThreshold) || 0.25));
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            content.classList.add('is-revealed');
            observer.disconnect();
          }
        });
      },
      { threshold: threshold, rootMargin: '0px 0px -8% 0px' }
    );
    observer.observe(content);

    if (finePointer && textCfg.glowEnabled !== false) {
      content.addEventListener('mouseenter', function () {
        content.classList.add('is-hover');
      });
      content.addEventListener('mouseleave', function () {
        content.classList.remove('is-hover');
      });
    }
  }

  function applyImageEffects(section, imageCfg) {
    if (!imageCfg || imageCfg.enabled === false) return;
    if (imageCfg.desktopEnabled === false) return;
    if (prefersReduced) return;

    var media = section.querySelector('.media-with-content__media, .media-block');
    if (!media) return;

    markSection(section, 'image');
    media.classList.add('giclee-page-fx-media');

    var hoverScale = Number(imageCfg.imageHoverScale) || 1.025;
    var hoverMs = Number(imageCfg.imageHoverDurationMs) || 850;
    media.style.setProperty('--gpf-media-hover-scale', String(hoverScale));
    media.style.setProperty('--gpf-media-hover-duration', hoverMs + 'ms');

    if (imageCfg.imageHoverEnabled !== false && finePointer) {
      media.addEventListener('mouseenter', function () {
        media.classList.add('is-hover');
      });
      media.addEventListener('mouseleave', function () {
        media.classList.remove('is-hover');
      });
    }

    if (!imageCfg.parallaxEnabled || !finePointer) return;

    var target = media.querySelector('img, picture, video, .background-image-container') || media;
    var maxX = Number(imageCfg.parallaxMaxX) || 16;
    var maxY = Number(imageCfg.parallaxMaxY) || 10;
    var ease = Number(imageCfg.parallaxEase) || 0.075;
    var currentX = 0;
    var currentY = 0;
    var targetX = 0;
    var targetY = 0;
    var rafId = 0;

    function tick() {
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;
      target.style.transform =
        'translate3d(' + currentX.toFixed(2) + 'px,' + currentY.toFixed(2) + 'px,0)';
      if (Math.abs(targetX - currentX) > 0.05 || Math.abs(targetY - currentY) > 0.05) {
        rafId = requestAnimationFrame(tick);
      } else {
        rafId = 0;
      }
    }

    section.addEventListener('mousemove', function (e) {
      var rect = section.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      var nx = (e.clientX - rect.left) / rect.width - 0.5;
      var ny = (e.clientY - rect.top) / rect.height - 0.5;
      targetX = nx * maxX;
      targetY = ny * maxY;
      if (!rafId) rafId = requestAnimationFrame(tick);
    });

    section.addEventListener('mouseleave', function () {
      targetX = 0;
      targetY = 0;
      if (!rafId) rafId = requestAnimationFrame(tick);
    });
  }

  function init() {
    Object.keys(cfg.sections).forEach(function (key) {
      var section = sectionEl(key);
      if (!section) return;
      var pack = cfg.sections[key] || {};
      applyTextEffects(section, pack.text);
      applyImageEffects(section, pack.image);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
