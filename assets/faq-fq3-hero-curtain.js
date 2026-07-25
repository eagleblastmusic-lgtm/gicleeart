/* FAQ / Wersja 3 (fq3) — tło sekcji FAQ rozwija się od dołu i zakrywa hero. */
(function () {
  var runtime = /** @type {any} */ (window);

  if (runtime.__GICLEE_FAQ_FQ3_HERO_CURTAIN__) return;
  runtime.__GICLEE_FAQ_FQ3_HERO_CURTAIN__ = true;

  var config = runtime.GICLEE_PAGE_SECTION_EFFECTS;
  if (!config || config.page !== 'faq' || config.variant !== 'fq3') return;

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var desktop = window.matchMedia('(min-width: 750px)').matches;
  if (reducedMotion || !desktop) return;

  function getGsap() {
    return runtime.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  function getScrollTrigger() {
    return runtime.ScrollTrigger ||
      (typeof ScrollTrigger !== 'undefined' ? ScrollTrigger : undefined);
  }

  /** @param {(tween: any, scrollTrigger: any) => void} callback */
  function whenReady(callback) {
    var tween = getGsap();
    var scrollPlugin = getScrollTrigger();

    if (tween && scrollPlugin) {
      callback(tween, scrollPlugin);
      return;
    }

    var attempts = 0;
    var timer = window.setInterval(function () {
      attempts += 1;
      tween = getGsap();
      scrollPlugin = getScrollTrigger();

      if (tween && scrollPlugin) {
        window.clearInterval(timer);
        callback(tween, scrollPlugin);
        return;
      }

      if (attempts >= 50) window.clearInterval(timer);
    }, 50);
  }

  /** @param {Element | null} element @returns {HTMLElement | null} */
  function closestShopifySection(element) {
    if (!element) return null;
    var section = element.closest('[id^="shopify-section-"]');
    return section instanceof HTMLElement ? section : null;
  }

  /** @returns {HTMLElement | null} */
  function findHeroSection() {
    return closestShopifySection(document.querySelector('#MainContent .hero'));
  }

  /** @returns {HTMLElement | null} */
  function findFaqSection() {
    return closestShopifySection(document.querySelector('#MainContent .faq-section'));
  }

  function getHeaderHeight() {
    var headerGroup = document.getElementById('header-group');
    var header = document.getElementById('header-component');
    var element = headerGroup || header;

    if (element) {
      var rect = element.getBoundingClientRect();
      if (rect.height > 0) return Math.round(rect.height);
    }

    var cssValue = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue('--header-group-height');
    var parsed = parseFloat(cssValue);
    return isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0;
  }

  /** @param {HTMLElement} source @param {HTMLElement} target */
  function copyFaqVisualSettings(source, target) {
    var styles = window.getComputedStyle(source);
    var variables = [
      '--faq-bg-blur',
      '--faq-bg-saturate',
      '--faq-bg-brightness',
      '--faq-bg-dim-overlay',
      '--faq-bg-scale',
    ];

    variables.forEach(function (name) {
      var value = styles.getPropertyValue(name);
      if (value) target.style.setProperty(name, value.trim());
    });

    target.style.backgroundColor = styles.backgroundColor;
  }

  /**
   * @param {HTMLElement} heroSection
   * @param {HTMLElement} faqSection
   * @returns {HTMLElement | null}
   */
  function buildCurtain(heroSection, faqSection) {
    var heroContainer = heroSection.querySelector('.hero__container');
    var faqSurface = faqSection.querySelector('.faq-section');
    var sourceBackground = faqSection.querySelector('.custom-section-background');

    if (!(heroContainer instanceof HTMLElement)) return null;
    if (!(faqSurface instanceof HTMLElement)) return null;
    if (!(sourceBackground instanceof HTMLElement)) return null;

    var existing = heroContainer.querySelector('.giclee-faq-hero-curtain');
    if (existing instanceof HTMLElement) return existing;

    var curtain = document.createElement('div');
    curtain.className = 'giclee-faq-hero-curtain faq-section faq-section--bg-image';
    curtain.setAttribute('aria-hidden', 'true');

    var clonedBackground = /** @type {HTMLElement} */ (sourceBackground.cloneNode(true));
    clonedBackground.removeAttribute('id');
    clonedBackground.classList.add('giclee-faq-hero-curtain__background');
    clonedBackground.setAttribute('aria-hidden', 'true');
    curtain.appendChild(clonedBackground);

    copyFaqVisualSettings(faqSurface, curtain);

    var sectionBackground = faqSection.querySelector('.section-background');
    if (sectionBackground instanceof HTMLElement) {
      var sectionStyles = window.getComputedStyle(sectionBackground);
      if (sectionStyles.backgroundColor) {
        curtain.style.backgroundColor = sectionStyles.backgroundColor;
      }
    }

    heroSection.classList.add('giclee-faq-curtain-hero');
    heroContainer.appendChild(curtain);
    return curtain;
  }

  function injectStyles() {
    if (document.getElementById('giclee-faq-fq3-curtain-styles')) return;

    var style = document.createElement('style');
    style.id = 'giclee-faq-fq3-curtain-styles';
    style.textContent = [
      'body.giclee-faq-fq3-curtain-active #header-group { position: relative; z-index: 1000; }',
      '.giclee-faq-curtain-hero { position: relative; isolation: isolate; }',
      '.giclee-faq-curtain-hero .hero__container { overflow: hidden; }',
      '.giclee-faq-hero-curtain {',
      '  position: absolute !important;',
      '  inset: 0 !important;',
      '  z-index: 30 !important;',
      '  display: block !important;',
      '  min-height: 0 !important;',
      '  overflow: hidden !important;',
      '  pointer-events: none !important;',
      '  transform: scaleY(0.001);',
      '  transform-origin: 50% 100%;',
      '  will-change: transform;',
      '  backface-visibility: hidden;',
      '}',
      '.giclee-faq-hero-curtain__background {',
      '  position: absolute !important;',
      '  inset: 0 !important;',
      '  width: 100% !important;',
      '  height: 100% !important;',
      '  min-height: 100% !important;',
      '  overflow: hidden !important;',
      '  pointer-events: none !important;',
      '}',
      '.giclee-faq-hero-curtain .background-image-container,',
      '.giclee-faq-hero-curtain video-background-component {',
      '  position: absolute !important;',
      '  inset: 0 !important;',
      '  width: 100% !important;',
      '  height: 100% !important;',
      '  max-height: none !important;',
      '  transform: scale(calc(1 + var(--faq-bg-scale, 0) * 0.01)) !important;',
      '  transform-origin: center center !important;',
      '  filter: blur(calc(var(--faq-bg-blur, 0) * 1px)) saturate(calc(var(--faq-bg-saturate, 100) * 0.01)) brightness(calc(var(--faq-bg-brightness, 100) * 0.01)) !important;',
      '}',
      '.giclee-faq-hero-curtain img,',
      '.giclee-faq-hero-curtain picture,',
      '.giclee-faq-hero-curtain video {',
      '  display: block !important;',
      '  width: 100% !important;',
      '  height: 100% !important;',
      '  object-fit: cover !important;',
      '}',
      '.giclee-faq-hero-curtain::after {',
      '  content: "";',
      '  position: absolute;',
      '  top: 0;',
      '  left: 0;',
      '  right: 0;',
      '  height: clamp(24px, 4vw, 58px);',
      '  pointer-events: none;',
      '  background: linear-gradient(180deg, rgba(255,255,255,0.045) 0%, rgba(255,255,255,0.014) 25%, transparent 100%);',
      '  box-shadow: 0 -1px 0 rgba(255,255,255,0.07), 0 -16px 44px rgba(0,0,0,0.16);',
      '}',
      '@media (prefers-reduced-motion: reduce), (max-width: 749px) {',
      '  .giclee-faq-hero-curtain { display: none !important; }',
      '}',
    ].join('\n');

    document.head.appendChild(style);
  }

  /** @param {any} tween @param {any} ScrollTriggerPlugin */
  function initialize(tween, ScrollTriggerPlugin) {
    var heroSection = findHeroSection();
    var faqSection = findFaqSection();
    if (!heroSection || !faqSection) return;

    injectStyles();

    var curtain = buildCurtain(heroSection, faqSection);
    if (!curtain) return;

    tween.registerPlugin(ScrollTriggerPlugin);
    document.body.classList.add('giclee-faq-fq3-curtain-active');

    tween.set(curtain, {
      scaleY: 0.001,
      transformOrigin: '50% 100%',
      force3D: true,
    });

    tween.to(curtain, {
      scaleY: 1,
      ease: 'none',
      force3D: true,
      scrollTrigger: {
        id: 'giclee-faq-fq3-hero-curtain',
        trigger: heroSection,
        start: function () {
          return 'top top+=' + getHeaderHeight();
        },
        end: function () {
          var hero = heroSection.querySelector('.hero');
          var height = hero instanceof HTMLElement
            ? hero.getBoundingClientRect().height
            : window.innerHeight * 0.3;
          return '+=' + Math.max(480, Math.round(height * 1.65));
        },
        scrub: 0.75,
        pin: heroSection,
        pinSpacing: false,
        anticipatePin: 1,
        invalidateOnRefresh: true,
      },
    });

    window.addEventListener(
      'load',
      function () {
        ScrollTriggerPlugin.refresh();
      },
      { once: true }
    );
  }

  function run() {
    whenReady(initialize);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }
})();