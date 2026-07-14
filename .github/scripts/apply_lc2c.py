from __future__ import annotations

from pathlib import Path

ROOT = Path("cursor-api")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")


grid_path = ROOT / "giclee_app" / "launcher_grid_layout.py"
grid_path.write_text(
    '''"""Czysty kontrakt placementu kafelków klasycznego launchera."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class GridWidget(Protocol):
    """Minimalny kontrakt widgetu akceptującego geometrię grid."""

    def grid(self, **kwargs: object) -> object:
        ...


@dataclass(frozen=True)
class TileGridSpec:
    """Niemutowalna konfiguracja placementu kafelków."""

    columns: int
    row_offset: int = 0
    padx: int = 0
    pady: int = 0
    sticky: str = ""

    def __post_init__(self) -> None:
        if self.columns <= 0:
            raise ValueError("columns must be greater than zero")
        if self.row_offset < 0:
            raise ValueError("row_offset cannot be negative")


@dataclass(frozen=True)
class TileGridSlot:
    """Rozwiązana pozycja i argumenty geometrii jednego kafelka."""

    row: int
    column: int
    padx: int
    pady: int
    sticky: str

    def grid_kwargs(self) -> dict[str, object]:
        return {
            "row": self.row,
            "column": self.column,
            "padx": self.padx,
            "pady": self.pady,
            "sticky": self.sticky,
        }


def resolve_tile_grid_slot(index: int, spec: TileGridSpec) -> TileGridSlot:
    """Oblicza pozycję kafelka bez Tk, I/O i mutacji."""

    if index < 0:
        raise ValueError("index cannot be negative")
    row, column = divmod(index, spec.columns)
    return TileGridSlot(
        row=row + spec.row_offset,
        column=column,
        padx=spec.padx,
        pady=spec.pady,
        sticky=spec.sticky,
    )


def place_tile(
    widget: GridWidget,
    index: int,
    spec: TileGridSpec,
) -> TileGridSlot:
    """Umieszcza widget dokładnie raz i zwraca rozwiązany slot."""

    slot = resolve_tile_grid_slot(index, spec)
    widget.grid(**slot.grid_kwargs())
    return slot
''',
    encoding="utf-8",
)

renderer_path = ROOT / "giclee_app" / "category_renderer.py"
replace_once(
    renderer_path,
    "from .component_loader import Component\n",
    "from .component_loader import Component\n"
    "from .launcher_grid_layout import TileGridSpec, place_tile\n",
)
replace_once(
    renderer_path,
    '''    tile_pad_x: int
    tile_pad_y: int


CategoryTileBuilder''',
    '''    tile_pad_x: int
    tile_pad_y: int

    def tile_grid_spec(self, *, row_offset: int = 1) -> TileGridSpec:
        return TileGridSpec(
            columns=self.columns,
            row_offset=row_offset,
            padx=self.tile_pad_x,
            pady=self.tile_pad_y,
            sticky="",
        )


CategoryTileBuilder''',
)
replace_once(
    renderer_path,
    '''    for index, (title, components) in enumerate(sections):
        row, column = divmod(index, config.columns)
        tile = build_category_tile(parent, title, len(components))
        tile.grid(
            row=row + 1,
            column=column,
            padx=config.tile_pad_x,
            pady=config.tile_pad_y,
            sticky="",
        )
''',
    '''    grid_spec = config.tile_grid_spec(row_offset=1)
    for index, (title, components) in enumerate(sections):
        tile = build_category_tile(parent, title, len(components))
        place_tile(tile, index, grid_spec)
''',
)
replace_once(
    renderer_path,
    '''    for index, component in enumerate(components):
        row, column = divmod(index, config.columns)
        tile = build_component_tile(parent, component)
        tile.grid(
            row=row + 1,
            column=column,
            padx=config.tile_pad_x,
            pady=config.tile_pad_y,
            sticky="",
        )
''',
    '''    grid_spec = config.tile_grid_spec(row_offset=1)
    for index, component in enumerate(components):
        tile = build_component_tile(parent, component)
        place_tile(tile, index, grid_spec)
''',
)


test_path = ROOT / "tests" / "test_launcher_grid_layout.py"
test_path.write_text(
    r'''"""Testy LC-2C: launcher-local placement kafelków."""

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
''',
    encoding="utf-8",
)

launcher_docs = ROOT / "giclee_app" / "docs" / "launcher.md"
replace_once(
    launcher_docs,
    "**LC-2B category renderer:** `category_renderer.py` buduje puste stany, indeks i ekran komponentów przez jawne callbacki. Metody `CategoryGicleeApp` pozostają wrapperami, a Styled i DnD nadal dostarczają własne hooki kafelków.\n",
    "**LC-2B category renderer:** `category_renderer.py` buduje puste stany, indeks i ekran komponentów przez jawne callbacki. Metody `CategoryGicleeApp` pozostają wrapperami, a Styled i DnD nadal dostarczają własne hooki kafelków.\n\n"
    "**LC-2C tile grid placement:** `launcher_grid_layout.py` waliduje i rozwiązuje launcher-local sloty siatki. Oba rendery używają jednego `place_tile()`, zachowując trzy kolumny, row offset, paddingi oraz realne ramki DnD.\n",
)

contract = ROOT / "giclee_app" / "docs" / "launcher-composition-lc2c-contract.md"
replace_once(
    contract,
    "**Status:** fresh reconnaissance · contract freeze  ",
    "**Status:** LC-2C implemented",
)
