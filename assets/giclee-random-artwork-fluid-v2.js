/*
 * Losuj Obraz V5 — Elegant fluid cursor smoke.
 * Framework-free port of Pedzel_Alchemy variant 2. Uses the theme Three.js module.
 */

const BASE_CONFIG = Object.freeze({
  SIM_RESOLUTION: 128,
  DYE_RESOLUTION: 1024,
  DENSITY_DISSIPATION: 1.55,
  VELOCITY_DISSIPATION: 1.15,
  PRESSURE: 0.75,
  PRESSURE_ITERATIONS: 20,
  CURL: 14,
  SPLAT_RADIUS: 0.14,
  SPLAT_FORCE: 720,
  BLOOM_ITERATIONS: 6,
  BLOOM_RESOLUTION: 256,
  BLOOM_INTENSITY: 0.1,
  BLOOM_THRESHOLD: 0.96,
  BLOOM_SOFT_KNEE: 0.5,
  SUNRAYS_RESOLUTION: 196,
  SUNRAYS_WEIGHT: 0.18,
  AUTO_SPLAT_INTERVAL: 5.5,
  INIT_SPLATS_MIN: 2,
  INIT_SPLATS_RANGE: 3,
  AUTO_SPLATS_MIN: 1,
  AUTO_SPLATS_RANGE: 1,
  AUTO_SPLAT_COLOR_BOOST: 3.2,
  SCROLL_FADE: 0.7,
});

const ELEGANT_PALETTE = Object.freeze([
  { r: 0.42, g: 0.55, b: 0.58 },
  { r: 0.55, g: 0.5, b: 0.62 },
  { r: 0.62, g: 0.56, b: 0.42 },
  { r: 0.35, g: 0.42, b: 0.52 },
  { r: 0.5, g: 0.48, b: 0.45 },
]);

const PRESETS = Object.freeze({
  elegant: Object.freeze({
    config: Object.freeze({}),
    palette: ELEGANT_PALETTE,
    colorIntensity: 0.045,
    opacity: 0.72,
  }),
  gallery_mist: Object.freeze({
    config: Object.freeze({
      DENSITY_DISSIPATION: 1.15,
      VELOCITY_DISSIPATION: 1,
      CURL: 9,
      SPLAT_RADIUS: 0.22,
      SPLAT_FORCE: 480,
      BLOOM_INTENSITY: 0.06,
      SUNRAYS_WEIGHT: 0.12,
      AUTO_SPLAT_INTERVAL: 7.5,
      INIT_SPLATS_MIN: 1,
      INIT_SPLATS_RANGE: 2,
      AUTO_SPLAT_COLOR_BOOST: 2.4,
    }),
    palette: Object.freeze([
      { r: 0.66, g: 0.59, b: 0.5 },
      { r: 0.54, g: 0.62, b: 0.6 },
      { r: 0.61, g: 0.55, b: 0.65 },
      { r: 0.58, g: 0.57, b: 0.54 },
    ]),
    colorIntensity: 0.038,
    opacity: 0.58,
  }),
  silk: Object.freeze({
    config: Object.freeze({
      DENSITY_DISSIPATION: 0.82,
      VELOCITY_DISSIPATION: 0.92,
      CURL: 22,
      SPLAT_RADIUS: 0.2,
      SPLAT_FORCE: 1050,
      BLOOM_INTENSITY: 0.2,
      SUNRAYS_WEIGHT: 0.3,
      AUTO_SPLAT_INTERVAL: 4,
      INIT_SPLATS_MIN: 3,
      INIT_SPLATS_RANGE: 4,
      AUTO_SPLAT_COLOR_BOOST: 5,
    }),
    palette: Object.freeze([
      { r: 0.48, g: 0.5, b: 0.72 },
      { r: 0.65, g: 0.49, b: 0.7 },
      { r: 0.43, g: 0.62, b: 0.7 },
      { r: 0.7, g: 0.58, b: 0.62 },
    ]),
    colorIntensity: 0.075,
    opacity: 0.82,
  }),
  whisper: Object.freeze({
    config: Object.freeze({
      DENSITY_DISSIPATION: 2.1,
      VELOCITY_DISSIPATION: 1.3,
      CURL: 6,
      SPLAT_RADIUS: 0.1,
      SPLAT_FORCE: 350,
      BLOOM_INTENSITY: 0.03,
      SUNRAYS_WEIGHT: 0.05,
      AUTO_SPLAT_INTERVAL: 9,
      INIT_SPLATS_MIN: 1,
      INIT_SPLATS_RANGE: 1,
      AUTO_SPLAT_COLOR_BOOST: 1.8,
    }),
    palette: Object.freeze([
      { r: 0.5, g: 0.52, b: 0.54 },
      { r: 0.57, g: 0.55, b: 0.52 },
      { r: 0.48, g: 0.51, b: 0.5 },
    ]),
    colorIntensity: 0.025,
    opacity: 0.42,
  }),
});

