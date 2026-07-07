from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio import perf


def test_perf_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_PERF", raising=False)
    assert perf.is_enabled() is False


def test_perf_enabled(monkeypatch) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    assert perf.is_enabled() is True


def test_log_event_disabled_does_not_write(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GICLEE_STUDIO_PERF", raising=False)
    target = tmp_path / "studio_perf.log"
    monkeypatch.setattr(perf, "_LOG_PATH", target)
    perf.log_event("test.disabled", value="x")
    assert not target.exists()


def test_log_event_enabled_writes_jsonl(monkeypatch, tmp_path) -> None:
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


def test_span_enabled_writes_elapsed(monkeypatch, tmp_path) -> None:
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


def test_log_event_survives_write_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GICLEE_STUDIO_PERF", "1")
    bad = tmp_path / "missing_parent" / "studio_perf.log"
    monkeypatch.setattr(perf, "_LOG_PATH", bad)
    perf.log_event("test.fail")
