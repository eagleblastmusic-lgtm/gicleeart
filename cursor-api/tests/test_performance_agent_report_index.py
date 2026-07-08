from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.report.index import (
    CopyBlockNotFoundError,
    discover_report_dirs,
    evaluate_report_health,
    extract_copy_for_chatgpt,
    extract_copy_for_chatgpt_text,
    format_latest_report,
    format_no_reports_message,
    format_report_health,
    format_report_list,
    load_summary_json,
    summarize_report_bundle,
)


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


def _sample_summary(*, mode: str = "run", slow: int = 3, suspects: int = 2) -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": mode,
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": 42,
        "malformed_lines": 0,
        "slow_event_count": slow,
        "suspect_count": suspects,
        "ux_conflicts": [{"id": "UX_TEST"}],
        "log_coverage_conflicts": [],
        "scenario_log_coverage": [
            {"scenario_id": "hub_theme", "status": "ok"},
            {"scenario_id": "gf_open", "status": "missing_expected_events"},
        ],
    }


def test_discover_report_dirs_skips_archive(tmp_path: Path) -> None:
    (tmp_path / "_archive").mkdir()
    _make_bundle(tmp_path, "20260707-120000_giclee_studio", summary=_sample_summary())
    _make_bundle(tmp_path / "_archive", "ignored", summary=_sample_summary())
    _make_bundle(tmp_path, "other_profile_dir", summary=_sample_summary())

    discovered = discover_report_dirs(tmp_path, "giclee_studio")

    assert len(discovered) == 1
    assert discovered[0].name == "20260707-120000_giclee_studio"


def test_discover_report_dirs_sorts_newest_first(tmp_path: Path) -> None:
    _make_bundle(tmp_path, "20260707-100000_giclee_studio", summary=_sample_summary())
    _make_bundle(tmp_path, "20260707-230000_giclee_studio", summary=_sample_summary())
    _make_bundle(tmp_path, "20260707-150000_giclee_studio", summary=_sample_summary())

    discovered = discover_report_dirs(tmp_path, "giclee_studio")

    assert [path.name for path in discovered] == [
        "20260707-230000_giclee_studio",
        "20260707-150000_giclee_studio",
        "20260707-100000_giclee_studio",
    ]


