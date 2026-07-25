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
V3_PATH = COMPONENT_DIR / "data" / "variants" / "lo3" / "page.losuj-produkt.json"
V4_PATH = COMPONENT_DIR / "data" / "variants" / "lo4" / "page.losuj-produkt.json"
V5_PATH = COMPONENT_DIR / "data" / "variants" / "lo5" / "page.losuj-produkt.json"
V6_PATH = COMPONENT_DIR / "data" / "variants" / "lo6" / "page.losuj-produkt.json"
GUI_PATH = COMPONENT_DIR / "gui.py"
REGISTRY_PATH = COMPONENT_DIR / "registry.py"

LIVING_MUSEUM_DEFAULTS = {
    "living_light_enabled": True,
    "living_dust_enabled": True,
    "living_light_intensity": 45,
}


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


def test_random_artwork_wires_v2_atmosphere_below_content() -> None:
    section = SECTION_PATH.read_text(encoding="utf-8")
    base_css = BASE_CSS_PATH.read_text(encoding="utf-8")

    assert "giclee-random-artwork-atmosphere.css" in section
    assert "giclee-random-artwork-atmosphere.js" in section
    assert 'data-design-variant="{{ design_variant }}"' in section
    assert 'data-atmosphere-enabled=' in section
    for key in (
        "intensity",
        "glow-size",
        "glow-response",
        "haze",
        "haze-speed",
        "dust",
        "dust-amount",
        "dust-speed",
    ):
        assert f'data-atmosphere-{key}=' in section
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


def test_random_artwork_variants_load_only_their_own_layers() -> None:
    section = SECTION_PATH.read_text(encoding="utf-8")

    assert "assign design_variant = section.settings.design_variant | default: 'v1'" in section
    assert "assign enable_atmosphere = false" in section
    assert "assign enable_living_museum = false" in section
    assert "assign enable_v4_finale = false" in section
    assert "if design_variant == 'v2'" in section
    assert "elsif design_variant == 'v3'" in section
    assert "elsif design_variant == 'v4'" in section
    assert "assign webgl_asset = 'giclee-random-artwork-webgl-v4.js'" in section
    assert section.count("{%- if enable_atmosphere -%}") == 2
    assert section.count("{%- if enable_living_museum -%}") == 1
    assert section.count("{%- if enable_v4_finale -%}") == 2
    assert "section.settings.enable_atmosphere" not in section


def test_random_artwork_design_variant_and_schema() -> None:
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
        {"value": "v3", "label": "V3 — Living Museum Light"},
        {"value": "v4", "label": "V4 — finał muzealny"},
    ]
    assert "enable_atmosphere" not in settings

    expected_ranges = {
        "living_light_intensity": (0, 100, 45),
    }
    for setting_id, (minimum, maximum, default) in expected_ranges.items():
        setting = settings[setting_id]
        assert setting["type"] == "range"
        assert setting["min"] == minimum
        assert setting["max"] == maximum
        assert setting["default"] == default

    assert settings["living_light_enabled"]["default"] is True
    assert settings["living_dust_enabled"]["default"] is True


