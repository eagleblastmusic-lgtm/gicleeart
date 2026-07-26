/*
 * Losuj Obraz V4 — ceremonial WebGL finale.
 * Preserves the V3 oracle scene while extending only the selection-to-exhibit handoff.
 */

const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = (t) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const easeInOutSine = (t) => -(Math.cos(Math.PI * t) - 1) / 2;
const clamp01 = (t) => Math.min(1, Math.max(0, t));
const smoothstep = (edge0, edge1, x) => {
  const t = clamp01((x - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
};

const smootherstep = (edge0, edge1, x) => {
  const span = edge1 - edge0;

  if (Math.abs(span) < 1e-6) {
    return x >= edge1 ? 1 : 0;
  }

  const t = clamp01((x - edge0) / span);
  return t * t * t * (t * (t * 6 - 15) + 10);
};
const TAU = Math.PI * 2;
const FINALE_EXTRA_MS = 1100;
/** First portion of the reveal window grows the winner; the rest settles into the DOM frame. */
const GROW_PORTION = 0.4;

/** Number of non-winning cards sharing the synchronized fade. */
const FRONT_FADE_COUNT = 3;

/** Existing non-winner retreat distance in the Z axis. */
const FRONT_RETREAT_Z = 3.6;

/** Number of samples used to detect side-card contact. */
const FRONT_CONTACT_SAMPLES = 320;

/** Fade duration measured in the local reveal progress range 0–1. */
const FRONT_FADE_WINDOW = 0.26;

function radialSprite(THREE, stops) {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2,
  );
  for (const [offset, color] of stops) gradient.addColorStop(offset, color);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/** Map a screen-space DOM rect onto the card plane in front of the camera. */
function resolveHandoffPose(THREE, camera, mount, rect, outerW, outerH, planePoint) {
  if (!rect?.width || !rect?.height || !mount || !outerW || !outerH) return null;
  const canvasRect = mount.getBoundingClientRect();
  if (!canvasRect.width || !canvasRect.height) return null;

  const cx = rect.left + rect.width * 0.5;
  const cy = rect.top + rect.height * 0.5;
  const ndcX = ((cx - canvasRect.left) / canvasRect.width) * 2 - 1;
  const ndcY = -(((cy - canvasRect.top) / canvasRect.height) * 2 - 1);

  const camPos = camera.position.clone();
  const planeNormal = camPos.clone().sub(planePoint).normalize();
  const aim = new THREE.Vector3(ndcX, ndcY, 0.5).unproject(camera);
  const dir = aim.sub(camPos).normalize();
  const denom = planeNormal.dot(dir);
  if (Math.abs(denom) < 1e-5) return null;
  const t = planeNormal.dot(planePoint.clone().sub(camera.position)) / denom;
  const position = camera.position.clone().add(dir.multiplyScalar(t));

  const dist = camera.position.distanceTo(position);
  const worldH = 2 * Math.tan((camera.fov * Math.PI) / 360) * dist;
  const worldW = worldH * camera.aspect;
  const targetH = (rect.height / canvasRect.height) * worldH;
  const targetW = (rect.width / canvasRect.width) * worldW;
  const scale = Math.min(targetW / outerW, targetH / outerH);
  if (!(scale > 0.05) || !Number.isFinite(scale)) return null;

  return { position, scale };
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
    onHandoffPrepare,
    getHandoffTarget,
    onComplete,
  } = options;

  const THREE = await import(threeUrl);

  const BASE_TOTAL_MS = reducedMotion ? 2600 : isMobile ? 4800 : 5400;
  const TOTAL_MS = BASE_TOTAL_MS + (reducedMotion ? 0 : FINALE_EXTRA_MS);
  const TURNS = isMobile ? 1.5 : 2.25;
  const DUST_COUNT = reducedMotion ? 0 : isMobile ? 160 : 440;
  const timeline = (baseFraction) => (baseFraction * BASE_TOTAL_MS) / TOTAL_MS;

  // Preserve the existing oracle timing, then reserve 800 ms for exhibition handoff.
  const T_INTRO = timeline(0.15);
  const T_ORBIT = timeline(0.58);
  const T_SLOW = timeline(0.8);
  const T_SELECT = timeline(0.86);

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
  const track = (object) => {
    disposables.push(object);
    return object;
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
    ]),
  );
  const glowMat = track(
    new THREE.SpriteMaterial({
      map: glowTex,
      color: 0xffffff,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0,
    }),
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
    }),
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
    }),
  );
  const ringInner = new THREE.Mesh(ringInnerGeo, ringInnerMat);
  portal.add(ringInner);

  // ── Light dust ──
  let dust = null;
  if (DUST_COUNT > 0) {
    const positions = new Float32Array(DUST_COUNT * 3);
    for (let index = 0; index < DUST_COUNT; index += 1) {
      positions[index * 3] = (Math.random() - 0.5) * 16;
      positions[index * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[index * 3 + 2] = (Math.random() - 0.5) * 10 - 1;
    }
    const dustGeo = track(new THREE.BufferGeometry());
    dustGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const dustTex = track(
      radialSprite(THREE, [
        [0, 'rgba(255,240,210,0.9)'],
        [0.5, 'rgba(201,168,76,0.4)'],
        [1, 'rgba(201,168,76,0)'],
      ]),
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
      }),
    );
    dust = new THREE.Points(dustGeo, dustMat);
    scene.add(dust);
  }

  // ── Product cards ──
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
        (texture) => {
          texture.colorSpace = THREE.SRGBColorSpace;
          texture.anisotropy = Math.min(
            4,
            renderer.capabilities.getMaxAnisotropy?.() || 1,
          );
          resolve(texture);
        },
        undefined,
        () => resolve(null),
      );
    });

  const count = cards.length;
  const radius = isMobile ? 2.7 : 3.4;
  const cardW = isMobile ? 1.05 : 1.25;
  const textures = await Promise.all(cards.map((card) => loadTexture(card.image)));

  const cardEntries = cards.map((card, index) => {
    const texture = textures[index];
    if (texture) track(texture);
    let aspect = 0.72;
    if (texture?.image?.width && texture?.image?.height) {
      aspect = texture.image.width / texture.image.height;
    }
    const cardH = Math.min(1.85, Math.max(0.85, cardW / aspect));

    // Museum exhibit card: thin dark rim + warm-white passepartout.
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
      new THREE.MeshBasicMaterial({ color: 0x0c0b0a, transparent: true, opacity: 0 }),
    );
    pivot.add(new THREE.Mesh(rimGeo, rimMat));

    const matteGeo = track(new THREE.PlaneGeometry(matteW, matteH));
    const matteMat = track(
      new THREE.MeshBasicMaterial({ color: 0xf4f2ec, transparent: true, opacity: 0 }),
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
      }),
    );
    const art = new THREE.Mesh(artGeo, artMat);
    art.position.z = 0.012;
    pivot.add(art);
    scene.add(pivot);

    return {
      pivot,
      mats: [rimMat, matteMat, artMat],
      outerW: rimW,
      outerH: rimH,
      baseAngle: (index / count) * TAU,
      yBase: (Math.random() - 0.5) * 1.1,
      bobPhase: Math.random() * TAU,
      isWinner: index === winnerIndex,
    };
  });

  const winnerBase = cardEntries[winnerIndex]?.baseAngle ?? 0;
  let landing = (-winnerBase) % TAU;
  if (landing < 0) landing += TAU;
  const spinTotal = TURNS * TAU + landing;
  // Slightly raised: room for captions under the frozen finale card.
  const winnerTarget = new THREE.Vector3(0, 0.22, 2.2);
  const winnerEntry = cardEntries[winnerIndex];

  /**
   * Resolve the final orbit position of every non-winning card.
   * Higher Z means closer to the camera.
   */
  const winnerFinalAngle =
    (winnerEntry?.baseAngle ?? 0) + spinTotal;

  const winnerOrbitZAtSelection =
    Math.cos(winnerFinalAngle) * radius;

  const frontFadeCandidates = cardEntries
    .filter((entry) => !entry.isWinner)
    .map((entry) => {
      const finalAngle = entry.baseAngle + spinTotal;

      return {
        entry,
        x: Math.sin(finalAngle) * radius,
        z: Math.cos(finalAngle) * radius,
      };
    })
    .sort((first, second) => second.z - first.z)
    .slice(
      0,
      Math.min(
        FRONT_FADE_COUNT,
        Math.max(0, cardEntries.length - 1),
      ),
    )
    .sort((first, second) => first.x - second.x);

  /** Fast membership check inside the render loop. */
  const frontFadeEntries = new Set(
    frontFadeCandidates.map(({ entry }) => entry),
  );

  /**
   * After sorting by X:
   * - first item is the left side card,
   * - last item is the right side card.
   *
   * The middle card shares opacity but does not control timing.
   */
  const frontFadeSidePoses =
    frontFadeCandidates.length > 1
      ? [
          frontFadeCandidates[0],
          frontFadeCandidates[
            frontFadeCandidates.length - 1
          ],
        ]
      : frontFadeCandidates;

  /** Winner Z position during the local reveal stage. */
  const winnerZAtReveal = (localT) =>
    THREE.MathUtils.lerp(
      winnerOrbitZAtSelection,
      winnerTarget.z,
      easeOutCubic(
        clamp01(localT / GROW_PORTION),
      ),
    );

  /** Non-winning side-card Z position during retreat. */
  const sideZAtReveal = (pose, localT) => {
    const revealEased = easeInOutCubic(
      clamp01(localT),
    );

    const retreatAtTime = easeInOutSine(
      revealEased,
    );

    return (
      pose.z -
      retreatAtTime * FRONT_RETREAT_Z
    );
  };

  /**
   * Detect the moment when a side card crosses the winner plane.
   *
   * signedGap > 0: side card is in front of the winner;
   * signedGap = 0: contact;
   * signedGap < 0: side card has passed behind the winner.
   */
  const findSideContactT = (pose) => {
    let previousT = 0;
    let previousGap =
      sideZAtReveal(pose, 0) -
      winnerZAtReveal(0);

    let wasInFront = previousGap > 0;

    for (
      let step = 1;
      step <= FRONT_CONTACT_SAMPLES;
      step += 1
    ) {
      const localT =
        step / FRONT_CONTACT_SAMPLES;

      const signedGap =
        sideZAtReveal(pose, localT) -
        winnerZAtReveal(localT);

      if (signedGap > 0) {
        wasInFront = true;
      }

      if (
        wasInFront &&
        previousGap > 0 &&
        signedGap <= 0
      ) {
        const denominator =
          previousGap - signedGap;

        const crossingMix =
          denominator > 1e-6
            ? previousGap / denominator
            : 1;

        return THREE.MathUtils.lerp(
          previousT,
          localT,
          crossingMix,
        );
      }

      previousT = localT;
      previousGap = signedGap;
    }

    return null;
  };

  /**
   * The earlier contact of the left or right card controls
   * the synchronized opacity of all three front cards.
   */
  const detectedSideContacts = frontFadeSidePoses
    .map(findSideContactT)
    .filter((value) => Number.isFinite(value))
    .sort((first, second) => first - second);

  const frontFadeEnd = clamp01(
    detectedSideContacts[0] ?? 0.56,
  );

  const frontFadeStart = Math.max(
    0,
    frontFadeEnd - FRONT_FADE_WINDOW,
  );
  // Screen-parallel pose: same basis as the camera (plane +Z faces the lens).
  // Do NOT yaw-flip — that turns the card's back to the camera (FrontSide cull).
  const _camDir = new THREE.Vector3();
  const _flatTarget = new THREE.Vector3();
  const _lookQuat = new THREE.Quaternion();
  const _flatQuat = new THREE.Quaternion();
  const applyFlatFacing = (object) => {
    camera.getWorldDirection(_camDir);
    _flatTarget.copy(object.position).sub(_camDir);
    object.lookAt(_flatTarget);
  };

  // ── Animation loop ──
  let rafId = 0;
  let startTime = 0;
  let destroyed = false;
  let contextLost = false;
  let completed = false;
  const phaseFired = { orbit: false, slow: false, handoff: false };
  let peakPose = null;
  let handoffPose = null;

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
    const select = smoothstep(T_SLOW, T_SELECT, p);
    const revealLocal = p > T_SELECT
      ? clamp01((p - T_SELECT) / Math.max(1e-6, 1 - T_SELECT))
      : 0;
    const growT = easeOutCubic(clamp01(revealLocal / GROW_PORTION));
    const settleT = easeInOutCubic(
      clamp01((revealLocal - GROW_PORTION) / Math.max(1e-6, 1 - GROW_PORTION)),
    );
    const reveal = easeInOutCubic(revealLocal);
    const retreat = easeInOutSine(reveal);

    /**
     * One synchronized fade for all three front cards.
     * It reaches exactly zero at the first side-card contact.
     */
    const frontGroupFade = smootherstep(
      frontFadeStart,
      frontFadeEnd,
      revealLocal,
    );

    const frontGroupOpacity =
      introEase * (1 - frontGroupFade);

    const camSettle = easeInOutSine(p);
    camera.position.z = 8.6 - easeInOutCubic(p) * 3.05;
    camera.position.x = Math.sin(time * 0.26) * 0.22 * (1 - camSettle);
    camera.position.y = 0.18 + Math.sin(time * 0.4) * 0.07 * (1 - camSettle * 0.7);
    camera.lookAt(0, 0.08, 0);

    // Portal / afterglow: fully fade out during the final settle (no pixelated halo left).
    const flare = select * (1 - reveal * 0.72);
    const afterglow = 1 - settleT;
    glowMat.opacity = introEase * afterglow * (
      0.32 +
      0.11 * Math.sin(time * 1.1) +
      0.5 * flare
    );
    ringMat.opacity = introEase * afterglow * (0.4 + 0.35 * flare) * (1 - reveal * 0.96);
    ringInnerMat.opacity = introEase * afterglow * (0.32 + 0.4 * flare) * (1 - reveal * 0.98);
    glow.scale.set(6 + reveal * 2.4, 6 - reveal * 2.6, 1);
    portal.scale.setScalar(1 + flare * 0.1 * afterglow + Math.sin(time * 0.7) * 0.006 * afterglow);
    ring.rotation.z = time * 0.16;
    ringInner.rotation.z = -time * 0.22;

    if (dust) {
      // Dust sparks must hit zero with settle — additive points read as white pixels.
      dust.material.opacity = introEase * afterglow * (1 - reveal) * 0.34;
      dust.rotation.y = time * 0.03;
      dust.rotation.x = Math.sin(time * 0.1) * 0.04;
      if (afterglow <= 0.001) dust.visible = false;
    }

    if (settleT > 0 && !phaseFired.handoff) {
      phaseFired.handoff = true;
      try {
        onHandoffPrepare?.();
      } catch (_) {
        /* host prep is best-effort */
      }
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
        const growPosX = THREE.MathUtils.lerp(orbitX, winnerTarget.x, growT);
        const growPosY = THREE.MathUtils.lerp(orbitY, winnerTarget.y, growT);
        const growPosZ = THREE.MathUtils.lerp(orbitZ, winnerTarget.z, growT);
        const ceremonialLift = Math.sin(growT * Math.PI) * 0.035;
        const growScale = baseScale * (1 + select * 0.045) + growT * 0.82 + ceremonialLift;

        if (settleT <= 0) {
          pivot.position.set(growPosX, growPosY, growPosZ);
          scale = growScale;
        } else {
          if (!peakPose) {
            peakPose = {
              x: growPosX,
              y: growPosY,
              z: growPosZ,
              scale: growScale,
            };
          }

          let target = handoffPose;
          try {
            const rect = typeof getHandoffTarget === 'function' ? getHandoffTarget() : null;
            const resolved = resolveHandoffPose(
              THREE,
              camera,
              mount,
              rect,
              winnerEntry?.outerW,
              winnerEntry?.outerH,
              winnerTarget,
            );
            if (resolved) {
              handoffPose = resolved;
              target = resolved;
            }
          } catch (_) {
            /* keep last good pose */
          }

          if (!target) {
            target = {
              position: winnerTarget.clone(),
              scale: Math.max(0.72, peakPose.scale * 0.52),
            };
          }

          pivot.position.set(
            THREE.MathUtils.lerp(peakPose.x, target.position.x, settleT),
            THREE.MathUtils.lerp(peakPose.y, target.position.y, settleT),
            THREE.MathUtils.lerp(peakPose.z, target.position.z, settleT),
          );
          scale = THREE.MathUtils.lerp(peakPose.scale, target.scale, settleT);
        }
        opacity = introEase;
      } else {
        const outwardX =
          orbitX * (1 + retreat * 0.16);

        const outwardY =
          orbitY +
          Math.sign(entry.yBase || 1) *
            retreat *
            0.2;

        pivot.position.set(
          outwardX,
          outwardY,
          orbitZ -
            retreat * FRONT_RETREAT_Z,
        );

        scale =
          baseScale *
          (1 - select * 0.05) *
          (1 - retreat * 0.42);

        if (frontFadeEntries.has(entry)) {
          /**
           * Three nearest front cards:
           * - identical opacity,
           * - no abrupt select * 0.3 drop,
           * - fully invisible at first side contact.
           */
          opacity = frontGroupOpacity;
        } else {
          /** Preserve the existing fade for all other cards. */
          opacity =
            introEase *
            (1 - select * 0.3) *
            (1 - retreat) *
            afterglow;
        }
      }

      pivot.scale.setScalar(scale);
      pivot.lookAt(camera.position);
      if (entry.isWinner && settleT > 0) {
        // Animate out of billboard skew into a straight-on (screen-parallel) pose.
        _lookQuat.copy(pivot.quaternion);
        applyFlatFacing(pivot);
        _flatQuat.copy(pivot.quaternion);
        pivot.quaternion.copy(_lookQuat).slerp(_flatQuat, settleT);
      }
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
    const nextWidth = width();
    const nextHeight = height();
    if (!nextWidth || !nextHeight) return;
    camera.aspect = nextWidth / nextHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(nextWidth, nextHeight, false);
    // Finale keeps the last WebGL frame as the exhibit — redraw after layout changes.
    if (completed) renderer.render(scene, camera);
  };
  window.addEventListener('resize', onResize);

  let resizeObserver = null;
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);
  }

  const onContextLost = (event) => {
    event.preventDefault();
    contextLost = true;
    cancelAnimationFrame(rafId);
    finish();
  };
  renderer.domElement.addEventListener('webglcontextlost', onContextLost, false);

  let exhibitBaseScale = 1;
  let exhibitHoverMul = 1;
  let exhibitHoverTarget = 1;
  let exhibitHoverRaf = 0;
  const EXHIBIT_HOVER_SCALE = 1.03;

  const renderExhibitHover = () => {
    exhibitHoverRaf = 0;
    if (destroyed || !completed || !winnerEntry?.pivot) return;
    exhibitHoverMul += (exhibitHoverTarget - exhibitHoverMul) * 0.22;
    if (Math.abs(exhibitHoverTarget - exhibitHoverMul) < 0.001) {
      exhibitHoverMul = exhibitHoverTarget;
    }
    winnerEntry.pivot.scale.setScalar(exhibitBaseScale * exhibitHoverMul);
    renderer.render(scene, camera);
    if (exhibitHoverMul !== exhibitHoverTarget) {
      exhibitHoverRaf = requestAnimationFrame(renderExhibitHover);
    }
  };

  /** Soft scale of the frozen winner card only (within the black rim). */
  const setExhibitHover = (active) => {
    if (destroyed || !completed || !winnerEntry?.pivot) return;
    if (typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    if (typeof matchMedia === 'function' && matchMedia('(hover: none), (pointer: coarse)').matches) {
      return;
    }
    exhibitHoverTarget = active ? EXHIBIT_HOVER_SCALE : 1;
    if (!exhibitHoverRaf) exhibitHoverRaf = requestAnimationFrame(renderExhibitHover);
  };

  const destroy = (options = {}) => {
    if (destroyed) return;
    destroyed = true;
    cancelAnimationFrame(rafId);
    cancelAnimationFrame(exhibitHoverRaf);
    exhibitHoverRaf = 0;
    window.removeEventListener('resize', onResize);
    resizeObserver?.disconnect();
    renderer.domElement.removeEventListener('webglcontextlost', onContextLost);

    const canvas = renderer.domElement;
    const instant = options.instant !== false;

    const disposeAll = () => {
      for (const object of disposables) object.dispose?.();
      scene.traverse((node) => {
        node.geometry?.dispose?.();
        if (Array.isArray(node.material)) node.material.forEach((material) => material.dispose?.());
        else node.material?.dispose?.();
      });
      renderer.dispose();
      renderer.forceContextLoss?.();
      canvas.parentNode?.removeChild(canvas);
    };

    if (contextLost || instant) {
      canvas.style.opacity = '0';
      canvas.style.visibility = 'hidden';
      disposeAll();
      return;
    }

    canvas.style.transition = 'opacity 0.35s cubic-bezier(0.22, 1, 0.36, 1)';
    canvas.style.opacity = '0';
    window.setTimeout(disposeAll, 360);
  };

  const freeze = () => {
    if (destroyed) return;
    completed = true;
    cancelAnimationFrame(rafId);
    cancelAnimationFrame(exhibitHoverRaf);
    exhibitHoverRaf = 0;
    exhibitHoverMul = 1;
    exhibitHoverTarget = 1;
    if (winnerEntry?.pivot) {
      applyFlatFacing(winnerEntry.pivot);
      exhibitBaseScale = winnerEntry.pivot.scale.x || 1;
    }
    // Ensure no residual portal/dust/non-winner pixels remain on the frozen frame.
    glowMat.opacity = 0;
    ringMat.opacity = 0;
    ringInnerMat.opacity = 0;
    if (dust) dust.material.opacity = 0;
    glow.visible = false;
    ring.visible = false;
    ringInner.visible = false;
    portal.visible = false;
    if (dust) dust.visible = false;
    for (const entry of cardEntries) {
      if (entry.isWinner) continue;
      entry.pivot.visible = false;
      for (const mat of entry.mats) mat.opacity = 0;
    }
    renderer.render(scene, camera);
  };

  return { destroy, freeze, setExhibitHover };
}
