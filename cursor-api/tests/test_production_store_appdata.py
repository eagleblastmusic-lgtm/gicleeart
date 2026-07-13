from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty.produkcja import orders_sync, production_store, retention, view, web_server
from tools.repository_safety.runtime_writes import scan_python_source


def _configure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    local_root = tmp_path / "local-root"
    legacy_dir = tmp_path / "repo" / "cursor-api" / "Komponenty" / "produkcja" / "dane"
    legacy_orders = legacy_dir / "zamowienia.json"
    legacy_sync = legacy_dir / "sync_state.json"

    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local_root))
    monkeypatch.setattr(production_store, "LEGACY_DATA_DIR", legacy_dir)

    for module in (orders_sync, retention, view, web_server):
        monkeypatch.setattr(module, "_LEGACY_DATA_DIR", legacy_dir)
        monkeypatch.setattr(module, "_DATA_DIR", legacy_dir)
        monkeypatch.setattr(module, "_LEGACY_ORDERS_FILE", legacy_orders)
        monkeypatch.setattr(module, "_ORDERS_FILE", legacy_orders)

    monkeypatch.setattr(orders_sync, "_LEGACY_SYNC_STATE_FILE", legacy_sync)
    monkeypatch.setattr(orders_sync, "_SYNC_STATE_FILE", legacy_sync)
    return local_root, legacy_orders, legacy_sync


def _external_data_dir(local_root: Path) -> Path:
    return local_root / "data" / "Komponenty" / "produkcja" / "dane"


def test_all_production_entry_points_share_external_first_orders(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root, legacy_orders, _legacy_sync = _configure_paths(monkeypatch, tmp_path)
    legacy_orders.parent.mkdir(parents=True)
    legacy_payload = {"next_id": 2, "orders": [{"id": "ORD-0001", "ramka_wariant": "Dab M"}]}
    legacy_orders.write_text(json.dumps(legacy_payload), encoding="utf-8")
    before = legacy_orders.read_bytes()

    assert orders_sync._load_db()["orders"][0]["id"] == "ORD-0001"
    assert view._load_db()["orders"][0]["id"] == "ORD-0001"
    assert web_server._load_db()["orders"][0]["id"] == "ORD-0001"
    assert retention._load_orders()["orders"][0]["id"] == "ORD-0001"

    updated = {"next_id": 3, "orders": [{"id": "ORD-0002", "ramka_wariant": "Dab XL"}]}
    orders_sync._save_db(updated)

    external = _external_data_dir(local_root) / "zamowienia.json"
    assert json.loads(external.read_text(encoding="utf-8"))["orders"][0]["id"] == "ORD-0002"
    assert view._load_db()["orders"][0]["id"] == "ORD-0002"
    assert web_server._load_db()["orders"][0]["id"] == "ORD-0002"
    assert retention._load_orders()["orders"][0]["id"] == "ORD-0002"
    assert legacy_orders.read_bytes() == before
    assert list(external.parent.glob(f".{external.name}.*.tmp")) == []


def test_view_initializes_external_store_only_when_no_legacy_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root, legacy_orders, _legacy_sync = _configure_paths(monkeypatch, tmp_path)

    db = view._load_db()

    external = _external_data_dir(local_root) / "zamowienia.json"
    assert db == {"next_id": 1, "orders": []}
    assert json.loads(external.read_text(encoding="utf-8")) == db
    assert not legacy_orders.exists()


def test_sync_state_reads_legacy_writes_external_and_reset_shadows_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root, _legacy_orders, legacy_sync = _configure_paths(monkeypatch, tmp_path)
    legacy_sync.parent.mkdir(parents=True)
    legacy_sync.write_text(json.dumps({"last_sync_iso": "legacy"}), encoding="utf-8")
    before = legacy_sync.read_bytes()

    assert orders_sync._load_sync_state()["last_sync_iso"] == "legacy"
    orders_sync._save_sync_state({"last_sync_iso": "external"})

    external = _external_data_dir(local_root) / "sync_state.json"
    assert json.loads(external.read_text(encoding="utf-8"))["last_sync_iso"] == "external"
    assert legacy_sync.read_bytes() == before

    orders_sync.reset_sync_state()

    assert json.loads(external.read_text(encoding="utf-8")) == {}
    assert orders_sync._load_sync_state() == {}
    assert legacy_sync.read_bytes() == before


def test_archives_merge_external_and_legacy_with_external_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_root, legacy_orders, _legacy_sync = _configure_paths(monkeypatch, tmp_path)
    legacy_orders.parent.mkdir(parents=True)
    legacy_2025 = legacy_orders.parent / "archive_2025.json"
    legacy_2025.write_text(json.dumps({"year": 2025, "orders": [{"id": "legacy"}]}), encoding="utf-8")
    before = legacy_2025.read_bytes()

    external_dir = _external_data_dir(local_root)
    external_dir.mkdir(parents=True)
    external_2026 = external_dir / "archive_2026.json"
    external_2026.write_text(json.dumps({"year": 2026, "orders": [{"id": "external"}]}), encoding="utf-8")

    listed = retention.list_archives()
    assert [(item["year"], item["count"]) for item in listed] == [("2025", 1), ("2026", 1)]

    retention._save_archive(2025, {"year": 2025, "orders": [{"id": "migrated"}]})

    external_2025 = external_dir / "archive_2025.json"
    assert json.loads(external_2025.read_text(encoding="utf-8"))["orders"][0]["id"] == "migrated"
    assert retention._load_archive(2025)["orders"][0]["id"] == "migrated"
    assert legacy_2025.read_bytes() == before


def test_explicit_file_and_directory_overrides_remain_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_paths(monkeypatch, tmp_path)

    orders_override = tmp_path / "override" / "orders.json"
    sync_override = tmp_path / "override" / "sync.json"
    monkeypatch.setattr(orders_sync, "_ORDERS_FILE", orders_override)
    monkeypatch.setattr(orders_sync, "_SYNC_STATE_FILE", sync_override)
    orders_sync._save_db({"next_id": 1, "orders": []})
    orders_sync._save_sync_state({"ok": True})
    assert orders_override.is_file()
    assert json.loads(sync_override.read_text(encoding="utf-8")) == {"ok": True}

    view_override = tmp_path / "view-data"
    monkeypatch.setattr(view, "_DATA_DIR", view_override)
    view._save_db({"next_id": 2, "orders": []})
    assert (view_override / "zamowienia.json").is_file()

    web_override = tmp_path / "web" / "orders.json"
    monkeypatch.setattr(web_server, "_ORDERS_FILE", web_override)
    web_server._save_db({"next_id": 3, "orders": []})
    assert web_override.is_file()

    retention_override = tmp_path / "retention-data"
    monkeypatch.setattr(retention, "_DATA_DIR", retention_override)
    retention._save_archive(2024, {"year": 2024, "orders": []})
    assert (retention_override / "archive_2024.json").is_file()


def test_runtime_write_inventory_no_longer_flags_production_store() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        "Komponenty/produkcja/orders_sync.py",
        "Komponenty/produkcja/retention.py",
        "Komponenty/produkcja/view.py",
        "Komponenty/produkcja/web_server.py",
        "Komponenty/produkcja/production_store.py",
    ]

    for relative in targets:
        source_path = repo_root / relative
        findings, error = scan_python_source(
            relative,
            source_path.read_text(encoding="utf-8"),
        )
        assert error == ""
        assert findings == [], (relative, findings)
