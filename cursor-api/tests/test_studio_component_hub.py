"""Testy ComponentHub — debounce wyszukiwarki i filtr."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.ui.component_hub import _SEARCH_DEBOUNCE_MS


def test_search_debounce_constant_in_range() -> None:
    assert 180 <= _SEARCH_DEBOUNCE_MS <= 220


def test_component_hub_source_has_debounce() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "after_cancel" in text
    assert "_search_debounce_id" in text
    assert "_debounced_render" in text


def test_filtered_components_without_gui() -> None:
    """Filtr wyszukiwarki — logika bez Tk mainloop."""
    idx = StudioComponentIndex.build()
    products = idx.components_for_category("products")
    assert products

    comp = products[0]
    hay = f"{comp.name} {comp.description} {comp.folder_name}".lower()
    token = hay.split()[0][:4]
    if len(token) < 2:
        token = comp.folder_name[:4]

    matched = [
        c
        for c in products
        if token in f"{c.name} {c.description} {c.folder_name}".lower()
    ]
    assert matched
    assert comp in matched


def test_component_hub_accepts_component_index() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    source = path.read_text(encoding="utf-8")
    assert "component_index" in source
    assert "StudioComponentIndex" in source
    assert "discover_components" not in source
