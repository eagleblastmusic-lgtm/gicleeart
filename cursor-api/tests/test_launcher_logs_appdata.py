from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from giclee_app import component_logs
from tools.repository_safety.runtime_writes import scan_python_source


LogPathResolver = Callable[..., Path]


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = tmp_path / "local-root"
    legacy_dir = tmp_path / "repo" / "cursor-api" / "logs"
    external_dir = local_root / "logs" / "components"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(component_logs, "LEGACY_COMPONENT_LOGS_DIR", legacy_dir)
    monkeypatch.setattr(component_logs, "DEFAULT_COMPONENT_LOGS_DIR", external_dir)
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

    result = component_logs.component_log_read_path("dodajobraz")

    assert result == external


def test_missing_external_reads_legacy_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy_dir, external_dir = _configure_paths(monkeypatch, tmp_path)
    legacy_dir.mkdir(parents=True)
    legacy = legacy_dir / "dodajobraz.log"
    legacy.write_text("legacy", encoding="utf-8")

    result = component_logs.component_log_read_path("dodajobraz")

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

    target = component_logs.component_log_write_path("dodajobraz")
    with target.open("a", encoding="utf-8") as handle:
        handle.write("new event\n")

    assert target == external_dir / "dodajobraz.log"
    assert target.read_text(encoding="utf-8") == "legacy history\nnew event\n"
    assert legacy.read_bytes() == before
    assert list(target.parent.glob(f".{target.name}.*.tmp")) == []

    second = component_logs.component_log_write_path("dodajobraz")
    assert second == target
    assert second.read_text(encoding="utf-8") == "legacy history\nnew event\n"


def test_explicit_logs_dir_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "override-logs"

    write_path = component_logs.component_log_write_path(
        "produkcja",
        logs_dir=override,
    )
    read_path = component_logs.component_log_read_path(
        "produkcja",
        logs_dir=override,
    )

    assert write_path == override / "produkcja.log"
    assert read_path == write_path
    assert override.is_dir()


def test_explicit_read_override_has_no_side_effects(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "read-only-logs"

    read_path = component_logs.component_log_read_path(
        "produkcja",
        logs_dir=override,
    )

    assert read_path == override / "produkcja.log"
    assert not override.exists()


@pytest.mark.parametrize(
    "safe_name",
    [
        "dodajobraz",
        "social-media.v2",
        "zażółć_gęślą",
        "  produkcja  ",
    ],
)
def test_safe_component_folder_names_are_portable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    safe_name: str,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "portable-logs"

    result = component_logs.component_log_write_path(
        safe_name,
        logs_dir=override,
    )

    assert result == override / f"{safe_name.strip()}.log"


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "",
        "   ",
        ".",
        "..",
        "../escape",
        "..\\escape",
        "nested/name",
        "nested\\name",
        "/absolute",
        "C:\\absolute",
        "C:relative",
        "bad:name",
        "bad*name",
        "bad?name",
        "bad|name",
        "bad<name",
        "bad>name",
        'bad"name',
        "control\x00name",
        "control\x1fname",
        "trailing.",
        "NUL",
        "con",
        "PRN.txt",
        "aux.data",
        "COM1",
        "com9.log",
        "LPT1",
        "lpt9.txt",
    ],
)
@pytest.mark.parametrize(
    "resolver",
    [
        component_logs.component_log_read_path,
        component_logs.component_log_write_path,
    ],
)
def test_unsafe_component_folder_is_rejected_portably(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    unsafe_name: str,
    resolver: LogPathResolver,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "unsafe-logs"

    with pytest.raises(ValueError, match="Unsafe component folder name"):
        resolver(unsafe_name, logs_dir=override)

    assert not override.exists()


@pytest.mark.parametrize(
    "resolver",
    [
        component_logs.component_log_read_path,
        component_logs.component_log_write_path,
    ],
)
def test_non_string_component_folder_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    resolver: LogPathResolver,
) -> None:
    _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "unsafe-type-logs"

    with pytest.raises(ValueError, match="Unsafe component folder name"):
        resolver(123, logs_dir=override)  # type: ignore[arg-type]

    assert not override.exists()


def test_runtime_write_inventory_no_longer_flags_launcher_logs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        "giclee_app/launcher.py",
        "giclee_app/launcher_delegate.py",
        "giclee_app/component_logs.py",
    ]

    for relative in targets:
        source_path = repo_root / relative
        findings, error = scan_python_source(
            relative,
            source_path.read_text(encoding="utf-8"),
        )
        assert error == ""
        assert findings == [], (relative, findings)
