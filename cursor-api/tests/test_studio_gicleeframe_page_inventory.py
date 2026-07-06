"""Testy GICLÉE FRAME™ F2 page inventory — bounded read, zero write."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.component_loader import find_components_dir
from giclee_app.studio.gicleeframe_page_inventory import (
    build_gicleeframe_page_inventory,
    inventory_count_stats,
    inventory_elements_by_group,
    inventory_display_rows,
)

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"


def test_inventory_reads_active_variant() -> None:
    report = build_gicleeframe_page_inventory(find_components_dir())
    assert report.variant_id
    assert report.live_variant_id == report.variant_id
    assert report.page_path is not None
    assert report.page_path.name == "page.giclee-frame.json"


def test_inventory_source_sections_vs_expanded_elements() -> None:
    report = build_gicleeframe_page_inventory(find_components_dir())
    stats = inventory_count_stats(report)
    assert stats["source_sections"] == report.source_section_count
    assert stats["source_sections"] >= 1
    assert stats["elements_total"] == len(report.elements)
    assert stats["elements_total"] > stats["source_sections"]


def test_inventory_has_dividers_media_and_texts() -> None:
    report = build_gicleeframe_page_inventory(find_components_dir())
    stats = inventory_count_stats(report)
    assert stats["separators"] >= 1
    assert stats["media_sections"] >= 1
    assert stats["images"] >= 1
    assert stats["text_blocks"] >= 1


def test_inventory_groups_non_empty() -> None:
    report = build_gicleeframe_page_inventory(find_components_dir())
    groups = inventory_elements_by_group(report)
    assert "separators" in groups
    assert "texts" in groups
    assert len(groups) >= 3


def test_inventory_display_rows_mentions_source_and_expanded() -> None:
    report = build_gicleeframe_page_inventory(find_components_dir())
    rows = dict(inventory_display_rows(report))
    assert "Źródłowe sekcje (order[])" in rows
    assert "Elementy inventory (po rozwinięciu)" in rows
    assert int(rows["Elementy inventory (po rozwinięciu)"]) > int(rows["Źródłowe sekcje (order[])"])


def test_inventory_module_no_komponenty_imports() -> None:
    path = _STUDIO_ROOT / "gicleeframe_page_inventory.py"
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")
