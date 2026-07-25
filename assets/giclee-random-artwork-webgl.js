/*
 * Losuj Obraz — scena WebGL (Museum Portal / Fine Art Oracle).
 * Modul ladowany dynamicznie tylko po przejsciu capability gate w
 * giclee-random-artwork.js. Three.js importowany jest lokalnie (threeUrl).
 *
 * Eksport: createOracleScene(options) -> Promise<controller>
 *   options: { mount, threeUrl, cards[], winnerIndex, reducedMotion, isMobile,
 *              onPhase(index), onComplete() }
 *   controller: { destroy() }
 */

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeInOutSine = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
const easeOutBack = (t) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
const clamp01 = (t) => Math.min(1, Math.max(0, t));
const smoothstep = (edge0, edge1, x) => {
  const t = clamp01((x - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
};
const TAU = Math.PI * 2;

function radialSprite(THREE, stops) {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [offset, color] of stops) gradient.addColorStop(offset, color);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

export async function createOracleScene(options) {
  const {
    mount,
    threeUrl,
    cards = [],
    winnerIndex = 0,
    reducedMotion = false,
    isMobile = false,
    onPhase,
    onComplete,
  } = options;

  const THREE = await import(threeUrl);

  const TOTAL_MS = reducedMotion ? 2600 : isMobile ? 4800 : 5400;
  const TURNS = isMobile ? 1.5 : 2.25;
  const DUST_COUNT = reducedMotion ? 0 : isMobile ? 160 : 440;

  // Dramaturgia: wejscie -> orbitowanie -> spowolnienie -> wybor -> reveal.
  const T_INTRO = 0.15;
  const T_ORBIT = 0.58;
  const T_SLOW = 0.8;
  const T_SELECT = 0.86;

  const width = () => mount.clientWidth || mount.offsetWidth || window.innerWidth;
  const height = () => mount.clientHeight || mount.offsetHeight || window.innerHeight;

  const renderer = new THREE.WebGLRenderer({
    antialias: !isMobile,
    alpha: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1.25 : 1.5));
  renderer.setSize(width(), height(), false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.className = 'giclee-random-artwork__gl';
  mount.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x06060a, 0.085);

  const camera = new THREE.PerspectiveCamera(50, width() / height(), 0.1, 100);
  camera.position.set(0, 0.2, 8.4);
  camera.lookAt(0, 0, 0);

  const disposables = [];
  const track = (obj) => {
    disposables.push(obj);
    return obj;
  };

  // ── Portal ──
  const portal = new THREE.Group();
  scene.add(portal);

  const glowTex = track(
    radialSprite(THREE, [
      [0, 'rgba(255,244,214,0.9)'],
      [0.25, 'rgba(201,168,76,0.45)'],
      [0.6, 'rgba(201,168,76,0.12)'],
      [1, 'rgba(201,168,76,0)'],
    ])
  );
  const glowMat = track(
    new THREE.SpriteMaterial({
      map: glowTex,
      color: 0xffffff,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0,
    })
  );
  const glow = new THREE.Sprite(glowMat);
  glow.scale.set(6, 6, 1);
  portal.add(glow);

  const ringGeo = track(new THREE.TorusGeometry(1.7, 0.012, 16, 120));
  const ringMat = track(
    new THREE.MeshBasicMaterial({
      color: 0xc9a84c,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  const ring = new THREE.Mesh(ringGeo, ringMat);
  portal.add(ring);

  const ringInnerGeo = track(new THREE.TorusGeometry(1.28, 0.006, 16, 120));
  const ringInnerMat = track(
    new THREE.MeshBasicMaterial({
      color: 0xe6cd86,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  const ringInner = new THREE.Mesh(ringInnerGeo, ringInnerMat);
  portal.add(ringInner);

  // ── Pyl swietlny ──
  let dust = null;
  if (DUST_COUNT > 0) {
    const positions = new Float32Array(DUST_COUNT * 3);
    for (let i = 0; i < DUST_COUNT; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 16;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 10 - 1;
    }
    const dustGeo = track(new THREE.BufferGeometry());
    dustGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const dustTex = track(
      radialSprite(THREE, [
        [0, 'rgba(255,240,210,0.9)'],
        [0.5, 'rgba(201,168,76,0.4)'],
        [1, 'rgba(201,168,76,0)'],
      ])
    );
    const dustMat = track(
      new THREE.PointsMaterial({
        size: isMobile ? 0.04 : 0.052,
        map: dustTex,
        color: 0xcdb488,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        sizeAttenuation: true,
        blending: THREE.AdditiveBlending,
      })
    );
    dust = new THREE.Points(dustGeo, dustMat);
    scene.add(dust);
  }

  // ── Karty produktow ──
  const loader = new THREE.TextureLoader();
  loader.crossOrigin = 'anonymous';
  const loadTexture = (src) =>
    new Promise((resolve) => {
      if (!src) {
        resolve(null);
        return;
      }
      loader.load(
        src,
        (tex) => {
          tex.colorSpace = THREE.SRGBColorSpace;
          tex.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy?.() || 1);
          resolve(tex);
        },
        undefined,
        () => resolve(null)
      );
    });

  const count = cards.length;
  const radius = isMobile ? 2.7 : 3.4;
  const cardW = isMobile ? 1.05 : 1.25;
  const textures = await Promise.all(cards.map((card) => loadTexture(card.image)));

  const cardEntries = cards.map((card, i) => {
    const texture = textures[i];
    if (texture) track(texture);
    let aspect = 0.72;
    if (texture?.image?.width && texture?.image?.height) {
      aspect = texture.image.width / texture.image.height;
    }
    const cardH = Math.min(1.85, Math.max(0.85, cardW / aspect));

    // Museum exhibit card: thin dark rim + warm-white passepartout (matches HTML result).
    const matte = isMobile ? 0.14 : 0.17;
    const rim = isMobile ? 0.034 : 0.042;
    const artW = cardW;
    const artH = cardH;
    const matteW = artW + matte * 2;
    const matteH = artH + matte * 2;
    const rimW = matteW + rim * 2;
    const rimH = matteH + rim * 2;

    const pivot = new THREE.Group();

    const rimGeo = track(new THREE.PlaneGeometry(rimW, rimH));
    const rimMat = track(
      new THREE.MeshBasicMaterial({ color: 0x0c0b0a, transparent: true, opacity: 0 })
    );
    pivot.add(new THREE.Mesh(rimGeo, rimMat));

    const matteGeo = track(new THREE.PlaneGeometry(matteW, matteH));
    const matteMat = track(
      new THREE.MeshBasicMaterial({ color: 0xf4f2ec, transparent: true, opacity: 0 })
    );
    const matteMesh = new THREE.Mesh(matteGeo, matteMat);
    matteMesh.position.z = 0.006;
    pivot.add(matteMesh);

    const artGeo = track(new THREE.PlaneGeometry(artW, artH));
    const artMat = track(
      new THREE.MeshBasicMaterial({
        color: texture ? 0xffffff : 0x2a2418,
        map: texture || null,
        transparent: true,
        opacity: 0,
      })
    );
    const art = new THREE.Mesh(artGeo, artMat);
    art.position.z = 0.012;
    pivot.add(art);

    scene.add(pivot);

    return {
      pivot,
      mats: [rimMat, matteMat, artMat],
      baseAngle: (i / count) * TAU,
      yBase: (Math.random() - 0.5) * 1.1,
      bobPhase: Math.random() * TAU,
      isWinner: i === winnerIndex,
    };
  });

  // Landing: winner ma wyladowac na froncie (kat 0) po wyhamowaniu.
  const winnerBase = cardEntries[winnerIndex]?.baseAngle ?? 0;
  let landing = (-winnerBase) % TAU;
  if (landing < 0) landing += TAU;
  const spinTotal = TURNS * TAU + landing;

  // Kamera konczy okolo z=5.5 — winner lands komfortowo, z zapasem na kadr.
  const winnerTarget = new THREE.Vector3(0, 0.12, 2.2);

  // ── Petla animacji ──
  let rafId = 0;
  let startTime = 0;
  let destroyed = false;
  let contextLost = false;
  let completed = false;
  const phaseFired = { orbit: false, slow: false };

  const finish = () => {
    if (completed) return;
    completed = true;
    onComplete?.();
  };

  const render = (now) => {
    if (destroyed || contextLost) return;
    if (!startTime) startTime = now;
    const p = clamp01((now - startTime) / TOTAL_MS);
    const time = (now - startTime) / 1000;

    if (!phaseFired.orbit && p >= T_INTRO) {
      phaseFired.orbit = true;
      onPhase?.(1);
    }
    if (!phaseFired.slow && p >= T_ORBIT) {
      phaseFired.slow = true;
      onPhase?.(2);
    }

    const introEase = easeOutCubic(clamp01(p / T_INTRO));
    const spin = easeOutCubic(clamp01(p / T_SLOW)) * spinTotal;
    // Wybor: subtelne napiecie miedzy spowolnieniem a revealem.
    const select = smoothstep(T_SLOW, T_SELECT, p);
    const reveal = p > T_SELECT ? easeInOutCubic((p - T_SELECT) / (1 - T_SELECT)) : 0;
    const revealBack = p > T_SELECT ? easeOutBack(clamp01((p - T_SELECT) / (1 - T_SELECT))) : 0;

    // Kamera — cinematic dolly push-in + delikatny, tlumiony sway, ktory sie wycisza.
    const settle = easeInOutSine(p);
    camera.position.z = 8.6 - easeInOutCubic(p) * 3.1;
    camera.position.x = Math.sin(time * 0.26) * 0.22 * (1 - settle);
    camera.position.y = 0.18 + Math.sin(time * 0.4) * 0.07 * (1 - settle * 0.7);
    camera.lookAt(0, 0, 0);

    // Portal — luksusowa soczewka: miekkie swiatlo, powolny obrot, blysk przy wyborze.
    const flare = select * (1 - reveal * 0.5);
    glowMat.opacity = introEase * (0.32 + 0.22 * Math.sin(time * 1.1) * 0.5 + 0.5 * flare + 0.25 * reveal);
    ringMat.opacity = introEase * (0.4 + 0.35 * flare);
    ringInnerMat.opacity = introEase * (0.32 + 0.4 * flare);
    portal.scale.setScalar(1 + flare * 0.12 + reveal * 0.06 + Math.sin(time * 0.7) * 0.008);
    ring.rotation.z = time * 0.16;
    ringInner.rotation.z = -time * 0.22;

    if (dust) {
      dust.material.opacity = introEase * (0.34 - reveal * 0.3);
      dust.rotation.y = time * 0.03;
      dust.rotation.x = Math.sin(time * 0.1) * 0.04;
    }

    for (const entry of cardEntries) {
      const { pivot, mats } = entry;
      const angle = entry.baseAngle + spin;
      const orbitX = Math.sin(angle) * radius;
      const orbitZ = Math.cos(angle) * radius;
      const bob = Math.sin(time * 0.7 + entry.bobPhase) * 0.1 * (1 - reveal);
      const orbitY = entry.yBase * (1 - reveal * 0.6) + bob;
      const baseScale = 0.62 + introEase * 0.38;

      let opacity;
      let scale;

      if (entry.isWinner) {
        pivot.position.set(
          THREE.MathUtils.lerp(orbitX, winnerTarget.x, reveal),
          THREE.MathUtils.lerp(orbitY, winnerTarget.y, reveal),
          THREE.MathUtils.lerp(orbitZ, winnerTarget.z, reveal)
        );
        // Pop wyboru (easeOutBack) + lekkie wzmocnienie w fazie napiecia.
        scale = baseScale * (1 + select * 0.06) + revealBack * 0.55;
        opacity = introEase;
      } else {
        pivot.position.set(orbitX, orbitY, orbitZ - reveal * 2.6);
        scale = baseScale * (1 - select * 0.06) * (1 - reveal * 0.28);
        // Pozostale przygasaja juz przy wyborze, znikaja przy reveal.
        opacity = introEase * (1 - select * 0.35) * (1 - reveal);
      }

      pivot.scale.setScalar(scale);
      pivot.lookAt(camera.position);
      mats[0].opacity = opacity; // dark rim
      mats[1].opacity = opacity; // passepartout
      mats[2].opacity = opacity; // artwork
    }

    renderer.render(scene, camera);

    if (p >= 1) {
      finish();
      return;
    }
    rafId = requestAnimationFrame(render);
  };

  rafId = requestAnimationFrame(render);

  // ── Resize ──
  const onResize = () => {
    if (destroyed) return;
    const w = width();
    const h = height();
    if (!w || !h) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  };
  window.addEventListener('resize', onResize);

  let resizeObserver = null;
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);
  }

  // ── Utrata kontekstu WebGL ──
  const onContextLost = (event) => {
    event.preventDefault();
    contextLost = true;
    cancelAnimationFrame(rafId);
    finish();
  };
  renderer.domElement.addEventListener('webglcontextlost', onContextLost, false);

  // ── Teardown ──
  const destroy = () => {
    if (destroyed) return;
    destroyed = true;
    cancelAnimationFrame(rafId);
    window.removeEventListener('resize', onResize);
    resizeObserver?.disconnect();
    renderer.domElement.removeEventListener('webglcontextlost', onContextLost);

    const canvas = renderer.domElement;
    canvas.style.transition = 'opacity 0.5s ease';
    canvas.style.opacity = '0';

    const disposeAll = () => {
      for (const obj of disposables) obj.dispose?.();
      scene.traverse((node) => {
        node.geometry?.dispose?.();
        if (Array.isArray(node.material)) node.material.forEach((m) => m.dispose?.());
        else node.material?.dispose?.();
      });
      renderer.dispose();
      renderer.forceContextLoss?.();
      canvas.parentNode?.removeChild(canvas);
    };

    if (contextLost) disposeAll();
    else window.setTimeout(disposeAll, 520);
  };

  return { destroy };
}
