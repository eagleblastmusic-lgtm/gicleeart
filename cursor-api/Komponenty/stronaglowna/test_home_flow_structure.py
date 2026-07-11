from __future__ import annotations

import json

import pytest

from .home_flow import flow_path, resolve_flow_items
from .home_flow_structure import (
    CORE_SECTION_IDS,
    add_custom_section,
    build_structure_plan,
    format_structure_plan,
    load_structure_draft,
    move_section,
    remove_custom_section,
    reorder_section,
    reset_structure_draft,
    resolve_structure_items,
    save_structure_draft,
    validate_structure_draft,
)


def test_hf3a_default_draft_does_not_change_active_flow(tmp_path) -> None:
    active_before = resolve_flow_items("home1", variants_root=tmp_path)
    draft = load_structure_draft("home1", variants_root=tmp_path)

    assert draft["section_order"] == list(CORE_SECTION_IDS)
    assert draft["custom_sections"] == []
    assert resolve_flow_items("home1", variants_root=tmp_path) == active_before
    assert not (tmp_path / "home1" / "index.json").exists()


def test_move_section_changes_only_draft_order() -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    moved = move_section(draft, "section:potential", -1)

    assert moved["section_order"].index("section:potential") == (
        list(CORE_SECTION_IDS).index("section:potential") - 1
    )
    assert draft["section_order"] == list(CORE_SECTION_IDS)


@pytest.mark.parametrize(
    "stable_id",
    ["section:prehero", "section:hero", "section:intro", "section:notice"],
)
def test_anchor_sections_cannot_be_moved(stable_id) -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    with pytest.raises(ValueError):
        move_section(draft, stable_id, 1)


def test_drag_reorder_rejects_drop_on_anchor() -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    with pytest.raises(ValueError):
        reorder_section(draft, "section:potential", "section:intro")


def test_add_blueprint_is_draft_only_and_is_numbered(tmp_path) -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    draft, stable_id = add_custom_section(
        draft,
        "editorial-image",
        "Materia i detal",
        token="material-detail",
    )
    save_structure_draft("home1", draft, variants_root=tmp_path)
    items = resolve_structure_items("home1", variants_root=tmp_path)

    custom = next(item for item in items if item.stable_id == stable_id)
    assert custom.display_name == "Materia i detal"
    assert custom.code.startswith("GH-")
    assert stable_id == "section:draft:material-detail"
    assert not (tmp_path / "home1" / "index.json").exists()


def test_remove_custom_section_does_not_allow_core_removal() -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    with pytest.raises(ValueError):
        remove_custom_section(draft, "section:potential")


def test_save_and_reset_structure_draft_preserve_names(tmp_path) -> None:
    path = flow_path("home2", variants_root=tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"schema": 1, "names": {"section:hero": "Hero własne"}}),
        encoding="utf-8",
    )
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    draft = move_section(draft, "section:potential", -1)

    save_structure_draft("home2", draft, variants_root=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == 2
    assert payload["names"] == {"section:hero": "Hero własne"}
    assert payload["structure_draft"]["section_order"].index("section:potential") == 4

    reset_structure_draft("home2", variants_root=tmp_path)
    reset_payload = json.loads(path.read_text(encoding="utf-8"))
    assert reset_payload == {"schema": 2, "names": {"section:hero": "Hero własne"}}


def test_plan_reports_writer_boundary(tmp_path) -> None:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    draft, _stable_id = add_custom_section(
        draft,
        "comparison",
        "Przed i po",
        token="before-after",
    )
    plan = build_structure_plan("home3", draft, variants_root=tmp_path)
    text = format_structure_plan(plan)

    assert plan["changed"] is True
    assert plan["ready_for_writer"] is True
    assert plan["writer_available"] is False
    assert "HF-3B" in text
    assert "nie modyfikuje templates/index.json" in text


def test_validation_detects_broken_anchor_order() -> None:
    draft = {
        "section_order": ["section:hero", "section:prehero", *CORE_SECTION_IDS[2:]],
        "custom_sections": [],
    }
    blockers = [
        issue for issue in validate_structure_draft(draft) if issue.severity == "blocker"
    ]
    assert any(issue.code == "LOCKED_PREFIX" for issue in blockers)
