from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SECTION = ROOT / "sections" / "giclee-random-artwork.liquid"
BASE_CSS = ROOT / "assets" / "giclee-random-artwork.css"
V4_CSS = ROOT / "assets" / "giclee-random-artwork-v4.css"
MAIN_JS = ROOT / "assets" / "giclee-random-artwork.js"
V4_JS = ROOT / "assets" / "giclee-random-artwork-v4.js"
V4_WEBGL = ROOT / "assets" / "giclee-random-artwork-webgl-v4.js"
BASE_WEBGL = ROOT / "assets" / "giclee-random-artwork-webgl.js"
TEMPLATE = ROOT / "templates" / "page.losuj-produkt.json"
COMPONENT = ROOT / "cursor-api" / "Komponenty" / "losujobraz"
MANIFEST = COMPONENT / "data" / "variants" / "manifest.json"
V3 = COMPONENT / "data" / "variants" / "lo3" / "page.losuj-produkt.json"
V4 = COMPONENT / "data" / "variants" / "lo4" / "page.losuj-produkt.json"
V5 = COMPONENT / "data" / "variants" / "lo5" / "page.losuj-produkt.json"
V6 = COMPONENT / "data" / "variants" / "lo6" / "page.losuj-produkt.json"


def _json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("/*"):
        raw = raw.split("*/", 1)[1]
    return json.loads(raw)


