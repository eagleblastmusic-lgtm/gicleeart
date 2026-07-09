/*
 * Strona główna: section-scroll — jeden wyraźny gest = przejście do następnej /
 * poprzedniej sekcji. Desktop-first; mobile: native / soft / disabled.
 *
 * Konfiguracja: window.GICLEE_HOME_SCROLL_CONFIG (generowana przez GicleeApp →
 * Strona główna → Animacja przewijania). Brak konfiguracji = bezpieczne domyślne.
 * Kill switch: enabled: false → moduł nie przechwytuje niczego.
 *
 * Współpraca ze stackiem (giclee-home-stack.js): cel animacji = zamrożony canonical dock
 * (documentTop − stopOffset, pomiar przy scrollY=0). getBoundingClientRect kłamie w sticky
 * stacku — tylko debug. Kolejność sekcji = hooki GICLEE_HOME_SECTIONS / DOM, bez sortu live.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  if (root.dataset.gicleeHomeSectionScroll === 'on') return;

  var RUNWAY_EPS = 24;
  var MIN_ANIM_PX = 80;
  var NAV_TOLERANCE = 2;
  var STACK_LAYOUT_MIN_GAP = 48;

  var DEFAULTS = {
    enabled: true,
    desktopEnabled: true,
    mobileMode: 'native', // native | soft | disabled
    minDuration: 650,
    maxDuration: 1100,
    wheelThreshold: 40,
    touchThreshold: 48,
    headerOffset: null, // null = auto (0 w stacku — header wygasza się sam)
    headerOffsetExtra: 24,
    separatorOffset: 8,
    motionDynamics: 50, // 0 = spokojny / kontemplacyjny, 100 = dynamiczny
    reducedMotionMode: 'instant', // off | instant
    headingSettle: true,
    debug: false,
  };

  var cfg = {};
  (function mergeConfig() {
    var user = window.GICLEE_HOME_SCROLL_CONFIG;
    Object.keys(DEFAULTS).forEach(function (key) {
      cfg[key] =
        user && Object.prototype.hasOwnProperty.call(user, key)
          ? user[key]
          : DEFAULTS[key];
    });
    if (cfg.minDuration > cfg.maxDuration) cfg.maxDuration = cfg.minDuration;
    cfg.motionDynamics = Math.min(100, Math.max(0, Number(cfg.motionDynamics) || 0));
  })();

  if (!cfg.enabled) return;
  if (window.Shopify && window.Shopify.designMode) return;

  var isTouchLike =
    window.matchMedia &&
    window.matchMedia('(hover: none) and (pointer: coarse)').matches;
  var isSmallViewport =
    window.matchMedia && window.matchMedia('(max-width: 749px)').matches;
  var touchContext = isTouchLike || isSmallViewport;

  if (touchContext && cfg.mobileMode !== 'soft') return;
  if (!touchContext && !cfg.desktopEnabled) return;

  function debugLog() {
    if (!cfg.debug || !window.console) return;
    var args = ['[giclee-section-scroll]'].concat(
      Array.prototype.slice.call(arguments)
    );
    console.log.apply(console, args);
  }

  function prefersReducedMotion() {
    return (
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    );
  }

  function motionDynamicsNorm() {
    return Math.min(100, Math.max(0, Number(cfg.motionDynamics) || 0)) / 100;
  }

  function durationScale() {
    return 1.2 - motionDynamicsNorm() * 0.5;
  }

  function easeOutMotion(t) {
    t = Math.min(Math.max(t, 0), 1);
    var p = 3 + motionDynamicsNorm() * 2;
    return 1 - Math.pow(1 - t, p);
  }

  /* ── Sekcje-targety ─────────────────────────────────────────── */

  var SECTION_HOOKS = [
    'hero',
    'intro',
    'restoration',
    'color-correction',
    'potential',
    'see-difference',
  ];

  var sections = [];
  var canonicalDockCache = [];
  var frozenSectionIds = [];
  var cachedRunwayStep = 0;

  function findSection(sectionKey) {
    if (!sectionKey) return null;
    return (
      document.getElementById('shopify-section-' + sectionKey) ||
      document.querySelector('.shopify-section[id*="' + sectionKey + '"]')
    );
  }

  function documentTop(el) {
    var top = 0;
    while (el) {
      top += el.offsetTop;
      el = el.offsetParent;
    }
    return top;
  }

  function isEligibleTarget(el) {
    if (!el) return false;
    if (el.classList.contains('giclee-home-stack-divider')) return false;
    if (el.offsetParent === null && getComputedStyle(el).position !== 'sticky') {
      return false;
    }
    return el.offsetHeight >= 160;
  }

  function sectionId(el) {
    return el && el.id ? el.id : '';
  }

  /** Kolejność mapy / DOM — bez sortowania po live offsetTop (stack psuje offset przy scrollu). */
  function collectSections() {
    var found = [];
    var map = window.GICLEE_HOME_SECTIONS;
    if (map && typeof map === 'object') {
      SECTION_HOOKS.forEach(function (hook) {
        if (!Object.prototype.hasOwnProperty.call(map, hook)) return;
        var el = findSection(map[hook]);
        if (isEligibleTarget(el)) found.push(el);
      });
      if (found.length < 2) {
        Object.keys(map).forEach(function (hook) {
          if (SECTION_HOOKS.indexOf(hook) >= 0) return;
          var el = findSection(map[hook]);
          if (isEligibleTarget(el)) found.push(el);
        });
      }
    }
    if (found.length < 2) {
      var main = document.getElementById('MainContent');
      if (main) {
        found = Array.prototype.slice
          .call(main.querySelectorAll(':scope > .shopify-section'))
          .filter(isEligibleTarget);
      }
    }
    sections = found;
    return sections;
  }

  function headerAutoOffset() {
    if (root.classList.contains('giclee-home-stack')) return 0;
    var header = document.getElementById('header-component');
    if (!header) return 0;
    var rect = header.getBoundingClientRect();
    return rect.height > 0 && rect.top <= 1 ? Math.round(rect.height) : 0;
  }

  function stopOffset() {
    var base =
      cfg.headerOffset === null || cfg.headerOffset === undefined
        ? headerAutoOffset()
        : Number(cfg.headerOffset) || 0;
    return base + (Number(cfg.headerOffsetExtra) || 0) + (Number(cfg.separatorOffset) || 0);
  }

  function maxScrollY() {
    return Math.max(
      0,
      (document.scrollingElement || root).scrollHeight - window.innerHeight
    );
  }

  function getScrollY() {
    return window.scrollY || window.pageYOffset || root.scrollTop || 0;
  }

  function stackSeamHeight() {
    var raw = getComputedStyle(root).getPropertyValue('--home-stack-seam-height');
    if (raw) {
      var probe = document.createElement('div');
      probe.style.height = raw.trim();
      probe.style.position = 'absolute';
      probe.style.visibility = 'hidden';
      document.body.appendChild(probe);
      var h = probe.offsetHeight;
      document.body.removeChild(probe);
      if (h > 0) return h;
    }
    return 61;
  }

  function stackRunwayStep() {
    var vh = window.innerHeight || document.documentElement.clientHeight || 800;
    return Math.max(Math.round(vh - stackSeamHeight()), Math.round(vh * 0.92));
  }

  function stackPinTop() {
    return root.classList.contains('giclee-home-stack') ? 0 : stopOffset();
  }

  function dockPositionsStack() {
    var limit = maxScrollY();
    var step = stackRunwayStep();
    var positions = [0];
    if (sections.length < 2) return positions;

    var prevDock = 0;
    for (var i = 1; i < sections.length; i++) {
      /* layoutTop = scrollY, przy którym sticky karta (top:0) trafia w pin — w stacku od 3. sekcji
       * offsetTop bywa zduplikowany / za mały; fallback = prevDock + runway step. */
      var layoutTop = Math.round(documentTop(sections[i]) - stackPinTop());
      var nextY =
        layoutTop > prevDock + STACK_LAYOUT_MIN_GAP ? layoutTop : prevDock + step;

      if (nextY <= prevDock) {
        nextY = prevDock + step;
      }
      nextY = Math.min(Math.max(nextY, 0), limit);
      if (nextY <= prevDock && i < sections.length - 1) {
        nextY = Math.min(prevDock + step, limit);
        if (nextY <= prevDock) {
          nextY = Math.min(prevDock + 1, limit);
        }
      }

      positions.push(nextY);
      prevDock = nextY;
    }
    return positions;
  }

  function computeCanonicalDockPositions() {
    if (root.classList.contains('giclee-home-stack') && sections.length >= 2) {
      return dockPositionsStack();
    }
    var offset = stopOffset();
    var limit = maxScrollY();
    return sections.map(function (el, index) {
      if (index === 0) return 0;
      return Math.min(Math.max(documentTop(el) - offset, 0), limit);
    });
  }

  function currentSectionIds() {
    return sections.map(sectionId);
  }

  function sectionIdsEqual(a, b) {
    if (!a || !b || a.length !== b.length) return false;
    for (var i = 0; i < a.length; i += 1) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }

  function isMonotonicPositions(positions) {
    if (!positions || positions.length < 2) return false;
    for (var i = 1; i < positions.length; i += 1) {
      if (positions[i] <= positions[i - 1]) return false;
    }
    return true;
  }

  /** Walidacja cache — monotoniczność + każdy dock mapuje na swój indeks nawigacji. */
  function isValidDockCache(positions, count) {
    if (!positions || positions.length !== count || count < 2) return false;
    if (!isMonotonicPositions(positions)) return false;
    for (var i = 0; i < positions.length; i += 1) {
      if (activeSectionIndexForNavigation(positions[i], positions) !== i) return false;
    }
    return true;
  }

  function rebuildCanonicalDock(forceApply) {
    if (sections.length < 2) {
      canonicalDockCache = [];
      frozenSectionIds = [];
      return;
    }

    var savedY = getScrollY();
    var savedScrollBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';
    if (savedY !== 0) {
      window.scrollTo(0, 0);
    }

    var newPositions = computeCanonicalDockPositions();

    if (savedY !== 0) {
      window.scrollTo(0, savedY);
    }
    root.style.scrollBehavior = savedScrollBehavior;

    if (!isValidDockCache(newPositions, sections.length)) {
      debugLog('rejected dock cache (invalid)', newPositions);
      return;
    }

    var oldValid = isValidDockCache(canonicalDockCache, sections.length);
    if (!forceApply && oldValid) {
      debugLog('rebuild skipped — frozen canonicalDockCache kept');
      return;
    }

    canonicalDockCache = newPositions;
    frozenSectionIds = currentSectionIds();
    cachedRunwayStep = stackRunwayStep();
  }

  function dockPositions() {
    return canonicalDockCache.slice();
  }

  function canonicalDockY(index) {
    if (index < 0 || index >= canonicalDockCache.length) return 0;
    return canonicalDockCache[index];
  }

  function runDebugAsserts(positions) {
    var failures = [];
    var ids = currentSectionIds();

    if (frozenSectionIds.length) {
      for (var o = 0; o < ids.length; o += 1) {
        if (ids[o] !== frozenSectionIds[o]) {
          failures.push(
            'section order changed at index ' +
              o +
              ': init=' +
              frozenSectionIds[o] +
              ' now=' +
              ids[o]
          );
        }
      }
    }

    for (var i = 1; i < positions.length; i += 1) {
      if (positions[i] <= positions[i - 1]) {
        failures.push(
          'canonicalDock not monotonic at index ' +
            i +
            ': ' +
            positions[i - 1] +
            ' → ' +
            positions[i]
        );
      }
    }

    for (var j = 0; j < positions.length; j += 1) {
      var navIdx = activeSectionIndexForNavigation(positions[j], positions);
      if (navIdx !== j) {
        failures.push(
          'canonicalDock index ' +
            j +
            ' (' +
            positions[j] +
            ') maps to nav idx ' +
            navIdx
        );
      }
    }

    return failures;
  }

  /** Tylko debug — w sticky stacku rect.top ≈ 0 dla wielu warstw naraz. */
  function resolveDockScrollY(el) {
    if (!el) return 0;
    var rect = el.getBoundingClientRect();
    var y = getScrollY() + rect.top - stackPinTop();
    return Math.min(Math.max(Math.round(y), 0), maxScrollY());
  }

  function currentIndex(positions, scrollY) {
    return activeSectionIndexForNavigation(scrollY, positions);
  }

  /** Źródło prawdy dla wheel / keyboard / stepDown / goToSection — tylko scrollY + docki. */
  function activeSectionIndexForNavigation(scrollY, positions) {
    var idx = 0;
    for (var i = 0; i < positions.length; i += 1) {
      if (scrollY >= positions[i] - NAV_TOLERANCE) idx = i;
    }
    return idx;
  }

  function viewportSectionIndex() {
    var cx = Math.round(window.innerWidth * 0.5);
    var cy = Math.round((window.innerHeight || 800) * 0.42);
    var hits = document.elementsFromPoint(cx, cy);
    var best = -1;
    var bestLayer = -1;
    for (var h = 0; h < hits.length; h += 1) {
      for (var s = 0; s < sections.length; s += 1) {
        if (sections[s] !== hits[h] && !sections[s].contains(hits[h])) continue;
        var layer = parseInt(sections[s].getAttribute('data-giclee-home-stack'), 10);
        if (isNaN(layer)) layer = s + 1;
        if (layer > bestLayer || (layer === bestLayer && s > best)) {
          bestLayer = layer;
          best = s;
        }
        break;
      }
    }
    return best;
  }

  function activeSectionIndexFromScroll(scrollY, positions) {
    return activeSectionIndexForNavigation(scrollY, positions);
  }

  /** Debug / UI — to samo co nawigacja; viewport osobno w debug(). */
  function activeSectionIndex(scrollY) {
    return activeSectionIndexForNavigation(scrollY, canonicalDockCache);
  }

  function findDuplicateDocks(positions) {
    var dupes = [];
    for (var i = 1; i < positions.length; i += 1) {
      if (positions[i] <= positions[i - 1]) {
        dupes.push({ index: i, dock: positions[i], prevDock: positions[i - 1] });
      }
    }
    return dupes;
  }

  function resolveScrollUpTargetIndex(idx, scrollY, positions) {
    if (idx <= 0) return 0;
    var dock = positions[idx];
    var runwayDist = scrollY - dock;

    if (runwayDist > 2) {
      /* Krótki runway (< MIN_ANIM_PX): snap o kilkadziesiąt px jest niewidoczny w stacku —
       * od razu poprzednia sekcja (np. restoration 32 px od pinu → intro, nie „nic się nie dzieje”). */
      if (runwayDist < MIN_ANIM_PX) {
        for (var k = idx - 1; k >= 0; k -= 1) {
          if (positions[k] < dock - 4) return k;
        }
        return 0;
      }
      return idx;
    }

    for (var j = idx - 1; j >= 0; j -= 1) {
      if (positions[j] < dock - 4) return j;
    }
    return 0;
  }

  function resolveScrollDownTargetIndex(idx, scrollY, positions) {
    if (idx >= sections.length - 1) return null;
    var dock = positions[idx];
    if (scrollY < dock - 2) {
      return idx;
    }
    if (positions[idx + 1] > dock + 4) {
      return idx + 1;
    }
    for (var j = idx + 1; j < sections.length; j += 1) {
      if (positions[j] > dock + 4) return j;
    }
    return null;
  }

  function resolveTargetForDirection(scrollY, direction) {
    var positions = canonicalDockCache;
    var idx = activeSectionIndexForNavigation(scrollY, positions);

    if (direction > 0) {
      return resolveScrollDownTargetIndex(idx, scrollY, positions);
    }

    if (idx <= 0) return 0;

    return resolveScrollUpTargetIndex(idx, scrollY, positions);
  }

  function navigateByDirection(direction) {
    var targetIdx = resolveTargetForDirection(getScrollY(), direction);
    if (targetIdx === null) return false;
    return goToIndex(targetIdx, direction);
  }

  /* ── Animacja ───────────────────────────────────────────────── */

  var animating = false;
  var animationFrame = 0;
  var quietTimer = 0;
  var waitingForQuiet = false;
  var lastNavDirection = 0;
  var QUIET_MS = 180;

  function durationFor(distance) {
    var vh = window.innerHeight || 800;
    var normalized = Math.min(Math.max((distance - vh * 0.5) / (vh * 2), 0), 1);
    var base = cfg.minDuration + (cfg.maxDuration - cfg.minDuration) * normalized;
    return Math.round(base * durationScale());
  }

  function beginQuietWindow() {
    waitingForQuiet = true;
    resetQuietTimer();
  }

  function resetQuietTimer() {
    clearTimeout(quietTimer);
    quietTimer = setTimeout(function () {
      waitingForQuiet = false;
    }, QUIET_MS);
  }

  function settleTarget(el) {
    if (!cfg.headingSettle || prefersReducedMotion() || !el) return;
    el.classList.add('giclee-snap-settle');
    setTimeout(function () {
      el.classList.remove('giclee-snap-settle');
    }, 900);
  }

  function animateScrollTo(targetY, onDone) {
    var startY = getScrollY();
    var delta = targetY - startY;
    if (Math.abs(delta) < 2) {
      if (onDone) onDone();
      return;
    }

    if (prefersReducedMotion()) {
      window.scrollTo(0, targetY);
      if (onDone) onDone();
      return;
    }

    var duration = durationFor(Math.abs(delta));
    var startTs = 0;
    animating = true;

    function step(ts) {
      if (!startTs) startTs = ts;
      var t = Math.min((ts - startTs) / duration, 1);
      window.scrollTo(0, Math.round(startY + delta * easeOutMotion(t)));
      if (t < 1) {
        animationFrame = requestAnimationFrame(step);
      } else {
        animating = false;
        animationFrame = 0;
        beginQuietWindow();
        if (onDone) onDone();
      }
    }
    animationFrame = requestAnimationFrame(step);
  }

  function cancelAnimation() {
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = 0;
    animating = false;
  }

  function resolveScrollUpTargetY(index, scrollY) {
    var positions = canonicalDockCache;
    if (index < 0 || index >= positions.length) return 0;
    var target = positions[index];
    if (target < scrollY - 2) {
      if (
        index > 0 &&
        index + 1 < positions.length &&
        positions[index + 1] - positions[index] < MIN_ANIM_PX &&
        scrollY - target < MIN_ANIM_PX
      ) {
        var deeper = Math.max(positions[index - 1], scrollY - MIN_ANIM_PX);
        if (deeper < scrollY - 2) return deeper;
      }
      return target;
    }
    if (index <= 0) return 0;
    /* Stack overlap: scroll już na pinie poprzedniej karty (np. potencjał widoczny przy
     * scrollY = dock korekcji) — sam pin dałby delta ≈ 0; cofnij o MIN_ANIM w runway. */
    var nudged = Math.max(positions[index - 1], scrollY - MIN_ANIM_PX);
    if (nudged < scrollY - 2) return nudged;
    for (var j = index - 1; j >= 0; j -= 1) {
      if (positions[j] < scrollY - 2) return positions[j];
    }
    return 0;
  }

  function goToIndex(index, direction) {
    if (index < 0 || index >= sections.length) return false;
    var el = sections[index];
    var scrollY = getScrollY();
    var target =
      typeof direction === 'number' && direction < 0
        ? resolveScrollUpTargetY(index, scrollY)
        : canonicalDockY(index);
    var delta = target - scrollY;
    if (typeof direction === 'number') lastNavDirection = direction;
    debugLog(
      'goToIndex',
      index,
      '→',
      target,
      'liveDock',
      resolveDockScrollY(el),
      'delta',
      delta
    );
    animateScrollTo(target, function () {
      settleTarget(el);
    });
    return true;
  }

  function shouldBlockForQuiet(direction) {
    if (animating) return true;
    if (waitingForQuiet && direction === lastNavDirection) return true;
    return false;
  }

  /* ── Blokery ────────────────────────────────────────────────── */

  var comparisonDragActive = false;

  document.addEventListener(
    'pointerdown',
    function (e) {
      if (e.target && e.target.closest && e.target.closest('.comparison-slider')) {
        comparisonDragActive = true;
      }
    },
    { passive: true, capture: true }
  );
  document.addEventListener('pointerup', function () { comparisonDragActive = false; }, { passive: true, capture: true });
  document.addEventListener('pointercancel', function () { comparisonDragActive = false; }, { passive: true, capture: true });

  function overlayOpen() {
    if (document.querySelector('dialog[open]')) return true;
    if (document.querySelector('#header-component details[open]')) return true;
    var notice = document.querySelector('.giclee-site-notice');
    if (notice && !notice.hidden) return true;
    if (document.body.classList.contains('pm-app-drawer-open')) return true;
    return false;
  }

  function splashActive() {
    return (
      root.classList.contains('splash-pending') ||
      root.classList.contains('splash-reveal')
    );
  }

  function focusInFormField() {
    var el = document.activeElement;
    if (!el) return false;
    var tag = el.tagName;
    return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable;
  }

  function inInnerScrollable(target) {
    var el = target;
    var main = document.getElementById('MainContent');
    while (el && el !== document.body && el !== main) {
      if (el.nodeType === 1 && el.scrollHeight > el.clientHeight + 4) {
        var overflowY = getComputedStyle(el).overflowY;
        if (overflowY === 'auto' || overflowY === 'scroll') return true;
      }
      el = el.parentElement;
    }
    return false;
  }

  function shouldBypass(e) {
    if (prefersReducedMotion() && cfg.reducedMotionMode === 'off') return true;
    if (e && (e.ctrlKey || e.metaKey || e.altKey)) return true;
    if (splashActive()) return true;
    if (overlayOpen()) return true;
    if (comparisonDragActive) return true;
    if (e && e.target && inInnerScrollable(e.target)) return true;
    return false;
  }

  /* ── Wheel ──────────────────────────────────────────────────── */

  var accum = 0;
  var accumResetTimer = 0;

  function normalizedDelta(e) {
    if (e.deltaMode === 1) return e.deltaY * 16;
    if (e.deltaMode === 2) return e.deltaY * window.innerHeight;
    return e.deltaY;
  }

  function inFooterZone(scrollY) {
    var lastIdx = sections.length - 1;
    if (lastIdx < 0) return false;
    return scrollY > canonicalDockY(lastIdx) + 4;
  }

  function onWheel(e) {
    if (shouldBypass(e)) return;

    if (sections.length < 2 || canonicalDockCache.length < 2) return;

    var scrollY = getScrollY();
    var delta = normalizedDelta(e);
    var vh = window.innerHeight || 800;

    if (inFooterZone(scrollY)) {
      if (delta > 0) return;
      var lastDock = canonicalDockY(sections.length - 1);
      if (scrollY - lastDock > vh * 0.75) return;
      e.preventDefault();
      if (shouldBlockForQuiet(-1)) {
        resetQuietTimer();
        return;
      }
      waitingForQuiet = false;
      goToIndex(sections.length - 1, -1);
      return;
    }

    if (scrollY <= 1 && delta < 0) return;

    e.preventDefault();

    if ((accum > 0 && delta < 0) || (accum < 0 && delta > 0)) accum = 0;
    accum += delta;
    clearTimeout(accumResetTimer);
    accumResetTimer = setTimeout(function () { accum = 0; }, 240);

    if (Math.abs(accum) < cfg.wheelThreshold) return;

    var direction = accum > 0 ? 1 : -1;
    accum = 0;

    if (shouldBlockForQuiet(direction)) {
      resetQuietTimer();
      return;
    }
    waitingForQuiet = false;

    var targetIdx = resolveTargetForDirection(scrollY, direction);
    if (targetIdx === null) return;

    goToIndex(targetIdx, direction);
  }

  /* ── Klawiatura ─────────────────────────────────────────────── */

  function onKeydown(e) {
    if (shouldBypass(e) || focusInFormField()) return;
    if (e.defaultPrevented) return;

    if (sections.length < 2 || canonicalDockCache.length < 2) return;

    var handled = false;
    var direction = 0;

    switch (e.key) {
      case 'PageDown':
      case 'ArrowDown':
        direction = 1;
        break;
      case ' ':
        direction = e.shiftKey ? -1 : 1;
        break;
      case 'PageUp':
      case 'ArrowUp':
        direction = -1;
        break;
      case 'Home':
        animateScrollTo(0);
        handled = true;
        break;
      case 'End':
        animateScrollTo(maxScrollY());
        handled = true;
        break;
      default:
        return;
    }

    if (direction !== 0) {
      if (shouldBlockForQuiet(direction)) return;
      waitingForQuiet = false;
      handled = navigateByDirection(direction);
    }

    if (handled) e.preventDefault();
  }

  /* ── Mobile soft ────────────────────────────────────────────── */

  var softTimer = 0;
  var softProgrammatic = false;

  function softSnap() {
    if (softProgrammatic || animating) return;
    if (shouldBypass(null)) return;
    if (sections.length < 2 || canonicalDockCache.length < 2) return;

    var scrollY = getScrollY();
    if (inFooterZone(scrollY)) return;

    var vh = window.innerHeight || 800;
    var nearest = -1;
    var nearestDist = Infinity;
    for (var i = 0; i < sections.length; i += 1) {
      var dock = canonicalDockY(i);
      var d = Math.abs(scrollY - dock);
      if (d < nearestDist) {
        nearestDist = d;
        nearest = i;
      }
    }
    if (nearest < 0) return;
    if (nearestDist < Number(cfg.touchThreshold) || nearestDist > vh * 0.3) return;

    softProgrammatic = true;
    animateScrollTo(canonicalDockY(nearest), function () {
      setTimeout(function () { softProgrammatic = false; }, 120);
    });
  }

  function onSoftScroll() {
    clearTimeout(softTimer);
    softTimer = setTimeout(softSnap, 160);
  }

  /* ── Cykl życia ─────────────────────────────────────────────── */

  var boundWheel = null;
  var boundKeydown = null;
  var boundSoftScroll = null;
  var boundLayoutRefresh = null;
  var boundShopifyLoad = null;
  var boundStackReady = null;
  var boundLoad = null;

  function refreshSections(force) {
    collectSections();
    if (sections.length < 2) {
      canonicalDockCache = [];
      frozenSectionIds = [];
      return;
    }

    var ids = currentSectionIds();
    var hasValidCache = isValidDockCache(canonicalDockCache, sections.length);
    var sameSections =
      frozenSectionIds.length === ids.length && sectionIdsEqual(frozenSectionIds, ids);

    if (!force && hasValidCache && sameSections) {
      debugLog('refreshSections: keeping frozen canonicalDockCache');
      return;
    }

    rebuildCanonicalDock(!!force || !hasValidCache || !sameSections);
  }

  function init() {
    collectSections();
    if (sections.length < 2) {
      debugLog('mniej niż 2 sekcje — moduł nieaktywny');
      return;
    }

    root.dataset.gicleeHomeSectionScroll = 'on';
    root.classList.add('giclee-home-section-scroll');

    boundLayoutRefresh = function () {
      refreshSections(true);
    };
    boundShopifyLoad = function () {
      refreshSections(true);
    };
    boundStackReady = function () {
      refreshSections(false);
    };
    boundLoad = function () {
      if (!isValidDockCache(canonicalDockCache, sections.length)) {
        refreshSections(false);
      }
    };

    window.addEventListener('resize', boundLayoutRefresh, { passive: true });
    window.addEventListener('orientationchange', boundLayoutRefresh, { passive: true });
    window.addEventListener('load', boundLoad, { passive: true });
    document.addEventListener('shopify:section:load', boundShopifyLoad);
    window.addEventListener('giclee:home-stack-ready', boundStackReady, { passive: true });

    if (!window.GICLEE_HOME_STACK || root.classList.contains('giclee-home-stack-ready')) {
      refreshSections();
    } else {
      requestAnimationFrame(function () {
        if (canonicalDockCache.length < 2) refreshSections();
      });
    }

    if (touchContext) {
      boundSoftScroll = onSoftScroll;
      window.addEventListener('scroll', boundSoftScroll, { passive: true });
    } else {
      boundWheel = onWheel;
      boundKeydown = onKeydown;
      window.addEventListener('wheel', boundWheel, { passive: false });
      window.addEventListener('keydown', boundKeydown);
    }

    debugLog('aktywny', { sections: sections.length, touchContext: touchContext, cfg: cfg });
  }

  function destroy() {
    cancelAnimation();
    clearTimeout(quietTimer);
    clearTimeout(accumResetTimer);
    clearTimeout(softTimer);
    if (boundWheel) window.removeEventListener('wheel', boundWheel);
    if (boundKeydown) window.removeEventListener('keydown', boundKeydown);
    if (boundSoftScroll) window.removeEventListener('scroll', boundSoftScroll);
    if (boundLayoutRefresh) {
      window.removeEventListener('resize', boundLayoutRefresh);
      window.removeEventListener('orientationchange', boundLayoutRefresh);
    }
    if (boundLoad) window.removeEventListener('load', boundLoad);
    if (boundShopifyLoad) {
      document.removeEventListener('shopify:section:load', boundShopifyLoad);
    }
    if (boundStackReady) {
      window.removeEventListener('giclee:home-stack-ready', boundStackReady);
    }
    delete root.dataset.gicleeHomeSectionScroll;
    root.classList.remove('giclee-home-section-scroll');
  }

  window.GICLEE_HOME_SECTION_SCROLL = {
    destroy: destroy,
    refresh: function (force) {
      refreshSections(!!force);
    },
    debug: function () {
      var positions = dockPositions();
      var scrollY = getScrollY();
      var assertFailures = runDebugAsserts(positions);
      var rows = sections.map(function (el, i) {
        var canonical = positions[i];
        var liveDock = resolveDockScrollY(el);
        var nextCanonical = i < sections.length - 1 ? positions[i + 1] : null;
        return {
          index: i,
          id: el.id,
          canonicalDock: canonical,
          liveDock: liveDock,
          runwayUpper: nextCanonical,
          deltaToCanonical: scrollY - canonical,
          runwayFromCanonical: scrollY - canonical,
          deltaUp: i > 0 ? scrollY - positions[i - 1] : null,
          deltaDown: nextCanonical !== null ? nextCanonical - scrollY : null,
        };
      });
      var navIdx = activeSectionIndexForNavigation(scrollY, positions);
      var visualIdx = viewportSectionIndex();
      var scrollIdx = navIdx;
      var duplicateDocks = findDuplicateDocks(positions);
      var runwayDist =
        navIdx >= 0 && navIdx < positions.length ? scrollY - positions[navIdx] : null;
      var targetUp = resolveTargetForDirection(scrollY, -1);
      var targetDown = resolveTargetForDirection(scrollY, 1);
      var targetUpScrollY =
        targetUp !== null && targetUp >= 0
          ? resolveScrollUpTargetY(targetUp, scrollY)
          : null;
      var targetDownScrollY =
        targetDown !== null && targetDown >= 0 ? positions[targetDown] : null;
      var snapshot = {
        cfg: cfg,
        touchContext: touchContext,
        animating: animating,
        waitingForQuiet: waitingForQuiet,
        lastNavDirection: lastNavDirection,
        motionDynamics: cfg.motionDynamics,
        durationScale: durationScale(),
        scrollY: scrollY,
        stopOffset: stopOffset(),
        frozenSectionIds: frozenSectionIds.slice(),
        positions: positions.slice(),
        assertFailures: assertFailures,
        assertOk: assertFailures.length === 0,
        navIdx: navIdx,
        activeIdx: navIdx,
        scrollIdx: scrollIdx,
        visualIdx: visualIdx,
        viewportIdx: visualIdx,
        navVsVisual: navIdx !== visualIdx ? { navIdx: navIdx, visualIdx: visualIdx } : null,
        duplicateDocks: duplicateDocks,
        hasDuplicateDocks: duplicateDocks.length > 0,
        runwayDist: runwayDist,
        targetUp: targetUp,
        targetUpScrollY: targetUpScrollY,
        expectedDeltaUp:
          targetUpScrollY !== null ? targetUpScrollY - scrollY : null,
        targetDown: targetDown,
        targetDownScrollY: targetDownScrollY,
        sections: rows,
      };
      console.table(rows);
      console.log('[giclee-section-scroll]', snapshot);
      if (assertFailures.length) {
        console.warn('[giclee-section-scroll] assert failures', assertFailures);
      }
      console.log('[giclee-section-scroll] summary', {
        scrollY: scrollY,
        positions: positions,
        navIdx: navIdx,
        visualIdx: visualIdx,
        scrollIdx: scrollIdx,
        runwayDist: runwayDist,
        hasDuplicateDocks: duplicateDocks.length > 0,
        duplicateDocks: duplicateDocks,
        visualAheadOfNav:
          visualIdx > navIdx &&
          visualIdx < positions.length &&
          scrollY < positions[visualIdx] - NAV_TOLERANCE,
        microRunwaySkip:
          runwayDist !== null && runwayDist > 2 && runwayDist < MIN_ANIM_PX,
        targetUp: targetUp,
        targetUpScrollY: targetUpScrollY,
        expectedDeltaUp: snapshot.expectedDeltaUp,
        targetDown: targetDown,
        targetDownScrollY: targetDownScrollY,
      });
      return snapshot;
    },
    /** API dla Playwright (gpt-record-preview) — te same animacje co wheel/PageDown. */
    sectionCount: function () {
      return sections.length;
    },
    isNavigationIdle: function () {
      return !animating && !waitingForQuiet;
    },
    maxAnimMs: function () {
      return Math.round(cfg.maxDuration * durationScale()) + QUIET_MS + 400;
    },
    stepDown: function () {
      if (sections.length < 2 || canonicalDockCache.length < 2) return false;
      if (animating) return false;
      waitingForQuiet = false;
      accum = 0;
      return navigateByDirection(1);
    },
    goToSection: function (index) {
      if (index < 0 || index >= sections.length) return false;
      if (animating) return false;
      waitingForQuiet = false;
      accum = 0;
      var scrollY = getScrollY();
      var current = activeSectionIndexForNavigation(scrollY, canonicalDockCache);
      var direction = index >= current ? 1 : -1;
      return goToIndex(index, direction);
    },
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
