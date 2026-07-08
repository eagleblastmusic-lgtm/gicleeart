from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.__main__ import (
    _build_parser,
    main,
    run_baseline_candidate,
    run_compare_baseline_latest,
    run_copy_analysis_prompt_latest,
    run_history,
    run_trend_latest,
)
from tools.performance_agent.report.analyzer import compare_report_bundles
from tools.performance_agent.report.history import (
    build_analysis_prompt_with_history,
    build_report_history,
    build_trend_summary,
    compare_baseline_to_latest,
    format_report_history,
    format_trend_summary,
    select_baseline_candidate,
    validate_history_limit,
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


def _ready_summary(*, slow: int = 3, suspects: int = 2, total_events: int = 1842) -> dict:
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


def _partial_summary(
    *,
    completed: int = 1,
    skipped: int = 8,
    slow: int = 7,
    suspects: int = 7,
    total_events: int = 35,
) -> dict:
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
        "ux_answers": {
            "scenarios": _ux_scenarios(completed=completed, skipped=skipped, total=9),
        },
        "scenario_log_coverage": [
            {"scenario_id": "dashboard_cold", "status": "no_events_in_window"},
            *[{"status": "skipped"} for _ in range(skipped)],
        ],
    }


def _history_bundle(root: Path, dir_name: str, summary: dict) -> Path:
    bundle = _make_bundle(root, dir_name, summary=summary)
    (bundle / "slow_events.csv").write_text("line_no,event,ms\n", encoding="utf-8")
    (bundle / "scenario_timeline.csv").write_text("scenario_id,completed\n", encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")
    return bundle


def _entries_from_root(root: Path) -> list:
    bundles = sorted(
        [path for path in root.iterdir() if path.is_dir()],
        key=lambda path: path.name,
        reverse=True,
    )
    return [summarize_report_bundle(path) for path in bundles]


def _mock_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    profile = MagicMock()
    profile.resolve_output_root.return_value = tmp_path
    monkeypatch.setattr("tools.performance_agent.__main__.get_profile", lambda _profile_id: profile)


def test_validate_history_limit_rejects_invalid() -> None:
    with pytest.raises(ValueError, match=">= 1"):
        validate_history_limit(0)
    with pytest.raises(ValueError, match="<= 50"):
        validate_history_limit(51)


def test_history_sorts_latest_first_and_formats_table(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(
        tmp_path,
        "20260707-162819_giclee_studio",
        _partial_summary(completed=8, skipped=1, slow=294, suspects=86, total_events=2081),
    )
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    output = format_report_history(build_report_history(entries, limit=10))

    assert "| 1 | 20260707-165000_giclee_studio | PARTIAL |" in output
    assert "| 2 | 20260707-162819_giclee_studio |" in output
    assert "| 3 | 20260707-160215_giclee_studio | READY |" in output
    assert "1/9" in output
    assert "9/9" in output
    assert "Recommendation:" in output


def test_history_empty_entries_uses_no_reports_message(tmp_path: Path) -> None:
    output = format_report_history(
        build_report_history([], limit=10),
        output_root=tmp_path,
        profile_id="giclee_studio",
    )

    assert "No performance report bundles found." in output
    assert str(tmp_path.resolve()) in output


def test_trend_shows_metric_sequences(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary(total_events=1842))
    _history_bundle(
        tmp_path,
        "20260707-162819_giclee_studio",
        _partial_summary(completed=8, skipped=1, slow=294, suspects=86, total_events=2081),
    )
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    output = format_trend_summary(build_trend_summary(entries, limit=10))

    assert "1842 -> 2081 -> 35" in output
    assert "3 -> 294 -> 7" in output
    assert "9/9 -> 8/9 -> 1/9" in output


def test_trend_detects_weaker_latest_coverage(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    output = format_trend_summary(build_trend_summary(entries, limit=10))

    assert "Do not treat lower slow/suspect counts as improvement" in output
    assert "python -m tools.performance_agent --run" in output


def test_baseline_prefers_newest_ready(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(
        tmp_path,
        "20260707-162819_giclee_studio",
        _partial_summary(completed=8, skipped=1, slow=294, suspects=86, total_events=2081),
    )
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    candidate = select_baseline_candidate(entries)

    assert candidate is not None
    assert candidate.entry.dir_name == "20260707-160215_giclee_studio"
    assert candidate.health.status == "READY"


def test_baseline_partial_with_good_coverage_when_no_ready(tmp_path: Path) -> None:
    _history_bundle(
        tmp_path,
        "20260707-162819_giclee_studio",
        _partial_summary(completed=8, skipped=1, slow=294, suspects=86, total_events=2081),
    )
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    candidate = select_baseline_candidate(entries)

    assert candidate is not None
    assert candidate.entry.dir_name == "20260707-162819_giclee_studio"
    assert candidate.health.status == "PARTIAL"


def test_baseline_rejects_weak_partial_only(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    assert select_baseline_candidate(entries) is None


def test_compare_baseline_latest_regressed_data_quality(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    result = compare_baseline_to_latest(entries)

    assert result.status == "compared"
    assert result.comparison is not None
    assert result.comparison.result == "REGRESSED_DATA_QUALITY"


def test_compare_baseline_latest_same_as_direct_compare(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    wrapped = compare_baseline_to_latest(entries)
    direct = compare_report_bundles(entries[1], entries[0])

    assert wrapped.comparison is not None
    assert wrapped.comparison.result == direct.result


def test_analysis_prompt_includes_history_trend_baseline_and_guardrails(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    prompt = build_analysis_prompt_with_history(entries, limit=10, workspace_root=tmp_path)

    assert "data quality first" in prompt.lower()
    assert "## Latest analysis" in prompt
    assert "## Report history" in prompt
    assert "## Trend" in prompt
    assert "## Baseline candidate" in prompt
    assert "## Baseline comparison" in prompt
    assert "REGRESSED_DATA_QUALITY" in prompt
    assert "Do not modify GicleeApp Studio code." in prompt
    assert "Do not change GICLÉE FRAME runtime." in prompt
    assert "Do not edit Komponenty/*." in prompt
    assert "Do not commit or push." in prompt


def test_analysis_prompt_no_baseline_message(tmp_path: Path) -> None:
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    entries = _entries_from_root(tmp_path)

    prompt = build_analysis_prompt_with_history(entries, limit=10, workspace_root=tmp_path)

    assert "No suitable baseline bundle found." in prompt
    assert "No suitable baseline — run a full PA session" in prompt


def test_parser_help_lists_pa2c_flags() -> None:
    help_text = _build_parser().format_help()

    assert "--history" in help_text
    assert "--trend-latest" in help_text
    assert "--baseline-candidate" in help_text
    assert "--compare-baseline-latest" in help_text
    assert "--copy-analysis-prompt-latest" in help_text


def test_cli_history_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())

    assert run_history(profile_id="giclee_studio", limit=10) == 0


def test_cli_history_invalid_limit_exit_1(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)

    exit_code = main(["--history", "0"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert ">= 1" in captured.err


def test_cli_trend_latest_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())

    assert run_trend_latest(profile_id="giclee_studio", limit=10) == 0


def test_cli_baseline_candidate_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())

    assert run_baseline_candidate(profile_id="giclee_studio") == 0


def test_cli_compare_baseline_latest_no_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _history_bundle(tmp_path, "20260707-160215_giclee_studio", _ready_summary())
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())

    assert run_compare_baseline_latest(profile_id="giclee_studio") == 0


def test_copy_analysis_prompt_latest_uses_clipboard_helper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _mock_profile(monkeypatch, tmp_path)
    _history_bundle(tmp_path, "20260707-165000_giclee_studio", _partial_summary())
    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    assert run_copy_analysis_prompt_latest(profile_id="giclee_studio") == 0
    captured = capsys.readouterr()
    assert copied
    assert "Performance analysis prompt copied to clipboard." in captured.out
    assert "data quality first" in copied[0].lower()


def test_main_history_no_reports_exit_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)

    assert main(["--history"]) == 0


def test_main_trend_latest_no_reports_exit_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _mock_profile(monkeypatch, tmp_path)

    assert main(["--trend-latest"]) == 0
