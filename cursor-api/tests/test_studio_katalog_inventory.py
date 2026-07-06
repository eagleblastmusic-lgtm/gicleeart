"""Testy Katalog inventory (F1) — read-only, bounded paths, tmp_path."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_inventory import (
    TLDOBIO_ABSORBED_STATUS,
    build_katalog_inventory,
    inventory_display_rows,
)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_inventory_missing_folders_no_error(tmp_path: Path) -> None:
    report = build_katalog_inventory(tmp_path)
    assert report.katalog.root_exists is False
    assert report.tldobio.root_exists is False
    assert report.katalog.variant_ids == ()
    rows = inventory_display_rows(report)
    assert any("missing" in v for _k, v in rows)


def test_inventory_detects_katalog_files(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    (katalog / "component.json").write_text("{}", encoding="utf-8")
    (katalog / "registry.py").write_text('zone_id="biography"\nzone_id="showcase"\n', encoding="utf-8")
    _write_json(
        katalog / "data" / "variants" / "manifest.json",
        {"active": "ka1", "variants": [{"id": "ka1", "label": "Wersja 1"}]},
    )
    _write_json(katalog / "data" / "variants" / "ka1" / "collection.json", {"sections": {}})

    report = build_katalog_inventory(tmp_path)
    assert report.katalog.root_exists is True
    assert report.katalog.component_json_exists is True
    assert report.katalog.registry_py_exists is True
    assert report.katalog.manifest_exists is True
    assert report.katalog.active_variant_id == "ka1"
    assert report.katalog.variant_ids == ("ka1",)
    assert report.katalog.collection_json_by_variant["ka1"] is True
    assert report.katalog.registry_zone_ids == ("biography", "showcase")


def test_inventory_detects_tldobio_cache(tmp_path: Path) -> None:
    tldobio = tmp_path / "tldobio"
    tldobio.mkdir()
    _write_json(
        tldobio / "data" / "collections.json",
        {
            "version": 2,
            "backgrounds": {
                "artist-a": {"url": "https://cdn.example/a.png"},
                "artist-b": {"url": ""},
            },
        },
    )

    report = build_katalog_inventory(tmp_path)
    assert report.tldobio.root_exists is True
    assert report.tldobio.collections_json_exists is True
    assert report.tldobio.cache_version == 2
    assert report.tldobio.background_count == 2
    assert report.tldobio.backgrounds_with_url == 1
    assert report.tldobio.absorbed_status == TLDOBIO_ABSORBED_STATUS


def test_inventory_display_shows_absorbed_tldobio(tmp_path: Path) -> None:
    report = build_katalog_inventory(tmp_path)
    text = " ".join(v for _k, v in inventory_display_rows(report))
    assert TLDOBIO_ABSORBED_STATUS in text


def test_inventory_module_no_komponenty_import() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "katalog_inventory.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def test_inventory_source_no_write_or_glob() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "katalog_inventory.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert "write_text" not in text
    assert "glob(" not in text
    assert "rglob(" not in text
    assert "requests" not in text
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert not any("shopify" in imp.lower() for imp in imports)


def test_inventory_does_not_mutate_tmp_path(tmp_path: Path) -> None:
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    build_katalog_inventory(tmp_path)
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert before == after
