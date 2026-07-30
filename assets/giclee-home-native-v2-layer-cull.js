/* Native v2 stack layer culling: keep only transition-relevant sticky layers active. */
(function () {
  'use strict';

  var root = document.documentElement;
  var config = window.GICLEE_PREHERO_CONFIG || {};
  var mode = String(config.smoothScrollMode || 'native').trim().toLowerCase();
  var STACK_HOOKS = [
    'hero',
    'intro',
    'restoration',
    'color-correction',
    'potential',
    'see-difference',
  ];
  var STACK_PIN_TOP = 16;

  var enabled = false;
  var ready = false;
  var frameId = 0;
  var measureFrameId = 0;
  var resizeObserver = null;
  var sections = [];
  var pairStarts = [];
  var activePair = -1;
  var frontIndex = 0;
  var hiddenCount = 0;
  var updateCount = 0;
  var measureCount = 0;
  var pauseCount = 0;
  var resumeCount = 0;
  var lastSignature = '';

  if (mode !== 'native-v2') return;

  function reducedMotionRequested() {
    return !!(
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function designModeActive() {
    return !!(window.Shopify && window.Shopify.designMode);
  }

  function touchLikeDevice() {
    return !!(
      window.matchMedia &&
      window.matchMedia('(hover: none) and (pointer: coarse)').matches
    );
  }

  function queryDisablesProfile() {
    try {
      return new URLSearchParams(window.location.search).get('giclee_native_scroll') === '1';
    } catch (error) {
      return false;
    }
  }

  function shouldDisable() {
    return (
      queryDisablesProfile() ||
      reducedMotionRequested() ||
      designModeActive() ||
      touchLikeDevice()
    );
  }

  function currentScrollY() {
    return (
      window.scrollY ||
      window.pageYOffset ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0
    );
  }

  function viewportHeight() {
    return window.innerHeight || document.documentElement.clientHeight || 800;
  }

  function documentTop(element) {
    var top = 0;
    var node = element;
    while (node) {
      top += Number(node.offsetTop) || 0;
      node = node.offsetParent;
    }
    return top;
  }

  function findSection(sectionKey) {
    if (!sectionKey) return null;
    return (
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]')
    );
  }

  function pauseBackgroundMedia(section) {
    if (!section) return;
    section.querySelectorAll('video').forEach(function (video) {
      if (video.paused || (!video.autoplay && !video.muted)) return;
      video.dataset.gicleeNativeV2CullResume = '1';
      try {
        video.pause();
        pauseCount += 1;
      } catch (error) {
        delete video.dataset.gicleeNativeV2CullResume;
      }
    });
  }

  function resumeBackgroundMedia(section) {
    if (!section) return;
    section.querySelectorAll('video[data-giclee-native-v2-cull-resume="1"]').forEach(function (video) {
      delete video.dataset.gicleeNativeV2CullResume;
      try {
        var result = video.play();
        if (result && typeof result.catch === 'function') result.catch(function () {});
        resumeCount += 1;
      } catch (error) {
        /* Browser autoplay policy remains authoritative. */
      }
    });
  }

  function setCovered(section, covered) {
    if (!section || section._gicleeNativeV2Covered === covered) return;
    section._gicleeNativeV2Covered = covered;
    section.classList.toggle('giclee-native-v2-covered', covered);
    section.setAttribute('data-giclee-native-v2-layer-state', covered ? 'covered' : 'visible');
    if (covered) pauseBackgroundMedia(section);
    else resumeBackgroundMedia(section);
  }

  function clearCulling() {
    sections.forEach(function (section) {
      setCovered(section, false);
      section.removeAttribute('data-giclee-native-v2-layer-state');
      delete section._gicleeNativeV2Covered;
    });
    hiddenCount = 0;
    activePair = -1;
    frontIndex = 0;
    lastSignature = '';
  }

  function resolveLayerState(scrollY) {
    var vh = viewportHeight();
    var resolvedActivePair = -1;
    var resolvedFrontIndex = 0;

    for (var i = 0; i < pairStarts.length; i += 1) {
      var transitionStart = pairStarts[i] - vh;
      var transitionEnd = pairStarts[i] - STACK_PIN_TOP;

      if (scrollY >= transitionEnd) {
        resolvedFrontIndex = i + 1;
        continue;
      }

      if (scrollY >= transitionStart) {
        resolvedActivePair = i;
        resolvedFrontIndex = i;
      }
      break;
    }

    return {
      activePair: resolvedActivePair,
      frontIndex: resolvedFrontIndex,
      cullBefore: resolvedActivePair >= 0 ? resolvedActivePair : resolvedFrontIndex,
    };
  }

  function applyCulling() {
    frameId = 0;
    if (!enabled || !ready || !sections.length || document.hidden) return;

    var state = resolveLayerState(currentScrollY());
    var signature = state.activePair + '|' + state.frontIndex + '|' + state.cullBefore;
    activePair = state.activePair;
    frontIndex = state.frontIndex;

    if (signature === lastSignature) return;
    lastSignature = signature;
    updateCount += 1;
    hiddenCount = 0;

    sections.forEach(function (section, index) {
      var covered = index < state.cullBefore;
      setCovered(section, covered);
      if (covered) hiddenCount += 1;
    });

    root.setAttribute('data-giclee-native-v2-front-layer', String(frontIndex + 1));
    root.setAttribute(
      'data-giclee-native-v2-active-pair',
      activePair >= 0 ? String(activePair) : 'none'
    );
  }

  function scheduleApply() {
    if (!frameId) frameId = window.requestAnimationFrame(applyCulling);
  }

  function measure() {
    measureFrameId = 0;
    if (!enabled) return;

    var map = window.GICLEE_HOME_SECTIONS;
    if (!map || typeof map !== 'object') return;

    var nextSections = [];
    STACK_HOOKS.forEach(function (hook) {
      var section = findSection(map[hook]);
      if (section) nextSections.push(section);
    });

    if (nextSections.length < 2) return;

    sections = nextSections;
    pairStarts = [];
    for (var i = 0; i < sections.length - 1; i += 1) {
      pairStarts.push(documentTop(sections[i + 1]));
    }
    measureCount += 1;
    ready = true;
    root.classList.add('giclee-native-v2-layer-cull');
    lastSignature = '';
    scheduleApply();
  }

  function scheduleMeasure() {
    if (!measureFrameId) measureFrameId = window.requestAnimationFrame(measure);
  }

  function boot() {
    if (shouldDisable()) return;
    enabled = true;

    window.addEventListener('scroll', scheduleApply, { passive: true });
    window.addEventListener('resize', scheduleMeasure, { passive: true });
    window.addEventListener('orientationchange', scheduleMeasure, { passive: true });
    window.addEventListener('pageshow', scheduleMeasure, { passive: true });
    window.addEventListener('load', scheduleMeasure, { once: true });
    window.addEventListener('giclee:home-stack-ready', scheduleMeasure, { passive: true });
    document.addEventListener('shopify:section:load', scheduleMeasure);
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) scheduleApply();
    });

    var main = document.getElementById('MainContent');
    if (main && typeof ResizeObserver === 'function') {
      resizeObserver = new ResizeObserver(scheduleMeasure);
      resizeObserver.observe(main);
    }

    window.GICLEE_NATIVE_V2_LAYER_CULL_STATUS = function () {
      return {
        ready: ready,
        enabled: enabled,
        activePair: activePair,
        frontLayer: frontIndex + 1,
        sectionCount: sections.length,
        pairCount: pairStarts.length,
        hiddenLayerCount: hiddenCount,
        hiddenLayerIndexes: sections
          .map(function (section, index) {
            return section.classList.contains('giclee-native-v2-covered') ? index + 1 : null;
          })
          .filter(function (index) { return index !== null; }),
        updateCount: updateCount,
        measureCount: measureCount,
        pausedVideoCount: pauseCount,
        resumedVideoCount: resumeCount,
        geometryPreserved: true,
        normalFlowGeometryPreserved: true,
        coveredStickyReleased: true,
        paintOnlyCulling: false,
      };
    };

    scheduleMeasure();
    window.setTimeout(scheduleMeasure, 120);
    window.setTimeout(scheduleMeasure, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
