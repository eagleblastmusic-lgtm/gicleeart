"""Testy Katalog data map (F2) — read-only, bounded paths, tmp_path."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_data_map import (
    MAX_FILE_BYTES,
    MAX_TLDOBIO_COLLECTION_KEYS,
    MAX_VARIANTS_PREVIEW,
    build_katalog_data_map,
    data_map_display_rows,
)


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_data_map_missing_folders_no_crash(tmp_path: Path) -> None:
    dm = build_katalog_data_map(tmp_path)
    assert dm.legacy_katalog.root_exists is False
    assert dm.tldobio.root_exists is False
    assert dm.external_shopify.write_policy == "out_of_scope"
    assert dm.studio_writer.write_policy == "not_started"
    rows = data_map_display_rows(dm)
    assert any("missing" in v.lower() for _k, v in rows)


def test_data_map_legacy_katalog_detected(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    (katalog / "component.json").write_text("{}", encoding="utf-8")
    (katalog / "registry.py").write_text(
        'zone_id="biography"\nTemplateField("bio_bg", "x", "shopify_image", "background_image")\n',
        encoding="utf-8",
    )
    _write_json(
        katalog / "data" / "variants" / "manifest.json",
        {"active": "ka1", "variants": [{"id": "ka1", "label": "V1"}]},
    )
    _write_json(
        katalog / "data" / "variants" / "ka1" / "collection.json",
        {"sections": {"s": {"settings": {"background_image": "x"}}}},
    )

    dm = build_katalog_data_map(tmp_path)
    lk = dm.legacy_katalog
    assert lk.root_exists is True
    assert lk.component_json_exists is True
    assert lk.registry_py_exists is True
    assert lk.manifest_exists is True
    assert lk.variant_count == 1
    assert lk.sample_variants == ("ka1",)
    assert lk.collection_json_count == 1
    assert lk.has_background_image_refs is True
    assert lk.status == "legacy_template_json"
    assert lk.write_policy == "not_defined"


def test_data_map_tldobio_detected(tmp_path: Path) -> None:
    tldobio = tmp_path / "tldobio"
    tldobio.mkdir()
    handles = {f"artist-{i}": {"url": "https://x" if i % 2 == 0 else ""} for i in range(3)}
    _write_json(tldobio / "data" / "collections.json", {"version": 2, "backgrounds": handles})
    (tldobio / "service.py").write_text(
        "METAFIELD_NAMESPACE = 'custom'\n# shopify_client GraphQL upload\n",
        encoding="utf-8",
    )

    dm = build_katalog_data_map(tmp_path)
    tb = dm.tldobio
    assert tb.root_exists is True
    assert tb.collections_json_exists is True
    assert tb.collection_count == 3
    assert len(tb.sample_collection_keys) <= MAX_TLDOBIO_COLLECTION_KEYS
    assert tb.backgrounds_with_url == 2
    assert tb.service_py_exists is True
    assert tb.shopify_integration_detected is True
    assert tb.metafield_refs_detected is True
    assert tb.status == "absorbed_cache_or_external_bridge"


def test_data_map_invalid_json_warning_no_crash(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    manifest = katalog / "data" / "variants" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{bad json", encoding="utf-8")

    dm = build_katalog_data_map(tmp_path)
    codes = {w.code for w in dm.warnings}
    assert "invalid_json" in codes
    assert dm.legacy_katalog.variant_count == 0


def test_data_map_file_too_large_warning(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    manifest = katalog / "data" / "variants" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b"x" * (MAX_FILE_BYTES + 1))

    dm = build_katalog_data_map(tmp_path)
    codes = {w.code for w in dm.warnings}
    assert "file_too_large" in codes


def test_data_map_variant_limit_warning(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    variants = [{"id": f"v{i}", "label": f"V{i}"} for i in range(MAX_VARIANTS_PREVIEW + 3)]
    _write_json(katalog / "data" / "variants" / "manifest.json", {"variants": variants})

    dm = build_katalog_data_map(tmp_path)
    assert dm.legacy_katalog.variant_count == MAX_VARIANTS_PREVIEW + 3
    assert len(dm.legacy_katalog.sample_variants) == MAX_VARIANTS_PREVIEW
    assert any(w.code == "variant_limit" for w in dm.warnings)


def test_data_map_sources_policies(tmp_path: Path) -> None:
    dm = build_katalog_data_map(tmp_path)
    assert dm.external_shopify.status == "out_of_scope"
    assert dm.external_shopify.risk == "high"
    assert dm.studio_draft.write_policy == "planned"
    assert dm.studio_writer.write_policy == "not_started"


def test_data_map_display_separates_sources(tmp_path: Path) -> None:
    dm = build_katalog_data_map(tmp_path)
    text = " ".join(f"{k} {v}" for k, v in data_map_display_rows(dm))
    assert "Legacy katalog" in text
    assert "tldobio" in text.lower() or "Tło do Bio" in text
    assert "out_of_scope" in text or "out-of-scope" in text.lower()
    assert "not_started" in text


def test_data_map_dual_persistence_warning(tmp_path: Path) -> None:
    (tmp_path / "katalog").mkdir()
    (tmp_path / "tldobio").mkdir()
    dm = build_katalog_data_map(tmp_path)
    assert any(w.code == "dual_persistence" for w in dm.warnings)


def test_data_map_no_komponenty_import() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "katalog_data_map.py"
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


def test_data_map_source_no_write_or_glob() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "studio" / "katalog_data_map.py"
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
    assert not any("shopify" in imp.lower() for imp in imports if imp != "katalog_inventory")


def test_data_map_does_not_mutate_tmp_path(tmp_path: Path) -> None:
    before = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    build_katalog_data_map(tmp_path)
    after = {p.relative_to(tmp_path) for p in tmp_path.rglob("*")}
    assert before == after
