from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _section_list_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")


def _rendering_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")


def _combined_text() -> str:
    return (
        _view_text()
        + "\n"
        + _section_list_shell_text()
        + "\n"
        + _rendering_text()
    )


def test_sections_column_shell_and_extras_split_exists() -> None:
    text = _section_list_shell_text()
    assert "def _build_sections_column_shell" in text
    assert "def _build_sections_column_extras" in text
    text = _view_text()
    assert "def _build_sections_column_extras_deferred" in text


def test_sections_column_shell_ready_event_exists() -> None:
    text = _section_list_shell_text()

    start = text.index("def _build_sections_column_shell")
    end = text.index("def _create_section_list_scroll_frame", start)
    body = text[start:end]

    assert "studio.gicleeframe.section_list.column_shell_ready" in text
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in text
    assert "_section_list_extras_frame" in body
    assert "_section_list_static_lane" in body or "_section_list_scroll" in body
    assert "_make_card_title" not in body
    assert "_section_dropdown_popup" not in body


def test_sections_column_extras_no_pack_before_scroll() -> None:
    text = _section_list_shell_text()

    start = text.index("def _build_sections_column_extras")
    end = text.index("def _build_sections_column(", start)
    body = text[start:end]

    assert "before=self._section_list_scroll" not in body
    assert "_section_list_extras_frame" in body


def test_sections_column_extras_uses_shell_slot() -> None:
    text = _section_list_shell_text()

    shell_start = text.index("def _build_sections_column_shell")
    shell_end = text.index("def _create_section_list_scroll_frame", shell_start)
    shell_body = text[shell_start:shell_end]

    extras_start = text.index("def _build_sections_column_extras")
    extras_end = text.index("def _build_sections_column(", extras_start)
    extras_body = text[extras_start:extras_end]

    assert "_section_list_extras_frame = ctk.CTkFrame" in shell_body
    assert "self._section_list_extras_frame.pack" in shell_body
    list_pack_markers = (
        "self._section_list_static_lane.pack",
        "self._section_list_scroll.pack",
    )
    assert any(marker in shell_body for marker in list_pack_markers)
    assert shell_body.index("self._section_list_extras_frame.pack") < min(
        shell_body.index(marker)
        for marker in list_pack_markers
        if marker in shell_body
    )
    assert "_make_card_title(\n            extras_slot," in extras_body
    assert "studio.gicleeframe.sections_column.extras_skipped_missing_slot" in extras_body


def test_build_sections_column_extras_safe_before_full_layout() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        parent = ctk.CTkFrame(view)
        parent.pack()
        card = view._build_sections_column_shell(parent)
        view._build_sections_column_extras(card)
        assert view._section_list_extras_frame is not None
        assert view._sections_column_extras_built
        assert view._section_list_trigger is not None
        assert view._section_dropdown_popup is not None
    finally:
        root.destroy()


def test_build_sections_column_extras_skips_missing_slot_without_error() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        parent = ctk.CTkFrame(view)
        parent.pack()
        card = view._build_sections_column_shell(parent)
        view._section_list_extras_frame = None
        view._sections_column_extras_built = False
        view._build_sections_column_extras(card)
        assert not view._sections_column_extras_built
    finally:
        root.destroy()


def test_sections_column_extras_deferred_after_shell_ready() -> None:
    text = _view_text()

    start = text.index("def _build_sections_column_deferred")
    end = text.index("def _build_sections_column_extras_deferred", start)
    body = text[start:end]

    assert "studio.gicleeframe.sections_column.early_lane_enter" in body
    assert "build.sections_column.deferred.shell" in body
    assert "_flush_pending_section_list_if_needed()" in body
    assert "_build_sections_column_extras_deferred" in body
    assert body.index("_flush_pending_section_list_if_needed()") < body.index(
        "_build_sections_column_extras_deferred"
    )


def test_sections_column_early_lane_enter_event_exists() -> None:
    text = _view_text()

    start = text.index("def _build_sections_column_deferred")
    end = text.index("def _build_sections_column_extras_deferred", start)
    body = text[start:end]

    assert "studio.gicleeframe.sections_column.early_lane_enter" in body
    assert "queue_latency_ms=self._queue_latency_since_ms(" in body
    assert "_sections_column_early_lane_scheduled_mono" in body


def test_sections_column_queue_latency_instrumentation() -> None:
    text = _combined_text()
    assert "def _queue_latency_since_ms" in _view_text()
    assert "_sections_column_early_lane_scheduled_mono" in text
    assert "_section_list_column_ready_mono" in text
    assert "_section_list_incremental_scheduled_mono" in text
    assert "_section_list_incremental_enter_mono" in text

    assert "queue_latency_ms=self._queue_latency_since_ms(" in text
    assert "since_early_lane_enter_ms=self._queue_latency_since_ms(" in text


def test_sections_column_split_preserves_prior_6g5_markers() -> None:
    text = _combined_text()
    assert "_GF_SECTIONS_COLUMN_EARLY_DEFER_MS = 0" in text
    assert "studio.gicleeframe.sections_column.early_lane_scheduled" in text
    assert "studio.gicleeframe.section_list.first_visible_fast_lane" in text
    assert "studio.gicleeframe.section_list.incremental_scheduled" in text
    assert "studio.gicleeframe.section_list.incremental_enter" in text
    assert "studio.gicleeframe.section_list.first_visible_ready" in text
    assert "studio.gicleeframe.visual.perceived_ready" in text
