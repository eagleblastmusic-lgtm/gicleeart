from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_gicleeframe_has_visual_state_fields() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "_visual_bootstrap_complete" in text
    assert "_loading_overlay" in text
    assert "_visual_enter_mono" in text


def test_gicleeframe_logs_all_visual_events() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    for event in (
        "studio.gicleeframe.visual.enter",
        "studio.gicleeframe.visual.shell_built",
        "studio.gicleeframe.visual.inventory_loaded",
        "studio.gicleeframe.visual.first_selection_done",
        "studio.gicleeframe.visual.idle_ready",
        "studio.gicleeframe.visual.visible_ready",
        "studio.gicleeframe.visual.full_ready_progressive",
    ):
        assert event in text


def test_on_show_schedules_visual_ready_via_after_idle() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "on_show")

    assert "_schedule_visual_ready" in block
    assert "cache_hit" in block


def test_schedule_visual_ready_uses_after_idle() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_schedule_visual_ready")

    assert "after_idle" in block
    assert "_mark_idle_ready" in block
    assert "_mark_visual_ready" in block


def test_loading_overlay_copy() -> None:
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")

    assert "Ładowanie Giclée Frame" in text
    assert "_GF_LOADING_OVERLAY_TEXT" in text


def test_launcher_gicleeframe_open_passes_cache_hit_without_update_idletasks() -> None:
    """GICLÉE FRAME re-entry uses mount lane; async views skip update_idletasks."""
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    shell_block = _method_block(text, "_show_gicleeframe_shell")
    mount_block = _method_block(text, "_mount_view_lane")
    idletasks_block = _method_block(text, "_maybe_update_idletasks_for_view")

    # Cache re-entry delegates to mount lane instead of inline on_show/update_idletasks.
    assert "_mount_view_lane" in shell_block
    assert "cache_hit=True" in shell_block
    assert "on_show" not in shell_block
    assert "update_idletasks" not in shell_block

    # Navigation is wired via pre_grid before grid/on_show.
    assert "pre_grid" in shell_block
    assert "set_navigation" in shell_block

    # Mount lane is the single place that calls on_show with cache_hit.
    assert "on_show(cache_hit=cache_hit)" in mount_block
    assert mount_block.index("on_show") < mount_block.index("_maybe_update_idletasks_for_view")

    # GicleeFrameView opts out of synchronous update_idletasks.
    assert GicleeFrameView.uses_async_first_paint is True
    assert "uses_async_first_paint" in idletasks_block
    assert "studio.show_view.update_idletasks.skipped" in idletasks_block
