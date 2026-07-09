(function () {
  var map = window.GICLEE_HOME_SECTIONS;
  if (!map || typeof map !== 'object') return;

  var SR_DEFAULTS = {
    enabled: true,
    desktopEnabled: true,
    revealThreshold: 0.25,
    durationMs: 980,
    cardDurationMs: 1100,
    textDurationMs: 900,
    hoverDurationMs: 850,
    headingDelayMs: 120,
    paragraphStaggerMs: 140,
    bgBrightnessStart: 88,
    lightOpacityMin: 5.5,
    lightOpacityMax: 11,
    cardHoverScale: 1.018,
    cardImageHoverScale: 1.025,
    copyHoverScale: 1.022,
    copyHoverTranslateY: -4,
    glowEnabled: true,
    easingBezier: '0.16, 1, 0.3, 1',
    gradientPreset: 'editorial',
    gradientOverlayOpacity: 100,
    radialCenterX: 35,
    radialCenterY: 50,
    radialRadiusX: 55,
    radialRadiusY: 85,
    radialFeather: 50,
    radialExposure: 50,
    parallaxEnabled: true,
    parallaxMaxX: 18,
    parallaxMaxY: 12,
    parallaxEase: 0.075,
    parallaxOverscan: 1.06,
  };

  var EASING_BEZIER = {
    museum: '0.16, 1, 0.3, 1',
    soft: '0.25, 1, 0.5, 1',
    crisp: '0.22, 1, 0.36, 1',
  };

  var BG_KEYS_FOR_SCROLL_REVEAL = [
    'gradientPreset',
    'gradientOverlayOpacity',
    'radialCenterX',
    'radialCenterY',
    'radialRadiusX',
    'radialRadiusY',
    'radialFeather',
    'radialExposure',
    'parallaxEnabled',
    'parallaxMaxX',
    'parallaxMaxY',
    'parallaxEase',
    'parallaxOverscan',
  ];

  function mergeStudioRevealConfig(userOverride) {
    var user =
      userOverride !== undefined ? userOverride : window.GICLEE_HOME_STUDIO_REVEAL_CONFIG;
    var cfg = {};
    Object.keys(SR_DEFAULTS).forEach(function (key) {
      cfg[key] =
        user && Object.prototype.hasOwnProperty.call(user, key) ? user[key] : SR_DEFAULTS[key];
    });
    cfg.revealThreshold = Math.min(1, Math.max(0.05, Number(cfg.revealThreshold) || 0.25));
    cfg.durationMs = Math.max(0, Number(cfg.durationMs) || SR_DEFAULTS.durationMs);
    cfg.cardDurationMs = Math.max(0, Number(cfg.cardDurationMs) || SR_DEFAULTS.cardDurationMs);
    cfg.textDurationMs = Math.max(0, Number(cfg.textDurationMs) || SR_DEFAULTS.textDurationMs);
    cfg.hoverDurationMs = Math.max(0, Number(cfg.hoverDurationMs) || SR_DEFAULTS.hoverDurationMs);
    cfg.headingDelayMs = Math.max(0, Number(cfg.headingDelayMs) || 0);
    cfg.paragraphStaggerMs = Math.max(0, Number(cfg.paragraphStaggerMs) || 0);
    cfg.bgBrightnessStart = Math.min(100, Math.max(50, Number(cfg.bgBrightnessStart) || 88));
    cfg.lightOpacityMin = Math.min(20, Math.max(0, Number(cfg.lightOpacityMin) || 0)) / 100;
    cfg.lightOpacityMax = Math.min(20, Math.max(0, Number(cfg.lightOpacityMax) || 0)) / 100;
    cfg.cardHoverScale = Math.min(1.05, Math.max(1, Number(cfg.cardHoverScale) || 1.018));
    cfg.cardImageHoverScale = Math.min(1.08, Math.max(1, Number(cfg.cardImageHoverScale) || 1.025));
    cfg.copyHoverScale = Math.min(1.05, Math.max(1, Number(cfg.copyHoverScale) || 1.022));
    cfg.copyHoverTranslateY = Math.max(-12, Math.min(0, Number(cfg.copyHoverTranslateY) || -4));
    var gradient = String(cfg.gradientPreset || 'editorial').toLowerCase();
    cfg.gradientPreset = ['none', 'editorial', 'menu_wide', 'menu_narrow', 'radial_spot'].indexOf(gradient) >= 0
      ? gradient
      : 'editorial';
    cfg.gradientOverlayOpacity = Math.min(100, Math.max(0, Number(cfg.gradientOverlayOpacity) || 100));
    cfg.radialCenterX = Math.min(100, Math.max(0, Number(cfg.radialCenterX) || 35));
    cfg.radialCenterY = Math.min(100, Math.max(0, Number(cfg.radialCenterY) || 50));
    cfg.radialRadiusX = Math.min(120, Math.max(20, Number(cfg.radialRadiusX) || 55));
    cfg.radialRadiusY = Math.min(120, Math.max(20, Number(cfg.radialRadiusY) || 85));
    cfg.radialFeather = Math.min(100, Math.max(0, Number(cfg.radialFeather) || 50));
    cfg.radialExposure = Math.min(100, Math.max(0, Number(cfg.radialExposure) || 50));
    cfg.parallaxEnabled = cfg.parallaxEnabled !== false;
    cfg.parallaxMaxX = Math.min(40, Math.max(0, Number(cfg.parallaxMaxX) || 18));
    cfg.parallaxMaxY = Math.min(28, Math.max(0, Number(cfg.parallaxMaxY) || 12));
    cfg.parallaxEase = Math.min(0.15, Math.max(0.03, Number(cfg.parallaxEase) || 0.075));
    var overscan = Number(cfg.parallaxOverscan);
    cfg.parallaxOverscan = overscan > 3 ? overscan / 100 : Math.min(1.12, Math.max(1, overscan || 1.06));
    if (!cfg.easingBezier && user && user.easing && EASING_BEZIER[user.easing]) {
      cfg.easingBezier = EASING_BEZIER[user.easing];
    }
    return cfg;
  }

  function mergeHookScrollRevealConfig(hook) {
    var effects = window.GICLEE_HOME_SECTION_EFFECTS_CONFIG;
    var raw =
      effects && effects[hook] && effects[hook].scroll_reveal ? effects[hook].scroll_reveal : null;
    if (!raw || !raw.enabled) return null;

    var user = {};
    Object.keys(raw).forEach(function (key) {
      user[key] = raw[key];
    });

    var bgAll = window.GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG;
    if (bgAll && bgAll[hook]) {
      var bg = mergeSectionBgEffectsConfig(bgAll[hook]);
      BG_KEYS_FOR_SCROLL_REVEAL.forEach(function (key) {
        if (Object.prototype.hasOwnProperty.call(bg, key)) {
          user[key] = bg[key];
        }
      });
    } else {
      user.gradientPreset = user.gradientPreset || 'none';
      user.parallaxEnabled = user.parallaxEnabled === true;
    }

    return mergeStudioRevealConfig(user);
  }

  function applyStudioRevealConfig(sectionInner, cfg) {
    if (!sectionInner || !cfg) return;

    sectionInner.style.setProperty('--ghsr-duration', String(cfg.durationMs) + 'ms');
    sectionInner.style.setProperty('--ghsr-card-duration', String(cfg.cardDurationMs) + 'ms');
    sectionInner.style.setProperty('--ghsr-text-duration', String(cfg.textDurationMs) + 'ms');
    sectionInner.style.setProperty('--ghsr-hover-duration', String(cfg.hoverDurationMs) + 'ms');
    sectionInner.style.setProperty('--ghsr-heading-delay', String(cfg.headingDelayMs) + 'ms');
    sectionInner.style.setProperty('--ghsr-paragraph-stagger', String(cfg.paragraphStaggerMs) + 'ms');
    sectionInner.style.setProperty(
      '--ghsr-bg-brightness-start',
      String(cfg.bgBrightnessStart / 100)
    );
    sectionInner.style.setProperty('--ghsr-light-opacity-min', String(cfg.lightOpacityMin));
    sectionInner.style.setProperty('--ghsr-light-opacity-max', String(cfg.lightOpacityMax));
    sectionInner.style.setProperty('--ghsr-card-hover-scale', String(cfg.cardHoverScale));
    sectionInner.style.setProperty(
      '--ghsr-card-image-hover-scale',
      String(cfg.cardImageHoverScale)
    );
    sectionInner.style.setProperty('--ghsr-copy-hover-scale', String(cfg.copyHoverScale));
    sectionInner.style.setProperty(
      '--ghsr-copy-hover-translate-y',
      String(cfg.copyHoverTranslateY) + 'px'
    );
    sectionInner.style.setProperty(
      '--ghsr-ease',
      'cubic-bezier(' + (cfg.easingBezier || SR_DEFAULTS.easingBezier) + ')'
    );
    sectionInner.style.setProperty(
      '--ghsr-gradient-overlay-opacity',
      String((Number(cfg.gradientOverlayOpacity) || 100) / 100)
    );
    sectionInner.style.setProperty('--ghsr-radial-cx', String(cfg.radialCenterX) + '%');
    sectionInner.style.setProperty('--ghsr-radial-cy', String(cfg.radialCenterY) + '%');
    sectionInner.style.setProperty('--ghsr-radial-rx', String(cfg.radialRadiusX) + '%');
    sectionInner.style.setProperty('--ghsr-radial-ry', String(cfg.radialRadiusY) + '%');
    sectionInner.style.setProperty('--ghsr-radial-feather', String(cfg.radialFeather));
    sectionInner.style.setProperty('--ghsr-radial-exposure', String(cfg.radialExposure));
    sectionInner.style.setProperty('--ghsr-parallax-scale', String(cfg.parallaxOverscan));

    sectionInner.classList.toggle('giclee-home-studio-reveal--motion', !!cfg.enabled);
    sectionInner.classList.toggle('giclee-home-studio-reveal--glow', !!cfg.enabled && !!cfg.glowEnabled);
    sectionInner.classList.toggle(
      'giclee-home-studio-reveal--parallax',
      !!cfg.enabled && !!cfg.parallaxEnabled && !!cfg.desktopEnabled
    );
    if (!cfg.desktopEnabled) {
      sectionInner.classList.remove('giclee-home-studio-reveal--motion');
      sectionInner.classList.remove('giclee-home-studio-reveal--parallax');
    }
  }

  function applyStudioGradientLayers(bg, cfg) {
    if (!bg || !cfg || cfg.gradientPreset === 'none') return;

    bg.classList.add('giclee-home-studio-reveal__bg--gradient-' + cfg.gradientPreset);

    if (cfg.gradientPreset === 'editorial' && !bg.querySelector('.giclee-home-studio-reveal__overlay')) {
      var overlay = document.createElement('div');
      overlay.className = 'giclee-home-studio-reveal__overlay';
      overlay.setAttribute('aria-hidden', 'true');
      bg.appendChild(overlay);
    }

    if (cfg.gradientPreset === 'radial_spot' && !bg.querySelector('.giclee-home-studio-reveal__radial-mask')) {
      var radial = document.createElement('div');
      radial.className = 'giclee-home-studio-reveal__radial-mask';
      radial.setAttribute('aria-hidden', 'true');
      bg.appendChild(radial);
    }
  }

  function initStudioParallax(root, cfg) {
    if (!root || !cfg || !cfg.enabled || !cfg.parallaxEnabled || !cfg.desktopEnabled) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (window.matchMedia('(max-width: 749px)').matches) return;
    if (window.matchMedia('(pointer: coarse)').matches) return;

    var bg = root.querySelector('.giclee-home-studio-reveal__bg');
    if (!bg) return;

    var layer = bg.querySelector('.background-image-container');
    if (!layer) return;

    layer.classList.add('giclee-home-studio-reveal__parallax-layer');

    var targetX = 0;
    var targetY = 0;
    var curX = 0;
    var curY = 0;
    var rafId = 0;
    var ease = cfg.parallaxEase || 0.075;
    var maxX = cfg.parallaxMaxX || 18;
    var maxY = cfg.parallaxMaxY || 12;

    function tick() {
      rafId = 0;
      curX += (targetX - curX) * ease;
      curY += (targetY - curY) * ease;
      root.style.setProperty('--ghsr-parallax-x', (-curX * maxX).toFixed(2) + 'px');
      root.style.setProperty('--ghsr-parallax-y', (-curY * maxY).toFixed(2) + 'px');
      if (Math.abs(targetX - curX) > 0.0008 || Math.abs(targetY - curY) > 0.0008) {
        rafId = window.requestAnimationFrame(tick);
      }
    }

    function startLoop() {
      if (!rafId) rafId = window.requestAnimationFrame(tick);
    }

    function onPointerMove(event) {
      var rect = root.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      ) {
        return;
      }
      var nx = ((event.clientX - rect.left) / (rect.width || 1)) * 2 - 1;
      var ny = ((event.clientY - rect.top) / (rect.height || 1)) * 2 - 1;
      targetX = Math.max(-1, Math.min(1, nx));
      targetY = Math.max(-1, Math.min(1, ny));
      startLoop();
    }

    function recenter() {
      targetX = 0;
      targetY = 0;
      startLoop();
    }

    root.addEventListener('pointermove', onPointerMove, { passive: true });
    root.addEventListener('pointerleave', recenter, { passive: true });
    root.addEventListener('blur', recenter, true);
  }

  function initStudioRevealObserver(root, cfg, sectionEl) {
    if (!root || !cfg) return;

    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reducedMotion || !cfg.enabled) {
      root.classList.add('is-revealed');
      return;
    }

    if (root.classList.contains('is-revealed')) return;

    var stackMode = !!window.GICLEE_HOME_STACK;
    var revealThreshold = stackMode
      ? Math.min(cfg.revealThreshold, 0.08)
      : cfg.revealThreshold;
    var revealed = false;
    var observer = null;

    function reveal() {
      if (revealed) return;
      revealed = true;
      root.classList.add('is-revealed');
      if (observer) observer.disconnect();
    }

    function visibleRatio(rect) {
      var vh = window.innerHeight || 1;
      var visible = Math.min(rect.bottom, vh) - Math.max(rect.top, 0);
      return visible / Math.max(1, Math.min(rect.height, vh));
    }

    function shouldRevealByGeometry() {
      var target = root;
      if (stackMode && sectionEl) {
        var sectionRect = sectionEl.getBoundingClientRect();
        if (sectionRect.bottom <= (window.innerHeight || 1) * 0.06) return false;
        if (sectionRect.top >= (window.innerHeight || 1) * 0.98) return false;
        target = sectionEl;
      }
      return visibleRatio(target.getBoundingClientRect()) >= revealThreshold;
    }

    function tryReveal() {
      if (revealed) return;
      if (shouldRevealByGeometry()) reveal();
    }

    if (!root.dataset.gicleeRevealBound) {
      root.dataset.gicleeRevealBound = '1';

      if ('IntersectionObserver' in window) {
        observer = new IntersectionObserver(
          function (entries) {
            entries.forEach(function (entry) {
              if (entry.isIntersecting && entry.intersectionRatio >= revealThreshold) reveal();
            });
          },
          {
            threshold: stackMode ? [0, 0.05, 0.1, 0.2, revealThreshold] : revealThreshold,
            rootMargin: stackMode ? '0px 0px 0px 0px' : '0px 0px -8% 0px',
          }
        );
        observer.observe(stackMode && sectionEl ? sectionEl : root);
      }

      if (stackMode) {
        window.addEventListener('scroll', tryReveal, { passive: true });
      }
    }

    tryReveal();
    if (!revealed && !('IntersectionObserver' in window)) {
      reveal();
    }
  }

  function enhanceStudioRevealMedia(sectionEl) {
    if (!sectionEl) return;

    var imageBlock = sectionEl.querySelector('.image-block');
    if (imageBlock) {
      imageBlock.classList.add('giclee-home-studio-reveal__card');
      var img = imageBlock.querySelector('.image-block__image, img');
      if (img) img.classList.add('giclee-home-studio-reveal__card-image');
      return;
    }

    var slider = sectionEl.querySelector('comparison-slider-component');
    if (slider) slider.classList.add('giclee-home-studio-reveal__card');
  }

  function enhanceStudioRevealCopy(sectionEl, cfg) {
    if (!sectionEl || !cfg) return;

    var paragraphIndex = 0;
    var headingSeen = false;

    sectionEl.querySelectorAll('.text-block').forEach(function (textBlock) {
      if (textBlock.closest('[hidden]')) return;
      if (textBlock.getClientRects().length === 0) return;

      var heading = textBlock.querySelector('h2');
      var paragraphs = textBlock.querySelectorAll('p');
      var participates = false;

      if (heading) {
        headingSeen = true;
        participates = true;
        heading.classList.add('giclee-home-studio-reveal__heading');
      } else if (headingSeen && paragraphs.length) {
        participates = true;
      }

      if (!participates) return;

      textBlock.classList.add('giclee-home-studio-reveal__copy');
      if (!textBlock.hasAttribute('tabindex')) {
        textBlock.setAttribute('tabindex', '0');
      }

      paragraphs.forEach(function (paragraph) {
        var copy = (paragraph.textContent || '').replace(/\s+/g, ' ').trim();
        if (!copy) return;
        paragraph.classList.add('giclee-home-studio-reveal__paragraph');
        paragraph.style.setProperty(
          '--ghsr-paragraph-delay',
          String(cfg.headingDelayMs + (paragraphIndex + 1) * cfg.paragraphStaggerMs) + 'ms'
        );
        paragraphIndex += 1;
      });
    });
  }

  function stripStudioRevealEnhancement(sectionEl) {
    if (!sectionEl) return;

    var sectionInner = sectionEl.querySelector('.section');
    if (!sectionInner) return;

    sectionInner.classList.remove(
      'giclee-home-studio-reveal',
      'giclee-home-studio-reveal--motion',
      'giclee-home-studio-reveal--glow',
      'giclee-home-studio-reveal--parallax',
      'is-revealed'
    );
    delete sectionInner.dataset.gicleeRevealBound;
    delete sectionInner.dataset.gicleeParallaxBound;

    var bg = sectionInner.querySelector('.custom-section-background');
    if (bg) {
      bg.classList.remove('giclee-home-studio-reveal__bg');
      ['none', 'editorial', 'menu_wide', 'menu_narrow', 'radial_spot'].forEach(function (preset) {
        bg.classList.remove('giclee-home-studio-reveal__bg--gradient-' + preset);
      });
      bg.querySelectorAll(
        '.giclee-home-studio-reveal__overlay, .giclee-home-studio-reveal__radial-mask'
      ).forEach(function (el) {
        el.remove();
      });
      bg.querySelectorAll('.giclee-home-studio-reveal__parallax-layer').forEach(function (el) {
        el.classList.remove('giclee-home-studio-reveal__parallax-layer');
      });
    }

    sectionEl.querySelectorAll('.giclee-home-studio-reveal__card').forEach(function (el) {
      el.classList.remove('giclee-home-studio-reveal__card');
    });
    sectionEl.querySelectorAll('.giclee-home-studio-reveal__card-image').forEach(function (el) {
      el.classList.remove('giclee-home-studio-reveal__card-image');
    });
    sectionEl.querySelectorAll('.giclee-home-studio-reveal__copy').forEach(function (el) {
      el.classList.remove('giclee-home-studio-reveal__copy');
    });
    sectionEl.querySelectorAll('.giclee-home-studio-reveal__heading').forEach(function (el) {
      el.classList.remove('giclee-home-studio-reveal__heading');
    });
    sectionEl.querySelectorAll('.giclee-home-studio-reveal__paragraph').forEach(function (el) {
      el.classList.remove('giclee-home-studio-reveal__paragraph');
      el.style.removeProperty('--ghsr-paragraph-delay');
    });
  }

  function enhanceIntro(sectionEl, cfg) {
    if (!sectionEl || !cfg) return;

    var sectionInner = sectionEl.querySelector('.section');
    if (!sectionInner) return;

    if (!cfg.enabled) {
      stripStudioRevealEnhancement(sectionEl);
      return;
    }

    var firstPass = !sectionInner.classList.contains('giclee-home-studio-reveal');
    sectionInner.classList.add('giclee-home-studio-reveal');
    applyStudioRevealConfig(sectionInner, cfg);

    var bg = sectionInner.querySelector('.custom-section-background');
    if (bg) {
      bg.classList.add('giclee-home-studio-reveal__bg');
      applyStudioGradientLayers(bg, cfg);
    }

    if (firstPass) {
      enhanceStudioRevealMedia(sectionEl);
      enhanceStudioRevealCopy(sectionEl, cfg);
    }

    initStudioRevealObserver(sectionInner, cfg, sectionEl);

    if (!sectionInner.dataset.gicleeParallaxBound) {
      initStudioParallax(sectionInner, cfg);
      sectionInner.dataset.gicleeParallaxBound = '1';
    }
  }

  function applySharedBgEffectsConfig(sectionInner, cfg) {
    if (!sectionInner || !cfg) return;
    sectionInner.style.setProperty(
      '--ghsr-gradient-overlay-opacity',
      String((Number(cfg.gradientOverlayOpacity) || 100) / 100)
    );
    sectionInner.style.setProperty('--ghsr-radial-cx', String(cfg.radialCenterX) + '%');
    sectionInner.style.setProperty('--ghsr-radial-cy', String(cfg.radialCenterY) + '%');
    sectionInner.style.setProperty('--ghsr-radial-rx', String(cfg.radialRadiusX) + '%');
    sectionInner.style.setProperty('--ghsr-radial-ry', String(cfg.radialRadiusY) + '%');
    sectionInner.style.setProperty('--ghsr-radial-feather', String(cfg.radialFeather));
    sectionInner.style.setProperty('--ghsr-radial-exposure', String(cfg.radialExposure));
    sectionInner.style.setProperty('--ghsr-parallax-scale', String(cfg.parallaxOverscan));
    sectionInner.classList.toggle(
      'giclee-home-section-bg-effects--parallax',
      !!cfg.enabled && !!cfg.parallaxEnabled && !!cfg.desktopEnabled
    );
  }

  var SBE_DEFAULTS = {
    enabled: false,
    desktopEnabled: true,
    gradientPreset: 'none',
    gradientOverlayOpacity: 100,
    radialCenterX: 35,
    radialCenterY: 50,
    radialRadiusX: 55,
    radialRadiusY: 85,
    radialFeather: 50,
    radialExposure: 50,
    parallaxEnabled: false,
    parallaxMaxX: 16,
    parallaxMaxY: 10,
    parallaxEase: 0.075,
    parallaxOverscan: 1.06,
  };

  function mergeSectionBgEffectsConfig(raw) {
    var user = raw && typeof raw === 'object' ? raw : {};
    var cfg = {};
    Object.keys(SBE_DEFAULTS).forEach(function (key) {
      cfg[key] =
        Object.prototype.hasOwnProperty.call(user, key) ? user[key] : SBE_DEFAULTS[key];
    });
    cfg.enabled = Boolean(cfg.enabled);
    cfg.desktopEnabled = cfg.desktopEnabled !== false;
    cfg.parallaxEnabled = cfg.parallaxEnabled === true || cfg.parallaxEnabled === 1;
    var gradient = String(cfg.gradientPreset || 'none').toLowerCase();
    cfg.gradientPreset = ['none', 'editorial', 'menu_wide', 'menu_narrow', 'radial_spot'].indexOf(gradient) >= 0
      ? gradient
      : 'none';
    cfg.gradientOverlayOpacity = Math.min(100, Math.max(0, Number(cfg.gradientOverlayOpacity) || 100));
    cfg.radialCenterX = Math.min(100, Math.max(0, Number(cfg.radialCenterX) || 35));
    cfg.radialCenterY = Math.min(100, Math.max(0, Number(cfg.radialCenterY) || 50));
    cfg.radialRadiusX = Math.min(120, Math.max(20, Number(cfg.radialRadiusX) || 55));
    cfg.radialRadiusY = Math.min(120, Math.max(20, Number(cfg.radialRadiusY) || 85));
    cfg.radialFeather = Math.min(100, Math.max(0, Number(cfg.radialFeather) || 50));
    cfg.radialExposure = Math.min(100, Math.max(0, Number(cfg.radialExposure) || 50));
    cfg.parallaxMaxX = Math.min(40, Math.max(0, Number(cfg.parallaxMaxX) || 16));
    cfg.parallaxMaxY = Math.min(28, Math.max(0, Number(cfg.parallaxMaxY) || 10));
    cfg.parallaxEase = Math.min(0.15, Math.max(0.03, Number(cfg.parallaxEase) || 0.075));
    var overscan = Number(cfg.parallaxOverscan);
    cfg.parallaxOverscan = overscan > 3 ? overscan / 100 : Math.min(1.12, Math.max(1, overscan || 1.06));
    return cfg;
  }

  function enhanceSectionBgEffects(sectionEl, cfg) {
    if (!sectionEl || !cfg || !cfg.enabled) return;

    var sectionInner = sectionEl.querySelector('.section');
    if (!sectionInner) return;
    if (sectionInner.classList.contains('giclee-home-studio-reveal')) return;

    sectionInner.classList.add('giclee-home-section-bg-effects');
    applySharedBgEffectsConfig(sectionInner, cfg);

    var bg = sectionInner.querySelector('.custom-section-background');
    if (bg) {
      bg.classList.add('giclee-home-studio-reveal__bg');
      applyStudioGradientLayers(bg, cfg);
    }

    if (!sectionInner.dataset.gicleeParallaxBound) {
      initStudioParallax(sectionInner, cfg);
      sectionInner.dataset.gicleeParallaxBound = '1';
    }
  }

  function initAllSectionBgEffects() {
    var allCfg = window.GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG;
    if (!allCfg || typeof allCfg !== 'object') return;

    Object.keys(allCfg).forEach(function (hook) {
      if (hook === 'intro') return;
      var sectionKey = map[hook];
      if (!sectionKey) return;
      enhanceSectionBgEffects(findSection(sectionKey), mergeSectionBgEffectsConfig(allCfg[hook]));
    });
  }

  var FD_DEFAULTS = {
    enabled: true,
    desktopEnabled: true,
    copyScale: 1.062,
    copyTranslateY: -8,
    mediaOffsetX: 24,
    mediaScale: 0.965,
    mediaBrightness: 82,
    bgBrightness: 78,
    bgVeilOpacity: 16,
    durationMs: 850,
    easingBezier: '0.16, 1, 0.3, 1',
    glowEnabled: true,
    reverseBehavior: false,
  };

  function mergeFinalDifferenceConfig(userOverride) {
    var user =
      userOverride !== undefined ? userOverride : window.GICLEE_HOME_FINAL_DIFFERENCE_CONFIG;
    var cfg = {};
    Object.keys(FD_DEFAULTS).forEach(function (key) {
      cfg[key] =
        user && Object.prototype.hasOwnProperty.call(user, key)
          ? user[key]
          : FD_DEFAULTS[key];
    });
    if (!cfg.easingBezier && user && user.easing === 'soft') {
      cfg.easingBezier = '0.25, 1, 0.5, 1';
    } else if (!cfg.easingBezier && user && user.easing === 'crisp') {
      cfg.easingBezier = '0.22, 1, 0.36, 1';
    }
    cfg.copyScale = Math.min(1.12, Math.max(1, Number(cfg.copyScale) || FD_DEFAULTS.copyScale));
    cfg.mediaScale = Math.min(1, Math.max(0.9, Number(cfg.mediaScale) || FD_DEFAULTS.mediaScale));
    cfg.mediaOffsetX = Math.max(0, Number(cfg.mediaOffsetX) || 0);
    cfg.durationMs = Math.max(0, Number(cfg.durationMs) || FD_DEFAULTS.durationMs);
    if (!cfg.easingBezier && user && user.easing && EASING_BEZIER[user.easing]) {
      cfg.easingBezier = EASING_BEZIER[user.easing];
    }
    return cfg;
  }

  function applyFinalDifferenceConfig(sectionInner, cfg) {
    if (!sectionInner || !cfg) return;

    sectionInner.style.setProperty('--gfd-copy-scale', String(cfg.copyScale));
    sectionInner.style.setProperty('--gfd-copy-translate-y', String(cfg.copyTranslateY) + 'px');
    sectionInner.style.setProperty('--gfd-media-offset-x', String(cfg.mediaOffsetX) + 'px');
    sectionInner.style.setProperty('--gfd-media-scale', String(cfg.mediaScale));
    sectionInner.style.setProperty(
      '--gfd-media-brightness',
      String((Number(cfg.mediaBrightness) || 82) / 100)
    );
    sectionInner.style.setProperty(
      '--gfd-bg-brightness',
      String((Number(cfg.bgBrightness) || 78) / 100)
    );
    sectionInner.style.setProperty(
      '--gfd-bg-veil',
      String((Number(cfg.bgVeilOpacity) || 0) / 100)
    );
    sectionInner.style.setProperty('--gfd-duration', String(cfg.durationMs) + 'ms');
    sectionInner.style.setProperty(
      '--gfd-ease',
      'cubic-bezier(' + (cfg.easingBezier || FD_DEFAULTS.easingBezier) + ')'
    );

    sectionInner.classList.toggle('giclee-home-final-difference--motion', !!cfg.enabled);
    sectionInner.classList.toggle(
      'giclee-home-final-difference--desktop',
      !!cfg.desktopEnabled
    );
    sectionInner.classList.toggle('giclee-home-final-difference--glow', !!cfg.glowEnabled);
    sectionInner.classList.toggle(
      'giclee-home-final-difference--reverse',
      !!cfg.reverseBehavior
    );

    if (!cfg.desktopEnabled) {
      sectionInner.classList.remove('giclee-home-final-difference--motion');
    }
  }

  function findSection(sectionKey) {
    if (!sectionKey) return null;
    return (
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]')
    );
  }

  function tagSection(hook, sectionKey) {
    var el = findSection(sectionKey);
    if (el) el.setAttribute('data-giclee-home', hook);
    return el;
  }

  function enhanceSeeDifference(sectionEl, cfg) {
    if (!sectionEl) return;

    var sectionInner = sectionEl.querySelector('.section');
    if (!sectionInner) return;

    sectionInner.classList.add('giclee-home-final-difference');
    applyFinalDifferenceConfig(sectionInner, cfg);

    var contentWrapper = sectionInner.querySelector('.section-content-wrapper');
    if (!contentWrapper) return;

    var sliders = contentWrapper.querySelectorAll('comparison-slider-component');
    if (sliders[0]) sliders[0].classList.add('giclee-final-difference__media--left');
    if (sliders[1]) sliders[1].classList.add('giclee-final-difference__media--right');

    var groupBlock = contentWrapper.querySelector('.group-block');
    if (groupBlock) {
      groupBlock.classList.add('giclee-final-difference__copy');
      if (!groupBlock.hasAttribute('tabindex')) {
        groupBlock.setAttribute('tabindex', '0');
      }
      if (!groupBlock.hasAttribute('role')) {
        groupBlock.setAttribute('role', 'group');
      }
      if (!groupBlock.hasAttribute('aria-label')) {
        groupBlock.setAttribute('aria-label', 'Zobacz różnicę');
      }
    }

    var bg = sectionInner.querySelector('.custom-section-background');
    if (bg) bg.classList.add('giclee-final-difference__bg');
  }

  var fdConfig = mergeFinalDifferenceConfig();
  var srConfig = mergeStudioRevealConfig();

  function initSeeDifference() {
    var sectionEl = tagSection('see-difference', map['see-difference']);
    enhanceSeeDifference(sectionEl, fdConfig);
  }

  function initIntro() {
    var sectionEl = tagSection('intro', map.intro);
    enhanceIntro(sectionEl, srConfig);
  }

  function initSectionEffectsForHook(hook) {
    if (!hook || hook === 'intro' || hook === 'see-difference') return;

    var sectionKey = map[hook];
    if (!sectionKey) return;

    var sectionEl = tagSection(hook, sectionKey);
    if (!sectionEl) return;

    var effects = window.GICLEE_HOME_SECTION_EFFECTS_CONFIG;
    if (!effects || !effects[hook]) return;

    var packs = effects[hook];
    if (packs.scroll_reveal && packs.scroll_reveal.enabled) {
      var srCfg = mergeHookScrollRevealConfig(hook);
      if (srCfg) enhanceIntro(sectionEl, srCfg);
    }
    if (packs.text_hover && packs.text_hover.enabled) {
      enhanceSeeDifference(sectionEl, mergeFinalDifferenceConfig(packs.text_hover));
    }
  }

  function initAllSectionEffects() {
    var effects = window.GICLEE_HOME_SECTION_EFFECTS_CONFIG;
    if (!effects || typeof effects !== 'object') return;
    Object.keys(effects).forEach(initSectionEffectsForHook);
  }

  function hookForSectionEl(sectionEl) {
    if (!sectionEl || !sectionEl.id) return null;
    var id = sectionEl.id;
    var found = null;
    Object.keys(map).forEach(function (hook) {
      if (map[hook] && id.indexOf(map[hook]) !== -1) found = hook;
    });
    return found;
  }

  function reinitSectionEffects(sectionEl, hook) {
    if (!sectionEl || !hook) return;
    sectionEl.setAttribute('data-giclee-home', hook);

    if (hook === 'intro') {
      enhanceIntro(sectionEl, mergeStudioRevealConfig());
      return;
    }
    if (hook === 'see-difference') {
      enhanceSeeDifference(sectionEl, mergeFinalDifferenceConfig());
      var sdBg = window.GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG;
      if (sdBg && sdBg['see-difference']) {
        enhanceSectionBgEffects(
          sectionEl,
          mergeSectionBgEffectsConfig(sdBg['see-difference'])
        );
      }
      return;
    }

    initSectionEffectsForHook(hook);
    var bgAll = window.GICLEE_HOME_SECTION_BG_EFFECTS_CONFIG;
    if (bgAll && bgAll[hook]) {
      enhanceSectionBgEffects(sectionEl, mergeSectionBgEffectsConfig(bgAll[hook]));
    }
  }

  Object.keys(map).forEach(function (hook) {
    if (hook === 'see-difference' || hook === 'intro') return;
    tagSection(hook, map[hook]);
  });

  function bootHomeSections() {
    initIntro();
    initSeeDifference();
    initAllSectionEffects();
    initAllSectionBgEffects();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootHomeSections);
  } else {
    bootHomeSections();
  }
  window.addEventListener('giclee:home-stack-ready', bootHomeSections);

  window.GICLEE_HOME_SECTIONS_BOOT_STATUS = function () {
    var out = {};
    Object.keys(map).forEach(function (hook) {
      var el = findSection(map[hook]);
      var inner = el && el.querySelector('.section');
      var effects = window.GICLEE_HOME_SECTION_EFFECTS_CONFIG;
      var scrollCfg = effects && effects[hook] && effects[hook].scroll_reveal;
      out[hook] = {
        found: !!el,
        studioReveal: !!(inner && inner.classList.contains('giclee-home-studio-reveal')),
        revealed: !!(inner && inner.classList.contains('is-revealed')),
        bgEffects: !!(inner && inner.classList.contains('giclee-home-section-bg-effects')),
        scrollRevealEnabled: !!(scrollCfg && scrollCfg.enabled),
        copyBlocks: el ? el.querySelectorAll('.giclee-home-studio-reveal__copy').length : 0,
        cards: el ? el.querySelectorAll('.giclee-home-studio-reveal__card').length : 0,
      };
    });
    return out;
  };

  document.addEventListener('shopify:section:load', function (event) {
    var sectionEl = event.target;
    if (!sectionEl || !sectionEl.classList || !sectionEl.classList.contains('shopify-section')) {
      return;
    }
    var hook = hookForSectionEl(sectionEl);
    if (hook) reinitSectionEffects(sectionEl, hook);
  });
})();
