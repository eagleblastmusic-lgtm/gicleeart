from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECTION_PATH = ROOT / "sections" / "giclee-random-artwork.liquid"
BASE_CSS_PATH = ROOT / "assets" / "giclee-random-artwork.css"
ATMOSPHERE_CSS_PATH = ROOT / "assets" / "giclee-random-artwork-atmosphere.css"
ATMOSPHERE_JS_PATH = ROOT / "assets" / "giclee-random-artwork-atmosphere.js"


def _schema(source: str) -> dict:
    raw = source.split("{% schema %}", 1)[1].split("{% endschema %}", 1)[0]
    return json.loads(raw)


def test_random_artwork_wires_atmosphere_below_content() -> None:
    section = SECTION_PATH.read_text(encoding="utf-8")
    base_css = BASE_CSS_PATH.read_text(encoding="utf-8")

    assert "giclee-random-artwork-atmosphere.css" in section
    assert "giclee-random-artwork-atmosphere.js" in section
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


def test_random_artwork_atmosphere_is_configurable_in_shopify_schema() -> None:
    schema = _schema(SECTION_PATH.read_text(encoding="utf-8"))
    settings = {
        item.get("id"): item
        for item in schema["settings"]
        if isinstance(item, dict) and item.get("id")
    }

    assert settings["enable_atmosphere"]["default"] is True
    assert settings["atmosphere_intensity"]["default"] == 35
    assert settings["atmosphere_intensity"]["max"] == 70
    assert settings["atmosphere_dust"]["default"] == 25
    assert settings["atmosphere_dust"]["max"] == 60


def test_random_artwork_atmosphere_keeps_input_and_motion_accessible() -> None:
    css = ATMOSPHERE_CSS_PATH.read_text(encoding="utf-8")

    assert ".giclee-random-artwork__atmosphere" in css
    assert "pointer-events: none;" in css
    assert "z-index: 1;" in css
    assert "contain: paint;" in css
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
