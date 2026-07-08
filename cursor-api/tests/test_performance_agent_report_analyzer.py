from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.__main__ import (
    _build_parser,
    run_analyze_latest,
    run_compare_latest,
)
from tools.performance_agent.report.analyzer import (
    analyze_report_bundle,
    compare_report_bundles,
    format_report_analysis,
    format_report_comparison,
    resolve_report_dir,
)
from tools.performance_agent.report.index import summarize_report_bundle


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
        "ux_conflicts": [],
        "log_coverage_conflicts": [],
        "scenario_log_coverage": [{"scenario_id": "hub_theme", "status": "ok"}],
    }


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


def _partial_9_9_one_no_events_summary(
    *,
    slow: int = 315,
    suspects: int = 92,
    total_events: int = 1894,
) -> dict:
    coverage = [{"status": "ok"} for _ in range(8)]
    coverage.insert(0, {"scenario_id": "dashboard_cold", "status": "no_events_in_window"})
    return {
        **_sample_summary(slow=slow, suspects=suspects),
        "total_events": total_events,
        "malformed_lines": 0,
        "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
        "ux_conflicts": [{"id": "UX_CONFLICT"}],
        "ux_answers": {"scenarios": _ux_scenarios(completed=9, skipped=0, total=9)},
        "scenario_log_coverage": coverage,
    }


def _ready_summary(*, slow: int = 3, suspects: int = 2, total_events: int = 120) -> dict:
    return {
        **_sample_summary(slow=slow, suspects=suspects),
        "total_events": total_events,
        "malformed_lines": 0,
        "log_coverage_conflicts": [],
        "ux_answers": {"scenarios": _ux_scenarios(completed=9, skipped=0, total=9)},
        "scenario_log_coverage": [{"status": "ok"} for _ in range(9)],
    }


def _mock_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = MagicMock()
    profile.resolve_output_root.return_value = tmp_path
    monkeypatch.setattr("tools.performance_agent.__main__.get_profile", lambda _profile_id: profile)


def test_resolve_report_dir_bundle_directory(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "20260707-120000_giclee_studio", summary=_sample_summary())

    resolved = resolve_report_dir(bundle)

    assert resolved == bundle.resolve()


def test_resolve_report_dir_summary_json_parent(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "20260707-120000_giclee_studio", summary=_sample_summary())
    summary_path = bundle / "summary.json"

    resolved = resolve_report_dir(summary_path)

    assert resolved == bundle.resolve()


def test_resolve_report_dir_report_md_parent(tmp_path: Path) -> None:
    bundle = _make_bundle(tmp_path, "20260707-120000_giclee_studio", summary=_sample_summary())
    report_path = bundle / "report.md"

    resolved = resolve_report_dir(report_path)

    assert resolved == bundle.resolve()


def test_resolve_report_dir_missing_path_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing_bundle"

    with pytest.raises(ValueError, match="Report path does not exist"):
        resolve_report_dir(missing)


def test_analyze_report_bundle_ready_maps_to_ok_for_review(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_ready_summary(slow=3, suspects=2),
    )
    entry = summarize_report_bundle(bundle)

    analysis = analyze_report_bundle(entry)

    assert analysis.health.status == "READY"
    assert analysis.analysis_status == "OK_FOR_REVIEW"


def test_analyze_report_bundle_partial_maps_to_partial_review(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-190000_giclee_studio",
        summary={
            **_sample_summary(slow=7, suspects=7),
            "total_events": 35,
            "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    entry = summarize_report_bundle(bundle)

    analysis = analyze_report_bundle(entry)

    assert analysis.health.status == "PARTIAL"
    assert analysis.analysis_status == "PARTIAL_REVIEW"


def test_analyze_report_bundle_needs_rerun_maps_to_needs_rerun_first(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-180000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 0,
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        },
    )
    entry = summarize_report_bundle(bundle)

    analysis = analyze_report_bundle(entry)

    assert analysis.health.status == "NEEDS_RERUN"
    assert analysis.analysis_status == "NEEDS_RERUN_FIRST"


def test_analyze_report_bundle_broken_maps_to_broken_bundle(tmp_path: Path) -> None:
    bundle_dir = tmp_path / "20260707-170000_giclee_studio"
    bundle_dir.mkdir()
    (bundle_dir / "report.md").write_text("# report\n", encoding="utf-8")
    entry = summarize_report_bundle(bundle_dir)

    analysis = analyze_report_bundle(entry)

    assert analysis.health.status == "BROKEN"
    assert analysis.analysis_status == "BROKEN_BUNDLE"


def test_format_report_analysis_contains_key_sections(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_ready_summary(),
    )
    analysis = analyze_report_bundle(summarize_report_bundle(bundle))

    output = format_report_analysis(analysis)

    assert "Health: READY" in output
    assert "Data quality:" in output
    assert "Recommended next action:" in output
    assert "Top signals:" in output


def test_analyze_report_bundle_partial_9_9_one_no_events_reviewable_caveat(
    tmp_path: Path,
) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-212000_giclee_studio",
        summary=_partial_9_9_one_no_events_summary(),
    )
    analysis = analyze_report_bundle(summarize_report_bundle(bundle))
    output = format_report_analysis(analysis)

    assert analysis.health.status == "PARTIAL"
    assert analysis.analysis_status == "PARTIAL_REVIEW"
    assert "only 9/9" not in output.lower()
    assert "reviewable with caveat" in output.lower()
    assert "all 9/9 scenarios completed" in output


