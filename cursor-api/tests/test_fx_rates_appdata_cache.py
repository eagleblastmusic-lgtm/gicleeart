from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty._shared import fx_rates
from tools.repository_safety.runtime_writes import scan_python_source


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = tmp_path / "local-root"
    legacy_dir = tmp_path / "repo" / "cursor-api" / "Komponenty" / "_shared" / "data"
    legacy_file = legacy_dir / "fx_cache.json"

    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(fx_rates, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(fx_rates, "_LEGACY_CACHE_FILE", legacy_file)
    monkeypatch.setattr(fx_rates, "_DEFAULT_DATA_DIR", legacy_dir)
    monkeypatch.setattr(fx_rates, "_DEFAULT_CACHE_FILE", legacy_file)
    monkeypatch.setattr(fx_rates, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(fx_rates, "_CACHE_FILE", legacy_file)

    external = (
        local_root
        / "data"
        / "Komponenty"
        / "_shared"
        / "data"
        / "fx_cache.json"
    )
    return legacy_file, external


def test_external_cache_takes_precedence_over_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"EUR": {"rate": 4.1}}', encoding="utf-8")
    external.parent.mkdir(parents=True)
    external.write_text('{"EUR": {"rate": 4.3}}', encoding="utf-8")

    assert fx_rates.load_cache()["EUR"]["rate"] == 4.3


def test_missing_external_cache_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, _external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"EUR": {"rate": 4.2}}', encoding="utf-8")

    assert fx_rates.load_cache()["EUR"]["rate"] == 4.2


def test_invalid_or_non_mapping_cache_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text('{"EUR": {"rate": 4.2}}', encoding="utf-8")

    external.parent.mkdir(parents=True)
    external.write_text("{invalid", encoding="utf-8")
    assert fx_rates.load_cache() == {}

    external.write_text("[1, 2, 3]", encoding="utf-8")
    assert fx_rates.load_cache() == {}


def test_save_is_atomic_external_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_paths(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b'{"source": "legacy"}')
    before = legacy.read_bytes()
    calls: list[Path] = []
    real_atomic_write = fx_rates.atomic_write_text

    def _record_atomic_write(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        real_atomic_write(path, text, encoding=encoding)

    monkeypatch.setattr(fx_rates, "atomic_write_text", _record_atomic_write)

    fx_rates.save_cache(
        {
            "EUR": {
                "rate": 4.35,
                "source": "ręczny 🪙",
                "fetched_at": "2026-07-12T22:00:00",
            }
        }
    )

    assert calls == [external]
    assert json.loads(external.read_text(encoding="utf-8"))["EUR"]["source"] == "ręczny 🪙"
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_cache_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)
    override = tmp_path / "override" / "custom.json"
    monkeypatch.setattr(fx_rates, "_CACHE_FILE", override)

    fx_rates.save_cache({"EUR": {"rate": 4.4}})

    assert json.loads(override.read_text(encoding="utf-8"))["EUR"]["rate"] == 4.4
    assert not external.exists()
    assert fx_rates.load_cache()["EUR"]["rate"] == 4.4


def test_data_dir_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)
    override_dir = tmp_path / "override-data"
    monkeypatch.setattr(fx_rates, "_DATA_DIR", override_dir)

    fx_rates.save_cache({"EUR": {"rate": 4.45}})

    override_file = override_dir / "fx_cache.json"
    assert json.loads(override_file.read_text(encoding="utf-8"))["EUR"]["rate"] == 4.45
    assert not external.exists()


def test_manual_rate_uses_external_cache_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_paths(monkeypatch, tmp_path)

    def _network_must_not_run(_currency: str) -> float:
        raise AssertionError("NBP lookup should not run for a fresh manual rate")

    monkeypatch.setattr(fx_rates, "_fetch_nbp", _network_must_not_run)
    fx_rates.set_manual_rate("EUR", 4.55)

    rate, info = fx_rates.get_rate("eur")
    assert rate == 4.55
    assert info["source"] == "manual"
    assert info["stale"] is False
    assert external.is_file()


def test_runtime_write_inventory_no_longer_flags_fx_rates() -> None:
    source_path = Path(fx_rates.__file__)
    findings, error = scan_python_source(
        "Komponenty/_shared/fx_rates.py",
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
