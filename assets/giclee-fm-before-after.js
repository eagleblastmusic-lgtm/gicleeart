/* Filozofia marki — galeria „Przed i po”, wzorzec preview.html. */
(function () {
  'use strict';

  if (window.GicleeFmBeforeAfter) return;

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function readConfig() {
    var source = document.getElementById('giclee-fm-before-after-data');
    var empty = {
      slides: [],
      motionBlur: true,
      filmGrain: true,
      bgTransparent: true,
      bgRadialOpacity: 0,
      bgLinearOpacity: 0,
      preservePrevBg: true,
      texts: {},
    };
    if (!source) return empty;
    try {
      var data = JSON.parse(source.textContent || '{}');
      if (!Array.isArray(data.slides)) {
        return empty;
      }
      var importedTexts = {};
      try {
        importedTexts = JSON.parse(data.textsJson || '{}');
      } catch (_textError) {}
      if (!importedTexts || typeof importedTexts !== 'object') importedTexts = {};
      var textSlides = Array.isArray(importedTexts.slides)
        ? importedTexts.slides
        : [];
      var texts = {
        brand: importedTexts.brand || 'Before / After Archive',
        scrollHint: importedTexts.scrollHint || 'Scroll to explore',
        beforeLabel: importedTexts.beforeLabel || 'Before',
        afterLabel: importedTexts.afterLabel || 'After',
        dragHint: importedTexts.dragHint || 'Drag to reveal',
        frameLabel: importedTexts.frameLabel || 'Frame',
      };
      var count = clamp(Number.parseInt(data.count || data.slides.length, 10) || 0, 0, 12);
      var slides = data.slides.slice(0, count).filter(function (slide) {
        return slide && slide.before && slide.after;
      }).map(function (slide, index) {
        var editable = textSlides[index] && typeof textSlides[index] === 'object'
          ? textSlides[index]
          : {};
        return Object.assign({}, slide, {
          title: editable.title || slide.title || 'Porównanie ' + (index + 1),
          location:
            editable.location ||
            slide.location ||
            'Giclée Art · Reprodukcja',
          type: editable.type || slide.type || 'Przed / Po',
        });
      });
      return {
        slides: slides,
        motionBlur: data.motionBlur !== false,
        filmGrain: data.filmGrain !== false,
        bgTransparent: data.bgTransparent !== false,
        bgRadialOpacity: clamp(Number(data.bgRadialOpacity) || 0, 0, 100),
        bgLinearOpacity: clamp(Number(data.bgLinearOpacity) || 0, 0, 100),
        preservePrevBg: data.preservePrevBg !== false,
        texts: texts,
      };
    } catch (_error) {
      return empty;
    }
  }

  function readSlides() {
    return readConfig().slides;
  }

  function mount(host, options) {
    if (!(host instanceof HTMLElement)) return null;
    var existing = host.querySelector('.giclee-fm-before-after');
    if (existing) return existing.__gicleeFmBeforeAfter || null;

    var config = options || readConfig();
    var slides = config.slides || [];
    if (!slides.length) return null;
    var texts = config.texts || {};
    var motionBlur = config.motionBlur !== false;
    var filmGrain = config.filmGrain !== false;
    var bgTransparent = config.bgTransparent !== false;
    var bgRadialOpacity = bgTransparent
      ? clamp(Number(config.bgRadialOpacity) || 0, 0, 100) / 100
      : 1;
    var bgLinearOpacity = bgTransparent
      ? clamp(Number(config.bgLinearOpacity) || 0, 0, 100) / 100
      : 1;

    var reducedMotion = !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
    var gsapApi = window.gsap || null;
    var root = document.createElement('section');
    root.className = 'giclee-fm-before-after cinematic-deck';
    if (!filmGrain) root.classList.add('is-film-grain-off');
    if (!motionBlur) root.classList.add('is-motion-blur-off');
    root.style.setProperty('--fm-ba-radial-opacity', bgRadialOpacity.toFixed(4));
    root.style.setProperty('--fm-ba-linear-opacity', bgLinearOpacity.toFixed(4));
    root.setAttribute('aria-label', 'Galeria porównań przed i po');
    root.innerHTML =
      '<div class="ambient-light"></div>' +
      '<div class="background-lines"></div>' +
      (filmGrain ? '<div class="film-noise"></div>' : '') +
      '<header class="deck-header">' +
        '<div class="brand">' + escapeHtml(texts.brand || 'Before / After Archive') + '</div>' +
        '<div class="header-counter">' +
          '<span class="header-counter-current">01</span><span>/</span>' +
          '<span class="header-counter-total"></span>' +
        '</div>' +
      '</header>' +
      '<div class="deck-stage"><div class="cards"></div></div>' +
      '<div class="scroll-hint">' + escapeHtml(texts.scrollHint || 'Scroll to explore') + '</div>' +
      '<footer class="deck-footer">' +
        '<div class="deck-dots"></div>' +
        '<nav class="navigation" aria-label="Nawigacja galerii">' +
          '<button class="nav-button nav-previous" type="button" aria-label="Poprzednia scena">' +
            '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M15 5L8 12L15 19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</button>' +
          '<button class="nav-button nav-next" type="button" aria-label="Następna scena">' +
            '<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M9 5L16 12L9 19" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
          '</button>' +
        '</nav>' +
      '</footer>';

    host.appendChild(root);

    var cardsContainer = root.querySelector('.cards');
    var dotsContainer = root.querySelector('.deck-dots');
    var currentCounter = root.querySelector('.header-counter-current');
    var totalCounter = root.querySelector('.header-counter-total');
    var previousButton = root.querySelector('.nav-previous');
    var nextButton = root.querySelector('.nav-next');
    var stage = root.querySelector('.deck-stage');
    var cards = [];
    var dots = [];
    var activeIndex = 0;
    var lastProgress = -1;
    var durationVh = 0.6 + slides.length * 0.8 + 0.6 + 0.6;
    var ENTER_END = 0.6 / durationVh;
    var EXIT_START = (0.6 + slides.length * 0.8) / durationVh;
    var EXIT_END = EXIT_START + 0.6 / durationVh;

    totalCounter.textContent = String(slides.length).padStart(2, '0');

    function tween(target, vars) {
      if (gsapApi) {
        gsapApi.to(target, vars);
        return;
      }
      Object.keys(vars).forEach(function (key) {
        if (key in target.style) target.style[key] = vars[key];
      });
    }

    function initializeComparison(card) {
      var handle = card.querySelector('.split-handle');
      var dragging = false;
      var splitPosition = 50;

      function render(value) {
        splitPosition = clamp(value, 0, 100);
        card.style.setProperty('--split', splitPosition + '%');
        card.setAttribute('aria-valuenow', String(Math.round(splitPosition)));
      }

      function positionFromEvent(event) {
        var bounds = card.getBoundingClientRect();
        return ((event.clientX - bounds.left) / Math.max(1, bounds.width)) * 100;
      }

      function move(value) {
        if (!gsapApi || reducedMotion) {
          render(value);
          return;
        }
        gsapApi.to({ value: splitPosition }, {
          value: clamp(value, 0, 100),
          duration: 0.16,
          ease: 'power3.out',
          overwrite: true,
          onUpdate: function () {
            render(this.targets()[0].value);
          },
        });
      }

      card.addEventListener('pointerdown', function (event) {
        if (!card.classList.contains('is-active')) return;
        dragging = true;
        card.setPointerCapture(event.pointerId);
        tween(handle, {
          scale: 0.86,
          duration: reducedMotion ? 0 : 0.2,
          ease: 'power2.out',
        });
        move(positionFromEvent(event));
      });
      card.addEventListener('pointermove', function (event) {
        if (dragging) move(positionFromEvent(event));
      });
      function endDragging(event) {
        if (!dragging) return;
        dragging = false;
        if (card.hasPointerCapture(event.pointerId)) {
          card.releasePointerCapture(event.pointerId);
        }
        tween(handle, {
          scale: 1,
          duration: reducedMotion ? 0 : 0.42,
          ease: 'back.out(2.2)',
        });
      }
      card.addEventListener('pointerup', endDragging);
      card.addEventListener('pointercancel', endDragging);
      card.addEventListener('keydown', function (event) {
        var next = splitPosition;
        if (event.key === 'ArrowLeft') next -= 5;
        else if (event.key === 'ArrowRight') next += 5;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = 100;
        else return;
        event.preventDefault();
        move(next);
      });
      render(50);
    }

    slides.forEach(function (slide, index) {
      var title = String(slide.title || 'Porównanie ' + (index + 1));
      var safeTitle = escapeHtml(title);
      var beforeSource = slide.beforeDisplay || slide.before;
      var afterSource = slide.afterDisplay || slide.after;
      var beforeSourceAttribute =
        index === 0
          ? ' src="' + escapeHtml(beforeSource) + '" loading="eager"'
          : ' data-src="' + escapeHtml(beforeSource) + '" loading="lazy"';
      var afterSourceAttribute =
        index === 0
          ? ' src="' + escapeHtml(afterSource) + '" loading="eager"'
          : ' data-src="' + escapeHtml(afterSource) + '" loading="lazy"';
      var card = document.createElement('article');
      card.className = 'comparison-card';
      card.dataset.index = String(index);
      card.setAttribute('tabindex', index === 0 ? '0' : '-1');
      card.setAttribute('role', 'slider');
      card.setAttribute('aria-label', title + ' — suwak przed i po');
      card.setAttribute('aria-valuemin', '0');
      card.setAttribute('aria-valuemax', '100');
      card.setAttribute('aria-valuenow', '50');
      card.innerHTML =
        '<div class="image-layer before-layer"><img' + beforeSourceAttribute + ' data-fallback-src="' + escapeHtml(slide.before) + '" alt="' + safeTitle + ' przed obróbką" draggable="false" decoding="async" fetchpriority="low"></div>' +
        '<div class="image-layer after-layer"><img' + afterSourceAttribute + ' data-fallback-src="' + escapeHtml(slide.after) + '" alt="' + safeTitle + ' po obróbce" draggable="false" decoding="async" fetchpriority="low"></div>' +
        '<div class="card-grade"></div><div class="card-vignette"></div>' +
        '<div class="card-top"><span class="card-index">' +
          escapeHtml(texts.frameLabel || 'Frame') + ' ' +
          String(index + 1).padStart(2, '0') +
          '</span><span class="card-type">' +
          escapeHtml(slide.type || 'Przed / Po') +
          '</span></div>' +
        '<span class="side-name side-name-before">' +
          escapeHtml(texts.beforeLabel || 'Before') +
          '</span>' +
        '<span class="side-name side-name-after">' +
          escapeHtml(texts.afterLabel || 'After') +
          '</span>' +
        '<div class="split-line"></div>' +
        '<div class="split-handle"><div class="handle-icon"><span></span><span></span></div></div>' +
        '<div class="card-bottom"><div><h2 class="card-title">' +
          safeTitle +
          '</h2><p class="card-location">' +
          escapeHtml(slide.location || 'Giclée Art · Reprodukcja') +
          '</p></div><div class="card-hint">' +
          escapeHtml(texts.dragHint || 'Drag to reveal') +
          '</div></div>';
      cardsContainer.appendChild(card);
      cards.push(card);
      card.querySelectorAll('.image-layer img').forEach(function (image) {
        image.addEventListener('error', function useOriginalOnce() {
          var fallback = image.getAttribute('data-fallback-src');
          image.removeEventListener('error', useOriginalOnce);
          if (fallback && image.src !== fallback) image.src = fallback;
        });
      });
      initializeComparison(card);

      var dot = document.createElement('button');
      dot.className = 'deck-dot';
      dot.type = 'button';
      dot.setAttribute('aria-label', 'Otwórz scenę ' + (index + 1) + ': ' + title);
      dot.addEventListener('click', function () {
        setActive(index, false);
      });
      dotsContainer.appendChild(dot);
      dots.push(dot);
    });

    function ensureCardImages(index) {
      var card = cards[index];
      if (!card) return;
      card.querySelectorAll('.image-layer img[data-src]').forEach(function (image) {
        var source = image.getAttribute('data-src');
        if (!source) return;
        image.removeAttribute('data-src');
        image.loading = 'eager';
        image.src = source;
      });
    }

    function ensureCardsAround(index) {
      ensureCardImages(index);
      ensureCardImages(index + 1);
      ensureCardImages(index - 1);
    }

    function setCardPose(card, relative, immediate) {
      var absolute = Math.abs(relative);
      var pose;
      if (relative === 0) {
        pose = { xPercent: 0, z: 0, rotateY: 0, scale: 1, opacity: 1, blur: 0 };
      } else if (absolute === 1) {
        pose = {
          xPercent: relative * 82,
          z: -230,
          rotateY: relative * -15,
          scale: 0.78,
          opacity: 0.34,
          blur: motionBlur ? 1.5 : 0,
        };
      } else {
        pose = {
          xPercent: relative * 105,
          z: -420,
          rotateY: relative * -22,
          scale: 0.62,
          opacity: 0,
          blur: motionBlur ? 5 : 0,
        };
      }
      card.classList.toggle('is-active', relative === 0);
      card.classList.toggle('is-nearby', absolute <= 1);
      if (absolute <= 1) card.style.visibility = 'visible';
      card.tabIndex = relative === 0 ? 0 : -1;
      card.style.pointerEvents = relative === 0 ? 'auto' : 'none';
      if (gsapApi) {
        gsapApi.to(card, {
          xPercent: pose.xPercent,
          z: pose.z,
          rotateY: pose.rotateY,
          scale: pose.scale,
          opacity: pose.opacity,
          filter: motionBlur ? 'blur(' + pose.blur + 'px)' : 'none',
          duration: immediate || reducedMotion ? 0 : 0.95,
          ease: 'power4.inOut',
          overwrite: true,
          onComplete: function () {
            if (absolute > 1) card.style.visibility = 'hidden';
          },
        });
      } else {
        card.style.opacity = String(pose.opacity);
        card.style.filter = motionBlur ? 'blur(' + pose.blur + 'px)' : 'none';
        card.style.transform =
          'translateX(' + pose.xPercent + '%) rotateY(' + pose.rotateY +
          'deg) scale(' + pose.scale + ')';
        card.style.visibility = absolute <= 1 ? 'visible' : 'hidden';
      }
    }

    function renderDeck(immediate) {
      cards.forEach(function (card, index) {
        setCardPose(card, index - activeIndex, immediate);
      });
      dots.forEach(function (dot, index) {
        dot.classList.toggle('is-active', index === activeIndex);
      });
      currentCounter.textContent = String(activeIndex + 1).padStart(2, '0');
    }

    function setActive(index, immediate, loadAround) {
      var next = clamp(Math.round(index), 0, slides.length - 1);
      if (loadAround !== false) ensureCardsAround(next);
      if (next === activeIndex && !immediate) return;
      activeIndex = next;
      renderDeck(immediate);
      if (gsapApi && !immediate) {
        gsapApi.fromTo(
          currentCounter,
          { y: 10, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: reducedMotion ? 0 : 0.5,
            ease: 'power3.out',
            overwrite: true,
          }
        );
      }
      return activeIndex;
    }

    previousButton.addEventListener('click', function () {
      setActive(activeIndex - 1, false);
    });
    nextButton.addEventListener('click', function () {
      setActive(activeIndex + 1, false);
    });
    stage.addEventListener('pointermove', function (event) {
      var activeCard = cards[activeIndex];
      if (!activeCard || reducedMotion || !gsapApi) return;
      var bounds = stage.getBoundingClientRect();
      var x = (event.clientX - bounds.left) / Math.max(1, bounds.width) - 0.5;
      var y = (event.clientY - bounds.top) / Math.max(1, bounds.height) - 0.5;
      gsapApi.to(activeCard.querySelectorAll('.image-layer img'), {
        xPercent: x * 1.2,
        yPercent: y * 0.8,
        duration: 1.3,
        ease: 'power3.out',
        overwrite: true,
      });
    });

    function setProgress(value) {
      var progress = clamp(Number(value) || 0, 0, 1);
      if (Math.abs(progress - lastProgress) < 0.0005) return progress;
      lastProgress = progress;
      var opacity =
        progress <= ENTER_END
          ? progress / Math.max(0.0001, ENTER_END)
        : progress >= EXIT_START
            ? 1 - (progress - EXIT_START) / Math.max(0.0001, EXIT_END - EXIT_START)
            : 1;
      opacity = clamp(opacity, 0, 1);
      root.style.opacity = opacity.toFixed(4);
      root.style.visibility = opacity > 0.001 ? 'visible' : 'hidden';
      root.style.pointerEvents =
        progress >= ENTER_END && progress <= EXIT_START ? 'auto' : 'none';

      var cardsStart = ENTER_END;
      var cardsEnd = EXIT_START;
      var local = clamp(
        (progress - cardsStart) / Math.max(0.0001, cardsEnd - cardsStart),
        0,
        1
      );
      var target =
        slides.length <= 1
          ? 0
          : Math.min(slides.length - 1, Math.floor(local * slides.length));
      if (progress > 0.001) ensureCardsAround(target);
      setActive(target, reducedMotion, false);

      root.setAttribute('data-gallery-progress', progress.toFixed(3));
      root.setAttribute('data-gallery-active-index', String(activeIndex));
      return progress;
    }

    var api = {
      root: root,
      count: slides.length,
      durationVh: 0.6 + slides.length * 0.8 + 0.6 + 0.6,
      setProgress: setProgress,
      next: function () {
        return setActive(activeIndex + 1, false);
      },
      previous: function () {
        return setActive(activeIndex - 1, false);
      },
      getActiveIndex: function () {
        return activeIndex;
      },
      destroy: function () {
        if (root.parentNode) root.parentNode.removeChild(root);
        delete root.__gicleeFmBeforeAfter;
      },
    };

    root.__gicleeFmBeforeAfter = api;
    renderDeck(true);
    setProgress(0);
    return api;
  }

  window.GicleeFmBeforeAfter = {
    mount: mount,
    readConfig: readConfig,
    readSlides: readSlides,
  };
})();
