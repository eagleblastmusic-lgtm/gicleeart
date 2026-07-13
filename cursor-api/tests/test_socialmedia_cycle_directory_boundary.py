from __future__ import annotations

from pathlib import Path

import pytest

from Komponenty.socialmedia.cykl import storage
from tools.repository_safety.runtime_writes import scan_python_source


def test_data_directory_override_is_dynamic_and_created_only_for_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "legacy"
    first = tmp_path / "override-first"
    second = tmp_path / "override-second"
    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(storage, "_DATA_DIR", first)

    assert storage.data_dir() == first
    assert not first.exists()
    assert storage.data_dir(for_write=True) == first
    assert first.is_dir()

    monkeypatch.setattr(storage, "_DATA_DIR", second)
    assert storage.data_dir(for_write=True) == second
    assert second.is_dir()


def test_images_directory_override_is_dynamic_and_created_only_for_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy = tmp_path / "legacy"
    first = tmp_path / "images-first"
    second = tmp_path / "images-second"
    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy)
    monkeypatch.setattr(storage, "IMAGES_DIR", first)

    assert storage.images_dir() == first
    assert not first.exists()
    assert storage.images_dir(for_write=True) == first
    assert first.is_dir()

    monkeypatch.setattr(storage, "IMAGES_DIR", second)
    assert storage.images_dir(for_write=True) == second
    assert second.is_dir()


def test_directory_boundary_rejects_unknown_constant_name() -> None:
    with pytest.raises(ValueError, match="Unsafe Social Media cycle directory constant"):
        storage._explicit_directory_override("../Obrazy", for_write=True)


def test_runtime_write_inventory_no_longer_flags_cycle_directories() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/socialmedia/cykl/storage.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
