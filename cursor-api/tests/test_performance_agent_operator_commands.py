from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.performance_agent.__main__ import (
    _build_parser,
    main,
    open_report_directory,
    run_doctor,
    run_open_latest,
    run_prepare_chatgpt_latest,
)
from tools.performance_agent.clipboard import ClipboardCopyError, describe_clipboard_support
from tools.performance_agent.report.index import (
    format_doctor_status,
    format_open_latest_paths,
    format_prepare_chatgpt_prep,
)

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


def _mock_profile(monkeypatch, tmp_path: Path, *, default_log_exists: bool = False) -> None:  # noqa: ANN001
    profile = MagicMock()
    profile.resolve_output_root.return_value = tmp_path
    default_log = tmp_path / "studio_perf.log"
    if default_log_exists:
        default_log.write_text("log\n", encoding="utf-8")
    profile.resolve_log_path.return_value = default_log
    monkeypatch.setattr(
        "tools.performance_agent.__main__.get_profile",
        lambda _profile_id: profile,
    )


def test_help_shows_operator_flags() -> None:
    help_text = _build_parser().format_help()
    assert "--prepare-chatgpt-latest" in help_text
    assert "--open-latest" in help_text
    assert "--doctor" in help_text


def test_format_prepare_chatgpt_prep_ready() -> None:
    output = format_prepare_chatgpt_prep("READY")
    assert "Status: READY" in output
    assert "COPY FOR CHATGPT block copied to clipboard." in output
    assert "Paste it into ChatGPT with Ctrl+V." in output
    assert "WARNING" not in output


def test_format_prepare_chatgpt_prep_partial() -> None:
    output = format_prepare_chatgpt_prep("PARTIAL")
    assert "Status: PARTIAL" in output
    assert "WARNING: Report is reviewable with caveat" in output


def test_format_doctor_status_no_reports(tmp_path: Path) -> None:
    output = format_doctor_status(
        version="0.1.0a",
        profile_id="giclee_studio",
        output_root=tmp_path,
        output_root_exists=False,
        report_bundle_count=0,
        latest_bundle_name=None,
        latest_health_status=None,
        default_log_exists=False,
        clipboard_support="Windows PowerShell Set-Clipboard",
    )
    assert "Report bundles: 0" in output
    assert "Latest bundle: none" in output
    assert "Latest health: n/a" in output
    assert "Default log exists: no" in output
    assert "--prepare-chatgpt-latest" in output


def test_prepare_ready_copies_exit_0(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
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
    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    exit_code = run_prepare_chatgpt_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Status: READY" in captured.out
    assert len(copied) == 1
    assert copied[0].startswith("## COPY FOR CHATGPT")


def test_prepare_partial_copies_warning_exit_0(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
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
    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    exit_code = run_prepare_chatgpt_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Status: PARTIAL" in captured.out
    assert "WARNING: Report is reviewable with caveat" in captured.out
    assert len(copied) == 1


def test_prepare_needs_rerun_no_clipboard_exit_2(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _make_health_bundle(
        tmp_path,
        "20260707-180000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 0,
            "ux_answers": {"scenarios": _ux_scenarios(completed=0, skipped=9, total=9)},
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

    exit_code = run_prepare_chatgpt_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 2
    assert copied == []
    assert "Status: NEEDS_RERUN" in captured.err
    assert "COPY FOR CHATGPT block was not copied." in captured.err


def test_prepare_broken_no_clipboard_exit_2(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _make_health_bundle(
        tmp_path,
        "20260707-170000_giclee_studio",
        summary=_sample_summary(),
        with_report_md=False,
    )
    copied: list[str] = []

    def fake_copy(text: str) -> None:
        copied.append(text)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    exit_code = run_prepare_chatgpt_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 2
    assert copied == []
    assert "Status: BROKEN" in captured.err


def test_prepare_clipboard_error_exit_1(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _make_health_bundle(
        tmp_path,
        "20260707-160000_giclee_studio",
        summary={
            **_sample_summary(),
            "total_events": 120,
            "ux_answers": {"scenarios": _ux_scenarios(completed=7, skipped=2, total=9)},
        },
    )

    def fake_copy(_text: str) -> None:
        raise ClipboardCopyError("access denied")

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "tools.performance_agent.__main__.copy_text_to_clipboard",
        fake_copy,
    )

    exit_code = run_prepare_chatgpt_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "access denied" in captured.err


def test_doctor_no_reports(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _mock_profile(monkeypatch, tmp_path, default_log_exists=False)

    exit_code = run_doctor(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Report bundles: 0" in captured.out
    assert "Latest bundle: none" in captured.out
    assert "Default log exists: no" in captured.out


def test_doctor_with_reports(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
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
    _mock_profile(monkeypatch, tmp_path, default_log_exists=True)

    exit_code = run_doctor(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Report bundles: 1" in captured.out
    assert "Latest bundle: 20260707-200000_giclee_studio" in captured.out
    assert "Latest health: READY" in captured.out
    assert "Default log exists: yes" in captured.out


def test_doctor_missing_default_log_no_crash(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _mock_profile(monkeypatch, tmp_path, default_log_exists=False)

    exit_code = run_doctor(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Default log exists: no" in captured.out


def test_open_latest_no_reports(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _mock_profile(monkeypatch, tmp_path)

    exit_code = run_open_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "No performance report bundles found." in captured.out


def test_open_latest_opens_dir(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    bundle = _make_health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_sample_summary(),
    )
    opened: list[str] = []

    def fake_startfile(path: str) -> None:
        opened.append(path)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("tools.performance_agent.__main__.os.startfile", fake_startfile)

    exit_code = run_open_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Report directory:" in captured.out
    assert "report.md:" in captured.out
    assert "summary.json:" in captured.out
    assert len(opened) == 1
    assert Path(opened[0]).resolve() == bundle.resolve()


def test_open_report_directory_raises_on_non_windows(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "linux")

    with pytest.raises(OSError, match="only supported on Windows"):
        open_report_directory(Path("/tmp/report"))


def test_open_latest_non_windows_skips_startfile(monkeypatch, tmp_path: Path, capsys) -> None:  # noqa: ANN001
    _make_health_bundle(
        tmp_path,
        "20260707-200000_giclee_studio",
        summary=_sample_summary(),
    )
    called: list[str] = []

    def fake_startfile(path: str) -> None:
        called.append(path)

    _mock_profile(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("tools.performance_agent.__main__.os.startfile", fake_startfile)

    exit_code = run_open_latest(profile_id="giclee_studio")

    captured = capsys.readouterr()
    assert exit_code == 0
    assert called == []
    assert "only supported on Windows" in captured.err


def test_main_doctor_dispatch(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    _mock_profile(monkeypatch, tmp_path)
    exit_code = main(["--doctor"])
    assert exit_code == 0


def test_describe_clipboard_support_windows(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "win32")
    assert describe_clipboard_support() == "Windows PowerShell Set-Clipboard"


def test_describe_clipboard_support_non_windows(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(sys, "platform", "linux")
    assert describe_clipboard_support() == "no"


def test_format_open_latest_paths(tmp_path: Path) -> None:
    bundle = tmp_path / "20260707-200000_giclee_studio"
    bundle.mkdir()
    output = format_open_latest_paths(bundle)
    assert "Report directory:" in output
    assert str((bundle / "report.md").resolve()) in output
    assert str((bundle / "summary.json").resolve()) in output
