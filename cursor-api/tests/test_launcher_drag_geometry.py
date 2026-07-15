"""Testy LC-3D: czysta geometria drag-and-drop launchera."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from giclee_app.launcher_drag_geometry import (
    DragPoint,
    DragRect,
    drag_threshold_reached,
    drop_after,
    nearest_rect_index,
    point_inside,
)


def test_drag_threshold_below_exact_and_above() -> None:
    start = DragPoint(10, 20)
    assert drag_threshold_reached(start, DragPoint(16, 24), 8) is False
    assert drag_threshold_reached(start, DragPoint(18, 20), 8) is True
    assert drag_threshold_reached(start, DragPoint(19, 20), 8) is True


def test_drag_threshold_rejects_negative_value() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        drag_threshold_reached(DragPoint(0, 0), DragPoint(0, 0), -1)


def test_drag_rect_properties() -> None:
    rect = DragRect(left=10, top=20, width=30, height=40)
    assert rect.right == 40
    assert rect.bottom == 60
    assert rect.center_x == 25
    assert rect.center_y == 40


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        (DragPoint(10, 20), True),
        (DragPoint(39.999, 59.999), True),
        (DragPoint(40, 30), False),
        (DragPoint(20, 60), False),
        (DragPoint(9.999, 30), False),
        (DragPoint(20, 19.999), False),
    ],
)
def test_point_inside_preserves_half_open_bounds(
    point: DragPoint,
    expected: bool,
) -> None:
    assert point_inside(DragRect(10, 20, 30, 40), point) is expected


def test_drop_after_uses_vertical_region_then_horizontal_center() -> None:
    rect = DragRect(0, 0, 100, 100)
    assert drop_after(rect, DragPoint(10, 20), vertical_ratio=0.22) is False
    assert drop_after(rect, DragPoint(10, 80), vertical_ratio=0.22) is True
    assert drop_after(rect, DragPoint(49, 50), vertical_ratio=0.22) is False
    assert drop_after(rect, DragPoint(51, 50), vertical_ratio=0.22) is True
    assert drop_after(rect, DragPoint(50, 50), vertical_ratio=0.22) is False


def test_drop_after_preserves_zero_height_floor() -> None:
    rect = DragRect(0, 10, 100, 0)
    assert drop_after(rect, DragPoint(40, 9), vertical_ratio=0.22) is False
    assert drop_after(rect, DragPoint(40, 11), vertical_ratio=0.22) is True


def test_drop_after_rejects_negative_ratio() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        drop_after(DragRect(0, 0, 1, 1), DragPoint(0, 0), vertical_ratio=-0.1)


def test_nearest_rect_returns_index_and_preserves_first_tie() -> None:
    rects = [
        DragRect(0, 0, 10, 10),
        DragRect(20, 0, 10, 10),
        DragRect(40, 0, 10, 10),
    ]
    before = list(rects)
    assert nearest_rect_index(rects, DragPoint(27, 5)) == 1
    assert nearest_rect_index(rects[:2], DragPoint(15, 5)) == 0
    assert nearest_rect_index([], DragPoint(0, 0)) is None
    assert rects == before


def test_geometry_module_has_no_ui_or_application_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_geometry.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert "tkinter" not in imports
    assert not any(name.startswith("giclee_app") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)


def test_motion_source_delegates_threshold_and_keeps_side_effects() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    motion = source.split("def _on_tile_motion", 1)[1].split("\n    def ", 1)[0]
    wrapper = source.split("def _find_drop_target", 1)[1].split("\n    def ", 1)[0]

    assert "drag_threshold_reached(" in motion
    assert "_DRAG_THRESHOLD_PX" in motion
    assert "state.dragging = True" in motion
    assert 'self.root.configure(cursor="fleur")' in motion
    assert "self._auto_scroll_drag(" in motion
    assert "find_drop_target(" in wrapper
    assert "winfo_containing(" not in wrapper
    assert "nearest_rect_index(" not in wrapper


def test_legacy_order_module_remains_separate() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_drag_geometry.py"
    )
    source = path.read_text(encoding="utf-8")
    assert "reorder_relative" not in source
    assert "replace_subset_order" not in source
