"""Testy save readiness + ref policy — Studio Preview (F5.4b0)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_draft_state import BackgroundDraftState
from giclee_app.studio.background_save_readiness import (
    CLEAR_PLAN_CHECKBOX,
    F54B0_DISCLAIMER,
    F54B1_FUTURE_NOTE,
    READINESS_SECTION_LABEL,
    evaluate_save_readiness,
    format_readiness_block,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_save_readiness.py"
)
_PANEL_PATH = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "background_panel.py"


def _write_fixture(tmp_path: Path, zone_index: dict) -> Path:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": [{"id": "v1", "label": "T"}]}),
        encoding="utf-8",
    )
    index = {"sections": {zone.section_key: {"settings": zone_index}}}
    (variants_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")
    return tmp_path


def test_kind_change_without_ref_not_ready(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(
        tmp_path,
        {
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert not readiness.ready
    assert readiness.operation == "set_with_ref"
    assert readiness.block_reason is not None
    assert "assetu" in readiness.block_reason.lower()


def test_brak_to_image_without_ref_not_ready(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[1]
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text(
        json.dumps({"sections": {zone.section_key: {"settings": {"background_media": "none"}}}}),
        encoding="utf-8",
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert not readiness.ready
    assert "brak" in readiness.block_reason.lower() or "assetu" in readiness.block_reason.lower()


def test_same_kind_existing_background_ready_noop(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[2]
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text(
        json.dumps(
            {
                "sections": {
                    zone.section_key: {
                        "settings": {
                            "background_media": "video",
                            "video": "shopify://files/videos/a.mp4",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert readiness.ready
    assert readiness.operation == "noop"
    assert readiness.status_label == "bez zmian"
    assert "nie jest potrzebny" in readiness.summary


def test_video_collage_rejected(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(tmp_path, {})
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video_collage")
    readiness = evaluate_save_readiness(draft, tmp_path)
    assert not readiness.ready
    assert "section_background" in (readiness.block_reason or "")


def test_clear_intent_ready_when_background_exists(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(
        tmp_path,
        {
            "background_media": "image",
            "background_image": "shopify://shop_images/x.jpg",
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    assert readiness.ready
    assert readiness.operation == "clear"
    assert readiness.requires_confirm
    assert "F5.4b1" in readiness.summary


def test_clear_intent_blocked_when_already_brak(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(tmp_path, {"background_media": "none"})
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="image")
    readiness = evaluate_save_readiness(draft, tmp_path, clear_intent=True)
    assert not readiness.ready
    assert "wyczyszczenia" in (readiness.block_reason or "").lower()


def test_readiness_summary_no_sensitive_data(tmp_path: Path) -> None:
    zone = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(
        tmp_path,
        {
            "background_media": "image",
            "background_image": "shopify://shop_images/secret.jpg",
        },
    )
    draft = BackgroundDraftState(zone_field_id=zone.field_id, asset_kind="video")
    block = format_readiness_block(evaluate_save_readiness(draft, tmp_path).summary)
    assert READINESS_SECTION_LABEL in block
    assert F54B0_DISCLAIMER in block
    assert F54B1_FUTURE_NOTE in block
    assert "shopify://" not in block
    assert "secret" not in block
    assert "http" not in block.lower()
    assert str(tmp_path) not in block


def test_no_komponenty_imports() -> None:
    tree = ast.parse(_MODULE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_no_write_or_forbidden_apis() -> None:
    text = _MODULE_PATH.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "service.py" not in text
    assert "homepage_variants" not in text
    assert "load_manifest" not in text
    assert "import shopify" not in text.lower()
    assert "from shopify" not in text.lower()
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "filedialog" not in text
    assert "requests" not in text


def test_panel_has_readiness_and_save_local_button() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    assert "evaluate_save_readiness" in text
    assert "format_readiness_block" in text
    assert "F54B0_DISCLAIMER" in text
    assert "CLEAR_PLAN_CHECKBOX" in text
    assert "SAVE_LOCAL_LABEL" in text
    assert "clear_section_background_with_backup" in text
    assert 'text="Zapisz"' not in text
    assert "Zastosuj" not in text


def test_format_readiness_block_clear_ready_hint() -> None:
    block = format_readiness_block("Status: gotowe", clear_ready=True)
    assert "Zapisz lokalnie" in block
    block_no = format_readiness_block("Status: gotowe", clear_ready=False)
    assert "przycisk" not in block_no.lower()


def test_panel_dry_run_includes_readiness() -> None:
    text = _PANEL_PATH.read_text(encoding="utf-8")
    save_block = text.split("def _run_save_dry_run")[1].split("\n    def ")[0]
    assert "evaluate_save_readiness" in save_block
    assert "_compose_save_plan_text" in save_block
    assert "write_text" not in save_block
