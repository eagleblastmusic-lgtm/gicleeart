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


def _sample_log(tmp_path: Path) -> Path:
    log = tmp_path / "studio_perf.log"
    rows = [
        {"event": "studio.dashboard.visual.visible_ready", "elapsed_ms": 120},
        {"event": "studio.gicleeframe.visual.perceived_ready", "since_enter_ms": 500},
        {"event": "studio.gicleeframe.build_shell", "elapsed_ms": 300},
        {
            "event": "studio.gicleeframe.details_module.applied",
            "since_request_ms": 800,
        },
    ]
    log.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return log


def _session_with_gf_open() -> ManualSession:
    return ManualSession(
        profile_id="giclee_studio",
        report_dir=Path("."),
        started_at=utc_now_iso(),
        log_path=Path("studio_perf.log"),
        scenarios=[
            ScenarioRun(
                scenario_id="gf_open",
                scenario_name="GICLÉE FRAME — pierwsze otwarcie",
                start_ts="2026-07-07T12:00:00+00:00",
                end_ts="2026-07-07T12:00:05+00:00",
                duration_ms=5000,
                completed=True,
                skipped=False,
                answers={
                    "smoothness_score": 4,
                    "main_complaint": "nothing",
                    "skeletons_seen": "no",
                    "layout_shift": "no",
                    "sequential_popin": "no",
                    "freeze_seen": "no",
                    "note": "",
                },
            )
        ],
        status="completed",
    )


def test_generate_report_bundle(tmp_path: Path) -> None:
    profile = get_profile("giclee_studio")
    source = _sample_log(tmp_path)
    report_dir = tmp_path / "report_out"

    collection = collect_log(source, report_dir)
    parse = parse_for_profile(collection.events_jsonl, profile)
    bundle = generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=None,
    )

    assert bundle.report_md.exists()
    assert bundle.summary_json.exists()
    assert bundle.slow_events_csv.exists()
    assert bundle.scenario_timeline_csv.exists()
    assert bundle.questions_answers_json.exists()
    assert bundle.events_jsonl.exists()
    assert bundle.raw_log.exists()

    report_text = bundle.report_md.read_text(encoding="utf-8")
    assert "## COPY FOR CHATGPT" in report_text
    assert "What I need ChatGPT to analyze" in report_text

    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    assert summary["profile_id"] == "giclee_studio"
    assert summary["total_events"] == 4
    assert summary["suspect_count"] >= 1
    assert "heuristics" in summary
    assert "suspects" in summary["heuristics"]

    csv_text = bundle.slow_events_csv.read_text(encoding="utf-8")
    assert "elapsed_ms" in csv_text
    assert "studio.gicleeframe.build_shell" in csv_text


def test_report_shows_display_title_with_scenario_id(tmp_path: Path) -> None:
    profile = get_profile("giclee_studio")
    log = tmp_path / "studio_perf.log"
    log.write_text(
        json.dumps(
            {
                "ts": "2026-07-07T12:00:01+00:00",
                "event": "studio.gicleeframe.build_shell",
                "elapsed_ms": 90,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report_dir = tmp_path / "report_display_title"
    collection = collect_log(log, report_dir)
    parse = parse_for_profile(collection.events_jsonl, profile)
    session = _session_with_gf_open()
    session.report_dir = report_dir

    bundle = generate_report(
        profile=profile,
        collection=collection,
        parse=parse,
        report_dir=report_dir,
        session=session,
    )

    report_text = bundle.report_md.read_text(encoding="utf-8")
    assert "gf_open — GICLÉE FRAME — pierwsze otwarcie" in report_text

    with bundle.scenario_timeline_csv.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["scenario_id"] == "gf_open"
    assert rows[0]["display_title"] == "GICLÉE FRAME — pierwsze otwarcie"