def test_v4_isolated_variant_inherits_v3_data_without_mutating_v3() -> None:
    manifest = _json(MANIFEST)
    v3 = _json(V3)
    v4 = _json(V4)
    v5 = _json(V5)
    v6 = _json(V6)
    live = _json(TEMPLATE)

    assert manifest["active"] == "lo6"
    assert manifest["variants"][-1] == {"id": "lo6", "label": "V6 — na bazie V5"}
    assert manifest["variants"][-3] == {"id": "lo4", "label": "V4 — finał muzealny"}
    assert v3["sections"]["random_artwork"]["settings"]["design_variant"] == "v3"
    assert v4["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert v5["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert v5["sections"]["random_artwork"]["settings"]["cursor_smoke_enabled"] is True

    v3_settings = dict(v3["sections"]["random_artwork"]["settings"])
    v4_settings = dict(v4["sections"]["random_artwork"]["settings"])
    v3_settings.pop("design_variant")
    v4_settings.pop("design_variant")
    assert v4_settings == v3_settings
    assert v6 == v5
    assert live == v6


def test_v4_loads_only_its_finale_assets_and_webgl_module() -> None:
    section = SECTION.read_text(encoding="utf-8")

    assert "assign enable_v4_finale = false" in section
    assert "elsif design_variant == 'v4'" in section
    assert "assign enable_living_museum = true" in section
    assert "assign webgl_asset = 'giclee-random-artwork-webgl-v4.js'" in section
    assert "giclee-random-artwork-v4.css" in section
    assert "grw-v4-galaxy-reset-20260725" in section
    assert "grw-galaxy-shell-reset-20260725" in section
    assert "giclee-random-artwork-v4.js" in section
    assert 'data-result-stage="hidden"' in section
    assert 'data-webgl-url="{{ webgl_asset | asset_url }}"' in section
    assert '{ "value": "v4", "label": "V4 — finał muzealny" }' in section


def test_v4_result_is_larger_lighter_and_does_not_create_page_overflow() -> None:
    css = V4_CSS.read_text(encoding="utf-8")
    base_css = BASE_CSS.read_text(encoding="utf-8")

    assert "--grw-v4-frame-max: min(540px, 88vw);" in css
    assert "padding: clamp(3px, 0.45vw, 5px);" in css
    assert "background: #f4f2ec;" in css
    assert "backdrop-filter: none;" in css
    assert "max-height: min(52vh, 560px);" in css
    assert "max-height: min(52vh, calc(100svh - 360px));" in css
    assert "--grw-v4-frame-max: min(92vw, 520px);" in css
    assert ".giclee-random-artwork__canvas" in css
    assert "z-index: 3;" in css
    assert "body:has(.giclee-random-artwork)" in base_css
    assert "overflow: hidden;" in base_css
    assert "grw--webgl-finale" in base_css
    assert "position: fixed;" in base_css
    assert "clip-path: inset(0);" in base_css
    assert "inset: 0;" in base_css


def test_v4_portal_becomes_exhibition_halo_and_resets_by_state() -> None:
    css = V4_CSS.read_text(encoding="utf-8")

    result_portal = (
        '.giclee-random-artwork[data-design-variant="v4"]'
        '[data-state="result"] .giclee-random-artwork__portal'
    )
    assert result_portal in css
    assert "scale: 1.34 0.62;" in css
    assert "opacity: 0.18;" in css
    assert "portal-ring" in css
    assert "opacity: 0;" in css
    assert "radial-gradient(ellipse" in css
    assert '[data-state="idle"]' not in css


def test_v4_typography_actions_and_staged_hierarchy_are_contractual() -> None:
    css = V4_CSS.read_text(encoding="utf-8")

    for stage in ("frame", "identity", "actions"):
        assert f'data-result-stage="{stage}"' in css
    assert "font-family: var(--font-heading--family, Georgia" in css
    assert "font-weight: 400;" in css
    assert "letter-spacing: 0.26em;" in css
    assert "background: rgba(12, 11, 10, 0.62);" in css
    assert "border-radius: 3px;" in css
    assert ".giclee-random-artwork__cta--primary::after" in css
    assert ".giclee-random-artwork__cta--primary.giclee-galaxy-btn" in css
    galaxy_reset = css.split(
        ".giclee-random-artwork__cta--primary.giclee-galaxy-btn {",
        1,
    )[1].split("}", 1)[0]
    for declaration in (
        "min-width: 0;",
        "height: auto;",
        "padding: 0;",
        "border: 0;",
        "background: transparent;",
        "box-shadow: none;",
    ):
        assert declaration in galaxy_reset
    galaxy_css = (
        ROOT / "assets" / "giclee-random-artwork-galaxy-btn.css"
    ).read_text(encoding="utf-8")
    protected_selector = (
        ".giclee-random-artwork__cta.giclee-galaxy-btn"
    )
    assert "html[data-giclee-button-style]" in galaxy_css
    assert protected_selector in galaxy_css
    assert f"{protected_selector}::before" in galaxy_css
    assert "flex: 0 0 auto;" in galaxy_css
    assert ".giclee-random-artwork__cta--ghost" in css
    assert "border: 0;" in css
    assert ":focus-visible" in css


def test_v4_webgl_extends_finale_and_keeps_non_winners_during_handoff() -> None:
    source = V4_WEBGL.read_text(encoding="utf-8")
    base = BASE_WEBGL.read_text(encoding="utf-8")

    assert "const FINALE_EXTRA_MS = 1100;" in source
    assert "const GROW_PORTION = 0.4;" in source
    assert "BASE_TOTAL_MS + (reducedMotion ? 0 : FINALE_EXTRA_MS)" in source
    assert "ringMat.opacity" in source and "1 - reveal * 0.96" in source
    assert "const afterglow = 1 - settleT;" in source
    assert "introEase * afterglow" in source
    assert "glowMat.opacity = 0;" in source
    assert "glow.scale.set(6 + reveal * 2.4, 6 - reveal * 2.6, 1);" in source
    assert "orbitZ - retreat * 3.6" in source
    assert "(1 - retreat) * afterglow" in source
    assert "afterglow * (1 - reveal) * 0.34" in source
    assert "entry.pivot.visible = false" in source
    assert "growT * 0.82" in source
    assert "resolveHandoffPose" in source
    assert "getHandoffTarget" in source
    assert "onHandoffPrepare" in source
    assert "freeze" in source
    assert "setExhibitHover" in source
    assert "EXHIBIT_HOVER_SCALE" in source
    assert "applyFlatFacing" in source
    assert "getWorldDirection" in source
    assert ".slerp(_flatQuat, settleT)" in source
    assert "multiply(_flipY)" not in source
    assert source.count("requestAnimationFrame(render)") == 2
    assert "const FINALE_EXTRA_MS" not in base


def test_existing_draw_selection_and_fallback_contract_remains_intact() -> None:
    main = MAIN_JS.read_text(encoding="utf-8")

    assert "if (this.isDrawing) return;" in main
    assert "const winner = this.pickWinner();" in main
    assert "await this.runDrawingSequence(winner);" in main
    assert "const module = await import(this.webglUrl);" in main
    assert "if (prefersReducedMotion())" in main
    assert "prepareHandoffTarget" in main
    assert "getHandoffTargetRect" in main
    assert "grw--webgl-finale" in main
    assert "this.sceneController.freeze" in main
    assert "bindFinaleExhibitHover" in main
    assert "this.resultLink.href = winner.url" in main
    assert "this.viewCta.href = winner.url" in main
    assert "this.teardownScene();" in main
    assert "playResultIdentityMotion" in main
    assert "initResultTitleGradientReveal" in main
    assert "revealResultArtistFade" in main
    assert "data-grw-result-artist-fade" in SECTION.read_text(encoding="utf-8")
    assert "data-grw-result-title-fade" in SECTION.read_text(encoding="utf-8")
    assert "is-artist-fade-ready" in BASE_CSS.read_text(encoding="utf-8")
    assert "grw-result-title-gradient" in BASE_CSS.read_text(encoding="utf-8")
    assert "is-title-gradient-ready" in BASE_CSS.read_text(encoding="utf-8")
    assert "result-artist" not in V4_CSS.read_text(encoding="utf-8").split("grw--webgl-finale")[1].split(".giclee-random-artwork__frame")[0]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_v4_result_controller_runtime_sequence_and_reset(tmp_path: Path) -> None:
    harness = tmp_path / "v4-runtime.js"
    harness.write_text(
        r'''"use strict";
const fs = require("fs");
const vm = require("vm");
const assert = require("assert");
let timerId = 0;
const timers = new Map();
const artist = { textContent: "Vincent van Gogh", hidden: true };
const year = { textContent: ", 1888", hidden: true };
const result = {};
const root = {
  dataset: { designVariant: "v4", state: "idle", resultStage: "hidden" },
  querySelector: (selector) => ({
    "[data-grw-result]": result,
    "[data-grw-result-artist]": artist,
    "[data-grw-result-year]": year,
  }[selector] || null),
  removeAttribute(name) {
    const key = name.replace(/^data-/, "").replace(/-([a-z])/g, (_m, c) => c.toUpperCase());
    delete this.dataset[key];
  },
};
class ElementClass {}
ElementClass.prototype.connectedCallback = function() {};
ElementClass.prototype.disconnectedCallback = function() {};
ElementClass.prototype.setState = function(state) { this.dataset.state = state; };
global.window = {
  matchMedia: () => ({ matches: false }),
  setTimeout: (callback, delay) => {
    const id = ++timerId;
    timers.set(id, {
      delay,
      callback: () => {
        timers.delete(id);
        callback();
      },
    });
    return id;
  },
  clearTimeout: (id) => timers.delete(id),
  customElements: { get: () => ElementClass },
};
global.document = { querySelectorAll: () => [] };
vm.runInThisContext(fs.readFileSync(process.argv[2], "utf8"), { filename: process.argv[2] });
const controller = window.GICLEE_RANDOM_ARTWORK_V4.create(root);
controller.setState("result");
assert.strictEqual(root.dataset.resultStage, "frame");
assert.strictEqual(artist.hidden, false);
assert.strictEqual(year.hidden, false);
const ordered = [...timers.values()].sort((a, b) => a.delay - b.delay);
assert.deepStrictEqual(ordered.map((item) => item.delay), [300, 550]);
ordered[0].callback();
assert.strictEqual(root.dataset.resultStage, "identity");
ordered[1].callback();
assert.strictEqual(root.dataset.resultStage, "actions");
assert.strictEqual(root.dataset.resultCeremony, "complete");
controller.setState("loading");
assert.strictEqual(root.dataset.resultStage, "hidden");
assert.strictEqual(timers.size, 0);
controller.destroy();
assert.deepStrictEqual(window.GICLEE_RANDOM_ARTWORK_V4.status(), []);
console.log(JSON.stringify({ stage: root.dataset.resultStage || null }));
''',
        encoding="utf-8",
    )
    result = subprocess.run(
        [shutil.which("node") or "node", str(harness), str(V4_JS)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["stage"] is None


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
@pytest.mark.parametrize("path", [V4_JS, V4_WEBGL])
def test_v4_javascript_syntax(path: Path, tmp_path: Path) -> None:
    node = shutil.which("node") or "node"
    if path == V4_WEBGL:
        module_path = tmp_path / f"{path.stem}.mjs"
        module_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(
            [node, "--check", str(module_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return

    subprocess.run(
        [node, "--check", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
