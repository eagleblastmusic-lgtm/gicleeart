from __future__ import annotations

import json
from pathlib import Path

import pytest

from .home_flow_structure import (
    CORE_SECTION_IDS,
    add_custom_section,
    move_section,
    save_structure_draft,
)
from .home_flow_structure_writer import (
    StructureWriterError,
    apply_structure_draft_to_variant,
    build_writer_plan,
    load_writer_state,
    undo_last_structure_write,
    writer_undo_status,
)
from .service import INDEX_HEADER


MANAGED_KEYS = (
    "slideshow_4LMfx7",
    "section_ThWw4Q",
    "section_XwRNDp",
    "section_bj9cY3",
    "section_p9Kcm6",
    "section_P9LgB3",
)


def _template() -> dict:
    order = [
        "utility-before",
        MANAGED_KEYS[0],
        "divider-a",
        MANAGED_KEYS[1],
        MANAGED_KEYS[2],
        "divider-b",
        MANAGED_KEYS[3],
        MANAGED_KEYS[4],
        MANAGED_KEYS[5],
        "utility-after",
    ]
    return {
        "sections": {
            key: {"type": "section", "settings": {"marker": key}}
            for key in order
        },
        "order": order,
    }


def _write_index(tmp_path, variant_id: str = "home1") -> bytes:
    path = tmp_path / variant_id / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (
        INDEX_HEADER
        + json.dumps(_template(), ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")
    path.write_bytes(raw)
    return raw


def _save_reorder_draft(tmp_path, variant_id: str = "home1") -> dict:
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    draft = move_section(draft, "section:potential", -1)
    save_structure_draft(variant_id, draft, variants_root=tmp_path)
    return draft


def test_writer_plan_replaces_only_managed_slots(tmp_path) -> None:
    _write_index(tmp_path)
    _save_reorder_draft(tmp_path)

    plan = build_writer_plan("home1", variants_root=tmp_path)

    assert plan["ready"] is True
    assert plan["writer_available"] is True
    assert plan["writes_theme"] is False
    source = plan["source_order"]
    target = plan["target_order"]
    unmanaged_positions = [
        index for index, key in enumerate(source) if key not in set(MANAGED_KEYS)
    ]
    assert [target[index] for index in unmanaged_positions] == [
        source[index] for index in unmanaged_positions
    ]
    assert target.index("section_p9Kcm6") < target.index("section_bj9cY3")


def test_writer_creates_exact_backup_and_changes_only_variant(tmp_path) -> None:
    original = _write_index(tmp_path)
    _save_reorder_draft(tmp_path)
    theme_index = tmp_path / "theme" / "templates" / "index.json"
    theme_index.parent.mkdir(parents=True)
    theme_index.write_bytes(b"theme-must-stay")

    result = apply_structure_draft_to_variant("home1", variants_root=tmp_path)

    assert (tmp_path / "home1" / "index.json").read_bytes() != original
    assert Path(result["backup_path"]).read_bytes() == original
    assert theme_index.read_bytes() == b"theme-must-stay"

    state = load_writer_state("home1", variants_root=tmp_path)
    assert state["before_sha256"] == result["before_sha256"]
    assert state["after_sha256"] == result["after_sha256"]
    assert state["undone_at"] == ""
    assert not list((tmp_path / "home1").glob(".*.tmp"))


def test_writer_undo_restores_exact_bytes(tmp_path) -> None:
    original = _write_index(tmp_path)
    _save_reorder_draft(tmp_path)
    apply_structure_draft_to_variant("home1", variants_root=tmp_path)

    assert writer_undo_status("home1", variants_root=tmp_path)["available"] is True
    undo_last_structure_write("home1", variants_root=tmp_path)

    assert (tmp_path / "home1" / "index.json").read_bytes() == original
    assert writer_undo_status("home1", variants_root=tmp_path)["available"] is False


def test_writer_blocks_custom_blueprints_until_hf3c(tmp_path) -> None:
    _write_index(tmp_path)
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    draft, _stable_id = add_custom_section(
        draft,
        "editorial-image",
        "Nowa narracja",
        token="new-story",
    )
    save_structure_draft("home1", draft, variants_root=tmp_path)

    plan = build_writer_plan("home1", variants_root=tmp_path)

    assert plan["ready"] is False
    assert any(
        row["code"] == "BLUEPRINT_RUNTIME_PENDING"
        for row in plan["issues"]
    )
    with pytest.raises(StructureWriterError):
        apply_structure_draft_to_variant("home1", variants_root=tmp_path)


def test_writer_blocks_missing_managed_section(tmp_path) -> None:
    _write_index(tmp_path)
    path = tmp_path / "home1" / "index.json"
    template = _template()
    template["sections"].pop("section_p9Kcm6")
    path.write_text(
        INDEX_HEADER + json.dumps(template, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _save_reorder_draft(tmp_path)

    plan = build_writer_plan("home1", variants_root=tmp_path)

    assert plan["ready"] is False
    assert any(row["code"] == "SECTION_OBJECT_MISSING" for row in plan["issues"])


def test_writer_undo_blocks_after_external_change(tmp_path) -> None:
    _write_index(tmp_path)
    _save_reorder_draft(tmp_path)
    apply_structure_draft_to_variant("home1", variants_root=tmp_path)

    path = tmp_path / "home1" / "index.json"
    path.write_bytes(path.read_bytes() + b"\n")

    status = writer_undo_status("home1", variants_root=tmp_path)
    assert status["available"] is False
    assert "zmienił się" in status["reason"]
    with pytest.raises(StructureWriterError):
        undo_last_structure_write("home1", variants_root=tmp_path)


def test_writer_rejects_stale_preview_hash(tmp_path) -> None:
    _write_index(tmp_path)
    _save_reorder_draft(tmp_path)
    plan = build_writer_plan("home1", variants_root=tmp_path)

    path = tmp_path / "home1" / "index.json"
    path.write_bytes(path.read_bytes() + b"\n")

    with pytest.raises(StructureWriterError, match="Odśwież plan"):
        apply_structure_draft_to_variant(
            "home1",
            variants_root=tmp_path,
            expected_source_sha256=plan["source_sha256"],
        )


def test_writer_noop_is_not_ready(tmp_path) -> None:
    _write_index(tmp_path)
    draft = {"section_order": list(CORE_SECTION_IDS), "custom_sections": []}
    save_structure_draft("home1", draft, variants_root=tmp_path)

    plan = build_writer_plan("home1", variants_root=tmp_path)

    assert plan["ready"] is False
    assert plan["changed"] is False