const controllers = new WeakMap();

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function numberSetting(dataset, name, fallback, min, max) {
  const value = Number(dataset[name]);
  return Number.isFinite(value) ? clamp(value, min, max) : fallback;
}

function readSettings(root) {
  const dataset = root.dataset;
  const presetKey = Object.prototype.hasOwnProperty.call(PRESETS, dataset.cursorSmokePreset)
    ? dataset.cursorSmokePreset
    : "elegant";
  const preset = PRESETS[presetKey];
  const quality = ["low", "standard", "high"].includes(dataset.cursorSmokeQuality)
    ? dataset.cursorSmokeQuality
    : "standard";
  const qualityResolution = { low: 512, standard: 1024, high: 1536 }[quality];
  const intensity = numberSetting(dataset, "cursorSmokeIntensity", 100, 25, 200) / 100;
  const opacity = numberSetting(dataset, "cursorSmokeOpacity", 100, 20, 150) / 100;
  const size = numberSetting(dataset, "cursorSmokeSize", 100, 50, 200) / 100;
  const force = numberSetting(dataset, "cursorSmokeForce", 100, 25, 200) / 100;
  const persistence = numberSetting(dataset, "cursorSmokePersistence", 100, 50, 200) / 100;
  const swirl = numberSetting(dataset, "cursorSmokeSwirl", 100, 0, 200) / 100;
  const bloom = numberSetting(dataset, "cursorSmokeBloom", 100, 0, 200) / 100;
  const autoFrequency = numberSetting(dataset, "cursorSmokeAutoFrequency", 100, 25, 200) / 100;
  const config = {
    ...BASE_CONFIG,
    ...preset.config,
    DYE_RESOLUTION: qualityResolution,
    DENSITY_DISSIPATION: (preset.config.DENSITY_DISSIPATION || BASE_CONFIG.DENSITY_DISSIPATION) / persistence,
    SPLAT_RADIUS: (preset.config.SPLAT_RADIUS || BASE_CONFIG.SPLAT_RADIUS) * size,
    SPLAT_FORCE: (preset.config.SPLAT_FORCE || BASE_CONFIG.SPLAT_FORCE) * force,
    CURL: (preset.config.CURL ?? BASE_CONFIG.CURL) * swirl,
    BLOOM_INTENSITY: (preset.config.BLOOM_INTENSITY ?? BASE_CONFIG.BLOOM_INTENSITY) * bloom,
    SUNRAYS_WEIGHT: (preset.config.SUNRAYS_WEIGHT ?? BASE_CONFIG.SUNRAYS_WEIGHT) * bloom,
    AUTO_SPLAT_INTERVAL: (preset.config.AUTO_SPLAT_INTERVAL || BASE_CONFIG.AUTO_SPLAT_INTERVAL) / autoFrequency,
  };
  const color = () => {
    const selected = preset.palette[Math.floor(Math.random() * preset.palette.length)];
    const multiplier = preset.colorIntensity * intensity;
    return { r: selected.r * multiplier, g: selected.g * multiplier, b: selected.b * multiplier };
  };

  return {
    config,
    color,
    opacity: clamp(preset.opacity * opacity, 0, 1),
    autoEnabled: dataset.cursorSmokeAutoEnabled !== "false",
  };
}

