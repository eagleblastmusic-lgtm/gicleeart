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
    run_copy_coverage_prompt_latest,
    run_coverage_latest,
    run_run_playbook,
    run_scenario_checklist,
)
from tools.performance_agent.report.coverage import (
    build_coverage_prompt,
    build_coverage_summary,
    build_run_playbook,
    build_scenario_checklist,
    classify_coverage_status,
    format_coverage_summary,
    format_scenario_checklist,
)
from tools.performance_agent.report.index import evaluate_report_health, summarize_report_bundle

TIMELINE_CSV = """scenario_id,display_title,scenario_name,start_ts,end_ts,duration_ms,completed,skipped,log_coverage_status,smoothness_score,main_complaint,note
dashboard_cold,Dashboard cold,Dashboard cold,2026-07-07T16:50:00Z,2026-07-07T16:50:10Z,10000.0,True,False,no_events_in_window,3,slow,
hub_theme,Hub theme,Hub theme,,,,False,True,skipped,,,
hub_products,Hub products,Hub products,,,,False,True,skipped,,,
gf_open,GICLÉE FRAME open,GICLÉE FRAME open,,,,False,True,skipped,,,
section_click_normal,Section normal,Section normal,,,,False,True,skipped,,,
section_click_fast,Section fast,Section fast,,,,False,True,skipped,,,
aba_cache,A B A,A B A,,,,False,True,skipped,,,
media_section,Media,Media,,,,False,True,skipped,,,
details_cta,Details,Details,,,,False,True,skipped,,,
"""


def _make_bundle(
    root: Path,
    dir_name: str,
    *,
    summary: dict | None = None,
    with_report_md: bool = True,
    timeline_csv: str | None = None,
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
    if timeline_csv is not None:
        (bundle_dir / "scenario_timeline.csv").write_text(timeline_csv, encoding="utf-8")
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


def _partial_summary(*, completed: int = 1, skipped: int = 8, total_events: int = 35) -> dict:
    coverage_entries: list[dict] = []
    for index in range(9):
        if index < completed:
            if index == 0 and completed == 1:
                coverage_entries.append(
                    {"scenario_id": "dashboard_cold", "status": "no_events_in_window"}
                )
            else:
                coverage_entries.append({"status": "ok"})
        elif index < completed + skipped:
            coverage_entries.append({"status": "skipped"})
        else:
            coverage_entries.append({"status": "not_completed"})
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": total_events,
        "malformed_lines": 0,
        "slow_event_count": 7,
        "suspect_count": 7,
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=completed, skipped=skipped, total=9)},
        "scenario_log_coverage": coverage_entries,
    }


def _no_events_summary() -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": 0,
        "malformed_lines": 0,
        "slow_event_count": 0,
        "suspect_count": 0,
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        "scenario_log_coverage": [{"status": "skipped"} for _ in range(9)],
    }


def _partial_light_summary() -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": 80,
        "malformed_lines": 0,
        "slow_event_count": 5,
        "suspect_count": 3,
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=7, skipped=2, total=9)},
        "scenario_log_coverage": [
            *[{"status": "ok"} for _ in range(6)],
            {"scenario_id": "details_cta", "status": "missing_expected_events"},
            {"status": "skipped"},
            {"status": "skipped"},
        ],
    }


@pytest.mark.parametrize(
    ("summary", "timeline_csv", "expected_status"),
    [
        (_ready_summary(), None, "GOOD_COVERAGE"),
        (_partial_summary(completed=8, skipped=1), None, "GOOD_COVERAGE"),
        (_partial_light_summary(), None, "WEAK_COVERAGE_LIGHT"),
        (_partial_summary(completed=1, skipped=8), TIMELINE_CSV, "WEAK_COVERAGE"),
        (_no_events_summary(), None, "NO_EVENTS"),
    ],
)
def test_classify_coverage_status(
    tmp_path: Path,
    summary: dict,
    timeline_csv: str | None,
    expected_status: str,
) -> None:
    bundle = _make_bundle(
        tmp_path,
        "test_bundle",
        summary=summary,
        timeline_csv=timeline_csv,
    )
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)
    from tools.performance_agent.report.insights import build_timeline_summary

    timeline = build_timeline_summary(entry)
    assert classify_coverage_status(entry, health, timeline) == expected_status


