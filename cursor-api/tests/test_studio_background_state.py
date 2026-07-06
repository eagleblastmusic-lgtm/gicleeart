"""Testy read-only background state summary (F4.3b)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.background_state import (
    STRONAGLOWNA_SECTION_BGS,
    summarize_background_state,
)

_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "background_state.py"


def test_tldobio_missing_collections_file(tmp_path: Path) -> None:
    summary = summarize_background_state("tldobio", tmp_path)
    assert "Brak lokalnego cache" in summary.text
    assert "http" not in summary.text.lower()
    assert "shopify" not in summary.text.lower()


def test_tldobio_valid_collections_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "collections.json").write_text(
        json.dumps(
            {
                "backgrounds": {
                    "a": {"url": "https://cdn.example/a.jpg"},
                    "b": {"url": ""},
                    "c": {"url": "https://cdn.example/c.jpg"},
                }
            }
        ),
        encoding="utf-8",
    )
    summary = summarize_background_state("tldobio", tmp_path)
    assert "3 kolekcji" in summary.text
    assert "2 z zapisanym tłem" in summary.text
    assert "https://" not in summary.text
    assert "cdn.example" not in summary.text


def test_tldobio_invalid_json(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "collections.json").write_text("{not-json", encoding="utf-8")
    summary = summarize_background_state("tldobio", tmp_path)
    assert "nieczytelny" in summary.text


def test_stronaglowna_missing_manifest_and_index(tmp_path: Path) -> None:
    summary = summarize_background_state("stronaglowna", tmp_path)
    assert "Aktywny wariant: nieznany" in summary.text
    assert "Nie udało się odczytać lokalnego stanu wariantu" in summary.text
    assert len(STRONAGLOWNA_SECTION_BGS) == 5
    for zone in STRONAGLOWNA_SECTION_BGS:
        assert zone.field_id in summary.text


def test_stronaglowna_manifest_and_minimal_index(tmp_path: Path) -> None:
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
    zone = STRONAGLOWNA_SECTION_BGS[0]
    index = {
        "sections": {
            zone.section_key: {
                "settings": {
                    "background_media": "image",
                    "background_image": "shopify://shop_images/hero.jpg",
                }
            }
        }
    }
    (variants_dir / "index.json").write_text(json.dumps(index), encoding="utf-8")

    summary = summarize_background_state("stronaglowna", tmp_path)
    assert "Aktywny wariant: v1 · Wariant testowy" in summary.text
    assert "Ustawione tło: 1/5" in summary.text
    assert f"· {zone.field_id}" in summary.text
    assert ": obraz" in summary.text
    assert "shopify://" not in summary.text


def test_stronaglowna_index_with_shopify_comment_header(tmp_path: Path) -> None:
    variants_dir = tmp_path / "data" / "variants" / "v1"
    variants_dir.mkdir(parents=True)
    (tmp_path / "data" / "variants" / "manifest.json").write_text(
        json.dumps({"active": "v1", "variants": []}),
        encoding="utf-8",
    )
    zone = STRONAGLOWNA_SECTION_BGS[1]
    payload = {
        "sections": {
            zone.section_key: {
                "settings": {
                    "background_media": "video",
                    "video": "shopify://files/videos/clip.mp4",
                }
            }
        }
    }
    (variants_dir / "index.json").write_text(
        f"/* shopify export */\n{json.dumps(payload)}",
        encoding="utf-8",
    )
    summary = summarize_background_state("stronaglowna", tmp_path)
    assert f"· {zone.field_id}" in summary.text
    assert ": wideo" in summary.text


def test_background_state_no_komponenty_imports() -> None:
    tree = ast.parse(_ROOT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("Komponenty")
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not node.module.startswith("Komponenty")


def test_background_state_no_write_text() -> None:
    text = _ROOT.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert "write_bytes" not in text
    assert "open(" not in text or "read_text" in text
