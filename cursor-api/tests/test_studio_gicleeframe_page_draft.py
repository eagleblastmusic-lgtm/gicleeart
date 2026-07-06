"""Testy GICLÉE FRAME™ F2/F2.1 RAM page draft — merge z inventory."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_page_draft import (
    DEFAULT_VARIANT_NAME,
    DRAFT_RAM_DISCLAIMER,
    ElementDraftPatch,
    GicleeFramePageDraft,
    VARIANT_ENV_DEV,
    VARIANT_ENV_LIVE,
    VARIANT_COMPARE_NOTE,
    editor_context_rows,
    editor_field_visibility,
    editor_title_for_element,
    merge_inventory_with_draft,
    page_blocks,
    reorder_page_blocks,
    merged_in_page_order,
    patch_changed_fields,
    section_dropdown_options,
    section_tree_rows,
    status_pill_label,
    working_variant_menu_label,
)
from giclee_app.studio.gicleeframe_page_inventory import (
    build_gicleeframe_page_inventory,
    variant_environment_tag,
)

_DRAFT_MODULE = (
    Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "gicleeframe_page_draft.py"
)


def test_working_variant_menu_label_includes_env_tag() -> None:
    draft = GicleeFramePageDraft()
    assert working_variant_menu_label(draft.active_variant()) == "Wariant 1 (dev)"
    live_variant = draft.add_variant(env_tag=VARIANT_ENV_LIVE)
    assert working_variant_menu_label(live_variant) == f"{live_variant.name} (live)"


def test_variant_environment_tag_active_is_dev_even_when_also_live() -> None:
    assert (
        variant_environment_tag("gf1", active_id="gf1", live_id="gf1") == VARIANT_ENV_DEV
    )
    assert (
        variant_environment_tag("gf1", active_id="gf2", live_id="gf1") == VARIANT_ENV_LIVE
    )
    assert (
        variant_environment_tag("gf2", active_id="gf2", live_id="gf1") == VARIANT_ENV_DEV
    )


def test_divider_inventory_includes_page_settings() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    divider = next(el for el in inv.elements if el.element_type == "divider")
    labels = [field.label for field in divider.page_settings]
    assert "Grubość linii" in labels
    assert "Schemat kolorów" in labels
    thickness = next(f for f in divider.page_settings if f.key == "thickness")
    assert thickness.control == "select"
    assert "0.5" in thickness.options


def test_divider_settings_ram_patch() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    divider = next(el for el in inv.elements if el.element_type == "divider")
    draft = GicleeFramePageDraft()
    draft.set_patch(divider.element_id, settings={"thickness": "2"})
    merged = merge_inventory_with_draft(inv, draft)
    m = next(x for x in merged if x.element_id == divider.element_id)
    thickness = next(f for f in m.page_settings if f.key == "thickness")
    assert thickness.value == "2"
    assert m.has_draft_patch is True


def test_editor_field_visibility_per_type() -> None:
    div = editor_field_visibility("divider")
    assert div.page_context is True
    assert div.title is False
    assert div.visible is True
    jumbo = editor_field_visibility("jumbo")
    assert jumbo.title is True
    assert jumbo.text is False
    body = editor_field_visibility("body")
    assert body.text is True
    image = editor_field_visibility("image")
    assert image.image_ref is True
    media = editor_field_visibility("media_section")
    assert media.children is True
    assert media.title is False


def test_editor_context_rows_for_divider() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    divider = next(el for el in inv.elements if el.element_type == "divider")
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    m = next(x for x in merged if x.element_id == divider.element_id)
    rows = dict(editor_context_rows(m))
    assert "Etykieta" in rows
    thickness = next(f for f in m.page_settings if f.key == "thickness")
    assert thickness.value == "0.5"


def test_draft_empty_merge_matches_inventory() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    merged = merge_inventory_with_draft(inv, draft)
    assert len(merged) == len(inv.elements)
    assert not any(m.has_draft_patch for m in merged)


def test_draft_patch_marks_element_edited() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    target = inv.elements[0]
    draft = GicleeFramePageDraft()
    draft.set_patch(target.element_id, title="RAM tytuł", status="draft_edited")
    merged = merge_inventory_with_draft(inv, draft)
    patched = next(m for m in merged if m.element_id == target.element_id)
    assert patched.title == "RAM tytuł"
    assert patched.has_draft_patch is True
    assert patched.source == "ram_draft"


def test_draft_clear_resets_patches() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("x::y", notes="test")
    assert not draft.is_empty()
    draft.clear()
    assert draft.is_empty()


def test_draft_edit_count() -> None:
    draft = GicleeFramePageDraft()
    assert draft.draft_edit_count() == 0
    draft.set_patch("a::b", title="x")
    draft.set_patch("c::d", alt="y")
    assert draft.draft_edit_count() == 2


def test_default_working_variant_is_wariant_1() -> None:
    draft = GicleeFramePageDraft()
    assert draft.draft_name == DEFAULT_VARIANT_NAME
    assert len(draft.variants) == 1
    assert draft.active_variant_id == "ram_v1"


def test_draft_name_rename_and_add_variant_ram_only() -> None:
    draft = GicleeFramePageDraft()
    assert draft.draft_name == DEFAULT_VARIANT_NAME
    draft.rename_active_variant("Mój test")
    assert draft.draft_name == "Mój test"
    draft.set_patch("x::y", notes="z")
    draft.add_variant()
    assert draft.is_empty()
    assert draft.draft_name == "Wariant 2"
    assert len(draft.variants) == 2


def test_add_variant_creates_empty_variant() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("a::b", title="x")
    draft.add_variant("Wariant test")
    assert draft.draft_name == "Wariant test"
    assert draft.is_empty()
    assert draft.draft_edit_count() == 0


def test_duplicate_active_variant_copies_patches() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("a::b", title="oryginał")
    draft.duplicate_active_variant("Kopia")
    assert draft.draft_name == "Kopia"
    assert draft.draft_edit_count() == 1
    patch = draft.patches["a::b"]
    assert patch.title == "oryginał"


def test_switch_variant_isolates_patches() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("a::b", title="w1")
    v1_id = draft.active_variant_id
    draft.add_variant("Wariant 2")
    draft.set_patch("c::d", alt="w2")
    v2_id = draft.active_variant_id
    draft.switch_variant(v1_id)
    assert draft.draft_edit_count() == 1
    assert "a::b" in draft.patches
    draft.switch_variant(v2_id)
    assert draft.draft_edit_count() == 1
    assert "c::d" in draft.patches


def test_clear_only_active_variant() -> None:
    draft = GicleeFramePageDraft()
    draft.set_patch("a::b", title="w1")
    v1_id = draft.active_variant_id
    draft.add_variant()
    draft.set_patch("c::d", alt="w2")
    draft.clear()
    assert draft.is_empty()
    draft.switch_variant(v1_id)
    assert draft.draft_edit_count() == 1


def test_patch_changed_fields() -> None:
    patch = ElementDraftPatch(title="a", alt="b", visible=False)
    fields = patch_changed_fields(patch)
    assert "tekst" in fields
    assert "alt" in fields
    assert "visible" in fields


def test_status_pill_label() -> None:
    assert status_pill_label("ok") == "OK"
    assert status_pill_label("needs_review") == "do sprawdzenia"
    assert status_pill_label("legacy_disabled") == "legacy"
    assert status_pill_label("ok", has_draft_patch=True) == "draft"


def test_merged_in_page_order_sorted() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    ordered = merged_in_page_order(merged)
    orders = [m.order for m in ordered]
    assert orders == sorted(orders)


def test_draft_disclaimer_copy() -> None:
    assert "lokalnym draftem" in DRAFT_RAM_DISCLAIMER.lower()
    assert "nic nie zapisano" in DRAFT_RAM_DISCLAIMER.lower()


def test_draft_module_zero_io() -> None:
    text = _DRAFT_MODULE.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_section_tree_page_order_not_flat() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    tree = section_tree_rows(merged)
    assert len(tree) < len(merged)
    assert len(tree) == inv.source_section_count


def test_media_section_has_heading_text_image_children() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    tree = section_tree_rows(merged)
    media_rows = [r for r in tree if r.row_kind == "media_section"]
    assert media_rows, "expected at least one media section in tree"
    first = media_rows[0]
    child_labels = [c.child_label for c in first.children]
    assert child_labels == ["Nagłówek", "Tekst", "Grafika"]
    child_types = [c.element_type for c in first.children]
    assert child_types == ["jumbo", "body", "image"]


def test_dividers_are_top_level_tree_rows() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    tree = section_tree_rows(merged)
    dividers = [r for r in tree if r.row_kind == "divider"]
    assert dividers
    assert all(r.display_title == "Separator" for r in dividers)
    assert all(not r.children for r in dividers)


def test_section_dropdown_top_level_only() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    options = section_dropdown_options(merged)
    tree = section_tree_rows(merged)
    assert len(options) == len(tree)
    labels = [o.display_label for o in options]
    assert not any("[" in label for label in labels)
    divider_labels = [label for label in labels if label.startswith("Separator ")]
    assert divider_labels, "expected numbered separators in dropdown"
    assert divider_labels[0] == "Separator 1"
    for index, label in enumerate(divider_labels, start=1):
        assert label == f"Separator {index}"
    assert any(label.startswith("Sekcja:") for label in labels)


def test_reorder_page_blocks_updates_ram_order() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    merged = merge_inventory_with_draft(inv, draft)
    blocks_before = page_blocks(merged)
    assert len(blocks_before) >= 2
    assert reorder_page_blocks(draft, merged, 0, 1)
    merged_after = merge_inventory_with_draft(inv, draft)
    blocks_after = page_blocks(merged_after)
    assert blocks_after[0] == blocks_before[1]
    assert blocks_after[1] == blocks_before[0]


def test_child_selection_uses_element_id_for_ram_patch() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    draft = GicleeFramePageDraft()
    tree = section_tree_rows(merge_inventory_with_draft(inv, draft))
    media = next(r for r in tree if r.row_kind == "media_section")
    body_child = next(c for c in media.children if c.element_type == "body")
    draft.set_patch(body_child.element_id, text="RAM body")
    merged = merge_inventory_with_draft(inv, draft)
    patched = next(m for m in merged if m.element_id == body_child.element_id)
    assert patched.text == "RAM body"
    assert patched.has_draft_patch is True


def test_editor_title_for_child_types() -> None:
    inv = build_gicleeframe_page_inventory(find_components_dir())
    merged = merge_inventory_with_draft(inv, GicleeFramePageDraft())
    by_type = {m.element_type: m for m in merged}
    assert editor_title_for_element(by_type["jumbo"]) == "Edytor: Nagłówek"
    assert editor_title_for_element(by_type["body"]) == "Edytor: Tekst"
    assert editor_title_for_element(by_type["image"]) == "Edytor: Grafika"
    divider = next(m for m in merged if m.element_type == "divider")
    assert editor_title_for_element(divider) == "Edytor: Separator"
