"""Minimal Python bridge runner for GicleeApp Studio worker jobs (GAS-2B/2C)."""

from __future__ import annotations

import argparse
import json
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

ALLOWED_TOOLS: dict[str, dict[str, Any]] = {
    "performance_agent_doctor": {
        "module": "tools.performance_agent",
        "args": ["--doctor"],
        "read_only": True,
        "default_timeout": 120,
        "log_source": "performance_agent_doctor",
    },
}

_SECRET_PATTERNS = (
    re.compile(r"(token=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(api_key=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(password=)([^\s]+)", re.IGNORECASE),
    re.compile(r"(bearer\s+)([^\s]+)", re.IGNORECASE),
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def validate_project_roots(request: dict[str, Any]) -> tuple[Path | None, str | None]:
    roots = request.get("projectRoots")
    if not isinstance(roots, dict):
        return None, "projectRoots must be an object with cursorApiRoot."

    cursor_api_root_raw = roots.get("cursorApiRoot")
    if not cursor_api_root_raw or not str(cursor_api_root_raw).strip():
        return None, "projectRoots.cursorApiRoot is required."

    cursor_api_root = Path(str(cursor_api_root_raw)).resolve()
    if not cursor_api_root.is_dir():
        return None, f"projectRoots.cursorApiRoot does not exist: {cursor_api_root}"

    cwd = Path.cwd().resolve()
    if cursor_api_root != cwd:
        return None, (
            f"projectRoots.cursorApiRoot ({cursor_api_root}) "
            f"does not match bridge working directory ({cwd})."
        )

    tools_path = cursor_api_root / "tools"
    if not tools_path.is_dir():
        return None, f"tools folder not found under cursorApiRoot: {tools_path}"

    return cursor_api_root, None


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


def run_tool(job_dir: Path, request: dict[str, Any]) -> int:
    request_id = request.get("requestId", "")
    started_utc = utc_now_iso()

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

    cursor_api_root, roots_error = validate_project_roots(request)
    if roots_error is not None:
        return fail_job(job_dir, request, "invalid_project_roots", roots_error)

    log_source = str(tool_spec.get("log_source", tool_id))
    module = str(tool_spec["module"])
    module_args = list(tool_spec["args"])
    command_line = f"{sys.executable} -m {module} {' '.join(module_args)}"

    append_log(job_dir, "Info", f"run_tool started: {tool_id}", source=log_source)
    write_status(job_dir, status="Running", progress=25, message=f"Running {tool_id}…")

    timeout_seconds = int(request.get("timeoutSeconds") or tool_spec.get("default_timeout") or 120)
    if timeout_seconds <= 0:
        timeout_seconds = int(tool_spec.get("default_timeout") or 120)

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
                "summary": f"Performance Agent doctor failed.",
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
                "summary": "Performance Agent doctor failed.",
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
        summary = "Performance Agent doctor completed successfully."
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

    summary = "Performance Agent doctor failed."
    write_result(
        job_dir,
        {
            "requestId": request_id,
            "status": "Failed",
            "exitCode": exit_code,
            "summary": summary,
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
    write_status(job_dir, status="Failed", progress=0, message=summary)
    return 1


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