def test_analyze_report_bundle_partial_1_9_strong_warning(tmp_path: Path) -> None:
    bundle = _health_bundle(
        tmp_path,
        "20260707-190000_giclee_studio",
        summary={
            **_sample_summary(slow=7, suspects=7),
            "total_events": 35,
            "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    analysis = analyze_report_bundle(summarize_report_bundle(bundle))
    output = format_report_analysis(analysis)

    assert "too weak for broad conclusions" in output.lower()
    assert "reviewable with caveat" not in output.lower()


def test_compare_ready_vs_partial_9_9_one_no_events_light_caveat(tmp_path: Path) -> None:
    old_bundle = _health_bundle(
        tmp_path,
        "20260707-160215_giclee_studio",
        summary=_ready_summary(slow=28, suspects=15, total_events=250),
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-212000_giclee_studio",
        summary=_partial_9_9_one_no_events_summary(),
    )
    comparison = compare_report_bundles(
        summarize_report_bundle(old_bundle),
        summarize_report_bundle(new_bundle),
    )

    assert comparison.result == "REGRESSED_DATA_QUALITY"
    assert "caveat" in comparison.interpretation.lower()
    assert "not comparable" not in comparison.interpretation.lower()


def test_compare_lower_metrics_weaker_coverage_not_improvement(tmp_path: Path) -> None:
    old_bundle = _health_bundle(
        tmp_path,
        "20260707-160215_giclee_studio",
        summary=_ready_summary(slow=10, suspects=8),
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-165000_giclee_studio",
        summary={
            **_sample_summary(slow=3, suspects=2),
            "total_events": 35,
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    comparison = compare_report_bundles(
        summarize_report_bundle(old_bundle),
        summarize_report_bundle(new_bundle),
    )

    assert comparison.result == "REGRESSED_DATA_QUALITY"
    assert comparison.result != "IMPROVED"


def test_compare_report_bundles_regressed_data_quality_major_wording(tmp_path: Path) -> None:
    old_bundle = _health_bundle(
        tmp_path,
        "20260707-160215_giclee_studio",
        summary=_ready_summary(slow=3, suspects=2, total_events=250),
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-165000_giclee_studio",
        summary={
            **_sample_summary(slow=7, suspects=7),
            "total_events": 35,
            "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    old_entry = summarize_report_bundle(old_bundle)
    new_entry = summarize_report_bundle(new_bundle)

    comparison = compare_report_bundles(old_entry, new_entry)

    assert comparison.result == "REGRESSED_DATA_QUALITY"
    assert "significantly" in comparison.interpretation.lower() or "not comparable" in comparison.interpretation.lower()
    output = format_report_comparison(comparison)
    assert "Old: 20260707-160215_giclee_studio" in output
    assert "New: 20260707-165000_giclee_studio" in output


def test_compare_report_bundles_improved(tmp_path: Path) -> None:
    old_bundle = _health_bundle(
        tmp_path,
        "20260707-100000_giclee_studio",
        summary=_ready_summary(slow=10, suspects=8),
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-110000_giclee_studio",
        summary=_ready_summary(slow=4, suspects=2),
    )

    comparison = compare_report_bundles(
        summarize_report_bundle(old_bundle),
        summarize_report_bundle(new_bundle),
    )

    assert comparison.result == "IMPROVED"


def test_compare_report_bundles_regressed(tmp_path: Path) -> None:
    old_bundle = _health_bundle(
        tmp_path,
        "20260707-100000_giclee_studio",
        summary=_ready_summary(slow=2, suspects=1),
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-110000_giclee_studio",
        summary=_ready_summary(slow=8, suspects=6),
    )

    comparison = compare_report_bundles(
        summarize_report_bundle(old_bundle),
        summarize_report_bundle(new_bundle),
    )

    assert comparison.result == "REGRESSED"


def test_compare_report_bundles_not_comparable_without_summary(tmp_path: Path) -> None:
    old_bundle = _make_bundle(
        tmp_path,
        "20260707-100000_giclee_studio",
        summary=None,
        with_report_md=True,
    )
    new_bundle = _health_bundle(
        tmp_path,
        "20260707-110000_giclee_studio",
        summary=_ready_summary(),
    )

    comparison = compare_report_bundles(
        summarize_report_bundle(old_bundle),
        summarize_report_bundle(new_bundle),
    )

    assert comparison.result == "NOT_COMPARABLE"


def test_parser_help_lists_pa2a_flags() -> None:
    help_text = _build_parser().format_help()

    assert "--analyze-latest" in help_text
    assert "--analyze-report" in help_text
    assert "--compare-latest" in help_text
    assert "--compare-reports" in help_text


def test_run_analyze_latest_with_one_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_ready_summary(),
    )

    exit_code = run_analyze_latest(profile_id="giclee_studio")
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Performance Agent — local analysis" in captured.out


def test_run_compare_latest_with_fewer_than_two_bundles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_ready_summary(),
    )

    exit_code = run_compare_latest(profile_id="giclee_studio")
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Need at least 2 report bundles to compare." in captured.out
