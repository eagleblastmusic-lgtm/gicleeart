/* GicleeApp — runtime warstw tekstowych. Bez GSAP i bez wykonywania kodu importowanego. */

(function () {
  'use strict';

  var config = window.GICLEE_TEXT_LAYERS;
  if (!config || !config.sections || typeof config.sections !== 'object') return;

  var EASING = {
    museum: 'cubic-bezier(0.16, 1, 0.3, 1)',
    soft: 'cubic-bezier(0.25, 1, 0.5, 1)',
    crisp: 'cubic-bezier(0.22, 1, 0.36, 1)',
    linear: 'linear'
  };
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var managedSections = [];
  var scheduled = false;
  var activeBreakpoint = window.innerWidth <= 749 ? 'mobile' : window.innerWidth <= 989 ? 'tablet' : 'desktop';

  function sectionElement(key) {
    var direct = document.getElementById('shopify-section-' + key);
    if (direct) return direct;
    var suffix = '__' + key;
    var rows = document.querySelectorAll('[id^="shopify-section-"]');
    for (var index = 0; index < rows.length; index += 1) {
      var id = rows[index].id || '';
      if (id.slice(-suffix.length) === suffix) return rows[index];
    }
    return null;
  }

  function unitValue(raw, fallback) {
    if (!raw || typeof raw !== 'object') return fallback;
    var value = Number(raw.value);
    if (!isFinite(value)) return fallback;
    var unit = ['px', '%', 'vw', 'vh'].indexOf(raw.unit) >= 0 ? raw.unit : 'px';
    return String(value) + unit;
  }

  function effectiveLayout(layer) {
    var layout = layer.layout || {};
    var result = layout.desktop || {};
    if (window.innerWidth <= 989 && layout.tablet) result = layout.tablet;
    if (window.innerWidth <= 749 && layout.mobile) result = layout.mobile;
    return result || {};
  }

  function effectivePin(layer) {
    var pin = layer.pin || {};
    var desktop = pin.desktop || {};
    if (window.innerWidth > 749) return desktop;
    var mobile = pin.mobile || {};
    var mode = mobile.mode || 'inherit';
    if (mode === 'off') return { enabled: false, durationVh: 0, top: mobile.top };
    if (mode === 'on') {
      return {
        enabled: true,
        durationVh: Number(desktop.durationVh) || 100,
        startVh: Number(desktop.startVh) || 0,
        top: mobile.top || desktop.top
      };
    }
    if (mode === 'custom') {
      return {
        enabled: true,
        durationVh: Number(mobile.durationVh) || 0,
        startVh: 0,
        top: mobile.top
      };
    }
    return desktop;
  }

  function anchorValues(anchor) {
    var parts = String(anchor || 'top-left').split('-');
    var vertical = parts.length === 1 && parts[0] === 'center' ? 'center' : parts[0];
    var horizontal = parts.length === 1 ? 'center' : parts[1];
    var left = horizontal === 'right' ? '100%' : horizontal === 'center' ? '50%' : '0';
    var top = vertical === 'bottom' ? '100%' : vertical === 'center' ? '50%' : '0';
    var tx = horizontal === 'right' ? '-100%' : horizontal === 'center' ? '-50%' : '0';
    var ty = vertical === 'bottom' ? '-100%' : vertical === 'center' ? '-50%' : '0';
    return { left: left, top: top, tx: tx, ty: ty };
  }

  function applyLayout(record) {
    var layer = record.layer;
    var root = record.root;
    var values = effectiveLayout(layer);
    var pin = effectivePin(layer);
    var anchor = anchorValues(values.anchor);
    root.style.setProperty(
      '--gtext-max-width',
      record.componentMode ? 'none' : unitValue(values.maxWidth, '720px')
    );
    root.style.setProperty(
      '--gtext-padding',
      record.componentMode ? '0px' : unitValue(values.padding, '0px')
    );
    root.style.setProperty(
      '--gtext-align',
      record.componentMode ? 'left' : (values.align || 'left')
    );
    root.style.setProperty('--gtext-z', String(Number(values.zIndex) || 20));
    root.style.setProperty('--gtext-left', anchor.left);
    root.style.setProperty('--gtext-top', anchor.top);
    root.style.setProperty('--gtext-anchor-x', anchor.tx);
    root.style.setProperty('--gtext-anchor-y', anchor.ty);
    root.style.setProperty('--gtext-offset-x', unitValue(values.offsetX, '0px'));
    root.style.setProperty('--gtext-offset-y', unitValue(values.offsetY, '0px'));
    root.style.setProperty('--gtext-pin-top', unitValue(pin.top, '0px'));
    if (record.pinTrack) {
      var pinStart = Math.max(0, Number(pin.startVh) || 0);
      var pinEnd =
        pin.endVh == null
          ? pinStart + Math.max(0, Number(pin.durationVh) || 0)
          : Math.max(pinStart, Number(pin.endVh) || 0);
      record.pinTrack.style.top = String(pinStart) + 'vh';
      record.pinTrack.style.height =
        'calc(100vh + ' + String(Math.max(0, pinEnd - pinStart)) + 'vh)';
    }
    root.style.setProperty(
      '--gtext-enter-duration',
      String(Math.max(0.1, Number((layer.motion || {}).enter && layer.motion.enter.duration) || 0.8) * 1000) + 'ms'
    );
    root.style.setProperty(
      '--gtext-enter-delay',
      String(Math.max(0, Number((layer.motion || {}).enter && layer.motion.enter.delay) || 0) * 1000) + 'ms'
    );
    root.style.setProperty(
      '--gtext-stagger',
      String(Math.max(0, Number((layer.motion || {}).enter && layer.motion.enter.stagger) || 0.04) * 1000) + 'ms'
    );
    root.style.setProperty(
      '--gtext-ease',
      EASING[((layer.motion || {}).enter || {}).easing] || EASING.museum
    );
  }

  function semanticElement(kind) {
    if (kind === 'h1' || kind === 'h2' || kind === 'h3') return kind;
    if (kind === 'quote') return 'blockquote';
    if (kind === 'signature') return 'cite';
    if (kind === 'eyebrow') return 'span';
    return 'p';
  }

  function splitStagger(content, enter) {
    if (!enter || enter.preset !== 'letter-spacing-reveal') return;
    var mode = enter.staggerMode || 'characters';
    if (mode === 'none' || content.children.length) return;
    var original = content.textContent || '';
    content.setAttribute('aria-label', original);
    content.textContent = '';
    var units = mode === 'words' ? original.split(/(\s+)/) : Array.from(original);
    units.forEach(function (unit, index) {
      if (/^\s+$/.test(unit)) {
        content.appendChild(document.createTextNode(unit));
        return;
      }
      var span = document.createElement('span');
      span.className = 'giclee-text-layer__stagger-unit';
      span.setAttribute('aria-hidden', 'true');
      span.style.setProperty('--gtext-stagger-index', String(index));
      span.textContent = unit;
      content.appendChild(span);
    });
  }

  function initialFrame(preset, motion) {
    var distance = (Number(motion.distance) || 32) * (Number(motion.intensity) || 1);
    var blur = (Number(motion.blur) || 12) * (Number(motion.intensity) || 1);
    var frame = { opacity: 0, transform: 'none', filter: 'none', clipPath: 'inset(0)' };
    if (preset === 'fade-up') frame.transform = 'translate3d(0,' + distance + 'px,0)';
    if (preset === 'fade-down') frame.transform = 'translate3d(0,' + -distance + 'px,0)';
    if (preset === 'slide-left') frame.transform = 'translate3d(' + distance + 'px,0,0)';
    if (preset === 'slide-right') frame.transform = 'translate3d(' + -distance + 'px,0,0)';
    if (preset === 'soft-blur-reveal') {
      frame.transform = 'translate3d(0,' + distance * 0.65 + 'px,0)';
      frame.filter = 'blur(' + blur + 'px)';
    }
    if (preset === 'gentle-scale-in') frame.transform = 'scale(' + (1 - 0.035 * (Number(motion.intensity) || 1)) + ')';
    if (preset === 'mask-reveal') frame.clipPath = 'inset(0 0 100% 0)';
    if (preset === 'letter-spacing-reveal') {
      frame.opacity = 1;
      frame.filter = 'blur(' + Math.min(blur, 8) + 'px)';
    }
    if (preset === 'none') frame.opacity = 1;
    return frame;
  }

  function exitFrame(preset, motion) {
    var distance = (Number(motion.distance) || 32) * (Number(motion.intensity) || 1);
    var blur = (Number(motion.blur) || 16) * (Number(motion.intensity) || 1);
    var frame = { opacity: 0, transform: 'none', filter: 'none', clipPath: 'inset(0)' };
    if (preset === 'fade-up-out') frame.transform = 'translate3d(0,' + -distance + 'px,0)';
    if (preset === 'fade-down-out') frame.transform = 'translate3d(0,' + distance + 'px,0)';
    if (preset === 'slide-left-out') frame.transform = 'translate3d(' + -distance + 'px,0,0)';
    if (preset === 'slide-right-out') frame.transform = 'translate3d(' + distance + 'px,0,0)';
    if (preset === 'blur-away') frame.filter = 'blur(' + blur + 'px)';
    if (preset === 'gentle-scale-out') frame.transform = 'scale(' + (1 + 0.04 * (Number(motion.intensity) || 1)) + ')';
    if (preset === 'mask-close') frame.clipPath = 'inset(100% 0 0 0)';
    return frame;
  }

  function cancelAnimation(record) {
    if (record.animation) {
      record.animation.cancel();
      record.animation = null;
    }
  }

  function animateState(record, state) {
    if (record.state === state) return;
    record.state = state;
    var computed = getComputedStyle(record.motion);
    var current = {
      opacity: computed.opacity,
      transform: computed.transform === 'none' ? 'none' : computed.transform,
      filter: computed.filter === 'none' ? 'none' : computed.filter,
      clipPath: computed.clipPath === 'none' ? 'inset(0)' : computed.clipPath
    };
    cancelAnimation(record);
    var enter = ((record.layer.motion || {}).enter || {});
    var exit = ((record.layer.motion || {}).exit || {});
    if (record.ownsMotion) {
      enter = {
        preset: 'none',
        duration: 0.1,
        delay: 0,
        easing: 'linear'
      };
      exit = { preset: 'none' };
    }
    var visible = { opacity: 1, transform: 'none', filter: 'none', clipPath: 'inset(0)' };
    var from = initialFrame(enter.preset || 'fade-up', enter);
    var target = visible;
    var timing = {
      duration: Math.max(100, Number(enter.duration || 0.8) * 1000),
      delay: Math.max(0, Number(enter.delay || 0) * 1000),
      easing: EASING[enter.easing] || EASING.museum,
      fill: 'forwards'
    };

    if (state === 'hidden') {
      record.motion.getAnimations().forEach(function (animation) { animation.cancel(); });
      Object.keys(from).forEach(function (key) { record.motion.style[key] = from[key]; });
      record.root.classList.remove('is-entered', 'is-exited');
      return;
    }
    var frames = [current, target];
    if (state === 'exited' && exit.preset !== 'none') {
      target = exitFrame(exit.preset, exit);
      frames = [current, target];
      timing.duration = Math.max(100, Number(exit.duration || 0.6) * 1000);
      timing.delay = 0;
      timing.easing = EASING[exit.easing] || EASING.museum;
      record.root.classList.add('is-exited');
      record.root.classList.remove('is-entered');
    } else {
      record.root.classList.add('is-entered');
      record.root.classList.remove('is-exited');
    }
    if (reducedMotion.matches || !record.motion.animate) {
      Object.keys(target).forEach(function (key) { record.motion.style[key] = target[key]; });
      return;
    }
    record.animation = record.motion.animate(frames, timing);
  }

  function loadFonts(fonts) {
    (fonts || []).forEach(function (url) {
      if (typeof url !== 'string' || url.indexOf('https://fonts.googleapis.com/') !== 0) return;
      var alreadyLoaded = Array.prototype.some.call(
        document.querySelectorAll('link[data-giclee-text-font]'),
        function (node) { return node.getAttribute('data-giclee-text-font') === url; }
      );
      if (alreadyLoaded) return;
      var link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = url;
      link.setAttribute('data-giclee-text-font', url);
      document.head.appendChild(link);
    });
  }

  function addImportedStyle(layer) {
    var styleConfig = layer.importedStyle || {};
    loadFonts(styleConfig.fontUrls);
    if (!styleConfig.scopedCss) return;
    var id = 'giclee-text-style-' + layer.id;
    if (document.getElementById(id)) return;
    var style = document.createElement('style');
    style.id = id;
    style.textContent = String(styleConfig.scopedCss);
    document.head.appendChild(style);
  }

  function makeLayer(section, layer, hosts) {
    var root = document.createElement('div');
    root.className = 'giclee-text-layer';
    root.setAttribute('data-giclee-text-layer-id', layer.id);
    root.setAttribute('data-giclee-text-layer-name', layer.name || '');
    var styleConfig = layer.importedStyle || {};
    var componentMode =
      (layer.content || {}).mode === 'adapted-code' &&
      styleConfig.componentMode === true;
    if (componentMode) {
      root.classList.add('giclee-text-layer--component');
    }

    var motion = document.createElement('div');
    motion.className = 'giclee-text-layer__motion';
    var contentConfig = layer.content || {};
    var content;
    if (contentConfig.mode === 'adapted-code' && contentConfig.html) {
      content = document.createElement('div');
      content.className = 'giclee-text-layer__content giclee-text-layer__content--adapted';
      content.innerHTML = String(contentConfig.html);
    } else {
      content = document.createElement(semanticElement(contentConfig.kind));
      content.className =
        'giclee-text-layer__content giclee-text-layer__content--' +
        String(contentConfig.kind || 'paragraph');
      content.textContent = String(contentConfig.text || '');
    }
    motion.appendChild(content);
    root.appendChild(motion);
    addImportedStyle(layer);
    splitStagger(content, ((layer.motion || {}).enter || {}));

    var pin = effectivePin(layer);
    var pinTrack = null;
    if (pin.enabled && !reducedMotion.matches) {
      root.classList.add('giclee-text-layer--pin');
      pinTrack = document.createElement('div');
      pinTrack.className = 'giclee-text-layer__pin-track';
      pinTrack.appendChild(root);
      hosts.pin.appendChild(pinTrack);
    } else if (componentMode || (layer.layout || {}).mode === 'absolute') {
      root.classList.add('giclee-text-layer--absolute');
      hosts.overlay.appendChild(root);
    } else {
      root.classList.add('giclee-text-layer--flow');
      hosts.flow.appendChild(root);
    }
    var record = {
      section: section,
      layer: layer,
      root: root,
      motion: motion,
      triggerElement: content.firstElementChild || content,
      componentMode: componentMode,
      ownsMotion: styleConfig.ownsMotion === true,
      behavior: styleConfig.behavior || {},
      hasEntered: false,
      pinTrack: pinTrack,
      state: '',
      animation: null
    };
    applyLayout(record);
    animateState(record, 'hidden');
    return record;
  }

  function prepareSection(key, layers) {
    var section = sectionElement(key);
    var readyToken = String(config.variant || 'ready');
    if (!section || section.getAttribute('data-giclee-text-ready') === readyToken) return;
    section.setAttribute('data-giclee-text-ready', readyToken);
    if (getComputedStyle(section).position === 'static') section.style.position = 'relative';
    section.style.isolation = 'isolate';
    var naturalHeight = section.getBoundingClientRect().height;
    var originalMinHeight = section.style.minHeight;

    var flow = document.createElement('div');
    flow.className = 'giclee-text-flow-host';
    var overlay = document.createElement('div');
    overlay.className = 'giclee-text-overlay-host';
    var pin = document.createElement('div');
    pin.className = 'giclee-text-pin-host';
    section.appendChild(flow);
    section.appendChild(overlay);
    section.appendChild(pin);

    var records = [];
    var maxRunwayVh = 0;
    (layers || []).forEach(function (layer) {
      if (!layer || layer.enabled === false) return;
      var pinCfg = effectivePin(layer);
      if (pinCfg.enabled && !reducedMotion.matches) {
        var start = Math.max(0, Number(pinCfg.startVh) || 0);
        var duration = Math.max(0, Number(pinCfg.durationVh) || 0);
        var end = pinCfg.endVh == null ? start + duration : Math.max(start, Number(pinCfg.endVh) || 0);
        maxRunwayVh = Math.max(maxRunwayVh, end);
      }
      records.push(makeLayer(section, layer, { flow: flow, overlay: overlay, pin: pin }));
    });
    if (maxRunwayVh > 0) {
      section.style.minHeight =
        String(
          Math.ceil(
            Math.max(naturalHeight, window.innerHeight) +
            window.innerHeight * maxRunwayVh / 100
          )
        ) + 'px';
    }
    managedSections.push({
      section: section,
      records: records,
      naturalHeight: naturalHeight,
      originalMinHeight: originalMinHeight,
      hosts: [flow, overlay, pin]
    });
  }

  function marginPixels(token, viewport) {
    var value = parseFloat(token);
    if (!isFinite(value)) return 0;
    return String(token).indexOf('%') >= 0
      ? viewport * value / 100
      : value;
  }

  function rootMarginValues(raw, viewport) {
    var parts = String(raw || '0px').trim().split(/\s+/);
    if (parts.length === 1) parts = [parts[0], parts[0], parts[0], parts[0]];
    if (parts.length === 2) parts = [parts[0], parts[1], parts[0], parts[1]];
    if (parts.length === 3) parts = [parts[0], parts[1], parts[2], parts[1]];
    return {
      top: marginPixels(parts[0] || '0px', viewport),
      bottom: marginPixels(parts[2] || '0px', viewport)
    };
  }

  function componentIntersectionReached(record, behavior, viewport) {
    var target = record.triggerElement || record.root;
    var rect = target.getBoundingClientRect();
    if (!rect.height || !rect.width) return false;
    var margins = rootMarginValues(behavior.rootMargin, viewport);
    var rootTop = -margins.top;
    var rootBottom = viewport + margins.bottom;
    var intersection = Math.max(
      0,
      Math.min(rect.bottom, rootBottom) - Math.max(rect.top, rootTop)
    );
    var ratio = Math.max(0, Math.min(1, intersection / rect.height));
    var threshold = Math.max(
      0,
      Math.min(1, Number(behavior.threshold) || 0)
    );
    return ratio >= threshold;
  }

  function update() {
    scheduled = false;
    var viewport = window.innerHeight || document.documentElement.clientHeight || 1;
    managedSections.forEach(function (group) {
      var rect = group.section.getBoundingClientRect();
      var progress = Math.max(0, Math.min(1, (viewport - rect.top) / (viewport + rect.height)));
      group.records.forEach(function (record) {
        applyLayout(record);
        if (reducedMotion.matches) {
          animateState(record, 'entered');
          return;
        }
        var behavior = record.behavior || {};
        if (record.componentMode && behavior.trigger === 'intersection') {
          var componentVisible = componentIntersectionReached(
            record,
            behavior,
            viewport
          );
          if (componentVisible) {
            record.hasEntered = true;
            animateState(record, 'entered');
          } else if (behavior.once && record.hasEntered) {
            animateState(record, 'entered');
          } else {
            animateState(record, 'hidden');
          }
          return;
        }
        var exit = ((record.layer.motion || {}).exit || {});
        var exitStart = Math.max(0, Math.min(1, Number(exit.startPct == null ? 80 : exit.startPct) / 100));
        if (progress < 0.08) {
          animateState(record, 'hidden');
        } else if (exit.preset !== 'none' && progress >= exitStart) {
          animateState(record, 'exited');
        } else {
          animateState(record, 'entered');
        }
      });
    });
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(update);
  }

  function initialize() {
    managedSections = managedSections.filter(function (group) {
      return group.section.isConnected;
    });
    Object.keys(config.sections).forEach(function (key) {
      prepareSection(key, config.sections[key]);
    });
    schedule();
  }

  function rebuild() {
    managedSections.forEach(function (group) {
      group.records.forEach(cancelAnimation);
      group.hosts.forEach(function (host) { host.remove(); });
      group.section.style.minHeight = group.originalMinHeight;
      group.section.removeAttribute('data-giclee-text-ready');
    });
    managedSections = [];
    initialize();
  }

  function handleResize() {
    var nextBreakpoint = window.innerWidth <= 749 ? 'mobile' : window.innerWidth <= 989 ? 'tablet' : 'desktop';
    if (nextBreakpoint !== activeBreakpoint) {
      activeBreakpoint = nextBreakpoint;
      rebuild();
      return;
    }
    schedule();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', handleResize, { passive: true });
  reducedMotion.addEventListener && reducedMotion.addEventListener('change', rebuild);
  document.addEventListener('shopify:section:load', initialize);
})();
