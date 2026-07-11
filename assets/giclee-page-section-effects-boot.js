/* Page section effects boot — tekst (reveal/hover) + grafika (parallax/hover).
   Config: window.GICLEE_PAGE_SECTION_EFFECTS (GicleeApp → Efekty tekstu/grafiki…). */

(function () {
  var cfg = window.GICLEE_PAGE_SECTION_EFFECTS;
  if (!cfg || !cfg.sections || typeof cfg.sections !== 'object') return;

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  var desktop = window.matchMedia('(min-width: 750px)').matches;

  function sectionEl(key) {
    var direct = document.getElementById('shopify-section-' + key);
    if (direct) return direct;

    var suffix = '__' + key;
    var sections = document.querySelectorAll('[id^="shopify-section-"]');
    for (var i = 0; i < sections.length; i += 1) {
      var id = sections[i].id || '';
      if (id.slice(-suffix.length) === suffix) return sections[i];
    }
    return null;
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

  function findImageEffectMedia(section, imageCfg) {
    var selector = typeof imageCfg.targetSelector === 'string' ? imageCfg.targetSelector.trim() : '';
    if (selector) {
      try {
        var explicitTarget = section.querySelector(selector);
        if (explicitTarget) return explicitTarget;
      } catch (error) {
        /* Nieprawidłowy selektor z konfiguracji nie może zatrzymać pozostałych efektów. */
      }
    }

    return section.querySelector(
      '.media-with-content__media, .media-block, .hero__media-wrapper--desktop, [data-testid^="hero-picture-"]'
    );
  }

  function findImageInteractionSurface(media, section) {
    /* Hero wyłącza pointer-events na siatce mediów. Szukamy najbliższego
       aktywnego przodka bez zmiany globalnego zachowania linków i przycisków. */
    var surface = media;
    while (surface && surface !== section) {
      if (window.getComputedStyle(surface).pointerEvents !== 'none') return surface;
      surface = surface.parentElement;
    }
    return section;
  }

  function applyImageEffects(section, imageCfg) {
    if (!imageCfg || imageCfg.enabled === false) return;
    if (imageCfg.desktopEnabled === false) return;
    if (!desktop || prefersReduced) return;

    var media = findImageEffectMedia(section, imageCfg);
    if (!media) return;

    markSection(section, 'image');
    media.classList.add('giclee-page-fx-media');

    var target = media.querySelector('img, picture, video, .background-image-container') || media;
    var interactionSurface = findImageInteractionSurface(media, section);
    var hoverScale = Number(imageCfg.imageHoverScale) || 1.025;
    var hoverMs = Number(imageCfg.imageHoverDurationMs) || 850;
    media.style.setProperty('--gpf-media-hover-scale', String(hoverScale));
    media.style.setProperty('--gpf-media-hover-duration', hoverMs + 'ms');

    if (imageCfg.imageHoverEnabled !== false && finePointer) {
      interactionSurface.addEventListener('mouseenter', function () {
        media.classList.add('is-hover');
      });
      interactionSurface.addEventListener('mouseleave', function () {
        media.classList.remove('is-hover');
      });
    }

    if (!imageCfg.parallaxEnabled || !finePointer) return;

    var maxX = Number(imageCfg.parallaxMaxX) || 16;
    var maxY = Number(imageCfg.parallaxMaxY) || 10;
    var ease = Number(imageCfg.parallaxEase) || 0.075;
    var returnEase = Number(imageCfg.parallaxReturnEase);
    if (!isFinite(returnEase)) returnEase = 0.035;
    returnEase = Math.max(0.01, Math.min(0.10, returnEase));
    var overscan = Number(imageCfg.parallaxOverscan);
    if (!isFinite(overscan)) overscan = 1.06;
    overscan = Math.max(1, Math.min(1.12, overscan));
    var overscanTransform = ' scale(' + overscan.toFixed(4) + ')';
    var returning = false;
    var currentX = 0;
    var currentY = 0;
    var targetX = 0;
    var targetY = 0;
    var rafId = 0;

    target.style.transform = 'translate3d(0,0,0)' + overscanTransform;

    function tick() {
      var frameEase = returning ? returnEase : ease;
      currentX += (targetX - currentX) * frameEase;
      currentY += (targetY - currentY) * frameEase;
      target.style.transform =
        'translate3d(' +
        currentX.toFixed(2) +
        'px,' +
        currentY.toFixed(2) +
        'px,0)' +
        overscanTransform;
      if (Math.abs(targetX - currentX) > 0.05 || Math.abs(targetY - currentY) > 0.05) {
        rafId = requestAnimationFrame(tick);
      } else {
        if (returning) {
          currentX = 0;
          currentY = 0;
          target.style.transform = 'translate3d(0,0,0)' + overscanTransform;
          returning = false;
        }
        rafId = 0;
      }
    }

    interactionSurface.addEventListener('mousemove', function (e) {
      var rect = media.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      var nx = Math.max(-0.5, Math.min(0.5, (e.clientX - rect.left) / rect.width - 0.5));
      var ny = Math.max(-0.5, Math.min(0.5, (e.clientY - rect.top) / rect.height - 0.5));
      returning = false;
      targetX = nx * maxX;
      targetY = ny * maxY;
      if (!rafId) rafId = requestAnimationFrame(tick);
    });

    interactionSurface.addEventListener('mouseleave', function () {
      returning = true;
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
