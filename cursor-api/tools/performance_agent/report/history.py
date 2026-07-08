"""Read-only report history, trend, and baseline analysis (PA-2C)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tools.performance_agent.report.analyzer import (
    ReportComparison,
    analyze_report_bundle,
    compare_report_bundles,
    format_report_comparison,
    health_rank,
)
from tools.performance_agent.report.index import (
    HealthStatus,
    ReportHealth,
    ReportIndexEntry,
    evaluate_report_health,
    format_no_reports_message,
)
from tools.performance_agent.report.insights import (
    _guardrails_section,
    build_hotspot_summary,
    build_timeline_summary,
    format_hotspot_summary,
    format_timeline_summary,
)

DEFAULT_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 50
MIN_BASELINE_COVERAGE_NUMERATOR = 7
MIN_BASELINE_COVERAGE_DENOMINATOR = 9

BaselineComparisonStatus = Literal[
    "compared",
    "same_bundle",
    "no_baseline",
    "no_reports",
]


@dataclass(frozen=True)
class ReportHistoryEntry:
    index: int
    entry: ReportIndexEntry
    health: ReportHealth


@dataclass(frozen=True)
class ReportHistorySummary:
    entries: tuple[ReportHistoryEntry, ...]
    window_size: int
    recommendation: str


@dataclass(frozen=True)
class TrendSummary:
    window_size: int
    entries_chronological: tuple[ReportHistoryEntry, ...]
    latest_health: HealthStatus
    best_coverage_completed: int | None
    best_coverage_total: int | None
    metric_sequences: dict[str, tuple[str, ...]]
    interpretation: str
    recommended_action: str


@dataclass(frozen=True)
class BaselineCandidate:
    entry: ReportIndexEntry
    health: ReportHealth
    reason: str


@dataclass(frozen=True)
class BaselineComparison:
    status: BaselineComparisonStatus
    baseline: BaselineCandidate | None
    latest: ReportIndexEntry | None
    comparison: ReportComparison | None
    message: str


def validate_history_limit(limit: int) -> int:
    """Validate *limit* for ``--history`` and ``--trend-latest``."""
    if limit < 1:
        raise ValueError("--history and --trend-latest limit must be >= 1")
    if limit > MAX_HISTORY_LIMIT:
        raise ValueError(f"--history and --trend-latest limit must be <= {MAX_HISTORY_LIMIT}")
    return limit


def _format_optional(value: int | None, *, missing: str = "n/a") -> str:
    if value is None:
        return missing
    return str(value)


def _format_scenario_ratio(completed: int | None, total: int | None) -> str:
    if total is None:
        return "n/a"
    return f"{completed or 0}/{total}"


def _meets_baseline_partial_threshold(health: ReportHealth) -> bool:
    completed = health.completed_scenarios or 0
    total = health.total_scenarios
    if total is None or total <= 0:
        return False
    return completed * MIN_BASELINE_COVERAGE_DENOMINATOR >= MIN_BASELINE_COVERAGE_NUMERATOR * total


def _coverage_ratio(completed: int | None, total: int | None) -> float:
    if total is None or total <= 0:
        return 0.0
    return (completed or 0) / total


def _build_history_entries(
    entries: list[ReportIndexEntry],
    *,
    limit: int,
) -> tuple[ReportHistoryEntry, ...]:
    window = entries[:limit]
    return tuple(
        ReportHistoryEntry(
            index=index,
            entry=entry,
            health=evaluate_report_health(entry),
        )
        for index, entry in enumerate(window, start=1)
    )


def _build_history_recommendation(history_entries: tuple[ReportHistoryEntry, ...]) -> str:
    if not history_entries:
        return ""
    latest = history_entries[0]
    latest_status = latest.health.status
    if latest_status in ("PARTIAL", "NEEDS_RERUN"):
        return (
            f"Latest bundle is {latest_status}. For performance comparison, prefer comparing "
            "against the latest READY/PARTIAL bundle with similar coverage."
        )
    if latest_status == "BROKEN":
        return (
            "Latest bundle is BROKEN. Regenerate a report before comparing performance:\n"
            "python -m tools.performance_agent --run"
        )
    return (
        "Latest bundle is READY. Performance comparisons are meaningful when baseline coverage "
        "is similar — use --baseline-candidate and --compare-baseline-latest."
    )


def build_report_history(
    entries: list[ReportIndexEntry],
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> ReportHistorySummary:
    """Build a history summary from *entries* (newest first)."""
    history_entries = _build_history_entries(entries, limit=limit)
    return ReportHistorySummary(
        entries=history_entries,
        window_size=limit,
        recommendation=_build_history_recommendation(history_entries),
    )


def format_report_history(
    summary: ReportHistorySummary,
    *,
    output_root: Path | None = None,
    profile_id: str = "giclee_studio",
) -> str:
    """Format operator output for ``--history``."""
    if not summary.entries:
        if output_root is not None:
            return format_no_reports_message(output_root=output_root, profile_id=profile_id)
        return (
            "No performance report bundles found.\n"
            "Tip: run --parse-only, --manual, or --run to generate a bundle."
        )

    lines = [
        "Performance Agent — report history",
        "=" * 34,
        f"Showing latest {len(summary.entries)} bundles",
        "",
        "| # | bundle | health | mode | events | slow | suspects | completed | skipped |",
        "|---|--------|--------|------|--------|------|----------|-----------|---------|",
    ]
    for item in summary.entries:
        health = item.health
        entry = item.entry
        lines.append(
            f"| {item.index} | {entry.dir_name} | {health.status} | {entry.mode or 'n/a'} | "
            f"{_format_optional(entry.total_events)} | {_format_optional(entry.slow_event_count)} | "
            f"{_format_optional(entry.suspect_count)} | "
            f"{_format_scenario_ratio(health.completed_scenarios, health.total_scenarios)} | "
            f"{_format_scenario_ratio(health.skipped_scenarios, health.total_scenarios)} |"
        )

    lines.extend(["", "Recommendation:", summary.recommendation])
    return "\n".join(lines)


def _format_metric_sequence(values: list[str]) -> str:
    if not values:
        return "n/a"
    return " -> ".join(values)


def build_trend_summary(
    entries: list[ReportIndexEntry],
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
) -> TrendSummary:
    """Build a trend summary from *entries* (newest first)."""
    history_entries = _build_history_entries(entries, limit=limit)
    chronological = tuple(reversed(history_entries))

    total_events: list[str] = []
    slow_events: list[str] = []
    suspects: list[str] = []
    completed: list[str] = []
    best_ratio = -1.0
    best_completed: int | None = None
    best_total: int | None = None

    for item in chronological:
        entry = item.entry
        health = item.health
        total_events.append(_format_optional(entry.total_events))
        slow_events.append(_format_optional(entry.slow_event_count))
        suspects.append(_format_optional(entry.suspect_count))
        completed.append(_format_scenario_ratio(health.completed_scenarios, health.total_scenarios))
        ratio = _coverage_ratio(health.completed_scenarios, health.total_scenarios)
        if ratio > best_ratio:
            best_ratio = ratio
            best_completed = health.completed_scenarios
            best_total = health.total_scenarios

    latest = history_entries[0] if history_entries else None
    latest_health: HealthStatus = latest.health.status if latest is not None else "BROKEN"
    latest_completed = latest.health.completed_scenarios if latest is not None else None
    latest_total = latest.health.total_scenarios if latest is not None else None
    latest_ratio = _coverage_ratio(latest_completed, latest_total)
    best_ratio_value = _coverage_ratio(best_completed, best_total)

    weaker_latest_coverage = (
        latest is not None
        and best_ratio_value > 0
        and latest_ratio + 1e-9 < best_ratio_value
    )
    weaker_latest_health = (
        latest is not None
        and len(chronological) > 1
        and any(
            health_rank(latest.health.status)
            > health_rank(item.health.status)
            for item in chronological[:-1]
        )
    )

    if weaker_latest_coverage or weaker_latest_health:
        interpretation = (
            "Latest bundle has weaker data quality than previous runs. "
            "Do not treat lower slow/suspect counts as improvement."
        )
        recommended_action = (
            "Run a full PA session before comparing performance:\n"
            "python -m tools.performance_agent --run"
        )
    elif len(chronological) <= 1:
        interpretation = "Only one bundle in the trend window — insufficient history for comparison."
        recommended_action = (
            "Generate more report bundles, then re-check trend:\n"
            "python -m tools.performance_agent --run"
        )
    else:
        interpretation = (
            "Health and coverage look similar across recent bundles. "
            "Metric trends may indicate performance changes — verify with --compare-baseline-latest."
        )
        recommended_action = (
            "Use baseline comparison for a focused delta:\n"
            "python -m tools.performance_agent --compare-baseline-latest"
        )

    return TrendSummary(
        window_size=limit,
        entries_chronological=chronological,
        latest_health=latest_health,
        best_coverage_completed=best_completed,
        best_coverage_total=best_total,
        metric_sequences={
            "total_events": tuple(total_events),
            "slow_events": tuple(slow_events),
            "suspects": tuple(suspects),
            "completed": tuple(completed),
        },
        interpretation=interpretation,
        recommended_action=recommended_action,
    )


def format_trend_summary(trend: TrendSummary) -> str:
    """Format operator output for ``--trend-latest``."""
    if not trend.entries_chronological:
        return (
            "No performance report bundles found.\n"
            "Tip: run --parse-only, --manual, or --run to generate a bundle."
        )

    count = len(trend.entries_chronological)
    lines = [
        "Performance Agent — trend",
        "=" * 25,
        f"Window: latest {count} bundles",
        "",
        "Data quality trend:",
        f"- latest health: {trend.latest_health}",
    ]
    if trend.best_coverage_total is not None:
        lines.append(
            f"- best recent coverage: "
            f"{_format_scenario_ratio(trend.best_coverage_completed, trend.best_coverage_total)}"
        )
    if trend.entries_chronological:
        latest_item = trend.entries_chronological[-1]
        lines.append(
            f"- latest completed: "
            f"{_format_scenario_ratio(latest_item.health.completed_scenarios, latest_item.health.total_scenarios)}"
        )

    lines.extend(
        [
            "",
            "Metrics trend:",
            f"- total_events: {_format_metric_sequence(list(trend.metric_sequences['total_events']))}",
            f"- slow_events: {_format_metric_sequence(list(trend.metric_sequences['slow_events']))}",
            f"- suspects: {_format_metric_sequence(list(trend.metric_sequences['suspects']))}",
            f"- completed: {_format_metric_sequence(list(trend.metric_sequences['completed']))}",
            "",
            "Interpretation:",
            trend.interpretation,
            "",
            "Recommended action:",
            trend.recommended_action,
        ]
    )
    return "\n".join(lines)


def select_baseline_candidate(entries: list[ReportIndexEntry]) -> BaselineCandidate | None:
    """Select the best baseline bundle from *entries* (newest first)."""
    for entry in entries:
        health = evaluate_report_health(entry)
        if health.status == "READY":
            return BaselineCandidate(
                entry=entry,
                health=health,
                reason="Latest READY bundle with full scenario coverage.",
            )

    for entry in entries:
        health = evaluate_report_health(entry)
        if health.status == "PARTIAL" and _meets_baseline_partial_threshold(health):
            completed = health.completed_scenarios or 0
            total = health.total_scenarios or 0
            return BaselineCandidate(
                entry=entry,
                health=health,
                reason=(
                    f"Latest PARTIAL bundle with sufficient coverage "
                    f"({completed}/{total} scenarios completed)."
                ),
            )

    return None


def format_baseline_candidate(
    candidate: BaselineCandidate | None,
    *,
    latest: ReportIndexEntry | None = None,
) -> str:
    """Format operator output for ``--baseline-candidate``."""
    if candidate is None:
        return "\n".join(
            [
                "Performance Agent — baseline candidate",
                "=" * 38,
                "No suitable baseline bundle found.",
                "",
                "A baseline requires READY health, or PARTIAL with at least 7/9 scenario coverage.",
                "NEEDS_RERUN and BROKEN bundles are never used as baseline.",
                "",
                "Recommendation:",
                "python -m tools.performance_agent --run",
            ]
        )

    health = candidate.health
    lines = [
        "Performance Agent — baseline candidate",
        "=" * 38,
        f"Selected: {candidate.entry.dir_name}",
        f"Health: {health.status}",
        f"Completed: {_format_scenario_ratio(health.completed_scenarios, health.total_scenarios)}",
        "Reason:",
        candidate.reason,
        "",
        "Use:",
    ]
    if latest is not None and latest.report_dir != candidate.entry.report_dir:
        lines.append(
            "python -m tools.performance_agent --compare-reports "
            f"{candidate.entry.report_dir} {latest.report_dir}"
        )
    else:
        lines.append(
            "python -m tools.performance_agent --compare-baseline-latest"
        )
    return "\n".join(lines)


def compare_baseline_to_latest(entries: list[ReportIndexEntry]) -> BaselineComparison:
    """Compare the best baseline against the newest bundle."""
    if not entries:
        return BaselineComparison(
            status="no_reports",
            baseline=None,
            latest=None,
            comparison=None,
            message="No performance report bundles found.",
        )

    latest = entries[0]
    baseline = select_baseline_candidate(entries)
    if baseline is None:
        return BaselineComparison(
            status="no_baseline",
            baseline=None,
            latest=latest,
            comparison=None,
            message=(
                "No suitable baseline bundle found. Run a full PA session first:\n"
                "python -m tools.performance_agent --run"
            ),
        )

    if baseline.entry.report_dir == latest.report_dir:
        return BaselineComparison(
            status="same_bundle",
            baseline=baseline,
            latest=latest,
            comparison=None,
            message=(
                "Latest bundle is the same as the baseline candidate — "
                "no newer bundle to compare."
            ),
        )

    comparison = compare_report_bundles(baseline.entry, latest)
    return BaselineComparison(
        status="compared",
        baseline=baseline,
        latest=latest,
        comparison=comparison,
        message="",
    )


def format_baseline_comparison(result: BaselineComparison) -> str:
    """Format operator output for ``--compare-baseline-latest``."""
    if result.status == "no_reports":
        return (
            "Performance Agent — baseline vs latest\n"
            "=" * 36 + "\n"
            f"{result.message}\n"
            "Tip: run --parse-only, --manual, or --run to generate a bundle."
        )

    if result.status == "no_baseline":
        return "\n".join(
            [
                "Performance Agent — baseline vs latest",
                "=" * 36,
                result.message,
            ]
        )

    assert result.baseline is not None
    assert result.latest is not None

    if result.status == "same_bundle":
        return "\n".join(
            [
                "Performance Agent — baseline vs latest",
                "=" * 36,
                f"Baseline: {result.baseline.entry.dir_name}",
                f"Latest:   {result.latest.dir_name}",
                "",
                result.message,
            ]
        )

    assert result.comparison is not None
    comparison_text = format_report_comparison(result.comparison)
    return "\n".join(
        [
            "Performance Agent — baseline vs latest",
            "=" * 36,
            f"Baseline: {result.baseline.entry.dir_name}",
            f"Latest:   {result.latest.dir_name}",
            "",
            comparison_text,
        ]
    )


def build_analysis_prompt_with_history(
    entries: list[ReportIndexEntry],
    *,
    limit: int = DEFAULT_HISTORY_LIMIT,
    workspace_root: Path | None = None,
) -> str:
    """Build a wide Cursor analysis prompt with history, trend, and baseline context."""
    if not entries:
        return (
            "No performance report bundles found.\n"
            "Run: python -m tools.performance_agent --run"
        )

    latest_entry = entries[0]
    latest_health = evaluate_report_health(latest_entry)
    analysis = analyze_report_bundle(latest_entry)
    hotspots = build_hotspot_summary(latest_entry)
    timeline = build_timeline_summary(latest_entry)
    history = build_report_history(entries, limit=limit)
    trend = build_trend_summary(entries, limit=limit)
    baseline = select_baseline_candidate(entries)
    baseline_compare = compare_baseline_to_latest(entries)

    if workspace_root is None:
        parent = latest_entry.report_dir.parent
        if parent.name == "performance" and parent.parent.name == "reports":
            workspace_root = parent.parent.parent.resolve()
        else:
            workspace_root = parent.parent.resolve()

    lines = [
        "# Cursor Prompt — Performance Agent Analysis (with history)",
        "",
        f"Workspace:\n{workspace_root}",
        "",
        f"Latest report bundle:\n{latest_entry.report_dir.resolve()}",
        "",
        f"Latest health: {latest_health.status}",
        "",
        "Important — data quality first:",
        "Lower slow_events or suspects in a bundle with weaker scenario coverage "
        "does NOT mean performance improved. Stabilize coverage before drawing conclusions.",
        "",
        "## Latest analysis",
        f"Analysis status: {analysis.analysis_status}",
        "",
        "Data quality notes:",
        *[f"- {note}" for note in analysis.data_quality_notes],
        "",
        "Interpretations:",
        *[f"- {item}" for item in analysis.interpretations],
        "",
        "Recommended action:",
        analysis.recommended_action,
        "",
        "## Hotspots (latest)",
        format_hotspot_summary(hotspots),
        "",
        "## Timeline (latest)",
        format_timeline_summary(timeline),
        "",
        "## Report history",
        format_report_history(history),
        "",
        "## Trend",
        format_trend_summary(trend),
        "",
        "## Baseline candidate",
        format_baseline_candidate(baseline, latest=latest_entry),
        "",
    ]

    if baseline_compare.status == "compared" and baseline_compare.comparison is not None:
        lines.extend(
            [
                "## Baseline comparison (baseline vs latest)",
                format_report_comparison(baseline_compare.comparison),
                "",
            ]
        )
    elif baseline_compare.status == "same_bundle":
        lines.extend(
            [
                "## Baseline comparison",
                "Latest bundle is the baseline candidate — no newer bundle to compare.",
                "",
            ]
        )
    elif baseline_compare.status == "no_baseline":
        lines.extend(
            [
                "## Baseline comparison",
                "No suitable baseline — run a full PA session before comparing performance.",
                "",
            ]
        )

    lines.extend(
        [
            "Task:",
            "Review the Performance Agent data above. Prioritize data quality issues before "
            "proposing performance optimizations.",
            "",
            "Expected output:",
            "- data quality assessment and whether a PA rerun is needed",
            "- performance findings only when coverage is sufficient",
            "- proposed fixes only (no implementation without approval)",
            "",
            *_guardrails_section(),
        ]
    )
    return "\n".join(lines)
