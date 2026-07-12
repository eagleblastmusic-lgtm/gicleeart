from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from Komponenty.stronyzobrazami.search import fng_local, wikidata_artists
from tools.repository_safety.runtime_writes import scan_python_source


def _local_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "local-root"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(root))
    return root


def _configure_wikidata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = _local_root(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "repo" / "Komponenty" / "stronyzobrazami" / "data" / "cache"
    legacy_file = legacy_dir / "wikidata_artist_aliases.json"

    monkeypatch.setattr(wikidata_artists, "_LEGACY_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(wikidata_artists, "_LEGACY_CACHE_FILE", legacy_file)
    monkeypatch.setattr(wikidata_artists, "_DEFAULT_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(wikidata_artists, "_DEFAULT_CACHE_FILE", legacy_file)
    monkeypatch.setattr(wikidata_artists, "CACHE_DIR", legacy_dir)
    monkeypatch.setattr(wikidata_artists, "CACHE_FILE", legacy_file)
    monkeypatch.setattr(wikidata_artists, "_qid_labels", None)
    monkeypatch.setattr(wikidata_artists, "_query_labels", None)

    external = (
        local_root
        / "data"
        / "Komponenty"
        / "stronyzobrazami"
        / "data"
        / "cache"
        / "wikidata_artist_aliases.json"
    )
    return legacy_file, external


def _configure_fng(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path]:
    local_root = _local_root(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "repo" / "Komponenty" / "stronyzobrazami" / "data" / "cache"
    legacy_file = legacy_dir / "fng_objects.json.gz"

    monkeypatch.setattr(fng_local, "_LEGACY_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(fng_local, "_LEGACY_FNG_OBJECTS_GZ", legacy_file)
    monkeypatch.setattr(fng_local, "_DEFAULT_CACHE_DIR", legacy_dir)
    monkeypatch.setattr(fng_local, "_DEFAULT_FNG_OBJECTS_GZ", legacy_file)
    monkeypatch.setattr(fng_local, "CACHE_DIR", legacy_dir)
    monkeypatch.setattr(fng_local, "FNG_OBJECTS_GZ", legacy_file)
    monkeypatch.setattr(fng_local, "_rows", None)
    monkeypatch.setattr(fng_local, "_artist_index", None)

    external = (
        local_root
        / "data"
        / "Komponenty"
        / "stronyzobrazami"
        / "data"
        / "cache"
        / "fng_objects.json.gz"
    )
    return legacy_file, external


def test_wikidata_external_cache_precedes_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_wikidata(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"qids": {"Q1": ["Legacy"]}, "queries": {}}),
        encoding="utf-8",
    )
    external.parent.mkdir(parents=True)
    external.write_text(
        json.dumps({"qids": {"Q1": ["External"]}, "queries": {}}),
        encoding="utf-8",
    )

    assert wikidata_artists.labels_for_qid("Q1", fetch=False) == ["External"]


def test_wikidata_missing_external_falls_back_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, _external = _configure_wikidata(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"qids": {"Q2": ["Legacy"]}, "queries": {}}),
        encoding="utf-8",
    )

    assert wikidata_artists.labels_for_qid("Q2", fetch=False) == ["Legacy"]


def test_wikidata_save_is_atomic_external_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_wikidata(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b'{"qids":{"Q1":["Legacy"]},"queries":{}}')
    before = legacy.read_bytes()
    calls: list[Path] = []
    real_atomic_write = wikidata_artists.atomic_write_text

    def _record(path: Path, text: str, *, encoding: str = "utf-8") -> None:
        calls.append(path)
        real_atomic_write(path, text, encoding=encoding)

    monkeypatch.setattr(wikidata_artists, "atomic_write_text", _record)
    monkeypatch.setattr(
        wikidata_artists,
        "_qid_labels",
        {"Q1": ["Claude Monet", "Oscar-Claude Monet"]},
    )
    monkeypatch.setattr(wikidata_artists, "_query_labels", {"monet": ["Claude Monet"]})

    wikidata_artists._save_cache()

    assert calls == [external]
    saved = json.loads(external.read_text(encoding="utf-8"))
    assert saved["qids"]["Q1"] == ["Claude Monet", "Oscar-Claude Monet"]
    assert saved["queries"]["monet"] == ["Claude Monet"]
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_wikidata_cache_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_wikidata(monkeypatch, tmp_path)
    override = tmp_path / "override" / "wikidata.json"
    monkeypatch.setattr(wikidata_artists, "CACHE_FILE", override)
    monkeypatch.setattr(wikidata_artists, "_qid_labels", {"Q3": ["Override"]})
    monkeypatch.setattr(wikidata_artists, "_query_labels", {})

    wikidata_artists._save_cache()
    wikidata_artists.reset_cache_for_tests()

    assert wikidata_artists.labels_for_qid("Q3", fetch=False) == ["Override"]
    assert not external.exists()


def test_fng_external_cache_precedes_legacy_for_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_fng(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"L" * 150)
    external.parent.mkdir(parents=True)
    external.write_bytes(b"E" * 200)

    assert fng_local.fng_cache_ready() is True
    assert fng_local._read_cache_file() == external


def test_fng_large_legacy_cache_is_reused_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_fng(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"L" * 1_000_001)

    monkeypatch.setattr(
        fng_local.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("network should not run")
        ),
    )

    assert fng_local.ensure_fng_cache() == legacy
    assert not external.exists()


def test_fng_download_writes_atomic_external_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    legacy, external = _configure_fng(monkeypatch, tmp_path)
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy-small")
    before = legacy.read_bytes()
    payload = json.dumps([{"objectId": "1", "title": {"en": "Work"}}]).encode("utf-8")
    calls: list[Path] = []
    real_atomic_write = fng_local.atomic_write_bytes

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self) -> bytes:
            return payload

    def _record(path: Path, data: bytes) -> None:
        calls.append(path)
        real_atomic_write(path, data)

    monkeypatch.setattr(fng_local, "fng_api_key", lambda: "test-key")
    monkeypatch.setattr(fng_local.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    monkeypatch.setattr(fng_local, "atomic_write_bytes", _record)

    result = fng_local.ensure_fng_cache(timeout=1.0)

    assert result == external
    assert calls == [external]
    with gzip.open(external, "rt", encoding="utf-8") as handle:
        assert json.load(handle)[0]["objectId"] == "1"
    assert legacy.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_fng_cache_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_fng(monkeypatch, tmp_path)
    override = tmp_path / "override" / "fng.json.gz"
    override.parent.mkdir(parents=True)
    override.write_bytes(b"X" * 1_000_001)
    monkeypatch.setattr(fng_local, "FNG_OBJECTS_GZ", override)

    assert fng_local.ensure_fng_cache() == override
    assert not external.exists()


def test_fng_load_rows_reads_external_gzip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _legacy, external = _configure_fng(monkeypatch, tmp_path)
    external.parent.mkdir(parents=True)
    with gzip.open(external, "wt", encoding="utf-8") as handle:
        json.dump([{"objectId": "7"}, "skip"], handle)

    assert fng_local._load_rows() == [{"objectId": "7"}]


@pytest.mark.parametrize(
    ("module", "relative"),
    [
        (
            wikidata_artists,
            "Komponenty/stronyzobrazami/search/wikidata_artists.py",
        ),
        (
            fng_local,
            "Komponenty/stronyzobrazami/search/fng_local.py",
        ),
    ],
)
def test_runtime_write_inventory_no_longer_flags_search_cache(
    module,
    relative: str,
) -> None:
    source_path = Path(module.__file__)
    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
