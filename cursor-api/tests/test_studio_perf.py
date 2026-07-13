from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio import perf
from tools.repository_safety.runtime_writes import scan_python_source


def _configure_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = tmp_path / "local-root"
    legacy = (
        tmp_path
        / "repo"
        / "cursor-api"
        / "giclee_app"
        / "logs"
        / "studio_perf.log"
    )
    external = local_root / "logs" / "giclee_app" / "studio_perf.log"

    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(perf, "_LEGACY_LOG_PATH", legacy)
    monkeypatch.setattr(perf, "_DEFAULT_LOG_PATH", external)
    monkeypatch.setattr(perf, "_LOG_PATH", external)
    return legacy, external


def test_perf_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_PERF", raising=False)
    assert perf.is_enabled() is False


def test_perf_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    assert perf.is_enabled() is True


def test_perf_disabled_does_not_create_default_log_directories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_PERF", raising=False)
    _legacy, external = _configure_default_paths(monkeypatch, tmp_path)

    perf.log_event("test.disabled", value="x")

    assert not external.exists()
    assert not external.parent.exists()


def test_log_event_disabled_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_PERF", raising=False)
    target = tmp_path / "studio_perf.log"
    monkeypatch.setattr(perf, "_LOG_PATH", target)
    perf.log_event("test.disabled", value="x")
    assert not target.exists()


def test_log_event_enabled_writes_jsonl(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    target = tmp_path / "studio_perf.log"
    monkeypatch.setattr(perf, "_LOG_PATH", target)

    perf.log_event("test.enabled", elapsed_ms=12.345, value="abc")

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event"] == "test.enabled"
    assert row["elapsed_ms"] == 12.35
    assert row["value"] == "abc"


def test_default_log_seeds_legacy_once_and_appends_external(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    legacy, external = _configure_default_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"event": "legacy", "value": "history"}) + "\n",
        encoding="utf-8",
    )
    before = legacy.read_bytes()

    perf.log_event("test.external", value="zażółć 🖼️")

    lines = external.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "legacy"
    row = json.loads(lines[1])
    assert row["event"] == "test.external"
    assert row["value"] == "zażółć 🖼️"
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_span_enabled_writes_elapsed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    target = tmp_path / "studio_perf.log"
    monkeypatch.setattr(perf, "_LOG_PATH", target)

    with perf.span("test.span", area="unit"):
        pass

    row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
    assert row["event"] == "test.span"
    assert "elapsed_ms" in row
    assert row["area"] == "unit"


def test_perf_module_no_komponenty_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "perf.py"
    text = path.read_text(encoding="utf-8")
    assert "Komponenty." not in text


def test_log_event_survives_write_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")

    def _fail() -> Path:
        raise OSError("simulated write failure")

    monkeypatch.setattr(perf, "_write_path", _fail)
    perf.log_event("test.fail")


def test_runtime_write_inventory_no_longer_flags_studio_perf() -> None:
    source_path = Path(perf.__file__)
    findings, error = scan_python_source(
        "giclee_app/studio/perf.py",
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
