from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MAIN_JS = ROOT / "assets" / "giclee-random-artwork.js"
LIVING_JS = ROOT / "assets" / "giclee-random-artwork-living-museum.js"
LIVING_CSS = ROOT / "assets" / "giclee-random-artwork-living-museum.css"
BASE_CSS = ROOT / "assets" / "giclee-random-artwork.css"
SECTION = ROOT / "sections" / "giclee-random-artwork.liquid"
POOL = ROOT / "snippets" / "giclee-random-artwork-pool.liquid"
WEBGL = ROOT / "assets" / "giclee-random-artwork-webgl.js"


def test_living_museum_markup_settings_and_plaque_contract() -> None:
    section = SECTION.read_text(encoding="utf-8")

    for fragment in (
        "giclee-random-artwork-living-museum.css",
        "giclee-random-artwork-living-museum.js",
        "data-grw-living-museum",
        "data-grw-living-spotlight",
        "data-grw-living-dust",
        "data-living-light-enabled=",
        "data-living-dust-enabled=",
        "data-living-light-intensity=",
        '"living_light_enabled"',
        '"living_dust_enabled"',
        '"living_light_intensity"',
        '"value": "v3"',
    ):
        assert fragment in section

    living_index = section.index("data-grw-living-museum")
    canvas_index = section.index("data-grw-canvas-mount")
    content_index = section.index('class="giclee-random-artwork__content"')
    assert living_index < canvas_index < content_index

    artist_index = section.index("data-grw-result-artist")
    title_index = section.index("data-grw-result-title")
    year_index = section.index("data-grw-result-year")
    assert artist_index < title_index < year_index
    assert section.count("data-grw-view") == 1
    assert section.count("data-grw-replay") == 1


def test_product_pool_contract_keeps_source_endpoint_and_availability() -> None:
    section = SECTION.read_text(encoding="utf-8")
    pool = POOL.read_text(encoding="utf-8")
    main = MAIN_JS.read_text(encoding="utf-8")

    assert "collections.all" in section
    assert "/collections/all/products.json" in section
    assert "collection.products limit: grw_limit" in pool
    assert '"rawTitle": {{ product.title | json }}' in pool
    assert "product.title | split: ' - '" in pool
    assert "render 'giclee-artist-catalog-name'" in pool
    assert '"artist": {{ grw_artist_display | json }}' in pool
    assert "available: raw.available !== false" in main
    assert "const available = this.pool.filter((item) => item.available);" in main


def test_living_museum_performance_state_and_cleanup_guardrails() -> None:
    source = LIVING_JS.read_text(encoding="utf-8")
    styles = LIVING_CSS.read_text(encoding="utf-8")
    base_styles = BASE_CSS.read_text(encoding="utf-8")

    for fragment in (
        "const DPR_CAP = 1.35;",
        "const DUST_FRAME_MS = 1000 / 24;",
        "clamp(48 * area, 40, 70)",
        "requestIdleCallback",
        "new IntersectionObserver",
        "new ResizeObserver",
        "document.visibilityState",
        "scene.addEventListener('pointermove'",
        "state !== 'drawing'",
        "this.scene?.removeEventListener('pointermove'",
        "window.cancelAnimationFrame(this.rafId)",
        "this.resizeObserver?.disconnect()",
        "this.intersectionObserver?.disconnect()",
        "this.dustCanvas.width = 0",
    ):
        assert fragment in source

    assert "window.addEventListener('pointermove'" not in source
    assert source.count("getBoundingClientRect()") <= 4
    assert "pointer-events: none;" in styles
    assert "contain: paint;" in styles
    assert "@media (max-width: 749px), (hover: none), (pointer: coarse)" in styles
    assert "@media (prefers-reduced-motion: reduce)" in styles
    assert "filter: blur" not in styles
    assert 'data-living-light-state="drawing"' in styles
    assert 'data-living-light-state="result"' in styles
    assert "body:has(.giclee-random-artwork)" in base_styles
    assert "min-height: 0;" in base_styles


