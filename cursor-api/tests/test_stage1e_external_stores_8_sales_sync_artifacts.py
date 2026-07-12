from __future__ import annotations

import json
from pathlib import Path

import pytest

from giclee_app.app_paths import data_path


def _bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def test_order_sync_state_reads_legacy_and_writes_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dokumentysprzedazy import orders_sync

    local = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    legacy = tmp_path / "legacy" / "orders_sync_state.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        json.dumps({"pending_order_ids": [7], "notified_order_ids": [7]}),
        encoding="utf-8",
    )
    before = legacy.read_bytes()

    monkeypatch.setattr(orders_sync, "_LEGACY_SYNC_STATE_FILE", legacy)
    monkeypatch.setattr(orders_sync, "_SYNC_STATE_FILE", legacy)
    monkeypatch.setattr(
        orders_sync,
        "_SYNC_STATE",
        data_path(
            "Komponenty/dokumentysprzedazy/dane/orders_sync_state.json",
            legacy=legacy,
        ),
    )

    assert orders_sync.pending_orders_count() == 1
    orders_sync._save_state({"pending_order_ids": [9], "notified_order_ids": [9]})

    target = (
        local
        / "data"
        / "Komponenty"
        / "dokumentysprzedazy"
        / "dane"
        / "orders_sync_state.json"
    )
    assert json.loads(target.read_text(encoding="utf-8"))["pending_order_ids"] == [9]
    assert orders_sync.pending_orders_count() == 1
    assert legacy.read_bytes() == before
    assert not list(target.parent.glob(f".{target.name}.*.tmp"))


def test_order_sync_direct_file_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dokumentysprzedazy import orders_sync

    override = tmp_path / "override" / "orders_sync_state.json"
    monkeypatch.setattr(orders_sync, "_SYNC_STATE_FILE", override)

    orders_sync._save_state({"pending_order_ids": [11]})

    assert json.loads(override.read_text(encoding="utf-8"))["pending_order_ids"] == [11]
    assert orders_sync._load_state()["pending_order_ids"] == [11]


def test_monthly_sales_export_writes_private_csv_to_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dokumentysprzedazy import export_monthly

    local = tmp_path / "local"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))

    legacy_dir = tmp_path / "legacy-exports"
    legacy_dir.mkdir(parents=True)
    legacy_csv = legacy_dir / "sales_2026_07.csv"
    legacy_csv.write_bytes(b"legacy-private-export")
    before = _bytes(legacy_csv)

    monkeypatch.setattr(export_monthly, "_LEGACY_EXPORT_DIR", legacy_dir)
    monkeypatch.setattr(export_monthly, "_EXPORT_DIR", legacy_dir)
    monkeypatch.setattr(
        export_monthly,
        "_EXPORT_ROOT",
        data_path(
            "Komponenty/dokumentysprzedazy/dane/exports/.path",
            legacy=legacy_dir / ".path",
        ),
    )
    monkeypatch.setattr(export_monthly, "list_invoices", lambda: [])

    out = export_monthly.export_month_csv(2026, 7)
    expected = (
        local
        / "data"
        / "Komponenty"
        / "dokumentysprzedazy"
        / "dane"
        / "exports"
        / "sales_2026_07.csv"
    )

    assert out == expected
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")
    assert "PODSUMOWANIE" in out.read_text(encoding="utf-8-sig")
    assert _bytes(legacy_csv) == before
    assert not list(expected.parent.glob(f".{expected.name}.*.tmp"))


def test_monthly_sales_export_direct_directory_override_remains_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.dokumentysprzedazy import export_monthly

    override = tmp_path / "exports"
    monkeypatch.setattr(export_monthly, "_EXPORT_DIR", override)
    monkeypatch.setattr(export_monthly, "list_invoices", lambda: [])

    out = export_monthly.export_month_csv(2026, 8)

    assert out == override / "sales_2026_08.csv"
    assert out.is_file()
