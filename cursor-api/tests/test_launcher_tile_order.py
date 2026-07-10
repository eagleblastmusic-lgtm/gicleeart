from __future__ import annotations

from giclee_app.launcher_tile_order import reorder_relative, replace_subset_order


def test_reorder_relative_moves_before_target() -> None:
    assert reorder_relative(
        ["a", "b", "c", "d"],
        "d",
        "b",
        after=False,
    ) == ["a", "d", "b", "c"]


def test_reorder_relative_moves_after_target() -> None:
    assert reorder_relative(
        ["a", "b", "c", "d"],
        "a",
        "c",
        after=True,
    ) == ["b", "c", "a", "d"]


def test_reorder_relative_keeps_order_for_same_or_missing_item() -> None:
    original = ["a", "b", "c"]
    assert reorder_relative(original, "b", "b", after=False) == original
    assert reorder_relative(original, "x", "b", after=False) == original
    assert reorder_relative(original, "a", "x", after=True) == original


def test_replace_subset_order_preserves_hidden_slots() -> None:
    assert replace_subset_order(
        ["visible-a", "hidden", "visible-b", "visible-c"],
        ["visible-c", "visible-a", "visible-b"],
    ) == ["visible-c", "hidden", "visible-a", "visible-b"]


def test_replace_subset_order_appends_new_subset_items() -> None:
    assert replace_subset_order(
        ["a", "hidden"],
        ["a", "b"],
    ) == ["a", "hidden", "b"]


def test_helpers_remove_accidental_duplicates() -> None:
    assert reorder_relative(["a", "a", "b"], "a", "b", after=True) == ["b", "a"]
    assert replace_subset_order(["a", "a", "x"], ["a"]) == ["a", "x"]
