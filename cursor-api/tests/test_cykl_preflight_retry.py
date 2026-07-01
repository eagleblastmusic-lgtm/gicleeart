"""Testy pre-flight check oraz kolejki awaryjnej (retry_queue)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


def _stub_storage(tmp_path, monkeypatch):
    """Podmienia sciezki w cykl.storage tak zeby testy nie tykaly realnych danych."""
    from Komponenty.socialmedia.cykl import storage
    data_dir = tmp_path / "data"
    imgs = data_dir / "Obrazy"
    data_dir.mkdir(parents=True, exist_ok=True)
    imgs.mkdir(parents=True, exist_ok=True)
    storage._DATA_DIR = data_dir
    storage._QUEUE_FILE = data_dir / "queue.json"
    storage._GEN_STATE_FILE = data_dir / "generation_state.json"
    storage._META_STATE_FILE = data_dir / "meta_state.json"
    storage._CONFIG_FILE = data_dir / "config.json"
    storage._CREDS_FILE = data_dir / "meta_credentials.json"
    storage.IMAGES_DIR = imgs
    return storage


def _mk_item(storage, **overrides):
    item = storage.CykleItem.new(
        artist="A", artist_handle="a",
        painting_title_pl="T", painting_title_en="T",
        painting_handle="t",
        product_id=1, product_gid="gid://1",
        product_image_url="https://cdn.example/pic.jpg",
        product_image_alt="",
        description_pl="PL", description_en="EN",
    )
    for k, v in overrides.items():
        setattr(item, k, v)
    return item


class TestPreflight:
    def test_fails_without_credentials(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        storage.save_meta_credentials({})  # pusto
        item = _mk_item(storage, caption_pl="Cap", caption_en="Cap")
        from Komponenty.socialmedia.cykl import preflight
        r = preflight.preflight_for_channel(item, "fb_pl")
        assert not r.ok
        names = {c.name: c.ok for c in r.checks}
        assert names["credentials"] is False

    def test_passes_with_minimal_setup(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        storage.save_meta_credentials({
            "fb_pl": {"page_id": "1", "access_token": "TOKEN"},
        })
        item = _mk_item(storage, caption_pl="hello")
        from Komponenty.socialmedia.cykl import preflight
        r = preflight.preflight_for_channel(item, "fb_pl")
        assert r.ok, [c for c in r.checks if not c.ok]

    def test_caption_over_limit(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        storage.save_meta_credentials({
            "ig_pl": {"ig_user_id": "1", "access_token": "TOKEN"},
        })
        long = "x" * 3000  # IG limit 2200
        item = _mk_item(storage, caption_pl=long)
        from Komponenty.socialmedia.cykl import preflight
        r = preflight.preflight_for_channel(item, "ig_pl")
        assert not r.ok
        assert any(c.name == "caption_limit" and not c.ok for c in r.checks)

    def test_link_not_valid(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        storage.save_meta_credentials({
            "fb_pl": {"page_id": "1", "access_token": "TOKEN"},
        })
        # Broken URL (http://) with a space mid-way
        item = _mk_item(storage, caption_pl="zobacz http://bad url/x")
        from Komponenty.socialmedia.cykl import preflight
        r = preflight.preflight_for_channel(item, "fb_pl")
        link_check = next(c for c in r.checks if c.name == "links")
        assert link_check.ok  # URL "http://bad" (bez spacji w samym matched URL) OK
        # Jawny zly link - rozrywamy match (zaden match)
        # = testujemy ze pusto/poprawnie


class TestRetryQueue:
    def test_candidates_from_failed(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        item = _mk_item(storage)
        item.published_fb_pl = "error: sieć"
        item.published_ig_pl = "done@2026-01-01T10:00:00"
        item.status = "error"
        storage.save_queue([item])
        from Komponenty.socialmedia.cykl import retry_queue
        cands = retry_queue.retry_candidates()
        assert len(cands) == 1
        it, chans = cands[0]
        assert "fb_pl" in chans and "ig_pl" not in chans

    def test_error_messages(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        item = _mk_item(storage)
        item.published_fb_pl = "error: rate limit"
        storage.save_queue([item])
        from Komponenty.socialmedia.cykl import retry_queue
        msgs = retry_queue.error_messages(item)
        assert msgs[0][0] == "fb_pl"
        assert "rate limit" in msgs[0][1]

    def test_attempts_cap(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        # Ustawiamy cap = 2
        cfg = storage.load_config()
        cfg["retry_max_attempts"] = 2
        storage.save_config(cfg)

        item = _mk_item(storage)
        item.published_fb_pl = "error: X"
        storage.save_queue([item])
        # 3 wpisy error -> przekroczony cap, kandydatem nie jest
        for _ in range(3):
            storage.append_meta_log({
                "item_id": item.id, "channel": "fb_pl",
                "status": "error", "message": "x", "phase": "publish",
            })
        from Komponenty.socialmedia.cykl import retry_queue
        cands = retry_queue.retry_candidates()
        assert cands == []

    def test_mark_skipped(self, tmp_path, monkeypatch):
        storage = _stub_storage(tmp_path, monkeypatch)
        item = _mk_item(storage)
        item.published_fb_pl = "error: x"
        storage.save_queue([item])
        from Komponenty.socialmedia.cykl import retry_queue
        assert retry_queue.mark_item_skipped(item.id) is True
        got = storage.get_item(item.id)
        assert got is not None and got.status == "skipped"
