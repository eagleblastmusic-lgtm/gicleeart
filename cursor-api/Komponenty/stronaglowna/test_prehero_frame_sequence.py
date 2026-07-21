from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
RENDERER = ROOT / "assets" / "giclee-home-prehero-frames.js"
SCRUB = ROOT / "assets" / "giclee-home-prehero-scrub.js"
CSS = ROOT / "assets" / "giclee-home-prehero-scrub.css"
MANIFEST = ROOT / "snippets" / "giclee-home-prehero-frame-manifest.liquid"
BUILDER = ROOT / "scripts" / "build_prehero_webp_sequence.py"


def test_frame_renderer_uses_predictive_two_level_cache() -> None:
    source = RENDERER.read_text(encoding="utf-8")

    assert "giclee-prehero-scrub__canvas" in source
    assert "getContext('2d'" in source
    assert "desynchronized: true" in source
    assert "var bitmapCache = new Map();" in source
    assert "var blobCache = new Map();" in source
    assert "function evictBitmaps()" in source
    assert "function evictBlobs()" in source
    assert "function rebuildDesiredFrames()" in source
    assert "function freeTargetSlot()" in source
    assert "AbortController" in source
    assert "requestIdleCallback" not in source
    assert "performance.now() - lastProgressAt > 90" not in source
    assert "GICLEE_PREHERO_FRAME_STATUS" in source


def test_frame_renderer_keeps_canvas_resolution_stable_during_scroll() -> None:
    source = RENDERER.read_text(encoding="utf-8")

    assert "function usefulDpr(width, height)" in source
    assert "Math.min(sourceWidthHint /" in source
    assert "function resize()" in source
    assert "motionDpr" not in source
    assert "idleQualityDelayMs" not in source
    assert "scheduleQualityRestore" not in source


def test_frame_renderer_has_monotonic_fallback_and_exact_final_draw() -> None:
    source = RENDERER.read_text(encoding="utf-8")

    assert "function monotonicFallback(index)" in source
    assert "cachedIndex > renderedFrame && cachedIndex <= index" in source
    assert "cachedIndex < renderedFrame && cachedIndex >= index" in source
    assert "if (task.index === targetFrame) scheduleDraw();" in source
    assert "publishRenderedFrame(targetFrame, exact.source, true);" in source


def test_native_v2_and_lenis_use_mp4_without_explicit_webp_opt_in() -> None:
    source = SCRUB.read_text(encoding="utf-8")

    assert "frameRendererAvailable()" in source
    assert "String(CONFIG.preheroRenderer || 'mp4')" in source
    assert "if (rendererMode !== 'webp') return false;" in source
    assert "renderMode: useFrameSequence ? 'webp-canvas' : 'mp4-seek'" in source
    assert "if (useFrameSequence) frameController.setProgress(progress);" in source
    assert "if (scrubState && scrubState.usesFrameSequence)" in source
    assert "parts.video.preload = 'none';" in source
    assert "if (useFrameSequence) return;" in source


def test_frame_canvas_visibility_is_scoped_to_frame_mode() -> None:
    styles = CSS.read_text(encoding="utf-8")

    assert ".giclee-prehero-scrub__canvas" in styles
    assert "data-frame-sequence-ready='true'" in styles
    assert "data-render-mode='webp-frames'" in styles
    assert "display: none;" in styles


def test_manifest_has_safe_disabled_fallback() -> None:
    source = MANIFEST.read_text(encoding="utf-8")

    assert "window.GICLEE_PREHERO_FRAME_SEQUENCE" in source
    assert "enabled: false" in source or "enabled: true" in source
    assert "urls:" in source


