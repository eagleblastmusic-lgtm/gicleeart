from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workers.bridge_runner import (
    LOG_FILE,
    REQUEST_FILE,
    RESULT_FILE,
    STATUS_FILE,
    fail_job,
    resolve_komponenty_paths,
    run_job,
    sanitize_log_line,
    write_json_atomic,
)


def _write_request(
    job_dir: Path,
    command: str,
    request_id: str = "req-1",
    *,
    args: dict[str, str] | None = None,
    project_roots: dict[str, str] | None = None,
    timeout_seconds: int | None = None,
) -> None:
    job_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "requestId": request_id,
        "schemaVersion": "1.0",
        "command": command,
        "workerId": "python-bridge",
    }
    if args is not None:
        payload["args"] = args
    if project_roots is not None:
        payload["projectRoots"] = project_roots
    if timeout_seconds is not None:
        payload["timeoutSeconds"] = timeout_seconds
    (job_dir / REQUEST_FILE).write_text(json.dumps(payload), encoding="utf-8")


def test_ping_creates_result(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-ping"
    _write_request(job_dir, "ping")

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Succeeded"
    assert "Python bridge ping completed successfully." in result["summary"]
    assert result["payload"]["jobDir"] == str(job_dir.resolve())
    assert (job_dir / STATUS_FILE).exists()
    assert (job_dir / LOG_FILE).exists()


def test_env_check_creates_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job_dir = tmp_path / "job-env"
    workspace = tmp_path / "cursor-api"
    tools = workspace / "tools"
    komponenty = workspace.parent / "Komponenty"
    tools.mkdir(parents=True)
    komponenty.mkdir(parents=True)
    monkeypatch.chdir(workspace)

    _write_request(job_dir, "env_check")
    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    payload = result["payload"]
    assert payload["komponentyExists"] == "true"
    assert payload["toolsExists"] == "true"
    assert payload["komponentyPath"] == str(komponenty)
    assert payload["toolsPath"] == str(tools)
    assert payload["ok"] == "true"


def test_unknown_command_fails(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-bad"
    _write_request(job_dir, "run_module")

    exit_code = run_job(job_dir)

    assert exit_code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"
    assert result["errors"][0]["code"] == "unknown_command"


def test_write_json_atomic_produces_valid_json(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    write_json_atomic(target, {"status": "Running", "progress": 50, "message": "x", "updatedUtc": "t"})
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["status"] == "Running"


def test_resolve_komponenty_prefers_parent(tmp_path: Path) -> None:
    cwd = tmp_path / "cursor-api"
    cwd.mkdir()
    parent_komponenty = tmp_path / "Komponenty"
    parent_komponenty.mkdir()
    local_komponenty = cwd / "Komponenty"
    local_komponenty.mkdir()

    path, exists = resolve_komponenty_paths(cwd)

    assert exists is True
    assert path == str(parent_komponenty)


def test_fail_job_writes_failed_result(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-fail"
    job_dir.mkdir()
    request = {"requestId": "r1", "command": "bad"}

    code = fail_job(job_dir, request, "unknown_command", "bad command")

    assert code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"


def test_sanitize_log_line_masks_secrets() -> None:
    assert "token=***" in sanitize_log_line("token=abc123")
    assert "api_key=***" in sanitize_log_line("api_key=secret")
    assert "password=***" in sanitize_log_line("password=hunter2")
    assert "bearer ***" in sanitize_log_line("bearer sk-abc")


def _setup_cursor_api_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    workspace = tmp_path / "cursor-api"
    (workspace / "tools").mkdir(parents=True)
    monkeypatch.chdir(workspace)
    return workspace


def test_run_tool_doctor_creates_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_dir = tmp_path / "job-doctor"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "performance_agent_doctor"},
        project_roots={
            "cursorApiRoot": str(workspace),
            "themeRoot": str(tmp_path),
        },
    )

    mock_process = MagicMock()
    mock_process.communicate.return_value = ("doctor ok line\n", "")
    mock_process.returncode = 0

    monkeypatch.setattr("workers.bridge_runner.subprocess.Popen", lambda *a, **k: mock_process)

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Succeeded"
    assert result["summary"] == "Performance Agent doctor completed successfully."
    assert result["payload"]["toolId"] == "performance_agent_doctor"
    assert result["payload"]["readOnly"] == "true"


def test_run_tool_unknown_tool_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job_dir = tmp_path / "job-unknown-tool"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "forbidden_tool"},
        project_roots={"cursorApiRoot": str(workspace), "themeRoot": str(tmp_path)},
    )

    exit_code = run_job(job_dir)

    assert exit_code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"
    assert result["errors"][0]["code"] == "tool_not_allowed"


