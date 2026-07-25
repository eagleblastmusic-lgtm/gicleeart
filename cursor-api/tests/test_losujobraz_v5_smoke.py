"""Kontrakt wariantu V5 modułu Losuj Obraz."""

from __future__ import annotations

import json
from pathlib import Path

from Komponenty._shared.theme_page_editor.service_base import (
    apply_zone_values,
    load_zone_values,
)
from Komponenty.losujobraz.registry import PAGE_ZONES


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "cursor-api" / "Komponenty" / "losujobraz"
VARIANTS_ROOT = COMPONENT_ROOT / "data" / "variants"


def _read_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if raw.lstrip().startswith("/*"):
        raw = raw.split("*/", 1)[1]
    return json.loads(raw)


def test_v5_is_v4_copy_with_cursor_smoke_enabled() -> None:
    manifest = _read_json(VARIANTS_ROOT / "manifest.json")
    v5 = _read_json(VARIANTS_ROOT / "lo5" / "page.losuj-produkt.json")
    v6 = _read_json(VARIANTS_ROOT / "lo6" / "page.losuj-produkt.json")
    live = _read_json(REPO_ROOT / "templates" / "page.losuj-produkt.json")
    settings = v5["sections"]["random_artwork"]["settings"]
    labels = {row["id"]: row["label"] for row in manifest["variants"]}

    assert manifest["active"] == "lo6"
    assert labels["lo5"] == "V5 — V4 + dym kursora"
    assert labels["lo6"] == "V6 — na bazie V5"
    assert settings["design_variant"] == "v4"
    assert settings["cursor_smoke_enabled"] is True
    assert settings["living_light_enabled"] is False
    assert settings["living_dust_enabled"] is True
    assert settings["background_parallax"] is True
    assert settings["cursor_smoke_preset"] == "elegant"
    assert settings["cursor_smoke_quality"] == "standard"
    assert settings["cursor_smoke_auto_enabled"] is True
    for field_id in (
        "cursor_smoke_intensity",
        "cursor_smoke_opacity",
        "cursor_smoke_size",
        "cursor_smoke_force",
        "cursor_smoke_persistence",
        "cursor_smoke_swirl",
        "cursor_smoke_bloom",
        "cursor_smoke_auto_frequency",
    ):
        assert settings[field_id] == 100
    assert v6 == v5
    assert v6 == live


def test_intro_circle_gates_dust_and_smoke_runtime() -> None:
    main_js = (REPO_ROOT / "assets" / "giclee-random-artwork.js").read_text(encoding="utf-8")
    living_js = (
        REPO_ROOT / "assets" / "giclee-random-artwork-living-museum.js"
    ).read_text(encoding="utf-8")
    fluid_js = (REPO_ROOT / "assets" / "giclee-random-artwork-fluid-v2.js").read_text(
        encoding="utf-8"
    )

    assert "markIntroCircleDone" in main_js
    assert "dataset.introCircleDone = 'true'" in main_js
    assert "scheduleDustAfterIntroCircle" in living_js
    assert "whenIntroCircleDone" in fluid_js
    assert "introCircleDone" in living_js
    assert "parallaxEnabled" in living_js


def test_older_variants_do_not_enable_cursor_smoke() -> None:
    for variant_id in ("lo1", "lo3", "lo4"):
        data = _read_json(VARIANTS_ROOT / variant_id / "page.losuj-produkt.json")
        settings = data["sections"]["random_artwork"]["settings"]
        assert settings.get("cursor_smoke_enabled", False) is False


def test_gicleeapp_exposes_v5_cursor_smoke_toggle_and_parameters() -> None:
    zone = next(zone for zone in PAGE_ZONES if zone.zone_id == "random_artwork_v5_smoke")
    fields = {field.field_id: field for field in zone.fields}

    assert zone.label == "V5 — włącz/wyłącz dym"
    assert "random_artwork_v5_smoke_parameters" not in {
        z.zone_id for z in PAGE_ZONES
    }
    assert fields["cursor_smoke_enabled"].kind == "bool"
    assert all(field.hint for field in zone.fields)
    assert fields["cursor_smoke_preset"].kind == "choice"
    assert dict(fields["cursor_smoke_preset"].choices) == {
        "elegant": "Elegant V2 — oryginalny",
        "gallery_mist": "Gallery Mist — miękka mgła",
        "silk": "Silk — dłuższe jedwabne smugi",
        "whisper": "Whisper — prawie niewidoczny",
    }
    assert fields["cursor_smoke_quality"].kind == "choice"
    assert fields["cursor_smoke_swirl"].min_value == 0
    assert fields["cursor_smoke_swirl"].max_value == 200
    assert fields["cursor_smoke_auto_enabled"].kind == "bool"


