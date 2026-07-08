"""Minimal Python bridge runner for GicleeApp Studio worker jobs (GAS-2B/2C/GAS-4).

GAS-4 adds a small, explicitly allowlisted set of read-only tools behind the
``run_tool`` command. Only the three tool ids below are permitted; there is no
general command runner, no ``shell=True`` and no user-provided arguments.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_FILE = "worker_request.json"
STATUS_FILE = "status.json"
LOG_FILE = "worker_log.jsonl"
RESULT_FILE = "worker_result.json"
SOURCE = "workers.bridge_runner"

# GAS-4 allowlist. Every entry is read-only. Nothing here may write files,
# call Shopify, build GPT ZIP archives or run arbitrary modules.
ALLOWED_TOOLS: dict[str, dict[str, Any]] = {
    "performance_agent_doctor": {
        "kind": "subprocess_module",
        "module": "tools.performance_agent",
        "args": ["--doctor"],
        "read_only": True,
        "default_timeout": 120,
        "log_source": "performance_agent_doctor",
        "summary_success": "Performance Agent doctor completed successfully.",
        "summary_failure": "Performance Agent doctor failed.",
    },
    "project_state_snapshot": {
        "kind": "builtin",
        "read_only": True,
        "default_timeout": 60,
        "log_source": "project_state_snapshot",
        "summary_success": "Project state snapshot completed successfully.",
    },
    "git_status_readonly": {
        "kind": "git_readonly",
        "read_only": True,
        "default_timeout": 120,
        "log_source": "git_status_readonly",
        "summary_success": "Git status (read-only) completed successfully.",
    },
}

# Only these exact git argument tuples may be executed. No add/commit/push/reset.
ALLOWED_GIT_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("status", "--short"),
    ("rev-parse", "--abbrev-ref", "HEAD"),
    ("rev-parse", "HEAD"),
)
GIT_LOG_MAX_LINES = 100


class GitNotAvailableError(RuntimeError):
    """Raised when the ``git`` executable cannot be found."""

_SECRET_PATTERNS = (
    re.compile(r"(token=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(api_key=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(password=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([^\s]+)", re.IGNORECASE),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def sanitize_log_line(line: str) -> str:
    sanitized = line
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub(r"\1***", sanitized)
    return sanitized


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def append_log_line(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def read_request(job_dir: Path) -> dict[str, Any]:
    request_path = job_dir / REQUEST_FILE
    return json.loads(request_path.read_text(encoding="utf-8"))


def write_status(job_dir: Path, *, status: str, progress: int, message: str) -> None:
    write_json_atomic(
        job_dir / STATUS_FILE,
        {
            "status": status,
            "progress": progress,
            "message": message,
            "updatedUtc": utc_now_iso(),
        },
    )


def append_log(job_dir: Path, level: str, message: str, *, source: str = SOURCE) -> None:
    append_log_line(
        job_dir / LOG_FILE,
        {
            "ts": utc_now_iso(),
            "level": level,
            "message": sanitize_log_line(message),
            "source": source,
        },
    )


def write_result(job_dir: Path, result: dict[str, Any]) -> None:
    write_json_atomic(job_dir / RESULT_FILE, result)


def resolve_komponenty_paths(cwd: Path) -> tuple[str, bool]:
    candidate_a = cwd / "Komponenty"
    candidate_b = cwd.parent / "Komponenty"
    exists_a = candidate_a.is_dir()
    exists_b = candidate_b.is_dir()
    if exists_b:
        return str(candidate_b), True
    if exists_a:
        return str(candidate_a), True
    return str(candidate_b), False


def validate_project_roots(
    request: dict[str, Any],
) -> tuple[Path | None, Path | None, str | None]:
    roots = request.get("projectRoots")
    if not isinstance(roots, dict):
        return None, None, "projectRoots must be an object with cursorApiRoot and themeRoot."

    cursor_api_root_raw = roots.get("cursorApiRoot")
    if not cursor_api_root_raw or not str(cursor_api_root_raw).strip():
        return None, None, "projectRoots.cursorApiRoot is required."

    cursor_api_root = Path(str(cursor_api_root_raw)).resolve()
    if not cursor_api_root.is_dir():
        return None, None, f"projectRoots.cursorApiRoot does not exist: {cursor_api_root}"

    cwd = Path.cwd().resolve()
    if cursor_api_root != cwd:
        return None, None, (
            f"projectRoots.cursorApiRoot ({cursor_api_root}) "
            f"does not match bridge working directory ({cwd})."
        )

    tools_path = cursor_api_root / "tools"
    if not tools_path.is_dir():
        return None, None, f"tools folder not found under cursorApiRoot: {tools_path}"

    theme_root_raw = roots.get("themeRoot")
    if not theme_root_raw or not str(theme_root_raw).strip():
        return None, None, "projectRoots.themeRoot is required."

    theme_root = Path(str(theme_root_raw)).resolve()
    if not theme_root.is_dir():
        return None, None, f"projectRoots.themeRoot does not exist: {theme_root}"

    return cursor_api_root, theme_root, None


def run_ping(job_dir: Path, request: dict[str, Any]) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()

    append_log(job_dir, "Info", "Python bridge ping started")
    write_status(job_dir, status="Running", progress=25, message="Python bridge ping running.")

    time.sleep(0.15)

    write_status(job_dir, status="Running", progress=100, message="Python bridge ping finalizing.")
    finished_utc = utc_now_iso()

    payload = {
        "pythonVersion": sys.version.split()[0],
        "cwd": str(Path.cwd()),
        "jobDir": str(job_dir.resolve()),
    }

    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Succeeded",
            "exitCode": 0,
            "summary": "Python bridge ping completed successfully.",
            "warnings": [],
            "errors": [],
            "artifacts": [],
            "reportRefs": [],
            "payload": payload,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(
        job_dir,
        status="Succeeded",
        progress=100,
        message="Python bridge ping completed successfully.",
    )
    return 0


def run_env_check(job_dir: Path, request: dict[str, Any]) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()

    append_log(job_dir, "Info", "Python bridge env_check started (read-only).")
    write_status(job_dir, status="Running", progress=50, message="Running environment check.")

    cwd = Path.cwd()
    cursor_api_root = str(cwd.resolve())
    tools_path = cwd / "tools"
    komponenty_path, komponenty_exists = resolve_komponenty_paths(cwd)
    tools_exists = tools_path.is_dir()

    payload = {
        "pythonVersion": sys.version.split()[0],
        "executable": sys.executable,
        "cwd": str(cwd),
        "cursorApiRoot": cursor_api_root,
        "komponentyPath": komponenty_path,
        "komponentyExists": "true" if komponenty_exists else "false",
        "toolsPath": str(tools_path),
        "toolsExists": "true" if tools_exists else "false",
        "ok": "true",
    }

    finished_utc = utc_now_iso()
    summary = "Environment check completed (read-only)."

    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Succeeded",
            "exitCode": 0,
            "summary": summary,
            "warnings": [],
            "errors": [],
            "artifacts": [],
            "reportRefs": [],
            "payload": payload,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(job_dir, status="Succeeded", progress=100, message=summary)
    return 0


def _resolve_timeout(request: dict[str, Any], tool_spec: dict[str, Any]) -> int:
    timeout_seconds = int(request.get("timeoutSeconds") or tool_spec.get("default_timeout") or 120)
    if timeout_seconds <= 0:
        timeout_seconds = int(tool_spec.get("default_timeout") or 120)
    return timeout_seconds


def run_tool(job_dir: Path, request: dict[str, Any]) -> int:
    args = request.get("args") or {}
    if not isinstance(args, dict):
        return fail_job(job_dir, request, "tool_not_allowed", "run_tool args must be an object.")

    tool_id = str(args.get("toolId", "")).strip()
    if not tool_id:
        return fail_job(job_dir, request, "tool_not_allowed", "run_tool requires args.toolId.")

    tool_spec = ALLOWED_TOOLS.get(tool_id)
    if tool_spec is None:
        return fail_job(
            job_dir,
            request,
            "tool_not_allowed",
            f"Tool is not allowed: {tool_id}",
        )

    cursor_api_root, theme_root, roots_error = validate_project_roots(request)
    if roots_error is not None or cursor_api_root is None or theme_root is None:
        return fail_job(
            job_dir,
            request,
            "invalid_project_roots",
            roots_error or "projectRoots validation failed.",
        )

    kind = str(tool_spec.get("kind", ""))
    if kind == "subprocess_module":
        return _run_subprocess_module_tool(job_dir, request, tool_id, tool_spec, cursor_api_root)
    if kind == "builtin":
        return run_project_state_snapshot(
            job_dir, request, tool_id, tool_spec, cursor_api_root, theme_root
        )
    if kind == "git_readonly":
        return run_git_status_readonly(
            job_dir, request, tool_id, tool_spec, cursor_api_root, theme_root
        )

    return fail_job(job_dir, request, "tool_not_allowed", f"Tool kind not supported: {kind}")


def _run_subprocess_module_tool(
    job_dir: Path,
    request: dict[str, Any],
    tool_id: str,
    tool_spec: dict[str, Any],
    cursor_api_root: Path,
) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()
    log_source = str(tool_spec.get("log_source", tool_id))
    module = str(tool_spec["module"])
    module_args = list(tool_spec["args"])
    command_line = f"{sys.executable} -m {module} {' '.join(module_args)}"
    summary_success = str(tool_spec.get("summary_success", f"{tool_id} completed successfully."))
    summary_failure = str(tool_spec.get("summary_failure", f"{tool_id} failed."))

    append_log(job_dir, "Info", f"run_tool started: {tool_id}", source=log_source)
    write_status(job_dir, status="Running", progress=25, message=f"Running {tool_id}…")

    timeout_seconds = _resolve_timeout(request, tool_spec)

    payload = {
        "toolId": tool_id,
        "cursorApiRoot": str(cursor_api_root),
        "commandLine": command_line,
        "readOnly": "true",
    }

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", module, *module_args],
            cwd=str(cursor_api_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )
    except OSError as exc:
        message = f"Failed to start tool {tool_id}: {exc}"
        append_log(job_dir, "Error", message, source=log_source)
        finished_utc = utc_now_iso()
        write_result(
            job_dir,
            {
                "requestId": request_id,
                "status": "Failed",
                "exitCode": 1,
                "summary": summary_failure,
                "warnings": [],
                "errors": [{"code": "tool_start_failed", "message": message}],
                "artifacts": [],
                "reportRefs": [],
                "payload": payload,
                "startedUtc": started_utc,
                "finishedUtc": finished_utc,
            },
        )
        write_status(job_dir, status="Failed", progress=0, message=message)
        return 1

    write_status(job_dir, status="Running", progress=50, message=f"{tool_id} running…")

    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        message = f"Tool {tool_id} timed out after {timeout_seconds}s."
        if stdout:
            for line in stdout.splitlines():
                if line:
                    append_log(job_dir, "Info", line, source=log_source)
        if stderr:
            for line in stderr.splitlines():
                if line:
                    append_log(job_dir, "Warning", line, source=log_source)
        append_log(job_dir, "Error", message, source=log_source)
        finished_utc = utc_now_iso()
        write_result(
            job_dir,
            {
                "requestId": request_id,
                "status": "Failed",
                "exitCode": 1,
                "summary": summary_failure,
                "warnings": [],
                "errors": [{"code": "tool_timeout", "message": message}],
                "artifacts": [],
                "reportRefs": [],
                "payload": payload,
                "startedUtc": started_utc,
                "finishedUtc": finished_utc,
            },
        )
        write_status(job_dir, status="Failed", progress=0, message=message)
        return 1

    if stdout:
        for line in stdout.splitlines():
            if line:
                append_log(job_dir, "Info", line, source=log_source)
    if stderr:
        for line in stderr.splitlines():
            if line:
                level = "Error" if process.returncode != 0 else "Warning"
                append_log(job_dir, level, line, source=log_source)

    finished_utc = utc_now_iso()
    exit_code = process.returncode or 0

    if exit_code == 0:
        write_result(
            job_dir,
            {
                "requestId": request_id,
                "status": "Succeeded",
                "exitCode": 0,
                "summary": summary_success,
                "warnings": [],
                "errors": [],
                "artifacts": [],
                "reportRefs": [],
                "payload": payload,
                "startedUtc": started_utc,
                "finishedUtc": finished_utc,
            },
        )
        write_status(job_dir, status="Succeeded", progress=100, message=summary_success)
        return 0

    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Failed",
            "exitCode": exit_code,
            "summary": summary_failure,
            "warnings": [],
            "errors": [
                {
                    "code": "tool_exit_code",
                    "message": f"Tool {tool_id} exited with code {exit_code}.",
                }
            ],
            "artifacts": [],
            "reportRefs": [],
            "payload": payload,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(job_dir, status="Failed", progress=0, message=summary_failure)
    return 1


def run_project_state_snapshot(
    job_dir: Path,
    request: dict[str, Any],
    tool_id: str,
    tool_spec: dict[str, Any],
    cursor_api_root: Path,
    theme_root: Path,
) -> int:
    """Read-only builtin. Never spawns a subprocess and never writes project files."""

    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()
    log_source = str(tool_spec.get("log_source", tool_id))
    summary = str(tool_spec.get("summary_success", "Project state snapshot completed successfully."))

    append_log(job_dir, "Info", f"run_tool started: {tool_id}", source=log_source)
    write_status(job_dir, status="Running", progress=40, message=f"Running {tool_id}…")

    cwd = Path.cwd().resolve()
    tools_path = cursor_api_root / "tools"
    workers_bridge = cursor_api_root / "workers" / "bridge_runner.py"
    reports_performance = cursor_api_root / "reports" / "performance"
    jobs_root = job_dir.resolve().parent

    payload: dict[str, str] = {
        "toolId": tool_id,
        "readOnly": "true",
        "pythonVersion": sys.version.split()[0],
        "pythonExecutable": sys.executable,
        "cwd": str(cwd),
        "cursorApiRoot": str(cursor_api_root),
        "cursorApiRootExists": _bool_str(cursor_api_root.is_dir()),
        "toolsExists": _bool_str(tools_path.is_dir()),
        "workersBridgeRunnerExists": _bool_str(workers_bridge.is_file()),
        "reportsPerformancePath": str(reports_performance),
        "reportsPerformanceExists": _bool_str(reports_performance.is_dir()),
        "themeRoot": str(theme_root),
        "themeRootExists": _bool_str(theme_root.is_dir()),
        "jobsRoot": str(jobs_root),
        "timestampUtc": started_utc,
    }

    append_log(
        job_dir,
        "Info",
        f"cursorApiRoot exists={payload['cursorApiRootExists']} tools={payload['toolsExists']}",
        source=log_source,
    )
    append_log(
        job_dir,
        "Info",
        f"reports/performance exists={payload['reportsPerformanceExists']}",
        source=log_source,
    )
    append_log(
        job_dir,
        "Info",
        f"themeRoot exists={payload['themeRootExists']}",
        source=log_source,
    )

    # Optional, cheap counts only (no recursion, no file reads).
    if reports_performance.is_dir():
        try:
            payload["countReportBundles"] = str(
                sum(1 for entry in reports_performance.iterdir() if entry.is_dir())
            )
        except OSError:
            pass

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        jobs_candidate = Path(local_appdata) / "GicleeAppStudio" / "jobs"
        if jobs_candidate.is_dir():
            try:
                payload["countRecentJobDirs"] = str(
                    sum(1 for entry in jobs_candidate.iterdir() if entry.is_dir())
                )
            except OSError:
                pass

    finished_utc = utc_now_iso()
    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Succeeded",
            "exitCode": 0,
            "summary": summary,
            "warnings": [],
            "errors": [],
            "artifacts": [],
            "reportRefs": [],
            "payload": payload,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(job_dir, status="Succeeded", progress=100, message=summary)
    return 0


def _git_run(repo_path: Path, git_args: tuple[str, ...], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run a single allowlisted git command. shell=False, no user arguments."""

    if tuple(git_args) not in ALLOWED_GIT_COMMANDS:
        raise ValueError(f"git command not allowlisted: {list(git_args)}")
    try:
        return subprocess.run(
            ["git", "-C", str(repo_path), *git_args],
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise GitNotAvailableError(str(exc)) from exc


def _collect_repo_git_state(
    repo_path: Path,
    timeout: int,
    job_dir: Path,
    log_source: str,
    label: str,
) -> tuple[dict[str, str], bool]:
    state = {
        "branch": "Unknown",
        "head": "Unknown",
        "dirtyCount": "0",
        "hasDirtyState": "false",
    }

    rev = _git_run(repo_path, ("rev-parse", "--abbrev-ref", "HEAD"), timeout)
    if rev.returncode != 0:
        append_log(
            job_dir,
            "Warning",
            f"{label}: not a git repository or no HEAD ({repo_path}).",
            source=log_source,
        )
        return state, False

    state["branch"] = rev.stdout.strip() or "Unknown"

    head = _git_run(repo_path, ("rev-parse", "HEAD"), timeout)
    if head.returncode == 0:
        state["head"] = head.stdout.strip() or "Unknown"

    status = _git_run(repo_path, ("status", "--short"), timeout)
    if status.returncode == 0:
        lines = [line for line in status.stdout.splitlines() if line.strip()]
        state["dirtyCount"] = str(len(lines))
        state["hasDirtyState"] = _bool_str(len(lines) > 0)
        for line in lines[:GIT_LOG_MAX_LINES]:
            append_log(job_dir, "Info", f"{label}: {line}", source=log_source)
        if len(lines) > GIT_LOG_MAX_LINES:
            append_log(
                job_dir,
                "Info",
                f"{label}: (truncated, {len(lines) - GIT_LOG_MAX_LINES} more lines)",
                source=log_source,
            )
    return state, True


def run_git_status_readonly(
    job_dir: Path,
    request: dict[str, Any],
    tool_id: str,
    tool_spec: dict[str, Any],
    cursor_api_root: Path,
    theme_root: Path,
) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()
    log_source = str(tool_spec.get("log_source", tool_id))
    summary = str(tool_spec.get("summary_success", "Git status (read-only) completed successfully."))
    timeout_seconds = _resolve_timeout(request, tool_spec)

    append_log(job_dir, "Info", f"run_tool started: {tool_id}", source=log_source)
    write_status(job_dir, status="Running", progress=30, message=f"Running {tool_id}…")

    try:
        cursor_state, _ = _collect_repo_git_state(
            cursor_api_root, timeout_seconds, job_dir, log_source, "cursor-api"
        )
        write_status(job_dir, status="Running", progress=65, message=f"{tool_id}: checking theme…")
        theme_state, _ = _collect_repo_git_state(
            theme_root, timeout_seconds, job_dir, log_source, "theme"
        )
    except GitNotAvailableError as exc:
        message = f"git executable not available: {exc}"
        append_log(job_dir, "Error", message, source=log_source)
        finished_utc = utc_now_iso()
        write_result(
            job_dir,
            {
                "requestId": request_id,
                "status": "Failed",
                "exitCode": 1,
                "summary": "Git status (read-only) failed: git not available.",
                "warnings": [],
                "errors": [{"code": "git_not_available", "message": message}],
                "artifacts": [],
                "reportRefs": [],
                "payload": {"toolId": tool_id, "readOnly": "true"},
                "startedUtc": started_utc,
                "finishedUtc": finished_utc,
            },
        )
        write_status(job_dir, status="Failed", progress=0, message=message)
        return 1
    except subprocess.TimeoutExpired:
        message = f"Tool {tool_id} timed out after {timeout_seconds}s."
        append_log(job_dir, "Error", message, source=log_source)
        finished_utc = utc_now_iso()
        write_result(
            job_dir,
            {
                "requestId": request_id,
                "status": "Failed",
                "exitCode": 1,
                "summary": "Git status (read-only) failed: timeout.",
                "warnings": [],
                "errors": [{"code": "git_timeout", "message": message}],
                "artifacts": [],
                "reportRefs": [],
                "payload": {"toolId": tool_id, "readOnly": "true"},
                "startedUtc": started_utc,
                "finishedUtc": finished_utc,
            },
        )
        write_status(job_dir, status="Failed", progress=0, message=message)
        return 1

    payload = {
        "toolId": tool_id,
        "readOnly": "true",
        "cursorApiBranch": cursor_state["branch"],
        "cursorApiHead": cursor_state["head"],
        "cursorApiDirtyCount": cursor_state["dirtyCount"],
        "cursorApiHasDirtyState": cursor_state["hasDirtyState"],
        "themeBranch": theme_state["branch"],
        "themeHead": theme_state["head"],
        "themeDirtyCount": theme_state["dirtyCount"],
        "themeHasDirtyState": theme_state["hasDirtyState"],
    }

    finished_utc = utc_now_iso()
    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Succeeded",
            "exitCode": 0,
            "summary": summary,
            "warnings": [],
            "errors": [],
            "artifacts": [],
            "reportRefs": [],
            "payload": payload,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(job_dir, status="Succeeded", progress=100, message=summary)
    return 0


def fail_job(job_dir: Path, request: dict[str, Any], code: str, message: str) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()
    finished_utc = utc_now_iso()

    append_log(job_dir, "Error", message)
    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Failed",
            "exitCode": 1,
            "summary": message,
            "warnings": [],
            "errors": [{"code": code, "message": message}],
            "artifacts": [],
            "reportRefs": [],
            "payload": None,
            "startedUtc": started_utc,
            "finishedUtc": finished_utc,
        },
    )
    write_status(job_dir, status="Failed", progress=0, message=message)
    return 1


def dispatch(job_dir: Path, request: dict[str, Any]) -> int:
    command = str(request.get("command", "")).strip().lower()
    if command == "ping":
        return run_ping(job_dir, request)
    if command == "env_check":
        return run_env_check(job_dir, request)
    if command == "run_tool":
        return run_tool(job_dir, request)
    return fail_job(job_dir, request, "unknown_command", f"Unknown command: {command}")


def run_job(job_dir: Path) -> int:
    job_dir = job_dir.resolve()
    if not job_dir.is_dir():
        print(f"Job directory does not exist: {job_dir}", file=sys.stderr)
        return 1

    try:
        request = read_request(job_dir)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read worker request: {exc}", file=sys.stderr)
        return 1

    return dispatch(job_dir, request)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GicleeApp Studio Python bridge runner (GAS-2C)")
    parser.add_argument("--job", required=True, help="Absolute path to the worker job directory")
    args = parser.parse_args(argv)
    return run_job(Path(args.job))


if __name__ == "__main__":
    raise SystemExit(main())
