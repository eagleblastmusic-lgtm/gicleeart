"""6G.5-Q / 6G.5-Q.1 — static first-visible lane; scroll upgrade after perceived ready."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _method_block(text: str, name: str) -> str:
    marker = f"def {name}"
    assert marker in text
    return text.split(marker, 1)[1].split("\n    def ", 1)[0]


def test_early_shell_can_use_static_lane_without_immediate_scroll_upgrade() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        parent = ctk.CTkFrame(view)
        parent.pack()
        card = view._build_sections_column_shell(parent, use_static_lane=True)
        assert card is not None
        assert view._section_list_static_lane is not None
        assert view._section_list_scroll is None
        assert not view._section_list_scroll_upgrade_scheduled
        assert view._section_list_scroll_upgrade_fallback_after_id is not None
    finally:
        root.destroy()


def test_static_lane_spike_events_exist() -> None:
    text = _view_text()
    for event in (
        "studio.gicleeframe.section_list.static_lane_ready",
        "studio.gicleeframe.section_list.scroll_upgrade_scheduled",
        "studio.gicleeframe.section_list.scroll_upgrade_enter",
        "studio.gicleeframe.section_list.scroll_upgrade_ready",
    ):
        assert event in text


def test_scroll_upgrade_scheduled_includes_reason_field() -> None:
    text = _view_text()
    marker = "def _schedule_section_list_scroll_upgrade(self, *, reason: str)"
    assert marker in text
    body = text.split(marker, 1)[1].split("\n    def ", 1)[0]
    assert "reason=reason" in body
    assert "perceived_ready_logged=" in body
    assert "static_lane_real_rows=" in body
    assert "delay_ms=" in body


def test_scroll_upgrade_scheduled_after_perceived_ready_path() -> None:
    body = _method_block(_view_text(), "_try_mark_perceived_ready")
    assert "_schedule_section_list_scroll_upgrade_after_perceived" in body
    after_body = _method_block(
        _view_text(), "_schedule_section_list_scroll_upgrade_after_perceived"
    )
    assert 'reason="after_perceived_ready"' in after_body


def test_scroll_upgrade_fallback_timeout_path_exists() -> None:
    body = _method_block(_view_text(), "_ensure_section_list_scroll_upgrade_fallback")
    assert 'reason="fallback_timeout"' in body
    assert "_GF_SECTION_SCROLL_UPGRADE_FALLBACK_TIMEOUT_MS" in body


def test_static_lane_shell_schedules_fallback_not_immediate_upgrade() -> None:
    body = _method_block(_view_text(), "_build_sections_column_shell")
    static_block = body.split("if use_static_lane:", 1)[1].split("else:", 1)[0]
    assert "_ensure_section_list_scroll_upgrade_fallback" in static_block
    assert "_schedule_section_list_scroll_upgrade" not in static_block


def test_first_visible_ready_logged_before_scroll_upgrade_scheduling() -> None:
    populate = _method_block(_view_text(), "_populate_section_list_static_lane")
    assert "studio.gicleeframe.section_list.first_visible_ready" in populate
    shell = _method_block(_view_text(), "_build_sections_column_shell")
    static_block = shell.split("if use_static_lane:", 1)[1].split("else:", 1)[0]
    first_visible_pos = static_block.index("_populate_section_list_static_lane")
    upgrade_pos = static_block.index("_ensure_section_list_scroll_upgrade_fallback")
    assert first_visible_pos < upgrade_pos


def test_scroll_frame_created_on_upgrade_path() -> None:
    text = _view_text()
    upgrade_body = _method_block(text, "_upgrade_section_list_scroll")
    assert "CTkScrollableFrame" in upgrade_body or "_create_section_list_scroll_frame" in upgrade_body
    scroll_body = _method_block(text, "_create_section_list_scroll_frame")
    assert "CTkScrollableFrame" in scroll_body
    assert "studio.gicleeframe.build.sections_column.shell.scroll_create" in scroll_body


def test_placeholder_static_lane_does_not_log_first_visible_ready() -> None:
    body = _method_block(_view_text(), "_populate_section_list_static_lane")
    placeholder_start = body.index("self._section_list_static_lane_real_rows = False")
    placeholder_body = body[placeholder_start:]
    assert "studio.gicleeframe.section_list.static_lane_ready" in placeholder_body
    assert "studio.gicleeframe.section_list.first_visible_ready" not in placeholder_body
    assert "self._section_list_first_visible_built = True" not in placeholder_body


def test_real_static_lane_rows_log_first_visible_ready() -> None:
    body = _method_block(_view_text(), "_populate_section_list_static_lane")
    assert "real_rows=True" in body
    assert "studio.gicleeframe.section_list.first_visible_ready" in body
    assert "self._section_list_first_visible_built = True" in body


def test_deferred_early_lane_uses_static_lane_shell() -> None:
    body = _method_block(_view_text(), "_build_sections_column_deferred")
    assert "use_static_lane=True" in body


def test_static_lane_spike_preserves_prior_6g5_markers() -> None:
    text = _view_text()
    assert "studio.gicleeframe.sections_column.early_lane_enter" in text
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in text
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "uses_async_first_paint = True" in text
    assert "_GF_SECTION_FIRST_BATCH_SIZE" in text


def test_scroll_upgrade_creates_scroll_and_schedules_incremental() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        parent = ctk.CTkFrame(view)
        parent.pack()
        view._build_sections_column_shell(parent, use_static_lane=True)
        view._section_list_scroll_upgrade_scheduled = False
        scheduled: list[str] = []

        def _capture_schedule(delay: int, callback) -> str:  # type: ignore[no-untyped-def]
            scheduled.append(getattr(callback, "__name__", str(callback)))
            callback()
            return "after-id"

        with patch.object(view, "after", side_effect=_capture_schedule):
            view._schedule_section_list_scroll_upgrade(reason="after_perceived_ready")
        assert view._section_list_scroll is not None
        assert view._section_list_static_lane is None
        assert view._section_list_scroll_upgrade_done
        assert "_upgrade_section_list_scroll" in scheduled
    finally:
        root.destroy()


def test_perceived_ready_triggers_scroll_upgrade_schedule() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        parent = ctk.CTkFrame(view)
        parent.pack()
        view._build_sections_column_shell(parent, use_static_lane=True)
        view._shell_sections_built = True
        view._shell_editor_built = True
        view._shell_control_built = True
        view._section_list_first_visible_built = True
        scheduled: list[tuple[int, str]] = []

        def _capture_schedule(delay: int, callback) -> str:  # type: ignore[no-untyped-def]
            scheduled.append((delay, getattr(callback, "__name__", str(callback))))
            return "after-id"

        with patch.object(view, "after", side_effect=_capture_schedule):
            view._try_mark_perceived_ready()
        assert view._perceived_ready_logged
        assert view._section_list_scroll_upgrade_scheduled
        assert scheduled
        assert scheduled[-1] == (120, "_upgrade_section_list_scroll")
        assert view._section_list_scroll is None
    finally:
        root.destroy()
