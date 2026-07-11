from __future__ import annotations

import json

from .home_flow import (
    flow_path,
    reset_flow_name,
    resolve_flow_items,
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
        "schema": 1,
        "names": {"section:hero": "Hero — Galeria ruchu"},
    }
    assert not (tmp_path / "home12" / "index.json").exists()

    reset_flow_name("home12", "section:hero", variants_root=tmp_path)
    reset_items = resolve_flow_items("home12", variants_root=tmp_path)
    reset_hero = next(item for item in reset_items if item.stable_id == "section:hero")
    assert reset_hero.display_name == reset_hero.default_name
