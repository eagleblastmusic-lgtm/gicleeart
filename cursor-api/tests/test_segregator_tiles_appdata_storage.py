from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.segregatorplikow import storage
from tools.repository_safety.runtime_writes import scan_python_source


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    roaming_root = tmp_path / "roaming-root"
    legacy = (
        tmp_path
        / "repo"
        / "cursor-api"
        / "Komponenty"
        / "segregatorplikow"
        / "data"
        / "tiles.json"
    )
    external = (
        roaming_root
        / "config"
        / "Komponenty"
        / "segregatorplikow"
        / "tiles.json"
    )

    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming_root))
    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy.parent)
    monkeypatch.setattr(storage, "_LEGACY_TILES_FILE", legacy)
    monkeypatch.setattr(storage, "_DEFAULT_TILES_FILE", legacy)
    monkeypatch.setattr(storage, "DATA_DIR", legacy.parent)
    monkeypatch.setattr(storage, "TILES_FILE", legacy)
    return legacy, external


def _payload(name: str) -> dict[str, object]:
    return {
        "version": 1,
        "tiles": [
            {
                "id": "tile-1",
                "name": name,
                "path": r"C:\Obrazy",
                "children": [],
            }
        ],
    }


def test_external_tiles_take_precedence_over_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    external.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_payload("Legacy")), encoding="utf-8")
    external.write_text(json.dumps(_payload("External")), encoding="utf-8")

    loaded = storage.load_tiles()

    assert [tile.name for tile in loaded.tiles] == ["External"]


def test_missing_external_falls_back_to_legacy_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps(_payload("Legacy")), encoding="utf-8")

    loaded = storage.load_tiles()

    assert [tile.name for tile in loaded.tiles] == ["Legacy"]
    assert not external.exists()
    assert not external.parent.exists()


def test_save_is_atomic_external_unicode_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy-tiles", encoding="utf-8")
    before = legacy.read_bytes()
    calls: list[Path] = []
    real_atomic_write = storage.atomic_write_text

    def _record_atomic_write(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        real_atomic_write(path, text, encoding=encoding)

    monkeypatch.setattr(storage, "atomic_write_text", _record_atomic_write)
    store = storage.TileStore(
        version=99,
        tiles=[
            storage.TileEntry(
                id="tile-1",
                name="Malarstwo — zażółć 🖼️",
                path=r"C:\Obrazy",
            )
        ],
    )

    storage.save_tiles(store)

    assert calls == [external]
    assert store.version == storage.CONFIG_VERSION
    saved = json.loads(external.read_text(encoding="utf-8"))
    assert saved["tiles"][0]["name"] == "Malarstwo — zażółć 🖼️"
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_explicit_tiles_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "override" / "custom-tiles.json"
    monkeypatch.setattr(storage, "TILES_FILE", override)
    store = storage.TileStore(
        tiles=[storage.TileEntry(id="tile-1", name="Override", path=r"C:\Cel")]
    )

    storage.save_tiles(store)
    loaded = storage.load_tiles()

    assert override.is_file()
    assert [tile.name for tile in loaded.tiles] == ["Override"]
    assert not external.exists()


def test_missing_or_invalid_tiles_return_empty_store_without_read_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)

    missing = storage.load_tiles()

    assert missing.tiles == []
    assert not external.parent.exists()

    external.parent.mkdir(parents=True)
    external.write_text("{invalid", encoding="utf-8")

    invalid = storage.load_tiles()

    assert invalid.tiles == []


def test_runtime_write_inventory_no_longer_flags_segregator_storage() -> None:
    source_path = Path(storage.__file__)
    findings, error = scan_python_source(
        "Komponenty/segregatorplikow/storage.py",
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
