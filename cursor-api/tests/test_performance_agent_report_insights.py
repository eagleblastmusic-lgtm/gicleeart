from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.__main__ import (
    _build_parser,
    main,
    run_copy_cursor_prompt_latest,
    run_cursor_prompt_latest,
    run_hotspots_latest,
    run_timeline_latest,
)
from tools.performance_agent.report.insights import (
    build_cursor_prompt,
    build_hotspot_summary,
    build_timeline_summary,
    format_hotspot_summary,
    format_timeline_summary,
    load_scenario_timeline_csv,
    load_slow_events_csv,
)
from tools.performance_agent.report.index import summarize_report_bundle


SLOW_CSV = """line_no,ts,event,ms,ms_field,severity,element_id,element_type,stage,module
98,2026-07-07T16:50:01Z,studio.gicleeframe.selection.populate_done,420.0,elapsed_ms,warning,,,selection,frame
123,2026-07-07T16:50:02Z,studio.gicleeframe.details_on_demand.ready,812.4,since_enter_ms,major,,,details,frame
124,2026-07-07T16:50:03Z,studio.gicleeframe.selection.populate_done,390.0,elapsed_ms,warning,,,selection,frame
125,2026-07-07T16:50:04Z,studio.gicleeframe.details_on_demand.ready,500.0,since_enter_ms,warning,,,details,frame
126,2026-07-07T16:50:05Z,studio.dashboard.visual.visible_ready,210.0,elapsed_ms,warning,,,dashboard,dashboard
127,2026-07-07T16:50:06Z,studio.hub.visual.visible_ready,180.0,elapsed_ms,warning,,,hub,hub
128,2026-07-07T16:50:07Z,studio.gicleeframe.selection.populate_done,150.0,elapsed_ms,warning,,,selection,frame
"""

TIMELINE_CSV = """scenario_id,display_title,scenario_name,start_ts,end_ts,duration_ms,completed,skipped,log_coverage_status,smoothness_score,main_complaint,note
dashboard_cold,Dashboard cold,Dashboard cold,2026-07-07T16:50:00Z,2026-07-07T16:50:10Z,10000.0,True,False,no_events_in_window,3,slow,
hub_theme,Hub theme,Hub theme,,,,False,True,skipped,,,
hub_products,Hub products,Hub products,,,,False,True,skipped,,,
gf_open,GICLÉE FRAME open,GICLÉE FRAME open,,,,False,True,skipped,,,
gf_details,GICLÉE FRAME details,GICLÉE FRAME details,,,,False,True,skipped,,,
gf_selection,GICLÉE FRAME selection,GICLÉE FRAME selection,,,,False,True,skipped,,,
gf_mockup,GICLÉE FRAME mockup,GICLÉE FRAME mockup,,,,False,True,skipped,,,
gf_checkout,GICLÉE FRAME checkout,GICLÉE FRAME checkout,,,,False,True,skipped,,,
gf_close,GICLÉE FRAME close,GICLÉE FRAME close,,,,False,True,skipped,,,
"""


def _make_bundle(
    root: Path,
    dir_name: str,
    *,
    summary: dict | None = None,
    with_report_md: bool = True,
) -> Path:
    bundle_dir = root / dir_name
    bundle_dir.mkdir(parents=True)
    if with_report_md:
        (bundle_dir / "report.md").write_text("# report\n", encoding="utf-8")
    if summary is not None:
        (bundle_dir / "summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
    return bundle_dir


def _ux_scenarios(*, completed: int, skipped: int, total: int = 9) -> list[dict]:
    scenarios: list[dict] = []
    for index in range(total):
        if index < completed:
            scenarios.append({"scenario_id": f"s{index}", "completed": True, "skipped": False})
        elif index < completed + skipped:
            scenarios.append({"scenario_id": f"s{index}", "completed": False, "skipped": True})
        else:
            scenarios.append({"scenario_id": f"s{index}", "completed": False, "skipped": False})
    return scenarios


def _partial_summary(*, slow: int = 7) -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": 35,
        "malformed_lines": 0,
        "slow_event_count": slow,
        "suspect_count": 7,
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
        "scenario_log_coverage": [
            {"scenario_id": "dashboard_cold", "status": "no_events_in_window"},
            *[{"status": "skipped"} for _ in range(8)],
        ],
    }


