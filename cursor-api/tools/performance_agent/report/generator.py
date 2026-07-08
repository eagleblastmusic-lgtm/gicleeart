"""Report bundle generator."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.performance_agent.collector import CollectionResult
from tools.performance_agent.models import ManualSession
from tools.performance_agent.parser.giclee_studio import ParseResult
from tools.performance_agent.profiles import AppProfile
from tools.performance_agent.parser.metrics import (
    ScenarioLogCoverage,
    compute_scenario_log_coverage,
)
from tools.performance_agent.report.conflicts import (
    LogCoverageConflict,
    UxConflict,
    detect_log_coverage_conflicts,
    detect_ux_conflicts,
)
from tools.performance_agent.timeutil import utc_now, utc_now_iso


def make_report_dir(profile: AppProfile) -> Path:
    stamp = utc_now().strftime("%Y%m%d-%H%M%S")
    return profile.resolve_output_root() / f"{stamp}_{profile.id}"


def _scenario_titles(profile: AppProfile) -> dict[str, str]:
    return {scenario.id: scenario.display_title for scenario in profile.manual_scenarios}


def _scenario_label(
    scenario_id: str,
    titles: dict[str, str],
    *,
    fallback: str = "",
) -> str:
    title = titles.get(scenario_id) or fallback
    if title:
        return f"{scenario_id} — {title}"
    return scenario_id


@dataclass(frozen=True)
class ReportBundle:
    report_dir: Path
    report_md: Path
    summary_json: Path
    slow_events_csv: Path
    scenario_timeline_csv: Path
    questions_answers_json: Path
    events_jsonl: Path | None
    raw_log: Path | None
    agent_events_jsonl: Path | None = None


def _write_slow_events_csv(path: Path, parse: ParseResult | None) -> None:
    fieldnames = [
        "line_no",
        "ts",
        "event",
        "ms",
        "ms_field",
        "severity",
        "element_id",
        "element_type",
        "stage",
        "module",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if parse is not None:
            for row in parse.metrics.slow_events:
                writer.writerow(row.to_dict())


def _write_scenario_timeline_csv(
    path: Path,
    session: ManualSession | None,
    coverage_by_id: dict[str, str] | None = None,
) -> None:
    fieldnames = [
        "scenario_id",
        "display_title",
        "scenario_name",
        "start_ts",
        "end_ts",
        "duration_ms",
        "completed",
        "skipped",
        "log_coverage_status",
        "smoothness_score",
        "main_complaint",
        "note",
    ]
    coverage_by_id = coverage_by_id or {}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        if session is not None:
            for run in session.scenarios:
                writer.writerow(
                    run.to_timeline_row(
                        log_coverage_status=coverage_by_id.get(run.scenario_id, ""),
                    )
                )
        else:
            writer.writerow(
                {
                    "scenario_id": "",
                    "display_title": "",
                    "scenario_name": "",
                    "start_ts": "",
                    "end_ts": "",
                    "duration_ms": "",
                    "completed": False,
                    "skipped": False,
                    "log_coverage_status": "",
                    "smoothness_score": "",
                    "main_complaint": "",
                    "note": "PA-1A parse-only — no manual session",
                }
            )


def _write_questions_answers_json(path: Path, session: ManualSession | None) -> None:
    if session is not None:
        payload = session.to_questions_answers_dict()
    else:
        payload = {
            "status": "parse-only",
            "note": "PA-1A parse-only — UX questionnaire not collected",
            "scenarios": [],
        }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _format_top_slow(parse: ParseResult | None, limit: int = 10) -> str:
    if parse is None:
        return "- (log missing — no metrics)"
    lines: list[str] = []
    for row in parse.metrics.slow_events[:limit]:
        lines.append(
            f"- L{row.line_no} `{row.event}` {row.ms_field}={row.ms:.1f}ms [{row.severity}]"
        )
    return "\n".join(lines) if lines else "- (none above warning threshold)"


def _format_suspects(parse: ParseResult | None, limit: int = 10) -> str:
    if parse is None:
        return "- (log missing — no suspects)"
    lines: list[str] = []
    for suspect in parse.heuristics.suspects[:limit]:
        ms_part = f" ({suspect.ms:.1f}ms)" if suspect.ms is not None else ""
        phase_part = f" [{suspect.phase}]" if suspect.phase else ""
        lines.append(
            f"- [{suspect.priority}]{phase_part} **{suspect.id}** L{suspect.line_no}: "
            f"`{suspect.event}` — {suspect.message}{ms_part}"
        )
    return "\n".join(lines) if lines else "- (no UX suspects detected)"


def _format_readiness(parse: ParseResult | None) -> str:
    if parse is None or not parse.metrics.readiness_timeline:
        return "- (no readiness milestones detected)"
    lines: list[str] = []
    for entry in parse.metrics.readiness_timeline:
        ms_bits: list[str] = []
        if entry.elapsed_ms is not None:
            ms_bits.append(f"elapsed={entry.elapsed_ms:.1f}ms")
        if entry.since_enter_ms is not None:
            ms_bits.append(f"since_enter={entry.since_enter_ms:.1f}ms")
        ms_text = f" ({', '.join(ms_bits)})" if ms_bits else ""
        lines.append(f"- **{entry.key}** L{entry.line_no} `{entry.event}`{ms_text}")
    return "\n".join(lines)


def _format_details_analysis(parse: ParseResult | None) -> str:
    if parse is None:
        return "- (log missing)"
    events = parse.heuristics.details_cta_events
    if not events:
        return "- (no details CTA events detected)"
    lines: list[str] = []
    for item in events[:20]:
        ms = item.get("since_request_ms")
        ms_text = f" since_request={ms}ms" if ms is not None else ""
        severity = item.get("severity")
        sev_text = f" [{severity}]" if severity else ""
        lines.append(f"- L{item['line_no']} `{item['event']}`{ms_text}{sev_text}")
    if len(events) > 20:
        lines.append(f"- … and {len(events) - 20} more details events")
    return "\n".join(lines)


def _format_manual_ux_summary(
    session: ManualSession | None,
    titles: dict[str, str],
) -> str:
    if session is None or not session.scenarios:
        return "- (no manual UX data)"
    header = (
        "| scenario | smoothness | main_complaint | skeletons | layout_shift | "
        "sequential_popin | freeze | note |\n"
        "|----------|------------|----------------|-----------|--------------|"
        "------------------|--------|------|\n"
    )
    rows: list[str] = []
    for run in session.scenarios:
        label = _scenario_label(run.scenario_id, titles, fallback=run.scenario_name)
        if run.skipped:
            rows.append(
                f"| {label} | — | skipped | — | — | — | — | — |"
            )
            continue
        answers = run.answers
        rows.append(
            "| {scenario} | {smooth} | {complaint} | {skel} | {layout} | {seq} | {freeze} | {note} |".format(
                scenario=label,
                smooth=answers.get("smoothness_score", "—"),
                complaint=answers.get("main_complaint", "—"),
                skel=answers.get("skeletons_seen", "—"),
                layout=answers.get("layout_shift", "—"),
                seq=answers.get("sequential_popin", "—"),
                freeze=answers.get("freeze_seen", "—"),
                note=(answers.get("note", "") or "—").replace("|", "/"),
            )
        )
    return header + "\n".join(rows)


def _format_ux_conflicts(
    conflicts: list[UxConflict],
    titles: dict[str, str],
) -> str:
    if not conflicts:
        return "- (no metric/UX conflicts detected)"
    lines: list[str] = []
    for conflict in conflicts:
        label = _scenario_label(conflict.scenario_id, titles)
        lines.append(
            f"- **{conflict.id}** scenario=`{label}` "
            f"score={conflict.smoothness_score} major_slow={conflict.major_slow_count} — "
            f"{conflict.evidence}"
        )
    return "\n".join(lines)


def _format_log_coverage_conflicts(
    conflicts: list[LogCoverageConflict],
    titles: dict[str, str],
) -> str:
    if not conflicts:
        return "- (all completed scenarios confirmed by performance log, or no session)"
    lines: list[str] = []
    for conflict in conflicts:
        label = _scenario_label(conflict.scenario_id, titles)
        lines.append(
            f"- **{conflict.id}** scenario=`{label}` "
            f"status={conflict.coverage_status} — {conflict.message}. {conflict.evidence}"
        )
    return "\n".join(lines)


def _format_scenario_log_coverage(
    coverage: list[ScenarioLogCoverage],
    titles: dict[str, str],
    *,
    session: ManualSession | None = None,
) -> str:
    if not coverage:
        return "- (no scenario timeline — parse-only or empty session)"
    header = (
        "| scenario | status | events | expected_match | matched_patterns | expected |\n"
        "|----------|--------|--------|----------------|------------------|----------|\n"
    )
    rows: list[str] = []
    for entry in coverage:
        label = _scenario_label(entry.scenario_id, titles)
        matched = ", ".join(entry.matched_patterns) if entry.matched_patterns else "—"
        expected = ", ".join(entry.expected) if entry.expected else "—"
        rows.append(
            f"| {label} | {entry.status} | {entry.event_count} | "
            f"{entry.expected_match_count} | {matched} | {expected} |"
        )
    note = (
        "\n\n_Note: missing expected events indicates the scenario was not confirmed in the "
        "performance log (session/data quality), not necessarily a GicleeApp runtime regression._"
    )
    if session is not None and session.session_mode == "run":
        dashboard = next((entry for entry in coverage if entry.scenario_id == "dashboard_cold"), None)
        if dashboard is not None and dashboard.status in {
            "missing_expected_events",
            "no_events_in_window",
            "early_event_seen",
        }:
            if dashboard.status == "early_event_seen":
                note += (
                    "\n\n_Note: `dashboard_cold` events were seen before the scenario window "
                    "(startup / intro timing) — classified as early_event_seen._"
                )
            else:
                note += (
                    "\n\n_Warning: `dashboard_cold` may be pre-session in `--run` mode — dashboard "
                    "events may have occurred before the wizard started this scenario._"
                )
    return header + "\n".join(rows) + note


def _build_report_md(
    *,
    profile: AppProfile,
    collection: CollectionResult | None,
    parse: ParseResult | None,
    report_dir: Path,
    session: ManualSession | None,
    ux_conflicts: list[UxConflict],
    log_coverage: list[ScenarioLogCoverage],
    log_coverage_conflicts: list[LogCoverageConflict],
) -> str:
    now = utc_now_iso()
    mode = session.session_mode if session is not None else "parse-only"
    log_missing = session.log_missing if session else False

    titles = _scenario_titles(profile)
    top_slow = _format_top_slow(parse)
    top_suspects = _format_suspects(parse)
    readiness = _format_readiness(parse)
    details = _format_details_analysis(parse)
    manual_ux = _format_manual_ux_summary(session, titles)
    conflicts_text = _format_ux_conflicts(ux_conflicts, titles)
    log_coverage_text = _format_scenario_log_coverage(log_coverage, titles, session=session)
    log_coverage_conflicts_text = _format_log_coverage_conflicts(log_coverage_conflicts, titles)

    source_log = str(collection.source_log) if collection else (
        str(session.log_path) if session else profile.resolve_log_path(None)
    )

    prefix_lines = ""
    if parse is not None:
        prefix_lines = "\n".join(
            f"- {prefix}: {count}"
            for prefix, count in parse.metrics.event_counts_by_prefix.items()
            if count
        )

    log_warning = ""
    if log_missing:
        log_warning = "\n- **WARNING:** performance log missing — metrics section incomplete\n"

    session_status = ""
    studio_meta = ""
    lifecycle_meta = ""
    if session is not None:
        session_status = f"\n- Session status: {session.status}\n"
        if session.studio_pid is not None:
            studio_meta = (
                f"\n- Studio PID: {session.studio_pid}"
                f"\n- Studio left running: {session.studio_left_running}"
                f"\n- Studio start failed: {session.studio_start_failed}\n"
            )
        if session.log_lifecycle:
            lc = session.log_lifecycle
            lifecycle_meta = (
                f"\n- Log lifecycle: {lc.get('mode')}"
                f"\n- Archived to: {lc.get('archived_to') or '—'}\n"
            )

    parsed_events = parse.metrics.total_events if parse else 0
    malformed = parse.metrics.malformed_lines if parse else 0
    slow_count = len(parse.metrics.slow_events) if parse else 0
    suspect_count = len(parse.heuristics.suspects) if parse else 0
    budgets = parse.budgets if parse else profile.budgets

    copy_block = f"""## COPY FOR CHATGPT

