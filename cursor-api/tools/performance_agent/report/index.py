"""Read-only index and inspection for existing Performance Agent report bundles."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


_PROFILE_SUFFIX = "_{profile_id}"
_COPY_FOR_CHATGPT_HEADING = "## COPY FOR CHATGPT"
_TECHNICAL_REPORT_MARKER = "# Performance Audit Report"


class CopyBlockNotFoundError(ValueError):
    """Raised when ``report.md`` does not contain a COPY FOR CHATGPT block."""


@dataclass(frozen=True)
class ReportIndexEntry:
    report_dir: Path
    dir_name: str
    mode: str | None
    source_log: str | None
    total_events: int | None
    malformed_lines: int | None
    slow_event_count: int | None
    suspect_count: int | None
    ux_conflict_count: int | None
    log_coverage_conflict_count: int | None
    coverage_status_counts: dict[str, int] | None
    has_report_md: bool
    has_summary_json: bool
    has_slow_events_csv: bool
    has_scenario_timeline_csv: bool
    has_questions_answers_json: bool


HealthStatus = Literal["READY", "PARTIAL", "NEEDS_RERUN", "BROKEN"]

_HEALTH_SEVERITY: dict[HealthStatus, int] = {
    "READY": 0,
    "PARTIAL": 1,
    "NEEDS_RERUN": 2,
    "BROKEN": 3,
}


@dataclass(frozen=True)
class ReportHealth:
    entry: ReportIndexEntry
    status: HealthStatus
    completed_scenarios: int | None
    skipped_scenarios: int | None
    total_scenarios: int | None
    recommendation: str


def discover_report_dirs(output_root: Path, profile_id: str) -> list[Path]:
    """Return report bundle directories for *profile_id*, newest first."""
    if not output_root.is_dir():
        return []

    suffix = _PROFILE_SUFFIX.format(profile_id=profile_id)
    candidates: list[Path] = []
    for child in output_root.iterdir():
        if not child.is_dir():
            continue
        if child.name == "_archive":
            continue
        if not child.name.endswith(suffix):
            continue
        candidates.append(child)

    return sorted(candidates, key=lambda path: path.name, reverse=True)


def load_summary_json(report_dir: Path) -> dict[str, Any]:
    """Load ``summary.json`` from a bundle, or return an empty dict if missing/invalid."""
    summary_path = report_dir / "summary.json"
    if not summary_path.is_file():
        return {}
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _coverage_status_counts(summary: dict[str, Any]) -> dict[str, int] | None:
    raw = summary.get("scenario_log_coverage")
    if not isinstance(raw, list) or not raw:
        return None
    counts: Counter[str] = Counter()
    for entry in raw:
        if isinstance(entry, dict):
            status = entry.get("status")
            if isinstance(status, str) and status:
                counts[status] += 1
    return dict(counts) if counts else None


def _optional_int(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def summarize_report_bundle(report_dir: Path) -> ReportIndexEntry:
    """Build an index entry for an on-disk report bundle."""
    summary = load_summary_json(report_dir)
    ux_conflicts = summary.get("ux_conflicts")
    log_coverage_conflicts = summary.get("log_coverage_conflicts")

    return ReportIndexEntry(
        report_dir=report_dir.resolve(),
        dir_name=report_dir.name,
        mode=summary.get("mode") if isinstance(summary.get("mode"), str) else None,
        source_log=summary.get("source_log")
        if isinstance(summary.get("source_log"), str)
        else None,
        total_events=_optional_int(summary, "total_events"),
        malformed_lines=_optional_int(summary, "malformed_lines"),
        slow_event_count=_optional_int(summary, "slow_event_count"),
        suspect_count=_optional_int(summary, "suspect_count"),
        ux_conflict_count=len(ux_conflicts) if isinstance(ux_conflicts, list) else None,
        log_coverage_conflict_count=(
            len(log_coverage_conflicts) if isinstance(log_coverage_conflicts, list) else None
        ),
        coverage_status_counts=_coverage_status_counts(summary),
        has_report_md=(report_dir / "report.md").is_file(),
        has_summary_json=(report_dir / "summary.json").is_file(),
        has_slow_events_csv=(report_dir / "slow_events.csv").is_file(),
        has_scenario_timeline_csv=(report_dir / "scenario_timeline.csv").is_file(),
        has_questions_answers_json=(report_dir / "questions_answers.json").is_file(),
    )


def _format_optional(value: int | None, *, missing: str = "n/a") -> str:
    if value is None:
        return missing
    return str(value)


def _format_coverage_counts(counts: dict[str, int] | None) -> str:
    if not counts:
        return "n/a"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def _format_file_flag(present: bool) -> str:
    return "yes" if present else "no"


def format_latest_report(entry: ReportIndexEntry) -> str:
    """Format operator summary for the newest report bundle."""
    report_md = entry.report_dir / "report.md"
    summary_json = entry.report_dir / "summary.json"

    lines = [
        "Performance Agent — latest report bundle",
        "=" * 42,
        f"Report directory: {entry.report_dir}",
        f"Mode:             {entry.mode or 'n/a'}",
        f"Source log:       {entry.source_log or 'n/a'}",
        f"Total events:     {_format_optional(entry.total_events)}",
        f"Malformed lines:  {_format_optional(entry.malformed_lines)}",
        f"Slow events:      {_format_optional(entry.slow_event_count)}",
        f"Suspects:         {_format_optional(entry.suspect_count)}",
        f"UX conflicts:     {_format_optional(entry.ux_conflict_count)}",
        f"Log coverage conflicts: {_format_optional(entry.log_coverage_conflict_count)}",
        f"Scenario coverage: {_format_coverage_counts(entry.coverage_status_counts)}",
        "",
        "Bundle files:",
        f"  report.md              {_format_file_flag(entry.has_report_md)}",
        f"  summary.json           {_format_file_flag(entry.has_summary_json)}",
        f"  slow_events.csv        {_format_file_flag(entry.has_slow_events_csv)}",
        f"  scenario_timeline.csv  {_format_file_flag(entry.has_scenario_timeline_csv)}",
        f"  questions_answers.json {_format_file_flag(entry.has_questions_answers_json)}",
        "",
        "Paths:",
        f"  report.md:    {report_md}",
        f"  summary.json: {summary_json}",
        "",
        "For ChatGPT review, paste the COPY FOR CHATGPT block from report.md.",
    ]
    return "\n".join(lines)


def format_report_list(entries: list[ReportIndexEntry]) -> str:
    """Format a compact table of report bundles."""
    if not entries:
        return (
            "No performance report bundles found.\n"
            "Tip: run --parse-only, --manual, or --run to generate a bundle."
        )

    lines = [
        "Performance Agent — report bundles (newest first)",
        "=" * 49,
    ]
    for index, entry in enumerate(entries, start=1):
        lines.append(
            f"{index}. {entry.dir_name}  "
            f"mode={entry.mode or 'n/a'}  "
            f"slow={_format_optional(entry.slow_event_count)}  "
            f"suspects={_format_optional(entry.suspect_count)}  "
            f"report.md={_format_file_flag(entry.has_report_md)}  "
            f"summary.json={_format_file_flag(entry.has_summary_json)}"
        )
    return "\n".join(lines)


def format_no_reports_message(*, output_root: Path, profile_id: str) -> str:
    return (
        "No performance report bundles found.\n"
        f"  Searched: {output_root.resolve()}\n"
        f"  Profile:  {profile_id}\n"
        "  Tip: run --parse-only, --manual, or --run to generate a bundle."
    )


def _strip_trailing_separator(block: str) -> str:
    """Remove a trailing ``---`` line from an extracted copy block."""
    trimmed = block.rstrip()
    while trimmed:
        lines = trimmed.splitlines()
        if lines and lines[-1].strip() == "---":
            trimmed = "\n".join(lines[:-1]).rstrip()
            continue
        return trimmed
    return trimmed


def extract_copy_for_chatgpt_text(text: str) -> str:
    """Return the COPY FOR CHATGPT block from *text*, ready to paste into ChatGPT."""
    start = text.find(_COPY_FOR_CHATGPT_HEADING)
    if start < 0:
        raise CopyBlockNotFoundError(f"Missing {_COPY_FOR_CHATGPT_HEADING!r} heading")

    after_heading = start + len(_COPY_FOR_CHATGPT_HEADING)
    tech_idx = text.find(_TECHNICAL_REPORT_MARKER, after_heading)
    if tech_idx >= 0:
        block = text[start:tech_idx]
    else:
        block = text[start:]

    block = _strip_trailing_separator(block.rstrip())
    if not block.strip():
        raise CopyBlockNotFoundError("COPY FOR CHATGPT block is empty")

    return block


def extract_copy_for_chatgpt(report_md: Path) -> str:
    """Load *report_md* and return its COPY FOR CHATGPT block."""
    try:
        text = report_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise CopyBlockNotFoundError(f"Cannot read {report_md}: {exc}") from exc
    return extract_copy_for_chatgpt_text(text)


def _scenario_counts_from_summary(
    summary: dict[str, Any],
) -> tuple[int | None, int | None, int | None]:
    """Return ``(completed, skipped, total)`` from ``ux_answers.scenarios``."""
    ux = summary.get("ux_answers")
    if not isinstance(ux, dict):
        return None, None, None
    scenarios = ux.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return None, None, None

    completed = sum(
        1 for item in scenarios if isinstance(item, dict) and item.get("completed") is True
    )
    skipped = sum(
        1 for item in scenarios if isinstance(item, dict) and item.get("skipped") is True
    )
    return completed, skipped, len(scenarios)


def _max_health_status(current: HealthStatus, candidate: HealthStatus) -> HealthStatus:
    if _HEALTH_SEVERITY[candidate] > _HEALTH_SEVERITY[current]:
        return candidate
    return current


def _build_health_recommendation(
    status: HealthStatus,
    *,
    completed: int | None,
    skipped: int | None,
    total: int | None,
) -> str:
    if status == "BROKEN":
        return (
            "BROKEN — bundle is missing key files or summary data.\n"
            "Regenerate with:\n"
            "python -m tools.performance_agent --run"
        )
    if status == "NEEDS_RERUN":
        if total is not None and completed is not None:
            detail = f"only {completed}/{total} scenarios completed"
            if skipped is not None and skipped > 0:
                detail += f" ({skipped} skipped)"
            return (
                f"NEEDS_RERUN — {detail}.\n"
                "Run:\n"
                "python -m tools.performance_agent --run"
            )
        return (
            "NEEDS_RERUN — bundle has insufficient log data for analysis.\n"
            "Run:\n"
            "python -m tools.performance_agent --run"
        )
    if status == "PARTIAL":
        if (
            total is not None
            and completed is not None
            and completed >= total
            and (skipped is None or skipped == 0)
        ):
            return (
                "PARTIAL — report is reviewable with caveat (all scenarios completed).\n"
                "For review:\n"
                "python -m tools.performance_agent --prepare-chatgpt-latest\n"
                "For a full audit:\n"
                "python -m tools.performance_agent --run"
            )
        return (
            "PARTIAL — report can be reviewed, but scenario coverage is weak.\n"
            "For a full audit, run:\n"
            "python -m tools.performance_agent --run"
        )
    return (
        "READY — bundle looks good for ChatGPT analysis.\n"
        "Use:\n"
        "python -m tools.performance_agent --chatgpt-latest\n"
        "python -m tools.performance_agent --chatgpt-latest --clip"
    )


def evaluate_report_health(entry: ReportIndexEntry) -> ReportHealth:
    """Evaluate whether a report bundle is ready for ChatGPT analysis."""
    summary = load_summary_json(entry.report_dir)
    completed, skipped, total = _scenario_counts_from_summary(summary)

    if not entry.has_summary_json or not entry.has_report_md:
        status: HealthStatus = "BROKEN"
        recommendation = _build_health_recommendation(
            status, completed=completed, skipped=skipped, total=total
        )
        return ReportHealth(
            entry=entry,
            status=status,
            completed_scenarios=completed,
            skipped_scenarios=skipped,
            total_scenarios=total,
            recommendation=recommendation,
        )

    status = "READY"
    events = entry.total_events

    if events is not None and events == 0:
        status = "NEEDS_RERUN"

    if total is not None and total > 1:
        completed_val = completed or 0
        skipped_val = skipped or 0
        if completed_val == 0:
            status = _max_health_status(status, "NEEDS_RERUN")
        elif skipped_val >= completed_val:
            if events is not None and events > 0:
                status = _max_health_status(status, "PARTIAL")
            else:
                status = _max_health_status(status, "NEEDS_RERUN")

    if entry.malformed_lines is not None and entry.malformed_lines > 0:
        status = _max_health_status(status, "PARTIAL")

    log_conflicts = entry.log_coverage_conflict_count or 0
    if log_conflicts > 0:
        if (
            total is not None
            and total > 1
            and skipped is not None
            and completed is not None
            and skipped >= completed
            and (events is None or events == 0)
        ):
            status = _max_health_status(status, "NEEDS_RERUN")
        else:
            status = _max_health_status(status, "PARTIAL")

    counts = entry.coverage_status_counts or {}
    problem_statuses = ("missing_expected_events", "no_events_in_window")
    if any(counts.get(name, 0) > 0 for name in problem_statuses):
        status = _max_health_status(status, "PARTIAL")

    if status == "READY" and (events is None or events == 0):
        status = "NEEDS_RERUN"

    recommendation = _build_health_recommendation(
        status, completed=completed, skipped=skipped, total=total
    )
    return ReportHealth(
        entry=entry,
        status=status,
        completed_scenarios=completed,
        skipped_scenarios=skipped,
        total_scenarios=total,
        recommendation=recommendation,
    )


def format_prepare_chatgpt_prep(status: HealthStatus) -> str:
    """Format operator stdout for ``--prepare-chatgpt-latest`` after a successful copy."""
    lines = [
        "Performance Agent — ChatGPT review prep",
        "=" * 39,
        f"Status: {status}",
    ]
    if status == "PARTIAL":
        lines.append(
            "WARNING: Report is reviewable with caveat — check coverage notes before broad conclusions."
        )
    lines.extend(
        [
            "COPY FOR CHATGPT block copied to clipboard.",
            "",
            "Paste it into ChatGPT with Ctrl+V.",
        ]
    )
    return "\n".join(lines)


def format_doctor_status(
    *,
    version: str,
    profile_id: str,
    output_root: Path,
    output_root_exists: bool,
    report_bundle_count: int,
    latest_bundle_name: str | None,
    latest_health_status: HealthStatus | None,
    default_log_exists: bool,
    clipboard_support: str,
) -> str:
    """Format read-only operator status for ``--doctor``."""
    latest_bundle = latest_bundle_name or "none"
    latest_health = latest_health_status or "n/a"
    lines = [
        "Performance Agent — doctor",
        "=" * 26,
        f"Version: {version}",
        f"Profile: {profile_id}",
        f"Output root: {output_root.resolve()}",
        f"Output root exists: {_format_file_flag(output_root_exists)}",
        f"Report bundles: {report_bundle_count}",
        f"Latest bundle: {latest_bundle}",
        f"Latest health: {latest_health}",
        f"Default log exists: {_format_file_flag(default_log_exists)}",
        f"Clipboard: {clipboard_support}",
        "",
        "Recommended workflow:",
        "1. python -m tools.performance_agent --run",
        "2. python -m tools.performance_agent --health-latest",
        "3. python -m tools.performance_agent --prepare-chatgpt-latest",
    ]
    return "\n".join(lines)


def format_open_latest_paths(report_dir: Path) -> str:
    """Format paths printed by ``--open-latest``."""
    report_md = report_dir / "report.md"
    summary_json = report_dir / "summary.json"
    return "\n".join(
        [
            "Performance Agent — open latest report",
            "=" * 38,
            f"Report directory: {report_dir.resolve()}",
            f"report.md:        {report_md.resolve()}",
            f"summary.json:     {summary_json.resolve()}",
        ]
    )


def format_report_health(health: ReportHealth) -> str:
    """Format operator health summary for a report bundle."""
    entry = health.entry
    lines = [
        "Performance Agent — latest bundle health",
        "=" * 40,
        f"Status: {health.status}",
        "",
        f"Report directory: {entry.report_dir}",
        f"Mode:             {entry.mode or 'n/a'}",
        f"Total events:     {_format_optional(entry.total_events)}",
        f"Malformed lines:  {_format_optional(entry.malformed_lines)}",
        f"Slow events:      {_format_optional(entry.slow_event_count)}",
        f"Suspects:         {_format_optional(entry.suspect_count)}",
        f"UX conflicts:     {_format_optional(entry.ux_conflict_count)}",
        f"Log coverage conflicts: {_format_optional(entry.log_coverage_conflict_count)}",
        f"Scenario coverage: {_format_coverage_counts(entry.coverage_status_counts)}",
    ]

    if health.total_scenarios is not None:
        lines.append(
            f"Completed scenarios: {health.completed_scenarios or 0}/{health.total_scenarios}"
        )
        lines.append(
            f"Skipped scenarios:   {health.skipped_scenarios or 0}/{health.total_scenarios}"
        )

    lines.extend(
        [
            "",
            "Bundle files:",
            f"  report.md              {_format_file_flag(entry.has_report_md)}",
            f"  summary.json           {_format_file_flag(entry.has_summary_json)}",
            f"  slow_events.csv        {_format_file_flag(entry.has_slow_events_csv)}",
            f"  scenario_timeline.csv  {_format_file_flag(entry.has_scenario_timeline_csv)}",
            f"  questions_answers.json {_format_file_flag(entry.has_questions_answers_json)}",
            "",
            "Recommendation:",
            health.recommendation,
        ]
    )
    return "\n".join(lines)
