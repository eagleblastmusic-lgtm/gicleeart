"""Czysty kontrakt placementu kafelków klasycznego launchera."""

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