Paste this block into ChatGPT (Performance Analyst mode).

### Context
- App / profile: {profile.display_name} (`{profile.id}`)
- Generated: {now}
- Mode: {mode}
- Source log: `{source_log}`
- Report bundle: `{report_dir}`{log_warning}{session_status}{studio_meta}{lifecycle_meta}

### Run summary
- Parsed events: {parsed_events}
- Malformed lines: {malformed}
- Slow events (>= {budgets.slow_event_warning_ms}ms): {slow_count}
- UX suspects: {suspect_count}

### Manual UX Summary
{manual_ux}

### Scenario Log Coverage
{log_coverage_text}

### Scenario log / session data quality
{log_coverage_conflicts_text}

### Metric / UX Conflicts
{conflicts_text}

### Top 10 slow events
{top_slow}

### Top UX suspects
{top_suspects}

### GICLÉE FRAME / readiness timeline
{readiness}

### Details CTA analysis
{details}

### What I need ChatGPT to analyze
1. Which suspects are true UX problems vs expected deferred work?
2. Do manual UX answers conflict with log metrics?
3. Are reveal → post-reveal work patterns causing visible layout shift?
4. Is details on-demand behaving correctly (no full-auto regression)?
5. What is the single safest P0 fix to try next?

---
"""

    technical = f"""# Performance Audit Report — {profile.display_name}