def test_run_tool_invalid_project_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job_dir = tmp_path / "job-bad-roots"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "performance_agent_doctor"},
        project_roots={"cursorApiRoot": str(tmp_path / "missing"), "themeRoot": str(tmp_path)},
    )

    exit_code = run_job(job_dir)

    assert exit_code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"
    assert result["errors"][0]["code"] == "invalid_project_roots"


def test_run_tool_captures_stdout_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job_dir = tmp_path / "job-capture"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "performance_agent_doctor"},
        project_roots={"cursorApiRoot": str(workspace), "themeRoot": str(tmp_path)},
    )

    mock_process = MagicMock()
    mock_process.communicate.return_value = ("stdout line\n", "stderr line\n")
    mock_process.returncode = 1

    monkeypatch.setattr("workers.bridge_runner.subprocess.Popen", lambda *a, **k: mock_process)

    run_job(job_dir)

    log_lines = (job_dir / LOG_FILE).read_text(encoding="utf-8").strip().splitlines()
    sources = [json.loads(line)["source"] for line in log_lines]
    messages = [json.loads(line)["message"] for line in log_lines]
    assert "performance_agent_doctor" in sources
    assert "stdout line" in messages
    assert "stderr line" in messages


def test_run_tool_missing_theme_root_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-no-theme"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "project_state_snapshot"},
        project_roots={"cursorApiRoot": str(workspace)},
    )

    exit_code = run_job(job_dir)

    assert exit_code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"
    assert result["errors"][0]["code"] == "invalid_project_roots"


def test_project_state_snapshot_succeeds_without_subprocess(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-snapshot"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    (workspace / "workers").mkdir()
    (workspace / "workers" / "bridge_runner.py").write_text("# stub", encoding="utf-8")
    (workspace / "reports" / "performance").mkdir(parents=True)

    def _fail_popen(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("project_state_snapshot must not spawn a subprocess")

    monkeypatch.setattr("workers.bridge_runner.subprocess.Popen", _fail_popen)

    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "project_state_snapshot"},
        project_roots={"cursorApiRoot": str(workspace), "themeRoot": str(tmp_path)},
    )

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Succeeded"
    assert result["summary"] == "Project state snapshot completed successfully."
    payload = result["payload"]
    assert payload["cursorApiRootExists"] == "true"
    assert payload["toolsExists"] == "true"
    assert payload["workersBridgeRunnerExists"] == "true"
    assert payload["reportsPerformanceExists"] == "true"
    assert payload["themeRootExists"] == "true"
    assert "timestampUtc" in payload


class _FakeCompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _git_readonly_request(job_dir: Path, workspace: Path, tmp_path: Path) -> None:
    _write_request(
        job_dir,
        "run_tool",
        args={"toolId": "git_status_readonly"},
        project_roots={"cursorApiRoot": str(workspace), "themeRoot": str(tmp_path)},
    )


