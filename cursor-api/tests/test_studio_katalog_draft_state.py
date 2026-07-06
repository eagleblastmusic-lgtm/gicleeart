"""Testy Katalog draft state (F3) — in-memory only."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.katalog_draft_state import (
    DRAFT_EMPTY_COPY,
    KatalogDraftState,
    intent_menu_options,
    intent_requires_variant,
    intent_requires_zone,
    variant_menu_options,
    zone_menu_options,
)

_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "giclee_app" / "studio"


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


def test_draft_starts_empty() -> None:
    draft = KatalogDraftState()
    assert draft.is_empty()
    assert draft.format_summary() == DRAFT_EMPTY_COPY


def test_draft_set_intent_and_variant() -> None:
    draft = KatalogDraftState()
    draft.set_intent("review_structure")
    draft.set_variant("ka1")
    assert not draft.is_empty()
    assert draft.plan_intent == "review_structure"
    assert draft.variant_id == "ka1"
    summary = draft.format_summary(variant_label="Katalog A")
    assert "Przegląd struktury" in summary
    assert "ka1" in summary or "Katalog A" in summary
    assert "niezapisany" in summary


def test_draft_set_zone_for_zone_intent() -> None:
    draft = KatalogDraftState()
    draft.set_intent("plan_zone_settings")
    draft.set_variant("ka1")
    draft.set_zone("biography")
    assert draft.zone_id == "biography"
    assert "biography" in draft.format_summary()


def test_draft_clear_resets_all() -> None:
    draft = KatalogDraftState()
    draft.set_intent("plan_collection_layout")
    draft.set_variant("ka1")
    draft.set_zone("works")
    draft.clear()
    assert draft.is_empty()
    assert draft.variant_id is None
    assert draft.zone_id is None


def test_intent_requires_variant_and_zone() -> None:
    assert intent_requires_variant("plan_collection_layout") is True
    assert intent_requires_variant("review_structure") is False
    assert intent_requires_zone("plan_zone_settings") is True
    assert intent_requires_zone("review_structure") is False


def test_menu_options_non_empty() -> None:
    assert len(intent_menu_options()) == 3
    assert len(zone_menu_options()) == 3
    opts = variant_menu_options(("ka1", "ka2"), {"ka1": "V1", "ka2": "V2"})
    assert len(opts) == 2
    assert opts[0][0] == "ka1"


def test_draft_state_source_guardrails() -> None:
    _assert_no_writes_in_source(_STUDIO_ROOT / "katalog_draft_state.py")
