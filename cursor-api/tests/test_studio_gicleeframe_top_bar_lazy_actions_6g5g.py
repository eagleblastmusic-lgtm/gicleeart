from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _view_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view.py").read_text(
        encoding="utf-8"
    )


def _editor_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
    ).read_text(encoding="utf-8")


def _top_bar_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view_top_bar.py").read_text(
        encoding="utf-8"
    )


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


def test_top_bar_lazy_actions_contract_and_methods_exist() -> None:
    text = _top_bar_text()
    overall_ms = _constant_int(text, "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS")
    secondary_ms = _constant_int(text, "_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS")

    assert 0 < secondary_ms <= overall_ms
    assert "_schedule_top_bar_actions_late_build" in text
    assert "_start_top_bar_actions_late_build" in text

    host = _view_text()
    assert "_top_bar_actions_late_started = False" in host
    assert "_top_bar_actions_late_done = False" in host


def test_top_bar_lazy_startup_events_exist() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.context_bar.actions_lazy_startup" in text
    assert "studio.gicleeframe.command_bar.primary_actions_lazy_startup" in text
    assert "studio.gicleeframe.command_bar.secondary_actions_lazy_startup" in text


def test_top_bar_late_build_events_exist() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.top_bar.actions_late_start" in text
    assert "studio.gicleeframe.top_bar.actions_late_done" in text
    assert "studio.gicleeframe.build.context_bar.actions_late" in text
    assert "studio.gicleeframe.build.command_bar.primary_actions_late" in text
    assert "studio.gicleeframe.build.command_bar.secondary_actions_late" in text


def test_startup_path_keeps_diagnostic_spans_for_placeholders() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.build.context_bar.actions" in text
    assert "studio.gicleeframe.build.command_bar.primary_actions" in text
    assert "studio.gicleeframe.build.command_bar.secondary_actions" in text


def _lifecycle_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
    ).read_text(encoding="utf-8")


def test_build_shell_schedules_top_bar_late_build() -> None:
    lifecycle_text = _lifecycle_text()
    body = lifecycle_text.split("def _build_shell", 1)[1].split("\n    def ", 1)[0]
    assert "_schedule_top_bar_actions_late_build()" in body


def test_startup_uses_placeholders_not_full_actions() -> None:
    text = _top_bar_text()

    ctx_start = text.index("def _build_context_bar")
    ctx_end = text.index("def _build_context_bar_actions_placeholder")
    ctx_body = text[ctx_start:ctx_end]
    assert "_build_context_bar_actions_placeholder" in ctx_body
    assert "_build_context_bar_actions(" not in ctx_body

    cmd_start = text.index("def _build_command_bar(self, parent:")
    cmd_end = text.index("def _build_command_bar_primary_actions(self, inner:")
    cmd_body = text[cmd_start:cmd_end]
    assert "_command_bar_primary_placeholder" in cmd_body
    assert "_command_bar_secondary_placeholder" in cmd_body
    assert "_build_command_bar_primary_actions(" not in cmd_body


def _combined_text() -> str:
    shell = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")
    rendering = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")
    return _view_text() + "\n" + shell + "\n" + rendering


def test_top_bar_lazy_preserves_prior_6g5_optimizations() -> None:
    lifecycle_text = _lifecycle_text()
    editor_text = _editor_shell_text()
    shell_text = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")
    rendering_text = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")
    assert "studio.gicleeframe.editor.fields_lazy_startup" in editor_text
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in editor_text
    assert "studio.gicleeframe.control.deferred_readiness_late" in lifecycle_text
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in editor_text
    assert "studio.gicleeframe.section_list.first_visible_ready" in rendering_text
    assert "studio.gicleeframe.section_list.first_visible_ready" in shell_text
    assert "def _build_sections_column_shell" in shell_text
