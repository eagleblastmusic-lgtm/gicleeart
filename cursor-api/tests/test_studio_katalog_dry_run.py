"""Testy Katalog dry-run (F3/F4) — pure, bez zapisu."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_data_map import build_katalog_data_map
from giclee_app.studio.katalog_draft_state import KatalogDraftState
from giclee_app.studio.katalog_dry_run import (
    DRY_RUN_BADGE,
    build_katalog_plan_dry_run,
    format_dry_run_summary,
)
from giclee_app.studio.katalog_inventory import build_katalog_inventory

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _assert_no_writes_in_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "write_text" not in text
    assert 'open(' not in text
    assert "shutil" not in text
    assert "requests" not in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    for imp in imports:
        assert not imp.startswith("Komponenty")


def _minimal_katalog_tree(tmp_path: Path) -> None:
    katalog = tmp_path / "katalog"
    katalog.mkdir()
    (katalog / "component.json").write_text("{}", encoding="utf-8")
    (katalog / "registry.py").write_text(
        'zone_id="biography"\nzone_id="showcase"\nzone_id="works"\n',
        encoding="utf-8",
    )
    _write_json(
        katalog / "data" / "variants" / "manifest.json",
        {"active": "ka1", "variants": [{"id": "ka1", "label": "V1"}]},
    )
    _write_json(
        katalog / "data" / "variants" / "ka1" / "collection.json",
        {"sections": {}},
    )


def test_dry_run_empty_draft_blocked(tmp_path: Path) -> None:
    inv = build_katalog_inventory(tmp_path)
    dm = build_katalog_data_map(tmp_path)
    draft = KatalogDraftState()
    result = build_katalog_plan_dry_run(draft, inv, dm)
    assert result.ok is False
    assert result.errors
    summary = format_dry_run_summary(result)
    assert summary.startswith(DRY_RUN_BADGE)


def test_dry_run_valid_review_structure(tmp_path: Path) -> None:
    _minimal_katalog_tree(tmp_path)
    inv = build_katalog_inventory(tmp_path)
    dm = build_katalog_data_map(tmp_path)
    draft = KatalogDraftState()
    draft.set_intent("review_structure")
    result = build_katalog_plan_dry_run(draft, inv, dm)
    assert result.ok is True
    assert "manifest" in result.fields_touched
    summary = format_dry_run_summary(result)
    assert DRY_RUN_BADGE in summary
    assert "writer: not started" in summary


def test_dry_run_requires_variant_for_layout(tmp_path: Path) -> None:
    _minimal_katalog_tree(tmp_path)
    inv = build_katalog_inventory(tmp_path)
    dm = build_katalog_data_map(tmp_path)
    draft = KatalogDraftState()
    draft.set_intent("plan_collection_layout")
    result = build_katalog_plan_dry_run(draft, inv, dm)
    assert result.ok is False
    assert any("wariant" in e.lower() for e in result.errors)


def test_dry_run_dual_persistence_in_blocked_paths(tmp_path: Path) -> None:
    _minimal_katalog_tree(tmp_path)
    tldobio = tmp_path / "tldobio"
    tldobio.mkdir()
    _write_json(tldobio / "data" / "collections.json", {"version": 2, "backgrounds": {}})
    inv = build_katalog_inventory(tmp_path)
    dm = build_katalog_data_map(tmp_path)
    draft = KatalogDraftState()
    draft.set_intent("review_structure")
    result = build_katalog_plan_dry_run(draft, inv, dm)
    assert result.ok is True
    assert any("dual persistence" in p for p in result.blocked_paths)


def test_dry_run_module_source_guardrails() -> None:
    _assert_no_writes_in_source(_STUDIO_ROOT / "katalog_dry_run.py")
