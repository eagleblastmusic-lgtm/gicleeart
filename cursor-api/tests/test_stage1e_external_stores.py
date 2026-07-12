from __future__ import annotations

import json
from pathlib import Path

import pytest

from Komponenty._shared import recent_images
from Komponenty.blog import storage as blog_storage
from Komponenty.dnr import storage as dnr_storage
from Komponenty.dokumentysprzedazy import storage as invoice_storage
from giclee_app.app_paths import data_path


def _legacy_bytes(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _assert_legacy_unchanged(path: Path, before: bytes | None) -> None:
    after = path.read_bytes() if path.is_file() else None
    assert after == before


def test_recent_images_writes_external_and_preserves_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    legacy = recent_images._STORE.legacy_path
    assert legacy is not None
    before = _legacy_bytes(legacy)

    recent_images._STORE.ensure_parent().write_text("[]", encoding="utf-8")
    recent_images.add_recent_image("shopify://image/test")

    assert recent_images._STORE.write_path.is_file()
    assert recent_images.list_recent_images() == ["shopify://image/test"]
    _assert_legacy_unchanged(legacy, before)


def test_blog_topics_and_cache_write_to_manifest_compatible_data_bucket(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))

    topic = blog_storage.TopicProposal.new("Temat testowy")
    blog_storage.save_topics([topic])
    blog_storage.save_articles_cache([{"id": 1, "title": "Test"}])

    expected_dir = tmp_path / "local" / "data" / "Komponenty" / "blog" / "data"
    assert blog_storage._TOPICS.write_path == expected_dir / "topics.json"
    assert blog_storage._ARTICLES_CACHE.write_path == expected_dir / "articles_cache.json"
    assert [item.title for item in blog_storage.load_topics()] == ["Temat testowy"]
    assert blog_storage.load_articles_cache()["articles"][0]["title"] == "Test"


def test_dnr_database_and_settings_use_separate_external_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(tmp_path / "roaming"))

    payload = {"next_sale_id": 2, "next_cost_id": 1, "sales": [], "costs": []}
    dnr_storage.save_db(payload)

    assert dnr_storage._DB.write_path == (
        tmp_path / "local" / "data" / "Komponenty" / "dnr" / "dane" / "dnr.json"
    )
    assert dnr_storage._SETTINGS.write_path == (
        tmp_path / "roaming" / "config" / "Komponenty" / "dnr" / "dane" / "dnr_settings.json"
    )
    assert dnr_storage.load_db() == payload
    assert not dnr_storage._SETTINGS.write_path.exists()


def test_invoice_store_writes_database_events_and_documents_outside_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    fresh_events = data_path(
        "Komponenty/dokumentysprzedazy/dane/invoice_events.jsonl",
        legacy=tmp_path / "missing-invoice-events.jsonl",
    )
    monkeypatch.setattr(invoice_storage, "_EVENTS", fresh_events)

    invoice_storage.save_invoices_db({"next_id": 2, "invoices": []})
    invoice_storage.append_event("created", "INV-000001", details="test")
    docs = invoice_storage.documents_dir_for_date("2026-07-11")

    expected_base = tmp_path / "local" / "data" / "Komponenty" / "dokumentysprzedazy"
    assert invoice_storage._INVOICES.write_path == expected_base / "dane" / "invoices.json"
    assert fresh_events.write_path == expected_base / "dane" / "invoice_events.jsonl"
    assert docs == expected_base / "documents" / "invoices" / "2026" / "07"
    assert invoice_storage.load_invoices_db()["next_id"] == 2
    assert invoice_storage.list_events("INV-000001")[0]["action"] == "created"
    assert json.loads(fresh_events.write_path.read_text(encoding="utf-8"))["actor"] == "user"


def test_invoice_event_append_seeds_legacy_history_without_modifying_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(tmp_path / "local"))
    legacy = tmp_path / "legacy" / "invoice_events.jsonl"
    legacy.parent.mkdir(parents=True)
    legacy_entry = {
        "id": "legacy-id",
        "action": "legacy",
        "invoice_id": "INV-LEGACY",
        "actor": "user",
        "details": "",
        "at": "2026-01-01T00:00:00",
    }
    legacy_text = json.dumps(legacy_entry) + "\n"
    legacy.write_text(legacy_text, encoding="utf-8")

    event_path = data_path(
        "Komponenty/dokumentysprzedazy/dane/invoice_events.jsonl",
        legacy=legacy,
    )
    monkeypatch.setattr(invoice_storage, "_EVENTS", event_path)

    invoice_storage.append_event("created", "INV-NEW")

    lines = event_path.write_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["action"] == "legacy"
    assert json.loads(lines[1])["action"] == "created"
    assert legacy.read_text(encoding="utf-8") == legacy_text
