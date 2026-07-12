from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty._shared import tile_grid


def _set_roaming_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    return roaming


def _component_dir(tmp_path: Path, *relative: str) -> Path:
    component = tmp_path / "repo" / "cursor-api" / "Komponenty"
    for part in relative or ("obrazy",):
        component /= part
    component.mkdir(parents=True)
    return component


def _external_settings(roaming: Path, *relative: str) -> Path:
    path = roaming / "config" / "Komponenty"
    for part in relative or ("obrazy",):
        path /= part
    return path / "settings.json"


def test_external_settings_take_precedence_over_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roaming = _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path)
    legacy = component / "settings.json"
    external = _external_settings(roaming)
    legacy.write_text('{"source": "legacy"}', encoding="utf-8")
    external.parent.mkdir(parents=True)
    external.write_text('{"source": "external"}', encoding="utf-8")

    assert tile_grid.load_settings(component) == {"source": "external"}


def test_missing_external_settings_fall_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path)
    legacy = component / "settings.json"
    legacy.write_text('{"source": "legacy"}', encoding="utf-8")

    assert tile_grid.load_settings(component) == {"source": "legacy"}


def test_missing_or_invalid_settings_return_empty_mapping(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roaming = _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path)
    legacy = component / "settings.json"
    external = _external_settings(roaming)

    assert tile_grid.load_settings(component) == {}

    legacy.write_text('{"source": "legacy"}', encoding="utf-8")
    external.parent.mkdir(parents=True)
    external.write_text("{invalid", encoding="utf-8")
    assert tile_grid.load_settings(component) == {}

    external.unlink()
    legacy.write_text("{invalid", encoding="utf-8")
    assert tile_grid.load_settings(component) == {}


def test_save_is_atomic_external_unicode_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roaming = _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path)
    legacy = component / "settings.json"
    legacy.write_bytes(b'{"source": "legacy"}')
    before = legacy.read_bytes()
    target = _external_settings(roaming)
    calls: list[Path] = []
    real_atomic_write = tile_grid.atomic_write_text

    def _record_atomic_write(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        real_atomic_write(path, text, encoding=encoding)

    monkeypatch.setattr(tile_grid, "atomic_write_text", _record_atomic_write)
    tile_grid.save_settings(
        component,
        {"folder": "Zażółć gęślą jaźń", "emoji": "🖼️"},
    )

    assert calls == [target]
    assert target.parent.is_dir()
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "folder": "Zażółć gęślą jaźń",
        "emoji": "🖼️",
    }
    assert legacy.read_bytes() == before
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []


def test_save_errors_are_not_silently_ignored(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path)

    def _fail_write(_path: Path, _text: str, *, encoding: str = "utf-8") -> None:
        raise OSError("write failed")

    monkeypatch.setattr(tile_grid, "atomic_write_text", _fail_write)

    with pytest.raises(OSError, match="write failed"):
        tile_grid.save_settings(component, {"value": 1})


def test_component_settings_relative_path_is_stable_and_safe(tmp_path: Path) -> None:
    nested = _component_dir(tmp_path, "theme_tools", "editor")
    outside = tmp_path / "standalone-component"
    unsafe = tmp_path / "repo" / "Komponenty" / ".." / "escape"

    assert tile_grid.component_settings_relative_path(nested) == (
        "Komponenty/theme_tools/editor/settings.json"
    )
    assert tile_grid.component_settings_relative_path(outside) == (
        "Komponenty/standalone-component/settings.json"
    )

    unsafe_relative = tile_grid.component_settings_relative_path(unsafe)
    assert unsafe_relative == "Komponenty/escape/settings.json"
    assert ".." not in unsafe_relative
    assert not Path(unsafe_relative).is_absolute()


def test_component_settings_path_targets_roaming_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    roaming = _set_roaming_root(monkeypatch, tmp_path)
    component = _component_dir(tmp_path, "obrazy")
    spec = tile_grid.component_settings_path(component)

    assert spec.legacy_path == component / "settings.json"
    assert spec.write_path == _external_settings(roaming, "obrazy")
