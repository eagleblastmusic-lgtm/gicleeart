"""Trwaly zapis konfiguracji kafelkow w JSON."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
TILES_FILE = DATA_DIR / "tiles.json"
CONFIG_VERSION = 1


@dataclass
class TileEntry:
    id: str
    name: str
    path: str
    children: list[TileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "path": self.path,
        }
        if self.children:
            row["children"] = [c.to_dict() for c in self.children]
        else:
            row["children"] = []
        return row

    @classmethod
    def from_dict(cls, row: dict[str, Any], *, allow_children: bool = True) -> TileEntry:
        children: list[TileEntry] = []
        if allow_children:
            for child in row.get("children") or []:
                if isinstance(child, dict):
                    children.append(cls.from_dict(child, allow_children=False))
        return cls(
            id=str(row.get("id") or new_tile_id()),
            name=str(row.get("name") or "").strip(),
            path=str(row.get("path") or "").strip(),
            children=children,
        )


@dataclass
class TileStore:
    version: int = CONFIG_VERSION
    tiles: list[TileEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "tiles": [t.to_dict() for t in self.tiles],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TileStore:
        tiles: list[TileEntry] = []
        for row in data.get("tiles") or []:
            if isinstance(row, dict):
                tiles.append(TileEntry.from_dict(row, allow_children=True))
        version = int(data.get("version") or CONFIG_VERSION)
        return cls(version=version, tiles=tiles)

    def find(self, tile_id: str) -> TileEntry | None:
        for tile in self.tiles:
            if tile.id == tile_id:
                return tile
            for child in tile.children:
                if child.id == tile_id:
                    return child
        return None

    def find_parent(self, tile_id: str) -> TileEntry | None:
        for tile in self.tiles:
            for child in tile.children:
                if child.id == tile_id:
                    return tile
        return None

    def is_parent(self, tile_id: str) -> bool:
        return any(t.id == tile_id for t in self.tiles)

    def all_tiles_flat(self) -> list[tuple[TileEntry, bool]]:
        """Zwraca (tile, is_child) dla wszystkich kafelkow."""
        out: list[tuple[TileEntry, bool]] = []
        for tile in self.tiles:
            out.append((tile, False))
            for child in tile.children:
                out.append((child, True))
        return out


def new_tile_id() -> str:
    return uuid.uuid4().hex[:12]


def load_tiles() -> TileStore:
    """Wczytuje konfigurację z tiles.json lub zwraca pusty store (bez crasha).

    Plik tiles.json jest lokalny (gitignore); przy pierwszym zapisie tworzy się automatycznie.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TILES_FILE.is_file():
        return TileStore()
    try:
        data = json.loads(TILES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return TileStore.from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return TileStore()


def save_tiles(store: TileStore) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    store.version = CONFIG_VERSION
    TILES_FILE.write_text(
        json.dumps(store.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_path(path: str) -> str:
    text = (path or "").strip()
    if not text:
        return ""
    try:
        return str(Path(text).resolve())
    except OSError:
        return text
