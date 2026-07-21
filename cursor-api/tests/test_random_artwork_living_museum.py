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


DUST_DEFAULTS = {
    "living_dust_particles": 120,
    "living_dust_opacity": 115,
    "living_dust_size": 125,
    "living_dust_speed": 75,
    "living_dust_fps": 24,
    "living_dust_dpr_cap": 125,
}


def _schema(source: str) -> dict:
    raw = source.split("{% schema %}", 1)[1].split("{% endschema %}", 1)[0]
    return json.loads(raw)


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

    for key in DUST_DEFAULTS:
        data_name = key.removeprefix("living_").replace("_", "-")
        assert f"data-living-{data_name}=" in section
        assert f'"{key}"' in section

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


def test_v3_dust_schema_matches_accepted_console_tuning() -> None:
    schema = _schema(SECTION.read_text(encoding="utf-8"))
    settings = {
        item.get("id"): item
        for item in schema["settings"]
        if isinstance(item, dict) and item.get("id")
    }

    expected_ranges = {
        "living_dust_particles": (20, 240, 120),
        "living_dust_opacity": (0, 200, 115),
        "living_dust_size": (50, 200, 125),
        "living_dust_speed": (0, 200, 75),
        "living_dust_fps": (12, 30, 24),
        "living_dust_dpr_cap": (75, 150, 125),
    }
    for setting_id, (minimum, maximum, default) in expected_ranges.items():
        setting = settings[setting_id]
        assert setting["type"] == "range"
        assert setting["min"] == minimum
        assert setting["max"] == maximum
        assert setting["default"] == default


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


def test_living_museum_optimized_dust_and_cleanup_guardrails() -> None:
    source = LIVING_JS.read_text(encoding="utf-8")
    styles = LIVING_CSS.read_text(encoding="utf-8")
    base_styles = BASE_CSS.read_text(encoding="utf-8")

    for fragment in (
        "desynchronized: true",
        "livingDustParticles",
        "livingDustOpacity",
        "livingDustSize",
        "livingDustSpeed",
        "livingDustFps",
        "livingDustDprCap",
        "this.dustFrameMs = 1000 / this.dustFps",
        "createDustSprite()",
        "createRadialGradient(16, 16, 0, 16, 16, 16)",
        "this.dustParticleLimit",
        "ctx.globalCompositeOperation = 'lighter'",
        "ctx.drawImage(",
        "requestIdleCallback",
        "new IntersectionObserver",
        "new ResizeObserver",
        "document.visibilityState",
        "scene.addEventListener('pointermove'",
        "this.state !== 'drawing'",
        "this.scene?.removeEventListener('pointermove'",
        "window.cancelAnimationFrame(this.rafId)",
        "this.resizeObserver?.disconnect()",
        "this.intersectionObserver?.disconnect()",
        "this.dustCanvas.width = 0",
    ):
        assert fragment in source

    assert "shadowBlur" not in source
    assert "window.addEventListener('pointermove'" not in source
    assert source.count("getBoundingClientRect()") <= 4
    assert "pointer-events: none;" in styles
    assert "contain: paint;" in styles
    assert "mix-blend-mode: screen;" in styles
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
console.log(JSON.stringify({ cases: cases.length, embedded, ajax }));
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
def test_living_museum_runtime_uses_defaults_and_cleans_up(tmp_path: Path) -> None:
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
const gradient = { addColorStop: () => {} };
const spriteContext = {
  createRadialGradient: () => gradient,
  fillRect: () => {},
  set fillStyle(_v) {},
};
const context = {
  setTransform: () => {}, clearRect: () => {}, drawImage: () => {},
  set globalAlpha(_v) {}, set globalCompositeOperation(_v) {},
};
const canvas = node("canvas"); canvas.width = 1; canvas.height = 1; canvas.getContext = () => context;
const selectors = new Map([
  ["[data-grw-scene]", scene], ["[data-grw-living-museum]", layer],
  ["[data-grw-living-spotlight]", spotlight], ["[data-grw-living-dust]", canvas],
  ["[data-grw-draw]", button], ["[data-grw-portal]", node("portal")],
  [".grw--custom-bg-parallax .giclee-random-artwork__custom-bg-layers", node("background")],
  ["[data-grw-result-link]", result],
]);
const root = {
  dataset: {
    livingLightEnabled: "true", livingDustEnabled: "true", livingLightIntensity: "45",
    livingDustParticles: "120", livingDustOpacity: "115", livingDustSize: "125",
    livingDustSpeed: "75", livingDustFps: "24", livingDustDprCap: "125",
  },
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
  createElement: () => ({ width: 0, height: 0, getContext: () => spriteContext }),
};
global.ResizeObserver = ResizeObserver; global.IntersectionObserver = IntersectionObserver;
global.window = {
  ResizeObserver, IntersectionObserver, matchMedia: () => ({ matches: false }), devicePixelRatio: 1,
  requestAnimationFrame: () => ++raf, cancelAnimationFrame: (id) => events.push(["cancelRaf", id]),
  requestIdleCallback: (callback) => { callback(); return 77; },
  cancelIdleCallback: (id) => events.push(["cancelIdle", id]),
  addEventListener: () => {}, removeEventListener: () => {}, setTimeout, clearTimeout,
};
vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"), { filename: process.argv[2] });
const controller = window.GICLEE_LIVING_MUSEUM_LIGHT.create(root);
const status = window.GICLEE_LIVING_MUSEUM_LIGHT.status()[0];
assert.strictEqual(status.particleCount, 120);
assert.strictEqual(status.dustOpacity, 1.15);
assert.strictEqual(status.dustSize, 1.25);
assert.strictEqual(status.dustSpeed, 0.75);
assert.strictEqual(status.dustFps, 24);
assert.strictEqual(status.dustDprCap, 1.25);
assert(events.some((entry) => entry[0] === "add" && entry[1] === "scene" && entry[2] === "pointermove"));
controller.setState("drawing"); assert.strictEqual(root.dataset.livingLightState, "drawing");
controller.setState("result"); assert.strictEqual(root.dataset.livingLightState, "result");
controller.destroy();
assert(events.some((entry) => entry[0] === "remove" && entry[1] === "scene" && entry[2] === "pointermove"));
assert(events.some((entry) => entry[0] === "cancelRaf"));
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