def test_gicleeapp_places_smoke_editor_action() -> None:
    gui = (COMPONENT_ROOT / "gui.py").read_text(encoding="utf-8")
    assert '("Dym kursora V5…", lambda: _open_v5_smoke_editor(host))' in gui
    assert "Edytuj dym V5…" not in gui
    assert "_open_v5_smoke_parameters_editor" not in gui


def test_smoke_choice_values_round_trip_as_internal_ids() -> None:
    template = _read_json(VARIANTS_ROOT / "lo6" / "page.losuj-produkt.json")
    zone = next(
        zone for zone in PAGE_ZONES if zone.zone_id == "random_artwork_v5_smoke"
    )
    values = load_zone_values(template, zone)
    values.update(
        cursor_smoke_preset="silk",
        cursor_smoke_quality="high",
        cursor_smoke_swirl=145,
        cursor_smoke_auto_enabled=False,
    )
    apply_zone_values(template, zone, values)
    settings = template["sections"]["random_artwork"]["settings"]

    assert settings["cursor_smoke_preset"] == "silk"
    assert settings["cursor_smoke_quality"] == "high"
    assert settings["cursor_smoke_swirl"] == 145
    assert settings["cursor_smoke_auto_enabled"] is False


def test_theme_loads_smoke_assets_conditionally() -> None:
    section = (REPO_ROOT / "sections" / "giclee-random-artwork.liquid").read_text(
        encoding="utf-8"
    )
    assert "if cursor_smoke_enabled" in section
    assert "giclee-random-artwork-fluid-v2.js" in section
    assert "giclee-random-artwork-fluid-v2-shaders.js" in section
    assert 'data-cursor-smoke-enabled=' in section
    assert 'data-cursor-smoke-preset=' in section
    assert '"id": "cursor_smoke_quality"' in section


def test_smoke_runtime_applies_presets_and_all_controls() -> None:
    script = (REPO_ROOT / "assets" / "giclee-random-artwork-fluid-v2.js").read_text(
        encoding="utf-8"
    )

    for preset in ("elegant", "gallery_mist", "silk", "whisper"):
        assert f"{preset}:" in script
    for setting in (
        "cursorSmokeIntensity",
        "cursorSmokeOpacity",
        "cursorSmokeSize",
        "cursorSmokeForce",
        "cursorSmokePersistence",
        "cursorSmokeSwirl",
        "cursorSmokeBloom",
        "cursorSmokeAutoEnabled",
        "cursorSmokeAutoFrequency",
    ):
        assert setting in script


def test_gicleeapp_exposes_galaxy_btn_variant_in_fine_art_oracle() -> None:
    zone = next(zone for zone in PAGE_ZONES if zone.zone_id == "random_artwork_draw")
    fields = {field.field_id: field for field in zone.fields}
    field = fields["galaxy_btn_variant"]

    assert field.kind == "choice"
    assert dict(field.choices) == {
        "v1": "V1 — srebrny (obecny)",
        "v2": "V2 — subtelny",
    }

    for variant_id in ("lo1", "lo3", "lo4", "lo5", "lo6"):
        data = _read_json(VARIANTS_ROOT / variant_id / "page.losuj-produkt.json")
        assert data["sections"]["random_artwork"]["settings"]["galaxy_btn_variant"] == "v1"

    template = _read_json(VARIANTS_ROOT / "lo6" / "page.losuj-produkt.json")
    values = load_zone_values(template, zone)
    values["galaxy_btn_variant"] = "v2"
    apply_zone_values(template, zone, values)
    assert template["sections"]["random_artwork"]["settings"]["galaxy_btn_variant"] == "v2"

    section = (REPO_ROOT / "sections" / "giclee-random-artwork.liquid").read_text(
        encoding="utf-8"
    )
    css = (REPO_ROOT / "assets" / "giclee-random-artwork-galaxy-btn.css").read_text(
        encoding="utf-8"
    )
    assert "galaxy_btn_variant" in section
    assert "giclee-galaxy-btn--{{ galaxy_btn_variant }}" in section
    assert section.count('data-grw-galaxy-btn') >= 2
    assert 'data-grw-view' in section and 'giclee-galaxy-btn' in section
    assert ".giclee-galaxy-btn--v2 .giclee-galaxy-btn__circle" in css
    assert "#b4bac2" in css
    assert "#d2d6dc" in css
