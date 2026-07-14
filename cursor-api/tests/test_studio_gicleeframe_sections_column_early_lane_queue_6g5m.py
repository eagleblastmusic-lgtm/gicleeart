from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
HOST_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view.py"
LIFECYCLE_PATH = ROOT / "giclee_app" / "ui" / "gicleeframe_view_lifecycle_inventory.py"
SECTION_LIST_SHELL_PATH = (
    ROOT / "giclee_app" / "ui" / "gicleeframe_view_section_list_shell.py"
)


def _view_text() -> str:
    return HOST_PATH.read_text(encoding="utf-8")


def _lifecycle_text() -> str:
    return LIFECYCLE_PATH.read_text(encoding="utf-8")


def _section_list_shell_text() -> str:
    return SECTION_LIST_SHELL_PATH.read_text(encoding="utf-8")


def test_init_refresh_light_defer_ms_constant_exists() -> None:
    assert "_GF_INIT_REFRESH_LIGHT_DEFER_MS = 0" in _lifecycle_text()


def test_init_refresh_light_scheduled_event_exists() -> None:
    lifecycle_text = _lifecycle_text()

    start = lifecycle_text.index("def _schedule_init_refresh_light")
    end = lifecycle_text.index("def _run_init_refresh_light_deferred", start)
    body = lifecycle_text[start:end]

    assert "studio.gicleeframe.init_refresh.light_scheduled" in body
    assert "delay_ms=_GF_INIT_REFRESH_LIGHT_DEFER_MS" in body
    assert "_sections_column_early_lane_scheduled_mono" in body


def test_init_refresh_light_not_sync_in_view_init() -> None:
    host_text = _view_text()

    start = host_text.index("def __init__")
    end = host_text.index("def _apply_edit_to_draft", start)
    body = host_text[start:end]

    assert "_schedule_init_refresh_light()" in body
    assert "self._refresh_inventory_light(warn_if_draft=False)" not in body


def test_init_refresh_light_deferred_runs_after_early_lane_queue() -> None:
    host_text = _view_text()
    lifecycle_text = _lifecycle_text()
    shell_text = _section_list_shell_text()

    init_start = host_text.index("def __init__")
    init_end = host_text.index("def _apply_edit_to_draft", init_start)
    init_body = host_text[init_start:init_end]

    critical_start = lifecycle_text.index("def _build_page_editor_section_critical")
    critical_end = lifecycle_text.index("def _build_workspace_skeleton_column", critical_start)
    critical_body = lifecycle_text[critical_start:critical_end]

    assert "_schedule_sections_column_early_lane()" in critical_body
    assert init_body.index("_build_shell()") < init_body.index(
        "_schedule_init_refresh_light()"
    )
    assert shell_text.index("def _schedule_sections_column_early_lane") < lifecycle_text.index(
        "def _schedule_init_refresh_light"
    )


def test_init_refresh_light_preserves_async_inventory_and_finalize_span() -> None:
    lifecycle_text = _lifecycle_text()

    run_start = lifecycle_text.index("def _run_init_refresh_light_deferred")
    run_end = lifecycle_text.index("def _finish_init_refresh_light", run_start)
    run_body = lifecycle_text[run_start:run_end]

    assert "run_async(" in run_body
    assert "build_gicleeframe_page_inventory(find_components_dir())" in run_body
    assert "self._finish_init_refresh_light" in run_body
    assert "on_error=" in run_body

    finish_start = run_end
    finish_end = lifecycle_text.index(
        "def _bootstrap_section_list_after_inventory_light",
        finish_start,
    )
    finish_body = lifecycle_text[finish_start:finish_end]

    assert 'span("studio.gicleeframe.init_refresh.light")' in finish_body
    assert "self._refresh_inventory_light(" in finish_body
    assert "prebuilt_inventory=prebuilt_inventory" in finish_body
    assert "self._bootstrap_section_list_after_inventory_light()" in finish_body


def test_bootstrap_section_list_after_inventory_light_lazy_shell_path() -> None:
    lifecycle_text = _lifecycle_text()

    start = lifecycle_text.index("def _bootstrap_section_list_after_inventory_light")
    end = lifecycle_text.index("def _flush_pending_section_list_if_needed", start)
    body = lifecycle_text[start:end]

    assert "_lazy_shell_enabled()" in body
    assert "_shell_sections_built" in body
    assert "_schedule_section_list_incremental()" in body


def test_runtime_marker_diagnostic_fields_exist() -> None:
    host_text = _view_text()

    start = host_text.index("studio.gicleeframe.runtime_marker")
    end = host_text.index("studio.gicleeframe.visual.enter", start)
    body = host_text[start:end]

    assert 'phase_marker="6G.5-M"' in body
    assert "module_file=__file__" in body
    assert "cwd=os.getcwd()" in body
    assert "sys_executable=sys.executable" in body
    assert "sys_path_0=" in body
    assert "sys_path_1=" in body
    assert "sys_path_2=" in body
    assert "has_schedule_init_refresh_light=" in body
    assert "has_init_refresh_light_scheduled_event=" in body


def test_early_lane_queue_6g5m_preserves_prior_6g5_markers() -> None:
    host_text = _view_text()
    shell_text = _section_list_shell_text()
    lifecycle_text = _lifecycle_text()
    assert 'phase_marker="6G.5-M"' in host_text
    assert "studio.gicleeframe.sections_column.early_lane_scheduled" in shell_text
    assert "studio.gicleeframe.sections_column.early_lane_enter" in lifecycle_text
    assert "studio.gicleeframe.section_list.column_shell_ready" in shell_text
    assert "studio.gicleeframe.section_list.column_ready_for_rows" in shell_text
    assert "studio.gicleeframe.section_list.incremental_scheduled" in lifecycle_text
    assert "studio.gicleeframe.section_list.first_visible_ready" in shell_text
    assert "studio.gicleeframe.visual.perceived_ready" in lifecycle_text
    assert "def _build_sections_column_shell" in shell_text
    assert "def _build_sections_column_extras" in shell_text
    assert "_section_list_extras_frame" in host_text
