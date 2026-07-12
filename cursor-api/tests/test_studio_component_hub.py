"""Testy ComponentHub — debounce, card cache, lazy render, skeleton first-paint."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from giclee_app.studio.component_index import StudioComponentIndex
from giclee_app.ui.component_hub import (
    _CARDS_PER_TICK,
    _FIRST_PAINT_DELAY_MS,
    _FIRST_VISIBLE_BUDGET_MS,
    _FIRST_VISIBLE_CARD_COUNT,
    _IDLE_BATCH_DELAY_MS,
    _IDLE_BATCH_SIZE,
    _IDLE_TICK_BUDGET_MS,
    _LOADING_TEXT,
    _PREPARE_TEXT,
    _REAL_SHELL_FIRST_PAINT_COUNT,
    _SEARCH_DEBOUNCE_MS,
    _SKELETON_COUNT,
    _batch_delay_for_start,
    _batch_size_for_start,
    _tick_delay_ms,
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

    assert 1 <= _FIRST_VISIBLE_CARD_COUNT <= _SKELETON_COUNT
    assert _REAL_SHELL_FIRST_PAINT_COUNT == _FIRST_VISIBLE_CARD_COUNT
    assert _IDLE_BATCH_SIZE >= 1
    assert _CARDS_PER_TICK == _IDLE_BATCH_SIZE
    assert _FIRST_VISIBLE_BUDGET_MS > 0
    assert _IDLE_TICK_BUDGET_MS > 0
    assert _IDLE_BATCH_DELAY_MS == 0

    assert _batch_size_for_start(0) == _FIRST_VISIBLE_CARD_COUNT
    assert _batch_size_for_start(1) == _IDLE_BATCH_SIZE
    assert _batch_delay_for_start(0) == 0
    assert _batch_delay_for_start(1) == _IDLE_BATCH_DELAY_MS
    assert _tick_delay_ms(first_visible_phase=True) == 0
    assert _tick_delay_ms(first_visible_phase=False) == _IDLE_BATCH_DELAY_MS

    assert "_render_generation" in text
    assert "_pending_render_after_id" in text
    assert _LOADING_TEXT in text
    assert "_batch_build_cards" in text
    assert "_append_cards_to_grid" in text
    assert "_sync_skeleton_slots" in text
    assert "ComponentCardShell" in text
    assert "_hydrate_queue" in text


def test_skeleton_first_paint_constants() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert _FIRST_PAINT_DELAY_MS == 0
    assert "_FIRST_PAINT_DELAY_MS <= 0" in text
    assert _SKELETON_COUNT == 6
    assert _PREPARE_TEXT in text
    assert "_make_skeleton_card" in text
    assert "_show_skeleton" in text
    assert "_begin_first_paint" in text
    assert "_start_batch_render" in text


def test_on_show_defers_card_build_via_after() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "def on_show" in text
    assert "_begin_first_paint" in text
    assert "_FIRST_PAINT_DELAY_MS" in text
    # on_show nie woła _batch_build_cards synchronicznie
    on_show_block = text.split("def on_show")[1].split("\n    def ")[0]
    assert "_batch_build_cards(" not in on_show_block


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

    original_init = widgets.ComponentCardShell.__init__

    def counting_init(self, *args, **kwargs):  # noqa: ANN001, ANN002
        nonlocal init_count
        init_count += 1
        return original_init(self, *args, **kwargs)

    try:
        with patch.object(widgets.ComponentCardShell, "__init__", counting_init):
            from giclee_app.ui.component_hub import ComponentHubView

            idx = StudioComponentIndex.build()
            hub = ComponentHubView(root, category_id="products", component_index=idx)
            hub.on_show()
            deadline = time.time() + 5.0
            while not hub._cards_fully_built and time.time() < deadline:
                root.update_idletasks()
                root.update()
            assert hub._cards_fully_built, "cards should finish lazy batch render"
            built_count = init_count
            hub._search_var.set("obraz")
            hub._debounced_filter()
            root.update_idletasks()
            root.update()
            assert init_count == built_count
    finally:
        root.destroy()


def test_hub_inline_uses_callback_not_launch() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "on_open_inline" in text
    assert 'comp.mode == "inline"' in text

    import customtkinter as ctk

    from giclee_app.component_loader import Component
    from giclee_app.ui.component_hub import ComponentHubView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    inline_comp = Component(
        folder_name="testinline",
        package_path=Path("/fake/testinline"),
        name="Inline Test",
        description="",
        mode="inline",
    )
    calls: list[tuple[str, str]] = []

    def on_open_inline(comp: Component, cat: str) -> None:
        calls.append((comp.folder_name, cat))

    idx = StudioComponentIndex.build()
    hub = ComponentHubView(
        root,
        category_id="products",
        component_index=idx,
        on_open_inline=on_open_inline,
    )
    with patch("giclee_app.ui.component_hub.launch") as mock_launch:
        hub._on_card_click(inline_comp)
        mock_launch.assert_not_called()
    assert calls == [("testinline", "products")]
    root.destroy()


def test_hub_subprocess_still_uses_launch() -> None:
    import customtkinter as ctk

    from giclee_app.component_loader import Component
    from giclee_app.launcher_delegate import LaunchOutcome, LaunchResult
    from giclee_app.ui.component_hub import ComponentHubView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    comp = Component(
        folder_name="sub",
        package_path=Path("/fake/sub"),
        name="Sub",
        description="",
        mode="subprocess",
    )
    idx = StudioComponentIndex.build()
    hub = ComponentHubView(
        root,
        category_id="products",
        component_index=idx,
        on_open_inline=lambda c, cat: None,
    )
    with patch(
        "giclee_app.ui.component_hub.launch",
        return_value=LaunchResult(LaunchOutcome.OK),
    ) as mock_launch:
        hub._on_card_click(comp)
        mock_launch.assert_called_once()
    root.destroy()


def test_hub_has_mode_filter_and_sort() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "_mode_filter" in text
    assert "sorted_components" in text
    assert "_EMPTY_FILTER_TEXT" in text
    assert "_EMPTY_CATEGORY_TEXT" in text


def test_pin_toggle_does_not_rebuild_card_cache() -> None:
    import customtkinter as ctk

    from giclee_app.studio.state import StudioState
    from giclee_app.ui.component_hub import ComponentHubView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    init_count = 0
    from giclee_app.ui import widgets

    original_init = widgets.ComponentCardShell.__init__

    def counting_init(self, *args, **kwargs):  # noqa: ANN001, ANN002
        nonlocal init_count
        init_count += 1
        return original_init(self, *args, **kwargs)

    try:
        with patch.object(widgets.ComponentCardShell, "__init__", counting_init):
            idx = StudioComponentIndex.build()
            products = idx.components_for_category("products")
            assert products
            comp = products[0]
            state = StudioState()
            hub = ComponentHubView(
                root,
                category_id="products",
                component_index=idx,
                studio_state=state,
            )
            hub.on_show()
            deadline = time.time() + 5.0
            while not hub._cards_fully_built and time.time() < deadline:
                root.update_idletasks()
                root.update()
            built = init_count
            hub._toggle_pin(comp)
            root.update_idletasks()
            root.update()
            assert init_count == built
            assert state.is_pinned(comp.folder_name)
    finally:
        root.destroy()


def test_hub_background_click_passes_category() -> None:
    path = Path(__file__).resolve().parents[1] / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")
    assert "on_open_background(comp, self._category_id)" in text

    import customtkinter as ctk

    from giclee_app.component_loader import Component
    from giclee_app.ui.component_hub import ComponentHubView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    bg_calls: list[tuple[str, str]] = []

    def on_open_background(comp: Component, cat: str) -> None:
        bg_calls.append((comp.folder_name, cat))

    idx = StudioComponentIndex.build()
    hub = ComponentHubView(
        root,
        category_id="theme",
        component_index=idx,
        on_open_background=on_open_background,
    )
    tldobio = idx.by_folder["tldobio"]
    hub._on_background_click(tldobio)
    assert bg_calls == [("tldobio", "theme")]

    katalog = idx.by_folder.get("katalog")
    if katalog is not None:
        hub._on_background_click(katalog)
        assert bg_calls == [("tldobio", "theme")]

    root.destroy()


def test_hub_search_during_partial_render() -> None:
    import customtkinter as ctk

    from giclee_app.ui.component_hub import ComponentHubView

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    root.withdraw()
    idx = StudioComponentIndex.build()
    hub = ComponentHubView(root, category_id="theme", component_index=idx)
    hub.on_show(cache_hit=False)
    hub._search_var.set("giclee")
    hub._debounced_filter()
    deadline = time.time() + 10.0
    while not hub._cards_fully_built and time.time() < deadline:
        root.update_idletasks()
        root.update()
    assert hub._cards_fully_built
    mapped = [folder for folder, card in hub._cards.items() if card.winfo_ismapped()]
    assert mapped == ["gicleeframe"]
    root.destroy()
