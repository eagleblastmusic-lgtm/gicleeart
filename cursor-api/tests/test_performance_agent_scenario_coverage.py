from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.parser.jsonl_loader import PerfEvent
from tools.performance_agent.parser.metrics import (
    compute_scenario_log_coverage,
    event_matches_pattern,
)
from tools.performance_agent.models import ScenarioRun
from tools.performance_agent.profiles import get_profile


def test_event_matches_pattern_cache_and_media() -> None:
    cache_event = PerfEvent.from_raw(1, {"event": "studio.gicleeframe.selection", "cache_hit": True})
    assert event_matches_pattern(cache_event, "cache_hit")
    assert event_matches_pattern(cache_event, "studio.gicleeframe.selection")

    media_event = PerfEvent.from_raw(
        2,
        {"event": "studio.gicleeframe.selection", "element_type": "media_section"},
    )
    assert event_matches_pattern(media_event, "media_section")


def test_compute_scenario_log_coverage_tolerance() -> None:
    profile = get_profile("giclee_studio")
    scenarios = profile.scenario_by_id()
    run = ScenarioRun(
        scenario_id="gf_open",
        scenario_name="GICLÉE FRAME open",
        start_ts="2026-07-07T12:00:00+00:00",
        end_ts="2026-07-07T12:00:01+00:00",
        completed=True,
    )
    events = [
        PerfEvent.from_raw(
            1,
            {
                "ts": "2026-07-07T11:59:59+00:00",
                "event": "studio.gicleeframe.build_shell",
            },
        ),
        PerfEvent.from_raw(
            2,
            {
                "ts": "2026-07-07T12:00:03+00:00",
                "event": "studio.gicleeframe.build_shell",
            },
        ),
    ]
    coverage = compute_scenario_log_coverage([run], scenarios, events, tolerance_s=2.0)
    assert coverage[0].status == "ok"
    assert coverage[0].expected_match_count >= 1
    assert "studio.gicleeframe" in coverage[0].matched_patterns


def test_compute_scenario_log_coverage_skipped() -> None:
    profile = get_profile("giclee_studio")
    run = ScenarioRun(scenario_id="gf_open", scenario_name="GF", skipped=True)
    coverage = compute_scenario_log_coverage([run], profile.scenario_by_id(), [])
    assert coverage[0].status == "skipped"


def test_dashboard_cold_early_event_seen_before_window() -> None:
    profile = get_profile("giclee_studio")
    scenarios = profile.scenario_by_id()
    run = ScenarioRun(
        scenario_id="dashboard_cold",
        scenario_name="Dashboard",
        start_ts="2026-07-07T21:21:41+00:00",
        end_ts="2026-07-07T21:21:41+00:00",
        completed=True,
    )
    events = [
        PerfEvent.from_raw(
            1,
            {
                "ts": "2026-07-07T21:20:30+00:00",
                "event": "studio.dashboard.visual.visible_ready",
            },
        ),
    ]
    coverage = compute_scenario_log_coverage([run], scenarios, events, tolerance_s=2.0)
    assert coverage[0].status == "early_event_seen"
    assert "studio.dashboard" in coverage[0].matched_patterns


def test_dashboard_cold_no_events_when_missing() -> None:
    profile = get_profile("giclee_studio")
    scenarios = profile.scenario_by_id()
    run = ScenarioRun(
        scenario_id="dashboard_cold",
        scenario_name="Dashboard",
        start_ts="2026-07-07T21:21:41+00:00",
        end_ts="2026-07-07T21:21:41+00:00",
        completed=True,
    )
    events = [
        PerfEvent.from_raw(
            1,
            {
                "ts": "2026-07-07T21:25:00+00:00",
                "event": "studio.hub.visual.visible_ready",
            },
        ),
    ]
    coverage = compute_scenario_log_coverage([run], scenarios, events, tolerance_s=2.0)
    assert coverage[0].status == "no_events_in_window"
