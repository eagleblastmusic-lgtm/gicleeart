from __future__ import annotations

from pathlib import Path

import pytest

from giclee_app import launcher_logs
from tools.repository_safety.runtime_writes import scan_python_source


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    legacy_dir = tmp_path / "repo" / "cursor-api" / "logs"
    external_dir = tmp_path / "local-root" / "logs" / "components"
    monkeypatch.setattr(launcher_logs, "LEGACY_COMPONENT_LOGS_DIR", legacy_dir)
    monkeypatch.setattr(launcher_logs, "DEFAULT_COMPONENT_LOGS_DIR", external_dir)
    return legacy_dir, external_dir


def test_external_log_takes_precedence_for_reads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_dir, external_dir = _configure_paths(monkeypatch, tmp_path)
    legacy_dir.mkdir(parents=True)
    external_dir.mkdir(parents=True)
    (legacy_dir / "dodajobraz.log").write_text("legacy", encoding="utf-8")
    external = external_dir / "dodajobraz.log"
    external.write_text("external", encoding="utf-8")

    result = launcher_logs.component_log_read_path("dodajobraz")

    assert result == external


def test_missing_external_reads_legacy_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_dir, external_dir = _configure_paths(monkeypatch, tmp_path)
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "dodajobraz.log"
    legacy.write_text("legacy", encoding="utf-8")

    result = launcher_logs.component_log_read_path("dodajobraz")

    assert result == legacy
    assert not external_dir.exists()


def test_first_write_seeds_legacy_once_and_preserves_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_dir, external_dir = _configure_paths(monkeypatch, tmp_path)
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "dodajobraz.log"
    legacy.write_text("legacy history\n", encoding="utf-8")
    before = legacy.read_bytes()

    target = launcher_logs.component_log_write_path("dodajobraz")
    with target.open("a", encoding="utf-8") as handle:
        handle.write("new event\n")

    assert target == external_dir / "dodajobraz.log"
    assert target.read_text(encoding="utf-8") == "legacy history\nnew event\n"
    assert legacy.read_bytes() == before
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []

    second = launcher_logs.component_log_write_path("dodajobraz")
    assert second == target
    assert second.read_text(encoding="utf-8") == "legacy history\nnew event\n"


def test_explicit_logs_dir_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "override-logs"

    write_path = launcher_logs.component_log_write_path(
        "produkcja",
        logs_dir=override,
    )
    read_path = launcher_logs.component_log_read_path(
        "produkcja",
        logs_dir=override,
    )

    assert write_path == override / "produkcja.log"
    assert read_path == write_path
    assert override.is_dir()


def test_unsafe_component_folder_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="Unsafe component folder name"):
        launcher_logs.component_log_write_path("../escape")


def test_runtime_write_inventory_no_longer_flags_launcher_logs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        "giclee_app/launcher.py",
        "giclee_app/launcher_delegate.py",
        "giclee_app/launcher_logs.py",
    ]

    for relative in targets:
        source_path = repo_root / relative
        findings, error = scan_python_source(
            relative,
            source_path.read_text(encoding="utf-8"),
        )
        assert error == ""
        assert findings == [], (relative, findings)