def test_git_status_readonly_reports_branch_head_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-git"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _git_readonly_request(job_dir, workspace, tmp_path)

    def _fake_run(cmd: list[str], **_kwargs: object) -> _FakeCompletedProcess:
        git_args = tuple(cmd[3:])
        if git_args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return _FakeCompletedProcess(0, stdout="main\n")
        if git_args == ("rev-parse", "HEAD"):
            return _FakeCompletedProcess(0, stdout="abc123\n")
        if git_args == ("status", "--short"):
            return _FakeCompletedProcess(0, stdout=" M a.py\n M b.py\n")
        raise AssertionError(f"unexpected git args: {git_args}")

    monkeypatch.setattr("workers.bridge_runner.subprocess.run", _fake_run)

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Succeeded"
    payload = result["payload"]
    assert payload["cursorApiBranch"] == "main"
    assert payload["cursorApiHead"] == "abc123"
    assert payload["cursorApiDirtyCount"] == "2"
    assert payload["cursorApiHasDirtyState"] == "true"


def test_git_status_readonly_truncates_long_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-git-long"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _git_readonly_request(job_dir, workspace, tmp_path)

    long_status = "".join(f" M file_{i}.py\n" for i in range(250))

    def _fake_run(cmd: list[str], **_kwargs: object) -> _FakeCompletedProcess:
        git_args = tuple(cmd[3:])
        if git_args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return _FakeCompletedProcess(0, stdout="main\n")
        if git_args == ("rev-parse", "HEAD"):
            return _FakeCompletedProcess(0, stdout="abc123\n")
        if git_args == ("status", "--short"):
            return _FakeCompletedProcess(0, stdout=long_status)
        raise AssertionError(f"unexpected git args: {git_args}")

    monkeypatch.setattr("workers.bridge_runner.subprocess.run", _fake_run)

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["payload"]["cursorApiDirtyCount"] == "250"

    log_lines = (job_dir / LOG_FILE).read_text(encoding="utf-8").strip().splitlines()
    messages = [json.loads(line)["message"] for line in log_lines]
    truncated = [m for m in messages if "truncated" in m]
    assert truncated, "expected a truncated marker in the git log output"
    status_lines = [m for m in messages if m.startswith("cursor-api:  M file_")]
    assert len(status_lines) == 100


def test_git_status_readonly_not_a_repo_is_warning_not_crash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-git-norepo"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _git_readonly_request(job_dir, workspace, tmp_path)

    def _fake_run(cmd: list[str], **_kwargs: object) -> _FakeCompletedProcess:
        return _FakeCompletedProcess(128, stderr="fatal: not a git repository")

    monkeypatch.setattr("workers.bridge_runner.subprocess.run", _fake_run)

    exit_code = run_job(job_dir)

    assert exit_code == 0
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Succeeded"
    payload = result["payload"]
    assert payload["cursorApiBranch"] == "Unknown"
    assert payload["cursorApiDirtyCount"] == "0"
    assert payload["cursorApiHasDirtyState"] == "false"


def test_git_status_readonly_missing_git_fails_cleanly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_dir = tmp_path / "job-git-missing"
    workspace = _setup_cursor_api_workspace(tmp_path, monkeypatch)
    _git_readonly_request(job_dir, workspace, tmp_path)

    def _fake_run(*_args: object, **_kwargs: object) -> _FakeCompletedProcess:
        raise FileNotFoundError("git")

    monkeypatch.setattr("workers.bridge_runner.subprocess.run", _fake_run)

    exit_code = run_job(job_dir)

    assert exit_code == 1
    result = json.loads((job_dir / RESULT_FILE).read_text(encoding="utf-8"))
    assert result["status"] == "Failed"
    assert result["errors"][0]["code"] == "git_not_available"


def test_git_readonly_rejects_non_allowlisted_command() -> None:
    from workers.bridge_runner import ALLOWED_GIT_COMMANDS, _git_run

    assert ("status", "--short") in ALLOWED_GIT_COMMANDS
    with pytest.raises(ValueError):
        _git_run(Path("."), ("push", "origin", "main"), 10)