def test_existing_webgl_and_draw_regressions_remain_intact() -> None:
    main = MAIN_JS.read_text(encoding="utf-8")
    webgl = WEBGL.read_text(encoding="utf-8")

    assert "const module = await import(this.webglUrl);" in main
    assert "if (this.isDrawing) return;" in main
    assert "this.setState(STATE.DRAWING);" in main
    assert "createOracleScene" in main
    assert "DUST_COUNT" in webgl
    assert "controller.destroy()" in main
    assert "grw--webgl" in main


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_artwork_identity_parser_and_product_model_runtime(tmp_path: Path) -> None:
    harness = tmp_path / "identity.js"
    harness.write_text(
        r'''"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
global.window = {
  matchMedia: () => ({ matches: false }), setTimeout, clearTimeout,
  requestAnimationFrame: () => 1, cancelAnimationFrame: () => {},
  location: { origin: "https://gicleeart.eu" }, WebGLRenderingContext: null,
};
global.document = { createElement: () => ({ getContext: () => null }) };
Object.defineProperty(globalThis, "navigator", { value: {}, configurable: true });
global.performance = { now: () => 0 };
global.HTMLElement = class {};
global.customElements = { get: () => null, define: () => {} };
global.Image = class { constructor() { this.complete = true; } };
vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"), { filename: process.argv[2] });
const api = window.GICLEE_RANDOM_ARTWORK_TEST_API;
const cases = [
  ["Mona Lisa", "Mona Lisa", null],
  ["Taras kawiarni w nocy (Café Terrace at Night) (1888)", "Taras kawiarni w nocy", "1888"],
  ["Pole pszenicy z krukami (Wheatfield with Crows (1890))", "Pole pszenicy z krukami", "1890"],
  ["Autoportret, 1889 (Self-Portrait)", "Autoportret", "1889"],
  ["Widok Delft (View of Delft), 1660–1661", "Widok Delft", "1660–1661"],
  ["Łąka o świcie, ok. 1892 (Meadow at Dawn)", "Łąka o świcie", "ok. 1892"],
];
for (const [raw, title, year] of cases) {
  const parsed = api.parseArtworkIdentity(raw);
  assert.strictEqual(parsed.title, title);
  assert.strictEqual(parsed.year, year);
  assert(!parsed.title.endsWith(","));
  assert(!parsed.title.includes("("));
}
assert.strictEqual(api.formatArtistDisplayName("Gogh, Vincent van"), "Vincent van Gogh");
const embedded = api.normalizeProduct({
  rawTitle: "Vincent van Gogh - Taras kawiarni w nocy (Café Terrace at Night) (1888)",
  artist: "Vincent van Gogh", url: "/products/taras",
  image: "https://cdn.example/taras.jpg", available: true,
});
const ajax = api.normalizeProduct({
  title: "Vincent van Gogh - Taras kawiarni w nocy (Café Terrace at Night) (1888)",
  url: "/products/taras", image: "https://cdn.example/taras.jpg", available: true,
});
assert.deepStrictEqual(
  { artist: embedded.artist, title: embedded.title, year: embedded.year },
  { artist: ajax.artist, title: ajax.title, year: ajax.year },
);
const merged = api.mergeProductRecords(
  { ...ajax, artist: "", year: null, available: true },
  { ...embedded, available: false },
);
assert.strictEqual(merged.artist, "Vincent van Gogh");
assert.strictEqual(merged.year, "1888");
assert.strictEqual(merged.available, true);
const missing = api.normalizeProduct({
  title: "Mona Lisa (La Gioconda)", url: "/products/mona-lisa",
  image: "https://cdn.example/mona.jpg", available: false,
});
assert.strictEqual(missing.artist, "");
assert.strictEqual(missing.year, null);
assert.strictEqual(missing.available, false);
console.log(JSON.stringify({ cases: cases.length, embedded, ajax, merged, missing }));
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [shutil.which("node") or "node", str(harness), str(MAIN_JS)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    assert payload["cases"] == 6
    assert payload["embedded"]["artist"] == "Vincent van Gogh"
    assert payload["embedded"]["year"] == "1888"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_living_museum_runtime_cleanup_and_state_handoff(tmp_path: Path) -> None:
    harness = tmp_path / "lifecycle.js"
    harness.write_text(
        r'''"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
const events = [];
const style = () => ({ setProperty: () => {} });
const node = (name, rect = { left: 0, top: 0, width: 1200, height: 760 }) => ({
  name, style: style(), offsetWidth: name === "spotlight" ? 760 : rect.width,
  offsetHeight: name === "spotlight" ? 420 : rect.height,
  addEventListener: (type) => events.push(["add", name, type]),
  removeEventListener: (type) => events.push(["remove", name, type]),
  getBoundingClientRect: () => rect,
});
const scene = node("scene"); const layer = node("layer"); const spotlight = node("spotlight");
const button = node("button", { left: 500, top: 500, width: 200, height: 60 });
const result = node("result", { left: 380, top: 130, width: 440, height: 500 });
const context = { setTransform: () => {}, clearRect: () => {}, beginPath: () => {}, arc: () => {}, fill: () => {}, set fillStyle(_v) {} };
const canvas = node("canvas"); canvas.width = 1; canvas.height = 1; canvas.getContext = () => context;
const selectors = new Map([
  ["[data-grw-scene]", scene], ["[data-grw-living-museum]", layer],
  ["[data-grw-living-spotlight]", spotlight], ["[data-grw-living-dust]", canvas],
  ["[data-grw-draw]", button], ["[data-grw-portal]", node("portal")],
  [".grw--custom-bg-parallax .giclee-random-artwork__custom-bg-layers", node("background")],
  ["[data-grw-result-link]", result],
]);
const root = {
  dataset: { livingLightEnabled: "true", livingDustEnabled: "true", livingLightIntensity: "45" },
  querySelector: (selector) => selectors.get(selector) || null,
  removeAttribute: () => {},
};
let raf = 0; let resizeDisconnected = false; let intersectionDisconnected = false;
class ResizeObserver { observe() {} disconnect() { resizeDisconnected = true; } }
class IntersectionObserver { observe() {} disconnect() { intersectionDisconnected = true; } }
Object.defineProperty(globalThis, "navigator", { value: { deviceMemory: 8 }, configurable: true });
global.performance = { now: () => 0 };
global.document = {
  visibilityState: "visible", addEventListener: (type) => events.push(["add", "document", type]),
  removeEventListener: (type) => events.push(["remove", "document", type]),
};
global.ResizeObserver = ResizeObserver; global.IntersectionObserver = IntersectionObserver;
global.window = {
  ResizeObserver, IntersectionObserver, matchMedia: () => ({ matches: false }), devicePixelRatio: 1,
  requestAnimationFrame: () => ++raf, cancelAnimationFrame: (id) => events.push(["cancelRaf", id]),
  requestIdleCallback: () => 77, cancelIdleCallback: (id) => events.push(["cancelIdle", id]),
  addEventListener: () => {}, removeEventListener: () => {}, setTimeout, clearTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"), { filename: process.argv[2] });
const controller = window.GICLEE_LIVING_MUSEUM_LIGHT.create(root);
assert(events.some((entry) => entry[0] === "add" && entry[1] === "scene" && entry[2] === "pointermove"));
controller.setState("drawing"); assert.strictEqual(root.dataset.livingLightState, "drawing");
controller.setState("result"); assert.strictEqual(root.dataset.livingLightState, "result");
controller.destroy();
assert(events.some((entry) => entry[0] === "remove" && entry[1] === "scene" && entry[2] === "pointermove"));
assert(events.some((entry) => entry[0] === "cancelRaf"));
assert(events.some((entry) => entry[0] === "cancelIdle" && entry[1] === 77));
assert(resizeDisconnected); assert(intersectionDisconnected);
assert.strictEqual(canvas.width, 0); assert.strictEqual(canvas.height, 0);
assert.deepStrictEqual(window.GICLEE_LIVING_MUSEUM_LIGHT.status(), []);
console.log(JSON.stringify({ eventCount: events.length }));
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [shutil.which("node") or "node", str(harness), str(LIVING_JS)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["eventCount"] > 5


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
@pytest.mark.parametrize("path", [MAIN_JS, LIVING_JS])
def test_random_artwork_javascript_syntax(path: Path) -> None:
    subprocess.run(
        [shutil.which("node") or "node", "--check", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