- Profile: `{profile.id}`
- Generated: {now}
- Mode: {mode}

## Source

| Field | Value |
|-------|-------|
| Log path | `{source_log}` |
| Log missing | {log_missing} |
| File size | {collection.file_size_bytes if collection else 0} bytes |
| Line count | {collection.line_count if collection else 0} |
| Parsed events | {parsed_events} |
| Malformed lines | {malformed} |

## Manual session

| Field | Value |
|-------|-------|
| Status | {session.status if session else "n/a"} |
| Scenarios recorded | {len(session.scenarios) if session else 0} |
| Completed | {len(session.completed_scenarios()) if session else 0} |

## Event counts by prefix

{prefix_lines or "- (none)"}

## Slow events

Total slow events: **{slow_count}**

See `slow_events.csv` for full list.

## UX suspects

Total suspects: **{suspect_count}**

{top_suspects}

## Manual UX Summary

{manual_ux}

## Scenario Log Coverage

{log_coverage_text}

## Scenario log / session data quality

{log_coverage_conflicts_text}

## Metric / UX Conflicts

{conflicts_text}

## Readiness timeline

{readiness}

## Details CTA

{details}

## Budgets

- slow_event_warning_ms: {budgets.slow_event_warning_ms}
- slow_event_major_ms: {budgets.slow_event_major_ms}
- details_cta_warning_ms: {budgets.details_cta_warning_ms}
- details_cta_major_ms: {budgets.details_cta_major_ms}

