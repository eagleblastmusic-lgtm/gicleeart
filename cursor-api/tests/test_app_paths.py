from __future__ import annotations

from pathlib import Path

import pytest

from giclee_app.app_paths import (
    AppPath,
    atomic_write_text,
    cache_path,
    config_path,
    data_path,
    local_root,
    roaming_root,
)


def test_external_roots_use_explicit_test_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local = tmp_path / "local-app"
    roaming = tmp_path / "roaming-app"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))

    assert local_root() == local
    assert roaming_root() == roaming
    assert data_path("Komponenty/demo/data/state.json").write_path == (
        local / "data" / "Komponenty" / "demo" / "data" / "state.json"
    )
    assert cache_path("Komponenty/demo/data/cache.json").write_path == (
        local / "data" / "Komponenty" / "demo" / "data" / "cache.json"
    )
    assert config_path("Komponenty/demo/data/settings.json").write_path == (
        roaming / "config" / "Komponenty" / "demo" / "data" / "settings.json"
    )


def test_read_prefers_external_then_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "app"))
    legacy = tmp_path / "repo" / "state.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("legacy", encoding="utf-8")

    spec = data_path("Komponenty/demo/data/state.json", legacy=legacy)
    assert spec.read_path() == legacy

    atomic_write_text(spec.write_path, "external")
    assert spec.read_path() == spec.write_path
    assert spec.write_path.read_text(encoding="utf-8") == "external"
    assert legacy.read_text(encoding="utf-8") == "legacy"


def test_seed_from_legacy_is_copy_only_and_idempotent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "app"))
    legacy = tmp_path / "repo" / "events.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy\n")
    spec = data_path("Komponenty/demo/data/events.jsonl", legacy=legacy)

    target = spec.seed_from_legacy()
    assert target.read_bytes() == b"legacy\n"
    assert legacy.read_bytes() == b"legacy\n"

    legacy.write_bytes(b"changed legacy\n")
    assert spec.seed_from_legacy().read_bytes() == b"legacy\n"


def test_first_run_without_external_or_legacy_returns_external_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "app"))
    spec = data_path("Komponenty/demo/data/new.json", legacy=tmp_path / "missing.json")

    assert spec.read_path() == spec.write_path
    assert not spec.write_path.exists()

    target = spec.ensure_parent()
    assert target == spec.write_path
    assert target.parent.is_dir()


def test_atomic_write_replaces_content_and_leaves_no_temp_file(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "state.json"
    atomic_write_text(target, "one")
    atomic_write_text(target, "two")

    assert target.read_text(encoding="utf-8") == "two"
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []


@pytest.mark.parametrize("relative", ["", ".", "../secret", "a/../../secret"])
def test_unsafe_relative_paths_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    relative: str,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "app"))
    spec = AppPath(relative=relative, bucket="data")

    with pytest.raises(ValueError):
        _ = spec.write_path
