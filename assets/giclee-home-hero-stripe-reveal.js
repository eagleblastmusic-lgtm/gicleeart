/* Hero-rise: 3-stripe mask (bottom→top) + shared lerp for the whole Hero frame. */

(function () {

  'use strict';



  var SCRUB_ROOT_ID = 'giclee-prehero-video-scrub';

  var MASK_CLASS = 'is-hero-stripe-masked';

  var LAG_CLASS = 'is-hero-rise-lagging';

  var OFFSETS = [0, 0.13, 0.26];

  var LAG = [0.085, 0.065, 0.048];

  /* Shared inertia for the whole sticky Hero (cinema bars + video together). */

  var SECTION_LAG = 0.07;



  var hero = null;

  var scrubRoot = null;

  var collage = null;

  var currentH = [0, 0, 0];

  var targetH = [0, 0, 0];

  var smoothedProgress = 0;

  var currentLagY = 0;

  var rafId = 0;

  var progress = 0;

  var complete = false;

  var reducedMotion = false;

  var masking = false;

  var observer = null;



  function clamp(value, min, max) {

    return Math.min(max, Math.max(min, value));

  }



  function easeOutCubic(t) {

    var x = clamp(t, 0, 1);

    return 1 - Math.pow(1 - x, 3);

  }



  function findHero() {

    var map = window.GICLEE_HOME_SECTIONS || {};

    var heroId = map.hero || 'slideshow_4LMfx7';

    return (

      document.getElementById('shopify-section-' + heroId) ||

      document.querySelector('[id$="__' + heroId + '"]') ||

      document.querySelector('.shopify-section.giclee-prehero-hero-rise')

    );

  }



  function findCollage(section) {

    if (!section) return null;

    return (

      section.querySelector('[data-giclee-video-collage]') ||

      section.querySelector('.giclee-video-collage')

    );

  }



  function readProgress() {

    if (!scrubRoot) return 0;

    var value = Number(scrubRoot.getAttribute('data-hero-rise-progress'));

    return Number.isFinite(value) ? clamp(value, 0, 1) : 0;

  }



  function setMasking(active) {

    if (!collage) return;

    masking = !!active;

    collage.classList.toggle(MASK_CLASS, masking);

    if (!masking) {

      collage.style.removeProperty('--giclee-hero-stripe-h0');

      collage.style.removeProperty('--giclee-hero-stripe-h1');

      collage.style.removeProperty('--giclee-hero-stripe-h2');

    }

  }



  function applyHeights() {

    if (!collage || !masking) return;

    collage.style.setProperty('--giclee-hero-stripe-h0', currentH[0].toFixed(3) + '%');

    collage.style.setProperty('--giclee-hero-stripe-h1', currentH[1].toFixed(3) + '%');

    collage.style.setProperty('--giclee-hero-stripe-h2', currentH[2].toFixed(3) + '%');

  }



  function applySectionLag(lagY) {

    currentLagY = lagY;

    if (!hero) return;

    if (Math.abs(lagY) < 0.05) {

      hero.style.removeProperty('--giclee-hero-rise-lag-y');

      hero.classList.remove(LAG_CLASS);

      return;

    }

    /* Sticky `top` moves the whole section (bars + video) as one unit. */

    hero.style.setProperty('--giclee-hero-rise-lag-y', lagY.toFixed(2) + 'px');

    hero.classList.add(LAG_CLASS);

  }



  function clearSectionLag() {

    smoothedProgress = progress;

    applySectionLag(0);

  }



  function updateTargetsFromWipe(wipe) {

    if (complete) {

      targetH[0] = 100;

      targetH[1] = 100;

      targetH[2] = 100;

      return;

    }



    if (wipe <= 0) {

      targetH[0] = 0;

      targetH[1] = 0;

      targetH[2] = 0;

      return;

    }



    var span = 1 - OFFSETS[2];

    for (var i = 0; i < 3; i += 1) {

      var local = clamp((wipe - OFFSETS[i]) / span, 0, 1);

      targetH[i] = easeOutCubic(local) * 100;

    }

  }



  function tickSharedMotion() {

    progress = readProgress();

    complete = scrubRoot

      ? scrubRoot.getAttribute('data-hero-rise-complete') === 'true' || progress >= 0.999

      : false;



    smoothedProgress += (progress - smoothedProgress) * SECTION_LAG;

    if (Math.abs(progress - smoothedProgress) < 0.0005) {

      smoothedProgress = progress;

    }



    /*

     * Stripes and cinema frame share smoothedProgress so one layer cannot

     * race ahead of the other. Per-stripe LAG only softens band edges.

     */

    updateTargetsFromWipe(complete ? 1 : smoothedProgress);



    var viewport = window.innerHeight || 1;

    var lagY = (progress - smoothedProgress) * viewport;

    applySectionLag(lagY);



    return Math.abs(progress - smoothedProgress) > 0.0005 || Math.abs(lagY) > 0.05;

  }



  function tick() {

    rafId = 0;

    if (!hero || !scrubRoot || !collage || reducedMotion) return;



    var sectionMoving = tickSharedMotion();

    var shouldMask = progress > 0.0005 && !complete;

    if (shouldMask && !masking) setMasking(true);

    if (!shouldMask && !masking && !complete) {

      if (

        hero.classList.contains('giclee-prehero-hero-rise') &&

        scrubRoot.getAttribute('data-hero-rise-active') === 'true'

      ) {

        setMasking(true);

        currentH = [0, 0, 0];

        targetH = [0, 0, 0];

        applyHeights();

      }

      rafId = window.requestAnimationFrame(tick);

      return;

    }



    var stillMoving = sectionMoving;

    if (masking || shouldMask || (complete && currentH.some(function (h) { return h < 99.5; }))) {

      if (!masking) setMasking(true);

      for (var i = 0; i < 3; i += 1) {

        var k = LAG[i];

        currentH[i] += (targetH[i] - currentH[i]) * k;

        if (Math.abs(targetH[i] - currentH[i]) > 0.08) stillMoving = true;

        else currentH[i] = targetH[i];

      }

      applyHeights();



      var fullyOpen =

        currentH[0] >= 99.5 && currentH[1] >= 99.5 && currentH[2] >= 99.5;

      if ((complete || fullyOpen) && !stillMoving) {

        setMasking(false);

        currentH = [100, 100, 100];

        clearSectionLag();

        return;

      }

      if (complete && !sectionMoving && currentH.every(function (h) { return h >= 99.5; })) {

        currentH = [100, 100, 100];

        applyHeights();

        setMasking(false);

        clearSectionLag();

        return;

      }

    } else if (complete && !sectionMoving) {

      clearSectionLag();

      return;

    }



    rafId = window.requestAnimationFrame(tick);

  }



  function requestTick() {

    if (!rafId) rafId = window.requestAnimationFrame(tick);

  }



  function boot() {

    reducedMotion = !!(

      window.matchMedia &&

      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    );

    if (reducedMotion) return;



    scrubRoot = document.getElementById(SCRUB_ROOT_ID);

    hero = findHero();

    collage = findCollage(hero);

    if (!scrubRoot || !hero || !collage) return;



    if (window.MutationObserver) {

      observer = new MutationObserver(requestTick);

      observer.observe(scrubRoot, {

        attributes: true,

        attributeFilter: [

          'data-hero-rise-progress',

          'data-hero-rise-complete',

          'data-hero-rise-active',

        ],

      });

    }



    window.addEventListener('scroll', requestTick, { passive: true });

    window.addEventListener('resize', requestTick, { passive: true });

    window.addEventListener('pageshow', requestTick, { passive: true });

    requestTick();



    window.GICLEE_HERO_STRIPE_REVEAL_STATUS = function () {

      return {

        ready: true,

        progress: progress,

        smoothedProgress: smoothedProgress,

        complete: complete,

        masking: masking,

        currentH: currentH.slice(),

        targetH: targetH.slice(),

        sectionLagY: currentLagY,

        sectionLag: SECTION_LAG,

      };

    };

  }



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', boot, { once: true });

  } else {

    boot();

  }

})();

