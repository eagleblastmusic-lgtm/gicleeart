"""6G.5-R.DIAG — perceived ready gate attribution instrumentation."""

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


def test_perceived_ready_gate_check_event_exists() -> None:
    text = _view_text()
    body = _method_block(text, "_try_mark_perceived_ready")
    assert "studio.gicleeframe.visual.perceived_ready_gate_check" in body
    for field in (
        "since_enter_ms",
        "shell_sections_built",
        "shell_editor_built",
        "shell_control_built",
        "section_list_first_visible_built",
        "missing_gates",
        "trigger",
    ):
        assert field in body


def test_visual_gate_ready_events_exist() -> None:
    text = _view_text()
    assert "_log_visual_gate_ready" in text
    for gate in ("sections", "editor", "control", "first_visible"):
        assert f'"{gate}"' in text or f"'{gate}'" in text
    assert 'f"studio.gicleeframe.visual.gate.{gate}_ready"' in text


def test_editor_control_deferred_diagnostic_events_exist() -> None:
    text = _view_text()
    for event in (
        "studio.gicleeframe.editor.deferred_scheduled",
        "studio.gicleeframe.editor.skeleton_enter",
        "studio.gicleeframe.editor.skeleton_done",
        "studio.gicleeframe.control.deferred_scheduled",
        "studio.gicleeframe.control.skeleton_enter",
        "studio.gicleeframe.control.skeleton_done",
        "studio.gicleeframe.control.structure_enter",
        "studio.gicleeframe.control.structure_done",
    ):
        assert event in text


def test_try_mark_perceived_ready_logs_missing_gates_before_final_ready() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        view._visual_enter_mono = __import__("time").perf_counter()
        view._shell_sections_built = True
        view._shell_editor_built = False
        view._shell_control_built = False
        view._section_list_first_visible_built = False

        logged: list[tuple[str, dict]] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append((event, kwargs))

        with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
            view._try_mark_perceived_ready(trigger="test_partial")

        assert not view._perceived_ready_logged
        gate_checks = [
            item for item in logged if item[0] == "studio.gicleeframe.visual.perceived_ready_gate_check"
        ]
        assert len(gate_checks) == 1
        _, fields = gate_checks[0]
        assert fields["shell_sections_built"] is True
        assert fields["shell_editor_built"] is False
        assert fields["missing_gates"] == "editor,control,first_visible"
        assert fields["trigger"] == "test_partial"
        assert not any(item[0] == "studio.gicleeframe.visual.perceived_ready" for item in logged)
    finally:
        root.destroy()


def test_perceived_ready_logs_only_once() -> None:
    import customtkinter as ctk

    from giclee_app.ui.gicleeframe_view import GicleeFrameView

    root = ctk.CTk()
    root.withdraw()
    try:
        view = GicleeFrameView(root)
        view.pack()
        view._visual_enter_mono = __import__("time").perf_counter()
        view._shell_sections_built = True
        view._shell_editor_built = True
        view._shell_control_built = True
        view._section_list_first_visible_built = True

        logged: list[str] = []

        def _capture(event: str, **kwargs) -> None:  # type: ignore[no-untyped-def]
            logged.append(event)

        with patch("giclee_app.ui.gicleeframe_view.log_event", side_effect=_capture):
            view._try_mark_perceived_ready(trigger="first")
            view._try_mark_perceived_ready(trigger="second")

        perceived = [
            event for event in logged if event == "studio.gicleeframe.visual.perceived_ready"
        ]
        assert len(perceived) == 1
        assert view._perceived_ready_logged
    finally:
        root.destroy()


def test_perceived_gate_diag_preserves_prior_6g5_markers() -> None:
    text = _view_text()
    for marker in (
        "studio.gicleeframe.section_list.static_lane_ready",
        "studio.gicleeframe.section_list.first_visible_ready",
        "studio.gicleeframe.visual.perceived_ready",
        "studio.gicleeframe.section_list.scroll_upgrade_scheduled",
        "studio.gicleeframe.sections_column.early_lane_scheduled",
    ):
        assert marker in text
