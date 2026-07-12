from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def home_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    local_root = tmp_path / "local"
    roaming_root = tmp_path / "roaming"
    legacy_root = tmp_path / "legacy-variants"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming_root))

    import giclee_app.app_paths as app_paths
    import Komponenty.stronaglowna.homepage_variants as variants

    monkeypatch.setattr(variants, "_LEGACY_VARIANTS_ROOT", legacy_root)
    monkeypatch.setattr(
        variants,
        "_VARIANTS_SENTINEL",
        app_paths.data_path(
            "Komponenty/stronaglowna/data/variants/.path",
            legacy=legacy_root / ".path",
        ),
    )
    monkeypatch.setattr(variants, "VARIANTS_ROOT", legacy_root)
    monkeypatch.setattr(variants, "MANIFEST_PATH", legacy_root / "manifest.json")

    return {
        "local": local_root,
        "roaming": roaming_root,
        "legacy": legacy_root,
        "external": local_root / "data" / "Komponenty" / "stronaglowna" / "data" / "variants",
        "variants": variants,
    }


def _write_json(path: Path, payload: dict) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return raw


def test_variant_index_and_settings_use_legacy_read_and_external_write(home_runtime):
    variants = home_runtime["variants"]
    legacy = home_runtime["legacy"] / "home1"
    external = home_runtime["external"] / "home1"
    legacy_index = _write_json(legacy / "index.json", {"sections": {}, "order": []})
    legacy_settings = _write_json(legacy / "settings.json", {"current": {"legacy": True}})
    template, settings = variants.load_variant_data("home1")
    assert template["order"] == []
    assert settings["current"]["legacy"] is True
    variants.save_variant_data("home1", {"sections": {}, "order": ["new"]}, {"current": {"legacy": False}}, copy_mobile_from_theme=False)
    assert external.joinpath("index.json").is_file()
    assert external.joinpath("settings.json").is_file()
    assert variants.load_variant_data("home1")[0]["order"] == ["new"]
    assert legacy.joinpath("index.json").read_bytes() == legacy_index
    assert legacy.joinpath("settings.json").read_bytes() == legacy_settings


def test_manifest_and_home_flow_metadata_never_write_legacy(home_runtime):
    variants = home_runtime["variants"]
    legacy_manifest = home_runtime["legacy"] / "manifest.json"
    legacy_bytes = _write_json(legacy_manifest, {"active": "home1", "variants": [{"id": "home1", "label": "Legacy"}]})
    assert variants.load_manifest()["variants"][0]["label"] == "Legacy"
    variants.save_manifest({"active": "home1", "variants": [{"id": "home1", "label": "External"}]})
    external_manifest = home_runtime["external"] / "manifest.json"
    assert json.loads(external_manifest.read_text(encoding="utf-8"))["variants"][0]["label"] == "External"
    assert legacy_manifest.read_bytes() == legacy_bytes
    import Komponenty.stronaglowna.home_flow as home_flow
    legacy_flow = home_runtime["legacy"] / "home1" / home_flow.FLOW_FILENAME
    flow_bytes = _write_json(legacy_flow, {"schema": 2, "names": {"section:hero": "Legacy Hero"}})
    assert home_flow.load_flow_metadata("home1")["names"]["section:hero"] == "Legacy Hero"
    home_flow.save_flow_metadata("home1", {"names": {"section:hero": "External Hero"}})
    external_flow = home_runtime["external"] / "home1" / home_flow.FLOW_FILENAME
    assert json.loads(external_flow.read_text(encoding="utf-8"))["names"]["section:hero"] == "External Hero"
    assert legacy_flow.read_bytes() == flow_bytes


def test_home_effect_settings_write_only_to_external_variant(home_runtime):
    legacy = home_runtime["legacy"] / "home2"
    legacy_scroll = _write_json(legacy / "scroll.json", {"enabled": False})
    import Komponenty.stronaglowna.scroll_settings as scroll
    import Komponenty.stronaglowna.final_difference_settings as difference
    import Komponenty.stronaglowna.section_bg_effects_settings as backgrounds
    import Komponenty.stronaglowna.section_effects_storage as effects
    import Komponenty.stronaglowna.studio_reveal_settings as reveal
    assert scroll.load_scroll_config("home2")["enabled"] is False
    scroll.save_scroll_config("home2", {"enabled": True})
    difference.save_final_difference_config("home2", {"enabled": True})
    backgrounds.save_section_bg_effects_for_hook("home2", "potential", {"enabled": True})
    effects.save_section_effects_file("home2", {"potential": {"scroll_reveal": {"enabled": True}}})
    reveal.save_studio_reveal_config("home2", {"enabled": True})
    external = home_runtime["external"] / "home2"
    for name in ("scroll.json", "final-difference.json", "section-bg-effects.json", "section-effects.json", "studio-reveal.json"):
        assert (external / name).is_file()
    assert (legacy / "scroll.json").read_bytes() == legacy_scroll
    for name in ("final-difference.json", "section-bg-effects.json", "section-effects.json", "studio-reveal.json"):
        assert not (legacy / name).exists()


def test_structure_writer_resolves_legacy_source_and_external_targets(home_runtime):
    legacy_index = home_runtime["legacy"] / "home3" / "index.json"
    _write_json(legacy_index, {"sections": {}, "order": []})
    import Komponenty.stronaglowna.home_flow_structure_writer as writer
    assert writer.variant_index_path("home3") == legacy_index
    assert writer.variant_index_path("home3", for_write=True) == home_runtime["external"] / "home3" / "index.json"
    assert writer.writer_state_path("home3", for_write=True).is_relative_to(home_runtime["external"])
    assert writer.writer_backup_dir("home3").is_relative_to(home_runtime["external"])
    assert legacy_index.is_file()