## Bundle files

- `summary.json`
- `slow_events.csv`
- `scenario_timeline.csv`
- `questions_answers.json`
- `agent_events.jsonl` (manual mode)
- `events.jsonl`
- `raw/studio_perf.log`
"""

    return copy_block + "\n" + technical


def generate_report(
    *,
    profile: AppProfile,
    collection: CollectionResult | None,
    parse: ParseResult | None,
    report_dir: Path | None = None,
    session: ManualSession | None = None,
) -> ReportBundle:
    out_dir = report_dir or (session.report_dir if session else make_report_dir(profile))
    out_dir.mkdir(parents=True, exist_ok=True)

    ux_conflicts = detect_ux_conflicts(session, parse) if session else []

    log_coverage: list[ScenarioLogCoverage] = []
    log_coverage_conflicts: list[LogCoverageConflict] = []
    if session is not None and parse is not None:
        log_coverage = compute_scenario_log_coverage(
            session.scenarios,
            profile.scenario_by_id(),
            parse.events,
        )
        log_coverage_conflicts = detect_log_coverage_conflicts(log_coverage)
    coverage_by_id = {entry.scenario_id: entry.status for entry in log_coverage}

    report_md = out_dir / "report.md"
    summary_json = out_dir / "summary.json"
    slow_events_csv = out_dir / "slow_events.csv"
    scenario_timeline_csv = out_dir / "scenario_timeline.csv"
    questions_answers_json = out_dir / "questions_answers.json"
    agent_events_jsonl = out_dir / "agent_events.jsonl" if session else None

    report_md.write_text(
        _build_report_md(
            profile=profile,
            collection=collection,
            parse=parse,
            report_dir=out_dir,
            session=session,
            ux_conflicts=ux_conflicts,
            log_coverage=log_coverage,
            log_coverage_conflicts=log_coverage_conflicts,
        ),
        encoding="utf-8",
    )

    summary: dict[str, Any] = {
        "profile_id": profile.id,
        "mode": session.session_mode if session else "parse-only",
        "report_dir": str(out_dir),
        "log_missing": session.log_missing if session else False,
    }

    if parse is not None and collection is not None:
        summary.update(
            parse.to_summary_dict(
                profile_id=profile.id,
                source_log=collection.source_log,
                report_dir=out_dir,
            )
        )
        summary["collection"] = {
            "file_size_bytes": collection.file_size_bytes,
            "line_count": collection.line_count,
        }
    else:
        summary.update(
            {
                "source_log": str(session.log_path) if session else "",
                "total_events": 0,
                "malformed_lines": 0,
                "slow_event_count": 0,
                "suspect_count": 0,
            }
        )

    if session is not None:
        summary["ux_answers"] = session.to_questions_answers_dict()
        summary["session_status"] = session.status
        summary["ux_conflicts"] = [c.to_dict() for c in ux_conflicts]
        if log_coverage:
            summary["scenario_log_coverage"] = [entry.to_dict() for entry in log_coverage]
        if log_coverage_conflicts:
            summary["log_coverage_conflicts"] = [c.to_dict() for c in log_coverage_conflicts]
        if session.log_lifecycle:
            summary["log_lifecycle"] = session.log_lifecycle
        if session.session_mode == "run":
            summary["studio"] = {
                "pid": session.studio_pid,
                "left_running": session.studio_left_running,
                "start_failed": session.studio_start_failed,
            }

    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _write_slow_events_csv(slow_events_csv, parse)
    _write_scenario_timeline_csv(scenario_timeline_csv, session, coverage_by_id)
    _write_questions_answers_json(questions_answers_json, session)

    return ReportBundle(
        report_dir=out_dir,
        report_md=report_md,
        summary_json=summary_json,
        slow_events_csv=slow_events_csv,
        scenario_timeline_csv=scenario_timeline_csv,
        questions_answers_json=questions_answers_json,
        events_jsonl=collection.events_jsonl if collection else None,
        raw_log=collection.raw_log if collection else None,
        agent_events_jsonl=agent_events_jsonl if agent_events_jsonl and agent_events_jsonl.exists() else None,
    )
