// @ts-nocheck
/* Blog / Wersja 3 (sb3) — tło sekcji wpisów rozwija się od dołu i zakrywa hero. */
(function () {
  if (window.__GICLEE_BLOG_SB3_HERO_CURTAIN__) return;
  window.__GICLEE_BLOG_SB3_HERO_CURTAIN__ = true;

  var config = window.GICLEE_PAGE_SECTION_EFFECTS;
  if (!config || config.page !== 'blog' || config.variant !== 'sb3') return;

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var desktopPointer = window.matchMedia('(min-width: 750px) and (hover: hover) and (pointer: fine)').matches;
  if (reducedMotion || !desktopPointer) return;

  function getGsap() {
    return window.gsap || (typeof gsap !== 'undefined' ? gsap : undefined);
  }

  function getScrollTrigger() {
    return (
      window.ScrollTrigger ||
      (typeof ScrollTrigger !== 'undefined' ? ScrollTrigger : undefined)
    );
  }

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

      if (attempts >= 50) {
        window.clearInterval(timer);
      }
    }, 50);
  }

  function closestShopifySection(element) {
    if (!element || typeof element.closest !== 'function') return null;
    return element.closest('[id^="shopify-section-"]');
  }

  function findHeroSection() {
    var hero = document.querySelector('#MainContent .hero');
    return closestShopifySection(hero) || (hero ? hero.parentElement : null);
  }

  function findBlogSection() {
    var blog = document.querySelector('#MainContent [data-testid="blog-posts"], #MainContent .blog-posts');
    return closestShopifySection(blog) || (blog ? blog.parentElement : null);
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

  function copyComputedBackground(source, target) {
    if (!source || !target) return;

    var styles = window.getComputedStyle(source);
    target.style.backgroundColor = styles.backgroundColor;

    if (styles.backgroundImage && styles.backgroundImage !== 'none') {
      target.style.backgroundImage = styles.backgroundImage;
      target.style.backgroundPosition = styles.backgroundPosition;
      target.style.backgroundSize = styles.backgroundSize;
      target.style.backgroundRepeat = styles.backgroundRepeat;
      target.style.backgroundAttachment = styles.backgroundAttachment;
    }
  }

  function buildCurtain(heroSection, blogSection) {
    var hero = heroSection.querySelector('.hero');
    var heroContainer = heroSection.querySelector('.hero__container') || hero;
    if (!hero || !heroContainer) return null;

    var existing = heroContainer.querySelector('.giclee-blog-hero-curtain');
    if (existing) return existing;

    var curtain = document.createElement('div');
    curtain.className = 'giclee-blog-hero-curtain';
    curtain.setAttribute('aria-hidden', 'true');

    var sourceBackground = blogSection.querySelector('.section-background');
    var sourceSurface =
      blogSection.querySelector('[data-testid="blog-posts"], .blog-posts') ||
      sourceBackground ||
      blogSection;

    if (sourceBackground) {
      var clonedBackground = sourceBackground.cloneNode(true);
      clonedBackground.removeAttribute('id');
      clonedBackground.classList.add('giclee-blog-hero-curtain__background');
      clonedBackground.setAttribute('aria-hidden', 'true');
      curtain.appendChild(clonedBackground);
    }

    copyComputedBackground(sourceSurface, curtain);
    if (sourceBackground) copyComputedBackground(sourceBackground, curtain);

    heroSection.classList.add('giclee-blog-curtain-hero');
    heroContainer.appendChild(curtain);
    return curtain;
  }

  function injectStyles() {
    if (document.getElementById('giclee-blog-sb3-curtain-styles')) return;

    var style = document.createElement('style');
    style.id = 'giclee-blog-sb3-curtain-styles';
    style.textContent = [
      'body.giclee-blog-sb3-curtain-active #header-component { z-index: 1000; }',
      '.giclee-blog-curtain-hero { position: relative; z-index: 1; isolation: isolate; }',
      '.giclee-blog-curtain-hero .hero__container { overflow: hidden; }',
      '.giclee-blog-hero-curtain {',
      '  position: absolute;',
      '  inset: 0;',
      '  z-index: 20;',
      '  display: block;',
      '  overflow: hidden;',
      '  pointer-events: none;',
      '  transform: scaleY(0.001);',
      '  transform-origin: 50% 100%;',
      '  will-change: transform;',
      '  backface-visibility: hidden;',
      '}',
      '.giclee-blog-hero-curtain__background {',
      '  position: absolute !important;',
      '  inset: 0 !important;',
      '  width: 100% !important;',
      '  height: 100% !important;',
      '  min-height: 100% !important;',
      '  pointer-events: none !important;',
      '}',
      '.giclee-blog-hero-curtain::after {',
      '  content: "";',
      '  position: absolute;',
      '  top: 0;',
      '  left: 0;',
      '  right: 0;',
      '  height: clamp(28px, 5vw, 64px);',
      '  pointer-events: none;',
      '  background: linear-gradient(180deg, rgba(255,255,255,0.055) 0%, rgba(255,255,255,0.018) 22%, transparent 100%);',
      '  box-shadow: 0 -1px 0 rgba(255,255,255,0.08), 0 -14px 42px rgba(0,0,0,0.14);',
      '}',
      '@media (prefers-reduced-motion: reduce), (max-width: 749px) {',
      '  .giclee-blog-hero-curtain { display: none !important; }',
      '}'
    ].join('\n');

    document.head.appendChild(style);
  }

  function initialize(tween, ScrollTriggerPlugin) {
    var heroSection = findHeroSection();
    var blogSection = findBlogSection();
    if (!heroSection || !blogSection) return;

    injectStyles();

    var curtain = buildCurtain(heroSection, blogSection);
    if (!curtain) return;

    tween.registerPlugin(ScrollTriggerPlugin);
    document.body.classList.add('giclee-blog-sb3-curtain-active');

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
        id: 'giclee-blog-sb3-hero-curtain',
        trigger: heroSection,
        start: function () {
          return 'top top+=' + getHeaderHeight();
        },
        end: function () {
          var hero = heroSection.querySelector('.hero');
          var height = hero ? hero.getBoundingClientRect().height : window.innerHeight * 0.6;
          return '+=' + Math.max(460, Math.round(height * 0.95));
        },
        scrub: 0.75,
        pin: heroSection,
        pinSpacing: true,
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
