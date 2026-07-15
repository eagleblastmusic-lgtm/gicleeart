"""Testy LC-3G: odczytowy adapter Tk do wyszukiwania celu drag-and-drop."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import tkinter as tk

from giclee_app import dragdrop_category_launcher as dnd
from giclee_app import launcher_tk_drag_targets as targets
from giclee_app.launcher_drag_geometry import DragPoint, DragRect


class FakeWidget:
    def __init__(
        self,
        *,
        left: int,
        top: int,
        width: int,
        height: int,
        exists: bool = True,
        kind: str = "component",
        key: str = "item",
        master: object | None = None,
        is_frame: bool = True,
    ) -> None:
        self._left = left
        self._top = top
        self._width = width
        self._height = height
        self._exists = exists
        self._launcher_dnd_kind = kind
        self._launcher_dnd_key = key
        self.master = master
        self._is_frame = is_frame
        self.configure_calls: list[object] = []

    def winfo_rootx(self) -> int:
        return self._left

    def winfo_rooty(self) -> int:
        return self._top

    def winfo_width(self) -> int:
        return self._width

    def winfo_height(self) -> int:
        return self._height

    def winfo_exists(self) -> bool:
        return self._exists

    def configure(self, **kwargs: object) -> None:
        self.configure_calls.append(kwargs)


class BrokenWidget(FakeWidget):
    def winfo_rootx(self) -> int:
        raise targets.tk.TclError("gone")


class ExistsBrokenWidget(FakeWidget):
    def winfo_exists(self) -> bool:
        raise targets.tk.TclError("gone")


class MasterAttributeErrorWidget:
    @property
    def master(self) -> object:
        raise AttributeError("no master")


class MasterTclErrorWidget:
    @property
    def master(self) -> object:
        raise targets.tk.TclError("master gone")


class TaggedNonFrame(FakeWidget):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(is_frame=False, **kwargs)  # type: ignore[arg-type]


def _area_and_tiles(
    *,
    tiles: list[FakeWidget],
    area: FakeWidget | None = None,
) -> tuple[FakeWidget, list[FakeWidget]]:
    canvas = area or FakeWidget(left=0, top=0, width=100, height=100)
    return canvas, tiles


def test_source_containment_returns_none_before_winfo_containing() -> None:
    source = FakeWidget(left=0, top=0, width=20, height=20, key="source")
    root = SimpleNamespace(
        winfo_containing=lambda _x, _y: (_ for _ in ()).throw(
            AssertionError("winfo_containing must not run")
        )
    )
    canvas, tiles = _area_and_tiles(tiles=[source])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(5, 5),
            exclude=source,
        )
        is None
    )


def test_direct_lookup_from_child_returns_root_tile_via_master() -> None:
    tk_root = tk.Tk()
    tk_root.withdraw()
    try:
        tile = tk.Frame(tk_root)
        setattr(tile, "_launcher_dnd_kind", "component")
        child = SimpleNamespace(master=tile)
        root = SimpleNamespace(winfo_containing=lambda _x, _y: child)
        canvas, tiles = _area_and_tiles(tiles=[tile])  # type: ignore[list-item]
        assert (
            targets.find_drop_target(
                root,
                tiles_area=canvas,
                tiles=tiles,  # type: ignore[arg-type]
                drag_kind="component",
                point=DragPoint(13, 13),
                exclude=FakeWidget(left=0, top=0, width=1, height=1, key="other"),
            )
            is tile
        )
    finally:
        tk_root.destroy()


def test_exclude_is_never_returned() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: source)
    canvas, tiles = _area_and_tiles(tiles=[source])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(50, 50),
            exclude=source,
        )
        is None
    )


def test_different_drag_kind_is_not_returned() -> None:
    tile = FakeWidget(left=0, top=0, width=10, height=10, kind="category", key="cat")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: tile)
    canvas, tiles = _area_and_tiles(tiles=[tile])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(5, 5),
            exclude=FakeWidget(left=50, top=50, width=1, height=1, key="other"),
        )
        is None
    )


def test_matching_tagged_non_frame_returns_none() -> None:
    tagged = TaggedNonFrame(left=0, top=0, width=10, height=10, key="tagged")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: tagged)
    canvas, tiles = _area_and_tiles(tiles=[])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(5, 5),
            exclude=FakeWidget(left=50, top=50, width=1, height=1, key="other"),
        )
        is None
    )


def test_winfo_containing_tcl_error_falls_back_to_nearest() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")

    def raise_tcl(_x: int, _y: int) -> object:
        raise targets.tk.TclError("no widget")

    root = SimpleNamespace(winfo_containing=raise_tcl)
    canvas, tiles = _area_and_tiles(tiles=[source, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(31, 5),
            exclude=source,
        )
        is first
    )


def test_traversal_attribute_error_allows_fallback() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: MasterAttributeErrorWidget())
    canvas, tiles = _area_and_tiles(tiles=[source, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(31, 5),
            exclude=source,
        )
        is first
    )


def test_traversal_tcl_error_allows_fallback() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: MasterTclErrorWidget())
    canvas, tiles = _area_and_tiles(tiles=[source, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(31, 5),
            exclude=source,
        )
        is first
    )


def test_point_outside_tiles_area_blocks_fallback() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas = FakeWidget(left=0, top=0, width=30, height=30)
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=[source, first],
            drag_kind="component",
            point=DragPoint(50, 50),
            exclude=source,
        )
        is None
    )


def test_dead_tiles_are_skipped() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    dead = FakeWidget(left=20, top=0, width=10, height=10, exists=False, key="dead")
    first = FakeWidget(left=40, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, dead, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(41, 5),
            exclude=source,
        )
        is first
    )


def test_winfo_exists_tcl_error_is_skipped() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    broken = ExistsBrokenWidget(left=20, top=0, width=10, height=10, key="broken")
    first = FakeWidget(left=40, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, broken, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(41, 5),
            exclude=source,
        )
        is first
    )


def test_tiles_with_bad_geometry_are_skipped() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    broken = BrokenWidget(left=0, top=0, width=10, height=10, key="broken")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, broken, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(31, 5),
            exclude=source,
        )
        is first
    )


def test_other_kind_tiles_are_skipped() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    category = FakeWidget(left=20, top=0, width=10, height=10, kind="category", key="cat")
    first = FakeWidget(left=40, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, category, first])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(41, 5),
            exclude=source,
        )
        is first
    )


def test_candidate_order_and_first_tie_semantics_are_preserved() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    second = FakeWidget(left=40, top=0, width=10, height=10, key="second")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, first, second])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(31, 5),
            exclude=source,
        )
        is first
    )
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(15, 5),
            exclude=source,
        )
        is first
    )


def test_empty_candidate_list_returns_none() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source])
    assert (
        targets.find_drop_target(
            root,
            tiles_area=canvas,
            tiles=tiles,
            drag_kind="component",
            point=DragPoint(50, 50),
            exclude=source,
        )
        is None
    )


def test_widget_drag_rect_preserves_exact_values() -> None:
    widget = FakeWidget(left=10, top=20, width=30, height=40)
    assert targets.widget_drag_rect(widget) == DragRect(10, 20, 30, 40)


def test_widget_drag_rect_returns_none_on_tcl_error() -> None:
    assert targets.widget_drag_rect(BrokenWidget(left=0, top=0, width=1, height=1)) is None


def test_adapter_does_not_mutate_tiles() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    tiles = [source, first]
    before = list(tiles)
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, _ = _area_and_tiles(tiles=tiles)
    targets.find_drop_target(
        root,
        tiles_area=canvas,
        tiles=tiles,
        drag_kind="component",
        point=DragPoint(25, 5),
        exclude=source,
    )
    assert tiles == before


def test_adapter_does_not_configure_widgets() -> None:
    source = FakeWidget(left=0, top=0, width=10, height=10, key="source")
    first = FakeWidget(left=20, top=0, width=10, height=10, key="first")
    root = SimpleNamespace(winfo_containing=lambda _x, _y: None)
    canvas, tiles = _area_and_tiles(tiles=[source, first])
    targets.find_drop_target(
        root,
        tiles_area=canvas,
        tiles=tiles,
        drag_kind="component",
        point=DragPoint(25, 5),
        exclude=source,
    )
    assert source.configure_calls == []
    assert first.configure_calls == []
    assert canvas.configure_calls == []


def test_adapter_has_no_application_imports() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "launcher_tk_drag_targets.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name.startswith("giclee_app.dragdrop") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)
    assert "giclee_app.launcher_layout" not in imports


def test_launcher_wrapper_delegates_to_find_drop_target() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    wrapper = source.split("def _find_drop_target", 1)[1].split("\n    def ", 1)[0]
    assert "find_drop_target(" in wrapper
    assert "self.root" in wrapper
    assert "tiles_area=self.canvas" in wrapper
    assert "tiles=self._dnd_tiles" in wrapper
    assert "drag_kind=kind" in wrapper
    assert "exclude=exclude" in wrapper
    assert "winfo_containing(" not in wrapper
    assert "nearest_rect_index(" not in wrapper


def test_drop_after_still_uses_ratio_and_lc3d() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "giclee_app"
        / "dragdrop_category_launcher.py"
    )
    source = path.read_text(encoding="utf-8")
    drop_after_block = source.split("def _drop_after", 1)[1].split("\n    @staticmethod", 1)[0]
    assert "widget_drag_rect(" in drop_after_block
    assert "drop_after(" in drop_after_block
    assert "_DROP_VERTICAL_RATIO" in drop_after_block

    widget = FakeWidget(left=0, top=0, width=100, height=100)
    assert dnd.DragDropCategoryGicleeApp._drop_after(widget, 51, 50) is True
