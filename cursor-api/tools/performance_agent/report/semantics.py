"""Shared data-quality semantics helpers for Performance Agent (PA-3B)."""

from __future__ import annotations

from typing import Literal

from tools.performance_agent.report.index import HealthStatus, ReportHealth, ReportIndexEntry

CoverageEvidenceTier = Literal["STRONG", "REVIEWABLE_LIGHT", "WEAK", "INSUFFICIENT"]

DataQualityRegressionSeverity = Literal["major", "light", "none"]

# Scenario coverage thresholds (9-scenario profile).
MIN_MEANINGFUL_COVERAGE_NUMERATOR = 7
MIN_MEANINGFUL_COVERAGE_DENOMINATOR = 9
REVIEWABLE_LIGHT_MIN_COMPLETED = 8

# Coverage statuses that indicate a log-window problem (not early_event_seen).
COVERAGE_PROBLEM_STATUSES = frozenset(
    {"missing_expected_events", "no_events_in_window", "skipped", "not_completed"}
)

# Timing fields that represent real latency/duration for slow-event ranking.
SLOW_EVENT_DURATION_FIELDS = frozenset(
    {
        "elapsed_ms",
        "since_click_ms",
        "since_request_ms",
        "since_details_cta_ms",
        "queue_latency_ms",
    }
)

NON_DURATION_MS_FIELDS = frozenset({"since_enter_ms"})


def is_duration_ms_field(field_name: str | None) -> bool:
    """Return True if *field_name* represents a real latency/duration measurement."""
    if not field_name:
        return False
    return field_name in SLOW_EVENT_DURATION_FIELDS


def coverage_problem_count(counts: dict[str, int] | None) -> int:
    """Count scenarios with log-window coverage problems."""
    if not counts:
        return 0
    return sum(
        counts.get(name, 0)
        for name in COVERAGE_PROBLEM_STATUSES
        if name not in {"skipped", "not_completed"}
    )


def coverage_problem_detail(counts: dict[str, int] | None) -> str:
    """Format coverage problem counts for operator notes."""
    if not counts:
        return ""
    parts: list[str] = []
    for name in ("no_events_in_window", "missing_expected_events", "skipped", "not_completed"):
        count = counts.get(name, 0)
        if count > 0:
            parts.append(f"{name}={count}")
    return ", ".join(parts)


def classify_coverage_evidence(
    entry: ReportIndexEntry,
    health: ReportHealth,
) -> CoverageEvidenceTier:
    """Classify how much performance evidence a bundle provides."""
    status = health.status
    completed = health.completed_scenarios or 0
    skipped = health.skipped_scenarios or 0
    total = health.total_scenarios

    if status in ("BROKEN", "NEEDS_RERUN"):
        return "INSUFFICIENT"
    if entry.total_events is not None and entry.total_events == 0:
        return "INSUFFICIENT"
    if total is not None and completed == 0:
        return "INSUFFICIENT"

    problems = coverage_problem_count(entry.coverage_status_counts)

    if total is not None and completed < MIN_MEANINGFUL_COVERAGE_NUMERATOR:
        return "WEAK"
    if skipped >= completed and skipped > 0:
        return "WEAK"
    if problems >= 2:
        return "WEAK"

    if status == "READY" and problems == 0:
        if total is not None and completed >= total:
            return "STRONG"
        if total is not None and completed >= REVIEWABLE_LIGHT_MIN_COMPLETED:
            return "REVIEWABLE_LIGHT"

    if problems == 1 and completed >= REVIEWABLE_LIGHT_MIN_COMPLETED:
        return "REVIEWABLE_LIGHT"

    if status == "PARTIAL" and problems <= 1 and completed >= REVIEWABLE_LIGHT_MIN_COMPLETED:
        return "REVIEWABLE_LIGHT"

    if status == "READY":
        return "STRONG"

    if problems == 0 and completed >= REVIEWABLE_LIGHT_MIN_COMPLETED:
        return "REVIEWABLE_LIGHT"

    return "WEAK"


def data_quality_regression_severity(
    old_entry: ReportIndexEntry,
    old_health: ReportHealth,
    new_entry: ReportIndexEntry,
    new_health: ReportHealth,
) -> DataQualityRegressionSeverity:
    """Classify data-quality regression between two bundles."""
    old_rank = _health_rank(old_health.status)
    new_rank = _health_rank(new_health.status)
    old_completed = old_health.completed_scenarios or 0
    new_completed = new_health.completed_scenarios or 0

    if new_rank > old_rank + 1:
        return "major"
    if new_health.status in ("NEEDS_RERUN", "BROKEN"):
        return "major"
    if new_completed < old_completed:
        return "major"
    new_total = new_health.total_scenarios or 0
    if new_total > 0 and new_completed < MIN_MEANINGFUL_COVERAGE_NUMERATOR:
        return "major"

    new_problems = coverage_problem_count(new_entry.coverage_status_counts)
    old_problems = coverage_problem_count(old_entry.coverage_status_counts)

    if new_problems >= 2 and new_problems > old_problems:
        return "major"

    if new_rank > old_rank:
        if (
            new_completed == old_completed
            and new_completed >= REVIEWABLE_LIGHT_MIN_COMPLETED
            and new_problems <= 1
        ):
            return "light"
        return "major"

    if new_problems > old_problems and new_problems >= 2:
        return "major"

    return "none"


def metrics_improvement_blocked(
    old_entry: ReportIndexEntry,
    old_health: ReportHealth,
    new_entry: ReportIndexEntry,
    new_health: ReportHealth,
) -> bool:
    """Return True when lower metrics must not be interpreted as improvement."""
    old_completed = old_health.completed_scenarios or 0
    new_completed = new_health.completed_scenarios or 0
    if new_completed < old_completed:
        return True
    old_problems = coverage_problem_count(old_entry.coverage_status_counts)
    new_problems = coverage_problem_count(new_entry.coverage_status_counts)
    if new_problems > old_problems:
        return True
    old_tier = classify_coverage_evidence(old_entry, old_health)
    new_tier = classify_coverage_evidence(new_entry, new_health)
    tier_order = {"STRONG": 0, "REVIEWABLE_LIGHT": 1, "WEAK": 2, "INSUFFICIENT": 3}
    return tier_order.get(new_tier, 3) > tier_order.get(old_tier, 0)


def _health_rank(status: HealthStatus) -> int:
    return {"READY": 0, "PARTIAL": 1, "NEEDS_RERUN": 2, "BROKEN": 3}.get(status, 3)
