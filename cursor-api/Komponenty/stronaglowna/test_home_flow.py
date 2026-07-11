from __future__ import annotations

import json

from .home_flow import (
    FLOW_SCHEMA_VERSION,
    STRUCTURE_DRAFT_KEY,
    flow_path,
    load_flow_metadata,
    reset_flow_name,
    resolve_flow_items,
    save_flow_metadata,
    set_flow_name,
)


def test_home_flow_numbers_sections_and_phases_independently(tmp_path) -> None:
    items = resolve_flow_items("home-test", variants_root=tmp_path)

    section_codes = [item.code for item in items if item.kind == "section"]
    phase_codes = [item.code for item in items if item.kind == "phase"]

    assert section_codes == [f"GH-{index:02d}" for index in range(len(section_codes))]
    assert phase_codes == [f"GH-T{index:02d}" for index in range(1, len(phase_codes) + 1)]
    assert items[0].stable_id == "section:prehero"
    assert items[0].code == "GH-00"
    assert next(item for item in items if item.stable_id == "section:hero").code == "GH-01"
    assert next(item for item in items if item.stable_id == "section:intro").code == "GH-02"


def test_home_flow_custom_names_are_variant_local_metadata(tmp_path) -> None:
    set_flow_name(
        "home12",
        "section:hero",
        "Hero — Galeria ruchu",
        variants_root=tmp_path,
    )

    items = resolve_flow_items("home12", variants_root=tmp_path)
    hero = next(item for item in items if item.stable_id == "section:hero")
    assert hero.display_name == "Hero — Galeria ruchu"

    path = flow_path("home12", variants_root=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "schema": FLOW_SCHEMA_VERSION,
        "names": {"section:hero": "Hero — Galeria ruchu"},
    }
    assert not (tmp_path / "home12" / "index.json").exists()

    reset_flow_name("home12", "section:hero", variants_root=tmp_path)
    reset_items = resolve_flow_items("home12", variants_root=tmp_path)
    reset_hero = next(item for item in reset_items if item.stable_id == "section:hero")
    assert reset_hero.display_name == reset_hero.default_name


def test_schema_v1_is_migrated_in_memory_without_touching_theme(tmp_path) -> None:
    path = flow_path("home-old", variants_root=tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "names": {"section:intro": "Intro własne"},
            }
        ),
        encoding="utf-8",
    )

    metadata = load_flow_metadata("home-old", variants_root=tmp_path)

    assert metadata == {
        "schema": FLOW_SCHEMA_VERSION,
        "names": {"section:intro": "Intro własne"},
    }
    assert not (tmp_path / "home-old" / "index.json").exists()


def test_name_save_preserves_hf3a_structure_draft(tmp_path) -> None:
    save_flow_metadata(
        "home-draft",
        {
            "names": {},
            STRUCTURE_DRAFT_KEY: {
                "section_order": [
                    "section:prehero",
                    "section:hero",
                    "section:intro",
                    "section:potential",
                    "section:restoration",
                    "section:color-correction",
                    "section:see-difference",
                    "section:notice",
                ],
                "custom_sections": [],
            },
        },
        variants_root=tmp_path,
    )

    set_flow_name(
        "home-draft",
        "section:hero",
        "Hero test",
        variants_root=tmp_path,
    )
    payload = json.loads(
        flow_path("home-draft", variants_root=tmp_path).read_text(encoding="utf-8")
    )

    assert payload["names"] == {"section:hero": "Hero test"}
    assert payload[STRUCTURE_DRAFT_KEY]["section_order"][3] == "section:potential"
