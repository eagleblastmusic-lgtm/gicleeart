"""Read-only coverage recovery diagnostics and operator guidance (PA-3A)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from tools.performance_agent.profiles import get_profile
from tools.performance_agent.report.history import (
    MIN_BASELINE_COVERAGE_DENOMINATOR,
    MIN_BASELINE_COVERAGE_NUMERATOR,
)
from tools.performance_agent.report.index import (
    ReportHealth,
    ReportIndexEntry,
    evaluate_report_health,
)
from tools.performance_agent.report.semantics import classify_coverage_evidence
from tools.performance_agent.report.insights import (
    TimelineInsightSummary,
    _guardrails_section,
    _format_scenario_ratio,
    _resolve_workspace_root,
    build_timeline_summary,
)

CoverageStatus = Literal[
    "GOOD_COVERAGE",
    "WEAK_COVERAGE_LIGHT",
    "WEAK_COVERAGE",
    "NO_EVENTS",
    "BROKEN_COVERAGE",
]

_PROBLEM_COVERAGE_STATUSES = frozenset(
    {"missing_expected_events", "no_events_in_window", "skipped"}
)

_SCENARIO_GOALS_EN: dict[str, str] = {
    "dashboard_cold": "Capture Studio dashboard cold/initial readiness.",
    "hub_theme": "Capture Theme hub interaction.",
    "hub_products": "Capture Catalog / Products view entry.",
    "gf_open": "Capture first GICLÉE FRAME editor open.",
    "section_click_normal": "Capture normal-paced section clicking in GICLÉE FRAME.",
    "section_click_fast": "Capture rapid section clicking stress in GICLÉE FRAME.",
    "aba_cache": "Capture A -> B -> A section cache behavior.",
    "media_section": "Capture media_section load and nested child interaction.",
    "details_cta": "Capture on-demand details panel via Show details CTA.",
}

_SCENARIO_COVERAGE_RISKS: dict[str, str] = {
    "dashboard_cold": (
        "no_events_in_window if log window starts too late or app is already warm."
    ),
    "hub_theme": "skipped if the step is bypassed in wizard.",
    "hub_products": "skipped if operator navigates away before confirming the step.",
    "gf_open": "skipped if GICLÉE FRAME tile is not opened during the wizard step.",
    "section_click_normal": (
        "skipped or missing_expected_events if section clicks happen outside the scenario window."
    ),
    "section_click_fast": (
        "skipped or missing_expected_events if rapid clicks are not performed during the step."
    ),
    "aba_cache": (
        "missing_expected_events if A->B->A sequence is incomplete or cache signals are absent."
    ),
    "media_section": (
        "skipped if no media_section is available or the step is bypassed."
    ),
    "details_cta": (
        "skipped or missing_expected_events if Show details CTA is not clicked during the step."
    ),
}

_RECOVERY_CHECKLIST: tuple[str, ...] = (
    "Run full guided session:\n   python -m tools.performance_agent --run",
    "Do not skip scenario prompts unless intentionally narrowing the audit.",
    "Keep Studio open long enough for expected events to flush to log.",
    "After run:\n   python -m tools.performance_agent --health-latest",
    (
        "If health is READY/PARTIAL with >=7/9 coverage:\n"
        "   python -m tools.performance_agent --prepare-chatgpt-latest"
    ),
)


@dataclass(frozen=True)
class CoverageIssue:
    scenario_id: str
    status: str


@dataclass(frozen=True)
class CoverageRecoverySummary:
    entry: ReportIndexEntry
    health: ReportHealth
    timeline: TimelineInsightSummary
    coverage_status: CoverageStatus
    weak_scenarios: tuple[CoverageIssue, ...]
    likely_causes: tuple[str, ...]
    recovery_checklist: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioChecklistItem:
    scenario_id: str
    goal: str
    operator_action: str
    coverage_risk: str
    expected_events: tuple[str, ...]


def _completed_count(timeline: TimelineInsightSummary) -> int:
    return timeline.completed if timeline.completed is not None else 0


def _skipped_count(timeline: TimelineInsightSummary) -> int:
    return timeline.skipped if timeline.skipped is not None else 0


def _total_count(timeline: TimelineInsightSummary) -> int | None:
    return timeline.total


def _has_problem_coverage_statuses(timeline: TimelineInsightSummary) -> bool:
    return any(
        timeline.coverage_counts.get(name, 0) > 0
        for name in ("missing_expected_events", "no_events_in_window")
    )


def classify_coverage_status(
    entry: ReportIndexEntry,
    health: ReportHealth,
    timeline: TimelineInsightSummary,
) -> CoverageStatus:
    """Deterministic coverage status from health and timeline data."""
    if health.status == "BROKEN":
        return "BROKEN_COVERAGE"

    completed = _completed_count(timeline)
    events = entry.total_events

    if health.status == "NEEDS_RERUN":
        return "NO_EVENTS"
    if events is not None and events == 0:
        return "NO_EVENTS"
    if completed == 0:
        return "NO_EVENTS"

    total = _total_count(timeline)
    if total is None or total == 0:
        return "NO_EVENTS"

    if health.status == "READY" and completed >= max(8, total - 1):
        return "GOOD_COVERAGE"

    if health.status == "PARTIAL":
        if completed >= MIN_BASELINE_COVERAGE_NUMERATOR:
            if _has_problem_coverage_statuses(timeline):
                return "WEAK_COVERAGE_LIGHT"
            return "GOOD_COVERAGE"
        return "WEAK_COVERAGE"

    if health.status == "READY":
        return "GOOD_COVERAGE"

    return "WEAK_COVERAGE"


def _weak_scenarios_from_timeline(timeline: TimelineInsightSummary) -> tuple[CoverageIssue, ...]:
    issues: list[CoverageIssue] = []
    for scenario_id, status in timeline.weakest_scenarios:
        if scenario_id in ("scenario", "scenarios"):
            continue
        issues.append(CoverageIssue(scenario_id=scenario_id, status=status))
    return tuple(issues)


def _build_likely_causes(
    *,
    entry: ReportIndexEntry,
    health: ReportHealth,
    timeline: TimelineInsightSummary,
    coverage_status: CoverageStatus,
) -> tuple[str, ...]:
    causes: list[str] = []
    completed = _completed_count(timeline)
    skipped = _skipped_count(timeline)
    total = _total_count(timeline)
    tier = classify_coverage_evidence(entry, health)

    if coverage_status == "BROKEN_COVERAGE":
        causes.append("Bundle is missing key report files — repair or rerun the audit.")
        return tuple(causes)

    if coverage_status == "NO_EVENTS":
        causes.append("Log data is empty or no scenarios completed — rerun with Studio logging enabled.")
        return tuple(causes)

    if skipped > 0 and total is not None and skipped >= completed:
        causes.append("Most scenarios were skipped by operator flow or wizard state.")

    no_events_count = timeline.coverage_counts.get("no_events_in_window", 0)
    if no_events_count > 0:
        count_text = "One scenario" if no_events_count == 1 else f"{no_events_count} scenarios"
        causes.append(
            f"{count_text} had no expected events in the selected log window."
        )

    early_count = timeline.coverage_counts.get("early_event_seen", 0)
    if early_count > 0:
        causes.append(
            "Dashboard events were seen before the scenario window (startup timing) — "
            "classified as early_event_seen."
        )

    missing_count = timeline.coverage_counts.get("missing_expected_events", 0)
    if missing_count > 0:
        causes.append(
            "Some completed scenarios lack expected log confirmation (instrumentation or timing)."
        )

    if health.status == "PARTIAL" and completed < MIN_BASELINE_COVERAGE_NUMERATOR:
        causes.append(
            f"Coverage is below the {MIN_BASELINE_COVERAGE_NUMERATOR}/"
            f"{MIN_BASELINE_COVERAGE_DENOMINATOR} threshold for meaningful comparison."
        )

    if coverage_status == "WEAK_COVERAGE":
        causes.append(
            "Current bundle is useful for instrumentation smoke review, not for performance comparison."
        )
    elif coverage_status == "WEAK_COVERAGE_LIGHT" and tier == "REVIEWABLE_LIGHT":
        causes.append(
            "Current bundle is reviewable with caveat — useful for focused review, "
            "not for broad performance comparison."
        )
    elif coverage_status in ("WEAK_COVERAGE", "WEAK_COVERAGE_LIGHT"):
        causes.append(
            "Current bundle is useful for instrumentation smoke review, not for performance comparison."
        )

    if not causes:
        causes.append("Coverage looks sufficient — verify health before drawing performance conclusions.")

    return tuple(causes)


def build_coverage_summary(entry: ReportIndexEntry) -> CoverageRecoverySummary:
    """Build a coverage recovery summary for a report bundle."""
    health = evaluate_report_health(entry)
    timeline = build_timeline_summary(entry)
    coverage_status = classify_coverage_status(entry, health, timeline)
    weak_scenarios = _weak_scenarios_from_timeline(timeline)
    likely_causes = _build_likely_causes(
        entry=entry,
        health=health,
        timeline=timeline,
        coverage_status=coverage_status,
    )
    return CoverageRecoverySummary(
        entry=entry,
        health=health,
        timeline=timeline,
        coverage_status=coverage_status,
        weak_scenarios=weak_scenarios,
        likely_causes=likely_causes,
        recovery_checklist=_RECOVERY_CHECKLIST,
    )


def format_coverage_summary(summary: CoverageRecoverySummary) -> str:
    """Format operator output for ``--coverage-latest`` / ``--coverage-report``."""
    timeline = summary.timeline
    completed = _completed_count(timeline)
    skipped = _skipped_count(timeline)
    total = _total_count(timeline)
    total_display = total if total is not None else "n/a"

    lines = [
        "Performance Agent — coverage recovery",
        "=" * 37,
        f"Bundle: {summary.entry.dir_name}",
        f"Health: {summary.health.status}",
        "",
        "Coverage:",
        f"- completed: {completed}/{total_display}",
        f"- skipped: {skipped}/{total_display}",
        f"- status: {summary.coverage_status}",
        "",
    ]

    no_events_count = timeline.coverage_counts.get("no_events_in_window", 0)
    if no_events_count > 0:
        lines.append(f"- no_events_in_window: {no_events_count}")
        lines.append("")

    if summary.weak_scenarios:
        lines.append("Weak scenarios:")
        for index, issue in enumerate(summary.weak_scenarios, start=1):
            lines.append(f"{index}. {issue.scenario_id} — {issue.status}")
        lines.append("")

    lines.append("Likely causes:")
    for cause in summary.likely_causes:
        lines.append(f"- {cause}")
    lines.append("")

    lines.append("Recovery checklist:")
    for index, step in enumerate(summary.recovery_checklist, start=1):
        lines.append(f"{index}. {step}")

    return "\n".join(lines)


def _operator_action_for_scenario(scenario) -> str:
    parts: list[str] = []
    if scenario.click_path:
        parts.append(scenario.click_path[0])
    if scenario.success_hint:
        parts.append(scenario.success_hint)
    return " ".join(parts) if parts else "Follow the wizard prompt for this scenario."


def build_scenario_checklist(profile_id: str = "giclee_studio") -> list[ScenarioChecklistItem]:
    """Build operator checklist items from profile scenario definitions."""
    profile = get_profile(profile_id)
    items: list[ScenarioChecklistItem] = []
    for scenario in profile.manual_scenarios:
        goal = _SCENARIO_GOALS_EN.get(scenario.id, scenario.goal or scenario.display_title)
        coverage_risk = _SCENARIO_COVERAGE_RISKS.get(
            scenario.id,
            "skipped if the wizard step is bypassed or log events are outside the window.",
        )
        items.append(
            ScenarioChecklistItem(
                scenario_id=scenario.id,
                goal=goal,
                operator_action=_operator_action_for_scenario(scenario),
                coverage_risk=coverage_risk,
                expected_events=scenario.expected_event_patterns,
            )
        )
    return items


def format_scenario_checklist(
    items: list[ScenarioChecklistItem],
    *,
    profile_id: str = "giclee_studio",
) -> str:
    """Format operator output for ``--scenario-checklist``."""
    lines = [
        "Performance Agent — scenario checklist",
        "=" * 38,
        f"Profile: {profile_id}",
        f"Scenarios: {len(items)}",
        "",
    ]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. {item.scenario_id}",
                f"   Goal: {item.goal}",
                f"   Operator action: {item.operator_action}",
                f"   Coverage risk: {item.coverage_risk}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def build_run_playbook(profile_id: str = "giclee_studio") -> str:
    """Return full-run operator playbook text."""
    return "\n".join(
        [
            "Performance Agent — full run playbook",
            "=" * 37,
            f"Profile: {profile_id}",
            "",
            "Before run:",
            "1. Close unnecessary apps if possible.",
            "2. Start from a known Studio state.",
            "3. Do not clear reports/performance manually.",
            "4. Keep terminal visible.",
            "",
            "Run:",
            "python -m tools.performance_agent --run",
            "",
            "During run:",
            "1. Follow each scenario prompt.",
            "2. Avoid skipping unless intentionally narrowing the audit.",
            "3. After each interaction, wait until UI settles.",
            "4. If scenario seems unclear, write notes in the wizard instead of skipping.",
            "",
            "After run:",
            "1. python -m tools.performance_agent --health-latest",
            "2. python -m tools.performance_agent --coverage-latest",
            "3. python -m tools.performance_agent --analyze-latest",
            "4. python -m tools.performance_agent --prepare-chatgpt-latest",
            "",
            "Quality target:",
            "- READY or PARTIAL with at least 7/9 completed scenarios.",
            "- Avoid drawing performance conclusions from 1/9 coverage.",
            "- 1/9 coverage is not performance evidence.",
        ]
    )


def build_coverage_prompt(
    entry: ReportIndexEntry,
    *,
    workspace_root: Path | None = None,
) -> str:
    """Build a Cursor prompt focused on coverage/instrumentation recovery."""
    summary = build_coverage_summary(entry)
    health = summary.health
    timeline = summary.timeline
    resolved_workspace = _resolve_workspace_root(entry.report_dir, workspace_root)
    bundle_path = entry.report_dir.resolve()

    weak_lines = [
        f"- {issue.scenario_id}: {issue.status}" for issue in summary.weak_scenarios
    ]
    if not weak_lines:
        weak_lines = ["- (none listed — verify scenario_timeline.csv)"]

    lines = [
        "# Cursor Prompt — Performance Agent Coverage Recovery",
        "",
        f"Workspace:\n{resolved_workspace}",
        "",
        f"Report bundle:\n{bundle_path}",
        "",
        f"Health:\n{health.status}",
        "",
        f"Coverage status:\n{summary.coverage_status}",
        "",
        f"Scenario coverage:\ncompleted {_format_scenario_ratio(timeline.completed, timeline.total)}, "
        f"skipped {_format_scenario_ratio(timeline.skipped, timeline.total)}",
        "",
        "Weak scenarios:",
        *weak_lines,
        "",
        "Important:",
        "This is a coverage / instrumentation recovery review — NOT a Studio performance optimization task.",
        "Do not optimize Studio from this bundle.",
        "Do not plan broad performance fixes from weak-coverage data.",
        "1/9 coverage is not performance evidence.",
        "",
        "Task:",
        "1. Review Performance Agent runner/wizard/scenario definitions.",
        "2. Explain why scenarios may have been skipped or marked no_events_in_window.",
        "3. Propose a plan to improve coverage for the next run.",
        "4. Do not implement without user approval.",
        "",
        "Inspect:",
        "- tools/performance_agent/runner.py",
        "- tools/performance_agent/wizard.py",
        "- tools/performance_agent/profiles.py",
        "- scenario_timeline.csv",
        "- summary.json",
        "- questions_answers.json",
        "",
        "Focus:",
        "1. Identify wizard skip paths and operator flow gaps.",
        "2. Check expected_event_patterns vs actual log events per scenario.",
        "3. Recommend the safest next run procedure.",
        "4. Do not modify GicleeApp Studio code.",
        "5. Do not change GICLÉE FRAME runtime.",
        "6. Do not edit Komponenty/*.",
        "7. Do not commit or push.",
        "",
        "Expected output:",
        "- coverage / data quality assessment",
        "- why each weak scenario failed (skipped / no_events_in_window / missing events)",
        "- step-by-step plan for the next full run",
        "- exact next command: python -m tools.performance_agent --run",
        "- no code changes without explicit user approval",
        "",
        *_guardrails_section(),
    ]
    return "\n".join(lines)
