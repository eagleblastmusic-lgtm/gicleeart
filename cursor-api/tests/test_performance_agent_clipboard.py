from __future__ import annotations

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.__main__ import _build_parser, main, run_chatgpt_latest
from tools.performance_agent.clipboard import ClipboardCopyError, copy_text_to_clipboard

_COPY_BLOCK_MD = (
    "## COPY FOR CHATGPT\n\nPaste this block.\n\n---\n\n# Performance Audit Report\n"
)


def _sample_summary(*, slow: int = 3, suspects: int = 2) -> dict:
    return {
        "profile_id": "giclee_studio",
        "mode": "run",
        "source_log": "giclee_app/logs/studio_perf.log",
        "total_events": 42,
        "malformed_lines": 0,
        "slow_event_count": slow,
        "suspect_count": suspects,
        "ux_conflicts": [{"id": "UX_TEST"}],
        "log_coverage_conflicts": [],
        "scenario_log_coverage": [
            {"scenario_id": "hub_theme", "status": "ok"},
            {"scenario_id": "gf_open", "status": "missing_expected_events"},
        ],
    }


def _ux_scenarios(*, completed: int, skipped: int, total: int = 9) -> list[dict]:
    scenarios: list[dict] = []
    for index in range(total):
        if index < completed:
            scenarios.append({"scenario_id": f"s{index}", "completed": True, "skipped": False})
        elif index < completed + skipped:
            scenarios.append({"scenario_id": f"s{index}", "completed": False, "skipped": True})
        else:
            scenarios.append({"scenario_id": f"s{index}", "completed": False, "skipped": False})
    return scenarios


def _make_health_bundle(
    root: Path,
    dir_name: str,
    *,
    summary: dict,
    with_report_md: bool = True,
) -> Path:
    bundle = root / dir_name
    bundle.mkdir(parents=True)
    if with_report_md:
        (bundle / "report.md").write_text(_COPY_BLOCK_MD, encoding="utf-8")
    (bundle / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (bundle / "slow_events.csv").write_text("line_no\n", encoding="utf-8")
    (bundle / "scenario_timeline.csv").write_text("scenario_id\n", encoding="utf-8")
    (bundle / "questions_answers.json").write_text("{}", encoding="utf-8")
    return bundle


def _mock_profile(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    profile = MagicMock()
    profile.resolve_output_root.return_value = tmp_path
    monkeypatch.setattr(
        "tools.performance_agent.__main__.get_profile",
        lambda _profile_id: profile,
    )


def test_copy_text_to_clipboard_invokes_powershell_with_stdin(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs) -> MagicMock:  # noqa: ANN001, ARG001
        captured["args"] = args
        captured["kwargs"] = kwargs
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "win32")

    copy_text_to_clipboard("## COPY FOR CHATGPT\n")

    kwargs = captured["kwargs"]
    assert kwargs["input"] == "## COPY FOR CHATGPT\n"
    assert kwargs["encoding"] == "utf-8"
    assert kwargs["text"] is True
    assert kwargs["timeout"] == 5
    cmd = captured["args"][0]
    assert cmd[0] == "powershell"
    assert "-NoProfile" in cmd
    assert "Set-Clipboard" in cmd[-1]


def test_copy_text_to_clipboard_passes_unicode_via_stdin(monkeypatch) -> None:  # noqa: ANN001
    captured: dict[str, object] = {}

    def fake_run(*args, **kwargs) -> MagicMock:  # noqa: ANN001, ARG001
        captured["kwargs"] = kwargs
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "win32")

    text = "→ — ąęść 🎯"
    copy_text_to_clipboard(text)

    assert captured["kwargs"]["input"] == text


def test_copy_text_to_clipboard_raises_on_nonzero_returncode(monkeypatch) -> None:  # noqa: ANN001
    def fake_run(*args, **kwargs) -> MagicMock:  # noqa: ANN001, ARG001
        return MagicMock(returncode=1, stdout="", stderr="access denied")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(ClipboardCopyError, match="access denied"):
        copy_text_to_clipboard("test")


def test_copy_text_to_clipboard_raises_on_timeout(monkeypatch) -> None:  # noqa: ANN001
    def fake_run(*args, **kwargs) -> None:  # noqa: ANN001, ARG001
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(ClipboardCopyError, match="timed out"):
        copy_text_to_clipboard("test")


