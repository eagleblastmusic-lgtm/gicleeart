"""Testy ComponentHub — debounce wyszukiwarki, card cache i lazy render."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.ui.component_hub import (
    _BATCH_SIZE,
    _LOADING_TEXT,
    _SEARCH_DEBOUNCE_MS,
)


def test_search_debounce_constant_in_range() -> None:
    assert 180 <= _SEARCH_DEBOUNCE_MS <= 220


def test_component_hub_source_has_debounce() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "after_cancel" in text
    assert "_search_debounce_id" in text
    assert "_debounced_filter" in text


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


def test_lazy_render_has_batching() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "_BATCH_SIZE" in text
    assert 3 <= _BATCH_SIZE <= 4
    assert "_render_generation" in text
    assert "_pending_render_after_id" in text
    assert _LOADING_TEXT in text
    assert "_batch_build_cards" in text


def test_hub_cards_not_recreated_on_filter() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "_cards:" in text or "_cards" in text
    assert "grid_remove" in text
    assert "_apply_filter_grid" in text
    assert "child.destroy()" not in text

    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    init_count = 0

    from giclee_app.ui import widgets

    original_init = widgets.ComponentCard.__init__

    def counting_init(self, *args, **kwargs):  # noqa: ANN001, ANN002
        nonlocal init_count
        init_count += 1
        return original_init(self, *args, **kwargs)

    try:
        with patch.object(widgets.ComponentCard, "__init__", counting_init):
            from giclee_app.ui.component_hub import ComponentHubView

            idx = StudioComponentIndex.build()
            hub = ComponentHubView(root, category_id="products", component_index=idx)
            hub.on_show()
            for _ in range(300):
                root.update_idletasks()
                root.update()
                if hub._cards_fully_built:
                    break
            assert hub._cards_fully_built, "cards should finish lazy batch render"
            built_count = init_count
            hub._search_var.set("obraz")
            hub._debounced_filter()
            root.update_idletasks()
            root.update()
            assert init_count == built_count
    finally:
        root.destroy()
