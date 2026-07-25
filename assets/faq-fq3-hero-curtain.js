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
    var candidates = [headerGroup, header];

    for (var index = 0; index < candidates.length; index += 1) {
      var element = candidates[index];
      if (!element) continue;

      var rect = element.getBoundingClientRect();
      if (rect.height > 0) return Math.round(rect.height);
    }

    var cssValue = window
      .getComputedStyle(document.documentElement)
      .getPropertyValue('--header-group-height');
    var parsed = parseFloat(cssValue);
    return isFinite(parsed) ? Math.max(0, Math.round(parsed)) : 0;
  }

  /** @param {HTMLElement} heroSection */
  function getCurtainScrollDistance(heroSection) {
    var hero = heroSection.querySelector('.hero');
    var heroHeight = hero instanceof HTMLElement
      ? hero.getBoundingClientRect().height
      : window.innerHeight * 0.3;
    var desiredDistance = Math.max(360, Math.round(heroHeight * 2.2));
    var startScroll =
      heroSection.getBoundingClientRect().top +
      window.scrollY -
      getHeaderHeight();
    var footer = document.querySelector('body > footer') || document.querySelector('footer');
    var documentEnd = Math.max(
      0,
      document.documentElement.scrollHeight - window.innerHeight
    );
    var footerEntry = footer instanceof HTMLElement
      ? footer.getBoundingClientRect().top + window.scrollY - window.innerHeight
      : documentEnd;
    var availableDistance = Math.min(documentEnd, footerEntry) - startScroll;

    return Math.max(1, Math.min(desiredDistance, Math.round(availableDistance)));
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

  /** @param {HTMLElement} faqSection @returns {HTMLElement | null} */
  function buildCurtain(faqSection) {
    var faqSurface = faqSection.querySelector('.faq-section');
    var sourceBackground = faqSection.querySelector('.custom-section-background');

    if (!(faqSurface instanceof HTMLElement)) return null;
    if (!(sourceBackground instanceof HTMLElement)) return null;

    var existing = document.querySelector('.giclee-faq-hero-curtain');
    if (existing instanceof HTMLElement) return existing;

    var curtain = document.createElement('div');
    curtain.className = 'giclee-faq-hero-curtain faq-section faq-section--bg-image';
    curtain.setAttribute('aria-hidden', 'true');

    var clonedBackground = /** @type {HTMLElement} */ (sourceBackground.cloneNode(true));
    clonedBackground.removeAttribute('id');
    clonedBackground.classList.add('giclee-faq-hero-curtain__background');
    clonedBackground.setAttribute('aria-hidden', 'true');
    curtain.appendChild(clonedBackground);

    faqSurface
      .querySelectorAll('.faq-artwork-decoration, .faq-disc')
      .forEach(function (node) {
        var clone = /** @type {HTMLElement} */ (node.cloneNode(true));
        clone.removeAttribute('id');
        clone.setAttribute('aria-hidden', 'true');
        curtain.appendChild(clone);
      });

    copyFaqVisualSettings(faqSurface, curtain);

    var sectionBackground = faqSection.querySelector('.section-background');
    if (sectionBackground instanceof HTMLElement) {
      var sectionStyles = window.getComputedStyle(sectionBackground);
      if (sectionStyles.backgroundColor) {
        curtain.style.backgroundColor = sectionStyles.backgroundColor;
      }
    }

    document.body.appendChild(curtain);
    return curtain;
  }

  function injectStyles() {
    if (document.getElementById('giclee-faq-fq3-curtain-styles')) return;

    var style = document.createElement('style');
    style.id = 'giclee-faq-fq3-curtain-styles';
    style.textContent = [
      'body.giclee-faq-fq3-curtain-active #header-group { position: relative; z-index: 1000; }',
      'body.giclee-faq-fq3-curtain-active #MainContent .giclee-faq-curtain-content-layer {',
      '  position: relative !important;',
      '  z-index: 901 !important;',
      '}',
      '.giclee-faq-hero-curtain {',
      '  position: fixed !important;',
      '  top: var(--giclee-faq-curtain-top, 0px) !important;',
      '  right: 0 !important;',
      '  bottom: 0 !important;',
      '  left: 0 !important;',
      '  z-index: 900 !important;',
      '  display: block !important;',
      '  min-height: 0 !important;',
      '  overflow: hidden !important;',
      '  pointer-events: none !important;',
      '  opacity: 1;',
      '  transform: scaleY(0.001);',
      '  transform-origin: 50% 100%;',
      '  will-change: transform, opacity;',
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

  /** @param {HTMLElement} curtain */
  function syncCurtainGeometry(curtain) {
    curtain.style.setProperty('--giclee-faq-curtain-top', getHeaderHeight() + 'px');
  }

  /** @param {any} tween @param {any} ScrollTriggerPlugin */
  function initialize(tween, ScrollTriggerPlugin) {
    var heroSection = findHeroSection();
    var faqSection = findFaqSection();
    if (!heroSection || !faqSection) return;

    injectStyles();
    faqSection.classList.add('giclee-faq-curtain-content-layer');

    var curtain = buildCurtain(faqSection);
    if (!curtain) return;

    syncCurtainGeometry(curtain);
    tween.registerPlugin(ScrollTriggerPlugin);
    document.body.classList.add('giclee-faq-fq3-curtain-active');

    tween.set(curtain, {
      scaleY: 0.001,
      opacity: 1,
      transformOrigin: '50% 100%',
      force3D: true,
    });

    var timeline = tween.timeline({
      scrollTrigger: {
        id: 'giclee-faq-fq3-hero-curtain',
        trigger: heroSection,
        start: function () {
          return 'top top+=' + getHeaderHeight();
        },
        end: function () {
          return '+=' + getCurtainScrollDistance(heroSection);
        },
        scrub: 0.65,
        invalidateOnRefresh: true,
        onLeave: function () {
          tween.set(curtain, { opacity: 0 });
        },
        onLeaveBack: function () {
          tween.set(curtain, { scaleY: 0.001, opacity: 1 });
        },
        onRefresh: function () {
          syncCurtainGeometry(curtain);
        },
      },
    });

    timeline
      .to(curtain, {
        scaleY: 1,
        opacity: 1,
        ease: 'none',
        force3D: true,
        duration: 0.88,
      })
      .to(curtain, {
        opacity: 0,
        ease: 'none',
        duration: 0.12,
      });

    window.addEventListener('resize', function () {
      syncCurtainGeometry(curtain);
    });

    window.addEventListener(
      'load',
      function () {
        syncCurtainGeometry(curtain);
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
