"""Testy save contract + dry-run — Studio Preview (F5.4a)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_contract import (
    DRY_RUN_BADGE,
    F54A_DISCLAIMER,
    VIDEO_COLLAGE_SCOPE_ERROR,
    build_background_save_dry_run,
    format_dry_run_summary,
    save_plan_enabled_for_folder,
    validate_background_save_request,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_save_contract.py"
)
_PANEL_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"


def _write_stronaglowna_fixture(
    tmp_path: Path,
    *,
    variant_id: str = "v1",
    variant_label: str = "Wariant testowy",
    index: dict | None = None,
    index_raw: str | None = None,
) -> Path:
    variants_dir = tmp_path / "data" / "variants" / variant_id
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps(
            {
                "active": variant_id,
                "variants": [{"id": variant_id, "label": variant_label}],
            }
        ),
        encoding="utf-8",
    )
    if index_raw is not None:
        (variants_dir / "index.json").write_text(index_raw, encoding="utf-8")
    elif index is not None:
        (variants_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return tmp_path


def test_empty_draft_validation_error(tmp_path: Path) -> None:
    _write_stronaglowna_fixture(tmp_path, index={"sections": {}})
    draft = BackgroundDraftState()
    result = validate_background_save_request(draft, tmp_path)
    assert not result.ok
    assert any("pusty" in err.lower() for err in result.errors)


def test_invalid_zone_validation_error(tmp_path: Path) -> None:
    _write_stronaglowna_fixture(tmp_path, index={"sections": {}})
    draft = BackgroundDraftState(zone_field_id="unknown_zone", asset_kind="image")
    result = validate_background_save_request(draft, tmp_path)
    assert not result.ok
    assert any("Nieznana strefa" in err for err in result.errors)


def test_video_collage_rejected(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_stronaglowna_fixture(
        tmp_path,
        index={"sections": {zone.section_key: {"settings": {}}}},
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video_collage")
    result = validate_background_save_request(draft, tmp_path)
    assert not result.ok
    assert VIDEO_COLLAGE_SCOPE_ERROR in result.errors


def test_missing_manifest_error(tmp_path: Path) -> None:
    draft = BackgroundDraftState(
        zone_field_id=STRONAGLOWNA_SECTION_BGS[0].field_id,
        asset_kind="image",
    )
    result = validate_background_save_request(draft, tmp_path)
    assert not result.ok
    assert any("manifest" in err.lower() for err in result.errors)


def test_invalid_index_json_error(tmp_path: Path) -> None:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text("{bad-json", encoding="utf-8")
    draft = BackgroundDraftState(
        zone_field_id=STRONAGLOWNA_SECTION_BGS[0].field_id,
        asset_kind="image",
    )
    result = validate_background_save_request(draft, tmp_path)
    assert not result.ok
    assert any("index.json" in err for err in result.errors)


def test_valid_draft_image_dry_run_ok(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_stronaglowna_fixture(
        tmp_path,
        index={
            "sections": {
                zone.section_key: {
                    "settings": {
                        "background_media": "image",
                        "background_image": "shopify://shop_images/hero.jpg",
                    }
                }
            }
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    dry_run = build_background_save_dry_run(draft, tmp_path)
    assert dry_run.ok
    assert dry_run.zone_field_id == zone.field_id
    assert dry_run.current_status == "obraz"
    assert dry_run.target_kind_pl == "wideo"
    assert dry_run.change_summary == "obraz → wideo"
    assert not dry_run.writable


def test_dry_run_brak_to_obraz(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[1]
    _write_stronaglowna_fixture(
        tmp_path,
        index={"sections": {zone.section_key: {"settings": {"background_media": "none"}}}},
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    dry_run = build_background_save_dry_run(draft, tmp_path)
    assert dry_run.ok
    assert dry_run.current_status == "brak"
    assert dry_run.target_kind_pl == "obraz"
    assert dry_run.change_summary == "brak → obraz"


def test_dry_run_wideo_no_op(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[2]
    _write_stronaglowna_fixture(
        tmp_path,
        index={
            "sections": {
                zone.section_key: {
                    "settings": {
                        "background_media": "video",
                        "video": "shopify://files/videos/clip.mp4",
                    }
                }
            }
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    dry_run = build_background_save_dry_run(draft, tmp_path)
    assert dry_run.ok
    assert dry_run.type_unchanged
    assert dry_run.writable
    assert "bez zmian" in format_dry_run_summary(dry_run)


def test_dry_run_summary_no_sensitive_data(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_stronaglowna_fixture(
        tmp_path,
        index={
            "sections": {
                zone.section_key: {
                    "settings": {
                        "background_media": "image",
                        "background_image": "shopify://shop_images/secret.jpg",
                    }
                }
            }
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    summary = format_dry_run_summary(build_background_save_dry_run(draft, tmp_path))
    assert DRY_RUN_BADGE in summary
    assert F54A_DISCLAIMER in summary
    assert "shopify://" not in summary
    assert "secret" not in summary
    assert "http" not in summary.lower()
    assert str(tmp_path) not in summary
    assert "background_image" in summary  # nazwa pola OK, nie wartość ref


def test_format_dry_run_error_includes_badge(tmp_path: Path) -> None:
    draft = BackgroundDraftState()
    summary = format_dry_run_summary(build_background_save_dry_run(draft, tmp_path))
    assert DRY_RUN_BADGE in summary
    assert F54A_DISCLAIMER in summary
    assert any("Błąd:" in line for line in summary.splitlines())


def test_save_plan_enabled_only_stronaglowna() -> None:
    assert save_plan_enabled_for_folder("stronaglowna")
    assert not save_plan_enabled_for_folder("tldobio")


def test_no_komponenty_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_no_write_or_forbidden_apis_in_contract_module() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "service.py" not in text
    assert "homepage_variants" not in text
    assert "load_manifest" not in text
    assert "shopify" not in text.lower()
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "filedialog" not in text
    assert "requests" not in text


def test_panel_has_dry_run_and_save_local_button() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "CHECK_SAVE_LABEL" in text
    assert "DRY_RUN_BADGE" in text
    assert "_render_save_plan_section" in text
    assert "save_plan_enabled_for_folder" in text
    assert "SAVE_LOCAL_LABEL" in text
    assert 'text="Zapisz"' not in text
    assert "Zastosuj" not in text


def test_panel_no_write_in_save_plan_handler() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    save_block = text.split("def _run_save_dry_run")[1].split("\n    def ")[0]
    assert "write_text" not in save_block
    assert "build_background_save_dry_run" in save_block
    assert "format_dry_run_summary" in save_block
