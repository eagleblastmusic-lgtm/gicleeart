"""Deep read-only insights from Performance Agent report bundles (PA-2B)."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from tools.performance_agent.report.analyzer import (
    ReportAnalysis,
    ReportComparison,
    analyze_report_bundle,
)
from tools.performance_agent.report.index import (
    ReportHealth,
    ReportIndexEntry,
    evaluate_report_health,
)
from tools.performance_agent.report.semantics import (
    classify_coverage_evidence,
    is_duration_ms_field,
)

_TRUE_VALUES = frozenset({"true", "1", "yes"})
_FALSE_VALUES = frozenset({"false", "0", "no"})


def _parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return None


def _parse_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _resolve_workspace_root(report_dir: Path, workspace_root: Path | None = None) -> Path:
    if workspace_root is not None:
        return workspace_root.resolve()
    parent = report_dir.parent
    if parent.name == "performance" and parent.parent.name == "reports":
        return parent.parent.parent.resolve()
    return parent.parent.resolve()


def load_slow_events_csv(report_dir: Path) -> list[dict]:
    """Load ``slow_events.csv`` rows, or return an empty list if missing/unreadable."""
    csv_path = report_dir / "slow_events.csv"
    if not csv_path.is_file():
        return []
    try:
        with csv_path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []


def load_scenario_timeline_csv(report_dir: Path) -> list[dict]:
    """Load ``scenario_timeline.csv`` rows, or return an empty list if missing/unreadable."""
    csv_path = report_dir / "scenario_timeline.csv"
    if not csv_path.is_file():
        return []
    try:
        with csv_path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except (OSError, csv.Error):
        return []


@dataclass(frozen=True)
class SlowHotspotSummary:
    entry: ReportIndexEntry
    health: ReportHealth
    csv_present: bool
    total: int
    summary_fallback_count: int | None
    severity_counts: dict[str, int]
    top_events: tuple[tuple[str, int], ...]
    top_modules: tuple[tuple[str, int], ...]
    top_stages: tuple[tuple[str, int], ...]
    top_slow_rows: tuple[str, ...]
    interpretation: str


@dataclass(frozen=True)
class TimelineInsightSummary:
    entry: ReportIndexEntry
    health: ReportHealth
    csv_present: bool
    completed: int | None
    skipped: int | None
    total: int | None
    coverage_counts: dict[str, int]
    longest_scenarios: tuple[tuple[str, float], ...]
    weakest_scenarios: tuple[tuple[str, str], ...]
    interpretation: str


@dataclass(frozen=True)
class CursorPromptBundle:
    entry: ReportIndexEntry
    health: ReportHealth
    analysis: ReportAnalysis
    hotspots: SlowHotspotSummary
    timeline: TimelineInsightSummary
    comparison: ReportComparison | None
    workspace_root: Path
    prompt_text: str


def _count_nonempty(rows: list[dict], field: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            counts[text] += 1
    return counts


def _filter_duration_slow_rows(rows: list[dict]) -> tuple[list[dict], bool]:
    """Keep only rows with duration-like ms fields; report if any were excluded."""
    kept: list[dict] = []
    excluded = False
    for row in rows:
        ms_field = str(row.get("ms_field") or "").strip()
        if ms_field and not is_duration_ms_field(ms_field):
            excluded = True
            continue
        kept.append(row)
    return kept, excluded


def _build_hotspot_interpretation(
    health: ReportHealth,
    *,
    csv_present: bool,
    non_duration_excluded: bool = False,
    entry: ReportIndexEntry | None = None,
) -> str:
    if not csv_present:
        if health.status in ("NEEDS_RERUN", "BROKEN"):
            return (
                "slow_events.csv is missing — rerun or regenerate the bundle before "
                "drawing performance conclusions."
            )
        return (
            "slow_events.csv is missing — hotspot detail is unavailable; "
            "use summary.json counts only as a fallback."
        )

    parts: list[str] = []
    tier = classify_coverage_evidence(entry, health) if entry is not None else None

    if tier == "REVIEWABLE_LIGHT":
        parts.append(
            "Data quality is PARTIAL with a small coverage caveat — treat hotspots as "
            "directional, reviewable with caveat."
        )
    elif health.status == "PARTIAL":
        parts.append(
            "Data quality is PARTIAL, so treat hotspots as directional, "
            "not as full regression proof."
        )
    elif health.status in ("NEEDS_RERUN", "BROKEN"):
        parts.append(
            "Bundle health is weak — treat any hotspot signals as preliminary "
            "until a full audit is repeated."
        )
    else:
        parts.append("Hotspot data looks sufficient for a focused performance review.")

    if non_duration_excluded:
        parts.append(
            "Some rows use non-duration timing fields (e.g. since_enter_ms) "
            "and were excluded from latency ranking."
        )

    return " ".join(parts)


def build_hotspot_summary(entry: ReportIndexEntry) -> SlowHotspotSummary:
    """Build a slow-event hotspot summary for a report bundle."""
    health = evaluate_report_health(entry)
    csv_present = entry.has_slow_events_csv
    raw_rows = load_slow_events_csv(entry.report_dir) if csv_present else []
    rows, non_duration_excluded = _filter_duration_slow_rows(raw_rows)

    severity_counts = dict(_count_nonempty(rows, "severity"))
    top_events = tuple(_count_nonempty(rows, "event").most_common(5))
    top_modules = tuple(_count_nonempty(rows, "module").most_common(5))
    top_stages = tuple(_count_nonempty(rows, "stage").most_common(5))

    ranked_rows: list[tuple[float, dict]] = []
    for row in rows:
        ms = _parse_float(row.get("ms"))
        if ms is not None:
            ranked_rows.append((ms, row))
    ranked_rows.sort(key=lambda item: item[0], reverse=True)

    top_slow_rows: list[str] = []
    for ms, row in ranked_rows[:10]:
        event = str(row.get("event") or "unknown")
        severity = str(row.get("severity") or "n/a")
        line_no = str(row.get("line_no") or "?")
        ms_field = str(row.get("ms_field") or "")
        field_suffix = f" {ms_field}" if ms_field else ""
        top_slow_rows.append(f"{ms:.1f}ms [{severity}] {event}{field_suffix} L{line_no}")

    summary_fallback = entry.slow_event_count if not raw_rows else None
    total = len(rows) if rows else 0

    return SlowHotspotSummary(
        entry=entry,
        health=health,
        csv_present=csv_present and bool(raw_rows),
        total=total,
        summary_fallback_count=summary_fallback if not raw_rows else None,
        severity_counts=severity_counts,
        top_events=top_events,
        top_modules=top_modules,
        top_stages=top_stages,
        top_slow_rows=tuple(top_slow_rows),
        interpretation=_build_hotspot_interpretation(
            health,
            csv_present=csv_present and bool(raw_rows),
            non_duration_excluded=non_duration_excluded,
            entry=entry,
        ),
    )


def format_hotspot_summary(summary: SlowHotspotSummary) -> str:
    """Format operator output for hotspot insights."""
    lines = [
        "Performance Agent — hotspots",
        "=" * 28,
        f"Bundle: {summary.entry.dir_name}",
        f"Health: {summary.health.status}",
        "",
        "Slow events:",
    ]

    if not summary.entry.has_slow_events_csv:
        lines.append("- slow_events.csv: not present in bundle")
        if summary.summary_fallback_count is not None:
            lines.append(
                f"- total (from summary.json fallback): {summary.summary_fallback_count}"
            )
        else:
            lines.append("- total: n/a")
    elif summary.total == 0:
        lines.append("- slow_events.csv: present but empty or unreadable")
        if summary.summary_fallback_count is not None:
            lines.append(
                f"- total (from summary.json fallback): {summary.summary_fallback_count}"
            )
    else:
        lines.append(f"- total: {summary.total}")
        for severity, count in sorted(summary.severity_counts.items()):
            lines.append(f"- {severity}: {count}")

    if summary.top_events:
        lines.extend(["", "Top event names:"])
        for index, (event, count) in enumerate(summary.top_events, start=1):
            lines.append(f"{index}. {event} — {count}")

    if summary.top_modules:
        lines.extend(["", "Top modules:"])
        for index, (module, count) in enumerate(summary.top_modules, start=1):
            lines.append(f"{index}. {module} — {count}")

    if summary.top_stages:
        lines.extend(["", "Top stages:"])
        for index, (stage, count) in enumerate(summary.top_stages, start=1):
            lines.append(f"{index}. {stage} — {count}")

    if summary.top_slow_rows:
        lines.extend(["", "Top slow rows:"])
        for index, row_text in enumerate(summary.top_slow_rows, start=1):
            lines.append(f"{index}. {row_text}")

    lines.extend(["", "Interpretation:", summary.interpretation])
    return "\n".join(lines)


def _timeline_counts_from_csv(
    rows: list[dict],
) -> tuple[int | None, int | None, int | None, dict[str, int]]:
    if not rows:
        return None, None, None, {}

    completed = 0
    skipped = 0
    total = 0
    coverage: Counter[str] = Counter()

    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        if not scenario_id:
            continue
        total += 1
        if _parse_bool(row.get("completed")) is True:
            completed += 1
        if _parse_bool(row.get("skipped")) is True:
            skipped += 1
        status = str(row.get("log_coverage_status") or "").strip()
        if status:
            coverage[status] += 1

    if total == 0:
        return None, None, None, {}

    return completed, skipped, total, dict(coverage)


def _weakest_from_csv(rows: list[dict]) -> list[tuple[str, str]]:
    weakest: list[tuple[str, str]] = []
    problem_statuses = ("missing_expected_events", "no_events_in_window")

    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        if not scenario_id:
            continue
        status = str(row.get("log_coverage_status") or "").strip()
        if status in problem_statuses:
            weakest.append((scenario_id, status))
        elif _parse_bool(row.get("skipped")) is True:
            weakest.append((scenario_id, "skipped"))

    return weakest


def _longest_from_csv(rows: list[dict], *, limit: int = 5) -> list[tuple[str, float]]:
    ranked: list[tuple[float, str]] = []
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        duration = _parse_float(row.get("duration_ms"))
        if scenario_id and duration is not None:
            ranked.append((duration, scenario_id))
    ranked.sort(reverse=True)
    return [(scenario_id, duration) for duration, scenario_id in ranked[:limit]]


def _build_timeline_interpretation(
    health: ReportHealth,
    entry: ReportIndexEntry,
    *,
    completed: int | None,
    total: int | None,
    coverage_counts: dict[str, int],
) -> str:
    if health.status in ("NEEDS_RERUN", "BROKEN"):
        return (
            "This bundle needs a rerun or repair before scenario timeline data "
            "can support performance conclusions."
        )

    tier = classify_coverage_evidence(entry, health)

    if tier == "REVIEWABLE_LIGHT":
        return (
            "Scenario coverage is mostly complete with a small log-window caveat — "
            "reviewable with caveat for focused performance review."
        )

    if tier == "WEAK":
        return (
            "This bundle is not suitable for full performance conclusions. "
            "It is useful only for checking instrumentation and a narrow smoke review."
        )

    weak_coverage = False
    if total is not None and completed is not None and total > 0:
        if completed < total:
            weak_coverage = True
    if any(
        coverage_counts.get(name, 0) > 0
        for name in ("skipped", "no_events_in_window", "missing_expected_events")
    ):
        weak_coverage = True

    if health.status == "PARTIAL" or weak_coverage:
        return (
            "This bundle is not suitable for full performance conclusions. "
            "It is useful only for checking instrumentation and a narrow smoke review."
        )
    return "Scenario coverage looks sufficient for timeline-based performance review."


def build_timeline_summary(entry: ReportIndexEntry) -> TimelineInsightSummary:
    """Build a scenario timeline insight summary for a report bundle."""
    health = evaluate_report_health(entry)
    csv_present = entry.has_scenario_timeline_csv
    rows = load_scenario_timeline_csv(entry.report_dir) if csv_present else []

    csv_completed, csv_skipped, csv_total, csv_coverage = _timeline_counts_from_csv(rows)

    completed = csv_completed if csv_total is not None else health.completed_scenarios
    skipped = csv_skipped if csv_total is not None else health.skipped_scenarios
    total = csv_total if csv_total is not None else health.total_scenarios

    coverage_counts = csv_coverage if csv_coverage else dict(entry.coverage_status_counts or {})

    weakest = tuple(_weakest_from_csv(rows) if rows else _weakest_from_health(entry, health))
    longest = tuple(_longest_from_csv(rows))

    return TimelineInsightSummary(
        entry=entry,
        health=health,
        csv_present=csv_present and bool(rows),
        completed=completed,
        skipped=skipped,
        total=total,
        coverage_counts=coverage_counts,
        longest_scenarios=longest,
        weakest_scenarios=weakest,
        interpretation=_build_timeline_interpretation(
            health,
            entry,
            completed=completed,
            total=total,
            coverage_counts=coverage_counts,
        ),
    )


def _weakest_from_health(entry: ReportIndexEntry, health: ReportHealth) -> list[tuple[str, str]]:
    weakest: list[tuple[str, str]] = []
    counts = entry.coverage_status_counts or {}
    if counts.get("no_events_in_window", 0) > 0:
        weakest.append(("scenario", "no_events_in_window"))
    if counts.get("missing_expected_events", 0) > 0:
        weakest.append(("scenario", "missing_expected_events"))
    if health.skipped_scenarios and health.skipped_scenarios > 0:
        weakest.append(("scenarios", "skipped"))
    return weakest


def format_timeline_summary(summary: TimelineInsightSummary) -> str:
    """Format operator output for scenario timeline insights."""
    lines = [
        "Performance Agent — scenario timeline",
        "=" * 37,
        f"Bundle: {summary.entry.dir_name}",
        f"Health: {summary.health.status}",
        "",
    ]

    if not summary.entry.has_scenario_timeline_csv:
        lines.append("scenario_timeline.csv: not present in bundle")
        lines.append("")

    completed = summary.completed if summary.completed is not None else 0
    skipped = summary.skipped if summary.skipped is not None else 0
    total = summary.total if summary.total is not None else "n/a"

    lines.extend(
        [
            "Scenarios:",
            f"- completed: {completed}/{total}",
            f"- skipped: {skipped}/{total}",
            "",
            "Coverage:",
        ]
    )

    if summary.coverage_counts:
        for status, count in sorted(summary.coverage_counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- n/a")

    if summary.longest_scenarios:
        lines.extend(["", "Longest scenarios:"])
        for scenario_id, duration in summary.longest_scenarios:
            lines.append(f"- {scenario_id} — {duration:.1f}ms")

    if summary.weakest_scenarios:
        lines.extend(["", "Weakest scenarios:"])
        for scenario_id, reason in summary.weakest_scenarios:
            lines.append(f"- {scenario_id} — {reason}")

    lines.extend(["", "Interpretation:", summary.interpretation])
    return "\n".join(lines)


def _guardrails_section() -> list[str]:
    return [
        "Guardrails:",
        "- Do not modify GicleeApp Studio code.",
        "- Do not change GICLÉE FRAME runtime.",
        "- Do not edit Komponenty/*.",
        "- Do not commit or push.",
    ]


def _format_scenario_ratio(completed: int | None, total: int | None) -> str:
    if total is None:
        return "n/a"
    return f"{completed or 0}/{total}"


def _build_ready_prompt_sections(
    *,
    bundle_path: Path,
    workspace_root: Path,
    health: ReportHealth,
    hotspots: SlowHotspotSummary,
    timeline: TimelineInsightSummary,
    comparison: ReportComparison | None,
) -> list[str]:
    lines = [
        "# Cursor Prompt — Performance Agent Report Review",
        "",
        f"Workspace:\n{workspace_root}",
        "",
        f"Report bundle:\n{bundle_path}",
        "",
        f"Health:\n{health.status}",
        "",
        "Important:",
        "This bundle looks READY for a focused performance review.",
        "You may analyze code paths and propose P0 fixes, but do not implement without user approval.",
        "",
        "Task:",
        "Review the Performance Agent bundle and identify the highest-priority performance issues.",
        "",
        "Inspect:",
        "- report.md",
        "- summary.json",
        "- slow_events.csv",
        "- scenario_timeline.csv",
        "- questions_answers.json",
        "",
        "Focus:",
        "1. Confirm whether slow events and UX suspects align with real code paths.",
        "2. Propose P0 fixes with file-level references — do not implement without approval.",
        "3. Note any instrumentation gaps even if coverage is generally good.",
        "4. Do not modify GicleeApp Studio code.",
        "5. Do not change GICLÉE FRAME runtime.",
        "6. Do not edit Komponenty/*.",
        "7. Do not commit or push.",
    ]

    if hotspots.top_slow_rows:
        lines.extend(["", "Top slow signals (from bundle):", *[f"- {row}" for row in hotspots.top_slow_rows[:5]]])

    if comparison is not None and comparison.result not in ("NOT_COMPARABLE",):
        lines.extend(
            [
                "",
                "Comparison (old vs new):",
                f"- result: {comparison.result}",
                f"- interpretation: {comparison.interpretation}",
            ]
        )

    lines.extend(
        [
            "",
            "Expected output:",
            "- P0 performance findings with evidence from the bundle",
            "- proposed fixes only (no code changes without approval)",
            "- whether another PA run is recommended",
            f"- scenario coverage: completed {_format_scenario_ratio(timeline.completed, timeline.total)}",
        ]
    )
    lines.extend([""] + _guardrails_section())
    return lines


def _build_partial_prompt_sections(
    *,
    bundle_path: Path,
    workspace_root: Path,
    health: ReportHealth,
    timeline: TimelineInsightSummary,
) -> list[str]:
    coverage_note = (
        f"This bundle has weak scenario coverage: "
        f"completed {_format_scenario_ratio(timeline.completed, timeline.total)}, "
        f"skipped {_format_scenario_ratio(timeline.skipped, timeline.total)}."
    )
    return [
        "# Cursor Prompt — Performance Agent Report Review",
        "",
        f"Workspace:\n{workspace_root}",
        "",
        f"Report bundle:\n{bundle_path}",
        "",
        f"Health:\n{health.status}",
        "",
        "Important:",
        coverage_note,
        "Do not plan broad Studio optimization from this data.",
        "",
        "Task:",
        "Review the Performance Agent bundle for data quality and instrumentation correctness.",
        "",
        "Inspect:",
        "- report.md",
        "- summary.json",
        "- slow_events.csv",
        "- scenario_timeline.csv",
        "- questions_answers.json",
        "",
        "Focus:",
        "1. Confirm whether the bundle is internally consistent.",
        "2. Identify why scenario coverage is weak.",
        "3. Suggest the safest next Performance Agent run procedure.",
        "4. Do not modify GicleeApp Studio code.",
        "5. Do not change GICLÉE FRAME runtime.",
        "6. Do not edit Komponenty/*.",
        "7. Do not commit or push.",
        "",
        "Expected output:",
        "- data quality assessment",
        "- whether rerun is required",
        "- exact next command to run: python -m tools.performance_agent --run",
        "- no code changes",
        "",
        *_guardrails_section(),
    ]


def _build_rerun_prompt_sections(
    *,
    bundle_path: Path,
    workspace_root: Path,
    health: ReportHealth,
    analysis: ReportAnalysis,
) -> list[str]:
    return [
        "# Cursor Prompt — Performance Agent Report Review",
        "",
        f"Workspace:\n{workspace_root}",
        "",
        f"Report bundle:\n{bundle_path}",
        "",
        f"Health:\n{health.status}",
        "",
        "Important:",
        "Do not analyze Studio performance code from this bundle.",
        "First repair or repeat the Performance Agent audit.",
        "",
        "Task:",
        "Diagnose why this bundle is not ready for performance analysis.",
        "",
        "Inspect:",
        "- report.md",
        "- summary.json",
        "- slow_events.csv",
        "- scenario_timeline.csv",
        "- questions_answers.json",
        "",
        "Focus:",
        "1. Identify missing files, empty logs, or broken scenario coverage.",
        "2. Recommend the exact rerun procedure — do not optimize Studio code.",
        "3. Check whether log lifecycle or wizard steps caused the failure.",
        "4. Do not modify GicleeApp Studio code.",
        "5. Do not change GICLÉE FRAME runtime.",
        "6. Do not edit Komponenty/*.",
        "7. Do not commit or push.",
        "",
        "Data quality notes:",
        *[f"- {note}" for note in analysis.data_quality_notes],
        "",
        "Expected output:",
        "- audit repair checklist",
        "- exact next command: python -m tools.performance_agent --run",
        "- no performance code changes",
        "",
        *_guardrails_section(),
    ]


def build_cursor_prompt_bundle(
    entry: ReportIndexEntry,
    *,
    workspace_root: Path | None = None,
    comparison: ReportComparison | None = None,
) -> CursorPromptBundle:
    """Build a health-aware Cursor prompt bundle for a report."""
    health = evaluate_report_health(entry)
    analysis = analyze_report_bundle(entry)
    hotspots = build_hotspot_summary(entry)
    timeline = build_timeline_summary(entry)
    resolved_workspace = _resolve_workspace_root(entry.report_dir, workspace_root)
    bundle_path = entry.report_dir.resolve()

    if health.status == "READY":
        sections = _build_ready_prompt_sections(
            bundle_path=bundle_path,
            workspace_root=resolved_workspace,
            health=health,
            hotspots=hotspots,
            timeline=timeline,
            comparison=comparison,
        )
    elif health.status == "PARTIAL":
        sections = _build_partial_prompt_sections(
            bundle_path=bundle_path,
            workspace_root=resolved_workspace,
            health=health,
            timeline=timeline,
        )
    else:
        sections = _build_rerun_prompt_sections(
            bundle_path=bundle_path,
            workspace_root=resolved_workspace,
            health=health,
            analysis=analysis,
        )

    return CursorPromptBundle(
        entry=entry,
        health=health,
        analysis=analysis,
        hotspots=hotspots,
        timeline=timeline,
        comparison=comparison,
        workspace_root=resolved_workspace,
        prompt_text="\n".join(sections),
    )


def build_cursor_prompt(
    entry: ReportIndexEntry,
    *,
    workspace_root: Path | None = None,
    comparison: ReportComparison | None = None,
) -> str:
    """Return the Cursor prompt text for a report bundle."""
    return build_cursor_prompt_bundle(
        entry,
        workspace_root=workspace_root,
        comparison=comparison,
    ).prompt_text
