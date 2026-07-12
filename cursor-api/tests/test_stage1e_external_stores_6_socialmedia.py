from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest


def _set_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    local = tmp_path / "local"
    roaming = tmp_path / "roaming"
    monkeypatch.setenv("GICLEEAPP_LOCAL_ROOT", str(local))
    monkeypatch.setenv("GICLEEAPP_ROAMING_ROOT", str(roaming))
    return local, roaming


def _write_json(path: Path, payload: object) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(raw)
    return raw


def test_socialmedia_posts_read_legacy_and_write_local_appdata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.socialmedia import storage

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-socialmedia"
    legacy_file = legacy_dir / "posts.json"
    legacy_bytes = _write_json(
        legacy_file,
        {
            "posts": [
                {
                    "id": "legacy-post",
                    "platform": "ig_feed",
                    "language": "pl",
                    "caption": "Legacy",
                }
            ]
        },
    )

    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(storage, "_LEGACY_POSTS_FILE", legacy_file)
    monkeypatch.setattr(storage, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(storage, "_POSTS_FILE", legacy_file)

    assert [post.id for post in storage.load_posts()] == ["legacy-post"]

    storage.add_post(
        storage.Post.new(
            platform="fb",
            language="en",
            caption="External",
        )
    )

    target = local / "data/Komponenty/socialmedia/data/posts.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert [item["caption"] for item in payload["posts"]] == ["Legacy", "External"]
    assert [post.caption for post in storage.load_posts()] == ["Legacy", "External"]
    assert legacy_file.read_bytes() == legacy_bytes


def test_socialmedia_presets_read_legacy_and_write_roaming_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.socialmedia import presets

    _, roaming = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-presets"
    legacy_file = legacy_dir / "content_presets.json"
    legacy_bytes = _write_json(
        legacy_file,
        {
            "presets": [
                {
                    "id": "legacy-preset",
                    "name": "Legacy",
                    "platforms": ["ig_feed"],
                    "language": "pl",
                }
            ]
        },
    )

    monkeypatch.setattr(presets, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(presets, "_LEGACY_FILE", legacy_file)
    monkeypatch.setattr(presets, "_DATA_DIR", legacy_dir)
    monkeypatch.setattr(presets, "_FILE", legacy_file)

    assert [preset.name for preset in presets.load_presets()] == ["Legacy"]

    presets.add_preset(
        presets.Preset.new(
            name="External",
            platforms=["fb"],
            language="en",
        )
    )

    target = roaming / "config/Komponenty/socialmedia/data/content_presets.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert {item["name"] for item in payload["presets"]} == {"Legacy", "External"}
    assert {preset.name for preset in presets.load_presets()} == {"Legacy", "External"}
    assert legacy_file.read_bytes() == legacy_bytes


def _patch_cycle_legacy(
    monkeypatch: pytest.MonkeyPatch,
    storage: object,
    legacy_dir: Path,
) -> dict[str, Path]:
    paths = {
        "_QUEUE_FILE": legacy_dir / "queue.json",
        "_GEN_STATE_FILE": legacy_dir / "generation_state.json",
        "_META_STATE_FILE": legacy_dir / "meta_state.json",
        "_CONFIG_FILE": legacy_dir / "config.json",
        "_CREDS_FILE": legacy_dir / "meta_credentials.json",
        "IMAGES_DIR": legacy_dir / "Obrazy",
    }
    monkeypatch.setattr(storage, "_LEGACY_DATA_DIR", legacy_dir)
    monkeypatch.setattr(storage, "_DATA_DIR", legacy_dir)
    for name, path in paths.items():
        monkeypatch.setattr(storage, name, path)
    return paths


def _cycle_item(storage: object, *, item_id: str, caption: str) -> object:
    return storage.CykleItem.new(
        id=item_id,
        artist="Artist",
        artist_handle="artist",
        painting_title_pl="Obraz",
        painting_title_en="Painting",
        painting_handle="painting",
        product_id=1,
        product_gid="gid://shopify/Product/1",
        product_image_url="",
        product_image_alt="",
        description_pl="",
        description_en="",
        caption_pl=caption,
    )


def test_socialmedia_cycle_runtime_and_config_paths_are_external(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.socialmedia.cykl import storage

    local, roaming = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-cycle"
    paths = _patch_cycle_legacy(monkeypatch, storage, legacy_dir)

    legacy_queue_bytes = _write_json(
        paths["_QUEUE_FILE"],
        {"items": [asdict(_cycle_item(storage, item_id="legacy-item", caption="Legacy"))]},
    )
    legacy_generation_bytes = _write_json(paths["_GEN_STATE_FILE"], {"through": "legacy"})
    legacy_meta_bytes = _write_json(paths["_META_STATE_FILE"], {"log": [{"event": "legacy"}]})
    legacy_config_bytes = _write_json(
        paths["_CONFIG_FILE"],
        {
            "slot_times": {"morning": "09:00"},
            "active_channels": ["fb_pl"],
            "timezone": "Europe/Warsaw",
        },
    )
    legacy_creds_bytes = _write_json(
        paths["_CREDS_FILE"],
        {"fb_pl": {"page_id": "123", "access_token": "placeholder"}},
    )

    assert [item.id for item in storage.load_queue()] == ["legacy-item"]
    assert storage.load_generation_state()["through"] == "legacy"
    assert storage.load_meta_log() == [{"event": "legacy"}]
    assert storage.load_config()["slot_times"]["morning"] == "09:00"
    assert storage.load_meta_credentials()["fb_pl"]["page_id"] == "123"

    storage.save_queue(
        [
            _cycle_item(storage, item_id="legacy-item", caption="Legacy"),
            _cycle_item(storage, item_id="external-item", caption="External"),
        ]
    )
    storage.save_generation_state({"through": "external"})
    storage.append_meta_log({"event": "external"})
    storage.save_config(
        {
            "slot_times": {"morning": "07:30"},
            "active_channels": ["ig_en"],
            "timezone": "Europe/Warsaw",
        }
    )
    storage.save_meta_credentials(
        {"ig_en": {"ig_user_id": "456", "access_token": "placeholder"}}
    )

    data_root = local / "data/Komponenty/socialmedia/data/cykl"
    config_root = roaming / "config/Komponenty/socialmedia/data/cykl"

    assert [item.id for item in storage.load_queue()] == ["legacy-item", "external-item"]
    assert json.loads((data_root / "generation_state.json").read_text(encoding="utf-8"))["through"] == "external"
    meta_log = json.loads((data_root / "meta_state.json").read_text(encoding="utf-8"))["log"]
    assert [entry["event"] for entry in meta_log] == ["legacy", "external"]
    assert json.loads((config_root / "config.json").read_text(encoding="utf-8"))["slot_times"]["morning"] == "07:30"
    creds = json.loads((config_root / "meta_credentials.json").read_text(encoding="utf-8"))
    assert set(creds) == {"fb_pl", "ig_en"}

    assert paths["_QUEUE_FILE"].read_bytes() == legacy_queue_bytes
    assert paths["_GEN_STATE_FILE"].read_bytes() == legacy_generation_bytes
    assert paths["_META_STATE_FILE"].read_bytes() == legacy_meta_bytes
    assert paths["_CONFIG_FILE"].read_bytes() == legacy_config_bytes
    assert paths["_CREDS_FILE"].read_bytes() == legacy_creds_bytes


def test_socialmedia_cycle_images_use_external_writable_root_without_deleting_legacy(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.socialmedia.cykl import images, storage

    local, _ = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-cycle-images"
    paths = _patch_cycle_legacy(monkeypatch, storage, legacy_dir)
    legacy_painting = paths["IMAGES_DIR"] / "artist" / "painting"
    legacy_painting.mkdir(parents=True)
    legacy_main = legacy_painting / "main.jpg"
    legacy_zoom = legacy_painting / "zoom-1.jpg"
    legacy_main.write_bytes(b"legacy-main")
    legacy_zoom.write_bytes(b"legacy-zoom")

    found = images.list_images_for("artist", "painting")
    assert found.main == "artist/painting/main.jpg"
    assert found.zooms == ["artist/painting/zoom-1.jpg"]

    # A legacy fallback can be read, but Stage 1E deletion never targets it.
    assert images.delete_image("artist/painting/main.jpg") is False
    assert legacy_main.read_bytes() == b"legacy-main"

    source = tmp_path / "new-zoom.jpg"
    source.write_bytes(b"external-zoom")
    rel = images.copy_into(source, "artist", "painting", role="zoom")
    external = local / "data/Komponenty/socialmedia/data/cykl/Obrazy" / rel
    assert external.read_bytes() == b"external-zoom"
    assert legacy_zoom.read_bytes() == b"legacy-zoom"

    assert images.delete_image(rel) is True
    assert not external.exists()
    assert legacy_zoom.read_bytes() == b"legacy-zoom"


def test_socialmedia_token_metadata_refresh_writes_only_roaming_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from Komponenty.socialmedia.cykl import meta_token_status, storage

    _, roaming = _set_roots(monkeypatch, tmp_path)
    legacy_dir = tmp_path / "legacy-token-status"
    paths = _patch_cycle_legacy(monkeypatch, storage, legacy_dir)
    legacy_bytes = _write_json(
        paths["_CREDS_FILE"],
        {"fb_pl": {"page_id": "123", "access_token": "placeholder"}},
    )

    monkeypatch.setattr(
        meta_token_status,
        "debug_access_token",
        lambda _token: {"is_valid": True, "expires_at": 0},
    )

    meta_token_status.refresh_token_metadata_in_file(mark_renewed=True)

    target = roaming / "config/Komponenty/socialmedia/data/cykl/meta_credentials.json"
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["fb_pl"]["is_valid"] == "true"
    assert payload["fb_pl"]["expires_at"] == "0"
    assert payload["token_renewed_at"]
    assert paths["_CREDS_FILE"].read_bytes() == legacy_bytes