def _ready_summary(*, slow: int = 3, suspects: int = 2, total_events: int = 120) -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": total_events,
        "malformed_lines": 0,
        "slow_event_count": slow,
        "suspect_count": suspects,
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=9, skipped=0, total=9)},
        "scenario_log_coverage": [{"status": "ok"} for _ in range(9)],
    }


def _insights_bundle(
    root: Path,
    dir_name: str,
    *,
    summary: dict,
    slow_csv: str | None = SLOW_CSV,
    timeline_csv: str | None = TIMELINE_CSV,
) -> Path:
    bundle = _make_bundle(root, dir_name, summary=summary)
    if slow_csv is not None:
        (bundle / "slow_events.csv").write_text(slow_csv, encoding="utf-8")
    if timeline_csv is not None:
        (bundle / "scenario_timeline.csv").write_text(timeline_csv, encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")
    return bundle


def _mock_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = MagicMock()
    profile.resolve_output_root.return_value = tmp_path
    monkeypatch.setattr("tools.performance_agent.__main__.get_profile", lambda _profile_id: profile)


def test_load_slow_events_csv_reads_rows_and_parses_ms(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "slow_events.csv").write_text(SLOW_CSV, encoding="utf-8")

    rows = load_slow_events_csv(bundle)

    assert len(rows) == 7
    assert float(rows[0]["ms"]) == 420.0


def test_load_slow_events_csv_missing_file_returns_empty(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()

    assert load_slow_events_csv(bundle) == []


def test_load_scenario_timeline_csv_parses_bool_strings(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    csv_text = (
        "scenario_id,completed,skipped,log_coverage_status\n"
        "a,True,False,ok\n"
        "b,false,1,skipped\n"
        "c,0,yes,no_events_in_window\n"
    )
    (bundle / "scenario_timeline.csv").write_text(csv_text, encoding="utf-8")

    rows = load_scenario_timeline_csv(bundle)

    assert len(rows) == 3
    summary = build_timeline_summary(summarize_report_bundle(bundle))
    assert summary.completed == 1
    assert summary.skipped == 2


def test_hotspots_groups_events_and_top_slow_rows(tmp_path: Path) -> None:
    bundle = _insights_bundle(
        tmp_path,
        "20260707-165000_giclee_studio",
        summary=_partial_summary(),
    )
    entry = summarize_report_bundle(bundle)

    output = format_hotspot_summary(build_hotspot_summary(entry))

    assert "studio.gicleeframe.selection.populate_done — 3" in output
    assert "420.0ms [warning]" in output
    assert "812.4ms" not in output
    assert "non-duration timing fields" in output
    assert "Health: PARTIAL" in output


def test_hotspots_excludes_selection_click_since_enter_latency(tmp_path: Path) -> None:
    click_csv = """line_no,ts,event,ms,ms_field,severity,element_id,element_type,stage,module
1,2026-07-07T21:28:50Z,studio.gicleeframe.selection.click,141406.27,since_enter_ms,major,sec-1,section,,
2,2026-07-07T21:28:50Z,studio.gicleeframe.details_on_demand.ready,812.4,since_request_ms,major,,,details,
"""
    bundle = _insights_bundle(
        tmp_path,
        "20260707-212000_giclee_studio",
        summary=_partial_summary(),
        slow_csv=click_csv,
    )
    output = format_hotspot_summary(build_hotspot_summary(summarize_report_bundle(bundle)))

    assert "selection.click" not in output or "141406" not in output
    assert "812.4ms [major]" in output
    assert "since_enter_ms" in output


def test_hotspots_missing_csv_shows_clear_message(tmp_path: Path) -> None:
    bundle = _insights_bundle(
        tmp_path,
        "20260707-170000_giclee_studio",
        summary=_partial_summary(slow=7),
        slow_csv=None,
    )
    entry = summarize_report_bundle(bundle)

    output = format_hotspot_summary(build_hotspot_summary(entry))

    assert "slow_events.csv: not present in bundle" in output
    assert "total (from summary.json fallback): 7" in output


def test_timeline_counts_completed_skipped_and_weakest(tmp_path: Path) -> None:
    bundle = _insights_bundle(
        tmp_path,
        "20260707-165000_giclee_studio",
        summary=_partial_summary(),
    )
    entry = summarize_report_bundle(bundle)

    output = format_timeline_summary(build_timeline_summary(entry))

    assert "completed: 1/9" in output
    assert "skipped: 8/9" in output
    assert "no_events_in_window: 1" in output
    assert "dashboard_cold — no_events_in_window" in output
    assert "hub_theme — skipped" in output


def test_cursor_prompt_ready_allows_review_with_guardrails(tmp_path: Path) -> None:
    bundle = _insights_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_ready_summary(),
    )
    entry = summarize_report_bundle(bundle)

    prompt = build_cursor_prompt(entry)

    assert "Health:\nREADY" in prompt
    assert "propose P0 fixes" in prompt.lower() or "P0 fixes" in prompt
    assert "Do not modify GicleeApp Studio code." in prompt
    assert "Do not change GICLÉE FRAME runtime." in prompt
    assert "Do not edit Komponenty/*." in prompt
    assert "Do not commit or push." in prompt


def test_cursor_prompt_partial_warns_about_weak_coverage(tmp_path: Path) -> None:
    bundle = _insights_bundle(
        tmp_path,
        "20260707-165000_giclee_studio",
        summary=_partial_summary(),
    )
    entry = summarize_report_bundle(bundle)

    prompt = build_cursor_prompt(entry)

    assert "Health:\nPARTIAL" in prompt
    assert "weak scenario coverage" in prompt
    assert "Do not plan broad Studio optimization" in prompt


def test_cursor_prompt_needs_rerun_blocks_performance_code_analysis(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "20260707-180000_giclee_studio",
        summary={
            **_partial_summary(),
            "total_events": 0,
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        },
    )
    (bundle / "slow_events.csv").write_text(SLOW_CSV, encoding="utf-8")
    (bundle / "scenario_timeline.csv").write_text(TIMELINE_CSV, encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")
    entry = summarize_report_bundle(bundle)

    prompt = build_cursor_prompt(entry)

    assert "NEEDS_RERUN" in prompt
    assert "Do not analyze Studio performance code" in prompt
    assert "Do not commit or push." in prompt


def test_parser_help_lists_pa2b_flags() -> None:
    parser = _build_parser()
    help_text = parser.format_help()

    assert "--hotspots-latest" in help_text
    assert "--hotspots-report" in help_text
    assert "--timeline-latest" in help_text
    assert "--timeline-report" in help_text
    assert "--cursor-prompt-latest" in help_text
    assert "--cursor-prompt-report" in help_text
    assert "--copy-cursor-prompt-latest" in help_text


def test_cli_hotspots_latest_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _insights_bundle(tmp_path, "20260707-165000_giclee_studio", summary=_partial_summary())

    assert run_hotspots_latest(profile_id="giclee_studio") == 0


def test_cli_timeline_latest_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _insights_bundle(tmp_path, "20260707-165000_giclee_studio", summary=_partial_summary())

    assert run_timeline_latest(profile_id="giclee_studio") == 0


def test_cli_cursor_prompt_latest_prints_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _insights_bundle(tmp_path, "20260707-165000_giclee_studio", summary=_partial_summary())

    assert run_cursor_prompt_latest(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert "# Cursor Prompt — Performance Agent Report Review" in captured.out


def test_copy_cursor_prompt_latest_uses_clipboard_helper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _insights_bundle(tmp_path, "20260707-165000_giclee_studio", summary=_partial_summary())
    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    assert run_copy_cursor_prompt_latest(profile_id="giclee_studio") == 0
    assert copied
    assert "Cursor performance review prompt copied to clipboard." in capsys.readouterr().out


def test_main_hotspots_latest_no_reports_exit_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _mock_profile(monkeypatch, tmp_path)

    assert main(["--hotspots-latest"]) == 0
