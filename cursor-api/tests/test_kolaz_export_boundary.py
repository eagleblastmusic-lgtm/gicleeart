from __future__ import annotations

from datetime import UTC, datetime as RealDateTime
from pathlib import Path
from typing import Any

import pytest

from Komponenty.kolaz import service
from tools.repository_safety.runtime_writes import scan_python_source


def _directory_snapshot(path: Path) -> tuple[bool, tuple[str, ...]]:
    if not path.is_dir():
        return False, ()
    return True, tuple(sorted(item.name for item in path.iterdir()))


def test_default_exports_directory_is_local_appdata_and_legacy_is_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(service, "_EXPORT_DIR", service._DEFAULT_EXPORT_DIR)

    legacy = Path(service._DEFAULT_EXPORT_DIR)
    before = _directory_snapshot(legacy)

    resolved = service.exports_dir()

    assert resolved == local_root / "data" / "Komponenty" / "kolaz" / "data" / "exports"
    assert resolved.is_dir()
    assert _directory_snapshot(legacy) == before


def test_explicit_export_directory_override_remains_authoritative(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    override = tmp_path / "chosen-exports"
    monkeypatch.setattr(service, "_EXPORT_DIR", override)

    assert service.exports_dir() == override
    assert override.is_dir()


def test_explicit_user_target_is_passed_through_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "user-selected" / "final.png"
    calls: list[tuple[Any, Path, str, int]] = []

    def fake_save(image: Any, path: Path, *, fmt: str, quality: int) -> Path:
        calls.append((image, Path(path), fmt, quality))
        return Path(path)

    monkeypatch.setattr(service, "save_collage", fake_save)
    image = object()

    saved = service.export_collage(image, target, fmt="png", quality=91)

    assert saved == target
    assert calls == [(image, target, "png", 91)]


def test_automatic_export_path_uses_collision_safe_suffix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class FixedDateTime:
        @classmethod
        def now(cls, tz):
            assert tz is UTC
            return RealDateTime(2026, 7, 13, 8, 55, 0, tzinfo=UTC)

    monkeypatch.setattr(service, "datetime", FixedDateTime)
    monkeypatch.setattr(service, "exports_dir", lambda: tmp_path)

    first = service.default_export_path(handle_or_name="Mój Kolaż", fmt="jpeg")
    assert first == tmp_path / "mój-kolaż-20260713-085500.jpg"
    first.write_bytes(b"existing")

    second = service.default_export_path(handle_or_name="Mój Kolaż", fmt="jpeg")
    assert second == tmp_path / "mój-kolaż-20260713-085500-2.jpg"
    assert not second.exists()


def test_runtime_write_inventory_no_longer_flags_kolaz_export_directory() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/kolaz/service.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
