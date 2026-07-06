"""Testy bounded set_with_ref writer — Studio Preview (F5.4b2)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_asset_catalog import build_background_asset_catalog
from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_readiness import (
    SaveReadiness,
    evaluate_save_readiness,
)
from giclee_app.studio.background_save_writer import (
    apply_set_with_ref_patch,
    assert_bounded_diff,
    build_set_with_ref_patch,
    resolve_active_index_path,
    restore_section_background_from_backup,
    set_section_background_with_ref_backup,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_save_writer.py"
)
_OTHER_ZONE = STRONAGLOWNA_SECTION_BGS[1]
_ZONE = STRONAGLOWNA_SECTION_BGS[0]


def _write_fixture(
    tmp_path: Path,
    *,
    zone_index: dict | None = None,
    other_zone_index: dict | None = None,
    index_raw: str | None = None,
) -> Path:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": [{"id": "v1", "label": "T"}]}),
        encoding="utf-8",
    )
    if index_raw is not None:
        (variants_dir / "index.json").write_text(index_raw, encoding="utf-8")
        return tmp_path
    sections: dict = {}
    if zone_index is not None:
        sections[_ZONE.section_key] = {"settings": zone_index}
    if other_zone_index is not None:
        sections[_OTHER_ZONE.section_key] = {"settings": other_zone_index}
    (variants_dir / "index.json").write_text(json.dumps({"sections": sections}), encoding="utf-8")
    return tmp_path


def _catalog_asset_id(tmp_path: Path, *, kind: str, label: str | None = None) -> str:
    catalog = build_background_asset_catalog(tmp_path)
    for entry in catalog.entries:
        if entry.kind != kind:
            continue
        if label is None or entry.display_label == label:
            return entry.asset_id
    raise AssertionError(f"asset not found: kind={kind} label={label}")


def _set_with_ref_readiness(
    tmp_path: Path,
    draft: BackgroundDraftState,
) -> SaveReadiness:
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert readiness.ready and readiness.operation == "set_with_ref"
    return readiness


def test_build_set_with_ref_patch_image() -> None:
    patch = build_set_with_ref_patch(
        "image",
        "shopify://shop_images/x.jpg",
        {"background_overlay_pct": 40},
    )
    assert patch == {
        "background_media": "image",
        "background_image": "shopify://shop_images/x.jpg",
        "video": "",
        "background_overlay_pct": 40,
    }


def test_build_set_with_ref_patch_video() -> None:
    patch = build_set_with_ref_patch(
        "video",
        "shopify://files/videos/a.mp4",
        {"background_overlay_pct": "25"},
    )
    assert patch == {
        "background_media": "video",
        "background_image": "",
        "video": "shopify://files/videos/a.mp4",
        "background_overlay_pct": 25,
    }


def test_overlay_fallback_zero() -> None:
    patch = build_set_with_ref_patch("image", "ref.jpg", {})
    assert patch["background_overlay_pct"] == 0


def test_brak_to_image_writes_four_fields(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={"background_media": "none"},
        other_zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/source.jpg",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image", label="source.jpg")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    assert result.backup_filename is not None

    index_path = resolve_active_index_path(tmp_path)
    assert index_path is not None
    data = json.loads(index_path.read_text(encoding="utf-8"))
    settings = data["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "image"
    assert settings["background_image"] == "shopify://shop_images/source.jpg"
    assert settings["video"] == ""
    assert settings["background_overlay_pct"] == 0


def test_brak_to_video_writes_four_fields(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={"background_media": "none"},
        other_zone_index={
            "background_media": "video",
            "video": "shopify://files/videos/source.mp4",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="video")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="video",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    data = json.loads(resolve_active_index_path(tmp_path).read_text(encoding="utf-8"))
    settings = data["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "video"
    assert settings["background_image"] == ""
    assert settings["video"] == "shopify://files/videos/source.mp4"


def test_image_to_video_switch(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/current.jpg",
            "background_overlay_pct": 30,
        },
        other_zone_index={
            "background_media": "video",
            "video": "shopify://files/videos/other.mp4",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="video")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="video",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    data = json.loads(resolve_active_index_path(tmp_path).read_text(encoding="utf-8"))
    settings = data["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "video"
    assert settings["background_image"] == ""
    assert settings["video"] == "shopify://files/videos/other.mp4"
    assert settings["background_overlay_pct"] == 30


def test_video_to_image_switch(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "video",
            "video": "shopify://files/videos/current.mp4",
            "background_overlay_pct": 15,
        },
        other_zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/other.jpg",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image", label="other.jpg")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    data = json.loads(resolve_active_index_path(tmp_path).read_text(encoding="utf-8"))
    settings = data["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "image"
    assert settings["background_image"] == "shopify://shop_images/other.jpg"
    assert settings["video"] == ""


def test_same_kind_same_ref_no_write(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/same.jpg",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image", label="same.jpg")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert not readiness.ready
    assert readiness.operation == "noop"

    forced = SaveReadiness(
        ready=True,
        operation="set_with_ref",
        block_reason=None,
        requires_confirm=True,
        summary="",
        status_label="gotowe",
        ref_complete=True,
    )
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=forced)
    assert not result.ok
    assert "Brak zmian" in result.message


def test_invalid_selected_asset_id_no_write(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index={"background_media": "none"})
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id="img:99",
    )
    forced = SaveReadiness(
        ready=True,
        operation="set_with_ref",
        block_reason=None,
        requires_confirm=True,
        summary="",
        status_label="gotowe",
        ref_complete=True,
    )
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=forced)
    assert not result.ok
    assert "nieprawidłowy" in result.message.lower()


def test_kind_mismatch_no_write(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={"background_media": "none"},
        other_zone_index={
            "background_media": "video",
            "video": "shopify://files/videos/v.mp4",
        },
    )
    video_id = _catalog_asset_id(tmp_path, kind="video")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=video_id,
    )
    forced = SaveReadiness(
        ready=True,
        operation="set_with_ref",
        block_reason=None,
        requires_confirm=True,
        summary="",
        status_label="gotowe",
        ref_complete=True,
    )
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=forced)
    assert not result.ok


def test_video_collage_no_write(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index={"background_media": "none"})
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="video_collage",
        selected_asset_id="img:0",
    )
    forced = SaveReadiness(
        ready=True,
        operation="set_with_ref",
        block_reason=None,
        requires_confirm=True,
        summary="",
        status_label="gotowe",
        ref_complete=True,
    )
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=forced)
    assert not result.ok


def test_set_with_ref_creates_backup_before_write(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={"background_media": "none"},
        other_zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    backups = list((tmp_path / "data" / "backups").glob("index-*.json"))
    assert len(backups) == 1


def test_only_target_section_changes(tmp_path: Path) -> None:
    other_before = {
        "background_media": "video",
        "video": "shopify://files/videos/keep.mp4",
        "background_overlay_pct": 25,
    }
    _write_fixture(
        tmp_path,
        zone_index={"background_media": "none"},
        other_zone_index=other_before,
    )
    asset_id = _catalog_asset_id(tmp_path, kind="video", label="keep.mp4")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="video",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    data = json.loads(resolve_active_index_path(tmp_path).read_text(encoding="utf-8"))
    assert data["sections"][_OTHER_ZONE.section_key]["settings"] == other_before


def test_header_preserved(tmp_path: Path) -> None:
    header = "/* shopify */\n"
    body = json.dumps(
        {
            "sections": {
                _ZONE.section_key: {"settings": {"background_media": "none"}},
                _OTHER_ZONE.section_key: {
                    "settings": {
                        "background_media": "image",
                        "background_image": "shopify://shop_images/x.jpg",
                    }
                },
            }
        }
    )
    _write_fixture(tmp_path, index_raw=f"{header}{body}")
    asset_id = _catalog_asset_id(tmp_path, kind="image")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    raw = resolve_active_index_path(tmp_path).read_text(encoding="utf-8")
    assert raw.startswith("/* shopify */")


def test_manifest_and_settings_untouched(tmp_path: Path) -> None:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = tmp_path / "data" / "variants" / "manifest.json"
    settings_path = variants_dir / "settings.json"
    manifest_before = {"active": "v1", "variants": [{"id": "v1", "label": "T"}]}
    settings_before = {"theme": "keep"}
    manifest_path.write_text(json.dumps(manifest_before), encoding="utf-8")
    settings_path.write_text(json.dumps(settings_before), encoding="utf-8")
    sections = {
        _ZONE.section_key: {"settings": {"background_media": "none"}},
        _OTHER_ZONE.section_key: {
            "settings": {
                "background_media": "image",
                "background_image": "shopify://shop_images/x.jpg",
            }
        },
    }
    (variants_dir / "index.json").write_text(
        json.dumps({"sections": sections}),
        encoding="utf-8",
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == manifest_before
    assert json.loads(settings_path.read_text(encoding="utf-8")) == settings_before


def test_restore_after_set_with_ref(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/original.jpg",
            "background_overlay_pct": 20,
        },
        other_zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/new.jpg",
        },
    )
    asset_id = _catalog_asset_id(tmp_path, kind="image", label="new.jpg")
    draft = BackgroundDraftState(
        zone_field_id=_ZONE.field_id,
        asset_kind="image",
        selected_asset_id=asset_id,
    )
    readiness = _set_with_ref_readiness(tmp_path, draft)
    result = set_section_background_with_ref_backup(draft, tmp_path, readiness=readiness)
    assert result.ok and result.backup_filename

    restore = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=result.backup_filename,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert restore.ok
    data = json.loads(resolve_active_index_path(tmp_path).read_text(encoding="utf-8"))
    settings = data["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "image"
    assert settings["background_image"] == "shopify://shop_images/original.jpg"
    assert settings["background_overlay_pct"] == 20


def test_apply_set_with_ref_patch_mutates_template() -> None:
    template = {"sections": {_ZONE.section_key: {"settings": {"title": "keep"}}}}
    patch = build_set_with_ref_patch("image", "ref.jpg", {})
    apply_set_with_ref_patch(template, _ZONE.section_key, patch)
    settings = template["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "image"
    assert settings["title"] == "keep"


def test_assert_bounded_diff_rejects_extra_fields() -> None:
    before = {
        "sections": {
            _ZONE.section_key: {
                "settings": {
                    "background_media": "none",
                    "title": "keep",
                }
            }
        }
    }
    after = json.loads(json.dumps(before))
    patch = build_set_with_ref_patch("image", "ref.jpg", {})
    apply_set_with_ref_patch(after, _ZONE.section_key, patch)
    after["sections"][_ZONE.section_key]["settings"]["title"] = "changed"
    try:
        assert_bounded_diff(before, after, _ZONE.section_key)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "title" in str(exc)


def test_writer_ast_guardrails() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "set_section_background_with_ref_backup" in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "filedialog" not in text
    assert "requests" not in text
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")
