from __future__ import annotations

from pathlib import Path

import pytest

from Komponenty.kpir import storage
from Komponenty.kpir.models import ChangeLogEntry, KpirSettings
from tools.repository_safety.runtime_writes import scan_python_source


def _snapshot(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _reset_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage, "_DATA_DIR", storage._LEGACY_DATA_DIR)
    monkeypatch.setattr(storage, "_SETTINGS_FILE", storage._DEFAULT_SETTINGS_FILE)
    monkeypatch.setattr(storage, "_DB_FILE", storage._DEFAULT_DB_FILE)
    monkeypatch.setattr(storage, "_CHANGELOG_FILE", storage._DEFAULT_CHANGELOG_FILE)


def test_named_store_resolvers_keep_default_writes_outside_checkout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    roaming_root = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming_root))
    _reset_aliases(monkeypatch)

    assert storage._write_store_path("db") == (
        local_root / "data" / "Komponenty" / "kpir" / "dane" / "kpir.json"
    )
    assert storage._write_store_path("settings") == (
        roaming_root
        / "config"
        / "Komponenty"
        / "kpir"
        / "dane"
        / "kpir_settings.json"
    )
    assert storage._write_store_path("changelog") == (
        local_root
        / "data"
        / "Komponenty"
        / "kpir"
        / "dane"
        / "kpir_changelog.jsonl"
    )


def test_direct_file_override_wins_over_shared_data_dir_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data_override = tmp_path / "shared-data"
    direct_db = tmp_path / "direct" / "kpir.json"
    monkeypatch.setattr(storage, "_DATA_DIR", data_override)
    monkeypatch.setattr(storage, "_DB_FILE", direct_db)
    monkeypatch.setattr(storage, "_SETTINGS_FILE", storage._DEFAULT_SETTINGS_FILE)
    monkeypatch.setattr(storage, "_CHANGELOG_FILE", storage._DEFAULT_CHANGELOG_FILE)

    assert storage._write_store_path("db") == direct_db
    assert storage._write_store_path("settings") == data_override / "kpir_settings.json"
    assert storage._write_store_path("changelog") == data_override / "kpir_changelog.jsonl"


def test_roundtrip_uses_named_boundaries_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root = tmp_path / "local"
    roaming_root = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming_root))
    _reset_aliases(monkeypatch)

    legacy_db = storage._DEFAULT_DB_FILE
    legacy_settings = storage._DEFAULT_SETTINGS_FILE
    legacy_changelog = storage._DEFAULT_CHANGELOG_FILE
    before_db = _snapshot(legacy_db)
    before_settings = _snapshot(legacy_settings)
    before_changelog = _snapshot(legacy_changelog)

    storage.save_db({"next_entry_id": 7, "entries": [], "costs": []})
    storage.save_settings(KpirSettings(seller_name="Resolver clarity"))
    storage.append_changelog(
        ChangeLogEntry(
            id="resolver-1",
            entry_id="KPIR-RESOLVER",
            field_name="description",
            old_value="old",
            new_value="new",
            changed_at="2026-07-13T00:00:00",
        )
    )

    assert storage.load_db()["next_entry_id"] == 7
    assert storage.load_settings().seller_name == "Resolver clarity"
    assert storage.list_changelog_for_entry("KPIR-RESOLVER")[0].new_value == "new"
    assert _snapshot(legacy_db) == before_db
    assert _snapshot(legacy_settings) == before_settings
    assert _snapshot(legacy_changelog) == before_changelog


def test_shared_data_dir_override_contract_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    data = tmp_path / "dane"
    docs = tmp_path / "documents"
    monkeypatch.setattr(storage, "_DATA_DIR", data)
    monkeypatch.setattr(storage, "_DOCUMENTS_DIR", docs)
    monkeypatch.setattr(storage, "_SETTINGS_FILE", storage._DEFAULT_SETTINGS_FILE)
    monkeypatch.setattr(storage, "_DB_FILE", storage._DEFAULT_DB_FILE)
    monkeypatch.setattr(storage, "_CHANGELOG_FILE", storage._DEFAULT_CHANGELOG_FILE)

    storage.save_db({"next_entry_id": 3, "entries": []})
    storage.save_settings(KpirSettings(seller_name="Shared override"))
    storage.ensure_dirs()

    assert (data / "kpir.json").is_file()
    assert (data / "kpir_settings.json").is_file()
    assert storage.documents_dir_for("exports", 2026, 7) == docs / "exports" / "2026" / "07"


def test_unknown_store_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="Nieznany magazyn KPiR"):
        storage._store_spec("other")  # type: ignore[arg-type]


def test_runtime_write_inventory_no_longer_flags_kpir_storage() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    relative = "Komponenty/kpir/storage.py"
    source_path = repo_root / relative

    findings, error = scan_python_source(
        relative,
        source_path.read_text(encoding="utf-8"),
    )

    assert error == ""
    assert findings == []
