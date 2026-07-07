from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.profiles import get_profile
from tools.performance_agent.runner import run_manual
from tools.performance_agent.wizard import WizardConfig, _scenario_action


class ScriptedIO:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.outputs: list[str] = []

    def input(self, prompt: str) -> str:
        self.outputs.append(prompt)
        if not self._responses:
            return ""
        return self._responses.pop(0)

    def print(self, text: str) -> None:
        self.outputs.append(text)


def _base_answers() -> dict:
    return {
        "answers": {
            "skeletons_seen": "no",
            "layout_shift": "no",
            "sequential_popin": "no",
            "click_instant": "yes",
            "freeze_seen": "no",
            "overlay_too_long": "no",
            "cache_felt": "yes",
            "main_complaint": "nothing",
            "smoothness_score": 4,
            "note": "",
        }
    }


def test_wizard_records_start_end_and_quit_partial_report(tmp_path: Path, monkeypatch) -> None:
    profile = get_profile("giclee_studio")
    report_dir = tmp_path / "report"
    missing_log = tmp_path / "missing.log"

    monkeypatch.setattr(
        "tools.performance_agent.runner.make_report_dir",
        lambda _profile: report_dir,
    )

    io = ScriptedIO(
        [
            "y",  # intro continue
            "",  # scenario 1 start
            "",  # scenario 1 done
            "q",  # quit on scenario 2
        ]
    )

    config = WizardConfig(
        auto_answers={
            "dashboard_cold": _base_answers(),
        },
        skip_scenarios=set(profile.manual_scenarios[i].id for i in range(2, len(profile.manual_scenarios))),
    )

    bundle = run_manual(
        profile_id="giclee_studio",
        log_path=missing_log,
        output_dir=report_dir,
        io=io,
        config=config,
    )

    assert bundle.report_md.exists()
    agent_log = report_dir / "agent_events.jsonl"
    assert agent_log.exists()

    events = [json.loads(line) for line in agent_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    event_names = [e["event"] for e in events]
    assert "agent.scenario.start" in event_names
    assert "agent.scenario.end" in event_names
    assert "agent.scenario.quit_requested" in event_names
    assert "agent.session.end" in event_names

    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    assert summary["mode"] == "manual"
    assert summary["log_missing"] is True
    assert summary["session_status"] == "quit_early"

    report_text = bundle.report_md.read_text(encoding="utf-8")
    assert "Manual UX Summary" in report_text
    assert "log missing" in report_text.lower() or "Log missing" in report_text


def test_wizard_skip_scenario_in_timeline(tmp_path: Path, monkeypatch) -> None:
    profile = get_profile("giclee_studio")
    report_dir = tmp_path / "report_skip"
    log = tmp_path / "studio_perf.log"
    log.write_text(
        '{"event":"studio.dashboard.visual.visible_ready","ts":"2026-07-07T12:00:00+00:00"}\n',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "tools.performance_agent.runner.make_report_dir",
        lambda _profile: report_dir,
    )

    skip_all = {s.id for s in profile.manual_scenarios}
    io = ScriptedIO(["y"])

    bundle = run_manual(
        profile_id="giclee_studio",
        log_path=log,
        output_dir=report_dir,
        io=io,
        config=WizardConfig(skip_scenarios=skip_all),
    )

    timeline = (report_dir / "scenario_timeline.csv").read_text(encoding="utf-8")
    assert "skipped" in timeline.lower() or "True" in timeline
    assert bundle.agent_events_jsonl is not None


def test_wizard_scenario_display_is_human_readable_checklist() -> None:
    profile = get_profile("giclee_studio")
    gf_open = profile.scenario_by_id()["gf_open"]
    io = ScriptedIO([""])

    _scenario_action(io, gf_open, index=4, total=9)
    output = "\n".join(io.outputs)

    assert "[4/9] GICLÉE FRAME — pierwsze otwarcie" in output
    assert "Co kliknąć:" in output
    assert "Co obserwować:" in output
    assert "Kiedy nacisnąć Enter:" in output
    assert "Oczekiwane sygnały w logu:" in output
    assert "studio.gicleeframe" in output
    assert "Enter=start | s=skip | q=quit:" in output