def test_classify_broken_coverage(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "broken_bundle", summary=None, with_report_md=False)
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)
    from tools.performance_agent.report.insights import build_timeline_summary

    timeline = build_timeline_summary(entry)
    assert classify_coverage_status(entry, health, timeline) == "BROKEN_COVERAGE"


def test_format_coverage_summary_contains_recovery_sections(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "partial_bundle",
        summary=_partial_summary(),
        timeline_csv=TIMELINE_CSV,
    )
    entry = summarize_report_bundle(bundle)
    text = format_coverage_summary(build_coverage_summary(entry))

    assert "completed: 1/9" in text
    assert "skipped: 8/9" in text
    assert "Weak scenarios:" in text
    assert "dashboard_cold — no_events_in_window" in text
    assert "Recovery checklist:" in text
    assert "python -m tools.performance_agent --run" in text
    assert "Likely causes:" in text


def test_scenario_checklist_has_nine_scenarios() -> None:
    items = build_scenario_checklist("giclee_studio")
    assert len(items) == 9
    ids = {item.scenario_id for item in items}
    assert "dashboard_cold" in ids
    assert "gf_open" in ids
    assert "details_cta" in ids


def test_format_scenario_checklist_contains_operator_fields() -> None:
    items = build_scenario_checklist("giclee_studio")
    text = format_scenario_checklist(items, profile_id="giclee_studio")

    assert "Scenarios: 9" in text
    assert "Operator action:" in text
    assert "Coverage risk:" in text
    assert "dashboard_cold" in text


def test_run_playbook_contains_workflow_commands() -> None:
    text = build_run_playbook("giclee_studio")

    assert "Before run:" in text
    assert "During run:" in text
    assert "After run:" in text
    assert "python -m tools.performance_agent --run" in text
    assert "--health-latest" in text
    assert "--coverage-latest" in text
    assert "1/9 coverage is not performance evidence" in text


def test_coverage_prompt_contains_guardrails_and_weak_scenarios(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "partial_bundle",
        summary=_partial_summary(),
        timeline_csv=TIMELINE_CSV,
    )
    entry = summarize_report_bundle(bundle)
    prompt = build_coverage_prompt(entry, workspace_root=tmp_path)

    assert str(bundle.resolve()) in prompt
    assert "PARTIAL" in prompt
    assert "dashboard_cold" in prompt
    assert "Do not optimize Studio" in prompt
    assert "GICLÉE FRAME runtime" in prompt
    assert "Komponenty/*" in prompt
    assert "Do not commit or push" in prompt
    assert "Do not implement without user approval" in prompt


def test_cli_help_shows_pa3a_flags() -> None:
    parser = _build_parser()
    help_text = parser.format_help()
    for flag in (
        "--coverage-latest",
        "--coverage-report",
        "--scenario-checklist",
        "--run-playbook",
        "--coverage-prompt-latest",
        "--copy-coverage-prompt-latest",
    ):
        assert flag in help_text


def test_cli_run_playbook_does_not_crash(capsys) -> None:
    assert run_run_playbook(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert "full run playbook" in captured.out


def test_cli_scenario_checklist_does_not_crash(capsys) -> None:
    assert run_scenario_checklist(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert "scenario checklist" in captured.out


def test_cli_coverage_latest_no_reports(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "tools.performance_agent.__main__.get_profile",
        lambda profile_id: MagicMock(resolve_output_root=lambda: tmp_path),
    )
    monkeypatch.setattr(
        "tools.performance_agent.__main__.discover_report_dirs",
        lambda output_root, profile_id: [],
    )
    assert run_coverage_latest(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert "No performance report bundles found" in captured.out


def test_copy_coverage_prompt_latest_uses_clipboard_helper(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    bundle = _make_bundle(
        tmp_path,
        "partial_bundle",
        summary=_partial_summary(),
        timeline_csv=TIMELINE_CSV,
    )
    output_root = tmp_path
    monkeypatch.setattr(
        "tools.performance_agent.__main__.get_profile",
        lambda profile_id: MagicMock(resolve_output_root=lambda: output_root),
    )
    monkeypatch.setattr(
        "tools.performance_agent.__main__.discover_report_dirs",
        lambda root, profile_id: [bundle],
    )
    copied: list[str] = []

    def _fake_copy(text: str) -> None:
        copied.append(text)

    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        _fake_copy,
    )

    assert run_copy_coverage_prompt_latest(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert "Coverage recovery prompt copied to clipboard." in captured.out
    assert len(copied) == 1
    assert "Coverage Recovery" in copied[0]
