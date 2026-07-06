"""Testy session-only undo restore — Studio Preview (F5.4c1)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_readiness import (
    UNDO_LAST_SAVE_LABEL,
    UNDO_RESTORE_STATUS,
    evaluate_save_readiness,
)
from giclee_app.studio.background_save_writer import (
    RestoreWriteResult,
    apply_restore_patch,
    assert_bounded_restore_diff,
    build_restore_patch,
    clear_section_background_with_backup,
    restore_section_background_from_backup,
    validate_backup_path,
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
_ZONE = STRONAGLOWNA_SECTION_BGS[0]

_ORIGINAL_SETTINGS = {
    "background_media": "image",
    "background_image": "shopify://shop_images/x.jpg",
    "video": "",
    "background_overlay_pct": 35,
    "title": "keep-me",
}


def _write_fixture(
    tmp_path: Path,
    *,
    zone_index: dict | None = None,
    other_zone_index: dict | None = None,
    variant_id: str = "v1",
) -> Path:
    variants_dir = tmp_path / "data" / "variants" / variant_id
    variants_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": variant_id, "variants": [{"id": variant_id, "label": "T"}]}),
        encoding="utf-8",
    )
    sections: dict = {}
    if zone_index is not None:
        sections[_ZONE.section_key] = {"settings": zone_index}
    if other_zone_index is not None:
        sections[_OTHER_ZONE.section_key] = {"settings": other_zone_index}
    (variants_dir / "index.json").write_text(json.dumps({"sections": sections}), encoding="utf-8")
    return tmp_path


def _clear_and_get_backup(tmp_path: Path) -> tuple[str, dict]:
    draft = BackgroundDraftState(zone_field_id=_ZONE.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok
    assert result.backup_filename
    index = json.loads(
        (tmp_path / "data" / "variants" / "v1" / "index.json").read_text(encoding="utf-8")
    )
    return result.backup_filename, index


def test_build_restore_patch_four_fields() -> None:
    patch = build_restore_patch(_ORIGINAL_SETTINGS)
    assert set(patch.keys()) == {
        "background_media",
        "background_image",
        "video",
        "background_overlay_pct",
    }
    assert patch["background_media"] == "image"


def test_restore_one_section_only(tmp_path: Path) -> None:
    other = {
        "background_media": "video",
        "video": "shopify://files/v.mp4",
        "background_overlay_pct": 20,
    }
    _write_fixture(
        tmp_path,
        zone_index=dict(_ORIGINAL_SETTINGS),
        other_zone_index=other,
    )
    backup_name, _ = _clear_and_get_backup(tmp_path)
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=backup_name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
        expected_variant_id="v1",
    )
    assert result.ok
    data = json.loads(
        (tmp_path / "data" / "variants" / "v1" / "index.json").read_text(encoding="utf-8")
    )
    target = data["sections"][_ZONE.section_key]["settings"]
    assert target["background_media"] == "image"
    assert target["background_image"] == "shopify://shop_images/x.jpg"
    assert target["title"] == "keep-me"
    assert data["sections"][_OTHER_ZONE.section_key]["settings"] == other


def test_restore_only_four_fields(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index=dict(_ORIGINAL_SETTINGS))
    backup_name, _ = _clear_and_get_backup(tmp_path)
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=backup_name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert result.ok
    assert set(result.restored_fields) == {
        "background_media",
        "background_image",
        "video",
        "background_overlay_pct",
    }


def test_validate_backup_path_ok(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index=dict(_ORIGINAL_SETTINGS))
    backup_name, _ = _clear_and_get_backup(tmp_path)
    path = validate_backup_path(tmp_path, backup_name)
    assert path is not None
    assert path.name == backup_name


def test_reject_parent_traversal(tmp_path: Path) -> None:
    assert validate_backup_path(tmp_path, "../index-20260706-120000.json") is None


def test_reject_path_separator(tmp_path: Path) -> None:
    assert validate_backup_path(tmp_path, "backups/index-20260706-120000.json") is None
    assert validate_backup_path(tmp_path, r"backups\index-20260706-120000.json") is None


def test_reject_wrong_pattern(tmp_path: Path) -> None:
    backup_dir = tmp_path / "data" / "backups"
    backup_dir.mkdir(parents=True)
    (backup_dir / "wrong-name.json").write_text("{}", encoding="utf-8")
    assert validate_backup_path(tmp_path, "wrong-name.json") is None


def test_reject_settings_backup(tmp_path: Path) -> None:
    backup_dir = tmp_path / "data" / "backups"
    backup_dir.mkdir(parents=True)
    name = "settings-20260706-120000.json"
    (backup_dir / name).write_text("{}", encoding="utf-8")
    assert validate_backup_path(tmp_path, name) is None


def test_reject_backup_outside_dir(tmp_path: Path) -> None:
    outside = tmp_path / "outside-index-20260706-120000.json"
    outside.write_text("{}", encoding="utf-8")
    assert validate_backup_path(tmp_path, outside.name) is None


def test_invalid_backup_json_no_write(tmp_path: Path) -> None:
    backup_dir = tmp_path / "data" / "backups"
    backup_dir.mkdir(parents=True)
    name = "index-20260706-120000.json"
    (backup_dir / name).write_text("{bad", encoding="utf-8")
    _write_fixture(tmp_path, zone_index={"background_media": "none"})
    before = (tmp_path / "data" / "variants" / "v1" / "index.json").read_text(encoding="utf-8")
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert not result.ok
    after = (tmp_path / "data" / "variants" / "v1" / "index.json").read_text(encoding="utf-8")
    assert before == after


def test_missing_section_in_backup_no_write(tmp_path: Path) -> None:
    backup_dir = tmp_path / "data" / "backups"
    backup_dir.mkdir(parents=True)
    name = "index-20260706-120000.json"
    (backup_dir / name).write_text(json.dumps({"sections": {}}), encoding="utf-8")
    _write_fixture(tmp_path, zone_index={"background_media": "none"})
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert not result.ok


def test_variant_changed_rejected(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index=dict(_ORIGINAL_SETTINGS))
    backup_name, _ = _clear_and_get_backup(tmp_path)
    manifest = json.loads(
        (tmp_path / "data" / "variants" / "manifest.json").read_text(encoding="utf-8")
    )
    manifest["active"] = "v2"
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    (tmp_path / "data" / "variants" / "v2").mkdir(parents=True)
    (tmp_path / "data" / "variants" / "v2" / "index.json").write_text(
        json.dumps({"sections": {_ZONE.section_key: {"settings": {"background_media": "none"}}}}),
        encoding="utf-8",
    )
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=backup_name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
        expected_variant_id="v1",
    )
    assert not result.ok
    assert "wariant" in result.message.lower()


def test_header_preserved_on_restore(tmp_path: Path) -> None:
    header = "/* shopify */\n"
    body = json.dumps({"sections": {_ZONE.section_key: {"settings": dict(_ORIGINAL_SETTINGS)}}})
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text(f"{header}{body}", encoding="utf-8")
    draft = BackgroundDraftState(zone_field_id=_ZONE.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    result = clear_section_background_with_backup(draft, tmp_path, readiness=readiness)
    assert result.ok and result.backup_filename
    restore = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=result.backup_filename,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert restore.ok
    raw = (variants_dir / "index.json").read_text(encoding="utf-8")
    assert raw.startswith("/* shopify */")


def test_post_write_json_valid(tmp_path: Path) -> None:
    _write_fixture(tmp_path, zone_index=dict(_ORIGINAL_SETTINGS))
    backup_name, _ = _clear_and_get_backup(tmp_path)
    result = restore_section_background_from_backup(
        package_path=tmp_path,
        backup_filename=backup_name,
        section_key=_ZONE.section_key,
        zone_field_id=_ZONE.field_id,
        zone_label=_ZONE.label,
    )
    assert result.ok
    json.loads(
        (tmp_path / "data" / "variants" / "v1" / "index.json").read_text(encoding="utf-8")
    )


def test_assert_bounded_restore_diff_rejects_extra_fields() -> None:
    before = {
        "sections": {
            _ZONE.section_key: {
                "settings": {
                    "background_media": "none",
                    "background_image": "",
                    "video": "",
                    "background_overlay_pct": 0,
                    "title": "keep",
                }
            }
        }
    }
    after = json.loads(json.dumps(before))
    after["sections"][_ZONE.section_key]["settings"]["title"] = "changed"
    try:
        assert_bounded_restore_diff(before, after, _ZONE.section_key)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "title" in str(exc)


def test_apply_restore_patch_mutates_only_four_fields() -> None:
    template = {
        "sections": {
            _ZONE.section_key: {
                "settings": {
                    "background_media": "none",
                    "background_image": "",
                    "video": "",
                    "background_overlay_pct": 0,
                    "title": "keep",
                }
            }
        }
    }
    apply_restore_patch(template, _ZONE.section_key, dict(_ORIGINAL_SETTINGS))
    settings = template["sections"][_ZONE.section_key]["settings"]
    assert settings["background_media"] == "image"
    assert settings["title"] == "keep"


def test_no_full_index_restore_function() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "shutil.copy2(backup_path, index_path)" not in text
    assert "restore_backup" not in text


def test_writer_ast_guardrails() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "shopify" not in text.lower()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_panel_undo_wiring() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "UNDO_LAST_SAVE_LABEL" in text
    assert "Cofnij ostatni zapis" in text
    assert "_on_undo_last_clear" in text
    assert "restore_section_background_from_backup" in text
    assert "_last_successful_clear" in text
    assert "_clear_session_undo" in text
    assert "UNDO_RESTORE_STATUS" in text
    undo_block = text.split("def _on_undo_last_clear")[1].split("\n    def ")[0]
    assert "write_text" not in undo_block
    hide_block = text.split("def on_hide")[1].split("\n    def ")[0]
    assert "_clear_session_undo" in hide_block


def test_panel_undo_hidden_by_default() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "_undo_button.pack_forget()" in text
    assert "_set_session_undo" in text


def test_restore_result_type() -> None:
    assert isinstance(
        RestoreWriteResult(
            ok=False,
            message="",
            backup_filename="index-20260706-120000.json",
            zone_field_id="x",
            zone_label="y",
            section_key="z",
            restored_fields=(),
        ),
        RestoreWriteResult,
    )
    assert UNDO_LAST_SAVE_LABEL == "Cofnij ostatni zapis"
    assert UNDO_RESTORE_STATUS == "przywrócono lokalnie · bez Shopify"
