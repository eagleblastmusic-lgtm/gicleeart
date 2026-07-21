from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECTION_PATH = ROOT / "sections" / "giclee-random-artwork.liquid"
BASE_CSS_PATH = ROOT / "assets" / "giclee-random-artwork.css"
ATMOSPHERE_CSS_PATH = ROOT / "assets" / "giclee-random-artwork-atmosphere.css"
ATMOSPHERE_JS_PATH = ROOT / "assets" / "giclee-random-artwork-atmosphere.js"
TEMPLATE_PATH = ROOT / "templates" / "page.losuj-produkt.json"
COMPONENT_DIR = ROOT / "cursor-api" / "Komponenty" / "losujobraz"
MANIFEST_PATH = COMPONENT_DIR / "data" / "variants" / "manifest.json"
V1_PATH = COMPONENT_DIR / "data" / "variants" / "lo1" / "page.losuj-produkt.json"
V2_PATH = COMPONENT_DIR / "data" / "variants" / "lo2" / "page.losuj-produkt.json"
GUI_PATH = COMPONENT_DIR / "gui.py"


def _strip_json_header(raw: str) -> str:
    if raw.lstrip().startswith("/*"):
        end = raw.find("*/")
        if end >= 0:
            return raw[end + 2 :]
    return raw


def _json_file(path: Path) -> dict:
    return json.loads(_strip_json_header(path.read_text(encoding="utf-8")))


def _schema(source: str) -> dict:
    raw = source.split("{% schema %}", 1)[1].split("{% endschema %}", 1)[0]
    return json.loads(raw)


def test_random_artwork_wires_atmosphere_below_content() -> None:
    section = SECTION_PATH.read_text(encoding="utf-8")
    base_css = BASE_CSS_PATH.read_text(encoding="utf-8")

    assert "giclee-random-artwork-atmosphere.css" in section
    assert "giclee-random-artwork-atmosphere.js" in section
    assert 'data-design-variant="{{ design_variant }}"' in section
    assert 'data-atmosphere-enabled=' in section
    assert 'data-atmosphere-intensity=' in section
    assert 'data-atmosphere-dust=' in section
    assert "data-grw-atmosphere" in section
    assert "data-grw-atmosphere-glow" in section
    assert "data-grw-atmosphere-dust" in section

    canvas_index = section.index("data-grw-canvas-mount")
    atmosphere_index = section.index("data-grw-atmosphere")
    portal_index = section.index("data-grw-portal")
    content_index = section.index('class="giclee-random-artwork__content"')
    assert canvas_index < atmosphere_index < portal_index < content_index

    assert ".giclee-random-artwork__content" in base_css
    assert "z-index: 2;" in base_css


def test_random_artwork_v1_does_not_load_v2_atmosphere() -> None:
    section = SECTION_PATH.read_text(encoding="utf-8")

    assert "assign design_variant = section.settings.design_variant | default: 'v1'" in section
    assert "assign enable_atmosphere = false" in section
    assert "if design_variant == 'v2'" in section
    assert section.count("{%- if enable_atmosphere -%}") == 2
    assert "section.settings.enable_atmosphere" not in section


def test_random_artwork_design_variant_is_configurable_in_shopify_schema() -> None:
    schema = _schema(SECTION_PATH.read_text(encoding="utf-8"))
    settings = {
        item.get("id"): item
        for item in schema["settings"]
        if isinstance(item, dict) and item.get("id")
    }

    design = settings["design_variant"]
    assert design["type"] == "select"
    assert design["default"] == "v1"
    assert design["options"] == [
        {"value": "v1", "label": "V1 — podstawowa"},
        {"value": "v2", "label": "V2 — atmosfera muzealna"},
    ]
    assert "enable_atmosphere" not in settings
    assert settings["atmosphere_intensity"]["default"] == 35
    assert settings["atmosphere_intensity"]["max"] == 70
    assert settings["atmosphere_dust"]["default"] == 25
    assert settings["atmosphere_dust"]["max"] == 60


def test_giclee_app_exposes_named_v1_and_v2_design_versions() -> None:
    manifest = _json_file(MANIFEST_PATH)
    assert manifest["active"] == "lo2"
    assert manifest["variants"] == [
        {"id": "lo1", "label": "V1 — podstawowa"},
        {"id": "lo2", "label": "V2 — atmosfera muzealna"},
    ]

    v1 = _json_file(V1_PATH)
    v2 = _json_file(V2_PATH)
    live = _json_file(TEMPLATE_PATH)
    v1_settings = v1["sections"]["random_artwork"]["settings"]
    v2_settings = v2["sections"]["random_artwork"]["settings"]
    live_settings = live["sections"]["random_artwork"]["settings"]

    assert v1_settings["design_variant"] == "v1"
    assert v2_settings["design_variant"] == "v2"
    assert live_settings["design_variant"] == "v2"
    assert v1_settings["atmosphere_intensity"] == 35
    assert v2_settings["atmosphere_intensity"] == 35
    assert v1_settings["atmosphere_dust"] == 25
    assert v2_settings["atmosphere_dust"] == 25

    v1_without_mode = dict(v1_settings)
    v2_without_mode = dict(v2_settings)
    v1_without_mode.pop("design_variant")
    v2_without_mode.pop("design_variant")
    assert v1_without_mode == v2_without_mode
    assert v2 == live

    gui = GUI_PATH.read_text(encoding="utf-8")
    assert "Lista «Wersja» jest listą wariantów designu" in gui
    assert 'variant_label_default="V1 — podstawowa"' in gui


def test_random_artwork_atmosphere_keeps_input_and_motion_accessible() -> None:
    css = ATMOSPHERE_CSS_PATH.read_text(encoding="utf-8")

    assert ".giclee-random-artwork__atmosphere" in css
    assert "pointer-events: none;" in css
    assert "z-index: 1;" in css
    assert "contain: paint;" in css
    assert "isolation: isolate;" in css
    assert "opacity: calc(0.46 + var(--grw-dust-level) * 1.55);" in css
    assert "brightness(1.55)" in css
    assert "mix-blend-mode: screen;" in css
    assert "opacity: calc(0.16 + var(--grw-atmosphere-level) * 0.96);" in css
    assert "@media (max-width: 749px), (hover: none), (pointer: coarse)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert css.count("giclee-random-artwork__atmosphere-dust") >= 3
    assert "display: none;" in css


def test_random_artwork_atmosphere_is_viewport_scoped_and_frame_limited() -> None:
    source = ATMOSPHERE_JS_PATH.read_text(encoding="utf-8")

    assert "const MAX_DEVICE_PIXEL_RATIO = 1.5;" in source
    assert "const DUST_FRAME_INTERVAL_MS = 1000 / 24;" in source
    assert "new IntersectionObserver" in source
    assert "new ResizeObserver" in source
    assert "document.hidden" in source
    assert "scene.addEventListener('pointermove'" in source
    assert "{ passive: true }" in source
    assert "requestAnimationFrame" in source
    assert "cancelAnimationFrame" in source
    assert "setInterval" not in source
    assert "window.addEventListener('pointermove'" not in source
    assert "10, 36" in source
    assert source.count("getBoundingClientRect()") <= 3
