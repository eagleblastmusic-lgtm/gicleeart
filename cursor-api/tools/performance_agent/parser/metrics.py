"""Aggregate metrics from parsed performance events."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal

from tools.performance_agent.models import ScenarioDefinition, ScenarioRun
from tools.performance_agent.parser.jsonl_loader import PerfEvent
from tools.performance_agent.profiles import Budgets
from tools.performance_agent.timeutil import parse_iso_ts

CoverageStatus = Literal[
    "ok",
    "early_event_seen",
    "missing_expected_events",
    "no_events_in_window",
    "skipped",
    "incomplete_timestamps",
    "not_completed",
]

DASHBOARD_PRE_WINDOW_GRACE_S = 120.0


PREFIX_ORDER = (
    "studio.show_view",
    "studio.dashboard",
    "studio.hub",
    "studio.katalog",
    "studio.gicleeframe.details",
    "studio.gicleeframe",
)


@dataclass
class SlowEventRow:
    line_no: int
    ts: str | None
    event: str
    ms: float
    ms_field: str
    severity: str
    element_id: str | None = None
    element_type: str | None = None
    stage: str | None = None
    module: str | None = None

    def to_dict(self) -> dict:
        return {
            "line_no": self.line_no,
            "ts": self.ts,
            "event": self.event,
            "ms": self.ms,
            "ms_field": self.ms_field,
            "severity": self.severity,
            "element_id": self.element_id,
            "element_type": self.element_type,
            "stage": self.stage,
            "module": self.module,
        }


@dataclass
class ReadinessEntry:
    key: str
    event: str
    line_no: int
    ts: str | None
    elapsed_ms: float | None = None
    since_enter_ms: float | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "event": self.event,
            "line_no": self.line_no,
            "ts": self.ts,
            "elapsed_ms": self.elapsed_ms,
            "since_enter_ms": self.since_enter_ms,
        }


READINESS_SPECS: list[tuple[str, str]] = [
    ("dashboard.visible_ready", "studio.dashboard.visual.visible_ready"),
    ("dashboard.full_ready", "studio.dashboard.visual.full_ready"),
    ("hub.real_shell_first_paint", "studio.hub.visual.real_shell_first_paint"),
    ("hub.visible_ready", "studio.hub.visual.visible_ready"),
    ("hub.full_ready", "studio.hub.visual.full_ready"),
    ("gicleeframe.overlay_shown", "studio.gicleeframe.atomic_reveal.overlay_shown"),
    ("gicleeframe.minimal_ready", "studio.gicleeframe.atomic_reveal.minimal_ready"),
    ("gicleeframe.revealed", "studio.gicleeframe.atomic_reveal.revealed"),
    ("gicleeframe.visible_ready", "studio.gicleeframe.visual.visible_ready"),
    ("gicleeframe.full_ready_progressive", "studio.gicleeframe.visual.full_ready_progressive"),
    ("details.shell_applied", "studio.gicleeframe.details_shell.applied"),
    ("details.on_demand_applied", "studio.gicleeframe.details_on_demand.applied"),
    ("details.module_applied", "studio.gicleeframe.details_module.applied"),
]


def _event_prefix(event_name: str) -> str:
    for prefix in PREFIX_ORDER:
        if event_name.startswith(prefix):
            return prefix
    return "other"


DETAILS_SLOW_MARKERS = (
    "details_on_demand.",
    "details_shell.",
    "details_module.",
)

DETAILS_SLOW_ALLOWED_FIELDS = frozenset(
    {
        "elapsed_ms",
        "since_request_ms",
        "since_details_cta_ms",
        "queue_latency_ms",
    }
)


def _is_details_slow_event(event_name: str) -> bool:
    return any(marker in event_name for marker in DETAILS_SLOW_MARKERS)


def _ms_fields(event: PerfEvent) -> list[tuple[str, float]]:
    """Return duration-like ms fields present on the event."""
    pairs: list[tuple[str, float]] = []
    for field_name in (
        "elapsed_ms",
        "since_click_ms",
        "since_request_ms",
        "since_details_cta_ms",
        "queue_latency_ms",
    ):
        value = getattr(event, field_name)
        if value is not None:
            pairs.append((field_name, float(value)))
    return pairs


def _slow_ms_fields(event: PerfEvent) -> list[tuple[str, float]]:
    """Return ms fields used for slow-event classification and ranking."""
    if event.event.endswith(".cancelled"):
        return []
    pairs = _ms_fields(event)
    if not _is_details_slow_event(event.event):
        return pairs
    return [(name, ms) for name, ms in pairs if name in DETAILS_SLOW_ALLOWED_FIELDS]


def _slow_severity(ms: float, budgets: Budgets) -> str | None:
    if ms >= budgets.slow_event_major_ms:
        return "major"
    if ms >= budgets.slow_event_warning_ms:
        return "warning"
    return None


@dataclass
class MetricsResult:
    total_events: int
    malformed_lines: int
    event_counts_by_prefix: dict[str, int] = field(default_factory=dict)
    slow_events: list[SlowEventRow] = field(default_factory=list)
    readiness_timeline: list[ReadinessEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "malformed_lines": self.malformed_lines,
            "event_counts_by_prefix": self.event_counts_by_prefix,
            "slow_event_count": len(self.slow_events),
            "readiness_timeline": [entry.to_dict() for entry in self.readiness_timeline],
        }


def compute_metrics(
    events: list[PerfEvent],
    *,
    malformed_lines: int,
    budgets: Budgets,
) -> MetricsResult:
    prefix_counter: Counter[str] = Counter()
    slow_events: list[SlowEventRow] = []
    readiness_seen: set[str] = set()
    readiness_timeline: list[ReadinessEntry] = []

    readiness_by_event = {event_name: key for key, event_name in READINESS_SPECS}

    for event in events:
        prefix_counter[_event_prefix(event.event)] += 1

        if event.event in readiness_by_event:
            key = readiness_by_event[event.event]
            if key not in readiness_seen:
                readiness_seen.add(key)
                readiness_timeline.append(
                    ReadinessEntry(
                        key=key,
                        event=event.event,
                        line_no=event.line_no,
                        ts=event.ts,
                        elapsed_ms=event.elapsed_ms,
                        since_enter_ms=event.since_enter_ms,
                    )
                )

        for field_name, ms in _slow_ms_fields(event):
            severity = _slow_severity(ms, budgets)
            if severity is None:
                continue
            slow_events.append(
                SlowEventRow(
                    line_no=event.line_no,
                    ts=event.ts,
                    event=event.event,
                    ms=ms,
                    ms_field=field_name,
                    severity=severity,
                    element_id=event.element_id,
                    element_type=event.element_type,
                    stage=event.stage,
                    module=event.module,
                )
            )

    slow_events.sort(key=lambda row: row.ms, reverse=True)

    event_counts = {prefix: prefix_counter.get(prefix, 0) for prefix in PREFIX_ORDER}
    event_counts["other"] = prefix_counter.get("other", 0)

    return MetricsResult(
        total_events=len(events),
        malformed_lines=malformed_lines,
        event_counts_by_prefix=event_counts,
        slow_events=slow_events,
        readiness_timeline=readiness_timeline,
    )


def event_matches_pattern(event: PerfEvent, pattern: str) -> bool:
    needle = pattern.lower()
    haystacks = (
        event.event,
        event.element_type or "",
        event.element_id or "",
        event.stage or "",
        event.module or "",
    )
    if any(needle in value.lower() for value in haystacks if value):
        return True
    if needle == "cache_hit":
        return event.cache_hit is True or event.raw.get("cache_hit") is True
    if needle == "minimal_cache_hit":
        return (
            event.raw.get("minimal_cache_hit") is True
            or "minimal_cache_hit" in event.event.lower()
        )
    return False


def _events_in_extended_window(
    events: list[PerfEvent],
    start_ts: str,
    end_ts: str,
    *,
    tolerance_s: float,
    pre_window_grace_s: float = 0.0,
) -> list[PerfEvent]:
    start_dt = parse_iso_ts(start_ts)
    end_dt = parse_iso_ts(end_ts)
    if start_dt is None or end_dt is None:
        return []
    margin = timedelta(seconds=tolerance_s)
    grace = timedelta(seconds=pre_window_grace_s)
    window_start = start_dt - margin - grace
    window_end = end_dt + margin
    result: list[PerfEvent] = []
    for event in events:
        event_dt = parse_iso_ts(event.ts)
        if event_dt is None:
            continue
        if window_start <= event_dt <= window_end:
            result.append(event)
    return result


def _dashboard_early_event_status(
    run: ScenarioRun,
    expected: list[str],
    events: list[PerfEvent],
    *,
    tolerance_s: float,
) -> ScenarioLogCoverage | None:
    """Detect dashboard events before the scenario window (startup / intro)."""
    if run.scenario_id != "dashboard_cold" or not expected:
        return None

    window_events = _events_in_extended_window(
        events,
        run.start_ts or "",
        run.end_ts or "",
        tolerance_s=tolerance_s,
        pre_window_grace_s=0.0,
    )
    if window_events:
        return None

    extended_events = _events_in_extended_window(
        events,
        run.start_ts or "",
        run.end_ts or "",
        tolerance_s=tolerance_s,
        pre_window_grace_s=DASHBOARD_PRE_WINDOW_GRACE_S,
    )
    matched_patterns: list[str] = []
    for pattern in expected:
        if any(event_matches_pattern(event, pattern) for event in extended_events):
            matched_patterns.append(pattern)

    if not matched_patterns:
        return None

    expected_match_count = sum(
        1
        for event in extended_events
        if any(event_matches_pattern(event, pattern) for pattern in expected)
    )
    return ScenarioLogCoverage(
        scenario_id=run.scenario_id,
        event_count=len(extended_events),
        expected_match_count=expected_match_count,
        status="early_event_seen",
        expected=expected,
        matched_patterns=matched_patterns,
    )


@dataclass
class ScenarioLogCoverage:
    scenario_id: str
    event_count: int
    expected_match_count: int
    status: CoverageStatus
    expected: list[str]
    matched_patterns: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "event_count": self.event_count,
            "expected_match_count": self.expected_match_count,
            "status": self.status,
            "expected": self.expected,
            "matched_patterns": self.matched_patterns,
        }


def compute_scenario_log_coverage(
    runs: list[ScenarioRun],
    scenarios: dict[str, ScenarioDefinition],
    events: list[PerfEvent],
    *,
    tolerance_s: float = 2.0,
) -> list[ScenarioLogCoverage]:
    results: list[ScenarioLogCoverage] = []

    for run in runs:
        definition = scenarios.get(run.scenario_id)
        expected = list(definition.expected_event_patterns) if definition else []

        if run.skipped:
            results.append(
                ScenarioLogCoverage(
                    scenario_id=run.scenario_id,
                    event_count=0,
                    expected_match_count=0,
                    status="skipped",
                    expected=expected,
                )
            )
            continue

        if not run.completed:
            results.append(
                ScenarioLogCoverage(
                    scenario_id=run.scenario_id,
                    event_count=0,
                    expected_match_count=0,
                    status="not_completed",
                    expected=expected,
                )
            )
            continue

        if not run.start_ts or not run.end_ts:
            results.append(
                ScenarioLogCoverage(
                    scenario_id=run.scenario_id,
                    event_count=0,
                    expected_match_count=0,
                    status="incomplete_timestamps",
                    expected=expected,
                )
            )
            continue

        window_events = _events_in_extended_window(
            events,
            run.start_ts,
            run.end_ts,
            tolerance_s=tolerance_s,
        )
        event_count = len(window_events)

        matched_patterns: list[str] = []
        expected_match_count = 0
        if expected:
            for pattern in expected:
                if any(event_matches_pattern(event, pattern) for event in window_events):
                    matched_patterns.append(pattern)
            expected_match_count = sum(
                1
                for event in window_events
                if any(event_matches_pattern(event, pattern) for pattern in expected)
            )
        else:
            expected_match_count = event_count

        if not expected:
            status: CoverageStatus = "ok" if event_count > 0 else "no_events_in_window"
        elif event_count == 0:
            early = _dashboard_early_event_status(
                run,
                expected,
                events,
                tolerance_s=tolerance_s,
            )
            if early is not None:
                results.append(early)
                continue
            status = "no_events_in_window"
        elif matched_patterns:
            status = "ok"
        else:
            status = "missing_expected_events"

        results.append(
            ScenarioLogCoverage(
                scenario_id=run.scenario_id,
                event_count=event_count,
                expected_match_count=expected_match_count,
                status=status,
                expected=expected,
                matched_patterns=matched_patterns,
            )
        )

    return results
