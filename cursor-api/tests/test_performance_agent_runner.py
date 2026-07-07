from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.process import StudioProcess, shutdown_studio, wait_startup_grace
from tools.performance_agent.profiles import get_profile
from tools.performance_agent.runner import run_with_studio
from tools.performance_agent.wizard import WizardConfig


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


def test_shutdown_studio_prompts_before_kill() -> None:
    popen = MagicMock()
    popen.poll.side_effect = [None, None, None, None]
    popen.pid = 9999
    proc = StudioProcess(popen=popen, pid=9999, command=["python"], started_at="2026-01-01T00:00:00+00:00")
    io = ScriptedIO(["n"])

    with patch("tools.performance_agent.process.time.sleep", return_value=None):
        with patch("tools.performance_agent.process.time.monotonic", side_effect=[0, 6]):
            result = shutdown_studio(proc, io)

    assert result is None
    popen.kill.assert_not_called()


def test_shutdown_studio_kill_when_confirmed() -> None:
    popen = MagicMock()
    popen.poll.side_effect = [None, None, None, 1]
    popen.wait.return_value = 1
    popen.pid = 9999
    proc = StudioProcess(popen=popen, pid=9999, command=["python"], started_at="2026-01-01T00:00:00+00:00")
    io = ScriptedIO(["y"])

    with patch("tools.performance_agent.process.time.sleep", return_value=None):
        with patch("tools.performance_agent.process.time.monotonic", side_effect=[0, 6]):
            result = shutdown_studio(proc, io)

    popen.kill.assert_called_once()
    assert result == 1


def test_wait_startup_grace_detects_early_exit() -> None:
    popen = MagicMock()
    popen.poll.return_value = 1
    proc = StudioProcess(popen=popen, pid=1, command=[], started_at="")
    assert wait_startup_grace(proc, seconds=0.01) is False


@patch("tools.performance_agent.runner.launch_studio")
@patch("tools.performance_agent.runner.wait_startup_grace", return_value=False)
def test_run_with_studio_start_failed_partial_report(
    _grace: MagicMock,
    mock_launch: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = get_profile("giclee_studio")
    report_dir = tmp_path / "report"
    log = tmp_path / "studio_perf.log"

    popen = MagicMock()
    popen.poll.return_value = 1
    popen.pid = 4242
    mock_launch.return_value = StudioProcess(
        popen=popen,
        pid=4242,
        command=["python", "-m", "giclee_app.studio_preview"],
        started_at="2026-07-07T12:00:00+00:00",
    )

    monkeypatch.setattr(
        "tools.performance_agent.runner.make_report_dir",
        lambda _profile: report_dir,
    )

    skip_all = {s.id for s in profile.manual_scenarios}
    io = ScriptedIO(["1", "y", "n"])

    bundle = run_with_studio(
        profile_id="giclee_studio",
        log_path=log,
        output_dir=report_dir,
        io=io,
        config=WizardConfig(skip_scenarios=skip_all),
        lifecycle_mode="clear",
    )

    assert bundle.report_md.exists()
    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    assert summary["mode"] == "run"
    assert summary["log_lifecycle"]["mode"] == "clear"
    assert summary["studio"]["start_failed"] is True
    assert summary["log_missing"] is True

    events = [
        json.loads(line)
        for line in (report_dir / "agent_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_names = [e["event"] for e in events]
    assert "agent.studio.launched" in event_names
    assert "agent.studio.start_failed" in event_names


@patch("tools.performance_agent.runner.launch_studio", side_effect=OSError("spawn failed"))
def test_run_with_studio_launch_error_partial_report(
    _mock_launch: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_dir = tmp_path / "report_err"
    monkeypatch.setattr(
        "tools.performance_agent.runner.make_report_dir",
        lambda _profile: report_dir,
    )

    profile = get_profile("giclee_studio")
    skip_all = {s.id for s in profile.manual_scenarios}
    io = ScriptedIO(["y", "n"])

    bundle = run_with_studio(
        profile_id="giclee_studio",
        log_path=tmp_path / "missing.log",
        output_dir=report_dir,
        io=io,
        config=WizardConfig(skip_scenarios=skip_all),
        lifecycle_mode="keep",
    )

    summary = json.loads(bundle.summary_json.read_text(encoding="utf-8"))
    assert summary["studio"]["start_failed"] is True
    assert bundle.report_md.read_text(encoding="utf-8")
