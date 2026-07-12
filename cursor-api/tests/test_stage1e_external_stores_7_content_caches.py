from __future__ import annotations

import json
from pathlib import Path

import pytest

from giclee_app.app_paths import cache_path


def _set_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    local = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))
    return local


def _write_json(path: Path, payload: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def test_karuzela_quotes_cache_reads_legacy_and_writes_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.karuzela import quotes_service as service

    local = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-karuzela"
    legacy_file = legacy_dir / "collection_quotes.json"
    legacy_bytes = _write_json(
        legacy_file,
        {"version": 2, "quotes": {"van-gogh": ["legacy"]}, "catalog": []},
    )

    monkeypatch.setattr(service, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(service, "_LEGACY_DATA_FILE", legacy_file)
    monkeypatch.setattr(service, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(service, "_DATA_FILE", legacy_file)
    monkeypatch.setattr(
        service,
        "_CACHE",
        cache_path("Komponenty/karuzela/data/collection_quotes.json", legacy=legacy_file),
    )

    assert service.load_local_cache()["quotes"]["van-gogh"] == ["legacy"]
    service.save_local_cache({"quotes": {"van-gogh": ["external"]}, "catalog": []})

    target = local / "data/Komponenty/karuzela/data/collection_quotes.json"
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["version"] == 2
    assert saved["quotes"]["van-gogh"] == ["external"]
    assert service.load_local_cache()["quotes"]["van-gogh"] == ["external"]
    assert legacy_file.read_bytes() == legacy_bytes


def test_tldobio_cache_reads_legacy_and_writes_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.tldobio import service

    local = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-tldobio"
    legacy_file = legacy_dir / "collections.json"
    legacy_bytes = _write_json(
        legacy_file,
        {"version": 2, "backgrounds": {"van-gogh": {"url": "legacy"}}, "catalog": []},
    )

    monkeypatch.setattr(service, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(service, "_LEGACY_DATA_FILE", legacy_file)
    monkeypatch.setattr(service, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(service, "_DATA_FILE", legacy_file)
    monkeypatch.setattr(
        service,
        "_CACHE",
        cache_path("Komponenty/tldobio/data/collections.json", legacy=legacy_file),
    )

    assert service.load_local_cache()["backgrounds"]["van-gogh"]["url"] == "legacy"
    service.save_local_cache(
        {"backgrounds": {"van-gogh": {"url": "external"}}, "catalog": []}
    )

    target = local / "data/Komponenty/tldobio/data/collections.json"
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert saved["backgrounds"]["van-gogh"]["url"] == "external"
    assert service.load_local_cache()["backgrounds"]["van-gogh"]["url"] == "external"
    assert legacy_file.read_bytes() == legacy_bytes


@pytest.mark.parametrize(
    ("module_name", "file_name", "payload"),
    [
        (
            "Komponenty.karuzela.quotes_service",
            "collection_quotes.json",
            {"quotes": {"x": ["override"]}, "catalog": []},
        ),
        (
            "Komponenty.tldobio.service",
            "collections.json",
            {"backgrounds": {"x": {"url": "override"}}, "catalog": []},
        ),
    ],
)
def test_content_cache_direct_directory_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    module_name: str,
    file_name: str,
    payload: dict,
) -> None:
    import importlib

    module = importlib.import_module(module_name)
    override = tmp_path / "override"
    monkeypatch.setattr(module, "_DATA_DIR", override)
    monkeypatch.setattr(module, "_DATA_FILE", module._LEGACY_DATA_FILE)

    module.save_local_cache(payload)

    target = override / file_name
    assert target.is_file()
    assert module.load_local_cache()["version"] == 2
