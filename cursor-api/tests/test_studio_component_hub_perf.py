from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_component_hub_has_first_visible_batch_constants() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "_FIRST_VISIBLE_CARD_COUNT" in text
    assert "_FIRST_VISIBLE_BUDGET_MS" in text
    assert "_CARDS_PER_TICK" in text
    assert "_IDLE_BATCH_SIZE" in text
    assert "_FIRST_VISIBLE_CARD_COUNT = 2" in text or "_FIRST_VISIBLE_CARD_COUNT = 3" in text
    assert "_CARDS_PER_TICK = 3" in text or "_CARDS_PER_TICK=3" in text
    assert "_IDLE_BATCH_SIZE = 3" in text or "_IDLE_BATCH_SIZE=3" in text


def test_component_hub_hover_hydration_is_disabled_by_default() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_HUB_HYDRATE_ON_HOVER" in text
    assert "default=False" in text
    assert "hover_disabled_default" in text
    assert (
        "on_request_hydration=self.request_card_hydration if _hover_hydration_enabled() else None"
        in text
    )


def test_component_hub_idle_batches_use_zero_delay_with_budget() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "_IDLE_BATCH_DELAY_MS = 0" in text or "_IDLE_BATCH_DELAY_MS=0" in text
    assert "_IDLE_TICK_BUDGET_MS" in text
    assert "_IDLE_BATCH_SIZE = 3" in text or "_IDLE_BATCH_SIZE=3" in text


def test_component_hub_uses_tick_budget_for_idle_batches() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "_IDLE_TICK_BUDGET_MS" in text

    block = text.split("def _batch_build_cards", 1)[1].split("\n    def ", 1)[0]
    assert "budget_ms" in block
    assert "while i < len(comps)" in block
    assert "created < max_cards" in block
    assert "avg_card_ms" in block


def test_component_hub_logs_batch_phase_and_avg_card_ms() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "phase=" in text
    assert "avg_card_ms" in text
    assert "first_visible" in text
    assert "idle" in text


def test_component_hub_has_hydration_logs() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "hub.card.shell_created" in text
    assert "hub.card.hydrate_start" in text
    assert "hub.hydration.queue_done" in text


def test_component_hub_has_visual_ready_events() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "hub.visual.enter" in text
    assert "hub.visual.first_cards_ready" in text
    assert "hub.visual.visible_ready" in text
    assert "hub.visual.full_ready" in text


def test_component_hub_keeps_card_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "_cards" in text
    assert "_cards_fully_built" in text
    assert "cards_fully_built" in text


def test_component_hub_does_not_destroy_cards_on_normal_show() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    if "def on_show" in text:
        block = text.split("def on_show", 1)[1].split("\n    def ", 1)[0]
        assert ".destroy()" not in block


def test_launcher_passes_cache_hit_to_on_show() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    assert "on_show(cache_hit=cache_hit)" in text
    assert "except TypeError:" in text


def test_component_hub_auto_hydration_is_disabled_by_default() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "GICLEE_HUB_AUTO_HYDRATE" in text
    assert "hydration.auto_disabled" in text
    assert "request_card_hydration" in text


def test_component_hub_has_filter_cache() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "_filter_cache_key" in text
    assert "_filter_cache_value" in text
    assert "def _invalidate_filter_cache" in text


def test_component_hub_does_not_requeue_hidden_hydration() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "hydrate_deferred_hidden" in text
    assert ".append(folder)" not in text.split("hydrate_deferred_hidden", 1)[1].split("def ", 1)[0]


def test_launcher_skips_update_idletasks_for_async_first_paint_views() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")

    assert "_maybe_update_idletasks_for_view" in text
    assert "uses_async_first_paint" in text
    block = text.split("def _maybe_update_idletasks_for_view", 1)[1].split("\n    def ", 1)[0]
    assert "update_idletasks" in block


def test_component_hub_lifecycle_log() -> None:
    path = ROOT / "giclee_app" / "ui" / "component_hub.py"
    text = path.read_text(encoding="utf-8")

    assert "hub.lifecycle" in text
    assert "cache_hit=cache_hit" in text
