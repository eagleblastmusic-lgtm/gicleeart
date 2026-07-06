"""Testy read-only asset browser shell (F5.1 / F5.1b)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_asset_shell import asset_library_rows, asset_library_section
from giclee_app.studio.background_asset_types import asset_type_labels_pl
from giclee_app.studio.background_capabilities import capability_for
from giclee_app.studio.background_state import STRONAGLOWNA_SECTION_BGS
from giclee_app.ui.background_panel import panel_rows

_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"
_MODULE_PATHS = (
    _ROOT / "background_asset_types.py",
    _ROOT / "background_asset_shell.py",
)


def test_stronaglowna_fallback_without_manifest(tmp_path: Path) -> None:
    section = asset_library_section("stronaglowna", tmp_path)
    assert section is not None
    assert section.title == "Biblioteka / Assety"
    assert "F5.1b · read-only" in section.body
    assert "Nie udało się odczytać przypisań" in section.body
    assert "shopify://" not in section.body
    assert "http" not in section.body.lower()


def test_stronaglowna_valid_manifest_and_index(tmp_path: Path) -> None:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps(
            {
                "active": "v1",
                "variants": [{"id": "v1", "label": "Wariant testowy"}],
            }
        ),
        encoding="utf-8",
    )
    zone_a = STRONAGLOWNA_SECTION_BGS[0]
    zone_b = STRONAGLOWNA_SECTION_BGS[1]
    index = {
        "sections": {
            zone_a.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/hero.jpg",
                }
            },
            zone_b.section_key: {
                "settings": {
                    "background_media": "video",
                    "video": "shopify://files/videos/clip.mp4",
                }
            },
        }
    }
    (variants_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    body = asset_library_rows("stronaglowna", tmp_path)[0][1]
    assert "Aktywny wariant: v1 · Wariant testowy" in body
    assert "Przypisania section_background (5):" in body
    assert f"· {zone_a.field_id} ({zone_a.label}): obraz" in body
    assert f"· {zone_b.field_id} ({zone_b.label}): wideo" in body
    assert "shopify://" not in body
    for label in asset_type_labels_pl():
        assert label in body


def test_stronaglowna_invalid_index_json(tmp_path: Path) -> None:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    (variants_dir / "index.json").write_text("{bad-json", encoding="utf-8")
    body = asset_library_rows("stronaglowna", tmp_path)[0][1]
    assert "Nie udało się odczytać przypisań" in body


def test_tldobio_no_asset_library_section() -> None:
    assert asset_library_section("tldobio") is None
    assert asset_library_rows("tldobio", Path(".")) == ()


def test_panel_rows_stronaglowna_includes_biblioteka(tmp_path: Path) -> None:
    cap = capability_for("stronaglowna")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Strona główna",
            folder_name="stronaglowna",
            package_path=tmp_path,
        )
    )
    assert "Biblioteka / Assety" in rows
    assert "F5.1b · read-only" in rows["Biblioteka / Assety"]
    assert "kolaż wideo" in rows["Biblioteka / Assety"]


def test_panel_rows_tldobio_no_biblioteka(tmp_path: Path) -> None:
    cap = capability_for("tldobio")
    assert cap is not None
    rows = dict(
        panel_rows(
            cap,
            component_name="Tło do Bio",
            folder_name="tldobio",
            package_path=tmp_path,
        )
    )
    assert "Biblioteka / Assety" not in rows


def test_no_komponenty_imports() -> None:
    for path in _MODULE_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("Komponenty")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("Komponenty")


def test_no_write_text_or_glob() -> None:
    for path in _MODULE_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "write_text" not in text
        assert "write_bytes" not in text
        assert "glob(" not in text
        assert "rglob(" not in text
        assert "is_file(" not in text
