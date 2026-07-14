"""Testy LC-2C: launcher-local placement kafelków."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from giclee_app.launcher_grid_layout import (
    TileGridSlot,
    TileGridSpec,
    place_tile,
    resolve_tile_grid_slot,
)


class _GridRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def grid(self, **kwargs: object) -> None:
        self.calls.append(dict(kwargs))


@pytest.mark.parametrize(
    ("index", "expected_row", "expected_column"),
    [
        (0, 1, 0),
        (2, 1, 2),
        (3, 2, 0),
        (5, 2, 2),
    ],
)
def test_resolve_slot_for_three_column_launcher_grid(
    index: int,
    expected_row: int,
    expected_column: int,
) -> None:
    spec = TileGridSpec(
        columns=3,
        row_offset=1,
        padx=6,
        pady=7,
        sticky="",
    )

    slot = resolve_tile_grid_slot(index, spec)

    assert slot == TileGridSlot(
        row=expected_row,
        column=expected_column,
        padx=6,
        pady=7,
        sticky="",
    )
    assert slot.grid_kwargs() == {
        "row": expected_row,
        "column": expected_column,
        "padx": 6,
        "pady": 7,
        "sticky": "",
    }


def test_spec_and_slot_are_immutable() -> None:
    spec = TileGridSpec(columns=3)
    slot = resolve_tile_grid_slot(0, spec)

    with pytest.raises(FrozenInstanceError):
        spec.columns = 4  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        slot.row = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TileGridSpec(columns=0),
        lambda: TileGridSpec(columns=-1),
        lambda: TileGridSpec(columns=3, row_offset=-1),
    ],
)
def test_invalid_spec_is_rejected(factory) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        factory()


def test_negative_index_is_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_tile_grid_slot(-1, TileGridSpec(columns=3))


def test_place_tile_calls_grid_once_and_returns_slot() -> None:
    widget = _GridRecorder()
    spec = TileGridSpec(
        columns=3,
        row_offset=1,
        padx=4,
        pady=5,
        sticky="nsew",
    )

    slot = place_tile(widget, 4, spec)

    assert slot == TileGridSlot(
        row=2,
        column=1,
        padx=4,
        pady=5,
        sticky="nsew",
    )
    assert widget.calls == [slot.grid_kwargs()]


def test_grid_module_has_no_tk_ui_or_component_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "launcher_grid_layout.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    assert not any(name == "tkinter" or name.startswith("tkinter.") for name in imports)
    assert not any(name.startswith("giclee_app.ui") for name in imports)
    assert not any(name.startswith("Komponenty") for name in imports)
    assert "launcher" not in imports
    assert "category_renderer" not in imports


def test_both_category_renderers_use_shared_placement_after_builder() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "category_renderer.py"
    source = path.read_text(encoding="utf-8")
    index_block = source.split("def render_category_index", 1)[1].split(
        "\ndef render_category_components", 1
    )[0]
    components_block = source.split("def render_category_components", 1)[1]

    assert "place_tile(tile, index, grid_spec)" in index_block
    assert "place_tile(tile, index, grid_spec)" in components_block
    assert index_block.index("build_category_tile(") < index_block.index("place_tile(")
    assert components_block.index("build_component_tile(") < components_block.index("place_tile(")
    assert "divmod(index, config.columns)" not in source
    assert source.count("tile_grid_spec(row_offset=1)") == 2
