from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.collector import collect_log
from tools.performance_agent.models import ManualSession, ScenarioRun
from tools.performance_agent.parser.giclee_studio import parse_for_profile
from tools.performance_agent.profiles import get_profile
from tools.performance_agent.report.generator import generate_report
from tools.performance_agent.timeutil import utc_now_iso


def _session_with_conflict_scenario() -> ManualSession:
    return ManualSession(
        profile_id="giclee_studio",
        report_dir=Path("."),
        started_at=utc_now_iso(),
        log_path=Path("studio_perf.log"),
        scenarios=[
            ScenarioRun(
                scenario_id="gf_open",
                scenario_name="GICLÉE FRAME open",
                start_ts="2026-07-07T12:00:00+00:00",
                end_ts="2026-07-07T12:00:05+00:00",
                duration_ms=5000,
                completed=True,
                skipped=False,
                answers={
                    "smoothness_score": 2,
                    "main_complaint": "freeze",
                    "skeletons_seen": "yes",
                    "layout_shift": "yes",
                    "sequential_popin": "yes",
                    "freeze_seen": "yes",
                    "note": "felt slow",
                },
            )
        ],
        status="completed",
    )


def test_scenario_timeline_csv_not_placeholder(tmp_path: Path) -> None:
    profile = get_profile("giclee_studio")
    log = tmp_path / "studio_perf.log"
    log.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts": "2026-07-07T12:00:01+00:00",
                        "event": "studio.dashboard.visual.visible_ready",
                        "elapsed_ms": 50,
                    }
                ),
                json.dumps(
                    {
                        "ts": "2026-07-07T12:00:03+00:00",
                        "event": "studio.gicleeframe.build_shell",
                        "elapsed_ms": 90,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report_dir = tmp_path / "out"
    collection = collect_log(log, report_dir)
    parse = parse_for_profile(collection.events_jsonl, profile)
    session = _session_with_conflict_scenario()
    session.report_dir = report_dir

    bundle = generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=session,
    )

    with bundle.scenario_timeline_csv.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["scenario_id"] == "gf_open"
    assert rows[0]["completed"] == "True"
    assert rows[0]["smoothness_score"] == "2"
    assert rows[0]["log_coverage_status"] == "ok"
    assert "placeholder" not in bundle.scenario_timeline_csv.read_text(encoding="utf-8").lower()

    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    assert "ux_answers" in summary
    assert "ux_conflicts" in summary
    assert "scenario_log_coverage" in summary
    gf_coverage = summary["scenario_log_coverage"][0]
    assert gf_coverage["scenario_id"] == "gf_open"
    assert gf_coverage["status"] == "ok"
    assert gf_coverage["expected_match_count"] >= 1
    assert any(c["id"] == "UX_CONFLICT_LOW_SCORE_WITH_OK_METRICS" for c in summary["ux_conflicts"])

    report_text = bundle.report_md.read_text(encoding="utf-8")
    assert "Manual UX Summary" in report_text
    assert "Scenario Log Coverage" in report_text
    assert "Metric / UX Conflicts" in report_text
    assert "session/data quality" in report_text.lower()


def test_scenario_log_coverage_missing_gf_events(tmp_path: Path) -> None:
    profile = get_profile("giclee_studio")
    log = tmp_path / "studio_perf.log"
    log.write_text(
        json.dumps(
            {
                "ts": "2026-07-07T12:00:01+00:00",
                "event": "studio.hub.visual.visible_ready",
                "elapsed_ms": 50,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report_dir = tmp_path / "out_missing"
    collection = collect_log(log, report_dir)
    parse = parse_for_profile(collection.events_jsonl, profile)
    session = _session_with_conflict_scenario()
    session.report_dir = report_dir

    bundle = generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=session,
    )

    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    gf_coverage = summary["scenario_log_coverage"][0]
    assert gf_coverage["status"] == "missing_expected_events"
    assert gf_coverage["expected_match_count"] == 0
    assert "studio.gicleeframe" in gf_coverage["expected"]

    assert summary["log_coverage_conflicts"]
    assert summary["log_coverage_conflicts"][0]["id"] == "SCENARIO_LOG_NOT_CONFIRMED"
    assert "session/data quality" in summary["log_coverage_conflicts"][0]["message"].lower()

    report_text = bundle.report_md.read_text(encoding="utf-8")
    assert "SCENARIO_LOG_NOT_CONFIRMED" in report_text
    assert "not necessarily a GicleeApp runtime regression" in report_text
