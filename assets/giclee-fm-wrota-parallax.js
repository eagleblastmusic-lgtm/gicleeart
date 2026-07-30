/* Filozofia / Wrota — flat parallax z pojedynczą warstwą Bottom & Cinematic GSAP Text Reveal. */
(function () {
  'use strict';

  if (window.GicleeFmWrotaParallax) return;

  var MAX_SHIFT_X = 52;
  var MAX_SHIFT_Y = 32;

  function readAssets() {
    var el = document.getElementById('giclee-fm-wrota-parallax-assets');
    if (!el) return null;
    try {
      var data = JSON.parse(el.textContent || '{}');
      if (data && data.bottom) return data;
    } catch (_error) {}
    return null;
  }

  function readParallaxEnabled(options) {
    if (options && typeof options.parallaxEnabled === 'boolean') {
      return options.parallaxEnabled;
    }
    var cfgEl = document.getElementById('giclee-fm-wrota-parallax-config');
    if (cfgEl) {
      try {
        var cfg = JSON.parse(cfgEl.textContent || '{}');
        if (cfg && typeof cfg.parallaxEnabled === 'boolean') {
          return cfg.parallaxEnabled;
        }
      } catch (_error) {}
    }
    var assets = readAssets();
    if (assets && typeof assets.parallaxEnabled === 'boolean') {
      return assets.parallaxEnabled;
    }
    // Domyślnie włączone — zachowanie sprzed przełącznika w GicleeApp.
    return true;
  }

  function splitTextIntoWords(element, options) {
    if (!element) return;
    var settings = options || {};
    var leadCount = Number.isFinite(settings.leadCount)
      ? settings.leadCount
      : 4;
    var accents = settings.accents || [];
    var words = element.textContent
      .trim()
      .replace(/\s+/g, ' ')
      .split(' ');

    element.innerHTML = words
      .map(function (word, index) {
        var normalized = word.toLocaleLowerCase('pl-PL').replace(/[.,„”"—]/g, '');
        var leadClass = index < leadCount ? ' word--lead' : '';
        var accentClass = accents.indexOf(normalized) >= 0 ? ' word--accent' : '';
        return (
          '<span class="word-mask">' +
          '<span class="word' + leadClass + accentClass + '">' + word + '</span>' +
          '</span>'
        );
      })
      .join(' ');
  }

  function mount(host, options) {
    if (!(host instanceof HTMLElement)) return null;
    var existing = host.querySelector('.giclee-fm-flat-parallax');
    if (existing) return existing.__gicleeFmParallax || null;

    var assets = (options && options.assets) || readAssets();
    if (!assets || !assets.bottom) return null;

    var parallaxEnabled = readParallaxEnabled(options);
    var reducedMotion = !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
    var ease = reducedMotion || !parallaxEnabled ? 1 : 0.08;

    var root = document.createElement('div');
    root.className = 'giclee-fm-flat-parallax';

    var layer = document.createElement('div');
    layer.className = 'giclee-fm-flat-parallax__layer';
    var image = document.createElement('img');
    image.alt = '';
    image.draggable = false;
    image.decoding = 'async';
    image.src = assets.bottom;
    image.addEventListener(
      'load',
      function () {
        root.classList.add('is-ready');
      },
      { once: true }
    );
    image.addEventListener(
      'error',
      function () {
        root.classList.add('is-ready');
      },
      { once: true }
    );
    layer.appendChild(image);
    root.appendChild(layer);

    /* ===== CINEMATIC QUOTE STRUCTURE ===== */
    var section = document.createElement('div');
    section.className = 'cinematic-quote';
    section.id = 'cinematicQuote';
    section.innerHTML =
      '<div class="scene">' +
        '<div class="scene-slice scene-slice--top"></div>' +
        '<div class="scene-slice scene-slice--middle"></div>' +
        '<div class="scene-slice scene-slice--bottom"></div>' +
        '<div class="separator separator--top"><span class="separator__flare"></span></div>' +
        '<div class="separator separator--bottom"><span class="separator__flare"></span></div>' +
        '<div class="quote-window">' +
          '<div class="quote-content">' +
            '<h2 class="quote-text">' +
              'Pierwszym są obrazy malarskie — często stare, pożółkłe, zapomniane lub wymagające ponownego opracowania w formie reprodukcji.' +
            '</h2>' +
          '</div>' +
        '</div>' +
        '<div class="quote-window quote-window--secondary">' +
          '<span class="quote-aurora" aria-hidden="true"></span>' +
          '<div class="quote-content quote-content--secondary">' +
            '<h2 class="quote-text quote-text--secondary">' +
              'W tym procesie traktuję je jak materię kulturową, którą można przywrócić do życia poprzez korekcję tonalną i kolorystyczną, precyzyjny druk Fine Art i świadomą oprawę.' +
            '</h2>' +
          '</div>' +
        '</div>' +
      '</div>';

    root.appendChild(section);
    host.appendChild(root);

    var galleryApi = null;
    var preservePrevBg = true;
    if (
      window.GicleeFmBeforeAfter &&
      typeof window.GicleeFmBeforeAfter.readConfig === 'function'
    ) {
      try {
        var baConfig = window.GicleeFmBeforeAfter.readConfig() || {};
        preservePrevBg = baConfig.preservePrevBg !== false;
      } catch (_configError) {
        preservePrevBg = true;
      }
    }
    if (
      window.GicleeFmBeforeAfter &&
      typeof window.GicleeFmBeforeAfter.mount === 'function'
    ) {
      galleryApi = window.GicleeFmBeforeAfter.mount(root);
    }

    var quoteText = section.querySelector('.quote-text');
    var secondaryText = section.querySelector('.quote-text--secondary');
    splitTextIntoWords(quoteText, { leadCount: 4 });
    splitTextIntoWords(secondaryText, {
      leadCount: 0,
      accents: [
        'materię',
        'kulturową',
        'korekcję',
        'tonalną',
        'kolorystyczną',
        'fine',
        'art',
        'świadomą',
        'oprawę'
      ]
    });

    var timeline = null;
    var breathTweens = [];
    var breathingActive = [false, false];

    function buildBreathing() {
      if (breathTweens.length || !window.gsap) return;
      [quoteText, secondaryText].forEach(function (text) {
        gsap.set(text, {
          scale: 1,
          y: 0,
          transformOrigin: '50% 50%'
        });
        breathTweens.push(
          gsap.to(text, {
            scale: 1.025,
            y: -3,
            duration: 3.2,
            ease: 'sine.inOut',
            repeat: -1,
            yoyo: true,
            paused: true
          })
        );
      });
    }

    function syncBreathing(progress) {
      buildBreathing();
      if (!breathTweens.length) return;
      var holds = [
        [0.32 / 2.14, 0.68 / 2.14],
        [1.42 / 2.14, 1.78 / 2.14]
      ];
      var activeName = 'off';
      breathTweens.forEach(function (tween, index) {
        var hold = holds[index];
        var active =
          !reducedMotion &&
          progress >= hold[0] &&
          progress < hold[1];
        if (active && !breathingActive[index]) {
          tween.play(0);
        } else if (!active && breathingActive[index]) {
          tween.pause(0);
          gsap.set(index === 0 ? quoteText : secondaryText, {
            scale: 1,
            y: 0
          });
        }
        breathingActive[index] = active;
        if (active) activeName = index === 0 ? 'primary' : 'secondary';
      });
      section.setAttribute('data-fm-cinematic-breathing', activeName);
    }

    function buildTimeline() {
      if (timeline || !window.gsap) return;

      var primaryWindow = section.querySelector('.quote-window:not(.quote-window--secondary)');
      var secondaryWindow = section.querySelector('.quote-window--secondary');
      var primaryWords = quoteText.querySelectorAll('.word');
      var secondaryWords = secondaryText.querySelectorAll('.word');
      var accentWords = secondaryText.querySelectorAll('.word--accent');
      var aurora = section.querySelector('.quote-aurora');
      if (!primaryWords || primaryWords.length === 0) return;

      gsap.set(primaryWords, {
        yPercent: 120,
        opacity: 0,
        rotateX: -24,
        filter: 'blur(12px)'
      });
      gsap.set(secondaryWindow, {
        clipPath: 'inset(50% 0 50% 0)',
        opacity: 0
      });
      gsap.set(secondaryWords, {
        yPercent: 72,
        opacity: 0,
        scale: 0.96,
        rotateX: -18,
        filter: 'blur(14px)'
      });
      gsap.set(aurora, { xPercent: -140, scaleX: 0.15, opacity: 0 });

      var topFlare = section.querySelector('.separator--top .separator__flare');
      var bottomFlare = section.querySelector('.separator--bottom .separator__flare');

      if (topFlare) gsap.set(topFlare, { xPercent: -130, opacity: 0 });
      if (bottomFlare) gsap.set(bottomFlare, { xPercent: 130, opacity: 0 });

      timeline = gsap.timeline({
        paused: true,
        defaults: { ease: 'power2.out' }
      });

      var topSeparator = section.querySelector('.separator--top');
      var bottomSeparator = section.querySelector('.separator--bottom');

      timeline
        // ===== ENTRANCE PHASE (0.00 to 0.32) =====
        .fromTo(
          section.querySelector('.scene'),
          { scale: 1.05, opacity: 0 },
          { scale: 1, opacity: 1, duration: 0.25, ease: 'power2.out' },
          0
        )
        .to(topSeparator, { scaleX: 1, duration: 0.25, ease: 'expo.inOut' }, 0.04)
        .to(topFlare, { opacity: 1, duration: 0.04 }, 0.05)
        .to(topFlare, { xPercent: 430, duration: 0.22, ease: 'power2.inOut' }, 0.05)
        .to(topFlare, { opacity: 0, duration: 0.04 }, 0.27)
        .to(bottomSeparator, { scaleX: 1, duration: 0.25, ease: 'expo.inOut' }, 0.06)
        .to(bottomFlare, { opacity: 1, duration: 0.04 }, 0.07)
        .to(bottomFlare, { xPercent: -430, duration: 0.22, ease: 'power2.inOut' }, 0.07)
        .to(bottomFlare, { opacity: 0, duration: 0.04 }, 0.29)
        .to(
          primaryWords,
          {
            yPercent: 0,
            opacity: 1,
            rotateX: 0,
            filter: 'blur(0px)',
            duration: 0.22,
            stagger: { each: 0.012, from: 'start' },
            ease: 'power2.out'
          },
          0.08
        )

        // ===== HOLD / PIN PHASE (0.32 to 0.68): bez ruchu =====

        // ===== EXIT PHASE (0.68 to 1.00) =====
        .to(
          primaryWords,
          {
            yPercent: -80,
            opacity: 0,
            rotateX: 20,
            filter: 'blur(10px)',
            duration: 0.22,
            stagger: { each: 0.01, from: 'end' },
            ease: 'power2.in'
          },
          0.68
        )
        .to(topFlare, { opacity: 1, duration: 0.04 }, 0.72)
        .to(topFlare, { xPercent: -130, duration: 0.22, ease: 'power2.inOut' }, 0.72)
        .to(topFlare, { opacity: 0, duration: 0.04 }, 0.94)
        .to(topSeparator, { scaleX: 0, duration: 0.24, ease: 'expo.inOut' }, 0.72)
        .to(bottomFlare, { opacity: 1, duration: 0.04 }, 0.74)
        .to(bottomFlare, { xPercent: 130, duration: 0.22, ease: 'power2.inOut' }, 0.74)
        .to(bottomFlare, { opacity: 0, duration: 0.04 }, 0.96)
        .to(bottomSeparator, { scaleX: 0, duration: 0.24, ease: 'expo.inOut' }, 0.74)
        .to(
          primaryWindow,
          { scale: 0.97, opacity: 0, duration: 0.2, ease: 'power2.in' },
          0.80
        )

        // ===== SECOND QUOTE ENTRANCE (1.00 to 1.42) =====
        .fromTo(
          secondaryWindow,
          { clipPath: 'inset(50% 0 50% 0)', opacity: 0 },
          {
            clipPath: 'inset(0% 0 0% 0)',
            opacity: 1,
            duration: 0.28,
            ease: 'expo.out'
          },
          1.00
        )
        .to(topSeparator, { scaleX: 1, duration: 0.28, ease: 'expo.inOut' }, 1.00)
        .to(bottomSeparator, { scaleX: 1, duration: 0.28, ease: 'expo.inOut' }, 1.02)
        .to(
          aurora,
          {
            xPercent: 140,
            scaleX: 1,
            opacity: 0.9,
            duration: 0.34,
            ease: 'power2.inOut'
          },
          1.02
        )
        .to(aurora, { opacity: 0, duration: 0.08 }, 1.34)
        .to(
          secondaryWords,
          {
            yPercent: 0,
            opacity: 1,
            scale: 1,
            rotateX: 0,
            filter: 'blur(0px)',
            duration: 0.22,
            stagger: { amount: 0.14, from: 'center' },
            ease: 'power3.out'
          },
          1.04
        )
        .to(
          accentWords,
          {
            color: '#f5f7fa',
            textShadow: '0 0 22px rgba(170, 207, 255, 0.28)',
            duration: 0.18,
            stagger: { amount: 0.08, from: 'start' }
          },
          1.18
        )

        // ===== SECOND QUOTE HOLD / PIN (1.42 to 1.78): bez ruchu =====

        // ===== SECOND QUOTE EXIT (1.78 to 2.14) =====
        .to(
          secondaryWords,
          {
            yPercent: -62,
            opacity: 0,
            scale: 1.025,
            rotateX: 16,
            filter: 'blur(12px)',
            duration: 0.24,
            stagger: { amount: 0.1, from: 'edges' },
            ease: 'power2.in'
          },
          1.78
        )
        .to(
          secondaryWindow,
          {
            clipPath: 'inset(50% 0 50% 0)',
            opacity: 0,
            duration: 0.3,
            ease: 'expo.inOut'
          },
          1.84
        )
        .to(topSeparator, { scaleX: 0, duration: 0.28, ease: 'expo.inOut' }, 1.86)
        .to(bottomSeparator, { scaleX: 0, duration: 0.28, ease: 'expo.inOut' }, 1.86);
    }

    var targetX = 0;
    var targetY = 0;
    var currentX = 0;
    var currentY = 0;
    var raf = 0;
    var reveal = 0;
    var revealApplied = false;
    var lastTextProgress = -1;
    var lastGalleryProgress = -1;
    var galleryActive = false;
    var listening = false;

    function applyLayer() {
      var x = currentX * -MAX_SHIFT_X;
      var y = currentY * -MAX_SHIFT_Y;
      layer.style.transform =
        'translate(' + x.toFixed(2) + 'px, ' + y.toFixed(2) + 'px)';
    }

    function frame() {
      raf = 0;
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;
      applyLayer();
      if (
        Math.abs(targetX - currentX) > 0.0008 ||
        Math.abs(targetY - currentY) > 0.0008
      ) {
        raf = window.requestAnimationFrame(frame);
      }
    }

    function requestFrame() {
      if (!raf) raf = window.requestAnimationFrame(frame);
    }

    function onPointerMove(event) {
      if (!parallaxEnabled || reveal < 0.02) return;
      var width = window.innerWidth || 1;
      var height = window.innerHeight || 1;
      targetX = (event.clientX / width - 0.5) * 2;
      targetY = (event.clientY / height - 0.5) * 2;
      requestFrame();

      if (window.gsap && section && !reducedMotion && !galleryActive) {
        var normalizedX = event.clientX / width - 0.5;
        var normalizedY = event.clientY / height - 0.5;

        gsap.to(section.querySelectorAll('.quote-content'), {
          rotateY: normalizedX * 16,
          rotateX: -normalizedY * 12,
          x: normalizedX * 24,
          y: normalizedY * 16,
          duration: 1.2,
          ease: 'power2.out',
          overwrite: 'auto'
        });
      }
    }

    function onPointerLeave() {
      targetX = 0;
      targetY = 0;
      requestFrame();

      if (window.gsap && section && !reducedMotion && !galleryActive) {
        gsap.to(section.querySelectorAll('.quote-content'), {
          rotateY: 0,
          rotateX: 0,
          x: 0,
          y: 0,
          duration: 1.4,
          ease: 'power2.out',
          overwrite: 'auto'
        });
      }
    }

    function setListening(on) {
      if (on === listening) return;
      listening = on;
      if (on) {
        window.addEventListener('pointermove', onPointerMove, { passive: true });
        window.addEventListener('pointerleave', onPointerLeave);
      } else {
        window.removeEventListener('pointermove', onPointerMove);
        window.removeEventListener('pointerleave', onPointerLeave);
        targetX = 0;
        targetY = 0;
        requestFrame();
      }
    }

    var api = {
      root: root,
      setReveal: function (value) {
        var nextReveal = Math.max(0, Math.min(1, Number(value) || 0));
        if (revealApplied && Math.abs(nextReveal - reveal) < 0.0005) {
          return reveal;
        }
        reveal = nextReveal;
        revealApplied = true;
        root.style.opacity = reveal.toFixed(4);
        root.classList.toggle('is-active', reveal > 0.001);
        // Paralaksa Bottom zostaje aktywna także pod galerią Przed/Po,
        // o ile włączono ją w GicleeApp (Paralaksa tła).
        setListening(parallaxEnabled && reveal > 0.02 && !reducedMotion);
        return reveal;
      },
      setTextProgress: function (value) {
        var progress = Math.max(0, Math.min(1, Number(value) || 0));
        if (Math.abs(progress - lastTextProgress) < 0.0005) return progress;
        lastTextProgress = progress;
        buildTimeline();
        if (timeline) {
          timeline.pause().progress(progress);
        }
        syncBreathing(progress);
        section.setAttribute(
          'data-fm-cinematic-text-progress',
          progress.toFixed(3)
        );
        return progress;
      },
      setGalleryProgress: function (value) {
        if (!galleryApi || typeof galleryApi.setProgress !== 'function') return 0;
        var progress = Math.max(0, Math.min(1, Number(value) || 0));
        if (Math.abs(progress - lastGalleryProgress) < 0.0005) return progress;
        lastGalleryProgress = progress;
        galleryActive = progress > 0.001 && progress < 0.999;
        if (preservePrevBg) {
          // Ukryj napisy/separatory, ale zostaw winietę i inne efekty tła.
          section.classList.toggle('is-gallery-overlay', galleryActive);
          section.style.visibility =
            progress >= 0.999 ? 'hidden' : 'visible';
        } else {
          section.classList.remove('is-gallery-overlay');
          section.style.visibility = progress > 0.001 ? 'hidden' : 'visible';
        }
        setListening(parallaxEnabled && reveal > 0.02 && !reducedMotion);
        return galleryApi.setProgress(progress);
      },
      getGalleryDurationVh: function () {
        return galleryApi && Number.isFinite(galleryApi.durationVh)
          ? galleryApi.durationVh
          : 0;
      },
      getGalleryCount: function () {
        return galleryApi && Number.isFinite(galleryApi.count)
          ? galleryApi.count
          : 0;
      },
      destroy: function () {
        setListening(false);
        if (raf) window.cancelAnimationFrame(raf);
        raf = 0;
        if (timeline) {
          timeline.kill();
          timeline = null;
        }
        breathTweens.forEach(function (tween) {
          tween.kill();
        });
        breathTweens = [];
        if (galleryApi && typeof galleryApi.destroy === 'function') {
          galleryApi.destroy();
        }
        galleryApi = null;
        if (root.parentNode) root.parentNode.removeChild(root);
        delete root.__gicleeFmParallax;
      },
    };

    root.__gicleeFmParallax = api;
    api.setReveal(0);
    api.setTextProgress(0);
    api.setGalleryProgress(0);
    applyLayer();
    return api;
  }

  window.GicleeFmWrotaParallax = {
    mount: mount,
    readAssets: readAssets,
  };
})();
