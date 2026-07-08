"""Local read-only analysis and comparison of Performance Agent report bundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tools.performance_agent.report.index import (
    HealthStatus,
    ReportHealth,
    ReportIndexEntry,
    evaluate_report_health,
    summarize_report_bundle,
)
from tools.performance_agent.report.semantics import (
    classify_coverage_evidence,
    coverage_problem_detail,
    data_quality_regression_severity,
    metrics_improvement_blocked,
)

AnalysisStatus = Literal[
    "OK_FOR_REVIEW",
    "PARTIAL_REVIEW",
    "NEEDS_RERUN_FIRST",
    "BROKEN_BUNDLE",
]

ComparisonResult = Literal[
    "IMPROVED",
    "REGRESSED",
    "MIXED",
    "NO_MEANINGFUL_CHANGE",
    "REGRESSED_DATA_QUALITY",
    "NOT_COMPARABLE",
]

_HEALTH_RANK: dict[str, int] = {
    "READY": 0,
    "PARTIAL": 1,
    "NEEDS_RERUN": 2,
    "BROKEN": 3,
}

_ANALYSIS_STATUS_BY_HEALTH: dict[HealthStatus, AnalysisStatus] = {
    "READY": "OK_FOR_REVIEW",
    "PARTIAL": "PARTIAL_REVIEW",
    "NEEDS_RERUN": "NEEDS_RERUN_FIRST",
    "BROKEN": "BROKEN_BUNDLE",
}

_BUNDLE_FILE_NAMES = frozenset(
    {
        "summary.json",
        "report.md",
        "slow_events.csv",
        "scenario_timeline.csv",
        "questions_answers.json",
    }
)


def health_rank(status: str) -> int:
    """Return numeric severity for *status* (READY < PARTIAL < NEEDS_RERUN < BROKEN)."""
    return _HEALTH_RANK.get(status, 3)


@dataclass(frozen=True)
class ReportAnalysis:
    entry: ReportIndexEntry
    health: ReportHealth
    analysis_status: AnalysisStatus
    data_quality_notes: tuple[str, ...]
    interpretations: tuple[str, ...]
    recommended_action: str


@dataclass(frozen=True)
class ReportComparison:
    old_entry: ReportIndexEntry
    new_entry: ReportIndexEntry
    old_health: ReportHealth
    new_health: ReportHealth
    result: ComparisonResult
    metric_deltas: dict[str, tuple[int | None, int | None]]
    interpretation: str
    recommended_action: str


def resolve_report_dir(path: Path) -> Path:
    """Resolve a bundle directory from a bundle path or a file inside the bundle."""
    resolved = path.resolve()
    if not resolved.exists():
        raise ValueError(f"Report path does not exist: {path}")

    if resolved.is_dir():
        return resolved

    if resolved.name in _BUNDLE_FILE_NAMES:
        return resolved.parent

    raise ValueError(f"Report path does not exist: {path}")


def _format_optional(value: int | None, *, missing: str = "n/a") -> str:
    if value is None:
        return missing
    return str(value)


def _format_delta(old: int | None, new: int | None) -> str:
    return f"{_format_optional(old)} -> {_format_optional(new)}"


def _format_scenario_ratio(completed: int | None, total: int | None) -> str:
    if total is None:
        return "n/a"
    return f"{completed or 0}/{total}"


def _build_data_quality_notes(entry: ReportIndexEntry, health: ReportHealth) -> list[str]:
    notes: list[str] = []
    status = health.status
    completed = health.completed_scenarios
    skipped = health.skipped_scenarios
    total = health.total_scenarios
    tier = classify_coverage_evidence(entry, health)

    if status == "BROKEN":
        missing: list[str] = []
        if not entry.has_summary_json:
            missing.append("summary.json")
        if not entry.has_report_md:
            missing.append("report.md")
        if missing:
            notes.append(f"BROKEN: missing {', '.join(missing)}.")
        else:
            notes.append("BROKEN: bundle is incomplete or unreadable.")
        return notes

    if entry.total_events is not None and entry.total_events == 0:
        notes.append("NEEDS_RERUN: no parsed perf events in the log.")

    if total is not None and completed is not None:
        if completed == 0:
            notes.append(f"NEEDS_RERUN: 0/{total} scenarios completed.")
        elif status == "PARTIAL":
            if completed < total or (skipped is not None and skipped > 0):
                detail = f"{completed}/{total} scenarios completed"
                if skipped is not None and skipped > 0:
                    detail += f" ({skipped} skipped)"
                notes.append(f"PARTIAL: {detail} — coverage is weak for broad conclusions.")
            else:
                notes.append(f"PARTIAL: all {completed}/{total} scenarios completed.")
        elif skipped is not None and skipped > 0:
            notes.append(f"Scenario coverage: {completed}/{total} completed, {skipped} skipped.")

    problem_detail = coverage_problem_detail(entry.coverage_status_counts)
    if problem_detail:
        if tier == "REVIEWABLE_LIGHT":
            notes.append(
                f"Log coverage caveat: {problem_detail} — reviewable with caveat."
            )
        elif tier == "WEAK":
            notes.append(f"Scenario coverage is weak: {problem_detail}.")

    if entry.malformed_lines is not None and entry.malformed_lines > 0:
        notes.append(f"Log quality: {entry.malformed_lines} malformed JSONL line(s).")

    if entry.log_coverage_conflict_count is not None and entry.log_coverage_conflict_count > 0:
        notes.append(
            f"Log coverage conflicts: {entry.log_coverage_conflict_count} "
            "(session/log data quality, not necessarily a runtime regression)."
        )

    if entry.ux_conflict_count is not None and entry.ux_conflict_count > 0:
        notes.append(
            f"UX conflicts: {entry.ux_conflict_count} "
            "(low UX score vs OK metrics — inspect manually)."
        )

    if status == "PARTIAL" and tier == "REVIEWABLE_LIGHT" and not any(
        "caveat" in note for note in notes
    ):
        notes.append("PARTIAL: report is reviewable with caveat for the affected scenario(s).")

    if status == "PARTIAL" and tier == "WEAK" and not any("weak" in note.lower() for note in notes):
        notes.append("PARTIAL: report can be reviewed, but conclusions should stay narrow.")

    if status == "READY" and not notes:
        notes.append("Data quality looks sufficient for a full performance review.")

    if status == "PARTIAL" and tier == "WEAK" and len(notes) == 1 and "Data quality" in notes[0]:
        notes.append(
            "This bundle is useful for smoke review, not for broad performance conclusions."
        )

    return notes


def _build_interpretations(
    entry: ReportIndexEntry,
    health: ReportHealth,
    analysis_status: AnalysisStatus,
) -> list[str]:
    interpretations: list[str] = []
    slow = entry.slow_event_count or 0
    suspects = entry.suspect_count or 0
    has_signals = slow > 0 or suspects > 0
    tier = classify_coverage_evidence(entry, health)

    if analysis_status == "BROKEN_BUNDLE":
        interpretations.append("The bundle is missing key files and cannot be analyzed.")
        interpretations.append("Regenerate a report before drawing any performance conclusions.")
        return interpretations

    if analysis_status == "NEEDS_RERUN_FIRST":
        if has_signals:
            interpretations.append(
                "Some signals exist, but the bundle has insufficient session or log data."
            )
        else:
            interpretations.append("The bundle has insufficient log or scenario data for analysis.")
        interpretations.append("Repeat a full PA session before planning Studio optimization.")
        return interpretations

    if analysis_status == "PARTIAL_REVIEW":
        if tier == "REVIEWABLE_LIGHT":
            if has_signals:
                interpretations.append(
                    "The report has real slow events or UX suspects and is reviewable "
                    "with caveat — treat conclusions narrowly for the affected scenario(s)."
                )
            else:
                interpretations.append(
                    "Scenario coverage is mostly complete with a small log-window caveat — "
                    "reviewable with caveat."
                )
            interpretations.append(
                "Current data is enough for focused review and instrumentation checks."
            )
            interpretations.append(
                "Optional: rerun with a longer dashboard window if you need full cold-start proof."
            )
            return interpretations

        if has_signals:
            interpretations.append(
                "The report indicates real slow events or UX suspects, "
                "but scenario coverage is too weak for broad conclusions."
            )
        else:
            interpretations.append(
                "Scenario coverage is too weak for broad performance conclusions."
            )
        interpretations.append("Current data is enough to inspect whether instrumentation works.")
        interpretations.append("Current data is not enough to plan deeper Studio optimization.")
        return interpretations

    # OK_FOR_REVIEW
    if has_signals:
        interpretations.append(
            "The bundle has enough coverage and measurable slow/suspect signals for review."
        )
    else:
        interpretations.append("Coverage looks good; few or no slow events / suspects were detected.")
    interpretations.append("Safe next step: paste into ChatGPT or inspect slow_events.csv locally.")
    return interpretations


def _build_recommended_action(
    analysis_status: AnalysisStatus,
    *,
    tier: str | None = None,
) -> str:
    if analysis_status == "BROKEN_BUNDLE":
        return (
            "Regenerate the bundle:\n"
            "python -m tools.performance_agent --run"
        )
    if analysis_status == "NEEDS_RERUN_FIRST":
        return (
            "Run a full PA session:\n"
            "python -m tools.performance_agent --run\n"
            "\n"
            "Then check health:\n"
            "python -m tools.performance_agent --health-latest"
        )
    if analysis_status == "PARTIAL_REVIEW":
        if tier == "REVIEWABLE_LIGHT":
            return (
                "Review current data with caveat:\n"
                "python -m tools.performance_agent --prepare-chatgpt-latest\n"
                "\n"
                "Optional — stronger dashboard cold-start proof:\n"
                "python -m tools.performance_agent --run"
            )
        return (
            "Run a full PA session for stronger coverage:\n"
            "python -m tools.performance_agent --run\n"
            "\n"
            "For a narrow review of current data:\n"
            "python -m tools.performance_agent --prepare-chatgpt-latest"
        )
    return (
        "Review with ChatGPT:\n"
        "python -m tools.performance_agent --prepare-chatgpt-latest\n"
        "\n"
        "Or inspect health details:\n"
        "python -m tools.performance_agent --health-latest"
    )


def analyze_report_bundle(entry: ReportIndexEntry) -> ReportAnalysis:
    """Build a local diagnostic analysis for an on-disk report bundle."""
    health = evaluate_report_health(entry)
    analysis_status = _ANALYSIS_STATUS_BY_HEALTH[health.status]
    tier = classify_coverage_evidence(entry, health)
    data_quality_notes = tuple(_build_data_quality_notes(entry, health))
    interpretations = tuple(_build_interpretations(entry, health, analysis_status))
    recommended_action = _build_recommended_action(analysis_status, tier=tier)
    return ReportAnalysis(
        entry=entry,
        health=health,
        analysis_status=analysis_status,
        data_quality_notes=data_quality_notes,
        interpretations=interpretations,
        recommended_action=recommended_action,
    )


def format_report_analysis(analysis: ReportAnalysis) -> str:
    """Format operator output for local bundle analysis."""
    entry = analysis.entry
    health = analysis.health
    lines = [
        "Performance Agent — local analysis",
        "=" * 34,
        f"Bundle: {entry.dir_name}",
        f"Health: {health.status}",
        f"Analysis: {analysis.analysis_status}",
        f"Mode: {entry.mode or 'n/a'}",
        "",
        "Data quality:",
    ]
    if analysis.data_quality_notes:
        lines.extend(f"- {note}" for note in analysis.data_quality_notes)
    else:
        lines.append("- (no issues detected)")

    lines.extend(
        [
            "",
            "Top signals:",
            f"- Slow events: {_format_optional(entry.slow_event_count)}",
            f"- UX suspects: {_format_optional(entry.suspect_count)}",
            f"- UX conflicts: {_format_optional(entry.ux_conflict_count)}",
            f"- Log coverage conflicts: {_format_optional(entry.log_coverage_conflict_count)}",
            "",
            "Likely interpretation:",
        ]
    )
    for index, item in enumerate(analysis.interpretations, start=1):
        lines.append(f"{index}. {item}")

    lines.extend(
        [
            "",
            "Recommended next action:",
            analysis.recommended_action,
        ]
    )
    return "\n".join(lines)


def _metric_values(entry: ReportIndexEntry, health: ReportHealth) -> dict[str, int | None]:
    return {
        "total_events": entry.total_events,
        "slow_events": entry.slow_event_count,
        "suspects": entry.suspect_count,
        "completed_scenarios": health.completed_scenarios,
    }


def _is_comparable(old: ReportIndexEntry, new: ReportIndexEntry) -> bool:
    if not old.has_summary_json or not new.has_summary_json:
        return False
    old_metrics = (old.total_events, old.slow_event_count, old.suspect_count)
    new_metrics = (new.total_events, new.slow_event_count, new.suspect_count)
    if all(value is None for value in old_metrics + new_metrics):
        return False
    return True


def _compare_metric_delta(old: int | None, new: int | None) -> int | None:
    if old is None or new is None:
        return None
    return new - old


def compare_report_bundles(
    old_entry: ReportIndexEntry,
    new_entry: ReportIndexEntry,
) -> ReportComparison:
    """Compare two report bundles with simple deterministic rules."""
    old_health = evaluate_report_health(old_entry)
    new_health = evaluate_report_health(new_entry)
    old_metrics = _metric_values(old_entry, old_health)
    new_metrics = _metric_values(new_entry, new_health)
    metric_deltas = {
        key: (old_metrics[key], new_metrics[key])
        for key in old_metrics
    }

    if not _is_comparable(old_entry, new_entry):
        return ReportComparison(
            old_entry=old_entry,
            new_entry=new_entry,
            old_health=old_health,
            new_health=new_health,
            result="NOT_COMPARABLE",
            metric_deltas=metric_deltas,
            interpretation="One or both bundles lack summary data needed for comparison.",
            recommended_action=(
                "Ensure both bundles have summary.json, then compare again:\n"
                "python -m tools.performance_agent --compare-latest"
            ),
        )

    dq_severity = data_quality_regression_severity(
        old_entry, old_health, new_entry, new_health
    )

    if dq_severity == "major":
        return ReportComparison(
            old_entry=old_entry,
            new_entry=new_entry,
            old_health=old_health,
            new_health=new_health,
            result="REGRESSED_DATA_QUALITY",
            metric_deltas=metric_deltas,
            interpretation=(
                "The newer bundle is not comparable as a performance regression "
                "because data quality regressed significantly (weak scenario coverage)."
            ),
            recommended_action=(
                "Repeat a full session before comparing performance:\n"
                "python -m tools.performance_agent --run"
            ),
        )

    if dq_severity == "light":
        return ReportComparison(
            old_entry=old_entry,
            new_entry=new_entry,
            old_health=old_health,
            new_health=new_health,
            result="REGRESSED_DATA_QUALITY",
            metric_deltas=metric_deltas,
            interpretation=(
                "Comparable with data-quality caveat — scenario completion is similar, "
                "but log-window coverage is slightly weaker. Do not treat lower "
                "slow/suspect counts as proof of improvement."
            ),
            recommended_action=(
                "Review with caveat:\n"
                "python -m tools.performance_agent --analyze-latest\n"
                "\n"
                "Optional — full session for stronger dashboard proof:\n"
                "python -m tools.performance_agent --run"
            ),
        )

    comparable_health = old_health.status in ("READY", "PARTIAL") and new_health.status in (
        "READY",
        "PARTIAL",
    )
    slow_delta = _compare_metric_delta(old_metrics["slow_events"], new_metrics["slow_events"])
    suspect_delta = _compare_metric_delta(old_metrics["suspects"], new_metrics["suspects"])

    if comparable_health and slow_delta is not None and suspect_delta is not None:
        if metrics_improvement_blocked(old_entry, old_health, new_entry, new_health):
            return ReportComparison(
                old_entry=old_entry,
                new_entry=new_entry,
                old_health=old_health,
                new_health=new_health,
                result="REGRESSED_DATA_QUALITY",
                metric_deltas=metric_deltas,
                interpretation=(
                    "Lower slow/suspect counts do not indicate improvement — "
                    "the newer bundle has weaker coverage evidence."
                ),
                recommended_action=(
                    "Repeat a full session before comparing performance:\n"
                    "python -m tools.performance_agent --run"
                ),
            )
        if slow_delta < 0 and suspect_delta < 0:
            result: ComparisonResult = "IMPROVED"
            interpretation = "Slow events and UX suspects both decreased."
            recommended_action = (
                "Improvement looks plausible — keep the change and re-run PA after further edits."
            )
        elif slow_delta > 0 and suspect_delta > 0:
            result = "REGRESSED"
            interpretation = "Slow events and UX suspects both increased."
            recommended_action = (
                "Investigate recent changes, then re-run:\n"
                "python -m tools.performance_agent --run"
            )
        elif abs(slow_delta) + abs(suspect_delta) <= 2:
            result = "NO_MEANINGFUL_CHANGE"
            interpretation = "Metric changes are small — no strong performance signal."
            recommended_action = (
                "No urgent action; run another session if symptoms persist:\n"
                "python -m tools.performance_agent --run"
            )
        else:
            result = "MIXED"
            interpretation = "Signals are mixed — one metric improved while another worsened."
            recommended_action = (
                "Inspect slow_events.csv and scenario coverage before deciding:\n"
                "python -m tools.performance_agent --analyze-latest"
            )
    else:
        result = "NOT_COMPARABLE"
        interpretation = "Bundles are not in a comparable READY/PARTIAL state."
        recommended_action = (
            "Stabilize data quality on both sides, then compare again:\n"
            "python -m tools.performance_agent --run"
        )

    return ReportComparison(
        old_entry=old_entry,
        new_entry=new_entry,
        old_health=old_health,
        new_health=new_health,
        result=result,
        metric_deltas=metric_deltas,
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


def format_report_comparison(comparison: ReportComparison) -> str:
    """Format operator output for bundle comparison."""
    old_health = comparison.old_health
    new_health = comparison.new_health
    lines = [
        "Performance Agent — report comparison",
        "=" * 37,
        f"Old: {comparison.old_entry.dir_name}",
        f"New: {comparison.new_entry.dir_name}",
        "",
        "Health:",
        f"- old: {old_health.status}",
        f"- new: {new_health.status}",
        f"Result: {comparison.result}",
        "",
        "Metrics:",
        f"- total_events: {_format_delta(*comparison.metric_deltas['total_events'])}",
        f"- slow_events: {_format_delta(*comparison.metric_deltas['slow_events'])}",
        f"- suspects: {_format_delta(*comparison.metric_deltas['suspects'])}",
        (
            "- completed_scenarios: "
            f"{_format_scenario_ratio(old_health.completed_scenarios, old_health.total_scenarios)}"
            f" -> "
            f"{_format_scenario_ratio(new_health.completed_scenarios, new_health.total_scenarios)}"
        ),
        "",
        "Interpretation:",
        comparison.interpretation,
        "",
        "Recommended action:",
        comparison.recommended_action,
    ]
    return "\n".join(lines)


def analyze_report_dir(report_dir: Path) -> ReportAnalysis:
    """Resolve *report_dir*, summarize, and analyze."""
    bundle_dir = resolve_report_dir(report_dir)
    entry = summarize_report_bundle(bundle_dir)
    return analyze_report_bundle(entry)
