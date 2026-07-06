"""Testy bounded asset catalog — Studio Preview (F5.4d)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_asset_catalog import (
    ASSET_SELECTION_SECTION_TITLE,
    build_background_asset_catalog,
    filter_by_kind,
    filter_entries_for_draft_kind,
    ref_to_display_label,
    resolve_selected_asset_ref,
    validate_selected_asset_id,
)
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "giclee_app"
    / "studio"
    / "background_asset_catalog.py"
)


def _write_fixture(tmp_path: Path, sections: dict) -> Path:
    variant_id = "v1"
    variants_dir = tmp_path / "data" / "variants" / variant_id
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": variant_id, "variants": [{"id": variant_id, "label": "T"}]}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text(json.dumps({"sections": sections}), encoding="utf-8")
    return tmp_path


def test_catalog_collects_image_and_video_refs(tmp_path: Path) -> None:
    z0, z1 = STRONAGLOWNA_SECTION_BGS[0], STRONAGLOWNA_SECTION_BGS[1]
    _write_fixture(
        tmp_path,
        {
            z0.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/a.jpg",
                }
            },
            z1.section_key: {
                "settings": {
                    "background_media": "video",
                    "video": "shopify://files/videos/b.mp4",
                }
            },
        },
    )
    catalog = build_background_asset_catalog(tmp_path)
    assert len(catalog.entries) == 2
    kinds = {entry.kind for entry in catalog.entries}
    assert kinds == {"image", "video"}


def test_catalog_dedupes_same_ref(tmp_path: Path) -> None:
    z0, z1 = STRONAGLOWNA_SECTION_BGS[0], STRONAGLOWNA_SECTION_BGS[1]
    ref = "shopify://shop_images/shared.jpg"
    _write_fixture(
        tmp_path,
        {
            z0.section_key: {
                "settings": {"background_media": "image", "background_image": ref}
            },
            z1.section_key: {
                "settings": {"background_media": "image", "background_image": ref}
            },
        },
    )
    catalog = build_background_asset_catalog(tmp_path)
    assert len(catalog.entries) == 1
    assert catalog.entries[0].display_label == "shared.jpg"


def test_filter_by_kind(tmp_path: Path) -> None:
    z0, z1 = STRONAGLOWNA_SECTION_BGS[0], STRONAGLOWNA_SECTION_BGS[1]
    _write_fixture(
        tmp_path,
        {
            z0.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/a.jpg",
                }
            },
            z1.section_key: {
                "settings": {
                    "background_media": "video",
                    "video": "shopify://files/videos/b.mp4",
                }
            },
        },
    )
    catalog = build_background_asset_catalog(tmp_path)
    images = filter_by_kind(catalog, "image")
    videos = filter_by_kind(catalog, "video")
    assert len(images) == 1
    assert len(videos) == 1


def test_filter_entries_for_draft_kind(tmp_path: Path) -> None:
    z0, z1 = STRONAGLOWNA_SECTION_BGS[0], STRONAGLOWNA_SECTION_BGS[1]
    _write_fixture(
        tmp_path,
        {
            z0.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/a.jpg",
                }
            },
            z1.section_key: {
                "settings": {
                    "background_media": "video",
                    "video": "shopify://files/videos/b.mp4",
                }
            },
        },
    )
    catalog = build_background_asset_catalog(tmp_path)
    assert len(filter_entries_for_draft_kind(catalog, "image")) == 1
    assert len(filter_entries_for_draft_kind(catalog, "video")) == 1
    assert filter_entries_for_draft_kind(catalog, "video_collage") == ()


def test_validate_and_resolve_selected_asset_id(tmp_path: Path) -> None:
    z0 = STRONAGLOWNA_SECTION_BGS[0]
    _write_fixture(
        tmp_path,
        {
            z0.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/a.jpg",
                }
            },
        },
    )
    catalog = build_background_asset_catalog(tmp_path)
    asset_id = catalog.entries[0].asset_id
    assert validate_selected_asset_id(asset_id, catalog, asset_kind="image")
    assert not validate_selected_asset_id(asset_id, catalog, asset_kind="video")
    assert not validate_selected_asset_id("img:99", catalog, asset_kind="image")
    assert resolve_selected_asset_ref(catalog, asset_id) == "shopify://shop_images/a.jpg"


def test_ref_to_display_label_strips_shopify_prefix() -> None:
    assert ref_to_display_label("shopify://shop_images/foo.webp") == "foo.webp"
    assert ref_to_display_label("shopify://files/videos/bar.mp4") == "bar.mp4"


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
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "filedialog" not in text
    assert "requests" not in text


def test_section_title_constant() -> None:
    assert ASSET_SELECTION_SECTION_TITLE == "Wybór assetu"