def test_copy_text_to_clipboard_raises_on_oserror(monkeypatch) -> None:  # noqa: ANN001
    def fake_run(*args, **kwargs) -> None:  # noqa: ANN001, ARG001
        raise OSError("powershell not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "platform", "win32")

    with pytest.raises(ClipboardCopyError, match="powershell not found"):
        copy_text_to_clipboard("test")


def test_copy_text_to_clipboard_raises_on_non_windows(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(ClipboardCopyError, match="only supported on Windows"):
        copy_text_to_clipboard("test")


def test_help_shows_clip_flag() -> None:
    help_text = _build_parser().format_help()
    assert "--clip" in help_text


def test_help_shows_health_gate_flag() -> None:
    help_text = _build_parser().format_help()
    assert "--health-gate" in help_text


def test_clip_without_chatgpt_latest_returns_error(capsys) -> None:
    exit_code = main(["--clip"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--clip can only be used with --chatgpt-latest" in captured.err


def test_health_gate_without_chatgpt_latest_returns_error(capsys) -> None:
    exit_code = main(["--health-gate"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--health-gate can only be used with --chatgpt-latest" in captured.err


def test_run_chatgpt_latest_clip_prints_operator_message(monkeypatch, tmp_path: Path) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-230000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 120,
            "ux_answers": {"scenarios": _ux_scenarios(completed=7, skipped=2, total=9)},
            "scenario_log_coverage": [{"status": "ok"} for _ in range(7)]
            + [{"status": "skipped"} for _ in range(2)],
        },
    )

    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    stdout = StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    exit_code = run_chatgpt_latest(profile_id="giclee_studio", clip=True)

    assert exit_code == 0
    assert stdout.getvalue().strip() == "COPY FOR CHATGPT block copied to clipboard."
    assert len(copied) == 1
    assert copied[0].startswith("## COPY FOR CHATGPT")
    assert "# Performance Audit Report" not in copied[0]


def test_health_gate_ready_prints_block(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 120,
            "ux_answers": {"scenarios": _ux_scenarios(completed=7, skipped=2, total=9)},
            "scenario_log_coverage": [{"status": "ok"} for _ in range(7)]
            + [{"status": "skipped"} for _ in range(2)],
        },
    )
    _mock_profile(monkeypatch, tmp_path)

    exit_code = run_chatgpt_latest(profile_id="giclee_studio", health_gate=True)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("## COPY FOR CHATGPT")
    assert "Health gate: READY" in captured.err


def test_health_gate_partial_prints_warning_and_block(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-190000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 35,
            "log_coverage_conflicts": [{"id": "SCENARIO_LOG_NOT_CONFIRMED"}],
            "ux_answers": {"scenarios": _ux_scenarios(completed=1, skipped=8, total=9)},
            "scenario_log_coverage": [
                {"status": "no_events_in_window"},
                *[{"status": "skipped"} for _ in range(8)],
            ],
        },
    )
    _mock_profile(monkeypatch, tmp_path)

    exit_code = run_chatgpt_latest(profile_id="giclee_studio", health_gate=True)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("## COPY FOR CHATGPT")
    assert "WARNING: Health gate status PARTIAL" in captured.err


def test_health_gate_needs_rerun_blocks_output(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-180000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 0,
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        },
    )
    _mock_profile(monkeypatch, tmp_path)

    exit_code = run_chatgpt_latest(profile_id="giclee_studio", health_gate=True)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "Status: NEEDS_RERUN" in captured.err


def test_health_gate_broken_blocks_output(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-170000_giclee_studio",
        summary=_sample_summary(),
        with_report_md=False,
    )
    _mock_profile(monkeypatch, tmp_path)

    exit_code = run_chatgpt_latest(profile_id="giclee_studio", health_gate=True)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "Status: BROKEN" in captured.err


def test_health_gate_clip_needs_rerun_skips_clipboard(monkeypatch, tmp_path: Path, capsys) -> None:
    _make_health_bundle(
        tmp_path,
        "20260707-160000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 0,
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
        },
    )
    _mock_profile(monkeypatch, tmp_path)

    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    exit_code = run_chatgpt_latest(
        profile_id="giclee_studio",
        clip=True,
        health_gate=True,
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert copied == []
    assert captured.out == ""
    assert "Status: NEEDS_RERUN" in captured.err