def test_builder_generates_flat_shopify_assets_and_liquid_manifest() -> None:
    source = BUILDER.read_text(encoding="utf-8")

    assert 'FRAME_PREFIX = "giclee-prehero-frame-"' in source
    assert "libwebp" in source
    assert "asset_url | json" in source
    assert "budget-mb" in source
    assert "TemporaryDirectory" in source
    assert "MANIFEST_PATH.write_text" in source


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for scheduler runtime proof")
def test_predictive_scheduler_preempts_stale_work_and_renders_final_frame(tmp_path: Path) -> None:
    harness = tmp_path / "prehero_scheduler_runtime.js"
    harness.write_text(
        r'''"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const attrs = new Map();
const draws = [];
let rafId = 0;

class Signal {
  constructor() { this.aborted = false; this.listeners = []; }
  addEventListener(name, callback) { if (name === "abort") this.listeners.push(callback); }
}
class Controller {
  constructor() { this.signal = new Signal(); }
  abort() {
    if (this.signal.aborted) return;
    this.signal.aborted = true;
    this.signal.listeners.forEach((callback) => callback());
  }
}
function indexOf(url) { return Number(/frame-(\d+)/.exec(url)[1]); }
function fetchFrame(url, options = {}) {
  const index = indexOf(url);
  const delay = ({18: 180, 4: 12, 19: 140, 0: 8})[index] ?? 24;
  return new Promise((resolve, reject) => {
    let done = false;
    const timer = setTimeout(() => {
      if (done) return;
      done = true;
      resolve({ok: true, blob: async () => ({index, width: 1920, height: 1080})});
    }, delay);
    if (options.signal) options.signal.addEventListener("abort", () => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      reject(new Error("aborted"));
    });
  });
}
async function createImageBitmap(source, ...args) {
  const options = args[4] || {};
  return {
    index: source.index,
    width: options.resizeWidth || source.width || 1920,
    height: options.resizeHeight || source.height || 1080,
    close() {},
  };
}
const context = {
  clearRect() {},
  drawImage(source) { draws.push(source.index); },
  imageSmoothingEnabled: false,
  imageSmoothingQuality: "low",
};
const canvas = {width: 0, height: 0, className: "", setAttribute() {}, getContext() { return context; }};
const stage = {clientWidth: 1459, clientHeight: 953, querySelector() { return null; }, insertBefore() {}};
const root = {
  setAttribute(name, value) { attrs.set(name, String(value)); },
  getAttribute(name) { return attrs.get(name) || null; },
};
const sandbox = {
  console, Promise, Map, Set, Math, Date, Error,
  Image: class {},
  document: {createElement() { return canvas; }},
  window: {
    GICLEE_PREHERO_FRAME_SEQUENCE: {
      enabled: true,
      urls: Array.from({length: 20}, (_, index) => `frame-${index}`),
      duration: 4.833333,
      cacheSize: 12,
      blobCacheSize: 24,
      preloadRadius: 4,
      maxConcurrentLoads: 2,
      maxDpr: 1.5,
      sourceWidth: 1920,
      sourceHeight: 1080,
    },
    innerWidth: 1459,
    innerHeight: 953,
    devicePixelRatio: 2,
    performance: {now: () => Date.now()},
    requestAnimationFrame(callback) { const id = ++rafId; setImmediate(() => callback(Date.now())); return id; },
    fetch: fetchFrame,
    createImageBitmap,
    AbortController: Controller,
  },
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), sandbox);
const controller = sandbox.window.GICLEE_PREHERO_FRAME_RENDERER.create({root, stage, video: null});
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
(async () => {
  controller.setProgress(18 / 19);
  await wait(5);
  controller.setProgress(4 / 19);
  await wait(90);
  let status = controller.status();
  assert.strictEqual(status.renderedFrame, 4);
  assert(status.abortedLoadCount >= 1);
  assert(status.bitmapCacheSize > 1);
  const resizeCount = status.resizeCount;
  controller.setProgress(1);
  await wait(220);
  status = controller.status();
  assert.strictEqual(status.renderedFrame, 19);
  assert.strictEqual(attrs.get("data-rendered-frame"), "19");
  assert.strictEqual(status.resizeCount, resizeCount);
  assert(status.currentDpr > 1 && status.currentDpr < 1.2);
  assert(draws.includes(4) && draws.includes(19));
})().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
''',
        encoding="utf-8",
    )

    result = subprocess.run(
        [shutil.which("node") or "node", str(harness), str(RENDERER)],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
