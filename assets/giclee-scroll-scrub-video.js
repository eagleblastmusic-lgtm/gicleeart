(() => {
  'use strict';

  const API_KEY = 'GicleeScrollFrameCanvas';
  const ROOT_SELECTOR = '.media-block--scroll-scrub';
  const CANVAS_SELECTOR = '[data-scroll-frame-canvas]';
  const VIDEO_SELECTOR = '[data-scroll-native-video]';
  const SECTION_MEDIA_END_PROGRESS = 0.8;
  const INTRO_EXIT_PROGRESS = 0.18;
  const STOP_DELAY_MS = 90;
  const MAX_SETTLE_MS = 1200;
  const MAX_SEQUENTIAL_WEBM_CATCHUP_SECONDS = 0.32;
  const ALPHA_WEBM_MAX_SEQUENTIAL_CATCHUP_SECONDS = 1.25;
  const ALPHA_WEBM_MIN_PLAYBACK_RATE = 0.25;
  const ALPHA_WEBM_MAX_PLAYBACK_RATE = 1;
  const PAGE_PARAMS = new URL(document.URL).searchParams;
  const DEBUG = PAGE_PARAMS.get('giclee_frames_debug') === '1';
  const DEBUG_PRESET = DEBUG
    ? PAGE_PARAMS.get('giclee_motion_preset') || ''
    : '';
  const DEBUG_REDUCED_MOTION =
    DEBUG && PAGE_PARAMS.get('giclee_reduced_motion') === '1';
  const ALPHA_DEBUG_QUERY = PAGE_PARAMS.get('giclee_alpha_debug') === '1';

  const clamp = (value, min = 0, max = 1) =>
    Math.min(Math.max(value, min), max);
  const finite = (value, fallback) => {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  };
  const bool = (value, fallback = false) => {
    if (value == null || value === '') return fallback;
    return String(value).toLowerCase() === 'true';
  };
  const moveTowards = (current, target, maxDelta) => {
    const difference = target - current;
    if (Math.abs(difference) <= maxDelta) return target;
    return current + Math.sign(difference) * maxDelta;
  };
  const mapProgress = (progress, start, end) =>
    end <= start ? 0 : clamp((progress - start) / (end - start));

  const DIRECT_PRESET = Object.freeze({
    label: 'Bezpośredni 1:1',
    speed: 1,
    easing: 'linear',
    bezier: '0.25,0.10,0.25,1.00',
    smoothingMs: 0,
    lagMs: 0,
    inertia: 0,
    damping: 100,
    maxCatchUpPerSecond: 0,
    stopBehavior: 'immediate',
    snapPoints: 5,
    direction: 'normal',
    materialStart: 0,
    materialEnd: 100,
    interpolation: 'none',
    frameRounding: 'round',
    mp4DeadZoneMs: 4,
    webpDeadZoneFrames: 1,
    preloadRadius: 12,
    cacheFrames: 0,
    tailPacing: false,
    tailWindowFrames: 12,
  });

  let motionCatalog = {
    version: 0,
    recommended: { video: 'direct', frames: 'direct' },
    presets: { direct: DIRECT_PRESET },
  };
  let catalogStatus = 'fallback';
  let catalogPromise = null;
  let runtimeStarted = false;

  async function loadMotionCatalog() {
    if (catalogPromise) return catalogPromise;
    const url = document.querySelector('[data-motion-presets-url]')?.dataset
      .motionPresetsUrl;
    if (!url) return motionCatalog;
    catalogPromise = fetch(url, {
      cache: 'force-cache',
      credentials: 'same-origin',
    })
      .then((response) => {
        if (!response.ok) throw new Error('Motion preset catalog failed');
        return response.json();
      })
      .then((catalog) => {
        if (!catalog?.presets?.direct) throw new Error('Invalid motion catalog');
        motionCatalog = catalog;
        catalogStatus = 'loaded';
        return catalog;
      })
      .catch(() => {
        catalogStatus = 'fallback';
        return motionCatalog;
      });
    return catalogPromise;
  }

  function parseBezier(raw) {
    const values = String(raw || '')
      .split(',')
      .map((value) => Number.parseFloat(value.trim()));
    if (
      values.length !== 4 ||
      values.some((value) => !Number.isFinite(value)) ||
      values[0] < 0 ||
      values[0] > 1 ||
      values[2] < 0 ||
      values[2] > 1
    ) {
      return [0.25, 0.1, 0.25, 1];
    }
    return values;
  }

  function cubicBezierAt(progress, points) {
    const [x1, y1, x2, y2] = points;
    const sample = (t, a1, a2) => {
      const c = 3 * a1;
      const b = 3 * (a2 - a1) - c;
      const a = 1 - c - b;
      return ((a * t + b) * t + c) * t;
    };
    const slope = (t, a1, a2) => {
      const c = 3 * a1;
      const b = 3 * (a2 - a1) - c;
      const a = 1 - c - b;
      return 3 * a * t * t + 2 * b * t + c;
    };
    let t = progress;
    for (let index = 0; index < 5; index += 1) {
      const error = sample(t, x1, x2) - progress;
      const currentSlope = slope(t, x1, x2);
      if (Math.abs(error) < 1e-6 || Math.abs(currentSlope) < 1e-6) break;
      t = clamp(t - error / currentSlope);
    }
    let low = 0;
    let high = 1;
    for (let index = 0; index < 8; index += 1) {
      const x = sample(t, x1, x2);
      if (Math.abs(x - progress) < 1e-6) break;
      if (x < progress) low = t;
      else high = t;
      t = (low + high) / 2;
    }
    return sample(t, y1, y2);
  }

  function applyEasing(progress, easing, bezier) {
    const value = clamp(progress);
    switch (easing) {
      case 'ease-in':
        return value * value;
      case 'ease-out':
        return 1 - (1 - value) ** 3;
      case 'ease-in-out':
      case 'cubic-in-out':
        return value < 0.5
          ? 4 * value ** 3
          : 1 - (-2 * value + 2) ** 3 / 2;
      case 'sine-in-out':
        return -(Math.cos(Math.PI * value) - 1) / 2;
      case 'quad-in-out':
        return value < 0.5
          ? 2 * value * value
          : 1 - (-2 * value + 2) ** 2 / 2;
      case 'quart-in-out':
        return value < 0.5
          ? 8 * value ** 4
          : 1 - (-2 * value + 2) ** 4 / 2;
      case 'expo-in-out':
        if (value === 0 || value === 1) return value;
        return value < 0.5
          ? 2 ** (20 * value - 10) / 2
          : (2 - 2 ** (-20 * value + 10)) / 2;
      case 'smoothstep':
        return value * value * (3 - 2 * value);
      case 'smootherstep':
        return value ** 3 * (value * (value * 6 - 15) + 10);
      case 'custom-bezier':
        return cubicBezierAt(value, bezier);
      default:
        return value;
    }
  }

  function readMotionConfig(root) {
    const dataset = root.dataset;
    const presetId = DEBUG_PRESET || dataset.motionPreset || 'direct';
    const preset =
      presetId !== 'custom' && motionCatalog.presets[presetId]
        ? motionCatalog.presets[presetId]
        : null;
    const pick = (datasetKey, presetKey, fallback) => {
      if (preset && preset[presetKey] != null) return preset[presetKey];
      return dataset[datasetKey] ?? fallback;
    };
    const easingValues = new Set([
      'linear',
      'ease-in',
      'ease-out',
      'ease-in-out',
      'sine-in-out',
      'quad-in-out',
      'cubic-in-out',
      'quart-in-out',
      'expo-in-out',
      'smoothstep',
      'smootherstep',
      'custom-bezier',
    ]);
    const interpolationValues = new Set([
      'none',
      'linear',
      'exponential',
      'damp',
      'spring',
      'velocity',
    ]);
    const stopValues = new Set([
      'immediate',
      'reach',
      'nearest-frame',
      'decelerate',
      'snap',
    ]);
    const easing = String(pick('motionEasing', 'easing', 'linear'));
    const interpolation = String(
      pick('motionInterpolation', 'interpolation', 'none')
    );
    const stopBehavior = String(
      pick('motionStopBehavior', 'stopBehavior', 'immediate')
    );
    let materialStart = clamp(
      finite(pick('motionMaterialStart', 'materialStart', 0), 0) / 100
    );
    let materialEnd = clamp(
      finite(pick('motionMaterialEnd', 'materialEnd', 100), 100) / 100
    );
    if (materialEnd <= materialStart) {
      materialStart = 0;
      materialEnd = 1;
    }
    return {
      preset: preset ? presetId : presetId === 'custom' ? 'custom' : 'direct',
      speed: clamp(finite(pick('motionSpeed', 'speed', 1), 1), 0.25, 3),
      easing: easingValues.has(easing) ? easing : 'linear',
      bezier: parseBezier(pick('motionBezier', 'bezier', DIRECT_PRESET.bezier)),
      smoothingMs: clamp(
        finite(pick('motionSmoothingMs', 'smoothingMs', 0), 0),
        0,
        1000
      ),
      lagMs: clamp(finite(pick('motionLagMs', 'lagMs', 0), 0), 0, 500),
      inertia: clamp(
        finite(pick('motionInertia', 'inertia', 0), 0),
        0,
        100
      ),
      damping: clamp(
        finite(pick('motionDamping', 'damping', 100), 100),
        0,
        100
      ),
      maxCatchUpPerSecond: clamp(
        finite(pick('motionMaxCatchup', 'maxCatchUpPerSecond', 0), 0),
        0,
        8
      ),
      stopBehavior: stopValues.has(stopBehavior) ? stopBehavior : 'immediate',
      snapPoints: Math.round(
        clamp(finite(pick('motionSnapPoints', 'snapPoints', 5), 5), 2, 20)
      ),
      direction:
        String(pick('motionDirection', 'direction', 'normal')) === 'reverse'
          ? 'reverse'
          : 'normal',
      materialStart,
      materialEnd,
      interpolation: interpolationValues.has(interpolation)
        ? interpolation
        : 'none',
      frameRounding: ['floor', 'round', 'ceil'].includes(
        String(pick('motionFrameRounding', 'frameRounding', 'round'))
      )
        ? String(pick('motionFrameRounding', 'frameRounding', 'round'))
        : 'round',
      mp4DeadZoneMs: clamp(
        finite(pick('motionMp4DeadZoneMs', 'mp4DeadZoneMs', 4), 4),
        0,
        100
      ),
      webpDeadZoneFrames: Math.round(
        clamp(
          finite(
            pick('motionWebpDeadZoneFrames', 'webpDeadZoneFrames', 1),
            1
          ),
          0,
          10
        )
      ),
      preloadRadius: Math.round(
        clamp(
          finite(pick('motionPreloadRadius', 'preloadRadius', 12), 12),
          2,
          60
        )
      ),
      cacheFrames: Math.round(
        clamp(
          finite(pick('motionCacheFrames', 'cacheFrames', 0), 0),
          0,
          120
        )
      ),
      tailPacing: bool(
        pick('motionTailPacing', 'tailPacing', false),
        false
      ),
      tailWindowFrames: Math.round(
        clamp(
          finite(
            pick('motionTailWindowFrames', 'tailWindowFrames', 12),
            12
          ),
          2,
          30
        )
      ),
      preserveAlpha: bool(dataset.preserveAlpha, true),
      forceTransparent: bool(dataset.forceTransparent, false),
      alphaDiagnostics:
        bool(dataset.alphaDiagnostics, false) || ALPHA_DEBUG_QUERY,
      backgroundMode: [
        'auto',
        'transparent',
        'color',
        'gradient',
        'image',
        'asset',
        'webm',
      ].includes(dataset.backgroundMode)
        ? dataset.backgroundMode
        : 'auto',
      backgroundValue: dataset.backgroundValue || '#000000',
    };
  }

  class MotionState {
    constructor(config, frameCount = 0) {
      this.config = config;
      this.frameCount = frameCount;
      this.sourceFps = 60;
      this.rawProgress = 0;
      this.targetProgress = 0;
      this.renderedProgress = 0;
      this.velocity = 0;
      this.inputVelocity = 0;
      this.previousRaw = 0;
      this.previousTarget = 0;
      this.lastInputAt = 0;
      this.lastInputSampleAt = 0;
      this.stopStartedAt = 0;
      this.overshootPreventions = 0;
      this.tailPacingSteps = 0;
      this.initialized = false;
    }

    mapSectionProgress(sectionProgress) {
      const normalized = clamp(
        sectionProgress / SECTION_MEDIA_END_PROGRESS
      );
      const paced = normalized <= 0 || normalized >= 1
        ? normalized
        : normalized ** (1 / this.config.speed);
      const eased = applyEasing(
        paced,
        this.config.easing,
        this.config.bezier
      );
      const local = this.config.direction === 'reverse' ? 1 - eased : eased;
      return clamp(
        this.config.materialStart +
          local * (this.config.materialEnd - this.config.materialStart)
      );
    }

    setSectionProgress(sectionProgress, now, immediate = false) {
      const next = this.mapSectionProgress(sectionProgress);
      if (!this.initialized || immediate) {
        this.rawProgress = next;
        this.targetProgress = next;
        this.renderedProgress = next;
        this.previousRaw = next;
        this.previousTarget = next;
        this.velocity = 0;
        this.inputVelocity = 0;
        this.initialized = true;
      } else {
        const elapsed = Math.max(0.001, (now - this.lastInputSampleAt) / 1000);
        this.inputVelocity = clamp(
          (next - this.previousRaw) / elapsed,
          -12,
          12
        );
        this.previousRaw = this.rawProgress;
        this.rawProgress = next;
      }
      this.lastInputSampleAt = now;
      this.lastInputAt = now;
      this.stopStartedAt = 0;
    }

    quantizeToFrame(value) {
      if (this.frameCount <= 1) return value;
      return Math.round(value * (this.frameCount - 1)) /
        (this.frameCount - 1);
    }

    tick(now, deltaTime, reducedMotion) {
      if (!this.initialized) return { changed: false, needsNext: false };
      const config = this.config;
      const dt = clamp(deltaTime / 1000, 0.001, 0.05);
      const lagMs = reducedMotion ? 0 : config.lagMs;
      const inertia = reducedMotion ? 0 : config.inertia / 100;
      const interpolation =
        reducedMotion && ['spring', 'velocity'].includes(config.interpolation)
          ? 'exponential'
          : config.interpolation;
      const smoothingMs = reducedMotion
        ? Math.min(config.smoothingMs, 80)
        : config.smoothingMs;
      const stopped = now - this.lastInputAt >= STOP_DELAY_MS;

      if (lagMs <= 0) {
        this.targetProgress = this.rawProgress;
      } else {
        const lagAlpha = 1 - Math.exp(-deltaTime / Math.max(1, lagMs));
        this.targetProgress +=
          (this.rawProgress - this.targetProgress) * lagAlpha;
      }
      const targetVelocity =
        (this.targetProgress - this.previousTarget) / dt;
      this.previousTarget = this.targetProgress;

      let destination = this.targetProgress;
      if (stopped && config.stopBehavior === 'snap') {
        const steps = Math.max(1, config.snapPoints - 1);
        destination = Math.round(destination * steps) / steps;
      } else if (stopped && config.stopBehavior === 'nearest-frame') {
        destination = this.quantizeToFrame(destination);
      }

      const previous = this.renderedProgress;
      if (
        interpolation === 'none' ||
        smoothingMs <= 0 ||
        config.stopBehavior === 'immediate'
      ) {
        this.renderedProgress = destination;
        this.velocity = 0;
      } else if (interpolation === 'linear') {
        const speed =
          config.maxCatchUpPerSecond > 0
            ? config.maxCatchUpPerSecond
            : Math.max(0.25, 1000 / smoothingMs);
        this.renderedProgress = moveTowards(
          this.renderedProgress,
          destination,
          speed * dt
        );
        this.velocity = (this.renderedProgress - previous) / dt;
      } else if (interpolation === 'spring') {
        const stiffness = clamp(180000 / (smoothingMs + 250), 35, 180);
        const critical = 2 * Math.sqrt(stiffness);
        const damping = critical * (0.72 + config.damping / 100 * 0.78);
        const acceleration =
          (destination - this.renderedProgress) * stiffness -
          this.velocity * damping;
        this.velocity += acceleration * dt;
        this.velocity += targetVelocity * inertia * dt * 0.35;
        this.renderedProgress += this.velocity * dt;
      } else if (interpolation === 'velocity') {
        const tau = Math.max(0.04, smoothingMs / 1000);
        const desiredVelocity =
          (destination - this.renderedProgress) / tau +
          targetVelocity * inertia * 0.18;
        const velocityAlpha =
          1 -
          Math.exp(
            -dt * (5 + (config.damping / 100) * 17)
          );
        this.velocity +=
          (desiredVelocity - this.velocity) * velocityAlpha;
        this.renderedProgress += this.velocity * dt;
      } else if (interpolation === 'damp') {
        const smoothTime = Math.max(0.035, smoothingMs / 1000);
        const omega = 2 / smoothTime;
        const x = omega * dt;
        const decay = 1 / (1 + x + 0.48 * x * x + 0.235 * x ** 3);
        const change = this.renderedProgress - destination;
        const temp = (this.velocity + omega * change) * dt;
        this.velocity =
          (this.velocity - omega * temp) *
          decay *
          (0.75 + config.damping / 400);
        this.renderedProgress =
          destination + (change + temp) * decay;
        this.renderedProgress += targetVelocity * inertia * dt * 0.025;
      } else {
        const tau = Math.max(0.001, smoothingMs);
        const alpha = 1 - Math.exp(-deltaTime / tau);
        const lead = clamp(
          destination + targetVelocity * inertia * 0.035,
          0,
          1
        );
        this.renderedProgress +=
          (lead - this.renderedProgress) * alpha;
        this.velocity = (this.renderedProgress - previous) / dt;
      }

      if (config.maxCatchUpPerSecond > 0) {
        const limited = moveTowards(
          previous,
          this.renderedProgress,
          config.maxCatchUpPerSecond * dt
        );
        this.velocity = (limited - previous) / dt;
        this.renderedProgress = limited;
      }

      // Końcowe kroki mniejsze niż jedna klatka źródła dają rytm
      // „pauza, przeskok, pauza”. W małym oknie po zatrzymaniu wymuszamy
      // równy pacing względem FPS materiału. Przy 60 Hz jest to najwyżej
      // jedna klatka źródła na RAF, przy 120 Hz pół klatki na RAF.
      if (
        stopped &&
        config.tailPacing &&
        this.frameCount > 1 &&
        interpolation !== 'none' &&
        config.stopBehavior !== 'immediate'
      ) {
        const frameStep = 1 / (this.frameCount - 1);
        const remainingAtFrameStart = Math.abs(destination - previous);
        const pacingWindow = config.tailWindowFrames * frameStep;
        if (
          remainingAtFrameStart > 0.00005 &&
          remainingAtFrameStart <= pacingWindow
        ) {
          const sourceFrameMs = 1000 / Math.max(1, this.sourceFps);
          const pacedStep =
            frameStep * clamp(deltaTime / sourceFrameMs, 0.25, 3);
          const desiredStep = Math.min(
            remainingAtFrameStart,
            pacedStep
          );
          if (
            Math.abs(this.renderedProgress - previous) < desiredStep
          ) {
            this.renderedProgress = moveTowards(
              previous,
              destination,
              desiredStep
            );
            this.velocity =
              (this.renderedProgress - previous) / dt;
            this.tailPacingSteps += 1;
          }
        }
      }

      // Interpolatory tłumione mogą przy gwałtownym wejściu minimalnie
      // przestrzelić cel, a następnie cofnąć materiał o jedną lub kilka klatek.
      // Bezwładność ma zmiękczać dochodzenie, nie odwracać kierunek obrazu.
      // Jawny preset sprężynowy zachowuje możliwość kontrolowanego overshootu.
      if (interpolation !== 'spring') {
        const lowerBound = Math.min(previous, destination);
        const upperBound = Math.max(previous, destination);
        const monotonicProgress = clamp(
          this.renderedProgress,
          lowerBound,
          upperBound
        );
        if (monotonicProgress !== this.renderedProgress) {
          this.renderedProgress = monotonicProgress;
          this.velocity = 0;
          this.overshootPreventions += 1;
        }
      }

      if (stopped && config.stopBehavior === 'decelerate') {
        this.velocity *= Math.exp(
          -dt * (4 + (config.damping / 100) * 12)
        );
      }

      this.renderedProgress = clamp(this.renderedProgress);
      if (
        (this.renderedProgress === 0 && this.velocity < 0) ||
        (this.renderedProgress === 1 && this.velocity > 0)
      ) {
        this.velocity = 0;
      }

      if (stopped) {
        if (!this.stopStartedAt) this.stopStartedAt = now;
        if (
          now - this.stopStartedAt > MAX_SETTLE_MS &&
          Math.abs(destination - this.renderedProgress) > 0.0001
        ) {
          this.renderedProgress = destination;
          this.velocity = 0;
        }
      }

      if (
        Math.abs(destination - this.renderedProgress) < 0.00005 &&
        Math.abs(this.velocity) < 0.0005
      ) {
        this.renderedProgress = destination;
        this.velocity = 0;
      }
      const changed = Math.abs(this.renderedProgress - previous) > 0.000001;
      const needsNext =
        Math.abs(this.rawProgress - this.targetProgress) > 0.00005 ||
        Math.abs(destination - this.renderedProgress) > 0.00005 ||
        Math.abs(this.velocity) > 0.0005;
      return { changed, needsNext };
    }
  }

  class DeclarativeDomAnimation {
    constructor(element) {
      this.element = element;
      this.id =
        element.dataset.scrollAnimationId ||
        element.id ||
        `dom-${Math.random().toString(36).slice(2)}`;
      this.start = clamp(finite(element.dataset.scrollStart, 0));
      this.end = clamp(finite(element.dataset.scrollEnd, 1));
      this.easing = element.dataset.scrollEasing || 'linear';
      this.bezier = parseBezier(element.dataset.scrollBezier);
      this.opacity = this.readPair('scrollOpacity');
      this.translateX = this.readPair('scrollTranslateX');
      this.translateY = this.readPair('scrollTranslateY');
      this.scale = this.readPair('scrollScale');
      this.rotate = this.readPair('scrollRotate');
      this.lastValue = -1;
      this.element.style.willChange = 'transform, opacity';
    }

    readPair(key) {
      const values = String(this.element.dataset[key] || '')
        .split(',')
        .map((value) => Number.parseFloat(value.trim()));
      return values.length === 2 && values.every(Number.isFinite)
        ? values
        : null;
    }

    setTargetProgress() {}

    render(context) {
      const local = applyEasing(
        mapProgress(context.renderedProgress, this.start, this.end),
        this.easing,
        this.bezier
      );
      if (Math.abs(local - this.lastValue) < 0.0001) return;
      this.lastValue = local;
      const interpolate = (pair, fallback) =>
        pair ? pair[0] + (pair[1] - pair[0]) * local : fallback;
      if (this.opacity) {
        this.element.style.opacity = String(interpolate(this.opacity, 1));
      }
      const x = interpolate(this.translateX, 0);
      const y = interpolate(this.translateY, 0);
      const scale = interpolate(this.scale, 1);
      const rotate = interpolate(this.rotate, 0);
      this.element.style.transform =
        `translate3d(${x}px, ${y}px, 0) scale(${scale}) rotate(${rotate}deg)`;
    }

    destroy() {
      this.element.style.removeProperty('will-change');
      this.element.style.removeProperty('opacity');
      this.element.style.removeProperty('transform');
    }
  }

  class BaseController {
    constructor(root, element, scheduler, engine) {
      this.root = root;
      this.element = element;
      this.scheduler = scheduler;
      this.engine = engine;
      this.stage = element?.closest('.media-block__scroll-stage');
      this.config = readMotionConfig(root);
      this.motion = new MotionState(this.config);
      this.scrollStart = 0;
      this.scrollTravel = 1;
      this.isReady = false;
      this.isNearViewport = true;
      this.destroyed = false;
      this.forceRender = true;
      this.resizeObserver = null;
      this.intersectionObserver = null;
      this.abortController = new AbortController();
      this.animatedElements = [];
      this.lastRenderedProgress = -1;
      this.sourceMetadata = {};
      this.applyBackground();
      this.measure();
      {
        const rect = this.root.getBoundingClientRect();
        const margin = (window.innerHeight || 1) * 0.75;
        this.isNearViewport =
          rect.bottom >= -margin && rect.top <= (window.innerHeight || 1) + margin;
      }
      this.observe();
      this.root.querySelectorAll('[data-scroll-animate]').forEach((node) => {
        this.registerAnimatedElement(new DeclarativeDomAnimation(node));
      });
      this.captureScroll(window.scrollY, performance.now(), true);
    }

    applyBackground() {
      const mode = this.config.backgroundMode;
      const value = this.config.backgroundValue;
      let background = '#000000';
      this.clearBackgroundVideo();
      if (mode === 'transparent') background = 'transparent';
      else if (mode === 'color' && /^#[0-9a-f]{3,8}$/i.test(value)) {
        background = value;
      } else if (
        mode === 'gradient' &&
        /^(linear|radial|conic)-gradient\(/i.test(value)
      ) {
        background = value;
      } else if (mode === 'image' && /^url\(/i.test(value)) {
        background = value;
      } else if (mode === 'asset' && value) {
        const safe = String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
        background = `url("${safe}") center / cover no-repeat`;
      } else if (mode === 'webm' && value) {
        background = '#000000';
        this.mountBackgroundVideo(value);
      } else if (mode === 'auto') {
        // Frames: przezroczystość. Video: też transparent — inaczej alfa
        // ląduje na #000 i po podmianie filmu „znika” tło scrolla.
        background = 'transparent';
      }
      this.root.style.setProperty('--scroll-runtime-background', background);
      this.root.classList.toggle(
        'is-scroll-alpha-debug',
        this.config.alphaDiagnostics
      );
    }

    clearBackgroundVideo() {
      const existing =
        this.stage?.querySelector('[data-scroll-bg-video]') ||
        this.root.querySelector('[data-scroll-bg-video]');
      if (existing?.parentNode) existing.parentNode.removeChild(existing);
    }

    mountBackgroundVideo(url) {
      if (!this.stage || !url) return;
      let video = this.stage.querySelector('[data-scroll-bg-video]');
      if (!(video instanceof HTMLVideoElement)) {
        video = document.createElement('video');
        video.dataset.scrollBgVideo = '1';
        video.className = 'media-block__scroll-bg-video';
        video.muted = true;
        video.defaultMuted = true;
        video.loop = true;
        video.autoplay = true;
        video.playsInline = true;
        video.setAttribute('muted', '');
        video.setAttribute('playsinline', '');
        video.setAttribute('webkit-playsinline', '');
        video.setAttribute('aria-hidden', 'true');
        video.preload = 'auto';
        this.stage.insertBefore(video, this.stage.firstChild);
      }
      if (video.getAttribute('src') !== url) {
        video.src = url;
      }
      try {
        const playPromise = video.play();
        if (playPromise && typeof playPromise.catch === 'function') {
          playPromise.catch(() => {});
        }
      } catch (_error) {}
    }

    observe() {
      if ('ResizeObserver' in window) {
        this.resizeObserver = new ResizeObserver(() => {
          this.scheduler.requestMeasure();
        });
        this.resizeObserver.observe(this.root);
        if (this.stage) this.resizeObserver.observe(this.stage);
      }
      if ('IntersectionObserver' in window) {
        this.intersectionObserver = new IntersectionObserver(
          (entries) => {
            this.isNearViewport = Boolean(entries[0]?.isIntersecting);
            this.root.dataset.scrollActive = String(this.isNearViewport);
            if (this.isNearViewport) {
              this.ensureInitialized?.();
              this.captureScroll(window.scrollY, performance.now(), true);
              this.forceRender = true;
              this.scheduler.request();
            }
          },
          { rootMargin: '75% 0px 75% 0px' }
        );
        this.intersectionObserver.observe(this.root);
      }
    }

    measure() {
      const rect = this.root.getBoundingClientRect();
      const stageHeight =
        this.stage?.getBoundingClientRect().height ||
        window.innerHeight ||
        document.documentElement.clientHeight ||
        1;
      const stickyTop =
        Number.parseFloat(
          this.stage ? window.getComputedStyle(this.stage).top : '0'
        ) || 0;
      const sectionTop = rect.top + window.scrollY;
      this.scrollStart = Math.max(0, sectionTop - stickyTop);
      this.scrollTravel = Math.max(1, rect.height - stageHeight);
    }

    sectionProgress(scrollY) {
      return clamp((scrollY - this.scrollStart) / this.scrollTravel);
    }

    captureScroll(scrollY, now, immediate = false) {
      if (this.root?.dataset?.fmExternalScrub === '1') return;
      this.motion.setSectionProgress(
        this.sectionProgress(scrollY),
        now,
        immediate
      );
      this.animatedElements.forEach((element) =>
        element.setTargetProgress?.(this.motion.rawProgress)
      );
    }

    setExternalProgress(progress, now = performance.now(), immediate = false) {
      const sectionProgress =
        clamp(progress) * SECTION_MEDIA_END_PROGRESS;
      this.motion.setSectionProgress(sectionProgress, now, immediate);
      this.animatedElements.forEach((element) =>
        element.setTargetProgress?.(this.motion.rawProgress)
      );
      this.ensureInitialized?.();
      this.forceRender = true;
      this.scheduler.request();
    }

    updateStory(progress) {
      const introPast = progress > INTRO_EXIT_PROGRESS;
      const outroVisible = progress >= this.config.materialEnd - 0.005;
      this.root.classList.toggle('is-scroll-frame-intro-past', introPast);
      this.root.classList.toggle(
        'is-scroll-frame-outro-visible',
        outroVisible
      );
      this.root
        .querySelector('.media-block__scroll-outro')
        ?.setAttribute('aria-hidden', String(!outroVisible));
    }

    tick(context) {
      const portalOverlayActive = Boolean(
        this.stage?.classList.contains('is-fm-portal-overlay')
      );
      if (
        this.destroyed ||
        !this.isReady ||
        (!this.isNearViewport && !portalOverlayActive) ||
        document.hidden
      ) {
        return false;
      }
      if (portalOverlayActive && !this.isNearViewport) {
        this.ensureInitialized?.();
      }
      const motionResult = this.motion.tick(
        context.now,
        context.deltaTime,
        context.reducedMotion
      );
      const changed =
        motionResult.changed ||
        this.forceRender ||
        Math.abs(this.motion.renderedProgress - this.lastRenderedProgress) >
          0.000001;
      if (changed) {
        this.renderProgress(this.motion.renderedProgress, context);
        this.updateStory(this.motion.renderedProgress);
        const animationContext = {
          ...context,
          globalProgress: this.motion.rawProgress,
          targetProgress: this.motion.targetProgress,
          renderedProgress: this.motion.renderedProgress,
        };
        this.animatedElements.forEach((element) =>
          element.render?.(animationContext)
        );
        this.lastRenderedProgress = this.motion.renderedProgress;
        this.forceRender = false;
      }
      if (DEBUG) this.writeDebugDataset();
      return motionResult.needsNext || this.hasPendingWork();
    }

    hasPendingWork() {
      return false;
    }

    renderProgress() {}

    registerAnimatedElement(element) {
      if (!element || this.animatedElements.includes(element)) return () => {};
      this.animatedElements.push(element);
      element.initialize?.();
      element.activate?.();
      this.forceRender = true;
      this.scheduler.request();
      return () => {
        const index = this.animatedElements.indexOf(element);
        if (index >= 0) this.animatedElements.splice(index, 1);
        element.deactivate?.();
        element.destroy?.();
      };
    }

    writeDebugDataset() {
      const state = this.diagnostics();
      this.root.dataset.motionPresetActive = this.config.preset;
      this.root.dataset.motionPresetOverride = DEBUG_PRESET || '';
      this.root.dataset.rawProgress = state.rawProgress.toFixed(5);
      this.root.dataset.targetProgress = state.targetProgress.toFixed(5);
      this.root.dataset.renderedProgress = state.renderedProgress.toFixed(5);
      this.root.dataset.motionVelocity = state.velocity.toFixed(4);
      this.root.dataset.motionOvershootPreventions = String(
        state.overshootPreventions
      );
      this.root.dataset.motionTailPacingSteps = String(
        state.tailPacingSteps
      );
      this.root.dataset.motionCatalog = catalogStatus;
      this.root.dataset.reducedMotion = String(
        this.scheduler.reducedMotion.matches || DEBUG_REDUCED_MOTION
      );
      this.root.dataset.pageFps = String(
        this.scheduler.metrics.pageFps.toFixed(1)
      );
      this.root.dataset.pageWorstFrameMs = String(
        this.scheduler.metrics.worstFrameMs.toFixed(1)
      );
      this.root.dataset.pageAverageFrameMs = String(
        this.scheduler.metrics.averageFrameMs.toFixed(1)
      );
    }

    diagnostics() {
      return {
        engine: this.engine,
        quality: this.element?.dataset.frameQuality || '',
        preset: this.config.preset,
        rawProgress: this.motion.rawProgress,
        targetProgress: this.motion.targetProgress,
        renderedProgress: this.motion.renderedProgress,
        velocity: this.motion.velocity,
        overshootPreventions: this.motion.overshootPreventions,
        tailPacingSteps: this.motion.tailPacingSteps,
        reducedMotion:
          this.scheduler.reducedMotion.matches || DEBUG_REDUCED_MOTION,
        nearViewport: this.isNearViewport,
        ready: this.isReady,
        backgroundMode: this.config.backgroundMode,
        preserveAlpha: this.config.preserveAlpha,
        forceTransparent: this.config.forceTransparent,
        catalogStatus,
        source: this.sourceMetadata,
      };
    }

    fail(error) {
      this.root.classList.add('has-scroll-frame-error');
      this.root.dataset.scrollError =
        error instanceof Error ? error.message : String(error);
    }

    destroy() {
      this.destroyed = true;
      this.abortController.abort();
      this.resizeObserver?.disconnect();
      this.intersectionObserver?.disconnect();
      this.animatedElements.splice(0).forEach((element) => {
        element.deactivate?.();
        element.destroy?.();
      });
      this.clearBackgroundVideo();
      this.root.style.removeProperty('--scroll-runtime-background');
    }
  }

  class ScrollFrameCanvas extends BaseController {
    constructor(root, scheduler) {
      const canvas = root.querySelector(CANVAS_SELECTOR);
      super(root, canvas, scheduler, 'frames');
      this.canvas = canvas;
      this.context = canvas?.getContext('2d', {
        alpha: true,
        desynchronized: true,
      });
      this.manifestUrl = canvas?.dataset.frameManifest || '';
      this.sourceKey = this.manifestUrl;
      this.frameCount = Math.max(
        1,
        Number.parseInt(canvas?.dataset.frameCount || '1', 10)
      );
      this.frameWidth = Number.parseInt(
        canvas?.dataset.frameWidth || '1280',
        10
      );
      this.frameHeight = Number.parseInt(
        canvas?.dataset.frameHeight || '720',
        10
      );
      this.fps = finite(canvas?.dataset.frameFps, 60);
      this.motion.frameCount = this.frameCount;
      this.motion.sourceFps = this.fps;
      this.frameUrls = [];
      this.targetFrame = 0;
      this.lastDrawnFrame = -1;
      this.lastRequestedFrame = -1;
      this.scrollDirection = 1;
      this.bitmapCache = new Map();
      this.bitmapRequests = new Map();
      this.blobCache = new Map();
      this.blobPromises = new Map();
      this.decodeQueue = [];
      this.activeDecodes = 0;
      this.maxDecodeConcurrency = this.chooseDecodeConcurrency();
      this.maxBitmapCache = this.chooseBitmapCacheSize();
      this.maxBlobCache = this.maxBitmapCache * 2;
      this.renderedHistory = [];
      this.skippedFrames = 0;
      this.renderTimeMs = 0;
      this.decodeFailures = 0;
      this.initializationStarted = false;

      if (!canvas || !this.context || !this.manifestUrl) {
        this.fail('Brak canvasu lub manifestu WebP.');
        return;
      }
      this.context.imageSmoothingEnabled = false;
      this.root.classList.remove(
        'is-scroll-frame-ready',
        'has-scroll-frame-error',
        'is-scroll-frame-outro-visible'
      );
      if (this.isNearViewport) this.ensureInitialized();
    }

    ensureInitialized() {
      if (this.initializationStarted || this.destroyed) return;
      this.initializationStarted = true;
      this.initialize();
    }

    chooseBitmapCacheSize() {
      if (this.config.cacheFrames > 0) return this.config.cacheFrames;
      const memory = finite(navigator.deviceMemory, 8);
      const fullHd = this.frameWidth * this.frameHeight >= 1920 * 1080;
      if (fullHd) return memory <= 4 ? 8 : memory <= 8 ? 12 : 16;
      return memory <= 4 ? 16 : memory <= 8 ? 20 : 24;
    }

    chooseDecodeConcurrency() {
      return 1;
    }

    async initialize() {
      try {
        const manifest = await this.loadManifest();
        if (this.destroyed) return;
        if (this.config.forceTransparent && manifest.hasAlpha !== true) {
          throw new Error('Wymuszono przezroczystość, ale sekwencja nie ma alfa.');
        }
        this.targetFrame = this.frameAtProgress(
          this.motion.renderedProgress
        );
        await this.requestBitmap(this.targetFrame, 0);
        if (this.destroyed) return;
        this.drawFrame(this.targetFrame);
        this.isReady = true;
        this.root.classList.add('is-scroll-frame-ready');
        this.prefetchAround(this.targetFrame);
        this.scheduler.request();
      } catch (error) {
        if (!this.destroyed) this.fail(error);
      }
    }

    async loadManifest() {
      const response = await fetch(this.manifestUrl, {
        cache: 'force-cache',
        credentials: 'same-origin',
        signal: this.abortController.signal,
      });
      if (!response.ok) throw new Error('Nie udało się pobrać manifestu WebP.');
      const manifest = await response.json();
      const count = Number.parseInt(manifest.frameCount, 10);
      const width = Number.parseInt(manifest.width, 10);
      const height = Number.parseInt(manifest.height, 10);
      const digits = Number.parseInt(manifest.digits, 10);
      const prefix = String(manifest.prefix || '');
      const extension = String(manifest.extension || '.webp');
      if (!count || !width || !height || !digits || !prefix) {
        throw new Error('Niepoprawny manifest WebP.');
      }
      this.frameCount = count;
      this.frameWidth = width;
      this.frameHeight = height;
      this.fps = finite(manifest.fps, this.fps);
      this.motion.frameCount = count;
      this.motion.sourceFps = this.fps;
      this.canvas.width = width;
      this.canvas.height = height;
      this.maxDecodeConcurrency = this.chooseDecodeConcurrency();
      this.maxBitmapCache = this.chooseBitmapCacheSize();
      this.maxBlobCache = this.maxBitmapCache * 2;
      const absoluteManifestUrl = new URL(this.manifestUrl, document.baseURI);
      this.frameUrls = Array.from({ length: count }, (_, index) => {
        const filename =
          `${prefix}${String(index).padStart(digits, '0')}${extension}`;
        return new URL(filename, absoluteManifestUrl).href;
      });
      this.sourceMetadata = {
        fps: this.fps,
        frameCount: count,
        width,
        height,
        codec: manifest.codec || 'webp',
        pixelFormat: manifest.pixelFormat || 'unknown',
        hasAlpha:
          manifest.hasAlpha == null
            ? bool(this.canvas.dataset.sourceHasAlpha, true)
            : Boolean(manifest.hasAlpha),
        alphaMode: manifest.alphaMode || this.canvas.dataset.alphaMode || 'unknown',
        sourceFps: manifest.sourceFps ?? null,
        sourceFrameCount: manifest.sourceFrameCount ?? null,
        sourceHasAlpha: manifest.sourceHasAlpha ?? null,
        fullSourceFrameUse: manifest.fullSourceFrameUse ?? null,
        premultipliedAlpha: true,
        compositing: 'copy',
      };
      return manifest;
    }

    rounding(value) {
      if (this.config.frameRounding === 'floor') return Math.floor(value);
      if (this.config.frameRounding === 'ceil') return Math.ceil(value);
      return Math.round(value);
    }

    frameAtProgress(progress) {
      return clamp(
        this.rounding(progress * (this.frameCount - 1)),
        0,
        this.frameCount - 1
      );
    }

    async loadBlob(frame) {
      if (this.blobCache.has(frame)) {
        const blob = this.blobCache.get(frame);
        this.blobCache.delete(frame);
        this.blobCache.set(frame, blob);
        return blob;
      }
      if (this.blobPromises.has(frame)) return this.blobPromises.get(frame);
      const promise = fetch(this.frameUrls[frame], {
        cache: 'force-cache',
        credentials: 'same-origin',
        signal: this.abortController.signal,
      })
        .then((response) => {
          if (!response.ok) throw new Error(`Klatka ${frame} nie została pobrana.`);
          return response.blob();
        })
        .then((blob) => {
          this.blobPromises.delete(frame);
          this.blobCache.set(frame, blob);
          while (this.blobCache.size > this.maxBlobCache) {
            this.blobCache.delete(this.blobCache.keys().next().value);
          }
          return blob;
        })
        .catch((error) => {
          this.blobPromises.delete(frame);
          throw error;
        });
      this.blobPromises.set(frame, promise);
      return promise;
    }

    async decodeBlob(blob) {
      if ('createImageBitmap' in window) {
        return window.createImageBitmap(blob, {
          premultiplyAlpha: 'premultiply',
          colorSpaceConversion: 'default',
        });
      }
      const objectUrl = URL.createObjectURL(blob);
      try {
        const image = new Image();
        image.decoding = 'async';
        image.src = objectUrl;
        await image.decode();
        return image;
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    }

    requestBitmap(frame, priority = 10) {
      const safeFrame = clamp(Math.round(frame), 0, this.frameCount - 1);
      if (this.bitmapCache.has(safeFrame)) {
        const bitmap = this.bitmapCache.get(safeFrame);
        this.touchBitmap(safeFrame, bitmap);
        return Promise.resolve(bitmap);
      }
      const existing = this.bitmapRequests.get(safeFrame);
      if (existing) {
        if (existing.state === 'queued' && priority < existing.priority) {
          existing.priority = priority;
          this.sortDecodeQueue();
        }
        return existing.promise;
      }
      let resolveRequest;
      let rejectRequest;
      const promise = new Promise((resolve, reject) => {
        resolveRequest = resolve;
        rejectRequest = reject;
      });
      const request = {
        frame: safeFrame,
        priority,
        state: 'queued',
        promise,
        resolve: resolveRequest,
        reject: rejectRequest,
      };
      this.bitmapRequests.set(safeFrame, request);
      this.decodeQueue.push(request);
      this.sortDecodeQueue();
      this.pumpDecodeQueue();
      return promise;
    }

    sortDecodeQueue() {
      this.decodeQueue.sort(
        (left, right) =>
          left.priority - right.priority ||
          Math.abs(left.frame - this.targetFrame) -
            Math.abs(right.frame - this.targetFrame)
      );
    }

    pumpDecodeQueue() {
      if (this.destroyed) return;
      while (
        this.activeDecodes < this.maxDecodeConcurrency &&
        this.decodeQueue.length
      ) {
        const request = this.decodeQueue.shift();
        if (!request || request.state !== 'queued') continue;
        request.state = 'active';
        this.activeDecodes += 1;
        this.loadBlob(request.frame)
          .then((blob) => this.decodeBlob(blob))
          .then((bitmap) => {
            if (this.destroyed) {
              bitmap.close?.();
              return;
            }
            this.touchBitmap(request.frame, bitmap);
            this.evictBitmaps();
            request.resolve(bitmap);
            if (request.frame === this.targetFrame) {
              this.forceRender = true;
              this.scheduler.request();
            }
          })
          .catch((error) => {
            this.decodeFailures += 1;
            request.reject(error);
          })
          .finally(() => {
            this.bitmapRequests.delete(request.frame);
            this.activeDecodes -= 1;
            this.pumpDecodeQueue();
          });
      }
    }

    touchBitmap(frame, bitmap) {
      this.bitmapCache.delete(frame);
      this.bitmapCache.set(frame, bitmap);
    }

    evictBitmaps() {
      while (this.bitmapCache.size > this.maxBitmapCache) {
        const candidate = [...this.bitmapCache.keys()].find(
          (frame) =>
            frame !== this.lastDrawnFrame && frame !== this.targetFrame
        );
        if (candidate == null) break;
        const bitmap = this.bitmapCache.get(candidate);
        this.bitmapCache.delete(candidate);
        bitmap?.close?.();
      }
    }

    prefetchAround(targetFrame) {
      const radius = Math.min(
        this.config.preloadRadius,
        Math.max(2, this.maxBitmapCache - 1)
      );
      const direction =
        Math.sign(targetFrame - this.lastDrawnFrame) || this.scrollDirection || 1;
      const wanted = [targetFrame];
      for (let offset = 1; offset <= radius; offset += 1) {
        const preferred = targetFrame + direction * offset;
        const opposite = targetFrame - direction * offset;
        if (preferred >= 0 && preferred < this.frameCount) wanted.push(preferred);
        if (opposite >= 0 && opposite < this.frameCount) wanted.push(opposite);
      }
      // Gorący preload jest celowo mały. Nowy cel zawsze ma pierwszeństwo,
      // a sąsiedzi są dekodowani dopiero po narysowaniu aktualnej klatki.
      const hotPreloadLimit = Math.min(
        this.maxBitmapCache,
        1 + Math.max(1, Math.ceil(this.config.preloadRadius / 6))
      );
      wanted.slice(0, hotPreloadLimit).forEach((frame, index) => {
        this.requestBitmap(frame, 20 + index).catch(() => {});
      });
    }

    discardStaleQueued(targetFrame) {
      const keepDistance = Math.max(
        4,
        Math.ceil(this.config.preloadRadius / 2)
      );
      const retained = [];
      this.decodeQueue.forEach((request) => {
        if (
          request.state === 'queued' &&
          Math.abs(request.frame - targetFrame) > keepDistance
        ) {
          request.state = 'cancelled';
          this.bitmapRequests.delete(request.frame);
          request.reject(new DOMException('Nieaktualna klatka.', 'AbortError'));
        } else {
          retained.push(request);
        }
      });
      this.decodeQueue = retained;
    }

    nearestCachedFrame(target) {
      let best = null;
      let distance = Number.POSITIVE_INFINITY;
      this.bitmapCache.forEach((_bitmap, frame) => {
        const nextDistance = Math.abs(target - frame);
        if (nextDistance < distance) {
          best = frame;
          distance = nextDistance;
        }
      });
      return best;
    }

    drawFrame(frame) {
      const bitmap = this.bitmapCache.get(frame);
      if (!bitmap || frame === this.lastDrawnFrame) return false;
      const started = performance.now();
      this.context.globalCompositeOperation = 'copy';
      this.context.drawImage(bitmap, 0, 0, this.canvas.width, this.canvas.height);
      this.renderTimeMs = performance.now() - started;
      if (this.lastDrawnFrame >= 0) {
        this.skippedFrames += Math.max(
          0,
          Math.abs(frame - this.lastDrawnFrame) - 1
        );
      }
      this.lastDrawnFrame = frame;
      this.renderedHistory.push({
        frame,
        at: performance.now(),
        renderMs: this.renderTimeMs,
      });
      this.trimHistory();
      this.touchBitmap(frame, bitmap);
      this.evictBitmaps();
      this.root.classList.remove('has-scroll-frame-error');
      return true;
    }

    trimHistory() {
      const cutoff = performance.now() - 1000;
      while (this.renderedHistory[0]?.at < cutoff) {
        this.renderedHistory.shift();
      }
    }

    renderProgress(progress) {
      if (!this.frameCount) return;
      const nextFrame = this.frameAtProgress(progress);
      const difference = Math.abs(nextFrame - this.lastRequestedFrame);
      if (
        nextFrame !== this.lastRequestedFrame &&
        (this.lastRequestedFrame < 0 ||
          difference >= this.config.webpDeadZoneFrames)
      ) {
        this.scrollDirection =
          Math.sign(nextFrame - this.lastRequestedFrame) || this.scrollDirection;
        this.lastRequestedFrame = nextFrame;
        this.targetFrame = nextFrame;
        this.discardStaleQueued(nextFrame);
        this.requestBitmap(nextFrame, 0).catch((error) => {
          if (error?.name !== 'AbortError') this.fail(error);
        });
      }
      if (this.bitmapCache.has(nextFrame)) {
        if (this.drawFrame(nextFrame)) this.prefetchAround(nextFrame);
      } else {
        const nearest = this.nearestCachedFrame(nextFrame);
        if (nearest != null) this.drawFrame(nearest);
      }
    }

    hasPendingWork() {
      return (
        this.lastDrawnFrame !== this.targetFrame &&
        this.bitmapCache.has(this.targetFrame)
      );
    }

    writeDebugDataset() {
      super.writeDebugDataset();
      this.trimHistory();
      const unique = new Set(this.renderedHistory.map((entry) => entry.frame));
      this.canvas.dataset.targetFrame = String(this.targetFrame);
      this.canvas.dataset.renderedFrame = String(this.lastDrawnFrame);
      this.canvas.dataset.uniqueFramesLastSecond = String(unique.size);
      this.canvas.dataset.skippedFrames = String(this.skippedFrames);
      this.canvas.dataset.frameRenderMs = this.renderTimeMs.toFixed(2);
      this.canvas.dataset.averageFrameRenderMs = String(
        this.averageFrameRenderMs().toFixed(2)
      );
      this.canvas.dataset.bitmapCache = String(this.bitmapCache.size);
      this.canvas.dataset.bitmapCacheLimit = String(this.maxBitmapCache);
      this.canvas.dataset.blobCache = String(this.blobCache.size);
      this.canvas.dataset.decodeQueue = String(this.decodeQueue.length);
      this.canvas.dataset.decodeFailures = String(this.decodeFailures);
      this.canvas.dataset.devicePixelRatio = String(window.devicePixelRatio || 1);
      this.canvas.dataset.canvasAlpha = 'true';
      this.canvas.dataset.compositing = 'copy';
    }

    diagnostics() {
      this.trimHistory();
      return {
        ...super.diagnostics(),
        targetFrame: this.targetFrame,
        renderedFrame: this.lastDrawnFrame,
        sourceFps: this.fps,
        sourceFrameCount: this.frameCount,
        uniqueFramesLastSecond: new Set(
          this.renderedHistory.map((entry) => entry.frame)
        ).size,
        skippedFrames: this.skippedFrames,
        frameRenderMs: this.renderTimeMs,
        averageFrameRenderMs: this.averageFrameRenderMs(),
        bitmapCache: this.bitmapCache.size,
        bitmapCacheLimit: this.maxBitmapCache,
        estimatedBitmapMemoryMb:
          (this.bitmapCache.size * this.frameWidth * this.frameHeight * 4) /
          (1024 * 1024),
        decodeQueue: this.decodeQueue.length,
        decodeFailures: this.decodeFailures,
        canvasAlpha: true,
        premultipliedAlpha: true,
        compositing: 'copy',
        devicePixelRatio: window.devicePixelRatio || 1,
      };
    }

    averageFrameRenderMs() {
      if (!this.renderedHistory.length) return 0;
      return (
        this.renderedHistory.reduce(
          (sum, entry) => sum + finite(entry.renderMs, 0),
          0
        ) / this.renderedHistory.length
      );
    }

    destroy() {
      super.destroy();
      this.bitmapCache.forEach((bitmap) => bitmap?.close?.());
      this.bitmapCache.clear();
      this.blobCache.clear();
      this.decodeQueue.length = 0;
    }
  }

  class ScrollNativeVideo extends BaseController {
    constructor(root, scheduler) {
      const video = root.querySelector(VIDEO_SELECTOR);
      super(root, video, scheduler, 'video');
      this.video = video;
      this.container =
        video?.dataset.videoContainer ||
        root.dataset.scrollVideoContainer ||
        'mp4';
      this.mediaLabel = this.container === 'webm' ? 'WebM' : 'MP4';
      this.sourceKey =
        video?.querySelector('source')?.getAttribute('src') ||
        video?.getAttribute('src') ||
        '';
      this.manifestUrl = video?.dataset.videoManifest || '';
      this.frameCount = Math.max(
        1,
        Number.parseInt(video?.dataset.frameCount || '210', 10)
      );
      this.fps = finite(video?.dataset.frameFps, 60);
      this.duration = this.frameCount / this.fps;
      this.motion.frameCount = this.frameCount;
      this.motion.sourceFps = this.fps;
      this.pendingTime = null;
      this.lastRequestedTime = -1;
      this.lastPresentedFrame = -1;
      this.objectUrl = '';
      this.seekExecuted = 0;
      this.seekSkipped = 0;
      this.seekErrors = 0;
      this.renderedHistory = [];
      this.skippedFrames = 0;
      this.videoFrameCallbackId = 0;
      this.initializationStarted = false;
      this.interFrameWebm = false;
      this.playTargetTime = null;
      this.sequentialPlaybackActive = false;
      this.playPromisePending = false;
      this.sequentialPlaybackStarts = 0;
      this.sequentialPlaybackStops = 0;
      this.sequentialPlaybackFrames = 0;
      this.largeForwardSeekCount = 0;
      this.deferredForwardSeekCount = 0;
      this.presentationRecoverySeekCount = 0;
      this.reverseSeekCount = 0;
      this.maxTargetDriftMs = 0;
      this.lastLargeForwardSeekTarget = null;
      this.prewarmCompleted = false;
      this.sourceDelivery = 'native-url';

      if (!video || !this.sourceKey) {
        this.fail(`Brak źródła filmu ${this.mediaLabel}.`);
        return;
      }
      this.video.muted = true;
      this.video.playsInline = true;
      this.video.pause();
      this.video.addEventListener(
        'seeked',
        () => {
          if (this.video && this.fps > 0) {
            this.lastPresentedFrame = clamp(
              Math.round(this.video.currentTime * this.fps),
              0,
              this.frameCount - 1
            );
          }
          if (this.interFrameWebm && this.pendingTime == null) {
            this.updateSequentialPlayback();
          }
          this.scheduler.request();
        },
        { signal: this.abortController.signal }
      );
      this.video.addEventListener(
        'error',
        () => {
          this.seekErrors += 1;
          this.fail(`Błąd dekodowania filmu ${this.mediaLabel}.`);
        },
        { signal: this.abortController.signal }
      );
      this.root.classList.remove(
        'is-scroll-frame-ready',
        'has-scroll-frame-error',
        'is-scroll-frame-outro-visible'
      );
      if (this.isNearViewport) this.ensureInitialized();
    }

    ensureInitialized() {
      if (this.initializationStarted || this.destroyed) return;
      this.initializationStarted = true;
      this.initialize();
    }

    async initialize() {
      try {
        const manifestPromise = this.loadManifest();
        const earlyManifest =
          this.container === 'webm' ? await manifestPromise : null;
        const localPreviewHost =
          window.location.hostname === 'localhost' ||
          window.location.hostname === '127.0.0.1' ||
          window.location.hostname === '::1';
        const useBufferedBlob =
          this.container !== 'webm' ||
          earlyManifest?.hasAlpha === true ||
          localPreviewHost;
        if (!useBufferedBlob) {
          // Nieprzezroczysty WebM pozostaje pod natywnym adresem CDN. Druga
          // kopia dużego pliku jako Blob podwajałaby transfer i pamięć.
          this.video.preload = 'auto';
          if (!this.video.currentSrc) this.video.load();
        } else {
          const response = await fetch(this.sourceKey, {
            cache: 'force-cache',
            credentials: 'same-origin',
            signal: this.abortController.signal,
          });
          if (!response.ok) {
            throw new Error(`Nie udało się pobrać filmu ${this.mediaLabel}.`);
          }
          const blob = await response.blob();
          if (this.destroyed) return;
          this.objectUrl = URL.createObjectURL(blob);
          this.video.src = this.objectUrl;
          this.sourceDelivery =
            this.container === 'webm'
              ? earlyManifest?.hasAlpha === true
                ? 'buffered-alpha-blob'
                : 'buffered-preview-blob'
              : 'blob';
          this.video.load();
        }
        if (this.video.readyState < 1) {
          await new Promise((resolve, reject) => {
            this.video.addEventListener('loadedmetadata', resolve, {
              once: true,
              signal: this.abortController.signal,
            });
            this.video.addEventListener(
              'error',
              () =>
                reject(
                  new Error(
                    `Metadane filmu ${this.mediaLabel} są niedostępne.`
                  )
                ),
              { once: true, signal: this.abortController.signal }
            );
          });
        }
        const manifest = earlyManifest || (await manifestPromise);
        if (this.destroyed) return;
        if (this.config.forceTransparent && manifest.hasAlpha !== true) {
          throw new Error(
            `Film ${this.mediaLabel} nie ma potwierdzonego kanału alfa.`
          );
        }
        if (Number.isFinite(this.video.duration) && this.video.duration > 0) {
          this.duration = this.video.duration;
        }
        this.frameCount = finite(manifest.frameCount, this.frameCount);
        this.fps = finite(manifest.fps, this.fps);
        this.motion.frameCount = this.frameCount;
        this.motion.sourceFps = this.fps;
        if (this.container === 'webm' && manifest.hasAlpha === true) {
          await this.prewarmAlphaWebm();
          if (this.destroyed) return;
        }
        this.interFrameWebm =
          this.container === 'webm' &&
          this.sourceMetadata.intraOnly === false;
        this.isReady = true;
        this.root.classList.add('is-scroll-frame-ready');
        this.trackPresentedFrames();
        const initialTime = this.timeForProgress(
          this.motion.renderedProgress
        );
        if (this.interFrameWebm) {
          this.renderInterFrameWebm(initialTime);
        } else {
          this.pendingTime = initialTime;
        }
        this.scheduler.request();
      } catch (error) {
        if (!this.destroyed) this.fail(error);
      }
    }

    async prewarmAlphaWebm() {
      if (
        !this.video ||
        this.video.readyState < 1 ||
        !Number.isFinite(this.video.duration) ||
        this.video.duration <= 0
      ) {
        return;
      }
      const seekOnce = (time) =>
        new Promise((resolve) => {
          if (Math.abs(this.video.currentTime - time) < 0.001) {
            resolve();
            return;
          }
          const finish = () => resolve();
          this.video.addEventListener('seeked', finish, {
            once: true,
            signal: this.abortController.signal,
          });
          this.abortController.signal.addEventListener('abort', finish, {
            once: true,
          });
          try {
            this.video.currentTime = time;
          } catch (_error) {
            resolve();
          }
        });
      const warmTime = Math.min(
        Math.max(this.frameDuration() * 6, 0.08),
        Math.max(0, this.video.duration - this.frameDuration())
      );
      await seekOnce(warmTime);
      if (this.destroyed) return;
      await seekOnce(0);
      this.prewarmCompleted = true;
    }

    async loadManifest() {
      let manifest = {};
      if (this.manifestUrl) {
        try {
          const response = await fetch(this.manifestUrl, {
            cache: 'force-cache',
            credentials: 'same-origin',
            signal: this.abortController.signal,
          });
          if (response.ok) manifest = await response.json();
        } catch (_error) {
          manifest = {};
        }
      }
      this.sourceMetadata = {
        fps: finite(manifest.fps, this.fps),
        frameCount: finite(manifest.frameCount, this.frameCount),
        width: finite(manifest.width, this.video.width),
        height: finite(manifest.height, this.video.height),
        codec:
          manifest.codec ||
          this.video.dataset.sourceCodec ||
          (this.container === 'webm' ? 'vp9' : 'h264'),
        pixelFormat:
          manifest.pixelFormat ||
          (this.container === 'webm' ? 'unknown' : 'yuv420p'),
        hasAlpha:
          manifest.hasAlpha == null
            ? bool(this.video.dataset.sourceHasAlpha, false)
            : Boolean(manifest.hasAlpha),
        alphaMode:
          manifest.alphaMode ||
          this.video.dataset.alphaMode ||
          'none',
        sourceFps: manifest.sourceFps ?? null,
        sourceFrameCount: manifest.sourceFrameCount ?? null,
        sourceHasAlpha: manifest.sourceHasAlpha ?? null,
        fullSourceFrameUse: manifest.fullSourceFrameUse ?? null,
        keyframeInterval: manifest.keyframeInterval ?? 1,
        intraOnly: manifest.intraOnly ?? true,
        container: manifest.container || this.container,
        mimeType:
          manifest.mimeType ||
          (this.container === 'webm' ? 'video/webm' : 'video/mp4'),
        passthrough: Boolean(manifest.passthrough),
        backgroundMode:
          manifest.backgroundMode ||
          (manifest.hasAlpha ? 'transparent' : 'color'),
        fallbackActive: Boolean(manifest.fallbackActive),
      };
      return manifest;
    }

    timeForProgress(progress) {
      const finalTime = Math.max(0, this.duration - 1 / this.fps);
      return clamp(progress) * finalTime;
    }

    frameDuration() {
      return 1 / Math.max(1, this.fps);
    }

    presentedTime() {
      if (this.lastPresentedFrame >= 0) {
        return this.lastPresentedFrame / Math.max(1, this.fps);
      }
      return this.video?.currentTime || 0;
    }

    inputIsActive(now = performance.now()) {
      return now - this.motion.lastInputAt < STOP_DELAY_MS;
    }

    maxSequentialCatchupSeconds() {
      if (this.sourceMetadata.hasAlpha !== true) {
        return MAX_SEQUENTIAL_WEBM_CATCHUP_SECONDS;
      }
      // Seek VP9 z alfą jest w Chromium dekodowany programowo i na 1080p
      // potrafi być znacznie droższy od odtworzenia krótkiego odcinka wprost.
      // Dla GOP <= 15 pozwalamy dekoderowi kontynuować sekwencyjnie zamiast
      // przerywać ruch kosztownym skokiem do klatki docelowej.
      return this.sourceMetadata.keyframeInterval <= 15
        ? ALPHA_WEBM_MAX_SEQUENTIAL_CATCHUP_SECONDS
        : 0.55;
    }

    queueLargeForwardSeek(time, current) {
      if (
        this.lastLargeForwardSeekTarget != null &&
        Math.abs(time - this.lastLargeForwardSeekTarget) <=
          this.frameDuration()
      ) {
        return false;
      }
      const delta = Math.max(0, time - current);
      const preRoll = Math.min(0.14, Math.max(0.08, delta * 0.25));
      this.pendingTime = Math.max(0, time - preRoll);
      this.lastLargeForwardSeekTarget = time;
      this.largeForwardSeekCount += 1;
      this.pauseSequentialPlayback();
      this.executeLatestSeek();
      return true;
    }

    pauseSequentialPlayback() {
      if (!this.sequentialPlaybackActive && this.video?.paused) return;
      this.video?.pause();
      if (this.sequentialPlaybackActive) {
        this.sequentialPlaybackStops += 1;
      }
      this.sequentialPlaybackActive = false;
    }

    startSequentialPlayback() {
      if (
        !this.interFrameWebm ||
        !this.video ||
        this.video.readyState < 2 ||
        this.video.seeking ||
        this.playTargetTime == null
      ) {
        return false;
      }
      const remaining = this.playTargetTime - this.presentedTime();
      const mediaRemaining =
        this.playTargetTime - (this.video.currentTime || 0);
      const tolerance = this.frameDuration() * 0.75;
      if (mediaRemaining <= tolerance) {
        this.pauseSequentialPlayback();
        return false;
      }
      if (remaining <= tolerance) {
        this.pauseSequentialPlayback();
        return false;
      }

      // Około 140 ms doganiania: bez długiego "ogona", ale też bez lawiny
      // seeków. Natywny dekoder odtwarza kolejne klatki VP9 w poprawnej
      // kolejności, dzięki czemu ruch do przodu pozostaje ciągły.
      const alphaSource = this.sourceMetadata.hasAlpha === true;
      const catchupWindow = 0.14;
      const minPlaybackRate = alphaSource
        ? ALPHA_WEBM_MIN_PLAYBACK_RATE
        : 0.75;
      const maxPlaybackRate = alphaSource
        ? ALPHA_WEBM_MAX_PLAYBACK_RATE
        : 2.5;
      this.video.playbackRate = clamp(
        remaining / catchupWindow,
        minPlaybackRate,
        maxPlaybackRate
      );
      this.pendingTime = null;
      if (!this.sequentialPlaybackActive) {
        this.sequentialPlaybackActive = true;
        this.sequentialPlaybackStarts += 1;
      }
      if (this.video.paused && !this.playPromisePending) {
        this.playPromisePending = true;
        Promise.resolve(this.video.play())
          .catch(() => {
            this.sequentialPlaybackActive = false;
          })
          .finally(() => {
            this.playPromisePending = false;
            this.scheduler.request();
          });
      }
      return true;
    }

    updateSequentialPlayback() {
      if (
        !this.interFrameWebm ||
        !this.video ||
        this.playTargetTime == null
      ) {
        return false;
      }
      const remaining = this.playTargetTime - this.presentedTime();
      const mediaRemaining =
        this.playTargetTime - (this.video.currentTime || 0);
      const tolerance = this.frameDuration() * 0.75;
      if (mediaRemaining <= tolerance) {
        this.pauseSequentialPlayback();
        if (
          remaining > this.frameDuration() * 1.5 &&
          !this.inputIsActive() &&
          !this.video.seeking
        ) {
          this.pendingTime = this.playTargetTime;
          this.presentationRecoverySeekCount += 1;
          this.executeLatestSeek();
          return this.video.seeking || this.pendingTime != null;
        }
        return false;
      }
      if (remaining <= tolerance) {
        // Przy ruchu do przodu dekoder może wyprzedzić cel o kilka klatek.
        // Nie cofamy wtedy filmu — powodowałoby to widoczny rollback i seek
        // mimo niezmienionego kierunku wejścia.
        this.pauseSequentialPlayback();
        return false;
      }
      if (
        remaining > this.maxSequentialCatchupSeconds() &&
        !this.inputIsActive()
      ) {
        if (
          this.queueLargeForwardSeek(
            this.playTargetTime,
            this.presentedTime()
          )
        ) {
          return this.video.seeking || this.pendingTime != null;
        }
        return this.startSequentialPlayback();
      }
      return this.startSequentialPlayback();
    }

    renderInterFrameWebm(time) {
      const current = this.presentedTime();
      const delta = time - current;
      const tolerance = this.frameDuration() * 0.75;
      const previousTarget = this.playTargetTime;
      const targetMovedBackward =
        previousTarget != null &&
        time < previousTarget - this.frameDuration() * 0.1;
      const targetChanged =
        previousTarget == null ||
        Math.abs(time - previousTarget) > this.frameDuration();
      this.playTargetTime = time;
      if (targetChanged) this.lastLargeForwardSeekTarget = null;
      this.maxTargetDriftMs = Math.max(
        this.maxTargetDriftMs,
        Math.abs(delta) * 1000
      );

      if (Math.abs(delta) <= tolerance) {
        this.pendingTime = null;
        this.pauseSequentialPlayback();
        return;
      }

      // Kierunek wejścia ma pierwszeństwo przed pozycją dekodera. Gdy film
      // pozostaje za scrollem, cofnięty target może nadal leżeć przed
      // presentedTime; bez tego warunku kontroler błędnie uruchamiał play()
      // do przodu podczas przewijania strony w górę.
      if (targetMovedBackward) {
        this.lastLargeForwardSeekTarget = null;
        this.pauseSequentialPlayback();
        this.pendingTime = time;
        if (!this.video.seeking) this.reverseSeekCount += 1;
        this.executeLatestSeek();
        return;
      }

      if (delta > 0 && !this.video.seeking) {
        if (delta <= this.maxSequentialCatchupSeconds()) {
          this.pendingTime = null;
          this.startSequentialPlayback();
          return;
        }

        if (this.inputIsActive()) {
          this.pendingTime = null;
          this.deferredForwardSeekCount += 1;
          this.startSequentialPlayback();
          return;
        }

        // Duży skok dostaje tylko jeden seek z krótkim pre-rollem. Ostatnie
        // klatki dochodzą już przez play(), więc zatrzymanie nie wygląda jak
        // pojedynczy skok dekodera.
        if (!this.queueLargeForwardSeek(time, current)) {
          this.startSequentialPlayback();
        }
        return;
      }

      if (delta < 0) {
        // Dekoder wyprzedził niezmieniony lub rosnący target. Nie cofamy go
        // wtedy, bo utworzyłoby to rollback mimo ruchu strony w dół.
        this.pendingTime = null;
        this.pauseSequentialPlayback();
        return;
      }

      // Seek już trwa: zachowujemy wyłącznie najnowszy cel. Dla ruchu do
      // przodu również zostawiamy krótki pre-roll zamiast kończyć drugim
      // skokiem dokładnie na klatce docelowej.
      if (delta > 0) {
        if (this.inputIsActive()) {
          this.pendingTime = null;
        } else {
          const preRoll = Math.min(0.14, Math.max(0.08, delta * 0.25));
          this.pendingTime = Math.max(current, time - preRoll);
        }
      } else {
        this.pendingTime = time;
      }
    }

    executeLatestSeek() {
      if (
        this.pendingTime == null ||
        !this.video ||
        this.video.readyState < 1 ||
        this.video.seeking
      ) {
        return;
      }
      const time = this.pendingTime;
      const deadZone = this.config.mp4DeadZoneMs / 1000;
      if (
        this.lastRequestedTime >= 0 &&
        Math.abs(time - this.lastRequestedTime) < deadZone
      ) {
        this.pendingTime = null;
        this.seekSkipped += 1;
        return;
      }
      this.pendingTime = null;
      this.lastRequestedTime = time;
      try {
        this.pauseSequentialPlayback();
        this.video.currentTime = time;
        this.seekExecuted += 1;
      } catch (_error) {
        this.seekErrors += 1;
      }
    }

    renderProgress(progress) {
      const time = this.timeForProgress(progress);
      if (this.interFrameWebm) {
        this.renderInterFrameWebm(time);
        return;
      }
      this.pendingTime = time;
      this.executeLatestSeek();
    }

    hasPendingWork() {
      if (this.pendingTime != null) {
        this.executeLatestSeek();
        if (this.pendingTime != null || this.video.seeking) return true;
      }
      const sequential = this.updateSequentialPlayback();
      return (
        sequential ||
        this.sequentialPlaybackActive ||
        this.playPromisePending ||
        Boolean(this.video?.seeking)
      );
    }

    trackPresentedFrames() {
      if (!this.video?.requestVideoFrameCallback) return;
      const onFrame = (now, metadata) => {
        if (this.destroyed) return;
        const frame = clamp(
          Math.round(metadata.mediaTime * this.fps),
          0,
          this.frameCount - 1
        );
        if (this.lastPresentedFrame >= 0 && frame !== this.lastPresentedFrame) {
          this.skippedFrames += Math.max(
            0,
            Math.abs(frame - this.lastPresentedFrame) - 1
          );
        }
        this.lastPresentedFrame = frame;
        if (this.sequentialPlaybackActive) {
          this.sequentialPlaybackFrames += 1;
          this.updateSequentialPlayback();
          this.scheduler.request();
        }
        this.renderedHistory.push({ frame, at: now });
        this.trimHistory(now);
        this.root.classList.remove('has-scroll-frame-error');
        this.videoFrameCallbackId =
          this.video.requestVideoFrameCallback(onFrame);
      };
      this.videoFrameCallbackId = this.video.requestVideoFrameCallback(onFrame);
    }

    trimHistory(now = performance.now()) {
      const cutoff = now - 1000;
      while (this.renderedHistory[0]?.at < cutoff) {
        this.renderedHistory.shift();
      }
    }

    writeDebugDataset() {
      super.writeDebugDataset();
      this.trimHistory();
      this.video.dataset.targetFrame = String(
        Math.round(this.motion.renderedProgress * (this.frameCount - 1))
      );
      this.video.dataset.renderedFrame = String(this.lastPresentedFrame);
      this.video.dataset.requestedTime = String(
        Math.max(0, this.lastRequestedTime).toFixed(4)
      );
      this.video.dataset.uniqueFramesLastSecond = String(
        new Set(this.renderedHistory.map((entry) => entry.frame)).size
      );
      this.video.dataset.skippedFrames = String(this.skippedFrames);
      this.video.dataset.seekExecuted = String(this.seekExecuted);
      this.video.dataset.seekSkipped = String(this.seekSkipped);
      this.video.dataset.seekErrors = String(this.seekErrors);
      this.video.dataset.seekPending = String(this.pendingTime != null);
      this.video.dataset.seeking = String(this.video.seeking);
      this.video.dataset.readyState = String(this.video.readyState);
      this.video.dataset.webmInterFrame = String(this.interFrameWebm);
      this.video.dataset.sequentialPlayback = String(
        this.sequentialPlaybackActive
      );
      this.video.dataset.sequentialPlaybackStarts = String(
        this.sequentialPlaybackStarts
      );
      this.video.dataset.sequentialPlaybackFrames = String(
        this.sequentialPlaybackFrames
      );
      this.video.dataset.largeForwardSeeks = String(
        this.largeForwardSeekCount
      );
      this.video.dataset.deferredForwardSeeks = String(
        this.deferredForwardSeekCount
      );
      this.video.dataset.presentationRecoverySeeks = String(
        this.presentationRecoverySeekCount
      );
      this.video.dataset.reverseSeeks = String(this.reverseSeekCount);
      this.video.dataset.maxTargetDriftMs = String(
        this.maxTargetDriftMs.toFixed(1)
      );
      this.video.dataset.keyframeInterval = String(
        this.sourceMetadata.keyframeInterval ?? ''
      );
      this.video.dataset.intraOnly = String(
        this.sourceMetadata.intraOnly ?? ''
      );
      this.video.dataset.sourceDelivery = this.sourceDelivery;
      this.video.dataset.prewarmCompleted = String(this.prewarmCompleted);
      this.video.dataset.sourceHasAlpha = String(
        this.sourceMetadata.hasAlpha === true
      );
      this.video.dataset.alphaMode =
        this.sourceMetadata.alphaMode || 'unknown';
    }

    diagnostics() {
      this.trimHistory();
      return {
        ...super.diagnostics(),
        targetFrame: Math.round(
          this.motion.renderedProgress * (this.frameCount - 1)
        ),
        renderedFrame: this.lastPresentedFrame,
        sourceFps: this.fps,
        sourceFrameCount: this.frameCount,
        uniqueFramesLastSecond: new Set(
          this.renderedHistory.map((entry) => entry.frame)
        ).size,
        skippedFrames: this.skippedFrames,
        currentTime: this.video?.currentTime || 0,
        requestedTime: this.lastRequestedTime,
        duration: this.duration,
        readyState: this.video?.readyState || 0,
        seeking: Boolean(this.video?.seeking),
        seekExecuted: this.seekExecuted,
        seekSkipped: this.seekSkipped,
        seekErrors: this.seekErrors,
        seekPending: this.pendingTime != null,
        webmInterFrame: this.interFrameWebm,
        sequentialPlayback: this.sequentialPlaybackActive,
        sequentialPlaybackStarts: this.sequentialPlaybackStarts,
        sequentialPlaybackStops: this.sequentialPlaybackStops,
        sequentialPlaybackFrames: this.sequentialPlaybackFrames,
        largeForwardSeeks: this.largeForwardSeekCount,
        deferredForwardSeeks: this.deferredForwardSeekCount,
        presentationRecoverySeeks: this.presentationRecoverySeekCount,
        reverseSeeks: this.reverseSeekCount,
        maxTargetDriftMs: this.maxTargetDriftMs,
        sourceDelivery: this.sourceDelivery,
        prewarmCompleted: this.prewarmCompleted,
        blobBytes: this.objectUrl ? 'full-source' : 0,
      };
    }

    destroy() {
      super.destroy();
      this.pauseSequentialPlayback();
      if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
      if (this.videoFrameCallbackId && this.video?.cancelVideoFrameCallback) {
        this.video.cancelVideoFrameCallback(this.videoFrameCallbackId);
      }
    }
  }

  class CentralScheduler {
    constructor() {
      this.controllers = new Map();
      this.rafId = 0;
      this.lastNow = 0;
      this.measureRequested = false;
      this.reducedMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      );
      this.metrics = {
        pageFps: 0,
        averageFrameMs: 0,
        worstFrameMs: 0,
        frameIntervals: [],
        schedulerFrames: 0,
      };
      this.tick = this.tick.bind(this);
    }

    request() {
      if (this.rafId || document.hidden) return;
      this.rafId = window.requestAnimationFrame(this.tick);
    }

    requestMeasure() {
      this.measureRequested = true;
      this.request();
    }

    captureScroll(scrollY = window.scrollY, now = performance.now()) {
      this.controllers.forEach((controller) => {
        if (controller.isNearViewport) {
          controller.captureScroll(scrollY, now);
        }
      });
      this.request();
    }

    recordFrame(now) {
      if (this.lastNow) {
        const interval = now - this.lastNow;
        if (interval < 250) {
          this.metrics.frameIntervals.push(interval);
          if (this.metrics.frameIntervals.length > 120) {
            this.metrics.frameIntervals.shift();
          }
          const total = this.metrics.frameIntervals.reduce(
            (sum, value) => sum + value,
            0
          );
          this.metrics.pageFps =
            (this.metrics.frameIntervals.length * 1000) / Math.max(1, total);
          this.metrics.averageFrameMs =
            total / this.metrics.frameIntervals.length;
          this.metrics.worstFrameMs = Math.max(
            ...this.metrics.frameIntervals
          );
        }
      }
      this.lastNow = now;
      this.metrics.schedulerFrames += 1;
    }

    tick(now) {
      this.rafId = 0;
      const deltaTime = this.lastNow
        ? clamp(now - this.lastNow, 1, 50)
        : 16.67;
      this.recordFrame(now);
      if (this.measureRequested) {
        this.measureRequested = false;
        this.controllers.forEach((controller) => controller.measure());
        const scrollY = window.scrollY;
        this.controllers.forEach((controller) =>
          controller.captureScroll(scrollY, now, true)
        );
      }
      const context = {
        now,
        deltaTime,
        reducedMotion: this.reducedMotion.matches || DEBUG_REDUCED_MOTION,
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        devicePixelRatio: window.devicePixelRatio || 1,
      };
      let needsNext = false;
      this.controllers.forEach((controller) => {
        needsNext = controller.tick(context) || needsNext;
      });
      if (needsNext || (DEBUG && this.hasVisibleController())) this.request();
    }

    hasVisibleController() {
      return [...this.controllers.values()].some(
        (controller) => controller.isNearViewport && !controller.destroyed
      );
    }

    add(root, controller) {
      this.controllers.set(root, controller);
      this.request();
    }

    remove(root) {
      const controller = this.controllers.get(root);
      controller?.destroy();
      this.controllers.delete(root);
    }

    diagnostics() {
      return {
        centralRafActive: Boolean(this.rafId),
        controllerCount: this.controllers.size,
        reducedMotion: this.reducedMotion.matches || DEBUG_REDUCED_MOTION,
        pageFps: this.metrics.pageFps,
        rafHz: this.metrics.pageFps,
        pageAverageFrameMs: this.metrics.averageFrameMs,
        pageWorstFrameMs: this.metrics.worstFrameMs,
        schedulerFrames: this.metrics.schedulerFrames,
        catalogStatus,
        controllers: [...this.controllers.values()].map((controller) =>
          controller.diagnostics()
        ),
      };
    }
  }

  const scheduler = new CentralScheduler();

  function controllerSourceKey(root) {
    const element =
      root.querySelector(VIDEO_SELECTOR) || root.querySelector(CANVAS_SELECTOR);
    const source = element?.matches(VIDEO_SELECTOR)
      ? element.querySelector('source')?.getAttribute('src') ||
        element.getAttribute('src') ||
        ''
      : element?.dataset.frameManifest || '';
    const motion = [
      root.dataset.scrollVideoContainer,
      root.dataset.motionPreset,
      root.dataset.motionSpeed,
      root.dataset.motionEasing,
      root.dataset.motionSmoothingMs,
      root.dataset.motionLagMs,
      root.dataset.motionInertia,
      root.dataset.motionDamping,
      root.dataset.motionMaxCatchup,
      root.dataset.motionStopBehavior,
      root.dataset.motionDirection,
      root.dataset.motionMaterialStart,
      root.dataset.motionMaterialEnd,
      root.dataset.motionInterpolation,
      root.dataset.motionFrameRounding,
      root.dataset.motionMp4DeadZoneMs,
      root.dataset.motionWebpDeadZoneFrames,
      root.dataset.motionPreloadRadius,
      root.dataset.motionCacheFrames,
      root.dataset.motionTailPacing,
      root.dataset.motionTailWindowFrames,
      root.dataset.backgroundMode,
      root.dataset.backgroundValue,
      root.dataset.forceTransparent,
    ].join('|');
    return `${source}|${motion}|${catalogStatus}|${DEBUG_PRESET}`;
  }

  function createController(root) {
    const element =
      root.querySelector(VIDEO_SELECTOR) || root.querySelector(CANVAS_SELECTOR);
    const controller = element?.matches(VIDEO_SELECTOR)
      ? new ScrollNativeVideo(root, scheduler)
      : new ScrollFrameCanvas(root, scheduler);
    controller.instanceKey = controllerSourceKey(root);
    return controller;
  }

  function prune() {
    scheduler.controllers.forEach((_controller, root) => {
      if (!root.isConnected) scheduler.remove(root);
    });
  }

  function refresh(scope = document) {
    scope.querySelectorAll(ROOT_SELECTOR).forEach((root) => {
      const existing = scheduler.controllers.get(root);
      const key = controllerSourceKey(root);
      if (existing && existing.instanceKey !== key) {
        scheduler.remove(root);
      }
      if (!scheduler.controllers.has(root)) {
        scheduler.add(root, createController(root));
      }
    });
    prune();
  }

  function resolveRoot(rootOrSelector) {
    if (rootOrSelector instanceof Element) {
      return rootOrSelector.matches(ROOT_SELECTOR)
        ? rootOrSelector
        : rootOrSelector.closest(ROOT_SELECTOR);
    }
    return document.querySelector(String(rootOrSelector));
  }

  function registerElement(rootOrSelector, element) {
    const root = resolveRoot(rootOrSelector);
    const controller = root ? scheduler.controllers.get(root) : null;
    if (!controller) {
      throw new Error('Film-scroll root is not registered.');
    }
    return controller.registerAnimatedElement(element);
  }

  function setProgress(rootOrSelector, progress, options = {}) {
    const root = resolveRoot(rootOrSelector);
    const controller = root ? scheduler.controllers.get(root) : null;
    if (!controller) return false;
    controller.setExternalProgress(
      progress,
      performance.now(),
      Boolean(options.immediate)
    );
    return true;
  }

  if (window[API_KEY]?.version >= 2) {
    window[API_KEY].refresh();
    return;
  }

  window[API_KEY] = {
    version: 2,
    refresh,
    update: () => scheduler.captureScroll(),
    diagnostics: () => scheduler.diagnostics(),
    registerElement,
    setProgress,
    mapProgress,
    applyEasing,
    presets: () => motionCatalog,
  };

  let refreshQueued = false;
  const requestRefresh = () => {
    if (!runtimeStarted) return;
    if (refreshQueued) return;
    refreshQueued = true;
    queueMicrotask(() => {
      refreshQueued = false;
      refresh();
    });
  };

  if ('MutationObserver' in window) {
    const mutationObserver = new MutationObserver(requestRefresh);
    mutationObserver.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: [
        'data-frame-manifest',
        'data-frame-quality',
        'data-scroll-video-container',
        'data-video-container',
        'data-motion-preset',
        'data-motion-speed',
        'data-motion-easing',
        'data-motion-smoothing-ms',
        'data-motion-lag-ms',
        'data-motion-inertia',
        'data-motion-damping',
        'data-motion-max-catchup',
        'data-motion-stop-behavior',
        'data-motion-direction',
        'data-motion-material-start',
        'data-motion-material-end',
        'data-motion-interpolation',
        'data-motion-frame-rounding',
        'data-motion-mp4-dead-zone-ms',
        'data-motion-webp-dead-zone-frames',
        'data-motion-preload-radius',
        'data-motion-cache-frames',
        'data-motion-tail-pacing',
        'data-motion-tail-window-frames',
        'data-background-mode',
        'data-background-value',
        'data-force-transparent',
      ],
    });
  }

  window.addEventListener(
    'scroll',
    () => scheduler.captureScroll(window.scrollY, performance.now()),
    { passive: true }
  );
  window.addEventListener('resize', () => scheduler.requestMeasure(), {
    passive: true,
  });
  window.addEventListener('pageshow', () => scheduler.requestMeasure());
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
      scheduler.lastNow = 0;
      scheduler.requestMeasure();
    }
  });
  document.addEventListener('shopify:section:load', (event) =>
    refresh(event.target)
  );
  document.addEventListener('shopify:section:unload', prune);

  const start = async () => {
    await loadMotionCatalog();
    runtimeStarted = true;
    refresh();
    scheduler.requestMeasure();
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
