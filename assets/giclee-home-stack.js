(function () {
  var STACK_HOOKS = [
    'hero',
    'intro',
    'restoration',
    'color-correction',
    'potential',
    'see-difference',
  ];

  var PREV_PIN_EPS = 16;
  var SCROLL_REST_EPS = 4;
  var SECTION_LERP_RISE = 0.042;
  var SECTION_LERP_RISE_MOBILE = 0.065;
  var SECTION_LERP_DECAY = 0.12;
  var SECTION_LERP_EPS = 0.002;
  var DIVIDER_LERP = 0.12;
  var DIVIDER_LERP_EPS = 0.002;
  var DIVIDER_APPROACH_MAX = 0.45;
  var PAIR_APPROACH_MAX = 0.25;
  var SLIP_VH_DESKTOP = 0.12;
  var SLIP_VH_MOBILE = 0.08;
  var SLIP_MIN_DESKTOP = 60;
  var SLIP_MAX_DESKTOP = 90;
  var SLIP_MIN_MOBILE = 40;
  var SLIP_MAX_MOBILE = 48;
  var SLIP_CLEAR_EPS = 2;
  var HERO_VIEWPORT_TOP_EPS = 16;

  var stackEls = [];
  var scrollDividerEls = [];
  var pairTargetPrevDim = [];
  var pairCurrentPrevDim = [];
  var pairTargetNextOver = [];
  var pairCurrentNextOver = [];
  var pairTargetOverlap = [];
  var pairCurrentOverlap = [];
  var motionFrameId = 0;
  var scrollActiveTimer = 0;

  function getOverlapBottomFromRect(prev, prevRect) {
    return prevRect.top + prev.offsetHeight;
  }

  function isNextOverlappingPrevFromRect(prev, prevRect, incomingTop) {
    return incomingTop <= getOverlapBottomFromRect(prev, prevRect) + PREV_PIN_EPS;
  }

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function isTouchLikeDevice() {
    return (
      window.matchMedia &&
      window.matchMedia('(hover: none) and (pointer: coarse)').matches
    );
  }

  function findSection(sectionKey) {
    if (!sectionKey) return null;
    return (
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]')
    );
  }

  function isDividerSection(el) {
    if (!el || !el.classList.contains('shopify-section')) return false;
    return !!el.querySelector('[data-testid^="divider-"]');
  }

  function resetScrollDividerLine(line) {
    if (!line) return;
    line.style.flexBasis = '';
    line.style.animation = 'none';
    line.style.removeProperty('--home-stack-divider-scale');
    line._dividerScaleApplied = null;
  }

  function clearGlobalDividerLineOverrides(line) {
    if (!line) return;
    line.style.flexBasis = '';
    line.style.animation = 'none';
  }

  function initDividerLineState(dividerEl) {
    var line = dividerEl.querySelector('.divider__line');
    if (!line) return null;
    if (dividerEl.classList.contains('giclee-home-stack-divider--scroll')) {
      clearGlobalDividerLineOverrides(line);
    }
    dividerEl._dividerLine = line;
    if (typeof dividerEl._dividerCurrentScale !== 'number') {
      dividerEl._dividerCurrentScale = 0;
    }
    if (typeof dividerEl._dividerTargetScale !== 'number') {
      dividerEl._dividerTargetScale = 0;
    }
    return line;
  }

  function applyDividerLineScale(dividerEl, scale) {
    var line = dividerEl._dividerLine || dividerEl.querySelector('.divider__line');
    if (!line) return;
    var rounded = Math.round(scale * 1000) / 1000;
    var key = rounded.toFixed(3);
    if (line._dividerScaleApplied === key) return;
    line._dividerScaleApplied = key;
    line.style.setProperty('--home-stack-divider-scale', String(rounded));
  }

  function initPairZeroScrollDivider(dividerEl) {
    if (dividerEl._dividerPairIndex !== 0) return;
    clearGlobalDividerLineOverrides(dividerEl._dividerLine || dividerEl.querySelector('.divider__line'));
    dividerEl._dividerCurrentRaw = 1;
    dividerEl._dividerTargetRaw = 1;
    dividerEl._dividerCurrentScale = 1;
    applyDividerLineScale(dividerEl, 1);
  }

  function collectScrollDividers() {
    scrollDividerEls = Array.prototype.slice.call(
      document.querySelectorAll('.giclee-home-stack-divider--scroll')
    );
  }

  function getBetweenElements(prev, next) {
    var nodes = [];
    var el = prev.nextElementSibling;
    while (el && el !== next) {
      nodes.push(el);
      el = el.nextElementSibling;
    }
    return nodes;
  }

  function getIncomingLeadEl(prev, next) {
    var between = getBetweenElements(prev, next);
    if (between.length > 0) return between[0];
    return next;
  }

  function resetPairProgressState(sections) {
    var pairCount = Math.max(sections.length - 1, 0);
    pairTargetPrevDim = [];
    pairCurrentPrevDim = [];
    pairTargetNextOver = [];
    pairCurrentNextOver = [];
    pairTargetOverlap = [];
    pairCurrentOverlap = [];
    for (var i = 0; i < pairCount; i += 1) {
      pairTargetPrevDim[i] = 0;
      pairCurrentPrevDim[i] = 0;
      pairTargetNextOver[i] = 0;
      pairCurrentNextOver[i] = 0;
      pairTargetOverlap[i] = 0;
      pairCurrentOverlap[i] = 0;
    }
  }

  function scheduleMotionTick() {
    if (motionFrameId) return;
    motionFrameId = requestAnimationFrame(tickMotion);
  }

  function markScrolling() {
    document.documentElement.classList.add('giclee-home-stack-scrolling');
    clearTimeout(scrollActiveTimer);
    scrollActiveTimer = setTimeout(function () {
      document.documentElement.classList.remove('giclee-home-stack-scrolling');
    }, 150);
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function smoothstep(t) {
    t = clamp(t, 0, 1);
    return t * t * (3 - 2 * t);
  }

  function easeInOutCubic(t) {
    t = clamp(t, 0, 1);
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  function getSectionLerpRise() {
    if (window.matchMedia && window.matchMedia('(max-width: 749px)').matches) {
      return SECTION_LERP_RISE_MOBILE;
    }
    return SECTION_LERP_RISE;
  }

  function getScrollY() {
    return (
      window.scrollY ||
      window.pageYOffset ||
      document.documentElement.scrollTop ||
      document.body.scrollTop ||
      0
    );
  }

  function isPrevPinnedAtTopFromRect(prev, pairIndex, prevRect) {
    if (!prev) return false;
    if (pairIndex === 0 && getScrollY() <= 0) return false;
    return prevRect.top <= PREV_PIN_EPS;
  }

  function getBoardTransitionProgress(boardTop) {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    if (boardTop >= vh) {
      return { progress: 0, phase: 'none' };
    }
    if (getScrollY() <= SCROLL_REST_EPS) {
      return { progress: 0, phase: 'rest' };
    }
    if (boardTop <= PREV_PIN_EPS) {
      return { progress: 1, phase: 'dock' };
    }
    var t = (vh - boardTop) / Math.max(vh - PREV_PIN_EPS, 1);
    var progress = smoothstep(clamp(t, 0, 1));
    return {
      progress: progress,
      phase: boardTop > vh * 0.55 ? 'approach' : 'overlap',
    };
  }

  function getPairOverlapProgress(prev, pairIndex, prevRect, incomingTop, boardTop) {
    return getBoardTransitionProgress(boardTop);
  }

  function getPairTargetsFromMetrics(prev, pairIndex, prevRect, incomingTop, boardTop) {
    var result = getPairOverlapProgress(prev, pairIndex, prevRect, incomingTop, boardTop);
    return {
      prevDim: result.progress,
      nextOver: result.progress,
      overlap: result.progress,
      phase: result.phase,
    };
  }

  function getDividerApproachProgress(prev, prevRect, boardTop) {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    if (boardTop >= vh) return 0;
    var overlapBottom = getOverlapBottomFromRect(prev, prevRect);
    var end = Math.max(Math.min(overlapBottom, vh - 1), PREV_PIN_EPS);
    var span = Math.max(vh - end, 1);
    var t = (vh - boardTop) / span;
    return smoothstep(clamp(t, 0, 1)) * DIVIDER_APPROACH_MAX;
  }

  function getDividerTargetProgress(pairIndex) {
    if (pairIndex === 0) return 1;
    if (pairIndex < 0) return 0;
    var prev = stackEls[pairIndex];
    var next = stackEls[pairIndex + 1];
    if (!prev || !next) return 0;

    var prevRect = prev.getBoundingClientRect();
    var incomingTop = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
    var boardTop = next.getBoundingClientRect().top;
    return getPairOverlapProgress(prev, pairIndex, prevRect, incomingTop, boardTop).progress;
  }

  function updatePairTargets(sections) {
    var pairCount = sections.length - 1;
    if (!pairCount) return;

    if (prefersReducedMotion()) {
      resetPairProgressState(sections);
      return;
    }

    for (var i = 0; i < pairCount; i += 1) {
      var prev = sections[i];
      var next = sections[i + 1];
      var prevRect = prev.getBoundingClientRect();
      var incomingTop = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
      var boardTop = next.getBoundingClientRect().top;
      var targets = getPairTargetsFromMetrics(prev, i, prevRect, incomingTop, boardTop);

      pairTargetPrevDim[i] = targets.prevDim;
      pairTargetNextOver[i] = targets.nextOver;
      pairTargetOverlap[i] = targets.overlap;
    }

    scrollDividerEls.forEach(function (divider) {
      initDividerLineState(divider);
      divider._dividerTargetRaw = getDividerTargetProgress(divider._dividerPairIndex);
    });
  }

  function getSlipMaxPx() {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    if (window.matchMedia && window.matchMedia('(max-width: 749px)').matches) {
      return clamp(vh * SLIP_VH_MOBILE, SLIP_MIN_MOBILE, SLIP_MAX_MOBILE);
    }
    return clamp(vh * SLIP_VH_DESKTOP, SLIP_MIN_DESKTOP, SLIP_MAX_DESKTOP);
  }

  function clearBlockSlip(el) {
    el.style.setProperty('--home-stack-slip-y', '0px');
    el._slipApplied = '0';
  }

  function applyBlockSlip(el, slipPx) {
    var px = Math.abs(slipPx) <= SLIP_CLEAR_EPS ? 0 : Math.round(slipPx);
    var rounded = String(px);
    if (el._slipApplied === rounded) return;
    el._slipApplied = rounded;
    el.style.setProperty('--home-stack-slip-y', px + 'px');
  }

  function applyPairSlip(pairIndex, slipPx, sections) {
    var next = sections[pairIndex + 1];
    if (next) applyBlockSlip(next, slipPx);
    scrollDividerEls.forEach(function (divider) {
      if (divider._dividerPairIndex === pairIndex) applyBlockSlip(divider, slipPx);
    });
  }

  function lerpSectionPair(current, target) {
    var rate = target < current ? SECTION_LERP_DECAY : getSectionLerpRise();
    current += (target - current) * rate;
    if (Math.abs(target - current) <= SECTION_LERP_EPS) {
      return { value: target, needsMore: false };
    }
    return { value: current, needsMore: true };
  }

  function applyOverlapEased(el, eased) {
    if (eased > SECTION_LERP_EPS) {
      el.style.setProperty('--home-stack-overlap-eased', eased.toFixed(4));
      el._overlapEasedActive = true;
    } else if (el._overlapEasedActive) {
      el.style.removeProperty('--home-stack-overlap-eased');
      el._overlapEasedActive = false;
    }
  }

  function applySmoothedStack(sections) {
    if (prefersReducedMotion()) return;

    var pairCount = sections.length - 1;
    var sectionPrevDim = [];
    var sectionNextOver = [];
    var sectionSlipPx = [];
    var sectionOverlapEased = [];
    var pairSlipPx = [];
    var slipMax = getSlipMaxPx();

    for (var i = 0; i < pairCount; i += 1) {
      var targetOverlap = pairTargetOverlap[i] || 0;
      var currentOverlap = pairCurrentOverlap[i] || 0;
      var easedOverlapCurrent = easeInOutCubic(currentOverlap);
      /* Poślizg = luka target↔current (scroll natychmiast, motion dogania z opóźnieniem) */
      var slipPx = (targetOverlap - currentOverlap) * slipMax;
      var easedPrevDim = easeInOutCubic(pairCurrentPrevDim[i] || 0);
      var easedNextOver = easeInOutCubic(pairCurrentNextOver[i] || 0);

      pairSlipPx[i] = slipPx;

      if (easedPrevDim > sectionPrevDim[i] || sectionPrevDim[i] === undefined) {
        sectionPrevDim[i] = easedPrevDim;
      }
      if (easedNextOver > sectionNextOver[i + 1] || sectionNextOver[i + 1] === undefined) {
        sectionNextOver[i + 1] = easedNextOver;
      }
      var overlapEased = easeInOutCubic(currentOverlap);
      if (overlapEased > (sectionOverlapEased[i + 1] || 0)) {
        sectionOverlapEased[i + 1] = overlapEased;
      }
      sectionSlipPx[i + 1] = slipPx;
    }

    sections.forEach(function (el, index) {
      var dim = sectionPrevDim[index] || 0;
      if (dim > SECTION_LERP_EPS) {
        el.style.setProperty('--home-stack-under-dim', dim.toFixed(4));
        el.classList.add('is-stack-under-dim');
        el._underDimActive = true;
      } else if (el._underDimActive) {
        clearUnderDim(el);
      }

      var over = sectionNextOver[index] || 0;
      if (over > SECTION_LERP_EPS) {
        el.style.setProperty('--home-stack-over-depth', over.toFixed(4));
        el._overDepthActive = true;
      } else if (el._overDepthActive) {
        clearOverDepth(el);
      }

      applyOverlapEased(el, sectionOverlapEased[index] || 0);
    });

    for (var p = 0; p < pairCount; p += 1) {
      applyPairSlip(p, pairSlipPx[p] || 0, sections);
    }
  }

  function applyReducedMotionStack(sections) {
    resetPairProgressState(sections);
    sections.forEach(function (el) {
      clearUnderDim(el);
      clearOverDepth(el);
      clearBlockSlip(el);
      if (el._overlapEasedActive) {
        el.style.removeProperty('--home-stack-overlap-eased');
        el._overlapEasedActive = false;
      }
    });
    scrollDividerEls.forEach(function (divider) {
      initDividerLineState(divider);
      divider._dividerCurrentScale = 1;
      applyDividerLineScale(divider, 1);
    });
  }

  function tickMotion() {
    motionFrameId = 0;
    if (prefersReducedMotion() || stackEls.length < 2) return;

    updatePairTargets(stackEls);

    var needsMore = false;
    var pairCount = stackEls.length - 1;

    for (var i = 0; i < pairCount; i += 1) {
      var prevResult = lerpSectionPair(
        pairCurrentPrevDim[i] || 0,
        pairTargetPrevDim[i] || 0
      );
      pairCurrentPrevDim[i] = prevResult.value;
      if (prevResult.needsMore) needsMore = true;

      var nextResult = lerpSectionPair(
        pairCurrentNextOver[i] || 0,
        pairTargetNextOver[i] || 0
      );
      pairCurrentNextOver[i] = nextResult.value;
      if (nextResult.needsMore) needsMore = true;

      var overlapResult = lerpSectionPair(
        pairCurrentOverlap[i] || 0,
        pairTargetOverlap[i] || 0
      );
      pairCurrentOverlap[i] = overlapResult.value;
      if (overlapResult.needsMore) needsMore = true;
    }

    applySmoothedStack(stackEls);

    scrollDividerEls.forEach(function (divider) {
      var pairIndex = divider._dividerPairIndex;
      if (pairIndex < 0) return;
      if (pairIndex === 0) {
        applyDividerLineScale(divider, 1);
        return;
      }
      applyDividerLineScale(divider, easeInOutCubic(pairCurrentOverlap[pairIndex] || 0));
    });

    if (needsMore || document.documentElement.classList.contains('giclee-home-stack-scrolling')) {
      scheduleMotionTick();
    }
  }

  function tagDividersForStack(sections) {
    for (var i = 0; i < sections.length; i += 1) {
      var isLast = i === sections.length - 1;
      var layer = isLast ? i + 1 : i + 2;
      var stopAt = isLast ? null : sections[i + 1];
      var dividersInGap = [];
      var el = sections[i].nextElementSibling;

      while (el && el !== stopAt) {
        if (isDividerSection(el)) dividersInGap.push(el);
        el = el.nextElementSibling;
      }

      dividersInGap.forEach(function (dividerEl, dividerIndex) {
        dividerEl.setAttribute('data-giclee-home-stack', String(layer));
        dividerEl.classList.add('giclee-home-stack-divider');
        dividerEl.classList.remove('giclee-home-stack-divider--scroll');
        dividerEl._dividerPairIndex = -1;

        var isScrollDivider = !isLast && dividerIndex === dividersInGap.length - 1;
        if (isScrollDivider) {
          dividerEl.classList.add('giclee-home-stack-divider--scroll');
          dividerEl._dividerPairIndex = i;
          if (i === 0) {
            initPairZeroScrollDivider(dividerEl);
          } else {
            resetScrollDividerLine(dividerEl.querySelector('.divider__line'));
          }
        }
      });
    }
  }

  function findActivePairIndex(sections) {
    for (var i = sections.length - 2; i >= 0; i -= 1) {
      var prev = sections[i];
      var next = sections[i + 1];
      var prevRect = prev.getBoundingClientRect();
      var incomingTop = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
      var boardTop = next.getBoundingClientRect().top;
      var result = getPairOverlapProgress(prev, i, prevRect, incomingTop, boardTop);

      if (result.phase === 'none' || result.phase === 'dock' || result.phase === 'rest') continue;
      if (result.phase === 'overlap' && incomingTop <= PREV_PIN_EPS && i < sections.length - 2) {
        continue;
      }

      return i;
    }
    return -1;
  }

  function getPairTargetsInstant(sections, pairIndex) {
    var prev = sections[pairIndex];
    var next = sections[pairIndex + 1];
    var prevRect = prev.getBoundingClientRect();
    var incomingTop = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
    var boardTop = next.getBoundingClientRect().top;
    return getPairTargetsFromMetrics(prev, pairIndex, prevRect, incomingTop, boardTop);
  }

  function getDividerElsBeforeNext(sections, pairIndex) {
    var prev = sections[pairIndex];
    var next = sections[pairIndex + 1];
    return getBetweenElements(prev, next).filter(isDividerSection);
  }

  function getOverlapMetrics(sections, pairIndex) {
    var prev = sections[pairIndex];
    var next = sections[pairIndex + 1];
    var prevRect = prev.getBoundingClientRect();
    var incomingTop = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
    var nextTop = next.getBoundingClientRect().top;
    var overlapBottom = getOverlapBottomFromRect(prev, prevRect);
    var overlapDepth =
      overlapBottom > 0
        ? Math.round(((overlapBottom - incomingTop) / overlapBottom) * 1000) / 1000
        : 0;

    return {
      prevTop: Math.round(prevRect.top * 10) / 10,
      prevBottom: Math.round(prevRect.bottom * 10) / 10,
      overlapBottom: Math.round(overlapBottom * 10) / 10,
      nextTop: Math.round(nextTop * 10) / 10,
      incomingTop: Math.round(incomingTop * 10) / 10,
      overlapDepth: overlapDepth,
      dividerCount: getDividerElsBeforeNext(sections, pairIndex).length,
      transitionComplete: incomingTop <= PREV_PIN_EPS,
      overlapping: isNextOverlappingPrevFromRect(prev, prevRect, incomingTop),
      prevPinned: isPrevPinnedAtTopFromRect(prev, pairIndex, prevRect),
    };
  }

  function clearUnderDim(el) {
    el.classList.remove('is-stack-under-dim');
    el.style.removeProperty('--home-stack-under-dim');
    el._underDimActive = false;
    if (el._overlapEasedActive) {
      el.style.removeProperty('--home-stack-overlap-eased');
      el._overlapEasedActive = false;
    }
  }

  function clearOverDepth(el) {
    el.style.removeProperty('--home-stack-over-depth');
    el._overDepthActive = false;
  }

  function updateStackUnderDim(sections) {
    if (prefersReducedMotion()) {
      sections.forEach(function (el) {
        if (el._underDimActive) clearUnderDim(el);
        if (el._overDepthActive) clearOverDepth(el);
        if (el._slipApplied && el._slipApplied !== '0') clearBlockSlip(el);
      });

      for (var i = 0; i < sections.length - 1; i += 1) {
        var targets = getPairTargetsInstant(sections, i);
        if (targets.prevDim <= 0.001 && targets.nextOver <= 0.001) continue;

        var prev = sections[i];
        var next = sections[i + 1];
        if (targets.prevDim > 0.001) {
          prev.style.setProperty('--home-stack-under-dim', targets.prevDim.toFixed(4));
          prev.classList.add('is-stack-under-dim');
          prev._underDimActive = true;
        }
        if (targets.nextOver > 0.001) {
          next.style.setProperty('--home-stack-over-depth', targets.nextOver.toFixed(4));
          next._overDepthActive = true;
        }
      }
      return;
    }

    updatePairTargets(sections);
    scheduleMotionTick();
  }

  function getHeaderFadeTarget() {
    return document.getElementById('header-component');
  }

  function getHeroSection() {
    var map = window.GICLEE_HOME_SECTIONS || {};
    return findSection(map.hero);
  }

  function getHeaderFadeAnchorScroll() {
    var hero = getHeroSection();
    if (!hero) return Math.max(window.innerHeight * 0.35, 120);

    var rect = hero.getBoundingClientRect();
    var scrollY = getScrollY();
    var heroBottom = scrollY + rect.top + rect.height;
    return Math.max(heroBottom * 0.22, 80);
  }

  function getHeaderFadeOpacity(scrollY) {
    var DIMMED = 0.1;
    if (scrollY <= 0) return 1;

    var anchor = getHeaderFadeAnchorScroll();
    var t = Math.min(1, scrollY / anchor);
    t = Math.pow(t, 0.35);

    if (scrollY <= anchor) {
      return 1 - (1 - DIMMED) * t;
    }

    var tailRange = Math.max(anchor * 0.32, 28);
    var beyond = scrollY - anchor;
    return Math.max(0, DIMMED * (1 - Math.min(1, beyond / tailRange)));
  }

  function updateHeaderScrollFade() {
    var header = getHeaderFadeTarget();
    if (!header || !document.documentElement.classList.contains('giclee-home-stack')) {
      return;
    }

    if (prefersReducedMotion()) {
      header.classList.remove('giclee-header-scroll-fade');
      header.style.removeProperty('--gab-header-fade-opacity');
      header.style.removeProperty('pointer-events');
      return;
    }

    var scrollY = getScrollY();
    var opacity = getHeaderFadeOpacity(scrollY);

    header.classList.add('giclee-header-scroll-fade');
    header.style.setProperty('--gab-header-fade-opacity', opacity.toFixed(3));
    header.style.pointerEvents = opacity < 0.12 ? 'none' : '';
  }

  function buildDebugSnapshot() {
    var scrollY = getScrollY();
    var activePairIndex = findActivePairIndex(stackEls);
    var slipMax = getSlipMaxPx();
    var pairs = [];

    for (var i = 0; i < stackEls.length - 1; i += 1) {
      var prev = stackEls[i];
      var next = stackEls[i + 1];
      var metrics = getOverlapMetrics(stackEls, i);
      var instant = getPairTargetsInstant(stackEls, i);
      var prevRectLive = prev.getBoundingClientRect();
      var incomingTopLive = getIncomingLeadEl(prev, next).getBoundingClientRect().top;
      var boardTopLive = next.getBoundingClientRect().top;
      var pairProgress = getPairOverlapProgress(
        prev,
        i,
        prevRectLive,
        incomingTopLive,
        boardTopLive
      );
      var dividers = getDividerElsBeforeNext(stackEls, i);
      var scrollDividers = dividers.filter(function (d) {
        return d.classList.contains('giclee-home-stack-divider--scroll');
      });
      var scrollDivider = scrollDividers.length > 0 ? scrollDividers[scrollDividers.length - 1] : null;
      var leadEl = getIncomingLeadEl(prev, next);

      var targetOverlap = pairTargetOverlap[i] || 0;
      var currentOverlap = pairCurrentOverlap[i] || 0;
      var easedOverlapCurrent = easeInOutCubic(currentOverlap);
      var easedOverlapTarget = easeInOutCubic(targetOverlap);
      var slipPxDebug = (targetOverlap - currentOverlap) * slipMax;

      pairs.push({
        layer: i + 1 + '→' + (i + 2),
        prevId: prev.id,
        nextId: next.id,
        leadId: leadEl.id,
        prevTop: metrics.prevTop,
        prevBottom: metrics.prevBottom,
        overlapBottom: metrics.overlapBottom,
        nextTop: metrics.nextTop,
        incomingTop: metrics.incomingTop,
        overlapDepth: metrics.overlapDepth,
        dividerCount: metrics.dividerCount,
        dividerScroll: scrollDividers.length > 0,
        pairTargetPrevDim: Math.round((pairTargetPrevDim[i] || 0) * 1000) / 1000,
        pairCurrentPrevDim: Math.round((pairCurrentPrevDim[i] || 0) * 1000) / 1000,
        pairTargetNextOver: Math.round((pairTargetNextOver[i] || 0) * 1000) / 1000,
        pairCurrentNextOver: Math.round((pairCurrentNextOver[i] || 0) * 1000) / 1000,
        pairTargetOverlap: Math.round(targetOverlap * 1000) / 1000,
        pairCurrentOverlap: Math.round(currentOverlap * 1000) / 1000,
        pairProgressInstant: Math.round(pairProgress.progress * 1000) / 1000,
        phase: pairProgress.phase,
        easedTarget: Math.round(easedOverlapTarget * 1000) / 1000,
        easedCurrent: Math.round(easedOverlapCurrent * 1000) / 1000,
        slipPx: Math.round(slipPxDebug * 10) / 10,
        slipMax: Math.round(slipMax * 10) / 10,
        instantTargets: instant,
        dividerCurrentScale: scrollDivider
          ? Math.round((scrollDivider._dividerCurrentScale || 0) * 1000) / 1000
          : null,
        dividerTarget: Math.round(getDividerTargetProgress(i) * 1000) / 1000,
        dividerApproach: Math.round(
          getDividerApproachProgress(prev, prev.getBoundingClientRect(), metrics.nextTop) * 1000
        ) / 1000,
        transitionComplete: metrics.transitionComplete,
        overlapping: metrics.overlapping,
        active: i === activePairIndex,
        prevPinned: metrics.prevPinned,
        scrollY: scrollY,
        prevDimClass: prev.classList.contains('is-stack-under-dim'),
        nextOverDepth: next.style.getPropertyValue('--home-stack-over-depth') || null,
      });
    }

    return {
      activePairIndex: activePairIndex,
      stackEnabled: !!window.GICLEE_HOME_STACK,
      htmlClass: document.documentElement.classList.contains('giclee-home-stack'),
      sectionCount: stackEls.length,
      touchLike: isTouchLikeDevice(),
      reducedMotion: prefersReducedMotion(),
      scrollY: scrollY,
      pairs: pairs,
    };
  }

  window.GICLEE_HOME_STACK_DEBUG = function () {
    var snap = buildDebugSnapshot();
    console.table(snap.pairs);
    console.log('[giclee-home-stack]', snap);
    return snap;
  };

  window.GICLEE_HOME_STACK_SLIP_CHECK = function (ms) {
    ms = ms || 3000;
    var start = performance.now();
    var mismatches = 0;
    var scaleUpdates = 0;
    function tick() {
      scrollDividerEls.forEach(function (divider) {
        var pairIndex = divider._dividerPairIndex;
        if (pairIndex < 0) return;
        var next = stackEls[pairIndex + 1];
        var divSlip = divider.style.getPropertyValue('--home-stack-slip-y') || '0px';
        var cardSlip = next ? next.style.getPropertyValue('--home-stack-slip-y') || '0px' : '0px';
        if (divSlip !== cardSlip) {
          mismatches += 1;
          console.warn('[slip mismatch]', pairIndex, { divider: divSlip, card: cardSlip });
        }
        var line = divider._dividerLine || divider.querySelector('.divider__line');
        var scale = line ? line.style.getPropertyValue('--home-stack-divider-scale') : '';
        if (line && line._lastScaleCheck !== scale) {
          scaleUpdates += 1;
          line._lastScaleCheck = scale;
        }
      });
      if (performance.now() - start < ms) {
        requestAnimationFrame(tick);
      } else {
        console.log('[giclee-home-stack slip check]', { mismatches: mismatches, scaleUpdates: scaleUpdates });
      }
    }
    requestAnimationFrame(tick);
    return 'Monitoring slip for ' + ms + 'ms — scroll now';
  };

  function readHeaderGroupHeightPx() {
    var raw = getComputedStyle(document.body).getPropertyValue('--header-group-height');
    var px = parseFloat(raw);
    return Number.isFinite(px) && px > 0 ? px : 0;
  }

  function resolveHeroMinHeightValue(heroTopPx) {
    if (heroTopPx <= HERO_VIEWPORT_TOP_EPS) {
      return '100svh';
    }
    return 'calc(100svh - ' + heroTopPx.toFixed(2) + 'px)';
  }

  function measureHeroViewportTopPx(heroElement) {
    if (!heroElement) return 0;
    if (getScrollY() <= SCROLL_REST_EPS) {
      return Math.max(0, heroElement.getBoundingClientRect().top);
    }
    if (document.querySelector('#header-component[transparent]')) {
      return 0;
    }
    return readHeaderGroupHeightPx();
  }

  function measureHeaderHeightPx() {
    var header = document.getElementById('header-component');
    if (header) {
      return Math.max(0, header.getBoundingClientRect().height);
    }
    var fallback = readHeaderGroupHeightPx();
    return fallback > 0 ? fallback : 60;
  }

  function applyHeroLayoutMetrics(heroElement) {
    if (!heroElement) return;

    var headerHeight = measureHeaderHeightPx();
    var headerHeightPx = headerHeight.toFixed(2) + 'px';
    var heroTopPx = measureHeroViewportTopPx(heroElement);
    var minHeight = resolveHeroMinHeightValue(heroTopPx);
    var mediaOffsetTopPx =
      heroTopPx <= HERO_VIEWPORT_TOP_EPS ? headerHeight.toFixed(2) + 'px' : '0px';
    var layoutKey =
      minHeight +
      '|' +
      headerHeightPx +
      '|' +
      mediaOffsetTopPx;

    if (heroElement._heroLayoutApplied === layoutKey) return;
    heroElement._heroLayoutApplied = layoutKey;

    document.documentElement.style.removeProperty('--home-stack-hero-min-height');
    heroElement.style.setProperty('--home-stack-hero-min-height', minHeight);
    heroElement.style.setProperty('--home-stack-hero-header-height', headerHeightPx);
    heroElement.style.setProperty('--home-stack-hero-footer-height', headerHeightPx);
    heroElement.style.setProperty('--home-stack-hero-media-offset-top', mediaOffsetTopPx);
  }

  function scheduleHeroLayoutMeasure(heroElement) {
    if (!heroElement) return;
    applyHeroLayoutMetrics(heroElement);
    requestAnimationFrame(function () {
      applyHeroLayoutMetrics(heroElement);
      requestAnimationFrame(function () {
        applyHeroLayoutMetrics(heroElement);
      });
    });
  }

  function ensureHeroFooterBand(heroElement) {
    if (!heroElement) return null;
    var footer = heroElement.querySelector('.giclee-home-hero-footer');
    if (!footer) {
      footer = document.createElement('div');
      footer.className = 'giclee-home-hero-footer';
      footer.setAttribute('aria-hidden', 'true');
      heroElement.appendChild(footer);
    }
    return footer;
  }

  function ensureHeroScrollCue(heroElement) {
    if (!heroElement) return;

    var footer = ensureHeroFooterBand(heroElement);
    var cue = heroElement.querySelector('.giclee-home-scroll-cue');

    if (!cue) {
      cue = document.createElement('div');
      cue.className = 'giclee-home-scroll-cue';
      cue.setAttribute('aria-hidden', 'true');

      var chevron1 = document.createElement('span');
      chevron1.className = 'giclee-home-scroll-cue__chevron';
      var chevron2 = document.createElement('span');
      chevron2.className = 'giclee-home-scroll-cue__chevron';

      cue.appendChild(chevron1);
      cue.appendChild(chevron2);
    }

    if (footer && cue.parentElement !== footer) {
      footer.appendChild(cue);
    }
  }

  function scheduleStackUpdate() {
    if (scheduleStackUpdate._ticking) return;
    scheduleStackUpdate._ticking = true;
    requestAnimationFrame(function () {
      scheduleStackUpdate._ticking = false;
      updateHeaderScrollFade();
      updateStackUnderDim(stackEls);
    });
  }

  function initHomeStack() {
    if (!window.GICLEE_HOME_STACK) return;

    var map = window.GICLEE_HOME_SECTIONS;
    if (!map || typeof map !== 'object') return;

    stackEls = [];

    STACK_HOOKS.forEach(function (hook, index) {
      var sectionKey = map[hook];
      var el = findSection(sectionKey);
      if (!el) return;
      el.setAttribute('data-giclee-home-stack', String(index + 1));
      stackEls.push(el);
    });

    if (stackEls.length < 2) return;

    ensureHeroScrollCue(stackEls[0]);
    document.documentElement.classList.add('giclee-home-stack');
    scheduleHeroLayoutMeasure(stackEls[0]);
    tagDividersForStack(stackEls);
    collectScrollDividers();
    resetPairProgressState(stackEls);
    scrollDividerEls.forEach(function (divider) {
      initDividerLineState(divider);
      if (divider._dividerPairIndex === 0) {
        initPairZeroScrollDivider(divider);
      } else {
        resetScrollDividerLine(divider._dividerLine || divider.querySelector('.divider__line'));
      }
    });
    if (prefersReducedMotion()) {
      applyReducedMotionStack(stackEls);
    } else {
      updatePairTargets(stackEls);
      scheduleMotionTick();
    }

    window.addEventListener('scroll', function () {
      markScrolling();
      scheduleStackUpdate();
      scheduleMotionTick();
    }, { passive: true });
    window.addEventListener('resize', function () {
      scheduleHeroLayoutMeasure(stackEls[0]);
      scheduleStackUpdate();
    }, { passive: true });
    window.addEventListener('giclee:splash-done', function () {
      scheduleHeroLayoutMeasure(stackEls[0]);
    }, { passive: true });
    scheduleStackUpdate();
    requestAnimationFrame(function () {
      scheduleHeroLayoutMeasure(stackEls[0]);
      document.documentElement.classList.add('giclee-home-stack-ready');
      window.dispatchEvent(new CustomEvent('giclee:home-stack-ready'));
    });
  }

  function runInitHomeStack() {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initHomeStack);
    } else {
      initHomeStack();
    }
  }

  runInitHomeStack();
})();
