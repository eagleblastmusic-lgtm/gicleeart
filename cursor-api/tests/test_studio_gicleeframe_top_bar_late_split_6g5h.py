from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def _top_bar_text() -> str:
    return (ROOT / "giclee_app" / "ui" / "gicleeframe_view_top_bar.py").read_text(
        encoding="utf-8"
    )


def _constant_int(text: str, name: str) -> int:
    match = re.search(rf"^{re.escape(name)}\s*=\s*(\d+)$", text, re.MULTILINE)
    assert match is not None, f"missing integer constant: {name}"
    return int(match.group(1))


def test_top_bar_late_split_preserves_staggered_ordering() -> None:
    text = _top_bar_text()
    overall_ms = _constant_int(text, "_GF_TOP_BAR_ACTIONS_LATE_DEFER_MS")
    context_ms = _constant_int(text, "_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS")
    primary_ms = _constant_int(text, "_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS")
    secondary_ms = _constant_int(text, "_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS")

    assert 0 <= context_ms < primary_ms < secondary_ms <= overall_ms


def test_top_bar_late_split_methods_exist() -> None:
    text = _top_bar_text()
    assert "_schedule_top_bar_actions_late_build" in text
    assert "_start_top_bar_actions_late_build" in text
    assert "_build_context_bar_actions_late" in text
    assert "_build_command_bar_primary_actions_late" in text
    assert "_build_command_bar_secondary_actions_late" in text


def test_top_bar_late_split_events_exist() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.top_bar.actions_late_scheduled" in text
    assert "studio.gicleeframe.top_bar.actions_late_start" in text
    assert "studio.gicleeframe.top_bar.context_actions_late_done" in text
    assert "studio.gicleeframe.top_bar.primary_actions_late_done" in text
    assert "studio.gicleeframe.top_bar.secondary_actions_late_done" in text
    assert "studio.gicleeframe.top_bar.actions_late_done" in text
    assert "studio.gicleeframe.build.context_bar.actions_late" in text
    assert "studio.gicleeframe.build.command_bar.primary_actions_late" in text
    assert "studio.gicleeframe.build.command_bar.secondary_actions_late" in text


def _editor_shell_text() -> str:
    return (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_editor_shell.py"
    ).read_text(encoding="utf-8")


def test_top_bar_late_split_preserves_prior_optimizations() -> None:
    text = _top_bar_text()
    assert "studio.gicleeframe.context_bar.actions_lazy_startup" in text
    assert "studio.gicleeframe.command_bar.primary_actions_lazy_startup" in text
    assert "studio.gicleeframe.command_bar.secondary_actions_lazy_startup" in text

    host = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
    ).read_text(encoding="utf-8")
    rendering = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_rendering.py"
    ).read_text(encoding="utf-8")
    shell = (
        ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
    ).read_text(encoding="utf-8")
    combined = host + "\n" + shell + "\n" + rendering + "\n" + _editor_shell_text()
    assert "studio.gicleeframe.section_list.first_visible_ready" in combined
    assert "studio.gicleeframe.editor.fields_lazy_startup" in combined
    assert "studio.gicleeframe.editor.identity_card_lazy_startup" in combined
    assert "studio.gicleeframe.populate_editor.preview_deferred_requested" in combined


def test_start_schedules_staggered_late_builds() -> None:
    text = _top_bar_text()
    body = text.split("def _start_top_bar_actions_late_build", 1)[1].split(
        "\n    def ", 1
    )[0]
    assert "_GF_TOP_BAR_CONTEXT_ACTIONS_LATE_DEFER_MS" in body
    assert "_build_context_bar_actions_late" in body
    assert "_GF_TOP_BAR_PRIMARY_ACTIONS_LATE_DEFER_MS" in body
    assert "_build_command_bar_primary_actions_late" in body
    assert "_GF_TOP_BAR_SECONDARY_ACTIONS_LATE_DEFER_MS" in body
    assert "_build_command_bar_secondary_actions_late" in body


def test_actions_late_done_only_after_secondary() -> None:
    text = _top_bar_text()
    body = text.split("def _build_command_bar_secondary_actions_late", 1)[1].split(
        "\n    def ", 1
    )[0]
    assert "studio.gicleeframe.top_bar.secondary_actions_late_done" in body
    assert 'studio.gicleeframe.top_bar.actions_late_done"' in body
    secondary_done = body.index("secondary_actions_late_done")
    actions_done = body.index('top_bar.actions_late_done"')
    assert secondary_done < actions_done
