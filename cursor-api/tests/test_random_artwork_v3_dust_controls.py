from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SECTION = ROOT / "sections" / "giclee-random-artwork.liquid"
LIVING_JS = ROOT / "assets" / "giclee-random-artwork-living-museum.js"
LIVING_CSS = ROOT / "assets" / "giclee-random-artwork-living-museum.css"
REGISTRY = ROOT / "cursor-api" / "Komponenty" / "losujobraz" / "registry.py"
TEMPLATE = ROOT / "templates" / "page.losuj-produkt.json"
VARIANTS = tuple(
    ROOT
    / "cursor-api"
    / "Komponenty"
    / "losujobraz"
    / "data"
    / "variants"
    / variant
    / "page.losuj-produkt.json"
    for variant in ("lo1", "lo3", "lo4", "lo5", "lo6")
)


DEFAULTS = {
    "living_dust_particles": 120,
    "living_dust_opacity": 115,
    "living_dust_size": 125,
    "living_dust_speed": 75,
    "living_dust_fps": 24,
    "living_dust_dpr_cap": 125,
}

RANGES = {
    "living_dust_particles": (20, 240),
    "living_dust_opacity": (0, 200),
    "living_dust_size": (50, 200),
    "living_dust_speed": (0, 200),
    "living_dust_fps": (12, 30),
    "living_dust_dpr_cap": (75, 150),
}


def _json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("/*"):
        raw = raw.split("*/", 1)[1]
    return json.loads(raw)


def _schema() -> dict:
    source = SECTION.read_text(encoding="utf-8")
    raw = source.split("{% schema %}", 1)[1].split("{% endschema %}", 1)[0]
    return json.loads(raw)


def test_living_dust_defaults_are_persisted_in_all_variants_and_live_template() -> None:
    documents = [*_json_variants(), _json(TEMPLATE)]
    for document in documents:
        settings = document["sections"]["random_artwork"]["settings"]
        for key, expected in DEFAULTS.items():
            assert settings[key] == expected

    assert documents[0]["sections"]["random_artwork"]["settings"]["design_variant"] == "v1"
    assert documents[1]["sections"]["random_artwork"]["settings"]["design_variant"] == "v3"
    assert documents[2]["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert documents[3]["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert documents[4]["sections"]["random_artwork"]["settings"]["design_variant"] == "v4"
    assert documents[4] == documents[3]
    assert documents[5] == documents[4]


def _json_variants() -> list[dict]:
    return [_json(path) for path in VARIANTS]


def test_living_dust_controls_are_exposed_in_giclee_app_and_shopify_schema() -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    settings = {
        item.get("id"): item
        for item in _schema()["settings"]
        if isinstance(item, dict) and item.get("id")
    }

    for key, expected in DEFAULTS.items():
        assert f'"{key}"' in registry
        assert settings[key]["type"] == "range"
        assert settings[key]["default"] == expected
        assert (settings[key]["min"], settings[key]["max"]) == RANGES[key]


def test_v3_v4_use_optimized_sprite_renderer_without_particle_shadows() -> None:
    source = LIVING_JS.read_text(encoding="utf-8")

    assert "desynchronized: true" in source
    assert "createRadialGradient(16, 16, 0, 16, 16, 16)" in source
    assert "ctx.drawImage(" in source
    assert "ctx.globalCompositeOperation = 'lighter'" in source
    assert "shadowBlur" not in source
    assert "this.dustFrameMs = 1000 / this.dustFps" in source
    assert "is-dust-fade-ready" in source
    assert "is-dust-fade-ready" in LIVING_CSS.read_text(encoding="utf-8")
    assert "readNumber(root, 'livingDustParticles', 120, 20, 240)" in source
    assert "readNumber(root, 'livingDustOpacity', 115, 0, 200)" in source
    assert "readNumber(root, 'livingDustSize', 125, 50, 200)" in source
    assert "readNumber(root, 'livingDustSpeed', 75, 0, 200)" in source
    assert "readNumber(root, 'livingDustFps', 24, 12, 30)" in source
    assert "readNumber(root, 'livingDustDprCap', 125, 75, 150)" in source
