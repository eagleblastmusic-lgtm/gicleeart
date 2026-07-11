/* Synchronize the Giclée Art studio reveal with the first frame of the Hero curtain. */
(function () {
  'use strict';

  var ROOT = document.documentElement;
  var INTRO_CLASS = 'giclee-hero-horizontal-curtain-intro-target';
  var EFFECTS_CLASS = 'giclee-home-studio-reveal';
  var REVEALED_CLASS = 'is-revealed';
  var MAX_RETRIES = 180;

  var intro = null;
  var introInner = null;
  var rootObserver = null;
  var innerObserver = null;
  var rafId = 0;
  var retries = 0;
  var effectsStarted = false;

  function flag(name) {
    return ROOT.getAttribute(name) === 'true';
  }

  function openingStarted() {
    return (
      flag('data-giclee-hero-horizontal-curtain-opening') ||
      flag('data-giclee-hero-horizontal-curtain-complete')
    );
  }

  function isCoveredHold() {
    return (
      flag('data-giclee-hero-horizontal-curtain-active') &&
      !flag('data-giclee-hero-horizontal-curtain-opening') &&
      !flag('data-giclee-hero-horizontal-curtain-complete') &&
      !flag('data-giclee-hero-horizontal-curtain-handoff-complete')
    );
  }

  function findIntro() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    var introId = map.intro || 'section_ThWw4Q';
    intro =
      document.getElementById('shopify-section-' + introId) ||
      document.querySelector('.shopify-section[id*="' + introId + '"]') ||
      document.querySelector('.shopify-section.' + INTRO_CLASS);

    introInner = intro ? intro.querySelector('.section.' + EFFECTS_CLASS) : null;
    return !!introInner;
  }

  function dispatchStarted() {
    try {
      window.dispatchEvent(
        new CustomEvent('giclee:intro-curtain-effects-start', {
          detail: { intro: intro, sectionInner: introInner },
        })
      );
    } catch (error) {}
  }

  function startEffects() {
    if (effectsStarted || !findIntro()) return false;

    effectsStarted = true;
    introInner.classList.add(REVEALED_CLASS);
    intro.setAttribute('data-giclee-curtain-effects-active', 'true');
    ROOT.setAttribute('data-giclee-hero-intro-effects-active', 'true');
    dispatchStarted();
    return true;
  }

  function keepCoveredState() {
    if (effectsStarted || !findIntro()) return;

    if (introInner.classList.contains(REVEALED_CLASS)) {
      introInner.classList.remove(REVEALED_CLASS);
    }
    intro.removeAttribute('data-giclee-curtain-effects-active');
    ROOT.setAttribute('data-giclee-hero-intro-effects-active', 'false');
  }

  function bindInnerObserver() {
    if (!introInner || !window.MutationObserver) return;
    if (innerObserver) innerObserver.disconnect();

    innerObserver = new MutationObserver(function () {
      if (effectsStarted) {
        if (!introInner.classList.contains(REVEALED_CLASS)) {
          introInner.classList.add(REVEALED_CLASS);
        }
      } else if (isCoveredHold() && introInner.classList.contains(REVEALED_CLASS)) {
        introInner.classList.remove(REVEALED_CLASS);
      }
    });
    innerObserver.observe(introInner, { attributes: true, attributeFilter: ['class'] });
  }

  function sync() {
    rafId = 0;

    var previousInner = introInner;
    var found = findIntro();
    if (found && introInner !== previousInner) bindInnerObserver();

    if (openingStarted()) {
      if (!startEffects() && !found && retries < MAX_RETRIES) scheduleSync();
      return;
    }

    if (isCoveredHold()) {
      keepCoveredState();
    }

    if (!found && retries < MAX_RETRIES) scheduleSync();
  }

  function scheduleSync() {
    retries += 1;
    if (!rafId) rafId = window.requestAnimationFrame(sync);
  }

  function boot() {
    retries = 0;
    sync();

    if (window.MutationObserver) {
      rootObserver = new MutationObserver(scheduleSync);
      rootObserver.observe(ROOT, {
        attributes: true,
        attributeFilter: [
          'data-giclee-hero-horizontal-curtain-active',
          'data-giclee-hero-horizontal-curtain-opening',
          'data-giclee-hero-horizontal-curtain-complete',
          'data-giclee-hero-horizontal-curtain-handoff-complete',
        ],
      });
    }

    window.addEventListener('giclee:home-stack-ready', scheduleSync, { passive: true });
    window.addEventListener('pageshow', scheduleSync, { passive: true });

    window.GICLEE_HOME_INTRO_CURTAIN_EFFECTS_STATUS = function () {
      findIntro();
      return {
        ready: !!introInner,
        effectsStarted: effectsStarted,
        opening: flag('data-giclee-hero-horizontal-curtain-opening'),
        curtainComplete: flag('data-giclee-hero-horizontal-curtain-complete'),
        introHoldActive: flag('data-giclee-hero-intro-hold-active'),
        handoffComplete: flag('data-giclee-hero-horizontal-curtain-handoff-complete'),
        introEffectsActive:
          ROOT.getAttribute('data-giclee-hero-intro-effects-active') === 'true',
        studioRevealClass: !!(
          introInner && introInner.classList.contains(EFFECTS_CLASS)
        ),
        revealedClass: !!(
          introInner && introInner.classList.contains(REVEALED_CLASS)
        ),
      };
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