function getResolution(resolution, width, height) {
  let aspect = width / height;
  if (aspect < 1) aspect = 1 / aspect;
  const min = Math.round(resolution);
  const max = Math.round(resolution * aspect);
  return width > height ? { width: max, height: min } : { width: min, height: max };
}

class FluidSimulation {
  constructor(renderer, width, height, THREE, shaders, settings) {
    this.renderer = renderer;
    this.width = width;
    this.height = height;
    this.THREE = THREE;
    this.shaders = shaders;
    this.config = settings.config;
    this.color = settings.color;
    this.autoEnabled = settings.autoEnabled;
    this.autoSplatTimer = 0;
    this.bloomFBOs = [];

    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2));
    this.mesh.frustumCulled = false;
    this.scene.add(this.mesh);

    const vec2 = () => ({ value: new THREE.Vector2() });
    const vec3 = () => ({ value: new THREE.Vector3() });
    const texture = () => ({ value: null });
    const number = (value = 0) => ({ value });
    const material = (vertexShader, fragmentShader, uniforms) =>
      new THREE.ShaderMaterial({ vertexShader, fragmentShader, uniforms, depthTest: false, depthWrite: false });

    this.curlMaterial = material(shaders.baseVertex, shaders.curlFrag, {
      texelSize: vec2(), uVelocity: texture(),
    });
    this.vorticityMaterial = material(shaders.baseVertex, shaders.vorticityFrag, {
      texelSize: vec2(), uVelocity: texture(), uCurl: texture(), curl: number(this.config.CURL), dt: number(),
    });
    this.divergenceMaterial = material(shaders.baseVertex, shaders.divergenceFrag, {
      texelSize: vec2(), uVelocity: texture(),
    });
    this.pressureMaterial = material(shaders.baseVertex, shaders.pressureFrag, {
      texelSize: vec2(), uPressure: texture(), uDivergence: texture(),
    });
    this.gradientMaterial = material(shaders.baseVertex, shaders.gradientSubtractFrag, {
      texelSize: vec2(), uPressure: texture(), uVelocity: texture(),
    });
    this.advectionMaterial = material(shaders.baseVertex, shaders.advectionFrag, {
      texelSize: vec2(), uVelocity: texture(), uSource: texture(), dt: number(), dissipation: number(),
    });
    this.splatMaterial = material(shaders.baseVertex, shaders.splatFrag, {
      texelSize: vec2(), uTarget: texture(), aspectRatio: number(), color: vec3(), point: vec2(), radius: number(),
    });
    this.clearMaterial = material(shaders.baseVertex, shaders.clearFrag, {
      texelSize: vec2(), uTexture: texture(), value: number(),
    });
    this.bloomPrefilterMaterial = material(shaders.baseVertex, shaders.bloomPrefilterFrag, {
      texelSize: vec2(), uTexture: texture(), curve: vec3(), threshold: number(),
    });
    this.bloomBlurMaterial = material(shaders.baseVertex, shaders.bloomBlurFrag, {
      texelSize: vec2(), uTexture: texture(),
    });
    this.bloomFinalMaterial = material(shaders.baseVertex, shaders.bloomFinalFrag, {
      texelSize: vec2(), uTexture: texture(), intensity: number(),
    });
    this.sunraysMaskMaterial = material(shaders.baseVertex, shaders.sunraysMaskFrag, {
      texelSize: vec2(), uTexture: texture(),
    });
    this.sunraysMaterial = material(shaders.baseVertex, shaders.sunraysFrag, {
      texelSize: vec2(), uTexture: texture(), weight: number(),
    });
    this.blurMaterial = material(shaders.blurVertex, shaders.blurFrag, {
      texelSize: vec2(), uTexture: texture(),
    });

    this.materials = [
      this.curlMaterial,
      this.vorticityMaterial,
      this.divergenceMaterial,
      this.pressureMaterial,
      this.gradientMaterial,
      this.advectionMaterial,
      this.splatMaterial,
      this.clearMaterial,
      this.bloomPrefilterMaterial,
      this.bloomBlurMaterial,
      this.bloomFinalMaterial,
      this.sunraysMaskMaterial,
      this.sunraysMaterial,
      this.blurMaterial,
    ];

    this.initFBOs();
    if (this.autoEnabled) {
      this.multipleSplats(
        Math.floor(this.config.INIT_SPLATS_RANGE * Math.random()) + this.config.INIT_SPLATS_MIN,
      );
    }
  }

  createFBO(width, height, filter) {
    const THREE = this.THREE;
    const target = new THREE.WebGLRenderTarget(width, height, {
      minFilter: filter,
      magFilter: filter,
      type: THREE.HalfFloatType,
      format: THREE.RGBAFormat,
      wrapS: THREE.ClampToEdgeWrapping,
      wrapT: THREE.ClampToEdgeWrapping,
      depthBuffer: false,
      stencilBuffer: false,
    });
    return { target, texelSizeX: 1 / width, texelSizeY: 1 / height };
  }

  createDoubleFBO(width, height, filter) {
    let read = this.createFBO(width, height, filter);
    let write = this.createFBO(width, height, filter);
    return {
      get read() { return read; },
      get write() { return write; },
      texelSizeX: 1 / width,
      texelSizeY: 1 / height,
      swap() { const previous = read; read = write; write = previous; },
    };
  }

  initFBOs() {
    const THREE = this.THREE;
    const sim = getResolution(this.config.SIM_RESOLUTION, this.width, this.height);
    const dyeResolution = /Mobi|Android/i.test(navigator.userAgent)
      ? Math.min(512, this.config.DYE_RESOLUTION)
      : this.config.DYE_RESOLUTION;
    const dye = getResolution(dyeResolution, this.width, this.height);
    this.velocity = this.createDoubleFBO(sim.width, sim.height, THREE.LinearFilter);
    this.dye = this.createDoubleFBO(dye.width, dye.height, THREE.LinearFilter);
    this.pressure = this.createDoubleFBO(sim.width, sim.height, THREE.NearestFilter);
    this.curl = this.createFBO(sim.width, sim.height, THREE.NearestFilter);
    this.divergence = this.createFBO(sim.width, sim.height, THREE.NearestFilter);

    const bloom = getResolution(this.config.BLOOM_RESOLUTION, this.width, this.height);
    this.bloom = this.createFBO(bloom.width, bloom.height, THREE.LinearFilter);
    for (let index = 0; index < this.config.BLOOM_ITERATIONS; index += 1) {
      const width = bloom.width >> (index + 1);
      const height = bloom.height >> (index + 1);
      if (width < 2 || height < 2) break;
      this.bloomFBOs.push(this.createFBO(width, height, THREE.LinearFilter));
    }

    const sunrays = getResolution(this.config.SUNRAYS_RESOLUTION, this.width, this.height);
    this.sunrays = this.createFBO(sunrays.width, sunrays.height, THREE.LinearFilter);
    this.sunraysTemp = this.createFBO(sunrays.width, sunrays.height, THREE.LinearFilter);
  }

  blit(material, target) {
    this.mesh.material = material;
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.scene, this.camera);
  }

  step(dt) {
    const velocity = this.velocity;
    const setTexel = (material, x, y) => material.uniforms.texelSize.value.set(x, y);

    setTexel(this.curlMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.curlMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.blit(this.curlMaterial, this.curl.target);

    setTexel(this.vorticityMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.vorticityMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.vorticityMaterial.uniforms.uCurl.value = this.curl.target.texture;
    this.vorticityMaterial.uniforms.dt.value = dt;
    this.blit(this.vorticityMaterial, velocity.write.target);
    velocity.swap();

    setTexel(this.divergenceMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.divergenceMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.blit(this.divergenceMaterial, this.divergence.target);

    setTexel(this.clearMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.clearMaterial.uniforms.uTexture.value = this.pressure.read.target.texture;
    this.clearMaterial.uniforms.value.value = this.config.PRESSURE;
    this.blit(this.clearMaterial, this.pressure.write.target);
    this.pressure.swap();

    setTexel(this.pressureMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.pressureMaterial.uniforms.uDivergence.value = this.divergence.target.texture;
    for (let index = 0; index < this.config.PRESSURE_ITERATIONS; index += 1) {
      this.pressureMaterial.uniforms.uPressure.value = this.pressure.read.target.texture;
      this.blit(this.pressureMaterial, this.pressure.write.target);
      this.pressure.swap();
    }

    setTexel(this.gradientMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.gradientMaterial.uniforms.uPressure.value = this.pressure.read.target.texture;
    this.gradientMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.blit(this.gradientMaterial, velocity.write.target);
    velocity.swap();

    setTexel(this.advectionMaterial, velocity.texelSizeX, velocity.texelSizeY);
    this.advectionMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.advectionMaterial.uniforms.uSource.value = velocity.read.target.texture;
    this.advectionMaterial.uniforms.dt.value = dt;
    this.advectionMaterial.uniforms.dissipation.value = this.config.VELOCITY_DISSIPATION;
    this.blit(this.advectionMaterial, velocity.write.target);
    velocity.swap();

    this.advectionMaterial.uniforms.uVelocity.value = velocity.read.target.texture;
    this.advectionMaterial.uniforms.uSource.value = this.dye.read.target.texture;
    this.advectionMaterial.uniforms.dissipation.value = this.config.DENSITY_DISSIPATION;
    this.blit(this.advectionMaterial, this.dye.write.target);
    this.dye.swap();
  }

  applyBloom() {
    if (this.bloomFBOs.length < 2) return;
    const knee = this.config.BLOOM_THRESHOLD * this.config.BLOOM_SOFT_KNEE + 0.0001;
    this.bloomPrefilterMaterial.uniforms.uTexture.value = this.dye.read.target.texture;
    this.bloomPrefilterMaterial.uniforms.curve.value.set(this.config.BLOOM_THRESHOLD - knee, 2 * knee, 0.25 / knee);
    this.bloomPrefilterMaterial.uniforms.threshold.value = this.config.BLOOM_THRESHOLD;
    this.blit(this.bloomPrefilterMaterial, this.bloom.target);

    let last = this.bloom;
    for (const fbo of this.bloomFBOs) {
      this.bloomBlurMaterial.uniforms.texelSize.value.set(last.texelSizeX, last.texelSizeY);
      this.bloomBlurMaterial.uniforms.uTexture.value = last.target.texture;
      this.blit(this.bloomBlurMaterial, fbo.target);
      last = fbo;
    }

    const material = this.bloomBlurMaterial;
    material.blending = this.THREE.CustomBlending;
    material.blendSrc = this.THREE.OneFactor;
    material.blendDst = this.THREE.OneFactor;
    material.transparent = true;
    for (let index = this.bloomFBOs.length - 2; index >= 0; index -= 1) {
      const fbo = this.bloomFBOs[index];
      material.uniforms.texelSize.value.set(last.texelSizeX, last.texelSizeY);
      material.uniforms.uTexture.value = last.target.texture;
      this.blit(material, fbo.target);
      last = fbo;
    }
    material.blending = this.THREE.NormalBlending;
    material.transparent = false;

    this.bloomFinalMaterial.uniforms.texelSize.value.set(last.texelSizeX, last.texelSizeY);
    this.bloomFinalMaterial.uniforms.uTexture.value = last.target.texture;
    this.bloomFinalMaterial.uniforms.intensity.value = this.config.BLOOM_INTENSITY;
    this.blit(this.bloomFinalMaterial, this.bloom.target);
  }

  applySunrays() {
    this.sunraysMaskMaterial.uniforms.uTexture.value = this.dye.read.target.texture;
    this.blit(this.sunraysMaskMaterial, this.dye.write.target);
    this.sunraysMaterial.uniforms.weight.value = this.config.SUNRAYS_WEIGHT;
    this.sunraysMaterial.uniforms.uTexture.value = this.dye.write.target.texture;
    this.blit(this.sunraysMaterial, this.sunrays.target);
    this.blurMaterial.uniforms.texelSize.value.set(this.sunrays.texelSizeX, 0);
    this.blurMaterial.uniforms.uTexture.value = this.sunrays.target.texture;
    this.blit(this.blurMaterial, this.sunraysTemp.target);
    this.blurMaterial.uniforms.texelSize.value.set(0, this.sunrays.texelSizeY);
    this.blurMaterial.uniforms.uTexture.value = this.sunraysTemp.target.texture;
    this.blit(this.blurMaterial, this.sunrays.target);
  }

  splat(x, y, dx, dy, color) {
    const aspect = this.width / this.height;
    let radius = this.config.SPLAT_RADIUS / 100;
    if (aspect > 1) radius *= aspect;
    this.splatMaterial.uniforms.uTarget.value = this.velocity.read.target.texture;
    this.splatMaterial.uniforms.aspectRatio.value = aspect;
    this.splatMaterial.uniforms.point.value.set(x, y);
    this.splatMaterial.uniforms.color.value.set(dx, dy, 0);
    this.splatMaterial.uniforms.radius.value = radius;
    this.blit(this.splatMaterial, this.velocity.write.target);
    this.velocity.swap();
    this.splatMaterial.uniforms.uTarget.value = this.dye.read.target.texture;
    this.splatMaterial.uniforms.color.value.set(color.r, color.g, color.b);
    this.blit(this.splatMaterial, this.dye.write.target);
    this.dye.swap();
  }

  multipleSplats(amount) {
    for (let index = 0; index < amount; index += 1) {
      const color = this.color();
      color.r *= this.config.AUTO_SPLAT_COLOR_BOOST;
      color.g *= this.config.AUTO_SPLAT_COLOR_BOOST;
      color.b *= this.config.AUTO_SPLAT_COLOR_BOOST;
      this.splat(
        Math.random(),
        Math.random(),
        1000 * (Math.random() - 0.5),
        1000 * (Math.random() - 0.5),
        color,
      );
    }
  }

  dispose() {
    const targets = [
      this.velocity.read,
      this.velocity.write,
      this.dye.read,
      this.dye.write,
      this.pressure.read,
      this.pressure.write,
      this.curl,
      this.divergence,
      this.bloom,
      ...this.bloomFBOs,
      this.sunrays,
      this.sunraysTemp,
    ];
    targets.forEach((fbo) => fbo.target.dispose());
    this.mesh.geometry.dispose();
    this.materials.forEach((material) => material.dispose());
  }
}

class ElegantFluidController {
  constructor(root, THREE, shaders, settings) {
    this.root = root;
    this.THREE = THREE;
    this.shaders = shaders;
    this.settings = settings;
    this.sceneElement = root.querySelector('[data-grw-scene]');
    this.pointer = {
      x: 0,
      y: 0,
      previousX: 0,
      previousY: 0,
      moved: false,
      color: settings.color(),
    };
    this.frame = 0;
    this.lastTime = performance.now();
    this.visible = true;
    this.destroyed = false;

    this.onPointerMove = this.onPointerMove.bind(this);
    this.onScroll = this.onScroll.bind(this);
    this.onVisibilityChange = this.onVisibilityChange.bind(this);
    this.tick = this.tick.bind(this);
    this.resize = this.resize.bind(this);

    this.canvas = document.createElement('canvas');
    this.canvas.className = 'giclee-random-artwork__fluid-smoke';
    this.canvas.dataset.grwFluidSmoke = '';
    this.canvas.setAttribute('aria-hidden', 'true');
    this.sceneElement.appendChild(this.canvas);

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      alpha: true,
      depth: false,
      stencil: false,
      antialias: false,
      preserveDrawingBuffer: false,
      powerPreference: 'high-performance',
    });
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

    this.displayScene = new THREE.Scene();
    this.displayCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.displayMaterial = new THREE.ShaderMaterial({
      vertexShader: shaders.baseVertex,
      fragmentShader: shaders.displayFrag,
      uniforms: {
        texelSize: { value: new THREE.Vector2() },
        uTexture: { value: null },
        uBloom: { value: null },
        uSunrays: { value: null },
      },
      defines: { SHADING: '', BLOOM: '', SUNRAYS: '' },
      transparent: true,
      depthTest: false,
      depthWrite: false,
      blending: THREE.CustomBlending,
      blendSrc: THREE.OneFactor,
      blendDst: THREE.OneMinusSrcAlphaFactor,
      blendEquation: THREE.AddEquation,
    });
    this.displayMesh = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.displayMaterial);
    this.displayMesh.frustumCulled = false;
    this.displayScene.add(this.displayMesh);

    this.resizeObserver = new ResizeObserver(this.resize);
    this.resizeObserver.observe(this.sceneElement);
    this.intersectionObserver = new IntersectionObserver(([entry]) => {
      this.visible = Boolean(entry?.isIntersecting);
    }, { rootMargin: '120px' });
    this.intersectionObserver.observe(this.root);
    this.sceneElement.addEventListener('pointermove', this.onPointerMove, { passive: true });
    window.addEventListener('scroll', this.onScroll, { passive: true });
    document.addEventListener('visibilitychange', this.onVisibilityChange);

    this.resize();
    this.onScroll();
    this.frame = requestAnimationFrame(this.tick);
  }

  resize() {
    if (this.destroyed) return;
    const rect = this.sceneElement.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    if (width === this.width && height === this.height) return;
    this.width = width;
    this.height = height;
    this.renderer.setSize(width, height, false);
    this.simulation?.dispose();
    this.simulation = new FluidSimulation(
      this.renderer,
      width,
      height,
      this.THREE,
      this.shaders,
      this.settings,
    );
  }

  onPointerMove(event) {
    const rect = this.sceneElement.getBoundingClientRect();
    const pointer = this.pointer;
    const x = (event.clientX - rect.left) / Math.max(rect.width, 1);
    const y = 1 - (event.clientY - rect.top) / Math.max(rect.height, 1);
    pointer.previousX = pointer.x;
    pointer.previousY = pointer.y;
    pointer.x = Math.min(1, Math.max(0, x));
    pointer.y = Math.min(1, Math.max(0, y));
    pointer.moved = true;
    pointer.color = this.settings.color();
  }

  onScroll() {
    const progress = Math.min(window.scrollY / Math.max(0.8 * window.innerHeight, 1), 1);
    this.canvas.style.opacity = String(
      this.settings.opacity * (1 - this.settings.config.SCROLL_FADE * progress),
    );
  }

  onVisibilityChange() {
    if (!document.hidden) this.lastTime = performance.now();
  }

  tick(now) {
    if (this.destroyed) return;
    this.frame = requestAnimationFrame(this.tick);
    if (!this.visible || document.hidden || !this.simulation) {
      this.lastTime = now;
      return;
    }

    const dt = Math.min(Math.max((now - this.lastTime) / 1000, 0), 1 / 60);
    this.lastTime = now;
    const simulation = this.simulation;
    if (this.settings.autoEnabled) simulation.autoSplatTimer += dt;
    if (
      this.settings.autoEnabled &&
      simulation.autoSplatTimer > simulation.config.AUTO_SPLAT_INTERVAL
    ) {
      simulation.autoSplatTimer = 0;
      simulation.multipleSplats(
        Math.floor(simulation.config.AUTO_SPLATS_RANGE * Math.random()) +
          simulation.config.AUTO_SPLATS_MIN,
      );
    }

    const pointer = this.pointer;
    if (pointer.moved) {
      pointer.moved = false;
      const aspect = simulation.width / simulation.height;
      let dx = pointer.x - pointer.previousX;
      let dy = pointer.y - pointer.previousY;
      if (aspect < 1) dx *= aspect;
      if (aspect > 1) dy /= aspect;
      simulation.splat(
        pointer.x,
        pointer.y,
        dx * simulation.config.SPLAT_FORCE,
        dy * simulation.config.SPLAT_FORCE,
        pointer.color,
      );
    }

    simulation.step(dt);
    simulation.applyBloom();
    simulation.applySunrays();
    this.displayMaterial.uniforms.uTexture.value = simulation.dye.read.target.texture;
    this.displayMaterial.uniforms.uBloom.value = simulation.bloom.target.texture;
    this.displayMaterial.uniforms.uSunrays.value = simulation.sunrays.target.texture;
    this.displayMaterial.uniforms.texelSize.value.set(
      1 / Math.max(this.canvas.width, 1),
      1 / Math.max(this.canvas.height, 1),
    );
    this.renderer.setRenderTarget(null);
    this.renderer.clear();
    this.renderer.render(this.displayScene, this.displayCamera);
  }

  destroy() {
    if (this.destroyed) return;
    this.destroyed = true;
    cancelAnimationFrame(this.frame);
    this.resizeObserver.disconnect();
    this.intersectionObserver.disconnect();
    this.sceneElement.removeEventListener('pointermove', this.onPointerMove);
    window.removeEventListener('scroll', this.onScroll);
    document.removeEventListener('visibilitychange', this.onVisibilityChange);
    this.simulation?.dispose();
    this.displayMesh.geometry.dispose();
    this.displayMaterial.dispose();
    this.renderer.dispose();
    this.canvas.remove();
  }
}

async function mount(root) {
  if (
    controllers.has(root) ||
    root.dataset.cursorSmokeEnabled !== 'true' ||
    !root.querySelector('[data-grw-scene]') ||
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  ) return;

  const threeUrl = root.dataset.threeUrl;
  const shadersUrl = root.dataset.fluidShadersUrl;
  if (!threeUrl || !shadersUrl) return;

  try {
    const [THREE, shaders] = await Promise.all([import(threeUrl), import(shadersUrl)]);
    if (!root.isConnected || root.dataset.cursorSmokeEnabled !== 'true') return;
    const controller = new ElegantFluidController(root, THREE, shaders, readSettings(root));
    controllers.set(root, controller);
    root.dataset.cursorSmokeReady = 'true';
  } catch (error) {
    root.dataset.cursorSmokeReady = 'error';
    console.warn('[GicleeArt] Efekt dymu kursora nie został uruchomiony.', error);
  }
}

function unmount(root) {
  const controller = controllers.get(root);
  controller?.destroy();
  controllers.delete(root);
}

function boot(scope = document) {
  scope.querySelectorAll?.('giclee-random-artwork[data-cursor-smoke-enabled="true"]').forEach(mount);
}

boot();
document.addEventListener('shopify:section:load', (event) => boot(event.target));
document.addEventListener('shopify:section:unload', (event) => {
  event.target.querySelectorAll?.('giclee-random-artwork').forEach(unmount);
});
