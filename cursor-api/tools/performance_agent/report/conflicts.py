"""Metric vs UX conflict detection for manual sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.performance_agent.models import ManualSession
from tools.performance_agent.parser.giclee_studio import ParseResult
from tools.performance_agent.parser.metrics import ScenarioLogCoverage, SlowEventRow
from tools.performance_agent.timeutil import parse_iso_ts


@dataclass
class UxConflict:
    id: str
    scenario_id: str
    message: str
    smoothness_score: int | None
    major_slow_count: int
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "message": self.message,
            "smoothness_score": self.smoothness_score,
            "major_slow_count": self.major_slow_count,
            "evidence": self.evidence,
        }


@dataclass
class LogCoverageConflict:
    id: str
    scenario_id: str
    message: str
    coverage_status: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "message": self.message,
            "coverage_status": self.coverage_status,
            "evidence": self.evidence,
        }


def _event_in_window(ts: str | None, start_ts: str | None, end_ts: str | None) -> bool:
    event_dt = parse_iso_ts(ts)
    start_dt = parse_iso_ts(start_ts)
    end_dt = parse_iso_ts(end_ts)
    if event_dt is None or start_dt is None or end_dt is None:
        return False
    return start_dt <= event_dt <= end_dt


def slow_events_in_window(
    slow_events: list[SlowEventRow],
    perf_events_ts: dict[int, str | None],
    *,
    start_ts: str | None,
    end_ts: str | None,
) -> list[SlowEventRow]:
    matched: list[SlowEventRow] = []
    for row in slow_events:
        ts = perf_events_ts.get(row.line_no)
        if _event_in_window(ts, start_ts, end_ts):
            matched.append(row)
    return matched


def build_perf_event_ts_index(parse: ParseResult) -> dict[int, str | None]:
    return {event.line_no: event.ts for event in parse.events}


def detect_ux_conflicts(session: ManualSession, parse: ParseResult | None) -> list[UxConflict]:
    if parse is None:
        return []

    ts_index = build_perf_event_ts_index(parse)
    conflicts: list[UxConflict] = []

    for run in session.completed_scenarios():
        if not run.start_ts or not run.end_ts:
            continue

        window_slow = slow_events_in_window(
            parse.metrics.slow_events,
            ts_index,
            start_ts=run.start_ts,
            end_ts=run.end_ts,
        )
        major_count = sum(1 for row in window_slow if row.severity == "major")
        score = run.answers.get("smoothness_score")
        if isinstance(score, str) and score.isdigit():
            score = int(score)
        if not isinstance(score, int):
            score = None

        if score is not None and score <= 2 and major_count == 0:
            conflicts.append(
                UxConflict(
                    id="UX_CONFLICT_LOW_SCORE_WITH_OK_METRICS",
                    scenario_id=run.scenario_id,
                    message="Low smoothness score but no major slow events in scenario window",
                    smoothness_score=score,
                    major_slow_count=major_count,
                    evidence=f"window {run.start_ts} .. {run.end_ts}; slow_in_window={len(window_slow)}",
                )
            )

        if score is not None and score >= 4 and major_count > 0:
            conflicts.append(
                UxConflict(
                    id="TECH_SLOW_BUT_UX_ACCEPTABLE",
                    scenario_id=run.scenario_id,
                    message="High smoothness score despite major slow events in scenario window",
                    smoothness_score=score,
                    major_slow_count=major_count,
                    evidence=f"window {run.start_ts} .. {run.end_ts}; major_slow={major_count}",
                )
            )

    return conflicts


def detect_log_coverage_conflicts(
    coverage: list[ScenarioLogCoverage],
) -> list[LogCoverageConflict]:
    conflicts: list[LogCoverageConflict] = []
    for entry in coverage:
        if entry.status not in {"missing_expected_events", "no_events_in_window"}:
            continue
        conflicts.append(
            LogCoverageConflict(
                id="SCENARIO_LOG_NOT_CONFIRMED",
                scenario_id=entry.scenario_id,
                message=(
                    "Scenario marked completed but performance log does not confirm expected "
                    "events — session/data quality issue, not a GicleeApp runtime regression"
                ),
                coverage_status=entry.status,
                evidence=(
                    f"status={entry.status}; events_in_window={entry.event_count}; "
                    f"expected_match_count={entry.expected_match_count}; "
                    f"expected={entry.expected}; matched={entry.matched_patterns}"
                ),
            )
        )
    return conflicts