def test_giclee_app_exposes_v1_v3_v4_v5_v6_and_atmosphere_editor() -> None:
    manifest = _json_file(MANIFEST_PATH)
    assert manifest["active"] == "lo6"
    assert manifest["variants"] == [
        {"id": "lo1", "label": "V1 — podstawowa"},
        {"id": "lo3", "label": "V3 — Living Museum Light"},
        {"id": "lo4", "label": "V4 — finał muzealny"},
        {"id": "lo5", "label": "V5 — V4 + dym kursora"},
        {"id": "lo6", "label": "V6 — na bazie V5"},
    ]

    v1 = _json_file(V1_PATH)
    v3 = _json_file(V3_PATH)
    v4 = _json_file(V4_PATH)
    v5 = _json_file(V5_PATH)
    v6 = _json_file(V6_PATH)
    live = _json_file(TEMPLATE_PATH)
    settings_by_mode = {
        "v1": v1["sections"]["random_artwork"]["settings"],
        "v3": v3["sections"]["random_artwork"]["settings"],
        "v4": v4["sections"]["random_artwork"]["settings"],
    }

    for mode, settings in settings_by_mode.items():
        assert settings["design_variant"] == mode
        for key, value in LIVING_MUSEUM_DEFAULTS.items():
            assert settings[key] == value

    # Living Museum strojenie wspólne dla lo1/lo3/lo4 (V1 trzyma wartości bez ładowania warstwy).
    shared_keys = tuple(LIVING_MUSEUM_DEFAULTS)
    baseline = {key: settings_by_mode["v1"][key] for key in shared_keys}
    for mode, settings in settings_by_mode.items():
        for key, value in baseline.items():
            assert settings[key] == value, f"{mode}.{key}"

    # Active V6 is a V5 snapshot: V4 design_variant, light off, smoke on.
    assert v5["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert v5["sections"]["random_artwork"]["settings"]["living_light_enabled"] is False
    assert v5["sections"]["random_artwork"]["settings"]["living_dust_enabled"] is True
    assert v5["sections"]["random_artwork"]["settings"]["cursor_smoke_enabled"] is True
    assert v5["sections"]["random_artwork"]["settings"]["background_parallax"] is True
    assert v6 == v5
    assert v6 == live

    gui = GUI_PATH.read_text(encoding="utf-8")
    registry = REGISTRY_PATH.read_text(encoding="utf-8")
    assert "V3 — Living Museum Light" in gui
    assert "V4 — finał muzealny" in gui
    assert "V5 — V4 z dymem kursora" in gui
    assert "V6 — na bazie V5" in gui
    assert "V2 — atmosfera muzealna" not in gui
    assert 'variant_label_default="V1 — podstawowa"' in gui
    assert '("Edytuj atmosferę…"' in gui
    assert '_ATMOSPHERE_ZONE_ID = "random_artwork_atmosphere"' in gui
    assert 'zone_id="random_artwork_atmosphere"' in registry
    assert 'label="Edytuj atmosferę…"' in registry
    assert '"atmosphere_intensity"' not in registry
    for key in LIVING_MUSEUM_DEFAULTS:
        assert f'"{key}"' in registry


def test_random_artwork_atmosphere_keeps_input_and_motion_accessible() -> None:
    css = ATMOSPHERE_CSS_PATH.read_text(encoding="utf-8")

    assert ".giclee-random-artwork__atmosphere" in css
    assert "pointer-events: none;" in css
    assert "z-index: 1;" in css
    assert "contain: paint;" in css
    assert "--grw-haze-gallery-opacity" in css
    assert "--grw-haze-depth-opacity" in css
    assert "--grw-haze-gallery-duration" in css
    assert "--grw-haze-depth-duration" in css
    assert 'data-atmosphere-haze-paused="true"' in css
    assert "@media (max-width: 749px), (hover: none), (pointer: coarse)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert css.count("giclee-random-artwork__atmosphere-dust") >= 3
    assert "display: none;" in css


def test_random_artwork_atmosphere_is_tunable_and_frame_limited() -> None:
    source = ATMOSPHERE_JS_PATH.read_text(encoding="utf-8")

    assert "const MAX_DEVICE_PIXEL_RATIO = 1.5;" in source
    assert "const DUST_FRAME_INTERVAL_MS = 1000 / 24;" in source
    for dataset_key in (
        "atmosphereIntensity",
        "atmosphereGlowSize",
        "atmosphereGlowResponse",
        "atmosphereHaze",
        "atmosphereHazeSpeed",
        "atmosphereDust",
        "atmosphereDustAmount",
        "atmosphereDustSpeed",
    ):
        assert f"'{dataset_key}'" in source
    assert "new IntersectionObserver" in source
    assert "new ResizeObserver" in source
    assert "document.hidden" in source
    assert "scene.addEventListener('pointermove'" in source
    assert "{ passive: true }" in source
    assert "requestAnimationFrame" in source
    assert "cancelAnimationFrame" in source
    assert "setInterval" not in source
    assert "window.addEventListener('pointermove'" not in source
    assert "baseCount * amountScale" in source
    assert "clamp(baseCount * amountScale, 0, 48)" in source
    assert "particle.speed * this.dustSpeed" in source
    assert "responseTimeMs" in source
    assert source.count("getBoundingClientRect()") <= 3
