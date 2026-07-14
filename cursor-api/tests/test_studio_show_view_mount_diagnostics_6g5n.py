"""6G.5-N.DIAG — mount lane diagnostics in launcher_studio (instrumentation only)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_deferred_factory_mount_lane_events_exist() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    deferred = _method_block(text, "_create_and_mount_view_deferred")
    giclee_deferred = _method_block(text, "_mount_gicleeframe_deferred")

    for block in (deferred, giclee_deferred):
        assert "studio.show_view.deferred_factory.enter" in block
        assert "studio.show_view.deferred_factory.returned" in block
        assert "_mount_view_lane" in block

    mount_lane = _method_block(text, "_mount_view_lane")
    expected = [
        "studio.show_view.pre_destroy_route_shell",
        "studio.show_view.post_destroy_route_shell",
        "studio.show_view.pre_hide_cached_views",
        "studio.show_view.post_hide_cached_views",
        "studio.show_view.pre_grid",
        "studio.show_view.post_grid",
        "studio.show_view.pre_on_show",
        "studio.show_view.post_on_show",
        "studio.show_view.pre_update_idletasks",
        "studio.show_view.post_update_idletasks",
        "studio.show_view.pre_mounted",
        "studio.show_view.post_mounted",
    ]
    for event in expected:
        assert event in mount_lane


def test_update_idletasks_diagnostic_events_exist() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_maybe_update_idletasks_for_view")
    assert "studio.show_view.update_idletasks.skipped" in block
    assert "studio.show_view.update_idletasks.executed" in block
    assert "self._content.update_idletasks()" in block


def test_show_view_warm_path_uses_mount_lane_without_changing_order() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_show_view")
    warm = block.split("with span(\"studio.show_view\"", 1)[1]
    assert "_mount_view_lane" in warm
    assert "except_key=key" not in warm or "_mount_view_lane" in warm
    mount_lane = _method_block(text, "_mount_view_lane")
    assert mount_lane.index("_destroy_route_shell") < mount_lane.index("_hide_cached_views")
    assert mount_lane.index("_hide_cached_views") < mount_lane.index("view.grid")
    assert mount_lane.index("view.grid") < mount_lane.index("on_show")
    assert mount_lane.index("on_show") < mount_lane.index("_maybe_update_idletasks_for_view")
    assert mount_lane.index("_maybe_update_idletasks_for_view") < mount_lane.index(
        "studio.show_view.mounted"
    )


def test_mount_lane_diag_fields_include_required_keys() -> None:
    path = ROOT / "giclee_app" / "launcher_studio.py"
    text = path.read_text(encoding="utf-8")
    block = _method_block(text, "_view_mount_diag_fields")
    for field in (
        "cache_hit",
        "uses_async_first_paint",
        "uses_route_shell",
        "will_update_idletasks",
    ):
        assert field in block


def test_gicleeframe_view_uses_async_first_paint() -> None:
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    assert GicleeFrameView.uses_async_first_paint is True


def test_maybe_update_idletasks_skips_async_first_paint_view() -> None:
    from unittest.mock import MagicMock

    from giclee_app.launcher_studio import GicleeAppStudio
    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    app = GicleeAppStudio()
    app.withdraw()
    app._content.update_idletasks = MagicMock()  # noqa: SLF001

    class AsyncView:
        uses_async_first_paint = True

    app._maybe_update_idletasks_for_view(AsyncView())  # noqa: SLF001
    app._content.update_idletasks.assert_not_called()

    assert GicleeFrameView.uses_async_first_paint is True

    app.destroy()


def test_gicleeframe_mount_lane_skips_update_idletasks_in_diagnostics() -> None:
    """6G.5-N.1: mount lane must not execute update_idletasks for GicleeFrameView."""
    path = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    text = path.read_text(encoding="utf-8")
    assert "uses_async_first_paint = True" in text

    launcher = (ROOT / "giclee_app" / "launcher_studio.py").read_text(encoding="utf-8")
    idletasks = launcher.split("def _maybe_update_idletasks_for_view", 1)[1].split("\n    def ", 1)[0]
    assert "uses_async_first_paint" in idletasks
    assert "studio.show_view.update_idletasks.skipped" in idletasks
    assert "studio.show_view.update_idletasks.executed" in idletasks
