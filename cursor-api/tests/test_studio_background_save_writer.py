"""Testy bounded local clear writer — Studio Preview (F5.4b1)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_readiness import (
    SaveReadiness,
    evaluate_save_readiness,
)
from giclee_app.studio.background_save_writer import (
    SaveWriteResult,
    apply_clear_patch,
    assert_bounded_diff,
    backup_index_json,
    build_clear_patch,
    clear_section_background_with_backup,
    resolve_active_index_path,
    split_json_header,
    write_index_json_preserving_header,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_save_writer.py"
)
_PANEL_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"
_OTHER_ZONE = STRONAGLOWNA_SECTION_BGS[1]


def _write_fixture(
    tmp_path: Path,
    *,
    zone_index: dict | None = None,
    other_zone_index: dict | None = None,
    index_raw: str | None = None,
) -> Path:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": [{"id": "v1", "label": "T"}]}),
        encoding="utf-8",
    )
    if index_raw is not None:
        (variants_dir / "index.json").write_text(index_raw, encoding="utf-8")
        return tmp_path
    sections: dict = {}
    if zone_index is not None:
        sections[zone.section_key] = {"settings": zone_index}
    if other_zone_index is not None:
        sections[_OTHER_ZONE.section_key] = {"settings": other_zone_index}
    (variants_dir / "index.json").write_text(json.dumps({"sections": sections}), encoding="utf-8")
    return tmp_path


def _clear_readiness(tmp_path: Path, zone_index: dict) -> SaveReadiness:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(tmp_path, zone_index=zone_index)
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    return evaluate_save_readiness(draft, tmp_path, clear_intent=True)


def test_build_clear_patch_values() -> None:
    patch = build_clear_patch({})
    assert patch == {
        "background_media": "none",
        "background_image": "",
        "video": "",
        "background_overlay_pct": 0,
    }


def test_clear_creates_backup(tmp_path: Path) -> None:
    readiness = _clear_readiness(
        tmp_path,
        {
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
            "background_overlay_pct": 40,
        },
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    assert result.backup_filename is not None
    assert result.backup_filename.startswith("index-")
    assert result.backup_filename.endswith(".json")
    backups = list((tmp_path / "data" / "backups").glob("index-*.json"))
    assert len(backups) == 1


def test_clear_only_target_section_changes(tmp_path: Path) -> None:
    other_before = {
        "background_media": "video",
        "video": "shopify://files/v.mp4",
        "background_overlay_pct": 25,
    }
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
        },
        other_zone_index=other_before,
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok

    index_path = resolve_active_index_path(tmp_path)
    assert index_path is not None
    data = json.loads(index_path.read_text(encoding="utf-8"))
    target = data["sections"][zone.section_key]["settings"]
    assert target["background_media"] == "none"
    assert target["background_image"] == ""
    assert target["video"] == ""
    assert target["background_overlay_pct"] == 0
    other = data["sections"][_OTHER_ZONE.section_key]["settings"]
    assert other == other_before


def test_clear_only_four_fields_changed(tmp_path: Path) -> None:
    readiness = _clear_readiness(
        tmp_path,
        {
            "background_media": "video",
            "video": "shopify://files/v.mp4",
            "background_image": "legacy.jpg",
            "background_overlay_pct": 15,
            "title": "keep-me",
        },
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    assert set(result.changed_fields) == {
        "background_media",
        "background_image",
        "video",
        "background_overlay_pct",
    }

    index_path = resolve_active_index_path(tmp_path)
    assert index_path is not None
    settings = json.loads(index_path.read_text(encoding="utf-8"))["sections"][
        zone.section_key
    ]["settings"]
    assert settings["title"] == "keep-me"


def test_manifest_and_settings_untouched(tmp_path: Path) -> None:
    readiness = _clear_readiness(
        tmp_path,
        {"background_media": "image", "background_image": "shopify://shop_images/x.jpg"},
    )
    manifest_path = tmp_path / "data" / "variants" / "manifest.json"
    manifest_before = manifest_path.read_text(encoding="utf-8")
    settings_path = tmp_path / "data" / "settings.json"
    settings_path.write_text('{"foo": 1}', encoding="utf-8")
    settings_before = settings_path.read_text(encoding="utf-8")

    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    clear_section_background_with_backup(draft, tmp_path, readiness=readiness)

    assert manifest_path.read_text(encoding="utf-8") == manifest_before
    assert settings_path.read_text(encoding="utf-8") == settings_before


def test_reject_when_not_clear_ready_no_backup(tmp_path: Path) -> None:
    _write_fixture(
        tmp_path,
        zone_index={
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
        },
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=False)
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert not result.ok
    assert not list((tmp_path / "data" / "backups").glob("index-*.json"))


def test_missing_index_error_no_write(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = SaveReadiness(
        ready=True,
        operation="clear",
        block_reason=None,
        requires_confirm=True,
        summary="ok",
        status_label="gotowe",
    )
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert not result.ok
    assert "index.json" in result.message.lower()


def test_invalid_json_error_no_write(tmp_path: Path) -> None:
    _write_fixture(tmp_path, index_raw="{bad-json")
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = SaveReadiness(
        ready=True,
        operation="clear",
        block_reason=None,
        requires_confirm=True,
        summary="ok",
        status_label="gotowe",
    )
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert not result.ok
    assert "json" in result.message.lower()
    assert not list((tmp_path / "data" / "backups").glob("index-*.json"))


def test_post_write_reparse_ok(tmp_path: Path) -> None:
    readiness = _clear_readiness(
        tmp_path,
        {"background_media": "image", "background_image": "shopify://shop_images/x.jpg"},
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    index_path = resolve_active_index_path(tmp_path)
    assert index_path is not None
    json.loads(index_path.read_text(encoding="utf-8"))


def test_header_preserved(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    header = "/* shopify */\n"
    body = json.dumps(
        {
            "sections": {
                zone.section_key: {
                    "settings": {
                        "background_media": "image",
                        "background_image": "shopify://shop_images/x.jpg",
                    }
                }
            }
        }
    )
    _write_fixture(tmp_path, index_raw=f"{header}{body}")
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    index_path = resolve_active_index_path(tmp_path)
    assert index_path is not None
    raw = index_path.read_text(encoding="utf-8")
    assert raw.startswith("/* shopify */")
    assert split_json_header(raw) == "/* shopify */"


def test_save_write_result_no_sensitive_paths(tmp_path: Path) -> None:
    readiness = _clear_readiness(
        tmp_path,
        {"background_media": "image", "background_image": "shopify://shop_images/secret.jpg"},
    )
    zone = STRONAGLOWNA_SECTION_BGS[0]
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert isinstance(result, SaveWriteResult)
    assert "shopify://" not in result.message
    assert all("shopify://" not in field for field in result.changed_fields)
    assert result.backup_filename is not None
    assert str(tmp_path) not in (result.backup_filename or "")
    assert "\\" not in (result.backup_filename or "")
    assert "/" not in (result.backup_filename or "")


def test_assert_bounded_diff_rejects_extra_fields() -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    before = {
        "sections": {
            zone.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "x.jpg",
                    "title": "keep",
                }
            }
        }
    }
    after = json.loads(json.dumps(before))
    after["sections"][zone.section_key]["settings"]["title"] = "changed"
    try:
        assert_bounded_diff(before, after, zone.section_key)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "title" in str(exc)


def test_apply_clear_patch_mutates_template() -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    template = {"sections": {zone.section_key: {"settings": {"background_media": "image"}}}}
    apply_clear_patch(template, zone.section_key)
    settings = template["sections"][zone.section_key]["settings"]
    assert settings["background_media"] == "none"
    assert settings["background_image"] == ""
    assert settings["video"] == ""
    assert settings["background_overlay_pct"] == 0


def test_backup_index_json_creates_file(tmp_path: Path) -> None:
    index_path = tmp_path / "data" / "variants" / "v1" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text("{}", encoding="utf-8")
    backup_path = backup_index_json(index_path, tmp_path)
    assert backup_path.is_file()
    assert backup_path.parent.name == "backups"


def test_write_index_json_preserving_header(tmp_path: Path) -> None:
    path = tmp_path / "index.json"
    write_index_json_preserving_header(path, {"a": 1}, "/* hdr */\n")
    assert path.read_text(encoding="utf-8").startswith("/* hdr */")


def test_no_komponenty_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_writer_ast_guardrails() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" in text
    assert "copy2" in text
    assert "service.py" not in text
    assert "glob(" not in text
    assert "filedialog" not in text
    assert "requests" not in text
    assert "shopify" not in text.lower()


def test_panel_has_save_local_wiring() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "SAVE_LOCAL_LABEL" in text
    assert "_save_local_button" in text
    assert "_save_local_button" in text
    assert "_on_save_local_clear" in text
    assert "clear_section_background_with_backup" in text
    assert "messagebox.askyesno" in text
    assert "_refresh_readonly_sections" in text
    save_block = text.split("def _on_save_local_clear")[1].split("\n    def ")[0]
    assert "clear_section_background_with_backup" in save_block
    assert "write_text" not in save_block


def test_panel_save_button_only_for_clear_ready() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    update_block = text.split("def _update_save_local_button")[1].split("\n    def ")[0]
    assert 'readiness.operation == "clear"' in update_block
    assert "_clear_plan_intent" in update_block
    assert "pack_forget" in update_block