def test_latest_summary_with_valid_summary_json(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "20260707-160000_giclee_studio",
        summary=_sample_summary(slow=7, suspects=4),
    )
    (bundle / "slow_events.csv").write_text("line_no\n", encoding="utf-8")
    (bundle / "scenario_timeline.csv").write_text("scenario_id\n", encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")

    entry = summarize_report_bundle(bundle)
    output = format_latest_report(entry)

    assert entry.mode == "run"
    assert entry.total_events == 42
    assert entry.slow_event_count == 7
    assert entry.suspect_count == 4
    assert entry.ux_conflict_count == 1
    assert entry.log_coverage_conflict_count == 0
    assert entry.coverage_status_counts == {
        "missing_expected_events": 1,
        "ok": 1,
    }
    assert entry.has_report_md is True
    assert entry.has_summary_json is True
    assert "Performance Agent — latest report bundle" in output
    assert "Slow events:      7" in output
    assert "For ChatGPT review, paste the COPY FOR CHATGPT block from report.md." in output


def test_latest_graceful_without_summary_json(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "20260707-170000_giclee_studio",
        summary=None,
        with_report_md=True,
    )

    entry = summarize_report_bundle(bundle)
    output = format_latest_report(entry)

    assert load_summary_json(bundle) == {}
    assert entry.mode is None
    assert entry.slow_event_count is None
    assert entry.has_summary_json is False
    assert entry.has_report_md is True
    assert "Slow events:      n/a" in output
    assert "summary.json           no" in output


def test_format_report_list_multiple_entries(tmp_path: Path) -> None:
    first = summarize_report_bundle(
        _make_bundle(
            tmp_path,
            "20260707-200000_giclee_studio",
            summary=_sample_summary(slow=10, suspects=5),
        )
    )
    second = summarize_report_bundle(
        _make_bundle(
            tmp_path,
            "20260707-190000_giclee_studio",
            summary=_sample_summary(slow=2, suspects=1),
        )
    )

    output = format_report_list([first, second])

    assert "20260707-200000_giclee_studio" in output
    assert "20260707-190000_giclee_studio" in output
    assert "slow=10" in output
    assert "slow=2" in output
    assert "report.md=yes" in output


def test_no_reports_message_is_clear_without_crash(tmp_path: Path) -> None:
    empty_root = tmp_path / "performance"
    empty_root.mkdir()

    discovered = discover_report_dirs(empty_root, "giclee_studio")
    message = format_no_reports_message(output_root=empty_root, profile_id="giclee_studio")
    listed = format_report_list([])

    assert discovered == []
    assert "No performance report bundles found." in message
    assert "giclee_studio" in message
    assert "No performance report bundles found." in listed


def _sample_report_md(*, with_technical: bool = True) -> str:
    copy_block = """## COPY FOR CHATGPT

Paste this block into ChatGPT (Performance Analyst mode).

### What I need ChatGPT to analyze
1. Which suspects are true UX problems vs expected deferred work?
5. What is the single safest P0 fix to try next?
"""
    if not with_technical:
        return copy_block + "\n---\n"
    return (
        copy_block
        + "\n---\n\n# Performance Audit Report — GicleeApp Studio Preview\n\n## Source\n"
    )


def test_extract_copy_for_chatgpt_text_strips_technical_section_and_separator() -> None:
    block = extract_copy_for_chatgpt_text(_sample_report_md())

    assert block.startswith("## COPY FOR CHATGPT")
    assert block.endswith("5. What is the single safest P0 fix to try next?")
    assert "---" not in block
    assert "# Performance Audit Report" not in block


def test_extract_copy_for_chatgpt_text_fallback_without_technical_section() -> None:
    block = extract_copy_for_chatgpt_text(_sample_report_md(with_technical=False))

    assert block.startswith("## COPY FOR CHATGPT")
    assert block.endswith("5. What is the single safest P0 fix to try next?")
    assert "---" not in block


def test_extract_copy_for_chatgpt_text_missing_heading_raises() -> None:
    with pytest.raises(CopyBlockNotFoundError, match="Missing '## COPY FOR CHATGPT' heading"):
        extract_copy_for_chatgpt_text("# Performance Audit Report\n")


def test_extract_copy_for_chatgpt_reads_from_path(tmp_path: Path) -> None:
    report_md = tmp_path / "report.md"
    report_md.write_text(_sample_report_md(), encoding="utf-8")

    block = extract_copy_for_chatgpt(report_md)

    assert "## COPY FOR CHATGPT" in block
    assert "# Performance Audit Report" not in block


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


def _health_bundle(
    root: Path,
    dir_name: str,
    *,
    summary: dict,
    with_report_md: bool = True,
) -> Path:
    bundle = _make_bundle(root, dir_name, summary=summary, with_report_md=with_report_md)
    (bundle / "slow_events.csv").write_text("line_no\n", encoding="utf-8")
    (bundle / "scenario_timeline.csv").write_text("scenario_id\n", encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")
    return bundle


def test_evaluate_report_health_ready(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary={
            **_sample_summary(slow=2, suspects=1),
            "total_events": 120,
            "malformed_lines": 0,
            "log_coverage_conflicts": [],
            "ux_answers": {"scenarios": _ux_scenarios(completed=7, skipped=2, total=9)},
            "scenario_log_coverage": [{"status": "ok"} for _ in range(7)]
            + [{"status": "skipped"} for _ in range(2)],
        },
    )
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)

    assert health.status == "READY"
    assert health.completed_scenarios == 7
    assert health.skipped_scenarios == 2
    output = format_report_health(health)
    assert "Status: READY" in output
    assert "READY — bundle looks good for ChatGPT analysis." in output


def test_evaluate_report_health_partial_with_log_coverage_conflicts(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-190000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 35,
            "malformed_lines": 0,
            "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)

    assert health.status == "PARTIAL"
    output = format_report_health(health)
    assert "Status: PARTIAL" in output
    assert "Completed scenarios: 1/9" in output
    assert "Skipped scenarios:   8/9" in output
    assert "PARTIAL — report can be reviewed" in output


def test_evaluate_report_health_needs_rerun_for_zero_events(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-180000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 0,
            "malformed_lines": 0,
            "log_coverage_conflicts": [],
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        },
    )
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)

    assert health.status == "NEEDS_RERUN"
    assert "NEEDS_RERUN" in health.recommendation


def test_evaluate_report_health_broken_without_summary_json(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "20260707-170000_giclee_studio"
    bundle_dir.mkdir()
    (bundle_dir / "report.md").write_text("# report\n", encoding="utf-8")

    entry = summarize_report_bundle(bundle_dir)
    health = evaluate_report_health(entry)

    assert health.status == "BROKEN"
    output = format_report_health(health)
    assert "Status: BROKEN" in output
    assert "summary.json           no" in output


def test_evaluate_report_health_broken_without_report_md(tmp_path: Path) -> None:
    bundle = _make_bundle(
        tmp_path,
        "20260707-160000_giclee_studio",
        summary=_sample_summary(),
        with_report_md=False,
    )
    entry = summarize_report_bundle(bundle)
    health = evaluate_report_health(entry)

    assert health.status == "BROKEN"
    output = format_report_health(health)
    assert "report.md              no" in output


def test_health_no_reports_does_not_crash(tmp_path: Path) -> None:
    empty_root = tmp_path / "performance"
    empty_root.mkdir()

    discovered = discover_report_dirs(empty_root, "giclee_studio")
    message = format_no_reports_message(output_root=empty_root, profile_id="giclee_studio")

    assert discovered == []
    assert "No performance report bundles found." in message
